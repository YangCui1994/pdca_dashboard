from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Any

from app.backend.markdown import render_capture_markdown, render_project_home
from app.backend.models import Capture, Project, VAULT_STATUSES, normalize_slug


class VaultStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for folder in ("inbox", "active", "waiting", "done", "archive", "reviews"):
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
            metadata = self._frontmatter(item["task"])
            summaries.append(
                {
                    "path": item["path"],
                    "title": item["title"],
                    "status": item["status"],
                    "created": metadata.get("created", "") or self._created_from_path(Path(item["path"])),
                    "tags": metadata.get("tags", []),
                    "summary": self._card_summary(item["task"]),
                    "blocker": self._short_text(self._extract_section_first_line(item["task"], "当前卡点")),
                    "basis": self._short_text(
                        self._extract_section_first_line(item["task"], "已有基础")
                        or self._first_non_empty_line(item["context"])
                    ),
                    "last_event": self._short_text(self._last_event_line(item.get("events", ""))),
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
        metadata = self._frontmatter(item["task"])
        tags = ", ".join(metadata.get("tags", [])) or "None"
        readiness = self.context_readiness(path)
        missing = "\n".join(f"- {entry}" for entry in readiness["missing"]) or "- None"
        return f"""# Agent Task Context

Path: {item["path"]}
Title: {item["title"]}
Status: {item["status"]}
Created: {metadata.get("created", self._created_from_path(Path(item["path"])))}
Tags: {tags}

## context-readiness

Ready: {readiness["ready"]}
Missing:
{missing}

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

    def move_work_item_status(self, path: Path | str, status: str) -> Path:
        if status not in VAULT_STATUSES:
            raise ValueError(f"Unsupported vault status: {status}")
        item_path = self._resolve_work_item(path)
        target_parent = self.root / status
        target_parent.mkdir(parents=True, exist_ok=True)
        if item_path.parent == target_parent:
            return item_path
        if item_path.is_dir():
            target = self._unique_child_folder(target_parent, item_path.name)
        else:
            target = self._unique_child_path(target_parent, item_path.name)
        shutil.move(str(item_path), str(target))
        return target

    def delete_work_item(self, path: Path | str) -> None:
        item_path = self._resolve_work_item(path)
        if item_path.is_dir():
            shutil.rmtree(item_path)
            return
        item_path.unlink()

    def append_work_item_event(self, path: Path | str, event: str, created_at: str | None = None) -> Path:
        item_path = self._resolve_work_item(path)
        if not item_path.is_dir():
            raise ValueError("Events can only be appended to task folders")
        timestamp = created_at or datetime.now().replace(microsecond=0).isoformat()
        events_path = item_path / "events.md"
        existing = self._read_optional_text(events_path) or "# Events\n\n"
        separator = "" if existing.endswith("\n\n") else "\n\n"
        events_path.write_text(f"{existing}{separator}## {timestamp}\n\n{event.strip()}\n", encoding="utf-8")
        return events_path

    def context_readiness(self, path: Path | str) -> dict[str, Any]:
        item = self.read_work_item(path)
        missing = []
        if not self._has_non_heading_content(item["task"]):
            missing.append("task.md lacks task content")
        if not self._has_non_heading_content(item["context"]):
            missing.append("context.md lacks non-heading context")
        if not self._has_event_content(item.get("events", "")):
            missing.append("events.md lacks task events")
        return {"ready": not missing, "missing": missing}

    def append_pdca_entry(
        self,
        title: str,
        plan: str,
        do: str,
        check: str,
        act: str,
        ai_output: str,
        created_at: str | None = None,
    ) -> Path:
        timestamp = created_at or datetime.now().replace(microsecond=0).isoformat()
        log_path = self.root / "reviews" / "pdca-input-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = f"""## {timestamp} - {title or "未命名 PDCA 输入"}

### Plan

{plan}

### Do

{do}

### Check

{check}

### Act

{act}

### AI Analysis

{ai_output}

"""
        with log_path.open("a", encoding="utf-8") as file:
            file.write(entry)
        return log_path

    def read_recent_pdca_entries(self, limit: int = 20) -> str:
        log_path = self.root / "reviews" / "pdca-input-log.md"
        if not log_path.exists():
            return ""
        content = log_path.read_text(encoding="utf-8")
        sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
        entries = [section for section in sections if section.strip()]
        if limit > 0:
            entries = entries[-limit:]
        return "".join(entries).strip()

    def save_pdca_review(self, review_text: str, created_at: str | None = None) -> Path:
        timestamp = self._review_timestamp(created_at)
        review_path = self.root / "reviews" / f"{timestamp}-pdca-review.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(review_text, encoding="utf-8")
        return review_path

    def _unique_child_folder(self, parent: Path, name: str) -> Path:
        candidate = parent / name
        suffix = 2
        while candidate.exists():
            candidate = parent / f"{name}-{suffix}"
            suffix += 1
        return candidate

    def _unique_child_path(self, parent: Path, name: str) -> Path:
        candidate = parent / name
        suffix = 2
        stem = Path(name).stem
        suffix_text = Path(name).suffix
        while candidate.exists():
            candidate = parent / f"{stem}-{suffix}{suffix_text}"
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

    def _card_summary(self, markdown: str) -> str:
        metadata = self._frontmatter(markdown)
        explicit_summary = metadata.get("summary", "")
        if explicit_summary:
            return self._short_text(explicit_summary)
        for heading in ("摘要", "简述", "原始问题", "为什么值得做", "下一步动作"):
            summary = self._extract_section_first_line(markdown, heading)
            if summary:
                return self._short_text(summary)
        return self._short_text(self._first_non_empty_line(self._without_frontmatter(markdown)))

    def _without_frontmatter(self, markdown: str) -> str:
        if not markdown.startswith("---\n"):
            return markdown
        end = markdown.find("\n---", 4)
        if end == -1:
            return markdown
        return markdown[end + 4 :].lstrip()

    def _short_text(self, text: str, limit: int = 28) -> str:
        clean = " ".join(text.split())
        if len(clean) <= limit:
            return clean
        return f"{clean[:limit].rstrip()}..."

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

    def _review_timestamp(self, created_at: str | None) -> str:
        if created_at:
            parsed = datetime.fromisoformat(created_at)
        else:
            parsed = datetime.now().replace(microsecond=0)
        return parsed.strftime("%Y-%m-%d-%H%M%S")

    def _frontmatter(self, markdown: str) -> dict[str, Any]:
        if not markdown.startswith("---\n"):
            return {}
        end = markdown.find("\n---", 4)
        if end == -1:
            return {}
        metadata: dict[str, Any] = {}
        lines = markdown[4:end].splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if ":" not in line:
                index += 1
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "tags":
                tags = []
                index += 1
                while index < len(lines) and lines[index].startswith("  "):
                    tag = lines[index].strip().removeprefix("- ").strip()
                    if tag and tag != "[]":
                        tags.append(tag)
                    index += 1
                metadata[key] = tags
                continue
            metadata[key] = value
            index += 1
        return metadata

    def _has_non_heading_content(self, text: str) -> bool:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and stripped not in {"---"} and ":" not in stripped:
                return True
        return False

    def _has_event_content(self, text: str) -> bool:
        return any(line.strip().startswith("- ") or line.strip().startswith("## ") for line in text.splitlines())
