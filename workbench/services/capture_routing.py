"""智能捕获路由与计划建议解析(纯函数,原型 A/E 的规则收编为正式版)。

捕获路由规则刻意保持简单可记:
    `!文字`       → 直接成为今日计划项
    `#项目名 文字` → 成为该项目的今日计划项(项目名包含匹配)
    其他任何文字   → 成为待整理想法
"""

from __future__ import annotations

import re

_PLAN_LINE = re.compile(r"^\s*\d+[.、]\s*(.+)$")


def route_capture(text: str, project_names: dict[str, str]) -> tuple[str, str, str]:
    """(kind, cleaned_text, project_id);kind ∈ {"plan", "idea"}。

    project_names 是 {项目名: project_id} 映射;调用方从 service 取。
    """

    cleaned = text.strip().replace("\u3000", " ")  # 全角空格按分隔符处理
    if cleaned.startswith("!"):
        return "plan", cleaned[1:].strip(), ""
    if cleaned.startswith("#"):
        head, _, rest = cleaned[1:].partition(" ")
        for name, project_id in project_names.items():
            if name in head:
                return "plan", rest.strip() or head, project_id
        return "idea", cleaned, ""
    return "idea", cleaned, ""


def parse_plan_lines(text: str) -> list[tuple[str, str]]:
    """计划建议草稿 → [(条目文本, project_id|"")]。

    草稿约定每行「1. 条目内容」;(proj-xxx) 尾注表示归属项目。
    """

    items: list[tuple[str, str]] = []
    for raw in text.splitlines():
        match = _PLAN_LINE.match(raw.strip())
        if not match:
            continue
        line = match.group(1)
        project_id = ""
        token = re.search(r"\((proj-[\w-]+)\)", line)
        if token:
            project_id = token.group(1)
            line = (line[: token.start()] + line[token.end():]).strip(" 　")
        items.append((line, project_id))
    return items
