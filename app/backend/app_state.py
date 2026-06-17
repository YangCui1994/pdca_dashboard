from __future__ import annotations

from datetime import date
from pathlib import Path

from app.backend.ai import AIProvider, FakeAIProvider
from app.backend.models import Capture, CaptureKind
from app.backend.prompts import render_prompt
from app.backend.storage import VaultStorage


PROMPT_MAP = {
    "idea_critique": Path("app/prompts/idea_critique.md"),
    "structure_capture": Path("app/prompts/structure_capture.md"),
    "daily_review": Path("app/prompts/daily_review.md"),
}


class WorkbenchApp:
    def __init__(self, vault_root: Path, ai_provider: AIProvider | None = None) -> None:
        self.storage = VaultStorage(vault_root)
        self.ai_provider = ai_provider or FakeAIProvider()

    def capture_with_ai(
        self,
        raw_text: str,
        action: str,
        title: str = "未命名输入",
        kind: CaptureKind = "idea",
    ) -> dict[str, str]:
        if action not in PROMPT_MAP:
            raise ValueError(f"Unsupported AI action: {action}")
        prompt = render_prompt(PROMPT_MAP[action], raw_text)
        ai_output = self.ai_provider.complete(prompt)
        capture = Capture(title=title, kind=kind, raw_text=raw_text, ai_output=ai_output)
        path = self.storage.save_capture(capture, created=date.today().isoformat())
        return {"path": str(path), "ai_output": ai_output}

    def list_files(self) -> list[str]:
        return [str(path) for path in self.storage.list_work_items()]

    def get_work_item(self, path: str) -> dict:
        return self.storage.read_work_item(path)

    def save_work_item(self, path: str, task: str, context: str, ai_notes: str) -> None:
        self.storage.save_work_item(path, task=task, context=context, ai_notes=ai_notes)

    def render_agent_context(self, path: str) -> str:
        return self.storage.render_agent_context(path)
