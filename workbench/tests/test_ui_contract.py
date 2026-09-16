"""UI contract tests: user-visible labels, routes, and callbacks only.

Builders must work without a Page so tests never open a window.
"""

import unittest
from datetime import date, timedelta

import flet as ft

from workbench.components import THEME
from workbench.components.ai_panel import AIPanelState, build_ai_panel
from workbench.components.concierge import ConciergeController
from workbench.components.navigation import (
    MAIN_NAV_ITEMS,
    ROUTE_ACTIVITY,
    ROUTE_ARCHIVE,
    ROUTE_IDEAS,
    ROUTE_PROJECTS,
    ROUTE_TODAY,
    build_main_nav,
)
from workbench.components.wrapup_wizard import STEPS, WrapupWizard
from workbench.domain.fixtures import load_demo_workspace
from workbench.runtime.text_runtime import FakePromptRuntime
from workbench.services.prompt_library import PromptLibrary
from workbench.services.workspace_service import WorkspaceService
from workbench.views.activity import build_activity
from workbench.views.archive import build_archive
from workbench.views.ideas import build_ideas
from workbench.views.node_detail import build_node_detail
from workbench.views.project_overview import build_project_overview
from workbench.views.projects_home import build_projects_home
from workbench.views.today import TodayHub, build_today


def visible_texts(control):
    """Collect user-visible strings from a control tree (no private details)."""

    out = []

    def walk(node):
        if node is None or isinstance(node, (int, float, bool)):
            return
        if isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item)
            return
        if isinstance(node, str):
            out.append(node)
            return
        if isinstance(node, ft.Text) and node.value:
            out.append(str(node.value))
        elif isinstance(node, ft.Markdown) and node.value:
            out.append(str(node.value))
        elif isinstance(node, ft.Checkbox) and node.label:
            out.append(str(node.label))
        elif isinstance(node, ft.Tooltip) and node.message:
            out.append(str(node.message))
        elif isinstance(node, ft.TextField) and node.label:
            out.append(str(node.label))
        for attr in ("content", "controls", "leading", "label"):
            walk(getattr(node, attr, None))

    walk(control)
    return out


def _noop(*_args, **_kwargs):
    return None


def _double_tap_targets(root, needle):
    """GestureDetectors whose visible text contains needle."""

    found = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        if isinstance(node, ft.GestureDetector):
            if any(needle in text for text in visible_texts(node)):
                found.append(node)
        for attr in ("content", "controls"):
            walk(getattr(node, attr, None))

    walk(root)
    return found


def _btn_text(button):
    content = getattr(button, "content", None)
    return content if isinstance(content, str) else ""


def _edit_and_submit(root, needle, new_value):
    """Double-tap the editable showing `needle`, type, submit.

    Only the editable target produces a TextField on double-tap, so try
    candidates until one does.
    """

    for target in _double_tap_targets(root, needle):
        target.on_double_tap(None)
        fields = _local_fields(root)
        if fields:
            fields[0].value = new_value
            fields[0].on_submit(None)
            return True
    return False


def _is_capture_field(field) -> bool:
    """常驻捕获条是唯一 hint 以「随手记」开头的输入框。"""

    hint_text = str(getattr(field, "hint_text", "") or "")
    return hint_text.startswith("随手记")


def _local_fields(root):
    """除常驻捕获条外的输入框(今天页改名/添加/工作记录等本地编辑框)。"""

    return [
        f for f in _walk_type(root, ft.TextField) if not _is_capture_field(f)
    ]


class NavigationContractTests(unittest.TestCase):
    def test_main_nav_has_today_ideas_projects_activity_archive(self):
        labels = {label for label, _route, _icon in MAIN_NAV_ITEMS}
        self.assertEqual(
            labels, {"今天", "想法", "项目", "活动", "归档"}
        )

    def test_main_nav_items_carry_routes(self):
        routes = {route for _label, route, _icon in MAIN_NAV_ITEMS}
        self.assertIn(ROUTE_TODAY, routes)
        self.assertIn(ROUTE_IDEAS, routes)
        self.assertIn(ROUTE_PROJECTS, routes)
        self.assertIn(ROUTE_ACTIVITY, routes)
        self.assertIn(ROUTE_ARCHIVE, routes)

    def test_built_nav_shows_all_labels(self):
        texts = visible_texts(build_main_nav(ROUTE_PROJECTS, on_route=_noop))
        for label in ("今天", "想法", "项目", "活动", "归档"):
            self.assertIn(label, texts)

    def test_sidebar_has_ai_toggle_independent_of_nav_items(self):
        # 2026-09-16 用户定:AI 面板默认收起,侧栏「AI 助手」是开关项,
        # 不占五个主导航位;待确认 Proposal 且收起时亮小圆点。
        called = []
        control = build_main_nav(
            ROUTE_PROJECTS,
            on_route=_noop,
            ai_open=True,
            on_toggle_ai=lambda: called.append(True),
            ai_attention=False,
        )
        self.assertIn("AI 助手", visible_texts(control))
        toggle = next(
            c
            for c in _walk_type(control, ft.Container)
            if c.on_click is not None and "AI 助手" in visible_texts(c)
        )
        toggle.on_click(None)
        self.assertTrue(called, "点击 AI 助手应触发面板开关回调")

    def test_ai_toggle_shows_attention_dot_when_awaiting_and_closed(self):
        control = build_main_nav(
            ROUTE_PROJECTS,
            on_route=_noop,
            ai_open=False,
            on_toggle_ai=_noop,
            ai_attention=True,
        )
        dots = [
            c
            for c in _walk_type(control, ft.Container)
            if c.bgcolor == THEME["stall"] and c.width == 7
        ]
        self.assertTrue(dots, "面板收起+有待确认 Proposal 应显示提醒圆点")


