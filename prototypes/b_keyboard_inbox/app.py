"""版本 B「键盘流 + 收件箱零」:借鉴 Superhuman/Tana 的 touch-once 处理。

交互哲学:
- 手不离键盘:j/k 选择,1/2/3 决定想法去向,e 改计划项,c 捕获,Ctrl+K 命令面板。
- 收件箱零:待整理想法以大卡片逐条呈现,处理完即空。
- 状态直接切换(set_action_status),不依赖 AI 提案通道。
- 一切列表有确定排序:待处理置顶、未完成置顶、按时间倒序。
- 零 AI:这个版本验证"没有 AI 会不会更快"。

运行:python -m prototypes.b_keyboard_inbox.app --vault prototypes/ux-2026-09/demo_vault
快捷键即帮助:按 Ctrl+K,空查询时面板就是完整命令文档。
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

import flet as ft

from prototypes.uxbase.seed_demo import DEFAULT_VAULT
from prototypes.uxbase.ui_kit import STATUS_COLORS, STATUS_LABELS, THEME, hint, tell, undo_snackbar
from workbench.domain.models import IN_PROGRESS
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import WorkspaceStorage

# --- 纯函数(冒烟测试覆盖) ---------------------------------------------------

IDEA_KEY_ACTIONS = {"1": "kept", "2": "archived", "3": "plan"}


def sort_ideas(ideas):
    """待处理置顶,其余按状态,同状态新的在前。"""

    order = {"pending": 0, "kept": 1, "archived": 2}
    return sorted(ideas, key=lambda i: (order.get(i.status, 9), -i.created_at.toordinal()))


def sort_plan(items):
    """未完成在前,完成的沉底(保持原相对顺序)。"""

    undone = [i for i in items if not i.done]
    done = [i for i in items if i.done]
    return undone + done


def move_selection(total: int, current: int, key: str) -> int:
    if key == "j":
        return min(current + 1, total - 1)
    if key == "k":
        return max(current - 1, 0)
    return current


def build_commands() -> list[tuple[str, str]]:
    """命令面板内容:空查询时它就是文档。"""

    return [
        ("c", "聚焦捕获框,输入想法"),
        ("j / k", "想法队列上/下移动"),
        ("1", "想法 → 保留"),
        ("2", "想法 → 归档"),
        ("3", "想法 → 转为今日计划"),
        ("e", "重命名选中今日计划项"),
        ("s", "选中行动 → 进行中"),
        ("d", "选中行动 → 完成"),
        ("Ctrl+K", "命令面板(本面板)"),
    ]


# --- UI ----------------------------------------------------------------------

class KeyboardInbox:
    def __init__(self, page: ft.Page, service: WorkspaceService):
        self.page = page
        self.service = service
        self.today = date.today()
        self.selected = 0
        self.capture = ft.Ref[ft.TextField]()
        self.queue_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self.plan_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.action_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.selected_action: tuple[str, str] | None = None  # (project_id, action_id)
        self.typing = False  # 任一文本框持有焦点时为 True,键盘流让路

    # -- 键盘 ---------------------------------------------------------------

    def on_key(self, event: ft.KeyboardEvent):
        if event.ctrl and event.key.lower() == "k":
            self.open_palette()
            return
        if self.typing:
            return  # 焦点守卫:输入框里打字绝不触发想法操作
        pending = [i for i in sort_ideas(self.service.ideas()) if i.status == "pending"]
        if event.key == "c":
            self.capture.current.focus()
            return
        if event.key == "e" and self.service.day_record(self.today).plan:
            undone = [i for i in sort_plan(self.service.day_record(self.today).plan) if not i.done]
            self.on_rename(undone[0] if undone else self.service.day_record(self.today).plan[0])(None)
            return
        if event.key == "s":
            self.apply_action_status("in_progress")
            return
        if event.key == "d":
            self.apply_action_status("completed")
            return
        if not pending:
            return
        self.selected = move_selection(len(pending), self.selected, event.key)
        action = IDEA_KEY_ACTIONS.get(event.key)
        if action:
            idea = pending[min(self.selected, len(pending) - 1)]
            if action == "plan":
                self.service.add_plan_item(self.today, idea.text)
            self.service.set_idea_status(idea.idea_id, "kept" if action == "plan" else action)
            self.selected = 0
            tell(self.page, {"kept": "已保留", "archived": "已归档", "plan": "已转今日计划"}[action])
        if event.key in ("j", "k"):
            self.page.update()
        self.refresh()

    # -- 捕获 ---------------------------------------------------------------

    def on_capture(self, event):
        text = (event.control.value or "").strip()
        if text:
            self.service.quick_capture(text)
            self.selected = 0
            tell(self.page, "已捕获")
        event.control.value = ""
        self.refresh()
        self.page.update()
        event.control.focus()

    # -- 计划项与行动 -------------------------------------------------------

    def on_rename(self, item):
        def handler(event):
            editor = ft.TextField(value=item.text, expand=True, autofocus=True)

            def save(save_event):
                self.service.rename_plan_item(self.today, item.item_id, editor.value)
                self.page.pop_dialog()
                tell(self.page, "计划项已改名")
                self.refresh()

            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("重命名计划项(e)", size=15),
                    content=editor,
                    actions=[ft.TextButton("保存", on_click=save, autofocus=True)],
                )
            )

        return handler

    def on_action_status(self, project_id: str, action_id: str, status: str):
        def handler(event):
            self.selected_action = (project_id, action_id)
            self.apply_action_status(status)

        return handler

    def apply_action_status(self, status: str):
        if not self.selected_action:
            tell(self.page, "先用 s/d 或点击选中一个行动")
            return
        project_id, action_id = self.selected_action
        if self.service.set_action_status(project_id, action_id, status):
            tell(self.page, f"行动 → {STATUS_LABELS[status]}")
        else:
            tell(self.page, "状态未变化")
        self.refresh()

    # -- 命令面板 -----------------------------------------------------------

    def open_palette(self):
        query = ft.TextField(hint_text="输入过滤,空查询=全部命令", autofocus=True)
        listing = ft.Column(spacing=2)

        def rebuild(filter_text=""):
            listing.controls = [
                ft.Row([ft.Container(ft.Text(k, weight=ft.FontWeight.BOLD, width=70)), ft.Text(desc, color=THEME["muted"])])
                for k, desc in build_commands()
                if not filter_text or filter_text.lower() in (k + desc).lower()
            ] or [ft.Text("没有匹配的命令", color=THEME["muted"])]
            listing.update() if listing.page else None

        def on_type(event):
            rebuild(event.control.value)

        rebuild()
        query.on_change = on_type

        def close(event):
            self.page.pop_dialog()
            self.capture.current.focus()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("命令面板", size=15),
                content=ft.Column([query, ft.Divider(), listing], tight=True, width=460),
                actions=[ft.TextButton("关闭(Esc 不行就点这)", on_click=close)],
            )
        )

    # -- 构建 ---------------------------------------------------------------

    def refresh(self):
        pending = [i for i in sort_ideas(self.service.ideas()) if i.status == "pending"]
        if self.selected >= max(len(pending), 1):
            self.selected = max(len(pending) - 1, 0)
        cards = []
        for idx, idea in enumerate(pending):
            active = idx == self.selected
            cards.append(
                ft.Container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Container(width=4, height=28, bgcolor=THEME["accent"] if active else ft.Colors.TRANSPARENT),
                                    ft.Text(idea.text, size=15, expand=True, weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL),
                                ],
                                spacing=8,
                            ),
                            ft.Row(
                                [
                                    ft.Text("1 保留", size=11, color=THEME["muted"]),
                                    ft.Text("2 归档", size=11, color=THEME["muted"]),
                                    ft.Text("3 转计划", size=11, color=THEME["muted"]),
                                    ft.Text("j/k 选择", size=11, color=THEME["muted"]),
                                ],
                                spacing=14,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=THEME["panel"] if active else "#fbfaf8",
                    border=ft.Border.all(2, THEME["accent"] if active else THEME["line"]),
                    border_radius=12,
                    padding=12,
                    on_click=self.make_select(idx),
                )
            )
        self.queue_column.controls = cards or [
            hint("收件箱零 ✓ 待整理想法清空了", action_label="随手捕获一条(c)", on_action=lambda e: self.capture.current.focus())
        ]

        record = self.service.day_record(self.today)
        plan_rows = []
        for item in sort_plan(record.plan):
            plan_rows.append(
                ft.Row(
                    [
                        ft.Checkbox(value=item.done, on_change=self.make_toggle(item.item_id)),
                        ft.Text(item.text, expand=True, size=13,
                                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if item.done else None),
                        ft.IconButton(ft.Icons.EDIT, icon_size=14, tooltip="重命名(e)", on_click=self.on_rename(item)),
                    ]
                )
            )
        self.plan_column.controls = plan_rows or [hint("今日计划为空;选中想法按 3 转入")]

        action_rows = []
        for project in self.service.projects():
            open_actions = [a for a in project.actions if a.status not in ("completed", "cancelled")]
            if not open_actions:
                continue
            action_rows.append(ft.Text(project.name, size=12, color=THEME["muted"]))
            for action in open_actions:
                selected = self.selected_action == (project.project_id, action.action_id)
                action_rows.append(
                    ft.Row(
                        [
                            ft.Container(
                                ft.Text(STATUS_LABELS[action.status], size=11, color=ft.Colors.WHITE),
                                bgcolor=STATUS_COLORS[action.status],
                                border_radius=8,
                                padding=ft.Padding.only(left=8, right=8, top=2, bottom=2),
                            ),
                            ft.Container(
                                content=ft.Text(
                                    action.title + ("  ⚠ 停滞" if action.status == IN_PROGRESS and (date.today() - action.last_meaningful_update_at).days >= 15 else ""),
                                    size=13,
                                    weight=ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL,
                                ),
                                expand=True,
                                on_click=self.make_pick_action(project.project_id, action.action_id),
                            ),
                            ft.TextButton("s", tooltip="进行中", on_click=self.on_action_status(project.project_id, action.action_id, "in_progress")),
                            ft.TextButton("d", tooltip="完成", on_click=self.on_action_status(project.project_id, action.action_id, "completed")),
                        ],
                        spacing=6,
                    )
                )
        self.action_column.controls = action_rows

    def make_select(self, idx):
        return lambda event: (setattr(self, "selected", idx), self.refresh(), self.page.update())

    def make_toggle(self, item_id):
        def handler(event):
            self.service.toggle_plan_item(self.today, item_id)
            tell(self.page, "已更新完成状态")
            self.refresh()

        return handler

    def make_pick_action(self, project_id, action_id):
        def handler(event):
            self.selected_action = (project_id, action_id)
            self.refresh()
            self.page.update()

        return handler

    def build(self):
        record = self.service.day_record(self.today)
        worklog = ft.TextField(
            label="工作记录(失焦即存)",
            multiline=True, min_lines=3, max_lines=6, shift_enter=True, expand=True,
            value=record.worklog, on_blur=self._save_worklog, on_submit=self._save_worklog,
            on_focus=self._set_typing(True),
        )
        return ft.Row(
            [
                ft.Container(
                    ft.Column(
                        [
                            ft.Text("待处理想法", size=18, weight=ft.FontWeight.BOLD),
                            ft.TextField(
                                ref=self.capture, hint_text="c 聚焦 · 回车捕获", on_submit=self.on_capture,
                                border_radius=20, filled=True,
                                on_focus=self._set_typing(True), on_blur=self._set_typing(False),
                            ),
                            self.queue_column,
                        ],
                        spacing=10,
                    ),
                    expand=5,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(
                    ft.Column(
                        [
                            ft.Text("今日计划", weight=ft.FontWeight.BOLD),
                            self.plan_column,
                            ft.Divider(),
                            worklog,
                            ft.Divider(),
                            ft.Text("项目行动(点标题选中,s/d 直改状态)", weight=ft.FontWeight.BOLD, size=13),
                            self.action_column,
                        ],
                        scroll=ft.ScrollMode.AUTO,
                        spacing=8,
                    ),
                    expand=4,
                ),
            ],
            expand=True,
            spacing=16,
        )

    def _set_typing(self, value: bool):
        def handler(event):
            self.typing = value

        return handler

    def _save_worklog(self, event):
        if self.service.set_worklog(self.today, event.control.value or ""):
            tell(self.page, "工作记录已保存")


def main(page: ft.Page):
    if os.environ.get("UX_SHOT"):
        page.enable_screenshots = True  # 须在页面注册前设置
    page.title = "B · 键盘流收件箱"
    page.padding = 18
    page.bgcolor = THEME["canvas"]
    app = KeyboardInbox(page, _SERVICE)
    app.refresh()
    page.on_keyboard_event = app.on_key
    page.add(app.build())
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="原型 B · 键盘流收件箱")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT))
    parser.add_argument("--desktop", action="store_true", help="桌面窗口模式(默认网页)")
    parser.add_argument("--port", type=int, default=8550, help="网页模式端口")
    args = parser.parse_args()
    _SERVICE = WorkspaceService.open(WorkspaceStorage(Path(args.vault)))
    view = ft.AppView.FLET_APP if args.desktop else ft.AppView.WEB_BROWSER
    ft.app(main, view=view, port=args.port)
