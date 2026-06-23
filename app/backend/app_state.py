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

    def capture_direct(
        self,
        raw_text: str,
        title: str = "未命名输入",
        kind: CaptureKind = "idea",
    ) -> dict[str, str]:
        capture = Capture(title=title, kind=kind, raw_text=raw_text)
        path = self.storage.save_capture(capture, created=date.today().isoformat())
        return {"path": str(path), "ai_output": ""}

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

    def draft_document_update(self, path: str, document: str, instruction: str, skills: str = "") -> dict[str, str]:
        item = self.storage.read_work_item(path)
        document_fields = {
            "task": "task",
            "context": "context",
            "events": "events",
            "ai-notes": "ai_notes",
        }
        if document not in document_fields:
            raise ValueError(f"Unsupported document: {document}")
        current_markdown = item[document_fields[document]]
        prompt = self._render_document_helper_prompt(
            title=item["title"],
            document=document,
            current_markdown=current_markdown,
            instruction=instruction,
            skills=skills,
        )
        return {"draft": self.ai_provider.complete(prompt)}

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

    def _render_document_helper_prompt(
        self,
        title: str,
        document: str,
        current_markdown: str,
        instruction: str,
        skills: str,
    ) -> str:
        return f"""你是 Quiet Workbench 的文档整理助手。

请只输出更新后的 Markdown，不要输出 HTML。HTML 预览会由系统从 Markdown 自动渲染。

任务标题：{title}
文档：{document}
用户想使用的 skills / 辅助视角：{skills or "未指定"}
用户输入或修改要求：
{instruction}

当前 Markdown：
```markdown
{current_markdown}
```

要求：
- 保留事实，不要编造外部信息。
- 如果用户只是补充新进展，把它整合进合适的小节。
- 如果是 task.md，保持任务目标、卡点、已有基础、下一步、产出物清楚。
- 如果需要首页短摘要，可在 frontmatter 中保留或新增一行 `summary: <不超过 20 字的一句话>`。
- 输出完整 Markdown 草稿，等待用户确认后再保存。
"""
