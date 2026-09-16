"""版本 C「引导复盘」:借鉴日志类应用的引导式复盘。

交互哲学:
- 打开先收尾昨天,再看今天:每步只问一件事,顶部进度点(1/4…)。
- 步骤:①勾昨日完成情况 → ②AI 引导写 Check(可改可跳过)→
  ③未完成项逐条处置(今日再做/放弃)→ ④写 Act 并生成今日。
- Check/Act 落 DayRecord,同步 days/<日期>.md 的 ## Check / ## Act 段。
- 向导之后:今天视图带 ← → 日期切换,可回看/补写任何一天的 Check/Act
  (修复正式版 Today 写死 date.today() 的复盘断档)。

运行:python -m prototypes.c_review_wizard.app --vault prototypes/ux-2026-09/demo_vault
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

import flet as ft

from prototypes.uxbase.loader import PromptLibrary
from prototypes.uxbase.runtime import FakePromptRuntime, OpenAITextRuntime, collect_text
from prototypes.uxbase.seed_demo import DEFAULT_VAULT, projects_summary
from prototypes.uxbase.ui_kit import THEME, hint, tell, undo_snackbar
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import WorkspaceStorage

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "prompts"

STEPS = ("开始", "勾完成", "写 Check", "清未完成", "写 Act")


# --- 纯函数(冒烟测试覆盖) ---------------------------------------------------

def plan_summary(record) -> str:
    return "\n".join(f"{'[已完成]' if i.done else '[未完成]'} {i.text}" for i in record.plan)


def apply_marks(service: WorkspaceService, day: date, marks: dict[str, bool]) -> int:
    """把向导里的勾选落到昨日计划上;返回实际变更数。"""

    changed = 0
    for item in service.day_record(day).plan:
        wanted = marks.get(item.item_id, item.done)
        if wanted != item.done:
            service.toggle_plan_item(day, item.item_id)
            changed += 1
    return changed


def carry_items(service: WorkspaceService, day: date, item_ids: list[str], action: str) -> tuple[int, int, list]:
    """action="carry":未完成项移到今天;action="drop":放弃(从昨天移除,可整体撤销)。
    返回 (处理数, 移入今天的数, 被移除的原文列表)。"""

    today = date.today()
    carried = dropped = 0
    removed: list = []
    for item_id in item_ids:
        item = next((i for i in service.day_record(day).plan if i.item_id == item_id), None)
        if item is None:
            continue
        if action == "carry":
            service.add_plan_item(today, item.text, item.project_id)
            carried += 1
        service.remove_plan_item(day, item_id)
        removed.append(item)
        dropped += 1
    return dropped, carried, removed


def act_draft(carry_texts: list[str], check_text: str) -> str:
    """Act 草稿:今天要做的事 + Check 里点名的调整,供编辑。"""

    lines = [f"明日优先:{text}" for text in carry_texts]
    if check_text:
        lines.append(f"调整:{check_text}")
    return "\n".join(lines) if lines else ""


# --- UI ----------------------------------------------------------------------

class ReviewWizard:
    def __init__(self, page: ft.Page, service: WorkspaceService, library: PromptLibrary, runtime):
        self.page = page
        self.service = service
        self.library = library
        self.runtime = runtime
        self.today = date.today()
        self.yesterday = date.today() - timedelta(days=1)
        self.step = 0
        self.marks: dict[str, bool] = {}
        self.carry_texts: list[str] = []
        self.body = ft.Column(spacing=14, expand=True, scroll=ft.ScrollMode.AUTO)
        self.wizard_open = True

    # -- 步骤渲染 -----------------------------------------------------------

    def progress_dots(self) -> ft.Row:
        items = []
        for idx, name in enumerate(STEPS):
            done = idx < self.step
            current = idx == self.step
            items.append(
                ft.Container(
                    ft.Text(name, size=11, color=ft.Colors.WHITE if current or done else THEME["muted"]),
                    bgcolor=THEME["accent"] if current else (THEME["ok"] if done else THEME["line"]),
                    border_radius=10,
                    padding=ft.Padding.only(left=10, right=10, top=3, bottom=3),
                )
            )
        return ft.Row(items, spacing=6)

    def render(self):
        handlers = [self.step0, self.step1, self.step2, self.step3, self.step4]
        self.body.controls = [self.progress_dots(), ft.Divider(), handlers[self.step]()]
        self.page.update()

    def step0(self):
        undone = len([i for i in self.service.day_record(self.yesterday).plan if not i.done])
        return ft.Column(
            [
                ft.Text("昨日收尾", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"{self.yesterday.strftime('%Y-%m-%d')} 的计划有 {undone} 项未完成。花两分钟收个尾,今天才有干净的起点。"),
                ft.Row(
                    [
                        ft.FilledButton("开始收尾", on_click=lambda e: self.goto(1)),
                        ft.TextButton("跳过,直接看今天", on_click=lambda e: self.finish()),
                    ]
                ),
            ],
            spacing=12,
        )

    def step1(self):
        record = self.service.day_record(self.yesterday)
        rows = []
        for item in record.plan:
            checked = self.marks.get(item.item_id, item.done)
            rows.append(
                ft.Checkbox(
                    label=item.text + ("" if item.project_id == "" else f"  ·  {self.service.project(item.project_id).name if self.service.project(item.project_id) else ''}"),
                    value=checked,
                    on_change=self.make_mark(item.item_id),
                )
            )
        return ft.Column(
            [
                ft.Text("昨天完成了哪些?(勾选,和实际不符直接改)", weight=ft.FontWeight.BOLD),
                ft.Column(rows, spacing=4),
                ft.Row([ft.FilledButton("下一步:写 Check", on_click=lambda e: self.save_marks())]),
            ],
            spacing=12,
        )

    def make_mark(self, item_id: str):
        def handler(event):
            self.marks[item_id] = event.control.value

        return handler

    def save_marks(self):
        apply_marks(self.service, self.yesterday, self.marks)
        self.goto(2)

    def step2(self):
        record = self.service.day_record(self.yesterday)
        self.check_editor = ft.TextField(
            value=self.service.day_record(self.yesterday).check_note or "",
            hint_text="点「生成 Check 草稿」,或直接写;Enter 提交,Shift+Enter 换行",
            multiline=True, min_lines=5, max_lines=10, shift_enter=True,
        )
        return ft.Column(
            [
                ft.Text("Check:昨天的实际情况说明了一句什么?", weight=ft.FontWeight.BOLD),
                ft.Container(
                    ft.Text(plan_summary(record), size=12, color=THEME["muted"]),
                    bgcolor="#f2f1ee", padding=10, border_radius=8,
                ),
                ft.Row(
                    [
                        ft.FilledTonalButton("生成 Check 草稿(AI,可改可跳过)", on_click=lambda e: self.gen_check()),
                        ft.Text("或自己写 ↓", size=12, color=THEME["muted"]),
                    ]
                ),
                self.check_editor,
                ft.Row(
                    [
                        ft.FilledButton("保存 Check,下一步", on_click=lambda e: self.save_check()),
                        ft.TextButton("跳过 Check", on_click=lambda e: self.goto(3)),
                    ]
                ),
            ],
            spacing=10,
        )

    def gen_check(self):
        spec = self.library.get("stages", "day_check")
        record = self.service.day_record(self.yesterday)
        rendered = spec.render(plan_summary=plan_summary(record), worklog=record.worklog or "(无记录)")
        text, trace = collect_text(self.runtime.complete(spec, rendered))
        if text:
            self.check_editor.value = text
            self.page.update()
        else:
            tell(self.page, "AI 不可用,自己写也完全可以")

    def save_check(self):
        text = self.check_editor.value or ""
        if text.strip():
            self.service.set_day_check(self.yesterday, text.strip())
            tell(self.page, "Check 已保存")
        self.check_text = text.strip()
        self.goto(3)

    def step3(self):
        undone = [i for i in self.service.day_record(self.yesterday).plan if not i.done]
        if not undone:
            self.undone_ids = []
            return ft.Column(
                [
                    ft.Text("清未完成", weight=ft.FontWeight.BOLD),
                    ft.Text("昨天没有未完成项,干净。"),
                    ft.FilledButton("下一步:写 Act", on_click=lambda e: self.goto(4)),
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
                            on_change=self.make_carry_choice(item.item_id),
                        ),
                    ]
                )
            )
        return ft.Column(
            [
                ft.Text("未完成项,逐条决定去向", weight=ft.FontWeight.BOLD),
                ft.Column(rows, spacing=8),
                ft.FilledButton("下一步:写 Act", on_click=lambda e: self.save_step3()),
            ],
            spacing=12,
        )

    def make_carry_choice(self, item_id: str):
        def handler(event):
            self.carry_flags[item_id] = "carry" in event.control.selected

        return handler

    def save_step3(self):
        carry_ids = [i for i in self.undone_ids if self.carry_flags[i]]
        drop_ids = [i for i in self.undone_ids if not self.carry_flags[i]]
        dropped, carried, removed_carry = carry_items(self.service, self.yesterday, carry_ids, "carry")
        dropped2, _, removed_drop = carry_items(self.service, self.yesterday, drop_ids, "drop")
        self.carry_texts = [i.text for i in removed_carry]
        tell(self.page, f"{carried} 项移入今天,{dropped + dropped2} 项已清理")

        def undo(undo_event):  # 整批撤回昨天
            for item in removed_carry:
                done_today = next(
                    (i.item_id for i in self.service.day_record(self.today).plan if i.text == item.text), None)
                if done_today:
                    self.service.remove_plan_item(self.today, done_today)
                self.service.add_plan_item(self.yesterday, item.text, item.project_id)
            for item in removed_drop:
                self.service.add_plan_item(self.yesterday, item.text, item.project_id)
            tell(self.page, "已撤回昨天的处置")
            self.goto(3)

        undo_snackbar(self.page, f"已处置 {dropped + dropped2} 项", "撤销", undo)
        self.goto(4)

    def step4(self):
        self.act_editor = ft.TextField(
            value=act_draft(self.carry_texts, getattr(self, "check_text", "")),
            hint_text="Act:明天要带走的调整(可改)",
            multiline=True, min_lines=4, max_lines=8, shift_enter=True,
        )
        return ft.Column(
            [
                ft.Text("Act:今天的计划已经生成,再带走一条调整", weight=ft.FontWeight.BOLD),
                self.act_editor,
                ft.Row(
                    [
                        ft.FilledButton("保存 Act,完成收尾", on_click=lambda e: self.finish()),
                        ft.TextButton("跳过 Act", on_click=lambda e: self.finish(save_act=False)),
                    ]
                ),
            ],
            spacing=12,
        )

    def finish(self, save_act: bool = True, event=None):
        if save_act and hasattr(self, "act_editor") and (self.act_editor.value or "").strip():
            self.service.set_day_act(self.yesterday, self.act_editor.value.strip())
            tell(self.page, "Act 已保存")
        self.wizard_open = False
        self.goto_today()

    def goto(self, step: int):
        self.step = step
        self.render()

    # -- 今天视图(日期可切,补写任何一天的 Check/Act) ----------------------

    def goto_today(self):
        self.view_date = self.today
        self.build_today_view()

    def build_today_view(self):
        record = self.service.day_record(self.view_date)
        plan_col = ft.Column(spacing=4)
        for item in record.plan:
            plan_col.controls.append(
                ft.Row(
                    [
                        ft.Checkbox(value=item.done, on_change=self.make_toggle(item.item_id)),
                        ft.Text(item.text, expand=True),
                    ]
                )
            )
        if not plan_col.controls:
            plan_col.controls.append(hint("这天没有计划;按 ! 添加"))
        add_box = ft.TextField(hint_text="! 加一条计划,回车提交", on_submit=self.make_add_plan(), expand=True)
        check_box = ft.TextField(
            label="Check(失焦即存)", multiline=True, min_lines=2, max_lines=5, shift_enter=True,
            value=record.check_note, on_blur=self.make_save_note("check"), on_submit=self.make_save_note("check"),
        )
        act_box = ft.TextField(
            label="Act(失焦即存)", multiline=True, min_lines=2, max_lines=5, shift_enter=True,
            value=record.act_note, on_blur=self.make_save_note("act"), on_submit=self.make_save_note("act"),
        )
        self.today_body.controls = [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self.shift_day(-1), tooltip="前一天"),
                    ft.Text(self.view_date.strftime("%Y-%m-%d %a"), size=18, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self.shift_day(1), tooltip="后一天"),
                    ft.Container(expand=True),
                    ft.FilledTonalButton("生成本周复盘(AI 草稿)", on_click=self.gen_weekly),
                ]
            ),
            ft.Row([plan_col, ft.VerticalDivider(width=1), add_box], spacing=14,
                   cross_axis_alignment=ft.CrossAxisAlignment.START),
            check_box,
            act_box,
        ]
        self.page.update()

    def shift_day(self, delta: int):
        self.view_date = self.view_date + timedelta(days=delta)
        self.build_today_view()

    def make_toggle(self, item_id: str):
        def handler(event):
            self.service.toggle_plan_item(self.view_date, item_id)
            tell(self.page, "已更新")
            self.build_today_view()

        return handler

    def make_add_plan(self):
        def handler(event):
            text = (event.control.value or "").strip()
            if text.startswith("!"):
                text = text[1:]
            if text:
                self.service.add_plan_item(self.view_date, text)
                tell(self.page, "已加入计划")
            self.build_today_view()

        return handler

    def make_save_note(self, which: str):
        def handler(event):
            setter = self.service.set_day_check if which == "check" else self.service.set_day_act
            if setter(self.view_date, event.control.value or ""):
                tell(self.page, "已保存(含 md 镜像)")
                self.build_today_view()

        return handler

    def gen_weekly(self, event):
        spec = self.library.get("stages", "weekly_review")
        week_ago = self.today - timedelta(days=7)
        activity = [
            e for e in self.service.activity() if e.occurred_at >= week_ago and e.kind != "page_viewed"
        ]
        week_activity = "\n".join(f"{e.occurred_at} {e.label}" for e in activity[-40:]) or "(本周无活动)"
        stalled = "\n".join(
            f"{a.title}({(self.today - a.last_meaningful_update_at).days} 天)" for a in self.service.stalled_actions()
        ) or "(无停滞)"
        rendered = spec.render(
            week_activity=week_activity,
            stalled_list=stalled,
            project_brief=projects_summary(self.service),
        )
        text, _ = collect_text(self.runtime.complete(spec, rendered))
        editor = ft.TextField(value=text or "(AI 不可用)", multiline=True, min_lines=8, max_lines=16, expand=True)

        def adopt(adopt_event):
            record = self.service.day_record(self.today)
            merged = (record.worklog + "\n\n## 周复盘\n\n" + editor.value.strip()).strip()
            self.service.set_worklog(self.today, merged)
            self.page.pop_dialog()
            tell(self.page, "周复盘已并入今日工作记录")
            self.build_today_view()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("本周复盘草稿(可改后采纳)", size=15),
                content=ft.Container(editor, width=560),
                actions=[ft.TextButton("采纳进工作记录", on_click=adopt, autofocus=True),
                         ft.TextButton("放弃", on_click=lambda e: self.page.pop_dialog())],
            )
        )

    def build(self):
        self.today_body = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        return self.body


def main(page: ft.Page):
    if os.environ.get("UX_SHOT"):
        page.enable_screenshots = True  # 须在页面注册前设置
    page.title = "C · 引导复盘"
    page.padding = 24
    page.bgcolor = THEME["canvas"]
    app = ReviewWizard(page, _SERVICE, _LIBRARY, _RUNTIME)
    body = app.build()
    page.add(ft.Container(body, expand=True))
    app.render()
    # 向导关闭后把今天视图装进同一个 body
    def goto_today_wrapped():
        app.body.controls = [app.today_body]
        app.build_today_view()
        app.page.update()

    app.goto_today = goto_today_wrapped
    page.update()

    async def _ux_shot_task():
        import asyncio as _asyncio
        await _asyncio.sleep(1.0)
        png = await page.take_screenshot(pixel_ratio=2, delay=0.4)
        shot_path = os.environ["UX_SHOT"]
        Path(shot_path).write_bytes(png)
        print("saved", shot_path, flush=True)
        page.window.destroy()

    if os.environ.get("UX_SHOT"):
        page.run_task(_ux_shot_task)


_SERVICE: WorkspaceService | None = None
_LIBRARY: PromptLibrary | None = None
_RUNTIME = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="原型 C · 引导复盘")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT))
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    parser.add_argument("--ai-base-url", default=os.environ.get("WORKBENCH_AI_BASE_URL", ""))
    parser.add_argument("--ai-model", default=os.environ.get("WORKBENCH_AI_MODEL", ""))
    parser.add_argument("--ai-api-key", default=os.environ.get("WORKBENCH_AI_API_KEY", ""))
    parser.add_argument("--desktop", action="store_true", help="桌面窗口模式(默认网页)")
    parser.add_argument("--port", type=int, default=8550, help="网页模式端口")
    args = parser.parse_args()
    _SERVICE = WorkspaceService.open(WorkspaceStorage(Path(args.vault)))
    _LIBRARY = PromptLibrary(PROMPTS_ROOT)
    if args.provider == "openai" and not (args.ai_base_url and args.ai_model):
        parser.error("--provider openai 需要 --ai-base-url 与 --ai-model")
    _RUNTIME = (
        OpenAITextRuntime(args.ai_base_url, args.ai_model, args.ai_api_key)
        if args.provider == "openai"
        else FakePromptRuntime()
    )
    view = ft.AppView.FLET_APP if args.desktop else ft.AppView.WEB_BROWSER
    ft.app(main, view=view, port=args.port)
