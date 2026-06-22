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
    "pdca_gate": Path("app/prompts/pdca_gate.md"),
    "pdca_periodic_review": Path("app/prompts/pdca_periodic_review.md"),
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

    def analyze_pdca_entry(self, title: str, plan: str, do: str, check: str, act: str) -> dict[str, str]:
        raw_text = self._render_pdca_input(plan, do, check, act)
        prompt = render_prompt(PROMPT_MAP["pdca_gate"], raw_text)
        ai_output = self.ai_provider.complete(prompt)
        log_path = self.storage.append_pdca_entry(
            title=title,
            plan=plan,
            do=do,
            check=check,
            act=act,
            ai_output=ai_output,
        )
        return {"log_path": str(log_path), "ai_output": ai_output}

    def review_pdca_history(self, limit: int = 20) -> dict[str, str]:
        history = self.storage.read_recent_pdca_entries(limit=limit)
        prompt = render_prompt(PROMPT_MAP["pdca_periodic_review"], history or "还没有可 review 的 PDCA 输入记录。")
        ai_output = self.ai_provider.complete(prompt)
        review_path = self.storage.save_pdca_review(ai_output)
        return {"review_path": str(review_path), "ai_output": ai_output}

    def list_files(self) -> list[str]:
        return [str(path) for path in self.storage.list_work_items()]

    def list_work_item_summaries(self) -> list[dict]:
        return self.storage.list_work_item_summaries()

    def get_work_item(self, path: str) -> dict:
        return self.storage.read_work_item(path)

    def save_work_item(self, path: str, task: str, context: str, ai_notes: str, events: str = "") -> None:
        self.storage.save_work_item(path, task=task, context=context, ai_notes=ai_notes, events=events)

    def render_agent_context(self, path: str) -> str:
        return self.storage.render_agent_context(path)

    def move_work_item_status(self, path: str, status: str) -> dict[str, str]:
        moved = self.storage.move_work_item_status(path, status)
        return {"path": str(moved)}

    def append_work_item_event(self, path: str, event: str) -> dict[str, str]:
        events_path = self.storage.append_work_item_event(path, event)
        return {"path": str(events_path), "ok": True}

    def context_readiness(self, path: str) -> dict:
        return self.storage.context_readiness(path)

    def _render_pdca_input(self, plan: str, do: str, check: str, act: str) -> str:
        return f"""# PDCA Input

## Plan

{plan}

## Do

{do}

## Check

{check}

## Act

{act}
"""
