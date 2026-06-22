from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from app.backend.markdown import render_capture_markdown, render_project_home
from app.backend.models import Capture, Project, normalize_slug


class VaultStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for folder in ("inbox", "active", "waiting", "done", "archive"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def save_capture(self, capture: Capture, created: str) -> Path:
        folder = self._unique_child_folder(self.root / capture.status, f"{created}-{normalize_slug(capture.title)}")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        (folder / "task.md").write_text(render_capture_markdown(capture, created), encoding="utf-8")
        (folder / "context.md").write_text("# Context\n\n", encoding="utf-8")
        (folder / "ai-notes.md").write_text("# AI Notes\n\n", encoding="utf-8")
        (folder / "events.md").write_text("# Events\n\n", encoding="utf-8")
        return folder

    def create_project(self, project: Project) -> Path:
        folder = self.root / project.status / project.folder_name()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        (folder / "project.md").write_text(render_project_home(project), encoding="utf-8")
        (folder / "tasks.md").write_text("# Tasks\n\n", encoding="utf-8")
        (folder / "log.md").write_text("# Log\n\n", encoding="utf-8")
        (folder / "ai-notes.md").write_text("# AI Notes\n\n", encoding="utf-8")
        return folder

    def list_markdown_files(self) -> list[Path]:
        return sorted(self.root.glob("**/*.md"))

    def list_work_items(self) -> list[Path]:
        items: list[Path] = []
        for status in ("inbox", "active", "waiting", "done", "archive"):
            folder = self.root / status
            items.extend(path for path in folder.iterdir() if path.is_dir() and (path / "task.md").exists())
            items.extend(folder.glob("*.md"))
        return sorted(items)

    def list_work_item_summaries(self) -> list[dict[str, Any]]:
        summaries = []
        for path in self.list_work_items():
            item = self.read_work_item(path)
            summaries.append(
                {
                    "path": item["path"],
                    "title": item["title"],
                    "status": item["status"],
                    "created": self._created_from_path(Path(item["path"])),
                    "blocker": self._extract_section_first_line(item["task"], "当前卡点"),
                    "basis": self._extract_section_first_line(item["task"], "已有基础")
                    or self._first_non_empty_line(item["context"]),
                    "last_event": self._last_event_line(item.get("events", "")),
                }
            )
        return summaries

    def read_work_item(self, path: Path | str) -> dict[str, Any]:
        item_path = self._resolve_work_item(path)
        if item_path.is_dir():
            return {
                "path": str(item_path),
                "title": self._title_from_path(item_path),
                "status": item_path.parent.name,
                "task": self._read_optional_text(item_path / "task.md"),
                "context": self._read_optional_text(item_path / "context.md"),
                "ai_notes": self._read_optional_text(item_path / "ai-notes.md"),
                "events": self._read_optional_text(item_path / "events.md"),
                "assets": self._list_assets(item_path),
            }
        return {
            "path": str(item_path),
            "title": self._title_from_path(item_path),
            "status": item_path.parent.name,
            "task": item_path.read_text(encoding="utf-8"),
            "context": "",
            "ai_notes": "",
            "events": "",
            "assets": [],
        }

    def save_work_item(self, path: Path | str, task: str, context: str, ai_notes: str, events: str = "") -> None:
        item_path = self._resolve_work_item(path)
        if item_path.is_dir():
            (item_path / "task.md").write_text(task, encoding="utf-8")
            (item_path / "context.md").write_text(context, encoding="utf-8")
            (item_path / "ai-notes.md").write_text(ai_notes, encoding="utf-8")
            (item_path / "events.md").write_text(events, encoding="utf-8")
            return
        item_path.write_text(task, encoding="utf-8")

    def render_agent_context(self, path: Path | str) -> str:
        item = self.read_work_item(path)
        assets = "\n".join(f"- {asset}" for asset in item["assets"]) or "- None"
        return f"""# Agent Task Context

Path: {item["path"]}
Status: {item["status"]}

## task.md

{item["task"]}

## context.md

{item["context"]}

## ai-notes.md

{item["ai_notes"]}

## events.md

{item["events"]}

## assets

{assets}
"""

    def _unique_child_folder(self, parent: Path, name: str) -> Path:
        candidate = parent / name
        suffix = 2
        while candidate.exists():
            candidate = parent / f"{name}-{suffix}"
            suffix += 1
        return candidate

    def _resolve_work_item(self, path: Path | str) -> Path:
        resolved_root = self.root.resolve()
        resolved_path = Path(path).resolve()
        if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
            raise ValueError("Work item path must be inside the vault")
        if not resolved_path.exists():
            raise FileNotFoundError(f"Work item not found: {path}")
        if resolved_path.is_dir() and not (resolved_path / "task.md").exists():
            raise ValueError("Work item folder must contain task.md")
        return resolved_path

    def _read_optional_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _list_assets(self, folder: Path) -> list[str]:
        assets_folder = folder / "assets"
        if not assets_folder.is_dir():
            return []
        return sorted(str(path.relative_to(assets_folder)) for path in assets_folder.rglob("*") if path.is_file())

    def _title_from_path(self, path: Path) -> str:
        title = path.stem if path.is_file() else path.name
        return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", title)

    def _created_from_path(self, path: Path) -> str:
        name = path.stem if path.is_file() else path.name
        match = re.match(r"^(\d{4}-\d{2}-\d{2})-", name)
        return match.group(1) if match else ""

    def _extract_section_first_line(self, markdown: str, heading: str) -> str:
        lines = markdown.splitlines()
        inside = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                inside = stripped == f"## {heading}"
                continue
            if inside and stripped and not stripped.startswith("#"):
                return stripped.removeprefix("- ").strip()
        return ""

    def _first_non_empty_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped.removeprefix("- ").strip()
        return ""

    def _last_event_line(self, text: str) -> str:
        events = [
            line.strip().removeprefix("- ").strip()
            for line in text.splitlines()
            if line.strip().startswith("- ")
        ]
        return events[-1] if events else ""
