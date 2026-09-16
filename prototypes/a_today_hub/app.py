"""版本 A「今日中枢」:借鉴 Things 3(Today 即家)与 Todoist 快速捕获。

交互哲学:
- 一页做完一天的事:捕获 → 计划勾选 → 工作记录,不切页。
- 智能捕获条(借鉴 Todoist 自然语言路由,规则刻意保持简单可记):
    `!文字`            → 直接成为今日计划项
    `#项目名 文字`      → 成为该项目的今日计划项(项目名做包含匹配)
    `其他任何文字`      → 成为待整理想法
- 昨日未完成一键顺延(借鉴 Things 3 rollover),可整体撤销。
- 待处理想法一行一操作(touch once):入今日/保留/归档/点名思考方式。

运行:python -m prototypes.a_today_hub.app --vault prototypes/ux-2026-09/demo_vault
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


# --- 纯函数(冒烟测试覆盖) ---------------------------------------------------

def route_capture(text: str, project_names: dict[str, str]) -> tuple[str, str, str]:
    """(kind, cleaned_text, project_id);kind ∈ {"plan", "idea"}。"""

    cleaned = text.strip()
    if cleaned.startswith("!"):
        return "plan", cleaned[1:].strip(), ""
    if cleaned.startswith("#"):
        head, _, rest = cleaned[1:].partition(" ")
        for name, project_id in project_names.items():
            if name in head:
                return "plan", rest.strip() or head, project_id
        return "idea", cleaned, ""
    return "idea", cleaned, ""


def plan_summary_lines(record) -> list[str]:
    return [f"{'[已完成]' if item.done else '[未完成]'} {item.text}" for item in record.plan]


# --- UI ----------------------------------------------------------------------

class TodayHub:
    def __init__(self, page: ft.Page, service: WorkspaceService, library: PromptLibrary, runtime):
        self.page = page
        self.service = service
        self.library = library
        self.runtime = runtime
        self.today = date.today()
        self.capture = ft.Ref[ft.TextField]()
        self.plan_list = ft.Column(spacing=6)
        self.idea_list = ft.Column(spacing=6)
        self.rollover_bar = ft.Container(visible=False)

    # -- 智能捕获 ---------------------------------------------------------

    def on_capture(self, event):
        text = event.control.value or ""
        if not text.strip():
            return
        names = {project.name: project.project_id for project in self.service.projects()}
        kind, payload, project_id = route_capture(text, names)
        if not payload:
            tell(self.page, "没有可记录的内容(#项目名 后面要跟正文)")
            return
        if kind == "plan":
            item = self.service.add_plan_item(self.today, payload, project_id)
            label = "已加入今日计划"
            if project_id:
                label += f"({self.service.project(project_id).name})"
        else:
            self.service.quick_capture(payload)
            label = "已收进待整理想法"
        event.control.value = ""
        self.refresh()
        self.page.update()
        event.control.focus()
        tell(self.page, label)

    # -- 计划:勾选 / 删除(可撤销) ----------------------------------------

    def on_toggle(self, item_id):
        def handler(event):
            done = self.service.toggle_plan_item(self.today, item_id)
            tell(self.page, "已完成 ✓" if done else "已取消完成")
            self.refresh_plan()

        return handler

    def on_remove_plan(self, item):
        def handler(event):
            self.service.remove_plan_item(self.today, item.item_id)

            def undo(undo_event):
                self.service.add_plan_item(self.today, item.text, item.project_id)
                self.refresh()
                self.page.update()

            undo_snackbar(self.page, f"已删除「{item.text[:20]}」", "撤销", undo)
            self.refresh_plan()

        return handler

    # -- 顺延 -------------------------------------------------------------

    def undone_from(self, day: date):
        return [item for item in self.service.day_record(day).plan if not item.done]

    def on_rollover(self, event):
        undone = self.undone_from(self.today - timedelta(days=1))
        moved = []
        for item in undone:
            self.service.add_plan_item(self.today, item.text, item.project_id)
            self.service.remove_plan_item(self.today - timedelta(days=1), item.item_id)
            moved.append(item)

        def undo(undo_event):
            for item in moved:
                self.service.remove_plan_item(self.today, next(
                    (i.item_id for i in self.service.day_record(self.today).plan if i.text == item.text), ""))
                self.service.add_plan_item(self.today - timedelta(days=1), item.text, item.project_id)
            self.refresh()
            self.page.update()

        undo_snackbar(self.page, f"已顺延 {len(moved)} 项到今天", "撤销", undo)
        self.refresh()

    # -- 想法处理(touch once)+ 思考方式 ----------------------------------

    def on_idea_action(self, idea, action: str):
        def handler(event):
            if action == "plan":
                self.service.add_plan_item(self.today, idea.text)
                self.service.set_idea_status(idea.idea_id, "kept")
                tell(self.page, "已按原文加入今日计划")
            elif action in ("kept", "archived"):
                self.service.set_idea_status(idea.idea_id, action)
                tell(self.page, "已保留" if action == "kept" else "已归档")
            self.refresh_ideas()

        return handler

    def on_thinking(self, idea, mode_spec):
        def handler(event):
            spec = self.library.get("thinking", mode_spec)
            rendered = spec.render(target_kind="想法", target_text=idea.text)
            text, _ = collect_text(self.runtime.complete(spec, rendered))
            if not text:
                tell(self.page, "AI 不可用,已跳过;想法仍可手动处理")
                return
            self.open_draft_dialog(f"{spec.title}·{idea.text[:16]}", text)

        return handler

    def open_draft_dialog(self, title: str, draft: str, on_adopt=None):
        editor = ft.TextField(value=draft or "(AI 无返回)", multiline=True, min_lines=6,
                              max_lines=14, expand=True, shift_enter=True)
        default_target = ft.TextField(hint_text="采纳为今日计划项(可改写)", expand=True)

        def adopt(event):
            self.service.add_plan_item(self.today, default_target.value or editor.value.splitlines()[0])
            tell(self.page, "已采纳为今日计划")
            self.page.pop_dialog()
            self.refresh()

        def ignore(event):
            self.page.pop_dialog()
            tell(self.page, "已忽略草稿")

        dialog = ft.AlertDialog(
            title=ft.Text(title, size=15),
            content=ft.Column([editor, default_target], tight=True, width=520),
            actions=[
                ft.TextButton("采纳为计划", on_click=adopt, autofocus=True, style=ft.ButtonStyle(color=THEME["accent"])),
                ft.TextButton("忽略", on_click=ignore),
            ],
        )
        self.page.show_dialog(dialog)

    # -- 列表构建 ---------------------------------------------------------

    def refresh_plan(self):
        record = self.service.day_record(self.today)
        rows = []
        for item in record.plan:
            rows.append(
                ft.Row(
                    [
                        ft.Checkbox(value=item.done, on_change=self.on_toggle(item.item_id)),
                        ft.Text(item.text, expand=True,
                                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if item.done else None),
                        ft.IconButton(ft.Icons.CLOSE, icon_size=14, icon_color=THEME["muted"],
                                      tooltip="删除(可撤销)", on_click=self.on_remove_plan(item)),
                    ],
                    spacing=4,
                )
            )
        self.plan_list.controls = rows or [hint("今天还没有计划,在上面输入「!第一件事」", action_label="昨日未完成顺延",
                                                on_action=self.on_rollover)]
        undone = self.undone_from(self.today - timedelta(days=1))
        self.rollover_bar.visible = bool(undone)
        self.rollover_bar.content = ft.Row(
            [
                ft.Text(f"昨天还有 {len(undone)} 项没完成", color=THEME["warn"]),
                ft.TextButton("顺延到今天", on_click=self.on_rollover),
            ]
        )

    def refresh_ideas(self):
        pending = sorted(
            (idea for idea in self.service.ideas() if idea.status == "pending"),
            key=lambda i: i.created_at,
        )
        modes = [(spec.title, spec.key) for spec in self.library.thinking()]
        rows = []
        for idea in pending:
            rows.append(
                ft.Column(
                    [
                        ft.Text(idea.text, size=13),
                        ft.Row(
                            [
                                ft.TextButton("入今日", on_click=self.on_idea_action(idea, "plan")),
                                ft.TextButton("保留", on_click=self.on_idea_action(idea, "kept")),
                                ft.IconButton(ft.Icons.ARCHIVE_OUTLINED, icon_size=16, tooltip="归档",
                                              on_click=self.on_idea_action(idea, "archived")),
                                ft.PopupMenuButton(
                                    icon=ft.Icons.PSYCHOLOGY_ALT, tooltip="点名思考方式",
                                    items=[
                                        ft.PopupMenuItem(content=ft.Text(title), on_click=self.on_thinking(idea, key))
                                        for title, key in modes
                                    ],
                                ),
                            ],
                            spacing=0,
                            wrap=True,
                        ),
                    ],
                    spacing=0,
                )
            )
        self.idea_list.controls = rows or [hint("没有待整理想法,在顶部输入框随手记一条")]

    def refresh(self):
        self.refresh_plan()
        self.refresh_ideas()

    def build(self):
        capture_bar = ft.TextField(
            ref=self.capture,
            hint_text="随手记:#星图 跟进口径问题 / !写周报 / 直接文字=想法",
            on_submit=self.on_capture,
            border_radius=24,
            filled=True,
            expand=True,
        )
        worklog = ft.TextField(
            label="工作记录(Enter 提交,Shift+Enter 换行,失焦即存)",
            multiline=True, min_lines=4, max_lines=8, shift_enter=True, expand=True,
            value=self.service.day_record(self.today).worklog,
            on_submit=self._save_worklog, on_blur=self._save_worklog,
        )
        header = ft.Row(
            [
                ft.Text("今日", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(self.today.strftime("%Y-%m-%d %a"), color=THEME["muted"]),
                ft.Container(expand=True),
                ft.Text("捕获:#项目 计划 · !直接计划 · 纯文字想法", size=12, color=THEME["muted"]),
            ]
        )
        return ft.Column(
            [
                header,
                ft.Row([capture_bar]),
                self.rollover_bar,
                ft.Row(
                    [
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Text("今日计划", weight=ft.FontWeight.BOLD),
                                    self.plan_list,
                                    ft.Divider(),
                                    worklog,
                                ],
                                spacing=10,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            expand=3,
                        ),
                        ft.VerticalDivider(width=1),
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Text("待整理想法", weight=ft.FontWeight.BOLD),
                                    self.idea_list,
                                ],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            expand=2,
                        ),
                    ],
                    expand=True,
                ),
            ],
            spacing=12,
            expand=True,
        )

    def _save_worklog(self, event):
        if self.service.set_worklog(self.today, event.control.value or ""):
            tell(self.page, "工作记录已保存")
        self.refresh_plan()


def main(page: ft.Page):
    if os.environ.get("UX_SHOT"):
        page.enable_screenshots = True  # 须在页面注册前设置
    page.title = "A · 今日中枢"
    page.padding = 18
    page.bgcolor = THEME["canvas"]
    app = TodayHub(page, _SERVICE, _LIBRARY, _RUNTIME)
    app.refresh()
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
_LIBRARY: PromptLibrary | None = None
_RUNTIME = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="原型 A · 今日中枢")
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
