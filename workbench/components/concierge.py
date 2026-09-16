"""草稿卡主控台:AI 面板里的阶段动作、思考方式点名与草稿卡队列。

原型 E「AI 主控台」的合并形态(2026-09-16 用户确认):右侧 AI 面板承载
草稿卡时间流,今天页的入口保留。与 TodayHub 共用同一套服务
(prompt_library + text_runtime),红线一致:AI 只产草稿,采纳(人工确认)
才落盘;AI 失败不出卡,只报错。
"""

from __future__ import annotations

from datetime import date, timedelta

import flet as ft

from workbench.components import FONT_SMALL, THEME, section_title
from workbench.components.feedback import error, tell
from workbench.domain.models import IDEA_PENDING
from workbench.runtime.text_runtime import generate_async
from workbench.services.capture_routing import parse_plan_lines
from workbench.services.prompt_library import PromptLibrary, projects_summary


def _safe_update(page) -> None:
    if page is not None:
        try:
            page.update()
        except Exception:
            pass


class ConciergeController:
    """主控台状态;library/runtime 由渲染方注入(main.render 每次传入)。"""

    def __init__(self, service, page=None):
        self.service = service
        self.page = page
        self.library: PromptLibrary | None = None
        self.runtime = None
        self.drafts_col = ft.Column(spacing=10)
        self.mode_key: str = ""
        self.target_key: str = ""
        self._ai_busy = False

    def set_providers(self, library, runtime) -> None:
        self.library = library
        self.runtime = runtime

    def preset_project(self, project_id: str) -> None:
        """从项目页打开面板时,思考方式目标预选为当前项目。"""

        if self.service.project(project_id) is not None:
            self.target_key = f"project:{project_id}"

    # --- AI 草稿统一入口(与 TodayHub._run_stage 同契约) ----------------------

    def _run_stage(self, card_title, namespace, key, variables, adopt, fail_message="AI 不可用,本次未生成草稿"):
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

    def _add_draft_card(self, title: str, body: str, on_adopt) -> None:
        """草稿卡三键:采纳 / 改后采纳 / 忽略;采纳与忽略后卡片离场。"""

        card_box = ft.Container(
            bgcolor=THEME["card"],
            border=ft.Border.all(1, THEME["border"]),
            border_radius=12,
            padding=12,
        )

        def dismiss():
            if card_box in self.drafts_col.controls:
                self.drafts_col.controls.remove(card_box)
            _safe_update(self.page)

        def adopt_click(_e=None):
            message = on_adopt(body)
            dismiss()
            tell(self.page, message)

        def adopt_via_editor(_e=None):
            if self.page is None:
                return
            editor = ft.TextField(
                value=body, multiline=True, min_lines=6, max_lines=14,
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
                    content=ft.Container(editor, width=520),
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
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=13, color=THEME["purple"]),
                        ft.Text(title, size=FONT_SMALL, color=THEME["text_sub"]),
                    ],
                    spacing=6,
                ),
                ft.Container(
                    ft.Text(body, size=12, selectable=True),
                    bgcolor=THEME["dot_empty"],
                    border_radius=8,
                    padding=8,
                ),
                ft.Row(
                    [
                        ft.FilledButton("采纳", on_click=adopt_click),
                        ft.TextButton("改后采纳", on_click=adopt_via_editor),
                        ft.TextButton("忽略", on_click=lambda _e: (dismiss(), tell(self.page, "已忽略草稿"))),
                    ],
                    spacing=6,
                ),
            ],
            spacing=8,
        )
        self.drafts_col.controls.insert(0, card_box)
        _safe_update(self.page)

    # --- 阶段动作 -------------------------------------------------------------

    def stage_plan_suggest(self, _e=None):
        today = date.today()
        yesterday = today - timedelta(days=1)

        def adopt(body: str) -> str:
            count = 0
            for line, project_id in parse_plan_lines(body):
                self.service.add_plan_item(today, line, project_id)
                count += 1
            return f"已采纳 {count} 条进入今日计划"

        self._run_stage(
            "阶段 · 今日计划建议",
            "stages",
            "plan_suggest",
            {
                "yesterday_unfinished": "\n".join(
                    f"{'[已完成]' if i.done else '[未完成]'} {i.text}"
                    for i in self.service.day_record(yesterday).plan
                ) or "(无)",
                "pending_ideas": "\n".join(
                    i.text
                    for i in self.service.ideas()
                    if i.status == IDEA_PENDING
                ) or "(无)",
                "project_brief": projects_summary(self.service),
            },
            adopt,
        )

    def stage_day_check(self, _e=None):
        record = self.service.day_record(date.today())

        def adopt(body: str) -> str:
            self.service.set_day_check(date.today(), body.strip())
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

    def stage_weekly(self, _e=None):
        today = date.today()
        week_ago = today - timedelta(days=7)
        activity = [
            e for e in self.service.activity()
            if e.occurred_at >= week_ago and e.kind != "page_viewed"
        ]

        def adopt(body: str) -> str:
            record = self.service.day_record(today)
            self.service.set_worklog(
                today,
                (record.worklog + "\n\n## 周复盘\n\n" + body.strip()).strip(),
            )
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
                    f"{a.title}({(today - a.last_meaningful_update_at).days} 天)"
                    for a in self.service.stalled_actions()
                ) or "(无停滞)",
                "project_brief": projects_summary(self.service),
            },
            adopt,
        )

    # --- 思考方式点名 ----------------------------------------------------------

    def _targets(self) -> list[tuple[str, str, str]]:
        """候选目标 (dropdown key, 显示名, kind:id)。"""

        options: list[tuple[str, str, str]] = []
        for idea in self.service.ideas():
            if idea.status == IDEA_PENDING:
                options.append((f"idea:{idea.idea_id}", f"想法:{idea.text[:14]}", f"idea:{idea.idea_id}"))
        for project in self.service.projects():
            options.append((f"project:{project.project_id}", f"项目:{project.name}", f"project:{project.project_id}"))
        for item in self.service.day_record(date.today()).plan:
            options.append((f"plan:{item.item_id}", f"计划:{item.text[:14]}", f"plan:{item.item_id}"))
        return options

    def _target_text(self, kind_and_id: str) -> str:
        kind, _, target_id = kind_and_id.partition(":")
        if kind == "idea":
            return next((i.text for i in self.service.ideas() if i.idea_id == target_id), "")
        if kind == "project":
            project = self.service.project(target_id)
            if project is None:
                return ""
            actions = ";".join(
                a.title
                for a in project.actions
                if a.status in ("pending", "in_progress", "waiting")
            )
            return f"{project.name}|目标:{project.goal}|焦点:{project.current_focus}|行动:{actions}"
        item = next(
            (i for i in self.service.day_record(date.today()).plan if i.item_id == target_id),
            None,
        )
        return item.text if item else ""

    def run_thinking(self, _e=None):
        if not self.mode_key or not self.target_key:
            tell(self.page, "先选思考方式和目标")
            return
        spec = self.library.get("thinking", self.mode_key)
        target_kind = "想法" if self.target_key.startswith("idea:") else (
            "项目" if self.target_key.startswith("project:") else "计划"
        )

        def adopt(body: str) -> str:
            first = next((ln for ln in body.splitlines() if ln.strip()), body[:40])
            self.service.add_plan_item(date.today(), first.lstrip("0123456789.、- "))
            return "已把第一条采纳为今日计划"

        self._run_stage(
            f"思考 · {spec.title}",
            "thinking",
            self.mode_key,
            {
                "target_kind": target_kind,
                "target_text": self._target_text(self.target_key),
                "project_brief": projects_summary(self.service),
            },
            adopt,
            fail_message="AI 不可用,已跳过本次点名",
        )

    # --- 面板区块 -------------------------------------------------------------

    def sections(self) -> ft.Control:
        """主控台区块:阶段动作 + 思考方式点名 + 草稿卡队列。"""

        modes = [(s.title, s.key) for s in self.library.thinking()] if self.library else []
        targets = self._targets()

        def _action_button(label, handler):
            return ft.OutlinedButton(
                label,
                on_click=handler,
                style=ft.ButtonStyle(
                    color=THEME["purple_deep"],
                    side=ft.BorderSide(1, THEME["border"]),
                    padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                ),
            )

        mode_dd = ft.Dropdown(
            value=self.mode_key or None,
            hint_text="思考方式",
            options=[ft.dropdown.Option(key, title) for title, key in modes],
            on_select=lambda e: setattr(self, "mode_key", e.control.value or ""),
            text_size=12,
            content_padding=ft.Padding(left=8, top=2, right=8, bottom=2),
        )
        target_dd = ft.Dropdown(
            value=self.target_key or None,
            hint_text="点名目标(想法/项目/计划)",
            options=[ft.dropdown.Option(key, name) for key, name, _k in targets],
            on_select=lambda e: setattr(self, "target_key", e.control.value or ""),
            text_size=12,
            content_padding=ft.Padding(left=8, top=2, right=8, bottom=2),
        )

        return ft.Column(
            [
                ft.Container(height=6),
                ft.Divider(color=THEME["border"], height=1),
                section_title("阶段动作"),
                ft.Row(
                    [
                        _action_button("今日计划建议", self.stage_plan_suggest),
                        _action_button("Check 引导", self.stage_day_check),
                        _action_button("本周复盘", self.stage_weekly),
                    ],
                    wrap=True,
                    spacing=6,
                    run_spacing=6,
                ),
                section_title("思考方式点名"),
                mode_dd,
                target_dd,
                ft.Row(
                    [
                        ft.FilledButton(
                            "点名运行",
                            icon=ft.Icons.PSYCHOLOGY_ALT,
                            bgcolor=THEME["purple"],
                            color=ft.Colors.WHITE,
                            on_click=self.run_thinking,
                        ),
                    ]
                ),
                section_title("草稿卡", trailing=ft.Text("采纳才落盘", size=FONT_SMALL, color=THEME["text_faint"])),
                self.drafts_col,
            ],
            spacing=8,
        )
