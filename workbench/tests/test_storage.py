"""Storage layer tests: roundtrip, conflict guard, path safety.

All tests run against temp directories — the real data-issue-vault is
never touched (AGENTS.md data boundary).
"""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from workbench.domain.fixtures import demo_day_seed, load_demo_workspace
from workbench.domain.models import (
    ActivityEvent,
    DayRecord,
    Idea,
    OutlineNode,
    PlanItem,
    Project,
    Resource,
)
from workbench.storage import StorageConflict, StorageError, WorkspaceStorage


def _save_demo_workspace(storage: WorkspaceStorage):
    """Persist the full demo workspace; returns the fixtures for comparison."""

    projects, activity = load_demo_workspace()
    seed = demo_day_seed()
    for project in projects:
        storage.save_project(project)
        for node in project.outline:
            storage.save_node(project.project_id, node)
    storage.save_day(seed)
    storage.save_ideas(
        [Idea(idea_id="idea-001", text="给热力图加月份分隔线", created_at=date.today())],
        next_seq=2,
    )
    for event in activity:
        storage.append_activity(event)
    return projects, seed


class RoundtripTests(unittest.TestCase):
    def test_full_workspace_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            projects, seed = _save_demo_workspace(storage)

            loaded = WorkspaceStorage(tmp).load()

            self.assertEqual(
                [p.project_id for p in loaded.projects],
                [p.project_id for p in projects],
            )
            self.assertEqual(loaded.projects, projects)
            self.assertEqual(loaded.days, {seed.day: seed})
            self.assertEqual(len(loaded.ideas), 1)
            self.assertEqual(loaded.ideas[0].text, "给热力图加月份分隔线")
            self.assertEqual(len(loaded.activity), len(load_demo_workspace()[1]))

    def test_empty_vault_loads_empty_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            loaded = WorkspaceStorage(tmp).load()

            self.assertEqual(loaded.projects, [])
            self.assertEqual(loaded.activity, [])
            self.assertEqual(loaded.ideas, [])
            self.assertEqual(loaded.days, {})

    def test_chinese_ids_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            project = Project(
                project_id="项目-星图",
                name="星图演示库",
                goal="中文标识符往返",
                phase="执行期",
                current_focus="验证中文路径",
                next_milestone="无",
                owner="林演示",
                outline=(
                    OutlineNode(
                        node_id="节点-目标",
                        project_id="项目-星图",
                        title="目标与边界",
                        kind="goal",
                        note="中文备注",
                        resources=(
                            Resource(resource_id="res-001", name="清单.xlsx", kind="表格"),
                        ),
                    ),
                ),
            )

            storage.save_project(project)
            storage.save_node("项目-星图", project.outline[0])
            loaded = WorkspaceStorage(tmp).load()

            self.assertEqual(loaded.projects, [project])
            self.assertTrue(
                (Path(tmp) / "projects" / "项目-星图" / "project.json").exists()
            )

    def test_activity_append_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            events = [
                ActivityEvent(date.today(), "", "capture_added", f"事件{i}")
                for i in range(3)
            ]

            for event in events:
                storage.append_activity(event)

            loaded = WorkspaceStorage(tmp).load()
            self.assertEqual(loaded.activity, events)


class ConflictGuardTests(unittest.TestCase):
    def test_external_day_edit_blocks_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            seed = demo_day_seed()
            storage.save_day(seed)

            md = Path(tmp) / "days" / f"{seed.day.isoformat()}.md"
            external = "## 手改的工作记录"
            md.write_text(external, encoding="utf-8")

            seed.worklog = "## 应用内的新内容"
            with self.assertRaises(StorageConflict):
                storage.save_day(seed)
            self.assertEqual(md.read_text(encoding="utf-8"), external)

    def test_external_node_edit_blocks_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            projects, _ = _save_demo_workspace(storage)
            node = projects[0].outline[0]

            node.title = "手改前标题"
            storage.save_node("proj-atlas", node)

            json_path = (
                Path(tmp) / "projects" / "proj-atlas" / "nodes" / f"{node.node_id}.json"
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            payload["title"] = "外部手改标题"
            json_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )

            node.title = "应用内新标题"
            with self.assertRaises(StorageConflict):
                storage.save_node("proj-atlas", node)

    def test_second_save_without_external_edit_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            record = DayRecord(
                day=date.today(), plan=[PlanItem(item_id="plan-001", text="正常连续保存")]
            )

            storage.save_day(record)
            record.plan.append(PlanItem(item_id="plan-002", text="第二条"))
            storage.save_day(record)  # 不应抛冲突

            loaded = WorkspaceStorage(tmp).load()
            self.assertEqual(
                [i.text for i in loaded.days[date.today()].plan],
                ["正常连续保存", "第二条"],
            )


