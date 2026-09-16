import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from workbench.domain.fixtures import demo_day_seed, load_demo_workspace
from workbench.runtime.contracts import RunRequest
from workbench.runtime.fake_runtime import FakeRuntime
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import StorageConflict, WorkspaceStorage


def _completed_proposal(runtime, project_id):
    events = list(
        runtime.events(RunRequest(kind="project.review", project_id=project_id))
    )
    completed = [event for event in events if event.state == "completed"]
    return completed[0].proposal


class WorkspaceServiceProposalBoundaryTests(unittest.TestCase):
    def test_snapshot_unchanged_until_accept_proposal(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        before = service.snapshot()

        proposal = _completed_proposal(FakeRuntime(), "proj-atlas")

        self.assertIsNotNone(proposal)
        self.assertEqual(service.snapshot(), before)

        result = service.accept_proposal(proposal)

        self.assertTrue(result.applied)
        self.assertNotEqual(service.snapshot(), before)

    def test_rejected_proposal_leaves_state_unchanged(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        before = service.snapshot()
        proposal = _completed_proposal(FakeRuntime(), "proj-atlas")

        service.reject_proposal(proposal)

        self.assertEqual(service.snapshot(), before)


class StalledActionTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_in_progress_action_15_days_without_update_is_stalled(self):
        stalled = self._service().stalled_actions(project_id="proj-atlas")

        stalled_ids = [action.action_id for action in stalled]
        self.assertIn("act-002", stalled_ids)
        self.assertNotIn("act-001", stalled_ids)

    def test_waiting_action_is_not_marked_stalled(self):
        stalled_ids = [
            action.action_id
            for action in self._service().stalled_actions(project_id="proj-atlas")
        ]
        self.assertNotIn("act-003", stalled_ids)

    def test_deferred_action_is_not_marked_stalled(self):
        stalled_ids = [
            action.action_id
            for action in self._service().stalled_actions(project_id="proj-atlas")
        ]
        self.assertNotIn("act-005", stalled_ids)

    def test_completed_action_is_not_marked_stalled(self):
        stalled_ids = [
            action.action_id
            for action in self._service().stalled_actions(project_id="proj-atlas")
        ]
        self.assertNotIn("act-004", stalled_ids)

    def test_cancelled_action_is_not_marked_stalled(self):
        stalled_ids = [
            action.action_id
            for action in self._service().stalled_actions(project_id="proj-atlas")
        ]
        self.assertNotIn("act-006", stalled_ids)

    def test_viewing_pages_never_refreshes_last_meaningful_update(self):
        service = self._service()
        before = service.snapshot()

        service.project("proj-atlas")
        service.stalled_actions(project_id="proj-atlas")
        service.activity()

        self.assertEqual(service.snapshot(), before)


class HeatmapAggregationTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_heatmap_counts_only_meaningful_events(self):
        counts = self._service().heatmap_counts()

        total = sum(counts.values())
        self.assertEqual(total, 7)
        today = date.today()
        self.assertEqual(counts.get(today), 1)  # page_viewed excluded
        self.assertNotIn(today - timedelta(days=6), counts)  # only a view that day

    def test_heatmap_supports_cross_project_filter(self):
        counts = self._service().heatmap_counts(project_id="proj-boreas")

        self.assertEqual(sum(counts.values()), 3)
        today = date.today()
        self.assertEqual(counts.get(today - timedelta(days=1)), 1)
        self.assertEqual(counts.get(today - timedelta(days=4)), 1)
        self.assertEqual(counts.get(today - timedelta(days=12)), 1)
        self.assertNotIn(today, counts)  # atlas-only day excluded
        self.assertNotIn(today - timedelta(days=7), counts)

    def test_querying_heatmap_never_writes(self):
        service = self._service()
        before = service.snapshot()

        service.heatmap_counts()
        service.heatmap_counts(project_id="proj-boreas")

        self.assertEqual(service.snapshot(), before)


class QuickCaptureTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_quick_capture_creates_pending_idea_and_activity(self):
        service = self._service()
        before = service.snapshot()

        idea = service.quick_capture("试试用可变字体做汇报页")

        self.assertEqual(idea.status, "pending")
        self.assertIn(idea, service.ideas())
        capture_events = [
            event for event in service.activity()
            if event.kind == "capture_added"
        ]
        self.assertEqual(len(capture_events), 1)
        self.assertNotEqual(service.snapshot(), before)

    def test_quick_capture_counts_as_meaningful_for_heatmap(self):
        service = self._service()
        service.quick_capture("记录一条今天的工作线索")

        counts = service.heatmap_counts()

        today = date.today()
        self.assertEqual(
            counts.get(today), 2
        )  # fixture 当日 1 条有意义事件 + 本次捕获

    def test_quick_capture_rejects_blank_text(self):
        service = self._service()

        with self.assertRaises(ValueError):
            service.quick_capture("   ")


class DayPlanWriteTests(unittest.TestCase):
    """每日计划/工作记录:显式写方法、no-op 不留痕、事件种类正确。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_today_seeded_with_demo_day(self):
        record = self._service().day_record()

        self.assertEqual(len(record.plan), 3)
        self.assertIn("上午", record.worklog)

    def test_reading_unknown_day_writes_nothing(self):
        service = self._service()
        before = service.snapshot()

        record = service.day_record(date.today() - timedelta(days=1))

        self.assertEqual(record.plan, [])
        self.assertEqual(service.snapshot(), before)

    def test_add_plan_item_appends_and_emits_plan_updated(self):
        service = self._service()
        baseline = len(service.activity())

        item = service.add_plan_item(None, " 复核捕获条交互 ")

        self.assertEqual(item.text, "复核捕获条交互")
        self.assertFalse(item.done)
        self.assertIn(item, service.day_record().plan)
        new = service.activity()[baseline:]
        self.assertEqual([e.kind for e in new], ["plan_updated"])

    def test_add_plan_item_rejects_blank(self):
        with self.assertRaises(ValueError):
            self._service().add_plan_item(None, "   ")

    def test_rename_plan_item_noop_and_unknown_write_nothing(self):
        service = self._service()
        before = service.snapshot()
        first = service.day_record().plan[0]

        self.assertFalse(service.rename_plan_item(None, first.item_id, first.text))
        self.assertFalse(service.rename_plan_item(None, "plan-999", "新文本"))

        self.assertEqual(service.snapshot(), before)
        self.assertTrue(service.rename_plan_item(None, first.item_id, "改名后的计划"))

    def test_toggle_emits_completion_only_when_finishing(self):
        service = self._service()
        baseline = len(service.activity())
        first = service.day_record().plan[0]  # seeded done=True

        service.toggle_plan_item(None, first.item_id)  # True → False
        service.toggle_plan_item(None, first.item_id)  # False → True

        self.assertTrue(first.done)
        new = service.activity()[baseline:]
        self.assertEqual(
            [e.kind for e in new], ["content_updated", "task_completed"]
        )

    def test_remove_plan_item(self):
        service = self._service()
        item_id = service.day_record().plan[1].item_id

        self.assertTrue(service.remove_plan_item(None, item_id))
        self.assertFalse(
            any(i.item_id == item_id for i in service.day_record().plan)
        )
        self.assertFalse(service.remove_plan_item(None, item_id))

    def test_set_worklog_saves_once_and_identical_write_is_noop(self):
        service = self._service()
        baseline = len(service.activity())

        self.assertTrue(service.set_worklog(None, "## 新记录\n- 测试保存"))
        self.assertEqual(service.day_record().worklog, "## 新记录\n- 测试保存")
        new = service.activity()[baseline:]
        self.assertEqual([e.kind for e in new], ["worklog_updated"])

        before = service.snapshot()
        self.assertFalse(service.set_worklog(None, "## 新记录\n- 测试保存"))
        self.assertEqual(service.snapshot(), before)


class ProjectMetaWriteTests(unittest.TestCase):
    """项目/行动/节点元数据编辑:白名单、no-op 不留痕、不改停滞判定。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_set_project_field_updates_and_emits(self):
        service = self._service()
        baseline = len(service.activity())

        self.assertTrue(
            service.set_project_field("proj-atlas", "current_focus", " 补齐测试资源 ")
        )

        self.assertEqual(
            service.project("proj-atlas").current_focus, "补齐测试资源"
        )
        new = service.activity()[baseline:]
        self.assertEqual(new[0].kind, "content_updated")
        self.assertEqual(new[0].project_id, "proj-atlas")

    def test_set_project_field_rejects_non_whitelisted_field(self):
        service = self._service()
        before = service.snapshot()

        self.assertFalse(service.set_project_field("proj-atlas", "owner", "某人"))
        self.assertFalse(service.set_project_field("proj-atlas", "actions", "[]"))
        self.assertFalse(service.set_project_field("proj-none", "goal", "x"))

        self.assertEqual(service.snapshot(), before)

    def test_set_project_field_blank_and_unchanged_are_noops(self):
        service = self._service()
        before = service.snapshot()
        goal = service.project("proj-atlas").goal

        self.assertFalse(service.set_project_field("proj-atlas", "goal", "   "))
        self.assertFalse(service.set_project_field("proj-atlas", "goal", goal))

        self.assertEqual(service.snapshot(), before)

    def test_rename_action_keeps_staleness_clock_untouched(self):
        service = self._service()
        act = next(
            a
            for a in service.project("proj-atlas").actions
            if a.action_id == "act-002"
        )
        stalled_before = act.last_meaningful_update_at

        self.assertTrue(
            service.rename_action("proj-atlas", "act-002", "清理重复条目(改)")
        )

        self.assertEqual(act.title, "清理重复条目(改)")
        self.assertEqual(act.last_meaningful_update_at, stalled_before)
        self.assertIn(
            "act-002",
            [a.action_id for a in service.stalled_actions(project_id="proj-atlas")],
        )

    def test_rename_node_title_and_note_in_one_action(self):
        service = self._service()

        self.assertTrue(
            service.rename_node(
                "proj-atlas", "node-goal", title="目标与范围", note="新备注"
            )
        )

        node = service.project("proj-atlas").outline[0]
        self.assertEqual((node.title, node.note), ("目标与范围", "新备注"))
        self.assertFalse(service.rename_node("proj-atlas", "node-none", title="x"))
        self.assertFalse(service.rename_node("proj-atlas", "node-goal", title=" 目标与范围 "))


class CreateProjectTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_create_project_generates_id_starter_node_and_activity(self):
        service = self._service()

        project = service.create_project(
            " 新归档库 ", goal="整理归档", current_focus="建目录", owner=""
        )

        self.assertEqual(project.project_id, "proj-001")
        self.assertEqual(project.name, "新归档库")
        self.assertEqual(project.owner, "我")  # 空负责人回落
        self.assertEqual(project.outline[0].title, "目标与边界")
        self.assertIn(project, service.projects())
        kinds = [e.kind for e in service.activity()]
        self.assertEqual(kinds.count("project_created"), 1)

        second = service.create_project("第二个")
        self.assertEqual(second.project_id, "proj-002")

    def test_create_project_rejects_blank_name(self):
        with self.assertRaises(ValueError):
            self._service().create_project("   ")

    def test_created_project_survives_restart_with_starter_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            service = WorkspaceService(storage=storage)

            service.create_project("落盘新项目", goal="验证创建持久化")

            reopened = WorkspaceService.open(WorkspaceStorage(tmp))
            self.assertEqual([p.name for p in reopened.projects()], ["落盘新项目"])
            self.assertEqual(
                reopened.projects()[0].outline[0].title, "目标与边界"
            )


class ResourceWriteTests(unittest.TestCase):
    """节点资源:增/改名/改链接/移除,事件与 no-op 边界。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def _node(self, service, node_id):
        return next(
            n
            for n in service.project("proj-atlas").outline
            if n.node_id == node_id
        )

    def test_add_resource_attaches_and_emits_resource_added(self):
        service = self._service()
        baseline = len(service.activity())

        resource = service.add_resource(
            "proj-atlas", "node-goal", " 交接清单.md ", source="演示链接:x"
        )

        self.assertEqual(resource.name, "交接清单.md")
        self.assertIn(resource, self._node(service, "node-goal").resources)
        new = service.activity()[baseline:]
        self.assertEqual(
            [(e.kind, e.project_id) for e in new],
            [("resource_added", "proj-atlas")],
        )

    def test_add_resource_rejects_blank_and_unknown_node(self):
        service = self._service()

        with self.assertRaises(ValueError):
            service.add_resource("proj-atlas", "node-goal", "   ")
        with self.assertRaises(KeyError):
            service.add_resource("proj-atlas", "node-none", "x.md")

    def test_rename_resource_name_and_source_in_one_action(self):
        service = self._service()

        self.assertTrue(
            service.rename_resource(
                "proj-atlas",
                "node-tests",
                "res-001",
                name="测试环境清单v2.xlsx",
                source="演示链接:更新",
            )
        )
        resource = self._node(service, "node-tests").resources[0]
        self.assertEqual(
            (resource.name, resource.source),
            ("测试环境清单v2.xlsx", "演示链接:更新"),
        )

    def test_rename_resource_noop_and_unknown_write_nothing(self):
        service = self._service()
        before = service.snapshot()
        current = self._node(service, "node-tests").resources[0]

        self.assertFalse(
            service.rename_resource(
                "proj-atlas", "node-tests", "res-001", name=current.name
            )
        )
        self.assertFalse(
            service.rename_resource("proj-atlas", "node-tests", "res-999", name="x")
        )

        self.assertEqual(service.snapshot(), before)

    def test_remove_resource(self):
        service = self._service()

        self.assertTrue(
            service.remove_resource("proj-atlas", "node-tests", "res-002")
        )
        self.assertFalse(
            any(
                r.resource_id == "res-002"
                for r in self._node(service, "node-tests").resources
            )
        )
        self.assertFalse(
            service.remove_resource("proj-atlas", "node-tests", "res-002")
        )

    def test_resource_ids_do_not_collide_after_removal(self):
        service = self._service()
        first = service.add_resource("proj-atlas", "node-goal", "A.md")
        service.remove_resource("proj-atlas", "node-goal", first.resource_id)
        second = service.add_resource("proj-atlas", "node-goal", "B.md")

        self.assertNotEqual(first.resource_id, second.resource_id)


class PlanItemProjectTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_add_with_project_and_unknown_falls_back(self):
        service = self._service()

        item = service.add_plan_item(None, "整理归档目录", project_id="proj-atlas")
        other = service.add_plan_item(None, "随便记的", project_id="proj-none")

        self.assertEqual(item.project_id, "proj-atlas")
        self.assertEqual(other.project_id, "")  # 未知项目 → 其他

    def test_set_plan_item_project_moves_and_noop(self):
        service = self._service()

        self.assertTrue(
            service.set_plan_item_project(None, "plan-003", "proj-boreas")
        )
        moved = [i for i in service.day_record().plan if i.item_id == "plan-003"][0]
        self.assertEqual(moved.project_id, "proj-boreas")
        self.assertFalse(
            service.set_plan_item_project(None, "plan-003", "proj-boreas")
        )  # 相同归属 no-op

    def test_set_plan_item_project_unknown_becomes_other(self):
        service = self._service()

        self.assertTrue(
            service.set_plan_item_project(None, "plan-001", "proj-none")
        )

        item = [i for i in service.day_record().plan if i.item_id == "plan-001"][0]
        self.assertEqual(item.project_id, "")

    def test_attribution_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            service = WorkspaceService(storage=storage)

            service.add_plan_item(None, "带归属的计划", project_id="")

            reopened = WorkspaceService.open(WorkspaceStorage(tmp))
            items = reopened.day_record().plan
            self.assertEqual(
                [(i.text, i.project_id) for i in items],
                [("带归属的计划", "")],
            )


class IdeaStatusTests(unittest.TestCase):
    """想法状态流转:显式白名单、no-op 不留痕、原文不可改写、落盘可读回。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_status_transitions_emit_activity(self):
        service = self._service()
        idea = service.quick_capture("试试热力图月份分隔")

        self.assertTrue(service.set_idea_status(idea.idea_id, "kept"))
        self.assertTrue(service.set_idea_status(idea.idea_id, "archived"))

        statuses = [i.status for i in service.ideas()]
        self.assertIn("archived", statuses)
        events = [
            e.label
            for e in service.activity()
            if e.label.startswith("想法状态:")
        ]
        self.assertEqual(len(events), 2)

    def test_same_status_and_unknown_idea_are_noops(self):
        service = self._service()
        idea = service.quick_capture("重复状态不写")
        before = service.snapshot()

        self.assertFalse(service.set_idea_status(idea.idea_id, "pending"))
        self.assertFalse(service.set_idea_status("idea-999", "kept"))

        self.assertEqual(service.snapshot(), before)

    def test_invalid_status_rejected(self):
        service = self._service()
        with self.assertRaises(ValueError):
            service.set_idea_status("idea-001", "deleted")

    def test_status_change_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = WorkspaceStorage(tmp)
            service = WorkspaceService(storage=storage)
            idea = service.quick_capture("落盘的想法")

            service.set_idea_status(idea.idea_id, "archived")

            reopened = WorkspaceService.open(WorkspaceStorage(tmp))
            self.assertEqual(
                [i.status for i in reopened.ideas()], ["archived"]
            )
            self.assertEqual(
                [i.text for i in reopened.ideas()], ["落盘的想法"]
            )


class StorageBackedServiceTests(unittest.TestCase):
    """P2′ 落盘:显式写方法持久化,重开服务可完整读回;冲突被拦截。

    全部使用临时目录,不触真实 data-issue-vault。
    """

    def _service_with_storage(self, tmp):
        projects, activity = load_demo_workspace()
        seed = demo_day_seed()
        storage = WorkspaceStorage(tmp)
        for project in projects:
            storage.save_project(project)
            for node in project.outline:
                storage.save_node(project.project_id, node)
        storage.save_day(seed)
        return WorkspaceService(
            projects, activity, days={seed.day: seed}, storage=storage
        )

    def test_writes_survive_service_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = self._service_with_storage(tmp)

            service.add_plan_item(None, "落盘验证条目")
            service.set_worklog(None, "## 落盘\n- 验证往返")
            service.set_project_field("proj-atlas", "goal", "落盘后的新目标")
            service.rename_node("proj-atlas", "node-goal", title="目标与范围")
            service.add_resource("proj-atlas", "node-goal", "落盘资源.md")
            service.quick_capture("落盘想法")

            reopened = WorkspaceService.open(WorkspaceStorage(tmp))

            plan_texts = [i.text for i in reopened.day_record().plan]
            self.assertIn("落盘验证条目", plan_texts)
            self.assertEqual(reopened.day_record().worklog, "## 落盘\n- 验证往返")
            self.assertEqual(reopened.project("proj-atlas").goal, "落盘后的新目标")
            node = next(
                n
                for n in reopened.project("proj-atlas").outline
                if n.node_id == "node-goal"
            )
            self.assertEqual(node.title, "目标与范围")
            self.assertTrue(
                any(r.name == "落盘资源.md" for r in node.resources)
            )
            self.assertIn("落盘想法", [i.text for i in reopened.ideas()])
            self.assertEqual(reopened.activity()[-1].kind, "capture_added")

    def test_external_edit_makes_service_save_raise_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = self._service_with_storage(tmp)
            today = date.today()
            md = Path(tmp) / "days" / f"{today.isoformat()}.md"
            md.write_text("## 外部手改", encoding="utf-8")

            with self.assertRaises(StorageConflict):
                service.set_worklog(None, "## 应用内内容")
            self.assertEqual(md.read_text(encoding="utf-8"), "## 外部手改")

    def test_noop_writes_touch_nothing_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = self._service_with_storage(tmp)
            manifest_before = (Path(tmp) / "workspace.json").read_text(encoding="utf-8")

            service.set_worklog(None, service.day_record().worklog)  # 相同内容
            service.rename_plan_item(
                None, "plan-001", service.day_record().plan[0].text
            )

            self.assertEqual(
                (Path(tmp) / "workspace.json").read_text(encoding="utf-8"),
                manifest_before,
            )


class DirectActionStatusTests(unittest.TestCase):
    """set_action_status:不经 AI 提案的手动状态切换通道。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def _first_action(self, service):
        project = service.projects()[0]
        return project, project.actions[0]

    def test_complete_action_counts_as_meaningful(self):
        service = self._service()
        project, action = self._first_action(service)

        self.assertTrue(
            service.set_action_status(project.project_id, action.action_id, "completed")
        )

        self.assertEqual(action.status, "completed")
        kinds = [event.kind for event in service.activity()]
        self.assertIn("task_completed", kinds)

    def test_same_status_and_unknown_action_are_noops(self):
        service = self._service()
        project, action = self._first_action(service)
        before = service.snapshot()

        self.assertFalse(
            service.set_action_status(project.project_id, action.action_id, action.status)
        )
        self.assertFalse(
            service.set_action_status(project.project_id, "act-404", "completed")
        )
        self.assertEqual(service.snapshot(), before)

    def test_invalid_status_rejected(self):
        service = self._service()
        project, action = self._first_action(service)

        with self.assertRaises(ValueError):
            service.set_action_status(project.project_id, action.action_id, "done")

    def test_status_change_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects, activity = load_demo_workspace()
            storage = WorkspaceStorage(tmp)
            for project in projects:
                storage.save_project(project)
                for node in project.outline:
                    storage.save_node(project.project_id, node)
            service = WorkspaceService(projects, activity, storage=storage)
            project = service.projects()[0]
            action = project.actions[0]
            service.set_action_status(project.project_id, action.action_id, "waiting")

            reloaded = WorkspaceService.open(WorkspaceStorage(tmp))
            action_after = next(
                a
                for p in reloaded.projects()
                if p.project_id == project.project_id
                for a in p.actions
                if a.action_id == action.action_id
            )
            self.assertEqual(action_after.status, "waiting")


class DayCheckActTests(unittest.TestCase):
    """Check/Act 落 DayRecord 并随 days/<day>.md 镜像持久化。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_check_and_act_write_and_noop(self):
        service = self._service()

        self.assertTrue(service.set_day_check(None, "三件事里完成两件,数据源那件被环境阻塞。"))
        self.assertTrue(service.set_day_act(None, "明天先把数据源权限申请提上计划。"))
        self.assertFalse(service.set_day_check(None, "三件事里完成两件,数据源那件被环境阻塞。"))

        record = service.day_record()
        self.assertTrue(record.check_note.startswith("三件事里完成两件"))
        self.assertTrue(record.act_note.startswith("明天先把数据源权限"))

    def test_check_act_survive_restart_with_md_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects, activity = load_demo_workspace()
            seed = demo_day_seed()
            storage = WorkspaceStorage(tmp)
            for project in projects:
                storage.save_project(project)
                for node in project.outline:
                    storage.save_node(project.project_id, node)
            storage.save_day(seed)
            service = WorkspaceService(
                projects, activity, days={seed.day: seed}, storage=storage
            )
            service.set_day_check(seed.day, "复盘:计划粒度偏粗。")
            service.set_day_act(seed.day, "行动:明天计划拆到 30 分钟粒度。")

            md = (
                Path(tmp) / "days" / f"{seed.day.isoformat()}.md"
            ).read_text(encoding="utf-8")
            self.assertIn("## Check", md)
            self.assertIn("## Act", md)
            reloaded = WorkspaceService.open(WorkspaceStorage(tmp))
            record = reloaded.day_record(seed.day)
            self.assertEqual(record.check_note, "复盘:计划粒度偏粗。")
            self.assertEqual(record.act_note, "行动:明天计划拆到 30 分钟粒度。")
            self.assertEqual(record.worklog, seed.worklog.strip("\n"))


class ProjectProgressTests(unittest.TestCase):
    """append/remove_project_progress:文件路由自动追加的落点与撤销。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_append_progress_records_entry_and_activity(self):
        service = self._service()
        project = service.projects()[0]

        entry = service.append_project_progress(
            project.project_id, "完成渠道数据接入,报表可跑通。"
        )

        self.assertIsNotNone(entry)
        self.assertEqual(project.progress[-1].text, "完成渠道数据接入,报表可跑通。")
        labels = [event.label for event in service.activity()]
        self.assertTrue(any(label.startswith("项目进度:") for label in labels))

    def test_append_progress_rejects_unknown_or_blank(self):
        service = self._service()
        self.assertIsNone(service.append_project_progress("proj-404", "x"))
        self.assertIsNone(service.append_project_progress(service.projects()[0].project_id, "  "))

    def test_remove_project_progress_undoes_append(self):
        service = self._service()
        project = service.projects()[0]
        entry = service.append_project_progress(project.project_id, "自动归档的进度")

        self.assertTrue(service.remove_project_progress(project.project_id, entry))
        self.assertFalse(
            any(e.text == "自动归档的进度" for e in project.progress)
        )

    def test_progress_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects, activity = load_demo_workspace()
            storage = WorkspaceStorage(tmp)
            for project in projects:
                storage.save_project(project)
                for node in project.outline:
                    storage.save_node(project.project_id, node)
            service = WorkspaceService(projects, activity, storage=storage)
            project = service.projects()[0]
            service.append_project_progress(project.project_id, "持久化的进度条目")

            reloaded = WorkspaceService.open(WorkspaceStorage(tmp))
            progress = {
                p.project_id: p.progress for p in reloaded.projects()
            }[project.project_id]
            self.assertEqual(len(progress), 1)
            self.assertEqual(progress[0].text, "持久化的进度条目")


if __name__ == "__main__":
    unittest.main()
