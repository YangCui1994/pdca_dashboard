"""提示词双轴注册表:一阶段/一思维模式一个 markdown 文件。

正式家目录为 ``workbench/prompts``(原型家 prototypes/ux-2026-09/prompts
同源)。目录布局:

    stages/    阶段提示词(到点自动触发):capture_critique / plan_suggest /
               day_check / weekly_review / file_route
    thinking/  思维方式库(用户点名触发):brainstorm / grill_me / six_hats /
               premortem …… 扔进一个 md 即新增模式,下拉框自动列出

每个文件用极简 front matter 自声明边界:

    ---
    name: brainstorm            # 注册键(缺省取文件名)
    title: 头脑风暴              # 下拉框显示名
    reads: 选中目标文本;项目清单  # 前置读取(给人看的边界声明)
    writes: 只产草稿,不直接落盘  # 允许产出(给人看的边界声明)
    ---
    正文:实际提示词模板,{{var}} 占位符在 render 时替换。

正文里约定一行 ``<fake>…</fake>``,FakePromptRuntime 用它作为离线
确定性输出(见 runtime/text_runtime.py);没有该行则回显输入。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_VAR = re.compile(r"\{\{(\w+)\}\}")
_FAKE = re.compile(r"<fake>\n?(.*?)</fake>", re.DOTALL)

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"


@dataclass(frozen=True)
class PromptSpec:
    """One registered prompt file (stage or thinking mode)."""

    key: str
    title: str
    namespace: str  # "stages" | "thinking"
    reads: str
    writes: str
    template: str
    fake_output: str  # 离线确定性输出;空串表示回显输入
    path: Path

    def render(self, **variables: str) -> str:
        """Replace {{vars}}; unknown placeholders are left visible on purpose."""

        def _sub(match: re.Match) -> str:
            return variables.get(match.group(1), match.group(0))

        return _VAR.sub(_sub, self.template).strip()

    def fake_reply(self, rendered_prompt: str) -> str:
        """The deterministic offline answer for this prompt."""

        if self.fake_output.strip():
            return self.fake_output.strip()
        return f"[fake] {rendered_prompt[:120]}"


class PromptLibrary:
    """Discovers and renders stage prompts and thinking modes."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root is not None else PROMPTS_ROOT
        self._specs: dict[str, PromptSpec] = {}
        for namespace in ("stages", "thinking"):
            for md in sorted((self.root / namespace).glob("*.md")):
                spec = _load_spec(md, namespace)
                self._specs[f"{namespace}/{spec.key}"] = spec

    def get(self, namespace: str, key: str) -> PromptSpec:
        spec = self._specs.get(f"{namespace}/{key}")
        if spec is None:
            raise KeyError(f"unknown prompt: {namespace}/{key}")
        return spec

    def stages(self) -> list[PromptSpec]:
        return [s for s in self._specs.values() if s.namespace == "stages"]

    def thinking(self) -> list[PromptSpec]:
        """思维模式注册表:目录里有什么文件,下拉框就有什么模式。"""

        return [s for s in self._specs.values() if s.namespace == "thinking"]


def projects_summary(service) -> str:
    """渲染 {{project_brief}}:一行一个项目,含 id/名称/焦点/行动概览。"""

    lines = []
    for project in service.projects():
        open_actions = [
            a for a in project.actions
            if a.status in ("pending", "in_progress", "waiting")
        ]
        lines.append(
            f"{project.project_id} {project.name}|目标:{project.goal or '未填'}"
            f"|当前焦点:{project.current_focus or '未填'}|进行中行动:"
            + (";".join(a.title for a in open_actions) or "无")
        )
    return "\n".join(lines)


def _load_spec(path: Path, namespace: str) -> PromptSpec:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    head = _FRONT.match(text)
    if head:
        for line in head.group(1).splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        body = text[head.end():]
    fake = _FAKE.search(body)
    if fake:
        body = body[: fake.start()] + body[fake.end():]
    key = meta.get("name") or path.stem
    return PromptSpec(
        key=key,
        title=meta.get("title") or key,
        namespace=namespace,
        reads=meta.get("reads", ""),
        writes=meta.get("writes", ""),
        template=body.strip(),
        fake_output=fake.group(1).strip() if fake else "",
        path=path,
    )