class ProjectOverviewContractTests(unittest.TestCase):
    def _build(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        return build_project_overview(
            service, "proj-atlas", on_open_node=_noop
        )

    def test_overview_has_summary_outline_focus_tasks_and_stalled(self):
        texts = visible_texts(self._build())
        for label in (
            "项目目标",
            "当前阶段",
            "当前焦点",
            "下一个里程碑",
            "选择节点查看详情",
            "目标与边界",
            "参与者与职责",
            "当前进展",
            "关键判断",
            "测试资源",
            "资料与链接",
            "待推进事项",
            "当前需要关注",
            "今日任务",
            "长期停滞",
            "14 天活动",
        ):
            self.assertIn(label, texts)

    def test_owner_is_avatar_with_tooltip(self):
        # 2026-09-16 用户决定:负责人不再占 meta 格,只留姓名圆框(全名在 tooltip)。
        page = self._build()
        avatars = [a for a in _walk_type(page, ft.CircleAvatar) if a.tooltip]
        self.assertTrue(
            any("林演示" in a.tooltip for a in avatars),
            "负责人应是带全名 tooltip 的圆框",
        )

    def test_detail_area_is_scrollable(self):
        # 2026-09-16 修复:矮窗口下详情区(节点树/关注卡)被裁且无法滚动。
        page = self._build()
        detail_columns = [
            c
            for c in _walk_type(page, ft.Column)
            if c.scroll == ft.ScrollMode.AUTO
            and "项目目标" in "".join(visible_texts(c))
        ]
        self.assertTrue(detail_columns, "详情区 Column 应可滚动且包含 meta 卡")

    def test_status_tags_follow_action_rows(self):
        control = self._build()
        rows = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Row):
                rows.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        in_progress_rows = [
            row
            for row in rows
            if "梳理星图目录结构" in "".join(visible_texts(row))
        ]
        self.assertTrue(in_progress_rows, "应存在包含行动条目的行")
        row_texts = visible_texts(in_progress_rows[0])
        self.assertIn("进行中", row_texts, "行动行内应紧跟状态徽章")

    def test_outline_rows_use_legible_text_chevron(self):
        """行尾箭头必须是文本字形:CHEVRON_RIGHT 图标 size=14 的墨迹仅约 7px,
        在 13px 标题旁视觉上像渲染损坏(2026-08-31 用户报告的根因)。"""
        from workbench.components.project_outline import (
            build_project_outline,
        )

        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        project = service.project("proj-atlas")
        outline = build_project_outline(project, on_open_node=_noop)

        clickable_rows = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Container) and node.on_click is not None:
                clickable_rows.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(outline)
        self.assertEqual(len(clickable_rows), 7, "大纲应有 7 个可点击行")
        for row in clickable_rows:
            texts = visible_texts(row)
            self.assertIn("›", texts, "大纲行尾应有可读的文本字形箭头")
            icons = []

            def collect_icons(node):
                if node is None:
                    return
                if isinstance(node, (list, tuple)):
                    for item in node:
                        collect_icons(item)
                    return
                if isinstance(node, ft.Icon):
                    icons.append(node)
                for attr in ("content", "controls"):
                    collect_icons(getattr(node, attr, None))

            collect_icons(row)
            chevron_icons = [
                icon for icon in icons if icon.icon == ft.Icons.CHEVRON_RIGHT
            ]
            self.assertEqual(
                chevron_icons, [], "行尾不得使用 CHEVRON_RIGHT 图标(墨迹过小)"
            )


class NodeDetailContractTests(unittest.TestCase):
    def _build(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        return build_node_detail(
            service,
            "proj-atlas",
            "node-tests",
            on_back=_noop,
            on_open_node=_noop,
        )

    def test_node_page_keeps_outline_and_content_sections(self):
        texts = visible_texts(self._build())
        for label in (
            "返回项目总览",
            "目标与边界",
            "待推进事项",  # outline persists on node page
            "相关资源",
            "关系",
        ):
            self.assertIn(label, texts)

    def test_tags_follow_resource_files_not_standalone_section(self):
        control = self._build()
        rows = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Row):
                rows.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        file_row_tags = []
        for row in rows:
            row_texts = visible_texts(row)
            joined = "".join(row_texts)
            if "测试环境清单" in joined:
                # 资源外层行最先命中;名称编辑标签内部还会再出现一层
                # 只含文件名的 Row,所以这里取第一个匹配即真正的文件行。
                file_row_tags = [t for t in row_texts if t in ("常用", "环境")]
                break
        self.assertEqual(
            sorted(file_row_tags), ["常用", "环境"],
            "文件行内应紧跟标签徽章",
        )
        all_texts = visible_texts(control)
        self.assertNotIn("标签", all_texts, "标签应为行内徽章,不作为独立区块")

    def test_node_page_has_markdown_body(self):
        control = self._build()
        found = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Markdown):
                found.append(node.value)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        self.assertTrue(any("#" in value or len(value) > 10 for value in found))


