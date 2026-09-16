"""草稿文本运行时(与 workbench RuntimeGateway 同风格,流式事件)。

- FakePromptRuntime:零 IO、确定性,离线可验证;优先用提示词文件里的
  ``<fake>…</fake>`` 输出,file_route 阶段输出确定性 JSON。
- OpenAITextRuntime:OpenAI 兼容 chat-completions(SSE,纯 stdlib),
  只取文本,不解析 Proposal(草稿是自由文本/JSON,不是提案对象)。

两者都只产"草稿文本";写盘一律由 UI 的人工确认动作完成。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from workbench.services.prompt_library import PromptSpec

_QUEUED, _RUNNING, _COMPLETED, _FAILED = "queued", "running", "completed", "failed"


@dataclass(frozen=True)
class TextEvent:
    seq: int
    state: str
    message: str = ""


class FakePromptRuntime:
    """确定性草稿生成器:同一输入永远同一输出,便于测试断言。"""

    def __init__(self, latency_events: int = 3):
        self.latency_events = latency_events

    def complete(
        self, spec: "PromptSpec", rendered: str, *, variables: dict[str, str] | None = None
    ) -> Iterator[TextEvent]:
        variables = variables or {}
        seq = 0
        seq += 1
        yield TextEvent(seq, _QUEUED, f"queued {spec.namespace}/{spec.key}")
        for i in range(self.latency_events):
            seq += 1
            yield TextEvent(seq, _RUNNING, f"drafting {i + 1}/{self.latency_events}")
        seq += 1
        yield TextEvent(seq, _COMPLETED, message=self._answer(spec, rendered, variables))

    def _answer(self, spec: "PromptSpec", rendered: str, variables: dict[str, str]) -> str:
        if spec.key == "file_route":
            return _fake_file_route(variables)
        return spec.fake_reply(rendered)


def _fake_file_route(variables: dict[str, str]) -> str:
    """确定性路由:取项目清单里第一个 proj-* id,文件含『[低置信]』则降级。"""

    file_text = variables.get("file_text", "")
    brief = variables.get("project_brief", "")
    match = re.search(r"proj-[\w-]+", brief)
    if not match:
        payload = {
            "related_project_id": "none",
            "confidence": "none",
            "progress_entry": "",
            "reason": "项目清单为空(fake 确定性判断)",
        }
        return json.dumps(payload, ensure_ascii=False)
    project_id = match.group(0)
    confidence = "low" if "[低置信]" in file_text else "high"
    first_line = next((ln.strip() for ln in file_text.splitlines() if ln.strip()), "")
    payload = {
        "related_project_id": project_id,
        "confidence": confidence,
        "progress_entry": f"来自文件《{variables.get('file_name', '')}》:{first_line[:60]}",
        "reason": "标题命中项目关键词(fake 确定性判断)",
    }
    return json.dumps(payload, ensure_ascii=False)


class OpenAITextRuntime:
    """OpenAI 兼容端点的最小文本补全(SSE,stdlib only)。"""

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(
        self, spec: "PromptSpec", rendered: str, *, variables: dict[str, str] | None = None
    ) -> Iterator[TextEvent]:
        seq = 0
        seq += 1
        yield TextEvent(seq, _QUEUED, f"queued {spec.key}")
        seq += 1
        yield TextEvent(seq, _RUNNING, f"请求 {self.base_url} · {self.model}")
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": rendered}],
                "stream": True,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key or os.environ.get('WORKBENCH_AI_API_KEY', '')}",
            },
        )
        chunks: list[str] = []
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                for raw in resp:
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    payload = json.loads(data)
                    # 容错:usage/心跳等无 choices 的 chunk 直接跳过
                    choices = payload.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}).get("content")
                    if delta:
                        chunks.append(delta)
                        seq += 1
                        yield TextEvent(seq, _RUNNING, delta)
        except Exception as exc:  # noqa: BLE001 — 失败必须显式暴露,绝不伪装完成
            seq += 1
            yield TextEvent(seq, _FAILED, f"运行失败:{exc}")
            return
        seq += 1
        yield TextEvent(seq, _COMPLETED, message="".join(chunks))


def collect_text(events: Iterator[TextEvent]) -> tuple[str | None, list[str]]:
    """Drain an event stream; returns (final_text, trace). Fake/failed aware."""

    trace: list[str] = []
    text: str | None = None
    for event in events:
        trace.append(f"{event.state}:{event.message[:60]}")
        if event.state == _COMPLETED:
            text = event.message
        if event.state == _FAILED:
            text = None
    return text, trace


def generate_async(
    page,
    runtime,
    spec,
    rendered: str,
    *,
    variables: dict[str, str] | None = None,
    on_done,
    on_error,
) -> None:
    """后台线程跑草稿生成,真实端点不冻结界面(Flet 0.86 page.run_thread)。

    on_done(final_text) / on_error() 在工作线程里被回调;回调内部改完
    控件后自行 update()(Flet 的 update 可跨线程发送)。page 为 None
    (离线构建/测试)时退化为同步执行,行为与原型一致。
    """

    def _run() -> tuple[str | None, list[str]]:
        return collect_text(runtime.complete(spec, rendered, variables=variables or {}))

    if page is None:
        text, _trace = _run()
        if text is None:
            on_error()
        else:
            on_done(text)
        return

    def worker():
        text, _trace = _run()
        if text is None:
            on_error()
        else:
            on_done(text)

    page.run_thread(worker)
