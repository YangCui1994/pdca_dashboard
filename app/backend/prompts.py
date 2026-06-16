from __future__ import annotations

from pathlib import Path


def render_prompt(template_path: Path, user_input: str) -> str:
    template = template_path.read_text(encoding="utf-8")
    return template.replace("{{input}}", user_input)