class TodayContractTests(unittest.TestCase):
    def _build(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        return build_today(service)

    def test_today_uses_simple_checkboxes_not_kanban(self):
        control = self._build()
        texts = visible_texts(control)
        for label in (
            "今日计划",
            "工作记录",
            "待整理想法",
            "整理今日上下文",
        ):
            self.assertIn(label, texts)
        self.assertNotIn("看板", "".join(texts))
        self.assertNotIn("Kanban", "".join(texts))

        checkboxes = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Checkbox):
                checkboxes.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        self.assertGreaterEqual(len(checkboxes), 2)

    def test_today_has_exactly_one_capture_box(self):
        """2026-09-15 改约:智能捕获条常驻 Today 页顶部(原约零输入框)。"""
        control = self._build()
        fields = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.TextField):
                fields.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        self.assertEqual(len(fields), 1, "Today 页应恰有 1 个常驻捕获框")
        self.assertTrue(_is_capture_field(fields[0]))

    def test_today_ideas_come_from_service(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        service.quick_capture("给热力图加月份分隔线")
        texts = visible_texts(build_today(service))
        self.assertIn("给热力图加月份分隔线", texts, "待整理想法应来自 service.ideas()")

    def test_ideas_and_context_stack_vertically(self):
        control = self._build()
        order = []
        marker_box = {"待整理想法": [], "整理今日上下文": []}

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.Text) and node.value in marker_box:
                order.append(str(node.value))
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        self.assertEqual(
            order, ["待整理想法", "整理今日上下文"]
        )  # vertical stack: ideas first, context below


class IdeasContractTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_ideas_page_groups_by_status_with_actions(self):
        service = self._service()
        service.quick_capture("给热力图加月份分隔线")
        service.quick_capture("第二个想法")
        service.set_idea_status("idea-001", "kept")

        texts = visible_texts(build_ideas(service))
        joined = "".join(texts)
        for label in ("想法", "待整理", "已保留", "已归档", "给热力图加月份分隔线"):
            self.assertIn(label, joined if label != "想法" else texts)

    def test_archive_button_moves_idea_to_archived(self):
        service = self._service()
        service.quick_capture("准备归档的想法")
        page = build_ideas(service, on_refresh=_noop)

        archive_btn = next(
            b for b in _walk_type(page, ft.TextButton) if _btn_text(b) == "归档"
        )
        archive_btn.on_click(None)

        self.assertEqual(
            [i.status for i in service.ideas()], ["archived"]
        )

    def test_original_text_is_not_editable(self):
        """Capture 原文不可覆盖:想法行不提供双击编辑目标。"""
        service = self._service()
        service.quick_capture("不可改写的原文")
        page = build_ideas(service, on_refresh=_noop)

        self.assertEqual(
            _double_tap_targets(page, "不可改写的原文"), [],
            "想法文本不应有双击编辑入口",
        )


class ArchiveContractTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_archive_page_lists_archived_ideas_and_closed_actions(self):
        service = self._service()
        service.quick_capture("已归档想法")
        service.set_idea_status("idea-001", "archived")

        texts = visible_texts(build_archive(service, on_refresh=_noop))
        joined = "".join(texts)
        self.assertIn("已归档想法", joined)
        self.assertIn("已归档想法", joined.replace("已归档想法", "", 1) + "已归档想法")
        self.assertIn("已完成 / 已取消行动", joined)
        self.assertIn("建立演示命名规范", joined)

    def test_restore_button_returns_idea_to_pending(self):
        service = self._service()
        service.quick_capture("要恢复的想法")
        service.set_idea_status("idea-001", "archived")
        page = build_archive(service, on_refresh=_noop)

        restore_btn = next(
            b
            for b in _walk_type(page, ft.TextButton)
            if _btn_text(b) == "恢复待整理"
        )
        restore_btn.on_click(None)

        self.assertEqual([i.status for i in service.ideas()], ["pending"])


