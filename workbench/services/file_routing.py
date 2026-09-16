"""file_route:监听到的文件 → 项目进度路由决策。

AI(或 fake)按 stages/file_route.md 的约定输出 JSON;这里做宽容解析。
决策三分类:
  high   → 自动追加项目进度(UI 必须给一键撤销)
  low    → 出草稿卡等人工确认
  none   → 无关,忽略并留痕
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workbench.runtime.text_runtime import FakePromptRuntime
    from workbench.services.prompt_library import PromptLibrary


@dataclass(frozen=True)
class RouteDecision:
    file_name: str
    project_id: str  # "none" 表示无关
    confidence: str  # "high" | "low" | "none"
    progress_entry: str
    reason: str
    raw: str

    @property
    def auto_append(self) -> bool:
        return self.project_id != "none" and self.confidence == "high" and bool(self.progress_entry.strip())


def route_file(
    runtime: "FakePromptRuntime",
    library: "PromptLibrary",
    projects_summary: str,
    file_path: Path,
) -> RouteDecision:
    """Read a watched file and ask (fake or real) AI where it belongs."""

    from workbench.runtime.text_runtime import collect_text  # 局部导入避免环

    spec = library.get("stages", "file_route")
    file_text = file_path.read_text(encoding="utf-8", errors="replace")
    variables = {
        "file_name": file_path.name,
        "file_text": file_text[:4000],
        "project_brief": projects_summary,
    }
    rendered = spec.render(**variables)
    text, _ = collect_text(runtime.complete(spec, rendered, variables=variables))
    return parse_route_decision(file_path.name, text or "")


def parse_route_decision(file_name: str, text: str) -> RouteDecision:
    """Tolerant JSON extraction: first {...} block wins, else route to none."""

    payload = {}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            payload = {}
    project_id = str(payload.get("related_project_id", "none")) or "none"
    confidence = str(payload.get("confidence", "none")) or "none"
    if project_id == "none":
        confidence = "none"
    return RouteDecision(
        file_name=file_name,
        project_id=project_id,
        confidence=confidence,
        progress_entry=str(payload.get("progress_entry", "")),
        reason=str(payload.get("reason", "")),
        raw=text,
    )