class PathSafetyTests(unittest.TestCase):
    def test_escaping_node_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            node = OutlineNode(
                node_id="../evil",
                project_id="proj-atlas",
                title="t",
                kind="goal",
            )
            with self.assertRaises(ValueError):
                storage.save_node("proj-atlas", node)

    def test_absolute_and_separated_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            project = Project(
                project_id="/abs/root",
                name="x",
                goal="x",
                phase="x",
                current_focus="x",
                next_milestone="x",
                owner="x",
            )
            with self.assertRaises(ValueError):
                storage.save_project(project)
            with self.assertRaises(ValueError):
                storage.save_project(
                    Project(
                        project_id="a/b",
                        name="x",
                        goal="x",
                        phase="x",
                        current_focus="x",
                        next_milestone="x",
                        owner="x",
                    )
                )


class CorruptVaultTests(unittest.TestCase):
    def test_corrupt_day_json_raises_storage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            seed = demo_day_seed()
            storage.save_day(seed)
            (Path(tmp) / "days" / f"{seed.day.isoformat()}.json").write_text(
                "{not json", encoding="utf-8"
            )

            with self.assertRaises(StorageError):
                WorkspaceStorage(tmp).load()

    def test_corrupt_manifest_raises_storage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            storage.save_day(demo_day_seed())
            (Path(tmp) / "workspace.json").write_text("nope", encoding="utf-8")

            with self.assertRaises(StorageError):
                storage.save_day(demo_day_seed())


class DayMdMirrorTests(unittest.TestCase):
    """days/<day>.md:worklog 叙事 + 可选 ## Check/## Act 段;旧格式兼容。"""

    def test_check_act_sections_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            seed = demo_day_seed()
            seed.check_note = "复盘:Check 段内容。"
            seed.act_note = "行动:Act 段内容。"

            storage.save_day(seed)
            loaded = WorkspaceStorage(tmp).load()

            record = loaded.days[seed.day]
            self.assertEqual(record.check_note, "复盘:Check 段内容。")
            self.assertEqual(record.act_note, "行动:Act 段内容。")
            self.assertEqual(record.worklog, seed.worklog.strip("\n"))
            md = (Path(tmp) / "days" / f"{seed.day.isoformat()}.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("## Check", md)
            self.assertIn("## Act", md)

    def test_legacy_md_without_sections_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            seed = demo_day_seed()
            storage.save_day(seed)
            day_md = Path(tmp) / "days" / f"{seed.day.isoformat()}.md"
            day_md.write_text("只有工作记录的旧格式文件。", encoding="utf-8")

            loaded = WorkspaceStorage(tmp).load()

            record = loaded.days[seed.day]
            self.assertEqual(record.worklog, "只有工作记录的旧格式文件。")
            self.assertEqual(record.check_note, "")
            self.assertEqual(record.act_note, "")


class ProjectProgressRoundtripTests(unittest.TestCase):
    def test_progress_entries_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            projects, _ = load_demo_workspace()
            project = projects[0]
            from workbench.domain.models import ProgressEntry

            project.progress = (
                ProgressEntry(at=date.today(), text="接入完成"),
                ProgressEntry(at=date.today(), text="报表跑通"),
            )
            storage.save_project(project)
            for node in project.outline:
                storage.save_node(project.project_id, node)

            loaded = WorkspaceStorage(tmp).load()

            saved = next(
                p for p in loaded.projects if p.project_id == project.project_id
            )
            self.assertEqual(
                [e.text for e in saved.progress], ["接入完成", "报表跑通"]
            )


if __name__ == "__main__":
    unittest.main()
