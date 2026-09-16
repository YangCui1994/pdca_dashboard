"""Spike domain models: projects, outline nodes, actions, proposals, activity.

Minimal for the Flet spike; the formal model is defined in backlog phase P1.
All dataclasses live in memory; persistence is out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Action statuses
PENDING = "pending"
IN_PROGRESS = "in_progress"
WAITING = "waiting"
DEFERRED = "deferred"
COMPLETED = "completed"
CANCELLED = "cancelled"

# Meaningful activity kinds (counted by heatmap aggregation)
TASK_COMPLETED = "task_completed"
CONTENT_UPDATED = "content_updated"
RESOURCE_ADDED = "resource_added"
DECISION_CONFIRMED = "decision_confirmed"
PROPOSAL_ACCEPTED = "proposal_accepted"
CAPTURE_ADDED = "capture_added"  # 用户主动输入的快速记录是真实工作内容
PLAN_UPDATED = "plan_updated"  # 每日计划的增删改(规划动作,不是执行)
PROJECT_CREATED = "project_created"  # 用户显式创建项目
WORKLOG_UPDATED = "worklog_updated"  # 工作记录正文被用户显式保存

MEANINGFUL_ACTIVITY_KINDS = (
    TASK_COMPLETED,
    CONTENT_UPDATED,
    RESOURCE_ADDED,
    DECISION_CONFIRMED,
    PROPOSAL_ACCEPTED,
    CAPTURE_ADDED,
    PLAN_UPDATED,
    PROJECT_CREATED,
    WORKLOG_UPDATED,
)

# Non-meaningful kinds (never counted, never refresh last_meaningful_update_at)
PAGE_VIEWED = "page_viewed"

# Idea statuses (formal vocabulary arrives in backlog phase P1)
IDEA_PENDING = "pending"
IDEA_KEPT = "kept"
IDEA_ARCHIVED = "archived"
IDEA_STATUSES = (IDEA_PENDING, IDEA_KEPT, IDEA_ARCHIVED)

STALLED_THRESHOLD_DAYS = 15

# Project metadata fields the user may edit directly on the overview page.
# Action/node *status* is deliberately absent: it only moves via AI proposals.
EDITABLE_PROJECT_FIELDS = ("name", "goal", "phase", "current_focus", "next_milestone")


@dataclass
class Action:
    action_id: str
    project_id: str
    title: str
    status: str = PENDING
    last_meaningful_update_at: date = field(default_factory=date.today)


@dataclass
class Resource:
    """A file/link attached to an outline node (name, kind, tags, source)."""

    resource_id: str
    name: str
    kind: str  # 表格/文档/笔记,决定行首图标
    tags: tuple[str, ...] = ()
    source: str = ""


@dataclass
class OutlineNode:
    node_id: str
    project_id: str
    title: str
    kind: str
    note: str = ""
    resources: tuple[Resource, ...] = ()


@dataclass(frozen=True)
class ProgressEntry:
    """One timestamped progress note appended to a project (audit trail)."""

    at: date
    text: str


@dataclass
class Project:
    project_id: str
    name: str
    goal: str
    phase: str
    current_focus: str
    next_milestone: str
    owner: str
    outline: tuple[OutlineNode, ...] = ()
    actions: tuple[Action, ...] = ()
    progress: tuple[ProgressEntry, ...] = ()


@dataclass
class PlanItem:
    item_id: str
    text: str
    done: bool = False
    project_id: str = ""  # 空 = 其他(未归属),后续整理成完整项目


@dataclass
class DayRecord:
    """One day's plan and work log; the editable core of the Today page.

    ``check_note``/``act_note`` close the PDCA loop: Check 是对当天计划的
    复盘判断,Act 是要带去明天的调整动作。The human-readable mirror in
    ``days/<day>.md`` carries them as ``## Check`` / ``## Act`` sections.
    """

    day: date
    plan: list[PlanItem] = field(default_factory=list)
    worklog: str = ""
    check_note: str = ""
    act_note: str = ""


@dataclass
class Idea:
    idea_id: str
    text: str
    status: str = IDEA_PENDING
    created_at: date = field(default_factory=date.today)


@dataclass(frozen=True)
class ActivityEvent:
    occurred_at: date
    project_id: str
    kind: str
    label: str


@dataclass(frozen=True)
class ProposedChange:
    field: str
    target_id: str
    current_value: str
    new_value: str


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    request_kind: str
    project_id: str
    summary: str
    changes: tuple[ProposedChange, ...] = ()
    facts: tuple[str, ...] = ()
    inferences: tuple[str, ...] = ()
    external_knowledge: tuple[str, ...] = ()
