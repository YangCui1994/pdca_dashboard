"""OpenAI-compatible runtime: chat-completions SSE streaming, stdlib only.

满足 RuntimeGateway 协议:任何 OpenAI 兼容端点(opencode serve、Ollama、
LM Studio、aigate /v1)都能即插即用。模型输出必须是约定 JSON,运行时
解析为 Proposal;解析或传输失败以 FAILED 事件显式暴露,绝不伪装成功。
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable

from workbench.domain.models import Proposal, ProposedChange
from workbench.runtime.contracts import (
    COMPLETED,
    FAILED,
    QUEUED,
    RUNNING,
    RunEvent,
    RunRequest,
)

_SYSTEM_PROMPT = """你是个人工作台的项目审查助手。只输出一个 JSON 对象,不要输出任何其他文字。
格式:
{
  "proposal_id": "prop-<短标识>",
  "summary": "一句话说明建议",
  "changes": [
    {
      "field": "action.status",
      "target_id": "<project_id>:<action_id>",
      "current_value": "当前状态",
      "new_value": "in_progress | waiting | deferred | completed | cancelled"
    }
  ],
  "facts": ["只能写上下文中可核实的事实"],
  "inferences": ["你的推断写在这里"],
  "external_knowledge": ["引用的通用经验写在这里"]
}
约束:changes 只允许 action.status 字段;没有值得改的就给空数组;
不要把推断混进 facts。"""


def _http_post_sse(url: str, headers: dict, payload: dict, timeout: int):
    """Default transport: POST and yield SSE lines (injectable for tests)."""

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.strip():
                yield line


def _extract_json(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _proposal_from(payload: dict, request: RunRequest) -> Proposal:
    def _strings(key):
        value = payload.get(key, [])
        return tuple(str(item) for item in value) if isinstance(value, list) else ()

    changes = []
    for change in payload.get("changes", []) or []:
        if not isinstance(change, dict) or "field" not in change or "target_id" not in change:
            continue
        changes.append(
            ProposedChange(
                field=str(change["field"]),
                target_id=str(change["target_id"]),
                current_value=str(change.get("current_value", "")),
                new_value=str(change.get("new_value", "")),
            )
        )
    return Proposal(
        proposal_id=str(payload.get("proposal_id") or f"prop-{request.kind}-{request.project_id}"),
        request_kind=request.kind,
        project_id=request.project_id,
        summary=str(payload.get("summary", "")),
        changes=tuple(changes),
        facts=_strings("facts"),
        inferences=_strings("inferences"),
        external_knowledge=_strings("external_knowledge"),
    )


class OpenAICompatibleRuntime:
    """RuntimeGateway over an OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: int = 120,
        build_context: Callable[[RunRequest], str] | None = None,
        transport=None,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._build_context = build_context or (lambda _request: "")
        self._transport = transport or _http_post_sse

    def events(self, request: RunRequest):
        seq = 0

        def _next(state, **kwargs):
            nonlocal seq
            seq += 1
            return RunEvent(seq=seq, state=state, **kwargs)

        yield _next(QUEUED, message=f"queued {request.kind}")
        yield _next(RUNNING, message=f"请求 {self._base_url} · {self._model}")

        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": self._build_context(request)},
            ],
        }

        collected: list[str] = []
        try:
            for line in self._transport(
                f"{self._base_url}/chat/completions", headers, payload, self._timeout
            ):
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if delta:
                    collected.append(delta)
                    yield _next(RUNNING, message=delta)
        except Exception as exc:  # 传输失败必须显式暴露,不伪装 completed
            yield _next(FAILED, message=f"运行失败:{exc}")
            return

        parsed = _extract_json("".join(collected))
        if parsed is None:
            yield _next(FAILED, message="模型输出未包含可解析的 Proposal JSON")
            return
        yield _next(
            COMPLETED,
            message="run completed",
            proposal=_proposal_from(parsed, request),
        )
