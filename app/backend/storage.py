from __future__ import annotations

from pathlib import Path

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

    def _unique_child_folder(self, parent: Path, name: str) -> Path:
        candidate = parent / name
        suffix = 2
        while candidate.exists():
            candidate = parent / f"{name}-{suffix}"
            suffix += 1
        return candidate
