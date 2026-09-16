"""In-memory workspace service: the only writer of formal workspace state.

Every mutation goes through an explicit, user-confirmed action
(accept_proposal). Views and runtime output never write directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from workbench.domain.fixtures import demo_day_seed
from workbench.domain.models import (
    CAPTURE_ADDED,
    CANCELLED,
    COMPLETED,
    CONTENT_UPDATED,
    DEFERRED,
    EDITABLE_PROJECT_FIELDS,
    IDEA_ARCHIVED,
    IDEA_KEPT,
    IDEA_PENDING,
    IDEA_STATUSES,
    IN_PROGRESS,
    MEANINGFUL_ACTIVITY_KINDS,
    OutlineNode,
    PENDING,
    PLAN_UPDATED,
    PROJECT_CREATED,
    RESOURCE_ADDED,
    STALLED_THRESHOLD_DAYS,
    TASK_COMPLETED,
    WAITING,
    WORKLOG_UPDATED,
    ActivityEvent,
    DayRecord,
    Idea,
    PlanItem,
    Project,
    Proposal,
    ProposedChange,
    ProgressEntry,
    Resource,
)
from workbench.domain.models import (
    PROPOSAL_ACCEPTED as _PROPOSAL_ACCEPTED,
)


@dataclass(frozen=True)
class ApplyResult:
    applied: bool
    applied_changes: tuple[str, ...] = ()
    skipped_changes: tuple[str, ...] = ()


class WorkspaceService:
    """Owns formal state; proposals apply only after explicit acceptance.

    Without ``storage`` the service is the original in-memory spike (demo
    fixtures, nothing survives a restart). With ``storage`` every explicit
    write persists the affected aggregate and appends its activity event
    to the vault (P2′).
    """

    def __init__(self, projects=None, activity=None, ideas=None, days=None, storage=None):
        self._storage = storage
        self._projects: dict[str, Project] = {
            project.project_id: project for project in (projects or [])
        }
        self._activity: list[ActivityEvent] = list(activity or [])
        self._ideas: list[Idea] = list(ideas) if ideas else []
        self._next_idea_seq = len(self._ideas) + 1
        if days is None and storage is None:
            seed = demo_day_seed()
            self._days: dict[date, DayRecord] = {seed.day: seed}
        else:
            self._days = {day: record for day, record in (days or {}).items()}
        self._next_plan_seq = {
            record.day: len(record.plan) + 1 for record in self._days.values()
        }
        self._next_res_seq: dict[str, int] = {
            node.node_id: len(node.resources) + 1
            for project in self._projects.values()
            for node in project.outline
        }

    @classmethod
    def open(cls, storage) -> "WorkspaceService":
        """Load the full workspace from a vault (the only disk-reading path)."""

        loaded = storage.load()
        return cls(
            loaded.projects,
            loaded.activity,
            ideas=loaded.ideas,
            days=loaded.days,
            storage=storage,
        )

    # --- persistence helpers (no-ops without storage) -----------------------

    def _record(self, event: ActivityEvent) -> None:
        self._activity.append(event)
        if self._storage is not None:
            self._storage.append_activity(event)

    def _persist_day(self, day: date) -> None:
        if self._storage is not None:
            self._storage.save_day(self._days[day])

    def _persist_project(self, project_id: str) -> None:
        if self._storage is not None:
            project = self._projects.get(project_id)
            if project is not None:
                self._storage.save_project(project)

    def _persist_node(self, project_id: str, node) -> None:
        if self._storage is not None:
            self._storage.save_node(project_id, node)

    def _persist_ideas(self) -> None:
        if self._storage is not None:
            self._storage.save_ideas(self._ideas, self._next_idea_seq)

    def set_idea_status(self, idea_id: str, status: str) -> bool:
        """Idea 状态流转(待整理/已保留/已归档);原文永不改写(P2′ 契约)。"""

        if status not in IDEA_STATUSES:
            raise ValueError(f"unknown idea status: {status}")
        for idea in self._ideas:
            if idea.idea_id != idea_id:
                continue
            if idea.status == status:
                return False
            old, idea.status = idea.status, status
            self._record(
                ActivityEvent(
                    date.today(),
                    "",
                    CONTENT_UPDATED,
                    f"想法状态:{old}→{status}:{idea.text[:30]}",
                )
            )
            self._persist_ideas()
            return True
        return False

    # --- reads -----------------------------------------------------------

    def projects(self) -> list[Project]:
        return list(self._projects.values())

    def project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def activity(self) -> list[ActivityEvent]:
        return list(self._activity)

    def ideas(self) -> list[Idea]:
        return list(self._ideas)

    def day_record(self, day: date | None = None) -> DayRecord:
        """Reading an unknown day yields a transient empty record (no write)."""

        day = day or date.today()
        record = self._days.get(day)
        if record is None:
            return DayRecord(day=day)
        return record

    def stalled_actions(
        self, project_id: str | None = None, today: date | None = None
    ) -> list:
        """In-progress actions with no meaningful update for 15+ days.

        Read-only by definition: waiting/deferred/completed/cancelled are
        excluded, and calling this never refreshes last_meaningful_update_at.
        """

        today = today or date.today()
        stalled = []
        for project in self._projects.values():
            if project_id is not None and project.project_id != project_id:
                continue
            for action in project.actions:
                idle_days = (today - action.last_meaningful_update_at).days
                if action.status == IN_PROGRESS and idle_days >= STALLED_THRESHOLD_DAYS:
                    stalled.append(action)
        return stalled

    def heatmap_counts(
        self, project_id: str | None = None
    ) -> dict[date, int]:
        """Meaningful-activity counts per day; browsing never counts."""

        counts: dict[date, int] = {}
        for event in self._activity:
            if event.kind not in MEANINGFUL_ACTIVITY_KINDS:
                continue
            if project_id is not None and event.project_id != project_id:
                continue
            counts[event.occurred_at] = counts.get(event.occurred_at, 0) + 1
        return counts

    def snapshot(self) -> str:
        """Stable serialized form used to prove state boundaries."""

        payload = {
            "projects": [
                {
                    "project_id": p.project_id,
                    "name": p.name,
                    "goal": p.goal,
                    "phase": p.phase,
                    "current_focus": p.current_focus,
                    "next_milestone": p.next_milestone,
                    "owner": p.owner,
                    "outline": [
                        {
                            "node_id": n.node_id,
                            "title": n.title,
                            "kind": n.kind,
                            "note": n.note,
                            "resources": [
                                {
                                    "resource_id": r.resource_id,
                                    "name": r.name,
                                    "kind": r.kind,
                                    "tags": list(r.tags),
                                    "source": r.source,
                                }
                                for r in n.resources
                            ],
                        }
                        for n in p.outline
                    ],
                    "actions": [
                        {
                            "action_id": a.action_id,
                            "title": a.title,
                            "status": a.status,
                            "last_meaningful_update_at": (
                                a.last_meaningful_update_at.isoformat()
                            ),
                        }
                        for a in p.actions
                    ],
                    "progress": [
                        {"at": e.at.isoformat(), "text": e.text}
                        for e in p.progress
                    ],
                }
                for p in self._projects.values()
            ],
            "activity": [
                {
                    "occurred_at": e.occurred_at.isoformat(),
                    "project_id": e.project_id,
                    "kind": e.kind,
                    "label": e.label,
                }
                for e in self._activity
            ],
            "ideas": [
                {
                    "idea_id": i.idea_id,
                    "text": i.text,
                    "status": i.status,
                    "created_at": i.created_at.isoformat(),
                }
                for i in self._ideas
            ],
            "days": [
                {
                    "day": record.day.isoformat(),
                    "plan": [
                        {
                            "item_id": item.item_id,
                            "text": item.text,
                            "done": item.done,
                            "project_id": item.project_id,
                        }
                        for item in record.plan
                    ],
                    "worklog": record.worklog,
                    "check_note": record.check_note,
                    "act_note": record.act_note,
                }
                for record in self._days.values()
            ],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    # --- explicit writes ---------------------------------------------------

    def quick_capture(self, text: str) -> Idea:
        """User-typed capture: the one write that bypasses proposals.

        The user typed it themselves, so it is an explicit action — but it
        still lands here (not in a UI callback) and emits a meaningful
        capture_added activity event.
        """

        cleaned = text.strip()
        if not cleaned:
            raise ValueError("quick capture text must not be blank")
        idea = Idea(
            idea_id=f"idea-{self._next_idea_seq:03d}",
            text=cleaned,
            status=IDEA_PENDING,
            created_at=date.today(),
        )
        self._next_idea_seq += 1
        self._ideas.append(idea)
        self._record(
            ActivityEvent(
                date.today(),
                "",  # workspace-level, not tied to one project
                CAPTURE_ADDED,
                cleaned[:50],
            )
        )
        self._persist_ideas()
        return idea

    # --- day plan / worklog (explicit user edits, proposal not required) ---

    def _stored_day(self, day: date) -> DayRecord:
        record = self._days.get(day)
        if record is None:
            record = DayRecord(day=day)
            self._days[day] = record
            self._next_plan_seq[day] = 1
        return record

    def _plan_item(self, day: date, item_id: str) -> PlanItem | None:
        for item in self._stored_day(day).plan:
            if item.item_id == item_id:
                return item
        return None

    def add_plan_item(self, day: date | None, text: str, project_id: str = "") -> PlanItem:
        """Append one plan item; blank text is rejected like quick capture.

        project_id 为空表示「其他」;未知项目按空处理,后续整理。
        """

        day = day or date.today()
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("plan item text must not be blank")
        if project_id not in self._projects:
            project_id = ""
        record = self._stored_day(day)
        item = PlanItem(
            item_id=f"plan-{self._next_plan_seq.get(day, len(record.plan) + 1):03d}",
            text=cleaned,
            done=False,
            project_id=project_id,
        )
        self._next_plan_seq[day] = self._next_plan_seq.get(day, 1) + 1
        record.plan.append(item)
        self._record(
            ActivityEvent(day, "", PLAN_UPDATED, f"新增计划:{cleaned[:50]}")
        )
        self._persist_day(day)
        return item

    def rename_plan_item(self, day: date | None, item_id: str, text: str) -> bool:
        day = day or date.today()
        item = self._plan_item(day, item_id)
        cleaned = text.strip()
        if item is None or not cleaned or cleaned == item.text:
            return False
        item.text = cleaned
        self._record(
            ActivityEvent(day, "", PLAN_UPDATED, f"修改计划:{cleaned[:50]}")
        )
        self._persist_day(day)
        return True

    def set_plan_item_project(self, day: date | None, item_id: str, project_id: str) -> bool:
        """Move a plan item to another project (or 其他)."""

        day = day or date.today()
        if project_id not in self._projects:
            project_id = ""
        item = self._plan_item(day, item_id)
        if item is None or item.project_id == project_id:
            return False
        item.project_id = project_id
        label = project_id or "其他"
        self._record(
            ActivityEvent(day, "", PLAN_UPDATED, f"计划归属→{label}:{item.text[:40]}")
        )
        self._persist_day(day)
        return True

    def toggle_plan_item(self, day: date | None, item_id: str) -> bool:
        """Flip done; only finishing counts as task completion."""

        day = day or date.today()
        item = self._plan_item(day, item_id)
        if item is None:
            raise KeyError(item_id)
        item.done = not item.done
        if item.done:
            kind, label = TASK_COMPLETED, f"完成计划:{item.text[:50]}"
        else:
            kind, label = CONTENT_UPDATED, f"取消完成:{item.text[:50]}"
        self._record(ActivityEvent(day, "", kind, label))
        self._persist_day(day)
        return item.done

    def remove_plan_item(self, day: date | None, item_id: str) -> bool:
        day = day or date.today()
        record = self._stored_day(day)
        remaining = [item for item in record.plan if item.item_id != item_id]
        if len(remaining) == len(record.plan):
            return False
        record.plan = remaining
        self._record(
            ActivityEvent(day, "", PLAN_UPDATED, f"删除计划:{item_id}")
        )
        self._persist_day(day)
        return True

    def set_worklog(self, day: date | None, text: str) -> bool:
        """Replace the day's worklog; identical text writes nothing."""

        day = day or date.today()
        record = self._stored_day(day)
        if text == record.worklog:
            return False
        record.worklog = text
        self._record(
            ActivityEvent(
                day, "", WORKLOG_UPDATED, f"保存工作记录:{len(text)} 字"
            )
        )
        self._persist_day(day)
        return True

    def set_day_check(self, day: date | None, text: str) -> bool:
        """Record the day's PDCA Check note; identical text writes nothing."""

        day = day or date.today()
        record = self._stored_day(day)
        if text == record.check_note:
            return False
        record.check_note = text
        self._record(
            ActivityEvent(day, "", CONTENT_UPDATED, f"保存 Check:{len(text)} 字")
        )
        self._persist_day(day)
        return True

    def set_day_act(self, day: date | None, text: str) -> bool:
        """Record the day's PDCA Act note; identical text writes nothing."""

        day = day or date.today()
        record = self._stored_day(day)
        if text == record.act_note:
            return False
        record.act_note = text
        self._record(
            ActivityEvent(day, "", CONTENT_UPDATED, f"保存 Act:{len(text)} 字")
        )
        self._persist_day(day)
        return True

    # --- direct action status / project progress (no AI proposal required) ---

    ACTION_STATUSES = (PENDING, IN_PROGRESS, WAITING, DEFERRED, COMPLETED, CANCELLED)

    def set_action_status(
        self, project_id: str, action_id: str, status: str
    ) -> bool:
        """Move an action's status directly; the manual counterpart of
        accepting an ``action.status`` proposal. Counts as a meaningful
        update, exactly like the proposal path does."""

        if status not in self.ACTION_STATUSES:
            raise ValueError(f"unknown action status: {status}")
        project = self._projects.get(project_id)
        if project is None:
            return False
        for action in project.actions:
            if action.action_id != action_id:
                continue
            if action.status == status:
                return False
            old = action.status
            action.status = status
            action.last_meaningful_update_at = date.today()
            kind = TASK_COMPLETED if status == COMPLETED else CONTENT_UPDATED
            self._record(
                ActivityEvent(
                    date.today(),
                    project_id,
                    kind,
                    f"行动状态:{old}→{status}:{action.title[:40]}",
                )
            )
            self._persist_project(project_id)
            return True
        return False

    def append_project_progress(
        self, project_id: str, text: str
    ) -> ProgressEntry | None:
        """Append a timestamped progress note to a project's audit trail."""

        project = self._projects.get(project_id)
        cleaned = text.strip()
        if project is None or not cleaned:
            return None
        entry = ProgressEntry(at=date.today(), text=cleaned)
        project.progress = tuple(project.progress) + (entry,)
        self._record(
            ActivityEvent(
                date.today(), project_id, CONTENT_UPDATED, f"项目进度:{cleaned[:50]}"
            )
        )
        self._persist_project(project_id)
        return entry

    def remove_project_progress(
        self, project_id: str, entry: ProgressEntry
    ) -> bool:
        """Undo one appended progress note (auto-route rollback path)."""

        project = self._projects.get(project_id)
        if project is None:
            return False
        remaining = tuple(
            e
            for e in project.progress
            if not (e.at == entry.at and e.text == entry.text)
        )
        if len(remaining) == len(project.progress):
            return False
        project.progress = remaining
        self._record(
            ActivityEvent(
                date.today(),
                project_id,
                CONTENT_UPDATED,
                f"撤销项目进度:{entry.text[:50]}",
            )
        )
        self._persist_project(project_id)
        return True

    # --- project / outline metadata edits ----------------------------------

    def create_project(
        self,
        name: str,
        goal: str = "",
        current_focus: str = "",
        owner: str = "",
        phase: str = "启动期",
    ) -> Project:
        """Create a project with one starter outline node; blank name rejected."""

        cleaned = name.strip()
        if not cleaned:
            raise ValueError("project name must not be blank")
        seq = 1
        for project_id in self._projects:
            if project_id.startswith("proj-") and project_id[5:].isdigit():
                seq = max(seq, int(project_id[5:]) + 1)
        project = Project(
            project_id=f"proj-{seq:03d}",
            name=cleaned,
            goal=goal.strip(),
            phase=phase,
            current_focus=current_focus.strip(),
            next_milestone="",
            owner=owner.strip() or "我",
            outline=(
                OutlineNode(
                    node_id="node-goal",
                    project_id=f"proj-{seq:03d}",
                    title="目标与边界",
                    kind="goal",
                    note="",
                ),
            ),
        )
        self._projects[project.project_id] = project
        self._next_res_seq[project.outline[0].node_id] = 1
        self._record(
            ActivityEvent(
                date.today(),
                project.project_id,
                PROJECT_CREATED,
                f"创建项目:{cleaned[:50]}",
            )
        )
        self._persist_project(project.project_id)
        if self._storage is not None:
            self._storage.save_node(project.project_id, project.outline[0])
        return project

    def set_project_field(self, project_id: str, field: str, value: str) -> bool:
        """Edit whitelisted metadata only; status-like fields are refused."""

        project = self._projects.get(project_id)
        if project is None or field not in EDITABLE_PROJECT_FIELDS:
            return False
        cleaned = value.strip()
        if not cleaned or cleaned == getattr(project, field):
            return False
        setattr(project, field, cleaned)
        self._record(
            ActivityEvent(
                date.today(),
                project_id,
                CONTENT_UPDATED,
                f"更新{field}:{cleaned[:50]}",
            )
        )
        self._persist_project(project_id)
        return True

    def rename_action(self, project_id: str, action_id: str, title: str) -> bool:
        """Rename an action title. Deliberately does NOT refresh
        last_meaningful_update_at: renaming metadata is not progress."""

        project = self._projects.get(project_id)
        cleaned = title.strip()
        if project is None or not cleaned:
            return False
        for action in project.actions:
            if action.action_id == action_id:
                if cleaned == action.title:
                    return False
                action.title = cleaned
                self._record(
                    ActivityEvent(
                        date.today(),
                        project_id,
                        CONTENT_UPDATED,
                        f"重命名行动:{cleaned[:50]}",
                    )
                )
                self._persist_project(project_id)
                return True
        return False

    def rename_node(
        self,
        project_id: str,
        node_id: str,
        title: str | None = None,
        note: str | None = None,
    ) -> bool:
        """Edit a node's title and/or note in one explicit action."""

        project = self._projects.get(project_id)
        if project is None:
            return False
        node = next(
            (n for n in project.outline if n.node_id == node_id), None
        )
        if node is None:
            return False
        changed = False
        if title is not None:
            cleaned = title.strip()
            if cleaned and cleaned != node.title:
                node.title = cleaned
                changed = True
        if note is not None and note != node.note:
            node.note = note
            changed = True
        if changed:
            self._record(
                ActivityEvent(
                    date.today(),
                    project_id,
                    CONTENT_UPDATED,
                    f"编辑节点:{node.title[:50]}",
                )
            )
            self._persist_node(project_id, node)
        return changed

    # --- node resources ------------------------------------------------------

    def _node(self, project_id: str, node_id: str):
        project = self._projects.get(project_id)
        if project is None:
            return None
        return next((n for n in project.outline if n.node_id == node_id), None)

    def add_resource(
        self,
        project_id: str,
        node_id: str,
        name: str,
        kind: str = "笔记",
        source: str = "",
        tags: tuple[str, ...] = (),
    ) -> Resource:
        """Attach a file/link card to a node; blank name is rejected."""

        node = self._node(project_id, node_id)
        if node is None:
            raise KeyError(node_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("resource name must not be blank")
        seq = self._next_res_seq.get(node_id, 1)
        self._next_res_seq[node_id] = seq + 1
        resource = Resource(
            resource_id=f"res-{seq:03d}",
            name=cleaned,
            kind=kind,
            tags=tuple(tags),
            source=source.strip(),
        )
        node.resources = tuple(node.resources) + (resource,)
        self._record(
            ActivityEvent(
                date.today(),
                project_id,
                RESOURCE_ADDED,
                f"加入资源:{cleaned[:50]}",
            )
        )
        self._persist_node(project_id, node)
        return resource

    def rename_resource(
        self,
        project_id: str,
        node_id: str,
        resource_id: str,
        name: str | None = None,
        source: str | None = None,
    ) -> bool:
        node = self._node(project_id, node_id)
        if node is None:
            return False
        for resource in node.resources:
            if resource.resource_id != resource_id:
                continue
            changed = False
            if name is not None:
                cleaned = name.strip()
                if cleaned and cleaned != resource.name:
                    resource.name = cleaned
                    changed = True
            if source is not None and source != resource.source:
                resource.source = source
                changed = True
            if changed:
                self._record(
                    ActivityEvent(
                        date.today(),
                        project_id,
                        CONTENT_UPDATED,
                        f"编辑资源:{resource.name[:50]}",
                    )
                )
                self._persist_node(project_id, node)
            return changed
        return False

    def remove_resource(
        self, project_id: str, node_id: str, resource_id: str
    ) -> bool:
        node = self._node(project_id, node_id)
        if node is None:
            return False
        remaining = [
            r for r in node.resources if r.resource_id != resource_id
        ]
        if len(remaining) == len(node.resources):
            return False
        node.resources = tuple(remaining)
        self._record(
            ActivityEvent(
                date.today(),
                project_id,
                CONTENT_UPDATED,
                f"移除资源:{resource_id}",
            )
        )
        self._persist_node(project_id, node)
        return True

    def accept_proposal(self, proposal: Proposal) -> ApplyResult:
        """Apply only the proposal's declared changes; nothing else moves."""

        applied: list[str] = []
        skipped: list[str] = []
        touched_projects: set[str] = set()
        for change in proposal.changes:
            outcome = self._apply_change(change)
            (applied if outcome else skipped).append(
                f"{change.target_id}:{change.field}"
            )
            if outcome:
                touched_projects.add(change.target_id.partition(":")[0])
        if applied:
            self._record(
                ActivityEvent(
                    date.today(),
                    proposal.project_id,
                    _PROPOSAL_ACCEPTED,
                    f"接受 {proposal.proposal_id}:{proposal.summary}",
                )
            )
            for project_id in sorted(touched_projects):
                self._persist_project(project_id)
        return ApplyResult(
            applied=bool(applied),
            applied_changes=tuple(applied),
            skipped_changes=tuple(skipped),
        )

    def reject_proposal(self, proposal: Proposal) -> None:
        """Rejection intentionally changes nothing in formal state."""

        return None

    # --- internals ---------------------------------------------------------

    def _apply_change(self, change: ProposedChange) -> bool:
        if change.field != "action.status":
            return False
        project_id, _, action_id = change.target_id.partition(":")
        project = self._projects.get(project_id)
        if project is None:
            return False
        for action in project.actions:
            if action.action_id == action_id:
                action.status = change.new_value
                action.last_meaningful_update_at = date.today()
                return True
        return False
