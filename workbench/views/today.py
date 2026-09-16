"""Today 页 = TodayHub(原型 A「今日中枢」骨架 + C/E 的收尾与草稿卡)。

一页做完一天的事:捕获 → 计划勾选 → 工作记录,不切页。
- 智能捕获条(左栏顶部常驻):`!`→今日计划、`#项目名`→归属计划、
  纯文字→待整理想法;提交后清空+焦点回归+snackbar。
- 顺延条:昨日未完成 N 项 → [顺延到今天](整批可撤销)+
  [昨日收尾向导];昨日 check/act 任一非空显示「已收尾 ✓」。
- 计划卡:勾选/双击改名/@项目徽章/添加行;CLOSE 删除可撤销。
- 待整理想法:每行 [入今日][保留][归档][思考方式▾] 全鼠标;
  上下方向键移动选择高亮(无输入焦点时才生效)。
- 「整理今日上下文」卡:计划建议草稿/Check 引导/本周复盘,统一出
  草稿卡(三键:采纳/改后采纳/忽略);AI 失败不出卡,只报错。
- 页内变更局部刷新(refs 子树更新),不触发全局 render()。

红线:AI 只产草稿,采纳(人工确认)才写盘。
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import flet as ft

from workbench.components import (
    FONT_SMALL,
    FONT_TITLE,
    THEME,
    card,
    section_title,
)
from workbench.components.editable import (
    build_editable_markdown,
    build_editable_label,
)
from workbench.components.feedback import error, hint, tell, undo_snackbar
from workbench.components.navigation import ROUTE_TODAY
from workbench.components.wrapup_wizard import WrapupWizard
from workbench.domain.models import IDEA_PENDING
from workbench.runtime.text_runtime import generate_async
from workbench.services.capture_routing import parse_plan_lines, route_capture
from workbench.services.prompt_library import PromptLibrary, projects_summary
from workbench.services.workspace_service import WorkspaceService


def _safe_update(control) -> None:
    """Repaint when attached to a page; stay silent in off-page tests."""

    try:
        control.update()
    except Exception:
        pass


def _parse_project_mention(text: str, projects):
    """提取 "@项目名"(支持前缀匹配),返回 (去提及后的文本, project_id|None)。"""

    match = re.search(r"@(\S+)", text)
    if not match:
        return text, None
    token = match.group(1)
    for project in projects:
        if token in (project.project_id, project.name) or project.name.startswith(token):
            return text.replace(match.group(0), "", 1).strip(), project.project_id
    return text, None


def _project_name(projects, project_id):
    return next(
        (p.name for p in projects if p.project_id == project_id), None
    )


class TodayHub:
    """今天页的状态与局部刷新;正式状态仍只在 WorkspaceService。"""

    def __init__(
        self,
        service: WorkspaceService,
        on_refresh=None,
        page: ft.Page | None = None,
        library: PromptLibrary | None = None,
        runtime=None,
    ):
        self.service = service
        self.on_refresh = on_refresh
        self.page = page
        self.library = library
        self.runtime = runtime
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.selected_idea = 0
        self._ai_busy = False
        self.capture_field = ft.TextField(
            hint_text="随手记:#项目名 计划 / !直接计划 / 纯文字=想法(回车)",
            on_submit=self._on_capture_submit,
            border_radius=24,
            filled=True,
            expand=True,  # 横向占满(只在 Row 里安全;Column 里是纵向抢占)
            border_color=THEME["border"],
            focused_border_color=THEME["purple"],
            content_padding=ft.Padding(left=16, top=10, right=16, bottom=10),
            text_size=13,
        )
        self.plan_col = ft.Column(spacing=2)
        self.plan_count = ft.Text("", size=FONT_SMALL, color=THEME["text_sub"])
        self.ideas_count = ft.Text("", size=FONT_SMALL, color=THEME["text_faint"])
        self.plan_card = card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("今日计划", size=FONT_TITLE, weight=ft.FontWeight.W_600, color=THEME["text"]),
                            ft.Container(expand=True),
                            self.plan_count,
                        ]
                    ),
                    ft.Container(height=2),
                    self.plan_col,
                    self._plan_add_row(),
                ],
                spacing=0,
            )
        )
        self.ideas_col = ft.Column(spacing=4)
        self.ideas_card = card(
            ft.Column(
                [
                    section_title("待整理想法", self.ideas_count),
                    ft.Container(height=6),
                    self.ideas_col,
                ],
                spacing=4,
            )
        )
        self.rollover_bar = ft.Container(visible=False)
        self.drafts_col = ft.Column(spacing=10)
        self.worklog_card = card(
            ft.Column(
                [
                    section_title("工作记录"),
                    ft.Container(height=4),
                    build_editable_markdown(
                        self.service.day_record(self.today).worklog,
                        lambda text: self.service.set_worklog(self.today, text),
                        on_refresh=lambda: tell(self.page, "工作记录已保存"),
                        min_lines=8,
                        empty_hint="双击此处或点「编辑」写今天的工作记录",
                    ),
                ],
                spacing=0,
            )
        )

    # --- 反馈与刷新 ---------------------------------------------------------

    def _refresh_global(self):
        if self.on_refresh is not None:
            self.on_refresh()

    def _refresh_local(self):
        self._render_plan()
        self._render_ideas()
        self._render_rollover()
        _safe_update(self.plan_card)
        _safe_update(self.ideas_card)
        _safe_update(self.rollover_bar)

    # --- 智能捕获 ------------------------------------------------------------

    def _on_capture_submit(self, event):
        field = self.capture_field
        text = field.value or ""
        if not text.strip():
            return
        names = {p.name: p.project_id for p in self.service.projects()}
        kind, payload, project_id = route_capture(text, names)
        if not payload:
            error(self.page, "没有可记录的内容(#项目名 后面要跟正文)")
            return
        if kind == "plan":
            self.service.add_plan_item(self.today, payload, project_id)
            label = "已加入今日计划"
            name = _project_name(self.service.projects(), project_id)
            if name:
                label += f"({name})"
        else:
            self.service.quick_capture(payload)
            label = "已收进待整理想法"
        field.value = ""
        self._refresh_local()
        tell(self.page, label)
        if self.page is not None:
            field.focus()

    # --- 计划卡 ---------------------------------------------------------------

    def _toggle(self, item_id):
        def handler(_e=None):
            done = self.service.toggle_plan_item(self.today, item_id)
            tell(self.page, "已完成 ✓" if done else "已取消完成")
            self._refresh_local()

        return handler

    def _remove(self, item):
        def handler(_e=None):
            self.service.remove_plan_item(self.today, item.item_id)

            def undo(_undo_event):
                self.service.add_plan_item(self.today, item.text, item.project_id)
                self._refresh_local()

            undo_snackbar(self.page, f"已删除「{item.text[:20]}」", "撤销", undo)
            self._refresh_local()

        return handler

    def _set_project(self, item_id):
        def handler(project_id):
            self.service.set_plan_item_project(self.today, item_id, project_id)
            self._refresh_local()

        return handler

    def _render_plan(self):
        record = self.service.day_record(self.today)
        projects = self.service.projects()
        rows = []
        for item in record.plan:
            label = build_editable_label(
                item.text,
                lambda text, item_id=item.item_id: self.service.rename_plan_item(
                    self.today, item_id, text
                ),
                size=13,
            )
            remove_btn = ft.IconButton(
                ft.Icons.CLOSE,
                icon_size=13,
                icon_color=THEME["text_faint"],
                tooltip="删除该计划项(可撤销)",
                style=ft.ButtonStyle(padding=0),
                on_click=self._remove(item),
            )
            name = _project_name(projects, item.project_id)
            badge = ft.PopupMenuButton(
                content=ft.Container(
                    content=ft.Text(
                        f"@{name}" if name else "@其他",
                        size=FONT_SMALL,
                        color=THEME["purple_deep"] if name else THEME["text_faint"],
                    ),
                    bgcolor=THEME["purple_soft"] if name else THEME["dot_empty"],
                    border_radius=99,
                    padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                ),
                items=[
                    ft.PopupMenuItem(
                        content=f"@{p.name}",
                        on_click=lambda _e, pid=p.project_id, iid=item.item_id: self._set_project(iid)(pid),
                    )
                    for p in projects
                ]
                + [
                    ft.PopupMenuItem(
                        content="@其他",
                        on_click=lambda _e, iid=item.item_id: self._set_project(iid)(""),
                    )
                ],
            )
            rows.append(
                ft.Row(
                    [
                        ft.Checkbox(
                            value=item.done,
                            active_color=THEME["green"],
                            on_change=self._toggle(item.item_id),
                        ),
                        label,
                        badge,
                        remove_btn,
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        if not rows:
            rows = [
                hint("今天还没有计划,在顶部输入「!第一件事」或「#项目 计划」")
            ]
        self.plan_col.controls = rows
        done_count = sum(1 for item in record.plan if item.done)
        self.plan_count.value = f"{done_count}/{len(record.plan)}"

    def _plan_add_row(self) -> ft.Control:
        """带项目下拉的计划添加行;文本里 @项目名 优先于下拉选择。"""

        projects = self.service.projects()
        state = {"editing": False}
        box = ft.Container()

        def idle():
            return ft.TextButton(
                "添加计划项",
                icon=ft.Icons.ADD,
                style=ft.ButtonStyle(
                    color=THEME["text_sub"],
                    padding=ft.Padding(left=0, top=2, right=8, bottom=2),
                ),
                on_click=lambda _e: enter(),
            )

        def restore():
            state["editing"] = False
            box.content = idle()
            _safe_update(box)

        def commit(_e=None):
            if not state["editing"]:
                return
            text = (field.value or "").strip()
            restore()
            if not text:
                return
            cleaned, mentioned = _parse_project_mention(text, projects)
            project_id = mentioned if mentioned is not None else project_dd.value or ""
            self.service.add_plan_item(self.today, cleaned, project_id)
            tell(self.page, "已加入今日计划")
            self._refresh_local()

        def enter():
            if state["editing"]:
                return
            state["editing"] = True
            box.content = ft.Row(
                [
                    ft.Column(
                        [field],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        expand=True,
                    ),
                    project_dd,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            field.value = ""
            _safe_update(box)

        field = ft.TextField(
            hint_text="回车添加;支持 @项目名(如 @星图)",
            autofocus=True,
            text_size=13,
            border_color=THEME["border"],
            focused_border_color=THEME["purple"],
            content_padding=ft.Padding(left=8, top=6, right=8, bottom=6),
            on_submit=commit,
        )
        project_dd = ft.Dropdown(
            value="",
            width=170,
            dense=True,
            text_size=12,
            border_color=THEME["border"],
            content_padding=ft.Padding(left=8, top=6, right=8, bottom=6),
            options=[ft.dropdown.Option(key="", text="其他")]
            + [ft.dropdown.Option(key=p.project_id, text=p.name) for p in projects],
        )
        box.content = idle()
        return box

    # --- 顺延条 -----------------------------------------------------------------

    def _undone_from(self, day: date):
        return [i for i in self.service.day_record(day).plan if not i.done]

    def _yesterday_wrapped(self) -> bool:
        record = self.service.day_record(self.yesterday)
        return bool(record.check_note.strip() or record.act_note.strip())

    def _render_rollover(self):
        undone = self._undone_from(self.yesterday)
        wrapped = self._yesterday_wrapped()
        if not undone and not wrapped:
            self.rollover_bar.visible = False
            self.rollover_bar.content = None
            return
        items: list = [
            ft.Icon(ft.Icons.HISTORY, size=14, color=THEME["orange"]),
        ]
        if undone:
            items.append(
                ft.Text(
                    f"昨天还有 {len(undone)} 项没完成",
                    size=FONT_SMALL,
                    color=THEME["orange"],
                )
            )
            items.append(ft.TextButton("顺延到今天", on_click=self._rollover))
            items.append(ft.TextButton("昨日收尾向导", on_click=lambda _e: self._open_wizard()))
        if wrapped:
            items.append(
                ft.Container(
                    content=ft.Text("昨日已收尾 ✓", size=FONT_SMALL, color=THEME["green"]),
                    bgcolor=THEME["green_soft"],
                    border_radius=99,
                    padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                )
            )
        self.rollover_bar.visible = True
        self.rollover_bar.content = ft.Row(items, spacing=8)

    def _rollover(self, _e=None):
        undone = self._undone_from(self.yesterday)
        moved = []
        for item in undone:
            self.service.add_plan_item(self.today, item.text, item.project_id)
            self.service.remove_plan_item(self.yesterday, item.item_id)
            moved.append(item)

        def undo(_undo_event):
            for item in moved:
                match = next(
                    (
                        i.item_id
                        for i in self.service.day_record(self.today).plan
                        if i.text == item.text
                    ),
                    "",
                )
                if match:
                    self.service.remove_plan_item(self.today, match)
                self.service.add_plan_item(self.yesterday, item.text, item.project_id)
            self._refresh_local()

        undo_snackbar(self.page, f"已顺延 {len(moved)} 项到今天", "撤销", undo)
        self._refresh_local()

    def _open_wizard(self):
        if self.page is None:
            return
        WrapupWizard(
            self.page,
            self.service,
            self.library,
            self.runtime,
            on_finish=self._refresh_local,
            target_day=self.yesterday,
        ).show()

    # --- 待整理想法(touch once)+ 思考方式 -------------------------------------

    def _pending_ideas(self):
        return sorted(
            (i for i in self.service.ideas() if i.status == IDEA_PENDING),
            key=lambda i: i.created_at,
        )

    def _idea_action(self, idea, action: str):
        def handler(_e=None):
            if action == "plan":
                self.service.add_plan_item(self.today, idea.text)
                self.service.set_idea_status(idea.idea_id, "kept")
                tell(self.page, "已按原文加入今日计划")
            elif action in ("kept", "archived"):
                self.service.set_idea_status(idea.idea_id, action)
                tell(self.page, "已保留" if action == "kept" else "已归档")
            self.selected_idea = 0
            self._refresh_local()

        return handler

    def _thinking_menu(self, idea):
        modes = [(s.title, s.key) for s in self.library.thinking()] if self.library else []
        if not modes:
            return None
        return ft.PopupMenuButton(
            icon=ft.Icons.PSYCHOLOGY_ALT,
            tooltip="点名思考方式",
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(title),
                    on_click=lambda _e, key=key: self._run_thinking(idea, key),
                )
                for title, key in modes
            ],
        )

    def _run_thinking(self, idea, mode_key: str):
        spec = self.library.get("thinking", mode_key)

        def adopt(body: str) -> str:
            first = next((ln for ln in body.splitlines() if ln.strip()), body[:40])
            self.service.add_plan_item(self.today, first.lstrip("0123456789.、- "))
            self._refresh_local()
            return "已把第一条采纳为今日计划"

        self._run_stage(
            f"思考 · {spec.title}",
            "thinking",
            mode_key,
            {
                "target_kind": "想法",
                "target_text": idea.text,
                "project_brief": projects_summary(self.service),
            },
            adopt,
            fail_message="AI 不可用,已跳过;想法仍可手动处理",
        )

    def _render_ideas(self):
        pending = self._pending_ideas()
        if not pending:
            self.ideas_col.controls = [
                hint("没有待整理想法,在顶部输入框随手记一条")
            ]
        else:
            self.selected_idea = max(0, min(self.selected_idea, len(pending) - 1))
            rows = []
            for index, idea in enumerate(pending):
                selected = index == self.selected_idea
                thinking = self._thinking_menu(idea)
                actions = [
                    ft.TextButton("入今日", on_click=self._idea_action(idea, "plan")),
                    ft.TextButton("保留", on_click=self._idea_action(idea, "kept")),
                    ft.IconButton(
                        ft.Icons.ARCHIVE_OUTLINED,
                        icon_size=16,
                        tooltip="归档",
                        on_click=self._idea_action(idea, "archived"),
                    ),
                ]
                if thinking is not None:
                    actions.append(thinking)
                rows.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.LIGHTBULB_OUTLINED,
                                            size=14,
                                            color=THEME["purple"],
                                        ),
                                        ft.Text(
                                            idea.text, size=13, color=THEME["text"], expand=True
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                ft.Row(actions, spacing=0, wrap=True),
                            ],
                            spacing=2,
                        ),
                        bgcolor=THEME["purple_soft"] if selected else None,
                        border_radius=8,
                        padding=ft.Padding(left=6, top=4, right=6, bottom=4),
                    )
                )
            self.ideas_col.controls = rows
        self.ideas_count.value = f"{len(pending)} 条"

    def _on_key(self, event: ft.KeyboardEvent):
        """上下方向键移动想法选择高亮;输入框聚焦时 Flet 不派发页面键事件。"""

        if self.page is None:
            return
        route = getattr(self.page, "route", "") or ""
        if not route.startswith(ROUTE_TODAY):
            return
        if event.key == "Arrow Down":
            delta = 1
        elif event.key == "Arrow Up":
            delta = -1
        else:
            return
        count = len(self._pending_ideas())
        if not count:
            return
        self.selected_idea = max(0, min(count - 1, self.selected_idea + delta))
        self._render_ideas()
        _safe_update(self.ideas_card)

    # --- 整理今日上下文 + 草稿卡 ------------------------------------------------

    def _run_stage(
        self,
        card_title: str,
        namespace: str,
        key: str,
        variables: dict,
        adopt,
        fail_message: str = "AI 不可用,本次未生成草稿",
    ):
        """AI 草稿统一入口:异步生成,失败不出卡,只报错。"""

        if self.library is None or self.runtime is None:
            error(self.page, "AI 未接入,本次未生成草稿")
            return
        if self._ai_busy:
            tell(self.page, "AI 正在生成,请稍候")
            return
        spec = self.library.get(namespace, key)
        rendered = spec.render(**variables)
        self._ai_busy = True

        def on_done(text):
            self._ai_busy = False
            self._add_draft_card(card_title, text, adopt)

        def on_error():
            self._ai_busy = False
            error(self.page, fail_message)

        tell(self.page, "AI 生成中…")
        generate_async(self.page, self.runtime, spec, rendered, on_done=on_done, on_error=on_error)

    def _stage_plan_suggest(self, _e=None):
        def adopt(body: str) -> str:
            count = 0
            for line, project_id in parse_plan_lines(body):
                self.service.add_plan_item(self.today, line, project_id)
                count += 1
            self._refresh_local()
            return f"已采纳 {count} 条进入今日计划"

        self._run_stage(
            "阶段 · 今日计划建议",
            "stages",
            "plan_suggest",
            {
                "yesterday_unfinished": "\n".join(
                    f"{'[已完成]' if i.done else '[未完成]'} {i.text}"
                    for i in self.service.day_record(self.yesterday).plan
                ) or "(无)",
                "pending_ideas": "\n".join(
                    i.text for i in self._pending_ideas()
                ) or "(无)",
                "project_brief": projects_summary(self.service),
            },
            adopt,
        )

    def _stage_day_check(self, _e=None):
        record = self.service.day_record(self.today)

        def adopt(body: str) -> str:
            self.service.set_day_check(self.today, body.strip())
            self._refresh_local()
            return "Check 已写入今天"

        self._run_stage(
            "阶段 · Check 引导",
            "stages",
            "day_check",
            {
                "plan_summary": "\n".join(
                    f"{'[已完成]' if i.done else '[未完成]'} {i.text}" for i in record.plan
                ) or "(今天还没有计划)",
                "worklog": record.worklog or "(还没有工作记录)",
            },
            adopt,
        )

    def _stage_weekly(self, _e=None):
        week_ago = self.today - timedelta(days=7)
        activity = [
            e for e in self.service.activity()
            if e.occurred_at >= week_ago and e.kind != "page_viewed"
        ]

        def adopt(body: str) -> str:
            record = self.service.day_record(self.today)
            self.service.set_worklog(
                self.today,
                (record.worklog + "\n\n## 周复盘\n\n" + body.strip()).strip(),
            )
            self._refresh_local()
            return "周复盘已并入今日工作记录"

        self._run_stage(
            "阶段 · 本周复盘",
            "stages",
            "weekly_review",
            {
                "week_activity": "\n".join(
                    f"{e.occurred_at} {e.label}" for e in activity[-40:]
                ) or "(本周无活动)",
                "stalled_list": "\n".join(
                    f"{a.title}({(self.today - a.last_meaningful_update_at).days} 天)"
                    for a in self.service.stalled_actions()
                ) or "(无停滞)",
                "project_brief": projects_summary(self.service),
            },
            adopt,
        )

    def _add_draft_card(self, title: str, body: str, on_adopt) -> None:
        """草稿卡三键:采纳 / 改后采纳 / 忽略;采纳与忽略后卡片离场。"""

        card_box = ft.Container(
            bgcolor=THEME["card"],
            border=ft.Border.all(1, THEME["border"]),
            border_radius=12,
            padding=14,
        )

        def dismiss():
            if card_box in self.drafts_col.controls:
                self.drafts_col.controls.remove(card_box)
            _safe_update(self.drafts_col)

        def adopt_click(_e=None):
            message = on_adopt(body)
            dismiss()
            tell(self.page, message)

        def adopt_via_editor(_e=None):
            if self.page is None:
                return
            editor = ft.TextField(
                value=body, multiline=True, min_lines=8, max_lines=18,
                expand=True, shift_enter=True,
            )

            def confirm(_confirm_e):
                self.page.pop_dialog()
                message = on_adopt(editor.value)
                dismiss()
                tell(self.page, message)

            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text(f"改后采纳 · {title}", size=15),
                    content=ft.Container(editor, width=560),
                    actions=[
                        ft.TextButton("采纳修改稿", on_click=confirm, autofocus=True),
                        ft.TextButton("取消", on_click=lambda _e: self.page.pop_dialog()),
                    ],
                )
            )

        card_box.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color=THEME["purple"]),
                        ft.Text(title, size=FONT_SMALL, color=THEME["text_sub"]),
                    ],
                    spacing=6,
                ),
                ft.Container(
                    ft.Text(body, size=13, selectable=True),
                    bgcolor=THEME["dot_empty"],
                    border_radius=8,
                    padding=10,
                ),
                ft.Row(
                    [
                        ft.FilledButton("采纳", on_click=adopt_click),
                        ft.TextButton("改后采纳", on_click=adopt_via_editor),
                        ft.TextButton("忽略", on_click=lambda _e: (dismiss(), tell(self.page, "已忽略草稿"))),
                    ],
                    spacing=8,
                ),
            ],
            spacing=8,
        )
        self.drafts_col.controls.insert(0, card_box)
        _safe_update(self.drafts_col)

    def _context_card(self) -> ft.Control:
        return card(
            ft.Column(
                [
                    section_title("整理今日上下文"),
                    ft.Container(height=4),
                    ft.Text(
                        "把今天的勾选、记录和想法压缩成一段交接上下文,"
                        "供明天或下一个 Agent 会话接续。",
                        size=FONT_SMALL,
                        color=THEME["text_sub"],
                    ),
                    ft.Container(height=8),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "生成整理建议",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=self._stage_plan_suggest,
                            ),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.TextButton("Check 引导", on_click=self._stage_day_check),
                            ft.TextButton("本周复盘", on_click=self._stage_weekly),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=0,
            )
        )

    # --- 组装 ----------------------------------------------------------------

    def build(self) -> ft.Control:
        if self.page is not None:
            self.page.on_keyboard_event = self._on_key
        self._render_plan()
        self._render_ideas()
        self._render_rollover()
        return ft.Container(
            expand=True,
            padding=ft.Padding(left=22, top=18, right=22, bottom=18),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TODAY, size=20, color=THEME["purple"]),
                            ft.Text(
                                f"今天 · {self.today.isoformat()}",
                                size=20,
                                weight=ft.FontWeight.W_700,
                                color=THEME["text"],
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),
                    ft.Row([self.capture_field], spacing=0),  # Row 里 expand 才是横向占满
                    ft.Container(height=10),
                    self.rollover_bar,
                    ft.Container(height=4),
                    ft.Row(
                        [
                            ft.Container(
                                expand=True,
                                content=ft.Column(
                                    [
                                        self.plan_card,
                                        ft.Container(height=12),
                                        self.worklog_card,
                                        ft.Container(height=12),
                                    ],
                                    spacing=0,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                ),
                            ),
                            ft.Container(width=12),
                            ft.Container(
                                width=360,
                                content=ft.Column(
                                    [
                                        self.ideas_card,
                                        ft.Container(height=12),
                                        self._context_card(),
                                        self.drafts_col,
                                    ],
                                    spacing=0,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                            ),
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=0,
            ),
        )


def build_today(
    service: WorkspaceService,
    on_refresh=None,
    page: ft.Page | None = None,
    library: PromptLibrary | None = None,
    runtime=None,
) -> ft.Control:
    """组装 TodayHub;page/library/runtime 缺省时退化为纯静态构建(测试)。"""

    return TodayHub(service, on_refresh=on_refresh, page=page, library=library, runtime=runtime).build()
