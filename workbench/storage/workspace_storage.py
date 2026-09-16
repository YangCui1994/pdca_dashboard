"""Markdown/JSON twin-file persistence for the workbench (P2′).

Layout under the vault root (usually data-issue-vault/v2/):

    workspace.json                      revision manifest (per data file)
    ideas.json                          ideas + capture originals (append-only content)
    activity.jsonl                      append-only activity log
    days/<YYYY-MM-DD>.json              day plan items (structured)
    days/<YYYY-MM-DD>.md                day worklog (narrative)
    projects/<pid>/project.json         project meta + actions
    projects/<pid>/nodes/<nid>.json     node title/kind/resources
    projects/<pid>/nodes/<nid>.md       node note (narrative)

Conflict rule: every guarded file's revision + content hash lives in
workspace.json. Before overwriting a guarded file we re-read the manifest
and re-hash the file on disk; any mismatch with what we last knew raises
StorageConflict — external hand-edits are never silently overwritten.
activity.jsonl is append-only and deliberately not guarded.

Path safety: identifiers containing separators, "..", absolute paths or
drive letters are rejected before they ever reach the filesystem.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from workbench.domain.models import (
    Action,
    ActivityEvent,
    DayRecord,
    Idea,
    OutlineNode,
    PlanItem,
    ProgressEntry,
    Project,
    Resource,
)

_MANIFEST = "workspace.json"
_IDEA_FILE = "ideas.json"
_ACTIVITY_FILE = "activity.jsonl"

_CHECK_HEADING = "## Check"
_ACT_HEADING = "## Act"


def compose_day_md(record: DayRecord) -> str:
    """Human-readable day file: worklog narrative + optional PDCA sections."""

    parts = [record.worklog]
    if record.check_note.strip():
        parts.append(f"{_CHECK_HEADING}\n\n{record.check_note.strip()}")
    if record.act_note.strip():
        parts.append(f"{_ACT_HEADING}\n\n{record.act_note.strip()}")
    return "\n\n".join(part for part in parts if part.strip())


def parse_day_md(text: str) -> tuple[str, str, str]:
    """Split a day md back into (worklog, check_note, act_note).

    The section headings are recognized only as standalone lines. A file
    without any section heading (legacy worklog-only days) returns the raw
    text unchanged so the no-section roundtrip stays byte-exact. With
    sections present, trailing newlines around each part are normalized.
    A worklog that itself contains a bare ``## Check``/``## Act`` line
    would be reinterpreted — keep such headings inside list items.
    """

    if _CHECK_HEADING not in text.splitlines() and _ACT_HEADING not in text.splitlines():
        return text, "", ""
    sections: dict[str, list[str]] = {"worklog": [], "check": [], "act": []}
    current = "worklog"
    for line in text.splitlines():
        if line.strip() == _CHECK_HEADING:
            current = "check"
            continue
        if line.strip() == _ACT_HEADING:
            current = "act"
            continue
        sections[current].append(line)
    return (
        "\n".join(sections["worklog"]).strip("\n"),
        "\n".join(sections["check"]).strip("\n"),
        "\n".join(sections["act"]).strip("\n"),
    )

_SAFE_ID = re.compile(r"^[^/\\:*?\"<>|\x00]+$")


class StorageError(Exception):
    """Malformed or unreadable vault content (never silently dropped)."""


class StorageConflict(Exception):
    """File changed externally since we last read it; refuse to overwrite."""


@dataclass
class LoadedWorkspace:
    projects: list[Project]
    activity: list[ActivityEvent]
    ideas: list[Idea]
    days: dict[date, DayRecord]


def _safe_segment(segment: str, what: str) -> str:
    cleaned = segment.strip()
    if (
        not cleaned
        or cleaned in (".", "..")
        or "/" in cleaned
        or "\\" in cleaned
        or ":" in cleaned
        or not _SAFE_ID.match(cleaned)
    ):
        raise ValueError(f"unsafe {what}: {segment!r}")
    return cleaned


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def _hash_bytes(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class WorkspaceStorage:
    """The only module that maps domain objects to vault files."""

    def __init__(self, root: Path | str):
        self._root = Path(root)

    # --- manifest (revision + content hash per guarded file) ---------------

    def _read_manifest(self) -> dict:
        path = self._root / _MANIFEST
        if not path.exists():
            return {"files": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageError(f"manifest unreadable: {path}") from exc

    def _write_manifest(self, manifest: dict) -> None:
        _atomic_write(
            self._root / _MANIFEST,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        )

    def _register(self, rel: Path, content: str, manifest: dict) -> None:
        manifest["files"][rel.as_posix()] = {
            "revision": manifest["files"].get(rel.as_posix(), {}).get("revision", 0) + 1,
            "sha256": _hash_bytes(content),
        }

    def _guard(self, rel: Path, manifest: dict) -> None:
        """Refuse to overwrite a file we do not recognize anymore."""

        entry = manifest["files"].get(rel.as_posix())
        if entry is None:
            return
        disk = self._root / rel
        if not disk.exists():
            raise StorageConflict(f"外部删除或移动: {rel}")
        current = _hash_bytes(disk.read_text(encoding="utf-8"))
        if current != entry["sha256"]:
            raise StorageConflict(
                f"文件已被外部修改,拒绝覆盖: {rel}(先备份你的修改再重试)"
            )

    # --- JSON helpers --------------------------------------------------------

    def _write_guarded(self, rel: Path, content: str) -> None:
        self._write_guarded_batch([(rel, content)])

    def _write_guarded_batch(self, items: list[tuple[Path, str]]) -> None:
        """Guard every file first, then write — a conflict aborts the whole
        batch before any sibling file is touched."""

        manifest = self._read_manifest()
        for rel, _content in items:
            self._guard(rel, manifest)
        for rel, content in items:
            _atomic_write(self._root / rel, content)
            self._register(rel, content, manifest)
        self._write_manifest(manifest)

    @staticmethod
    def _dumps(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

    # --- save ----------------------------------------------------------------

    def save_project(self, project: Project) -> None:
        pid = _safe_segment(project.project_id, "project_id")
        payload = {
            "project_id": project.project_id,
            "name": project.name,
            "goal": project.goal,
            "phase": project.phase,
            "current_focus": project.current_focus,
            "next_milestone": project.next_milestone,
            "owner": project.owner,
            "outline_order": [n.node_id for n in project.outline],
            "progress": [
                {"at": e.at.isoformat(), "text": e.text}
                for e in project.progress
            ],
            "actions": [
                {
                    "action_id": a.action_id,
                    "title": a.title,
                    "status": a.status,
                    "last_meaningful_update_at": a.last_meaningful_update_at.isoformat(),
                }
                for a in project.actions
            ],
        }
        self._write_guarded(Path("projects") / pid / "project.json", self._dumps(payload))

    def save_node(self, project_id: str, node: OutlineNode) -> None:
        pid = _safe_segment(project_id, "project_id")
        nid = _safe_segment(node.node_id, "node_id")
        payload = {
            "node_id": node.node_id,
            "project_id": node.project_id,
            "title": node.title,
            "kind": node.kind,
            "resources": [
                {
                    "resource_id": r.resource_id,
                    "name": r.name,
                    "kind": r.kind,
                    "tags": list(r.tags),
                    "source": r.source,
                }
                for r in node.resources
            ],
        }
        base = Path("projects") / pid / "nodes" / nid
        self._write_guarded_batch(
            [
                (base.with_suffix(".json"), self._dumps(payload)),
                (base.with_suffix(".md"), node.note),
            ]
        )

    def save_day(self, record: DayRecord) -> None:
        key = _safe_segment(record.day.isoformat(), "day")
        payload = {
            "day": record.day.isoformat(),
            "plan": [
                {
                    "item_id": i.item_id,
                    "text": i.text,
                    "done": i.done,
                    "project_id": i.project_id,
                }
                for i in record.plan
            ],
            "check_note": record.check_note,
            "act_note": record.act_note,
        }
        base = Path("days") / key
        self._write_guarded_batch(
            [
                (base.with_suffix(".json"), self._dumps(payload)),
                (base.with_suffix(".md"), compose_day_md(record)),
            ]
        )

    def save_ideas(self, ideas: list[Idea], next_seq: int) -> None:
        payload = {
            "next_idea_seq": next_seq,
            "ideas": [
                {
                    "idea_id": i.idea_id,
                    "text": i.text,
                    "status": i.status,
                    "created_at": i.created_at.isoformat(),
                }
                for i in ideas
            ],
        }
        self._write_guarded(Path(_IDEA_FILE), self._dumps(payload))

    def append_activity(self, event: ActivityEvent) -> None:
        line = json.dumps(
            {
                "occurred_at": event.occurred_at.isoformat(),
                "project_id": event.project_id,
                "kind": event.kind,
                "label": event.label,
            },
            ensure_ascii=False,
        )
        path = self._root / _ACTIVITY_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # --- load ------------------------------------------------------------------

    def _read_json(self, rel: Path):
        path = self._root / rel
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageError(f"vault file unreadable: {rel}") from exc

    def _load_projects(self) -> list[Project]:
        projects_dir = self._root / "projects"
        if not projects_dir.exists():
            return []
        projects = []
        for pdir in sorted(projects_dir.iterdir()):
            if not pdir.is_dir():
                continue
            meta = self._read_json(Path("projects") / pdir.name / "project.json")
            if meta is None:
                continue
            nodes_dir = pdir / "nodes"
            nodes = []
            if nodes_dir.exists():
                for jfile in sorted(nodes_dir.glob("*.json")):
                    npayload = self._read_json(jfile.relative_to(self._root))
                    if npayload is None:
                        continue
                    md = jfile.with_suffix(".md")
                    note = md.read_text(encoding="utf-8") if md.exists() else ""
                    nodes.append(
                        OutlineNode(
                            node_id=npayload["node_id"],
                            project_id=npayload["project_id"],
                            title=npayload["title"],
                            kind=npayload["kind"],
                            note=note,
                            resources=tuple(
                                Resource(
                                    resource_id=r["resource_id"],
                                    name=r["name"],
                                    kind=r["kind"],
                                    tags=tuple(r.get("tags", ())),
                                    source=r.get("source", ""),
                                )
                                for r in npayload.get("resources", ())
                            ),
                        )
                    )
            # 大纲顺序是领域事实,存于 project.json;文件名排序只是读取手段。
            order = {nid: idx for idx, nid in enumerate(meta.get("outline_order", []))}
            nodes.sort(key=lambda n: order.get(n.node_id, len(order)))
            projects.append(
                Project(
                    project_id=meta["project_id"],
                    name=meta["name"],
                    goal=meta["goal"],
                    phase=meta["phase"],
                    current_focus=meta["current_focus"],
                    next_milestone=meta["next_milestone"],
                    owner=meta["owner"],
                    outline=tuple(nodes),
                    progress=tuple(
                        ProgressEntry(
                            at=date.fromisoformat(e["at"]),
                            text=e["text"],
                        )
                        for e in meta.get("progress", ())
                    ),
                    actions=tuple(
                        Action(
                            action_id=a["action_id"],
                            project_id=meta["project_id"],
                            title=a["title"],
                            status=a["status"],
                            last_meaningful_update_at=date.fromisoformat(
                                a["last_meaningful_update_at"]
                            ),
                        )
                        for a in meta.get("actions", ())
                    ),
                )
            )
        return projects

    def _load_days(self) -> dict[date, DayRecord]:
        days_dir = self._root / "days"
        if not days_dir.exists():
            return {}
        days = {}
        for jfile in sorted(days_dir.glob("*.json")):
            payload = self._read_json(jfile.relative_to(self._root))
            if payload is None:
                continue
            day = date.fromisoformat(payload["day"])
            md = jfile.with_suffix(".md")
            if md.exists():
                worklog, check, act = parse_day_md(md.read_text(encoding="utf-8"))
            else:
                worklog = ""
                check = payload.get("check_note", "")
                act = payload.get("act_note", "")
            days[day] = DayRecord(
                day=day,
                plan=[
                    PlanItem(
                        item_id=i["item_id"],
                        text=i["text"],
                        done=bool(i["done"]),
                        project_id=i.get("project_id", ""),
                    )
                    for i in payload.get("plan", [])
                ],
                worklog=worklog,
                check_note=check,
                act_note=act,
            )
        return days

    def _load_activity(self) -> list[ActivityEvent]:
        path = self._root / _ACTIVITY_FILE
        if not path.exists():
            return []
        events = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise StorageError(f"activity line {lineno} unreadable") from exc
            events.append(
                ActivityEvent(
                    occurred_at=date.fromisoformat(payload["occurred_at"]),
                    project_id=payload["project_id"],
                    kind=payload["kind"],
                    label=payload["label"],
                )
            )
        return events

    def load(self) -> LoadedWorkspace:
        """Rebuild domain state; missing/empty vault yields an empty workspace."""

        ideas_payload = self._read_json(Path(_IDEA_FILE)) or {"ideas": [], "next_idea_seq": 1}
        ideas = [
            Idea(
                idea_id=i["idea_id"],
                text=i["text"],
                status=i.get("status", "pending"),
                created_at=date.fromisoformat(i["created_at"]),
            )
            for i in ideas_payload.get("ideas", [])
        ]
        return LoadedWorkspace(
            projects=self._load_projects(),
            activity=self._load_activity(),
            ideas=ideas,
            days=self._load_days(),
        )
