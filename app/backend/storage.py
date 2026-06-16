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
        folder = self.root / capture.status
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{created}-{normalize_slug(capture.title)}.md"
        path = folder / filename
        path.write_text(render_capture_markdown(capture, created), encoding="utf-8")
        return path

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