class ActivityContractTests(unittest.TestCase):
    def test_activity_page_has_heatmap_legend_and_stalled(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        texts = visible_texts(build_activity(service, on_pick_date=_noop))
        for label in ("活动统计", "长期停滞", "少", "多"):
            self.assertIn(label, texts)


class AIPanelContractTests(unittest.TestCase):
    def test_panel_has_run_button_and_status(self):
        state = AIPanelState(status="idle")
        texts = visible_texts(
            build_ai_panel(
                state, on_run_review=_noop, on_accept=_noop, on_reject=_noop
            )
        )
        self.assertIn("AI 助手", texts)
        self.assertIn("运行项目审查", texts)
        self.assertIn("运行状态", texts)

    def test_awaiting_state_shows_proposal_and_legend(self):
        from workbench.runtime.contracts import RunRequest
        from workbench.runtime.fake_runtime import FakeRuntime

        events = list(
            FakeRuntime().events(
                RunRequest(kind="project.review", project_id="proj-atlas")
            )
        )
        proposal = [e for e in events if e.state == "completed"][0].proposal
        state = AIPanelState(status="awaiting", proposal=proposal)
        texts = visible_texts(
            build_ai_panel(
                state, on_run_review=_noop, on_accept=_noop, on_reject=_noop
            )
        )
        joined = "".join(texts)
        self.assertIn("待确认", joined)
        self.assertIn("确认更新", joined)
        self.assertIn("暂不更新", joined)
        self.assertIn("已确认", joined)
        self.assertIn("AI 推荐", joined)
        self.assertIn("外部知识", joined)

    def test_panel_hosts_concierge_sections(self):
        # 2026-09-16 合并:AI 面板承载草稿卡主控台(E 形态)。
        from workbench.runtime.text_runtime import FakePromptRuntime
        from workbench.services.prompt_library import PromptLibrary

        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        concierge = ConciergeController(service)
        concierge.set_providers(PromptLibrary(), FakePromptRuntime())
        texts = visible_texts(
            build_ai_panel(
                AIPanelState(status="idle"),
                on_run_review=_noop,
                on_accept=_noop,
                on_reject=_noop,
                concierge=concierge,
            )
        )
        for label in ("阶段动作", "今日计划建议", "Check 引导", "本周复盘", "思考方式点名", "点名运行", "草稿卡"):
            self.assertIn(label, texts)

    def test_concierge_thinking_targets_cover_ideas_and_projects(self):
        from workbench.runtime.text_runtime import FakePromptRuntime
        from workbench.services.prompt_library import PromptLibrary

        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        service.quick_capture("给主控台试一条想法")  # 演示库默认 0 条待整理想法
        concierge = ConciergeController(service)
        concierge.set_providers(PromptLibrary(), FakePromptRuntime())
        keys = [key for key, _name, _k in concierge._targets()]
        self.assertTrue(any(k.startswith("idea:") for k in keys))
        self.assertTrue(any(k == "project:proj-atlas" for k in keys))


class CaptureBarContractTests(unittest.TestCase):
    """全局底部快速记录条:每个页面的骨架都带,提交经 on_capture 上交。"""

    def _page(self, on_capture):
        from workbench.components.navigation import build_page

        return build_page(
            ROUTE_PROJECTS,
            on_route=_noop,
            content=ft.Text("内容区"),
            on_capture=on_capture,
        )

    def test_build_page_has_bottom_capture_bar(self):
        control = self._page(_noop)
        texts = visible_texts(control)
        self.assertIn("记录", texts)
        fields = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.TextField):
                fields.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        walk(control)
        self.assertEqual(len(fields), 1, "骨架应有且仅有一个捕获输入框")
        self.assertIn("快速记录", fields[0].hint_text or "")

    def test_capture_bar_sits_below_main_row(self):
        from workbench.components.navigation import build_page

        control = build_page(
            ROUTE_TODAY, on_route=_noop, content=ft.Text("x"), on_capture=_noop
        )
        column = control.content
        self.assertIsInstance(column, ft.Column)
        self.assertEqual(len(column.controls), 2, "骨架 = 主行 + 底部捕获条")
        self.assertIsInstance(column.controls[0], ft.Row)
        self.assertNotIsInstance(column.controls[1], ft.Row, "捕获条不是主行的一部分")

    def test_capture_bar_submit_passes_text_to_callback(self):
        received = []
        control = self._page(received.append)
        fields = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if isinstance(node, ft.TextField):
                fields.append(node)
            if isinstance(node, ft.FilledButton):
                buttons.append(node)
            for attr in ("content", "controls"):
                walk(getattr(node, attr, None))

        buttons = []
        walk(control)
        fields[0].value = "复测 Windows 字体渲染"
        fields[0].on_submit(None)

        self.assertEqual(received, ["复测 Windows 字体渲染"])

        received.clear()
        buttons[0].on_click(None)
        self.assertEqual(received, ["复测 Windows 字体渲染"], "按钮与回车提交走同一回调")

    def test_blank_capture_submits_nothing(self):
        received = []
        control = self._page(received.append)
        fields = [
            node for node in _walk_type(control, ft.TextField)
        ]
        fields[0].value = "   "
        fields[0].on_submit(None)
        self.assertEqual(received, [])


def _walk_type(root, control_type):
    found = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        if isinstance(node, control_type):
            found.append(node)
        for attr in ("content", "controls"):
            walk(getattr(node, attr, None))

    walk(root)
    return found


