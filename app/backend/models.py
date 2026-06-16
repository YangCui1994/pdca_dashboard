from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal


TaskStatus = Literal["idea", "todo", "doing", "waiting", "done"]
CaptureKind = Literal["idea", "task", "project-note", "data-issue", "communication-draft"]
VaultStatus = Literal["inbox", "active", "waiting", "done", "archive"]

TASK_STATUSES = {"idea", "todo", "doing", "waiting", "done"}
CAPTURE_KINDS = {"idea", "task", "project-note", "data-issue", "communication-draft"}
VAULT_STATUSES = {"inbox", "active", "waiting", "done", "archive"}


def normalize_slug(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", cleaned).strip("-")
    return collapsed or "untitled"


@dataclass
class Task:
    title: str
    status: TaskStatus = "idea"
    project: str = ""
    value: str = ""
    next_action: str = ""
    expected_artifact: str = ""
    main_risk: str = ""
    minimum_mvp: str = ""

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Unsupported task status: {self.status}")


@dataclass
class Capture:
    raw_text: str
    title: str = "未命名输入"
    kind: CaptureKind = "idea"
    status: VaultStatus = "inbox"
    ai_output: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind not in CAPTURE_KINDS:
            raise ValueError(f"Unsupported capture kind: {self.kind}")
        if self.status not in VAULT_STATUSES:
            raise ValueError(f"Unsupported vault status: {self.status}")


@dataclass
class Project:
    title: str
    created: str
    status: VaultStatus = "active"
    project_type: str = ""
    business_object: str = ""
    phase: str = "探索"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VAULT_STATUSES:
            raise ValueError(f"Unsupported project status: {self.status}")

    def folder_name(self) -> str:
        return f"{self.created}-{normalize_slug(self.title)}"
