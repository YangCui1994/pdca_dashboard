"""昨日收尾向导(原型 C 收编):AlertDialog 四步+进度点,每步只问一件事。

步骤:①开始 → ②勾昨日完成 → ③Check 引导(AI 草稿可改可跳)→
④未完成逐条处置(今日再做/放弃)→ ⑤写 Act 完成收尾。
Check/Act 落 DayRecord(days/<日期>.md 镜像由 storage 层负责);
「放弃」处置走整批可撤销 snackbar。完成后回调 on_finish 回今天页。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import flet as ft

from workbench.components import FONT_SMALL, THEME
from workbench.components.feedback import error, tell, undo_snackbar
from workbench.runtime.text_runtime import generate_async
from workbench.services.prompt_library import PromptLibrary
from workbench.services.workspace_service import WorkspaceService
from workbench.services.wrapup import act_draft, apply_marks, carry_items, plan_summary

if TYPE_CHECKING:
    from workbench.runtime.text_runtime import FakePromptRuntime

STEPS = ("开始", "勾完成", "写 Check", "清未完成", "写 Act")


class WrapupWizard:
    """一个实例对应一次向导会话;show() 弹出,完成后自动关闭。"""

    def __init__(
        self,
        page: ft.Page,
        service: WorkspaceService,
        library: PromptLibrary | None = None,
        runtime: "FakePromptRuntime | None" = None,
        on_finish=None,
        target_day: date | None = None,
    ):
        self.page = page
        self.service = service
        self.library = library
        self.runtime = runtime
        self.on_finish = on_finish
        self.day = target_day or (date.today() - timedelta(days=1))
        self.step = 0
        self.marks: dict[str, bool] = {}
        self.carry_texts: list[str] = []
        self.check_text = ""
        self._gen_busy = False
        self.body = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO)
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("昨日收尾", size=16, weight=ft.FontWeight.W_700),
            content=ft.Container(self.body, width=560, height=430),
        )

    # -- 生命周期 -----------------------------------------------------------

    def show(self):
        self.page.show_dialog(self.dialog)
        self.render()

    def _close(self):
        if self.page is not None:
            self.page.pop_dialog()
        if self.on_finish is not None:
            self.on_finish()

    def goto(self, step: int):
        self.step = step
        self.render()

    def render(self):
        steps = (self.step_start, self.step_marks, self.step_check,
                 self.step_undone, self.step_act)
        self.body.controls = [self._progress_dots(), ft.Divider(), steps[self.step]()]
        try:
            self.page.update()
        except Exception:
            pass

    def _progress_dots(self) -> ft.Row:
        items = []
        for idx, name in enumerate(STEPS):
            done = idx < self.step
            current = idx == self.step
            items.append(
                ft.Container(
                    ft.Text(
                        name,
                        size=11,
                        color=ft.Colors.WHITE if current or done else THEME["text_sub"],
                    ),
                    bgcolor=THEME["purple"] if current else (
                        THEME["green"] if done else THEME["dot_empty"]
                    ),
                    border_radius=10,
                    padding=ft.Padding(left=10, right=10, top=3, bottom=3),
                )
            )
        return ft.Row(items, spacing=6)

    # -- 步骤 0:开始 ---------------------------------------------------------

    def step_start(self):
        undone = len([i for i in self.service.day_record(self.day).plan if not i.done])
        return ft.Column(
            [
                ft.Text(
                    f"{self.day.isoformat()} 的计划有 {undone} 项未完成。"
                    "花两分钟收个尾,今天才有干净的起点。"
                ),
                ft.Row(
                    [
                        ft.FilledButton("开始收尾", on_click=lambda _e: self.goto(1)),
                        ft.TextButton("跳过,直接看今天", on_click=lambda _e: self._close()),
                    ]
                ),
            ],
            spacing=12,
        )

    # -- 步骤 1:勾完成 -------------------------------------------------------

    def step_marks(self):
        record = self.service.day_record(self.day)
        rows = []
        for item in record.plan:
            checked = self.marks.get(item.item_id, item.done)
            project = self.service.project(item.project_id) if item.project_id else None
            rows.append(
                ft.Checkbox(
                    label=item.text + (f"  ·  {project.name}" if project else ""),
                    value=checked,
                    on_change=self._mark_changed(item.item_id),
                )
            )
        return ft.Column(
            [
                ft.Text("昨天完成了哪些?(勾选,和实际不符直接改)", weight=ft.FontWeight.W_700),
                ft.Column(rows, spacing=4),
                ft.FilledButton("下一步:写 Check", on_click=lambda _e: self._save_marks()),
            ],
            spacing=12,
        )

    def _mark_changed(self, item_id: str):
        def handler(e):
            self.marks[item_id] = e.control.value

        return handler

    def _save_marks(self):
        apply_marks(self.service, self.day, self.marks)
        self.goto(2)

    # -- 步骤 2:Check --------------------------------------------------------

    def step_check(self):
        record = self.service.day_record(self.day)
        self.check_editor = ft.TextField(
            value=record.check_note or "",
            hint_text="点「生成 Check 草稿」,或直接写;Enter 提交,Shift+Enter 换行",
            multiline=True,
            min_lines=4,
            max_lines=8,
            shift_enter=True,
        )
        return ft.Column(
            [
                ft.Text("Check:昨天的实际情况说明了一句什么?", weight=ft.FontWeight.W_700),
                ft.Container(
                    ft.Text(plan_summary(record), size=FONT_SMALL, color=THEME["text_sub"]),
                    bgcolor=THEME["dot_empty"],
                    padding=10,
                    border_radius=8,
                ),
                ft.FilledTonalButton(
                    "生成 Check 草稿(AI,可改可跳)",
                    on_click=lambda _e: self._gen_check(),
                ),
                self.check_editor,
                ft.Row(
                    [
                        ft.FilledButton("保存 Check,下一步", on_click=lambda _e: self._save_check()),
                        ft.TextButton("跳过 Check", on_click=lambda _e: self.goto(3)),
                    ]
                ),
            ],
            spacing=10,
        )

    def _gen_check(self):
        if self.library is None or self.runtime is None:
            error(self.page, "AI 未接入,自己写也完全可以")
            return
        if self._gen_busy:
            tell(self.page, "AI 正在生成,请稍候")
            return
        spec = self.library.get("stages", "day_check")
        record = self.service.day_record(self.day)
        rendered = spec.render(
            plan_summary=plan_summary(record),
            worklog=record.worklog or "(无记录)",
        )
        self._gen_busy = True

        def on_done(text):
            self._gen_busy = False
            self.check_editor.value = text
            try:
                self.page.update()
            except Exception:
                pass

        def on_error():
            self._gen_busy = False
            error(self.page, "AI 不可用,自己写也完全可以")

        tell(self.page, "AI 生成中…")
        generate_async(self.page, self.runtime, spec, rendered, on_done=on_done, on_error=on_error)

    def _save_check(self):
        text = (self.check_editor.value or "").strip()
        if text:
            self.service.set_day_check(self.day, text)
            tell(self.page, "Check 已保存")
        self.check_text = text
        self.goto(3)

    # -- 步骤 3:清未完成 ------------------------------------------------------

    def step_undone(self):
        undone = [i for i in self.service.day_record(self.day).plan if not i.done]
        if not undone:
            self.undone_ids = []
            return ft.Column(
                [
                    ft.Text("昨天没有未完成项,干净。"),
                    ft.FilledButton("下一步:写 Act", on_click=lambda _e: self.goto(4)),
                ],
                spacing=12,
            )
        self.undone_ids = [i.item_id for i in undone]
        self.carry_flags = {i.item_id: True for i in undone}
        rows = []
        for item in undone:
            rows.append(
                ft.Row(
                    [
                        ft.Text(item.text, expand=True),
                        ft.SegmentedButton(
                            selected={"carry"} if self.carry_flags[item.item_id] else {"drop"},
                            segments=[
                                ft.Segment(value="carry", label=ft.Text("今日再做")),
                                ft.Segment(value="drop", label=ft.Text("放弃")),
                            ],
                            on_change=self._carry_choice(item.item_id),
                        ),
                    ]
                )
            )
        return ft.Column(
            [
                ft.Text("未完成项,逐条决定去向", weight=ft.FontWeight.W_700),
                ft.Column(rows, spacing=8),
                ft.FilledButton("下一步:写 Act", on_click=lambda _e: self._dispose()),
            ],
            spacing=12,
        )

    def _carry_choice(self, item_id: str):
        def handler(e):
            self.carry_flags[item_id] = "carry" in e.control.selected

        return handler

    def _dispose(self):
        carry_ids = [i for i in self.undone_ids if self.carry_flags[i]]
        drop_ids = [i for i in self.undone_ids if not self.carry_flags[i]]
        _dropped, carried, removed_carry = carry_items(self.service, self.day, carry_ids, "carry")
        dropped, _c2, removed_drop = carry_items(self.service, self.day, drop_ids, "drop")
        self.carry_texts = [i.text for i in removed_carry]
        tell(self.page, f"{carried} 项移入今天,{dropped} 项已清理")

        removed_all = list(removed_carry) + list(removed_drop)

        def undo(_e):
            for item in removed_all:
                self.service.add_plan_item(self.day, item.text, item.project_id)
            today = date.today()
            for item in removed_carry:
                match = next(
                    (i.item_id for i in self.service.day_record(today).plan if i.text == item.text),
                    None,
                )
                if match:
                    self.service.remove_plan_item(today, match)
            tell(self.page, "已撤回昨天的处置")
            self.goto(3)

        undo_snackbar(self.page, f"已处置 {carried + dropped} 项", "撤销", undo)
        self.goto(4)

    # -- 步骤 4:Act -----------------------------------------------------------

    def step_act(self):
        self.act_editor = ft.TextField(
            value=act_draft(self.carry_texts, self.check_text),
            hint_text="Act:今天要带走的调整(可改)",
            multiline=True,
            min_lines=3,
            max_lines=7,
            shift_enter=True,
        )
        return ft.Column(
            [
                ft.Text("Act:今天的计划已经生成,再带走一条调整", weight=ft.FontWeight.W_700),
                self.act_editor,
                ft.Row(
                    [
                        ft.FilledButton("保存 Act,完成收尾", on_click=lambda _e: self._finish(save_act=True)),
                        ft.TextButton("跳过 Act", on_click=lambda _e: self._finish(save_act=False)),
                    ]
                ),
            ],
            spacing=12,
        )

    def _finish(self, save_act: bool):
        if save_act:
            text = (self.act_editor.value or "").strip()
            if text:
                self.service.set_day_act(self.day, text)
                tell(self.page, "Act 已保存,收尾完成 ✓")
        else:
            tell(self.page, "收尾完成 ✓")
        self._close()


def open_wrapup_wizard(page, service, library=None, runtime=None, on_finish=None):
    """便捷入口:构造并弹出向导。"""

    WrapupWizard(page, service, library, runtime, on_finish=on_finish).show()