class ArtifactEntryContractTests(unittest.TestCase):
    """2026-09-16:Artifact 大卡压缩为详情区头部的「项目流图」点击入口。"""

    def test_overview_header_has_flow_entry(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        called = []
        page = build_project_overview(
            service,
            "proj-atlas",
            on_open_node=_noop,
            on_open_artifact=lambda: called.append(True),
        )
        entry = next(
            b
            for b in _walk_type(page, ft.TextButton)
            if _btn_text(b) == "项目流图"
        )
        entry.on_click(None)
        self.assertTrue(called, "点击项目流图入口应触发外部打开回调")

    def test_overview_without_entry_builds(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        page = build_project_overview(service, "proj-atlas", on_open_node=_noop)
        self.assertFalse(
            [_btn_text(b) for b in _walk_type(page, ft.TextButton) if _btn_text(b) == "项目流图"]
        )


class TodayEditingContractTests(unittest.TestCase):
    """Today 页可编辑:加号行、点标签改名、勾选持久化、工作记录编辑。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_today_shows_add_plan_row(self):
        page = build_today(self._service())
        self.assertIn("添加计划项", "".join(visible_texts(page)))

    def test_add_plan_row_submit_adds_item(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        add_btn = next(
            b
            for b in _walk_type(page, ft.TextButton)
            if "添加计划项" in _btn_text(b)
        )
        add_btn.on_click(None)
        field = _local_fields(page)[0]
        field.value = "复核双击编辑交互"
        field.on_submit(None)

        self.assertTrue(
            any(i.text == "复核双击编辑交互" for i in service.day_record().plan)
        )

    def test_blank_add_submits_nothing(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)
        before = len(service.day_record().plan)

        add_btn = next(
            b
            for b in _walk_type(page, ft.TextButton)
            if "添加计划项" in _btn_text(b)
        )
        add_btn.on_click(None)
        field = _local_fields(page)[0]
        field.value = "   "
        field.on_submit(None)

        self.assertEqual(len(service.day_record().plan), before)

    def test_click_label_then_submit_renames_plan_item(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        self.assertTrue(
            _edit_and_submit(page, "清理重复演示条目", "清理重复条目v2")
        )
        self.assertTrue(
            any(i.text == "清理重复条目v2" for i in service.day_record().plan)
        )

    def test_checkbox_toggle_persists_to_service(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        boxes = _walk_type(page, ft.Checkbox)
        boxes[1].on_change(None)  # 清理重复演示条目 False → True

        self.assertTrue(service.day_record().plan[1].done)

    def test_worklog_edit_button_save_roundtrip(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        target = _double_tap_targets(page, "复核演示条目命名")[0]
        target.on_double_tap(None)
        field = next(f for f in _walk_type(page, ft.TextField) if f.multiline)
        field.value = "## 工作记录\n- 测试保存链路"
        save = next(
            b for b in _walk_type(page, ft.FilledButton) if _btn_text(b) == "保存"
        )
        save.on_click(None)

        self.assertEqual(
            service.day_record().worklog, "## 工作记录\n- 测试保存链路"
        )

    def test_plan_rows_carry_project_badges(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        joined = "".join(visible_texts(page))
        self.assertIn("@星图演示库", joined)  # 种子条目归属
        self.assertIn("@其他", joined)  # plan-003 未归属
        menus = _walk_type(page, ft.PopupMenuButton)
        self.assertGreaterEqual(len(menus), 3, "每条计划应有项目选单")

    def test_badge_menu_moves_item_to_other_project(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        menu = next(
            m
            for m in _walk_type(page, ft.PopupMenuButton)
            if "@其他" in visible_texts(m)
        )
        item = next(
            i
            for i in service.day_record().plan
            if i.text == "写周报草稿"
        )
        pick_boreas = next(
            mi
            for mi in menu.items
            if getattr(mi, "content", "") == "@北风档案"
        )
        pick_boreas.on_click(None)

        refreshed = [
            i for i in service.day_record().plan if i.item_id == item.item_id
        ][0]
        self.assertEqual(refreshed.project_id, "proj-boreas")

    def test_add_row_has_project_dropdown_and_mention_parsing(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        add_btn = next(
            b for b in _walk_type(page, ft.TextButton) if _btn_text(b) == "添加计划项"
        )
        add_btn.on_click(None)

        dropdowns = _walk_type(page, ft.Dropdown)
        self.assertEqual(len(dropdowns), 1, "添加行应有项目下拉")
        options = dropdowns[0].options
        self.assertEqual(options[0].text, "其他")
        self.assertIn("北风档案", [o.text for o in options])

        field = _local_fields(page)[0]
        field.value = "归组测试 @星图"
        field.on_submit(None)

        item = [
            i for i in service.day_record().plan if i.text == "归组测试"
        ]
        self.assertTrue(item, "@提及应从文本剥离")
        self.assertEqual(item[0].project_id, "proj-atlas")

    def test_multiline_editor_fills_width_and_grows_with_content(self):
        service = self._service()
        long_text = "## 工作记录\n" + "\n".join(f"- 条目{i}" for i in range(30))
        service.set_worklog(None, long_text)
        page = build_today(service, on_refresh=_noop)

        target = _double_tap_targets(page, "## 工作记录")[0]
        target.on_double_tap(None)

        field = next(f for f in _walk_type(page, ft.TextField) if f.multiline)
        self.assertGreaterEqual(
            field.min_lines, long_text.count("\n") + 1,
            "编辑态高度应至少覆盖现有内容行数",
        )
        self.assertIsNone(
            field.max_lines, "未设 max_lines,内容增多时输入框随内容向下生长"
        )
        stretched = [
            col
            for col in _walk_type(page, ft.Column)
            if col.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
            and field in (col.controls or [])
        ]
        self.assertTrue(stretched, "编辑态应位于 STRETCH 列中,占满卡片宽度")

    def test_label_editor_fills_available_width(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)

        target = _double_tap_targets(page, "清理重复演示条目")[0]
        target.on_double_tap(None)
        field = _local_fields(page)[0]

        stretched = [
            col
            for col in _walk_type(page, ft.Column)
            if col.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
            and field in (col.controls or [])
        ]
        self.assertTrue(stretched, "单行编辑态也应位于 STRETCH 列中,不缩窄")


    def test_badge_menu_moves_its_own_item_not_the_last(self):
        """回归:徽章菜单曾晚绑定 item_id,所有行都会改到最后一行(P0)。"""

        service = self._service()
        page = build_today(service, on_refresh=_noop)
        menus = [
            m
            for m in _walk_type(page, ft.PopupMenuButton)
            if getattr(m, "tooltip", "") is None and _btn_text(m) == ""
            and visible_texts(m) and str(visible_texts(m)[0]).startswith("@")
        ]
        first_menu = menus[0]  # 第一条计划(梳理星图目录结构)的归属菜单
        pick = next(
            mi for mi in first_menu.items if getattr(mi, "content", "") == "@北风档案"
        )
        pick.on_click(None)

        moved = next(
            i
            for i in service.day_record().plan
            if i.text == "梳理星图目录结构"
        )
        self.assertEqual(moved.project_id, "proj-boreas", "应改到被点中的那一行")
        untouched = next(
            i
            for i in service.day_record().plan
            if i.text == "写周报草稿"
        )
        self.assertEqual(untouched.project_id, "", "最后一行不应被误改")


class TodayHubContractTests(unittest.TestCase):
    """合并版 TodayHub 新契约:捕获路由/顺延条/思考方式/草稿卡/键选。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def _capture(self, page):
        return next(
            f for f in _walk_type(page, ft.TextField) if _is_capture_field(f)
        )

    # -- 捕获路由三落点 ------------------------------------------------------

    def test_capture_bang_routes_to_plan(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)
        capture = self._capture(page)
        capture.value = "!写周报"
        capture.on_submit(None)
        self.assertTrue(any(i.text == "写周报" for i in service.day_record().plan))
        self.assertEqual(capture.value or "", "", "提交后应清空捕获条")

    def test_capture_hash_routes_to_project_plan(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)
        capture = self._capture(page)
        capture.value = "#星图演示库 跟进口径问题"
        capture.on_submit(None)
        item = next(
            i for i in service.day_record().plan if i.text == "跟进口径问题"
        )
        self.assertEqual(item.project_id, "proj-atlas")

    def test_capture_plain_text_routes_to_idea(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop)
        capture = self._capture(page)
        capture.value = "给热力图加月份分隔线"
        capture.on_submit(None)
        self.assertTrue(
            any(i.text == "给热力图加月份分隔线" for i in service.ideas())
        )

    # -- 顺延条 ---------------------------------------------------------------

    def test_rollover_bar_moves_yesterday_undone(self):
        service = self._service()
        yesterday = date.today() - timedelta(days=1)
        service.add_plan_item(yesterday, "昨天没做完的事")
        page = build_today(service, on_refresh=_noop)

        self.assertIn("昨天还有 1 项没完成", visible_texts(page))
        roll = next(
            b for b in _walk_type(page, ft.TextButton) if _btn_text(b) == "顺延到今天"
        )
        roll.on_click(None)

        self.assertTrue(
            any(i.text == "昨天没做完的事" for i in service.day_record().plan)
        )
        self.assertEqual(
            [i.text for i in service.day_record(yesterday).plan], []
        )

    def test_rollover_bar_offers_wizard(self):
        service = self._service()
        yesterday = date.today() - timedelta(days=1)
        service.add_plan_item(yesterday, "另一件没做完的事")
        page = build_today(service, on_refresh=_noop)
        self.assertIn(
            "昨日收尾向导", [_btn_text(b) for b in _walk_type(page, ft.TextButton)]
        )

    def test_wrapped_badge_when_check_or_act_present(self):
        service = self._service()
        yesterday = date.today() - timedelta(days=1)
        service.set_day_check(yesterday, "口径问题定位到数据源")
        page = build_today(service, on_refresh=_noop)
        self.assertIn("昨日已收尾 ✓", visible_texts(page))

    # -- 思考方式菜单 + 方向键选择 ---------------------------------------------

    def test_idea_rows_carry_thinking_menu(self):
        service = self._service()
        service.quick_capture("第一个想法")
        library = PromptLibrary()
        page = build_today(service, on_refresh=_noop, library=library)
        menus = [
            m
            for m in _walk_type(page, ft.PopupMenuButton)
            if getattr(m, "tooltip", "") == "点名思考方式"
        ]
        self.assertEqual(len(menus), 1, "每个待整理想法一行思考方式菜单")
        self.assertEqual(len(menus[0].items), len(library.thinking()))

    def test_archived_ideas_not_mixed_into_today(self):
        service = self._service()
        service.quick_capture("活着的想法")
        service.set_idea_status("idea-001", "archived")
        texts = visible_texts(build_today(service, on_refresh=_noop))
        self.assertNotIn("活着的想法", texts, "Today 只列待整理想法")

    def test_arrow_keys_move_idea_selection(self):
        from types import SimpleNamespace

        service = self._service()
        service.quick_capture("想法一")
        service.quick_capture("想法二")
        hub_page = SimpleNamespace(route=ROUTE_TODAY)
        hub = TodayHub(service, page=hub_page)
        hub.build()

        self.assertEqual(hub.selected_idea, 0)
        hub._on_key(SimpleNamespace(key="Arrow Down"))
        self.assertEqual(hub.selected_idea, 1)
        hub._on_key(SimpleNamespace(key="Arrow Down"))
        self.assertEqual(hub.selected_idea, 1, "选择应钳制不越界")
        hub._on_key(SimpleNamespace(key="Arrow Up"))
        hub._on_key(SimpleNamespace(key="Arrow Up"))
        self.assertEqual(hub.selected_idea, 0)

    # -- 草稿卡(三键) ----------------------------------------------------------

    def test_plan_suggest_makes_draft_card_with_three_keys(self):
        service = self._service()
        page = build_today(
            service,
            on_refresh=_noop,
            library=PromptLibrary(),
            runtime=FakePromptRuntime(),
        )
        suggest = next(
            b
            for b in _walk_type(page, ft.OutlinedButton)
            if _btn_text(b) == "生成整理建议"
        )
        before = len(service.day_record().plan)

        suggest.on_click(None)

        joined = "".join(visible_texts(page))
        self.assertIn("阶段 · 今日计划建议", joined, "草稿卡应出现在页面树中")
        for label in ("采纳", "改后采纳", "忽略"):
            self.assertIn(label, joined)
        adopt = next(
            b for b in _walk_type(page, ft.FilledButton) if _btn_text(b) == "采纳"
        )
        adopt.on_click(None)
        self.assertGreater(
            len(service.day_record().plan), before, "采纳应写入今日计划"
        )
        self.assertNotIn("阶段 · 今日计划建议", "".join(visible_texts(page)))

    def test_plan_suggest_without_ai_makes_no_card(self):
        service = self._service()
        page = build_today(service, on_refresh=_noop, library=None, runtime=None)
        suggest = next(
            b
            for b in _walk_type(page, ft.OutlinedButton)
            if _btn_text(b) == "生成整理建议"
        )
        suggest.on_click(None)
        self.assertNotIn("阶段 · 今日计划建议", "".join(visible_texts(page)))


class WrapupWizardContractTests(unittest.TestCase):
    """收尾向导:四步进度点,每步控件齐全;离线可构建。"""

    def _wizard(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        yesterday = date.today() - timedelta(days=1)
        service.add_plan_item(yesterday, "未完成的甲")
        service.toggle_plan_item(yesterday, "plan-001")  # 未完成的甲 → 已完成
        service.add_plan_item(yesterday, "未完成的乙")
        return WrapupWizard(None, service), service, yesterday

    def test_all_five_progress_points_exist(self):
        wizard, _service, _yesterday = self._wizard()
        wizard.render()
        texts = visible_texts(wizard.dialog)
        for step_label in STEPS:
            self.assertIn(step_label, texts)

    def test_step1_marks_then_step3_disposes(self):
        wizard, service, yesterday = self._wizard()
        wizard.render()
        wizard.goto(1)
        boxes = _walk_type(wizard.dialog, ft.Checkbox)
        self.assertEqual(len(boxes), 2)

        def mark(value):
            return type("E", (), {"control": type("C", (), {"value": value})()})()

        # 甲取消完成、乙补勾完成 → 第 3 步只剩甲待处置
        boxes[0].on_change(mark(False))
        boxes[1].on_change(mark(True))
        wizard._save_marks()
        record = service.day_record(yesterday)
        self.assertFalse(record.plan[0].done)
        self.assertTrue(record.plan[1].done)

        wizard.goto(3)
        segments = _walk_type(wizard.dialog, ft.SegmentedButton)
        self.assertEqual(len(segments), 1, "未完成的甲 应有今日再做/放弃处置")

    def test_step2_check_editor_and_step4_act_editor(self):
        wizard, _service, _yesterday = self._wizard()
        wizard.goto(2)
        editor = next(
            f for f in _walk_type(wizard.dialog, ft.TextField) if f.multiline
        )
        editor.value = "Check 一句"
        wizard._save_check()
        self.assertEqual(
            wizard.service.day_record(date.today() - timedelta(days=1)).check_note,
            "Check 一句",
        )

        wizard.goto(4)
        act = next(
            f for f in _walk_type(wizard.dialog, ft.TextField) if f.multiline
        )
        act.value = "Act 一句"
        wizard._finish(save_act=True)
        record = wizard.service.day_record(date.today() - timedelta(days=1))
        self.assertEqual(record.act_note, "Act 一句")

    def test_act_draft_prefills_carry_texts(self):
        wizard, _service, _yesterday = self._wizard()
        wizard.carry_texts = ["带走的调整"]
        wizard.goto(4)
        act = next(
            f for f in _walk_type(wizard.dialog, ft.TextField) if f.multiline
        )
        self.assertEqual(act.value, "明日优先:带走的调整")


class ProjectsHomeContractTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_home_shows_all_project_cards(self):
        service = self._service()
        opened = []
        page = build_projects_home(service, on_open_project=opened.append)

        texts = visible_texts(page)
        joined = "".join(texts)
        self.assertIn("项目", texts)
        self.assertIn("星图演示库", joined)
        self.assertIn("北风档案", joined)  # 第二个项目必须可见,不藏下拉里
        self.assertIn("共 2 个", joined)

        clickable = []
        for c in _walk_type(page, ft.Container):
            if c.on_click is not None:
                clickable.append(c)
        self.assertTrue(clickable, "项目卡片应可点击")
        for c in clickable:
            c.on_click(None)
        self.assertIn("proj-atlas", opened)
        self.assertIn("proj-boreas", opened)

    def test_create_button_opens_form_and_submits(self):
        service = self._service()
        created = []
        page = build_projects_home(
            service,
            on_open_project=_noop,
            on_refresh=_noop,
            on_create=lambda **fields: created.append(fields),
        )

        texts = visible_texts(page)
        self.assertIn("新建项目", "".join(texts))

        add_card = next(
            c
            for c in _walk_type(page, ft.Container)
            if c.on_click is not None and "新建项目" in visible_texts(c)
        )
        add_card.on_click(None)
        fields = _walk_type(page, ft.TextField)
        self.assertEqual(len(fields), 4, "表单应有名称/目标/焦点/负责人四个输入框")

        fields[0].value = "南风清单"
        fields[1].value = "整理清单"
        create_btn = next(
            b for b in _walk_type(page, ft.FilledButton) if _btn_text(b) == "创建"
        )
        create_btn.on_click(None)

        self.assertEqual(
            created,
            [{"name": "南风清单", "goal": "整理清单", "current_focus": "", "owner": ""}],
        )

    def test_blank_create_name_shows_error_and_creates_nothing(self):
        service = self._service()
        created = []
        page = build_projects_home(
            service,
            on_open_project=_noop,
            on_refresh=_noop,
            on_create=lambda **fields: created.append(fields),
        )

        add_card = next(
            c
            for c in _walk_type(page, ft.Container)
            if c.on_click is not None and "新建项目" in visible_texts(c)
        )
        add_card.on_click(None)
        create_btn = next(
            b for b in _walk_type(page, ft.FilledButton) if _btn_text(b) == "创建"
        )
        create_btn.on_click(None)

        self.assertEqual(created, [])
        error_texts = [
            t for t in visible_texts(page) if "项目名称不能为空" in t
        ]
        self.assertTrue(error_texts, "空名称应显示错误提示")

    def test_overview_has_back_to_home(self):
        service = self._service()
        called = []
        page = build_project_overview(
            service,
            "proj-atlas",
            on_open_node=_noop,
            on_refresh=_noop,
            on_back=lambda: called.append(True),
        )

        back = next(
            b
            for b in _walk_type(page, ft.TextButton)
            if _btn_text(b) == "‹ 全部项目"
        )
        back.on_click(None)
        self.assertTrue(called)


class ProjectMasterDetailContractTests(unittest.TestCase):
    """合并版项目页契约:master 列表切换、状态色块直改、任务勾选持久。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def test_master_lists_all_projects_and_switches_detail(self):
        service = self._service()
        page = build_project_overview(service, "proj-atlas", on_open_node=_noop)

        # master 卡是可点击 Container;详情区项目名是可双击编辑标签
        boreas_cards = [
            c
            for c in _walk_type(page, ft.Container)
            if c.on_click is not None and "北风档案" in visible_texts(c)
        ]
        self.assertTrue(boreas_cards, "master 列表应有北风档案紧凑卡")
        self.assertTrue(
            "停滞" in "".join(visible_texts(boreas_cards[0])),
            "停滞项目卡应带红标天数",
        )

        boreas_cards[0].on_click(None)
        self.assertTrue(
            _double_tap_targets(page, "北风档案"),
            "点击 master 卡后详情区应切换为北风档案(名称可编辑)",
        )

    def test_action_status_block_click_cycles_status(self):
        service = self._service()
        page = build_project_overview(service, "proj-atlas", on_open_node=_noop)
        action = next(
            a
            for a in service.project("proj-atlas").actions
            if a.title == "梳理星图目录结构"
        )
        before = action.status

        block = next(
            c
            for c in _walk_type(page, ft.Container)
            if getattr(c, "tooltip", "") == "点按切换状态"
            and visible_texts(c) == ["进行中"]
        )
        block.on_click(None)

        self.assertNotEqual(action.status, before, "点按色块应循环切换状态")
        self.assertEqual(action.status, "waiting", "进行中 → 下一个状态是等待")

    def test_today_task_checkbox_persists_to_service(self):
        service = self._service()
        page = build_project_overview(service, "proj-atlas", on_open_node=_noop)
        box = next(
            b
            for b in _walk_type(page, ft.Checkbox)
            if b.label == "梳理星图目录结构"
        )

        box.on_change(
            type("E", (), {"control": type("C", (), {"value": True})()})()
        )

        action = next(
            a
            for a in service.project("proj-atlas").actions
            if a.title == "梳理星图目录结构"
        )
        self.assertEqual(action.status, "completed", "勾选应直写服务,不回弹")

    def test_stalled_uses_red_semantic_color(self):
        service = self._service()
        page = build_project_overview(service, "proj-atlas", on_open_node=_noop)
        joined = "".join(visible_texts(page))
        self.assertIn("1 项停滞", joined, "master 卡显示停滞计数")
        self.assertIn("长期停滞", joined)
        self.assertIn("20 天未更新", joined, "停滞天数必须是真实差值")


class ProjectOverviewEditingContractTests(unittest.TestCase):
    def test_goal_label_click_submits_rename(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        page = build_project_overview(
            service, "proj-atlas", on_open_node=_noop, on_refresh=_noop
        )

        self.assertTrue(
            _edit_and_submit(
                page,
                "为工作台样片提供一套可整理的虚构资料库",
                "新目标:验证全页可编辑",
            )
        )
        self.assertEqual(
            service.project("proj-atlas").goal, "新目标:验证全页可编辑"
        )


class NodeDetailEditingContractTests(unittest.TestCase):
    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def _node(self, service, node_id="node-tests"):
        return next(
            n
            for n in service.project("proj-atlas").outline
            if n.node_id == node_id
        )

    def test_title_label_click_submits_rename(self):
        service = self._service()
        page = build_node_detail(
            service,
            "proj-atlas",
            "node-tests",
            on_back=_noop,
            on_open_node=_noop,
            on_refresh=_noop,
        )

        self.assertTrue(_edit_and_submit(page, "测试资源", "测试资源v2"))
        self.assertEqual(self._node(service).title, "测试资源v2")

    def test_note_editor_save_roundtrip(self):
        service = self._service()
        page = build_node_detail(
            service,
            "proj-atlas",
            "node-tests",
            on_back=_noop,
            on_open_node=_noop,
            on_refresh=_noop,
        )

        target = _double_tap_targets(page, "样片自检清单见测试目录")[0]
        target.on_double_tap(None)
        field = next(f for f in _walk_type(page, ft.TextField) if f.multiline)
        field.value = "新的节点备注"
        save = next(
            b for b in _walk_type(page, ft.FilledButton) if _btn_text(b) == "保存"
        )
        save.on_click(None)

        self.assertEqual(self._node(service).note, "新的节点备注")


class NodeResourceEditingContractTests(unittest.TestCase):
    """节点相关资源:名称可点改、加号行添加、✕ 移除。"""

    def _service(self):
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    def _node(self, service, node_id="node-tests"):
        return next(
            n
            for n in service.project("proj-atlas").outline
            if n.node_id == node_id
        )

    def _page(self, service):
        return build_node_detail(
            service,
            "proj-atlas",
            "node-tests",
            on_back=_noop,
            on_open_node=_noop,
            on_refresh=_noop,
        )

    def test_resource_name_click_submits_rename(self):
        service = self._service()
        page = self._page(service)

        self.assertTrue(
            _edit_and_submit(page, "测试环境清单.xlsx", "测试环境清单v2.xlsx")
        )
        self.assertEqual(
            self._node(service).resources[0].name, "测试环境清单v2.xlsx"
        )

    def test_resource_source_click_submits_rename(self):
        service = self._service()
        page = self._page(service)
        needle = "演示链接:https://wiki.internal.example.net/atlas/tests"

        self.assertTrue(_edit_and_submit(page, needle, "演示链接:已更新"))
        self.assertEqual(
            self._node(service).resources[0].source, "演示链接:已更新"
        )

    def test_add_resource_row_submit_attaches_resource(self):
        service = self._service()
        page = self._page(service)

        add_btn = next(
            b for b in _walk_type(page, ft.TextButton) if "添加资源" in _btn_text(b)
        )
        add_btn.on_click(None)
        field = _walk_type(page, ft.TextField)[0]
        field.value = "接口说明.md"
        field.on_submit(None)

        self.assertTrue(
            any(
                r.name == "接口说明.md"
                for r in self._node(service).resources
            )
        )

    def test_resource_remove_button_detaches(self):
        service = self._service()
        page = self._page(service)
        before = [r.resource_id for r in self._node(service).resources]

        remove_btn = next(
            b
            for b in _walk_type(page, ft.IconButton)
            if (b.tooltip or "") == "移除该资源"
        )
        remove_btn.on_click(None)

        after = [r.resource_id for r in self._node(service).resources]
        self.assertEqual(len(after), len(before) - 1)
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
