"""版本 E「AI 主控台」:借鉴 ymos 的「阶段 → 角色卡 → 提示词文件」编排。

交互哲学:
- 主界面是对话式时间流:AI 按阶段产出「草稿卡」
  (早:今日计划建议;晚:Check 引导;周:周期复盘;随时:思维模式点名)。
- 每张草稿卡【采纳 / 改后采纳 / 忽略】:采纳即按契约写入
  (计划建议逐行进计划;Check 进当天;复盘并入工作记录)。
- 思考方式下拉:目标(想法/计划项/项目) + 模式(brainstorm/grill_me/
  six_hats/premortem,注册表自动发现) → 运行 → 草稿卡。
- 文件监听:watch_inbox/ 来新 .md/.txt → file_route 判定 →
  高置信自动追加项目进度(通知卡带一键撤销);低置信出草稿卡;无关留痕。
- 红线:除"高置信自动追加+可撤销"外,AI 只产草稿、落盘必经人工确认。

运行:python -m prototypes.e_ai_concierge.app --vault prototypes/ux-2026-09/demo_vault \
      --watch-dir prototypes/ux-2026-09/watch_inbox
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from datetime import date, timedelta
from pathlib import Path

import flet as ft

from prototypes.uxbase.loader import PromptLibrary
from prototypes.uxbase.router import route_file
from prototypes.uxbase.runtime import FakePromptRuntime, OpenAITextRuntime, collect_text
from prototypes.uxbase.seed_demo import DEFAULT_VAULT, projects_summary
from prototypes.uxbase.ui_kit import THEME, tell, undo_snackbar
from prototypes.uxbase.watcher import FileWatcher
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import WorkspaceStorage

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "prompts"

# --- 纯函数(冒烟测试覆盖) ---------------------------------------------------

_PLAN_LINE = re.compile(r"^\s*\d+[.、]\s*(.+)$")


def parse_plan_lines(text: str) -> list[tuple[str, str]]:
    """计划建议草稿 → [(条目文本, project_id|"")]。"""

    items: list[tuple[str, str]] = []
    for raw in text.splitlines():
        match = _PLAN_LINE.match(raw.strip())
        if not match:
            continue
        line = match.group(1)
        project_id = ""
        token = re.search(r"\((proj-[\w-]+)\)", line)
        if token:
            project_id = token.group(1)
            line = (line[: token.start()] + line[token.end():]).strip(" 　")
        items.append((line, project_id))
    return items


def build_target_options(service: WorkspaceService) -> list[tuple[str, str, str]]:
    """思考方式的候选目标:(显示名, kind, id)。"""

    options: list[tuple[str, str, str]] = []
    for idea in service.ideas():
        if idea.status == "pending":
            options.append((f"想法:{idea.text[:18]}", "idea", idea.idea_id))
    for project in service.projects():
        options.append((f"项目:{project.name}", "project", project.project_id))
    for item in service.day_record().plan:
        options.append((f"计划:{item.text[:18]}", "plan", item.item_id))
    return options


def target_text(service: WorkspaceService, kind: str, target_id: str) -> str:
    if kind == "idea":
        return next((i.text for i in service.ideas() if i.idea_id == target_id), "")
    if kind == "project":
        project = service.project(target_id)
        if project is None:
            return ""
        actions = ";".join(a.title for a in project.actions if a.status in ("pending", "in_progress", "waiting"))
        return f"{project.name}|目标:{project.goal}|焦点:{project.current_focus}|行动:{actions}"
    item = next((i for i in service.day_record().plan if i.item_id == target_id), None)
    return item.text if item else ""


def process_watched_file(service: WorkspaceService, runtime, library: PromptLibrary, path: Path) -> dict:
    """监听文件 → file_route 判定 → 落盘或等待确认。返回卡片数据。"""

    decision = route_file(runtime, library, projects_summary(service), path)
    result = {
        "file": path.name,
        "decision": decision,
        "progress_entry": None,
        "kind": ("auto" if decision.auto_append else "confirm" if decision.confidence == "low" else "ignored"),
    }
    if decision.auto_append:
        entry = service.append_project_progress(decision.project_id, decision.progress_entry)
        result["progress_entry"] = entry
        result["project_name"] = service.project(decision.project_id).name if service.project(decision.project_id) else decision.project_id
    return result


# --- UI ----------------------------------------------------------------------

class AiConcierge:
    def __init__(self, page: ft.Page, service: WorkspaceService, library: PromptLibrary, runtime, watch_dir: Path | None):
        self.page = page
        self.service = service
        self.library = library
        self.runtime = runtime
        self.watcher = FileWatcher(watch_dir) if watch_dir else None
        self.today = date.today()
        self.stream = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self.capture = ft.Ref[ft.TextField]()
        self.mode_dropdown = ft.Ref[ft.Dropdown]()
        self.target_dropdown = ft.Ref[ft.Dropdown]()

    # -- 草稿卡 -------------------------------------------------------------

    def add_draft_card(self, title: str, body: str, on_adopt) -> None:
        card = ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color=THEME["accent"]),
                            ft.Text(title, size=12, color=THEME["muted"]),
                        ],
                        spacing=6,
                    ),
                    ft.Container(ft.Text(body, size=13, selectable=True), bgcolor="#faf7f2",
                                 border_radius=8, padding=10),
                    ft.Row(
                        [
                            ft.FilledButton("采纳", on_click=lambda e: self.adopt(on_adopt, body, e),
                                            style=ft.ButtonStyle(bgcolor=THEME["accent"], color=ft.Colors.WHITE)),
                            ft.TextButton("改后采纳", on_click=lambda e: self.adopt_via_editor(title, body, on_adopt)),
                            ft.TextButton("忽略", on_click=lambda e: self.dismiss_card(e)),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=THEME["panel"], border=ft.Border.all(1, THEME["line"]),
            border_radius=14, padding=14,
        )
        self.stream.controls.insert(0, card)
        self.page.update()

    def dismiss_card(self, event):
        card = event.control
        while card is not None and not (isinstance(card, ft.Container) and card.bgcolor == THEME["panel"]):
            card = card.parent
        if card is not None and card in self.stream.controls:
            self.stream.controls.remove(card)
        tell(self.page, "已忽略草稿")
        self.page.update()

    def adopt_via_editor(self, title: str, body: str, on_adopt):
        editor = ft.TextField(value=body, multiline=True, min_lines=8, max_lines=18, expand=True, shift_enter=True)

        def confirm(event):
            self.page.pop_dialog()
            self.adopt(on_adopt, editor.value)

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(f"改后采纳 · {title}", size=15),
                content=ft.Container(editor, width=560),
                actions=[
                    ft.TextButton("采纳修改稿", on_click=confirm, autofocus=True),
                    ft.TextButton("取消", on_click=lambda e: self.page.pop_dialog()),
                ],
            )
        )

    def adopt(self, on_adopt, text: str, event=None):
        message = on_adopt(text)
        if event is not None:  # 采纳后卡片离场,防止重复写盘
            card = event.control
            while card is not None and not (isinstance(card, ft.Container) and card.bgcolor == THEME["panel"]):
                card = card.parent
            if card is not None and card in self.stream.controls:
                self.stream.controls.remove(card)
        self.page.update()
        tell(self.page, message)

    # -- 阶段动作 -----------------------------------------------------------

    def stage_plan_suggest(self, event=None):
        spec = self.library.get("stages", "plan_suggest")
        yesterday = self.today - timedelta(days=1)
        rendered = spec.render(
            yesterday_unfinished="\n".join(
                f"{'[已完成]' if i.done else '[未完成]'} {i.text}" for i in self.service.day_record(yesterday).plan
            ) or "(无)",
            pending_ideas="\n".join(i.text for i in self.service.ideas() if i.status == "pending") or "(无)",
            project_brief=projects_summary(self.service),
        )
        tell(self.page, "AI 生成中…(fake 端即回)")
        text, _ = collect_text(self.runtime.complete(spec, rendered))
        if not text:
            tell(self.page, "AI 不可用,本次未生成草稿;计划可直接手动添加")
            return

        def adopt(body: str) -> str:
            count = 0
            for line, project_id in parse_plan_lines(body):
                self.service.add_plan_item(self.today, line, project_id)
                count += 1
            return f"已采纳 {count} 条进入今日计划"

        self.add_draft_card("阶段 · 今日计划建议", text, adopt)

    def stage_day_check(self, event=None):
        spec = self.library.get("stages", "day_check")
        record = self.service.day_record(self.today)
        rendered = spec.render(
            plan_summary="\n".join(f"{'[已完成]' if i.done else '[未完成]'} {i.text}" for i in record.plan) or "(今天还没有计划)",
            worklog=record.worklog or "(还没有工作记录)",
        )
        tell(self.page, "AI 生成中…(fake 端即回)")
        text, _ = collect_text(self.runtime.complete(spec, rendered))
        if not text:
            tell(self.page, "AI 不可用,本次未生成草稿;Check 可手写")
            return

        def adopt(body: str) -> str:
            self.service.set_day_check(self.today, body.strip())
            return "Check 已写入今天"

        self.add_draft_card("阶段 · Check 引导", text, adopt)

    def stage_weekly(self, event=None):
        spec = self.library.get("stages", "weekly_review")
        week_ago = self.today - timedelta(days=7)
        activity = [e for e in self.service.activity() if e.occurred_at >= week_ago]
        rendered = spec.render(
            week_activity="\n".join(f"{e.occurred_at} {e.label}" for e in activity[-40:]) or "(本周无活动)",
            stalled_list="\n".join(
                f"{a.title}({(self.today - a.last_meaningful_update_at).days} 天)"
                for a in self.service.stalled_actions()
            ) or "(无停滞)",
            project_brief=projects_summary(self.service),
        )
        tell(self.page, "AI 生成中…(fake 端即回)")
        text, _ = collect_text(self.runtime.complete(spec, rendered))
        if not text:
            tell(self.page, "AI 不可用,本次未生成复盘草稿")
            return

        def adopt(body: str) -> str:
            record = self.service.day_record(self.today)
            self.service.set_worklog(self.today, (record.worklog + "\n\n## 周复盘\n\n" + body.strip()).strip())
            return "周复盘已并入今日工作记录"

        self.add_draft_card("阶段 · 周期复盘", text, adopt)

    # -- 思考方式(点名才来) -------------------------------------------------

    def run_thinking(self, event=None):
        option = self.target_dropdown.current.value
        mode = self.mode_dropdown.current.value
        if not option or not mode:
            tell(self.page, "先选目标和思考方式")
            return
        kind, _, target_id = option.partition(":")
        spec = self.library.get("thinking", mode)
        rendered = spec.render(
            target_kind=kind, target_text=target_text(self.service, kind, target_id),
            project_brief=projects_summary(self.service),
        )
        tell(self.page, "AI 生成中…(fake 端即回)")
        text, _ = collect_text(self.runtime.complete(spec, rendered))
        if not text:
            tell(self.page, "AI 不可用,本次未生成草稿")
            return
        spec_title = spec.title

        def adopt(body: str) -> str:
            first = next((ln for ln in body.splitlines() if ln.strip()), body[:40])
            self.service.add_plan_item(self.today, first.lstrip("0123456789.、- "))
            return "已把第一条采纳为今日计划"

        self.add_draft_card(f"思考 · {spec_title}", text, adopt)

    # -- 文件监听 ------------------------------------------------------------

    async def watch_loop(self):
        while True:
            await asyncio.sleep(5)
            if self.watcher is None:
                continue
            for path in self.watcher.scan_once():
                self.handle_watched_file(path)

    def handle_watched_file(self, path: Path):
        result = process_watched_file(self.service, self.runtime, self.library, path)
        decision = result["decision"]
        if result["kind"] == "auto":
            entry = result["progress_entry"]

            def undo(undo_event):
                self.service.remove_project_progress(decision.project_id, entry)
                tell(self.page, "已撤销自动追加的进度")
                self.page.update()

            undo_snackbar(
                self.page,
                f"《{result['file']}》已自动归档到「{result['project_name']}」",
                "撤销",
                undo,
            )
            self.add_info_card(
                f"文件 · {result['file']}",
                f"高置信 → 已自动记入「{result['project_name']}」进度:\n{decision.progress_entry}\n(理由:{decision.reason})",
                undo_label="撤销这次自动归档",
                on_undo=undo,
            )
        elif result["kind"] == "confirm":
            def adopt(body: str) -> str:
                project_id = decision.project_id
                self.service.append_project_progress(project_id, body.strip() or decision.progress_entry)
                return "进度已手动确认写入"

            self.add_draft_card(
                f"文件 · {result['file']}(低置信,待确认)",
                f"可能是「{decision.reason}」:\n{decision.progress_entry or decision.raw[:120]}",
                adopt,
            )
        else:
            self.add_info_card(f"文件 · {result['file']}", f"与本轮项目无关,已忽略留痕({decision.reason})")

    def add_info_card(self, title: str, body: str, undo_label: str | None = None, on_undo=None) -> None:
        actions = []
        if undo_label and on_undo is not None:
            actions.append(ft.TextButton(undo_label, on_click=on_undo, style=ft.ButtonStyle(color=THEME["accent"])))
        self.stream.controls.insert(
            0,
            ft.Container(
                ft.Column(
                    [
                        ft.Row([ft.Icon(ft.Icons.INBOX, size=14, color=THEME["info"]), ft.Text(title, size=12, color=THEME["muted"])]),
                        ft.Text(body, size=12, selectable=True),
                        ft.Row(actions, spacing=8) if actions else ft.Container(height=0),
                    ],
                    spacing=6,
                ),
                bgcolor=THEME["panel"], border=ft.Border.all(1, THEME["line"]), border_radius=14, padding=12,
            ),
        )
        self.page.update()

    # -- 捕获 ----------------------------------------------------------------

    def on_capture(self, event):
        text = (event.control.value or "").strip()
        if text:
            idea = self.service.quick_capture(text)
            self.add_info_card("捕获", f"已收进想法:{idea.text}")
        event.control.value = ""
        self.page.update()
        event.control.focus()

    # -- 构建 ----------------------------------------------------------------

    def build(self):
        modes = self.library.thinking()
        self.mode_dropdown.current = None
        mode_dd = ft.Dropdown(
            ref=self.mode_dropdown,
            label="思考方式",
            options=[ft.dropdown.Option(spec.key, spec.title) for spec in modes],
            value=modes[0].key if modes else None,
            width=150,
        )
        options = build_target_options(self.service)
        target_dd = ft.Dropdown(
            ref=self.target_dropdown,
            label="目标",
            options=[ft.dropdown.Option(f"{kind}:{tid}", label) for label, kind, tid in options],
            value=options[0][2] and f"{options[0][1]}:{options[0][2]}" if options else None,
            width=230,
        )
        side = ft.Container(
            ft.Column(
                [
                    ft.Text("捕获", weight=ft.FontWeight.BOLD),
                    ft.TextField(ref=self.capture, hint_text="随手记一条,回车", on_submit=self.on_capture,
                                 border_radius=18, filled=True),
                    ft.Text("阶段草稿(到点自动来的思路,这里手动触发)", size=12, color=THEME["muted"]),
                    ft.Row([ft.FilledTonalButton("今日计划建议", on_click=self.stage_plan_suggest)], wrap=True),
                    ft.Row([ft.FilledTonalButton("Check 引导", on_click=self.stage_day_check)], wrap=True),
                    ft.Row([ft.FilledTonalButton("本周复盘", on_click=self.stage_weekly)], wrap=True),
                    ft.Divider(),
                    ft.Text("点名思考方式", weight=ft.FontWeight.BOLD),
                    target_dd,
                    mode_dd,
                    ft.FilledButton("运行", on_click=self.run_thinking,
                                    style=ft.ButtonStyle(bgcolor=THEME["accent"], color=ft.Colors.WHITE)),
                    ft.Divider(),
                    ft.Text(
                        f"监听:{'开(' + str(self.watcher.watch_dir.name) + ')' if self.watcher else '未启用(--watch-dir)'}"
                        f" · Provider:{type(self.runtime).__name__}",
                        size=11, color=THEME["muted"],
                    ),
                ],
                spacing=10,
            ),
            width=300,
        )
        return ft.Row(
            [
                ft.Container(
                    ft.Column(
                        [
                            ft.Text("主控台 · 阶段时间流", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text("AI 产草稿,你决定落不落盘;采纳前不写任何文件", size=12, color=THEME["muted"]),
                            self.stream,
                        ],
                        spacing=8,
                    ),
                    expand=True,
                ),
                ft.VerticalDivider(width=1),
                side,
            ],
            expand=True,
            spacing=16,
        )


def main(page: ft.Page):
    if os.environ.get("UX_SHOT"):
        page.enable_screenshots = True  # 须在页面注册前设置
    page.title = "E · AI 主控台"
    page.padding = 18
    page.bgcolor = THEME["canvas"]
    app = AiConcierge(page, _SERVICE, _LIBRARY, _RUNTIME, _WATCH_DIR)
    page.add(app.build())
    page.update()
    if os.environ.get("UX_SCENE") == "stage":
        app.stage_plan_suggest()
        app.add_info_card(
            "文件 · 渠道日报核对.md",
            "高置信 → 已自动记入「星图演示库」进度:\n来自文件的进度记录(可撤销)",
        )
    if app.watcher is not None:
        page.run_task(app.watch_loop)


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
_WATCH_DIR: Path | None = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="原型 E · AI 主控台")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT))
    parser.add_argument("--watch-dir", default="")
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    parser.add_argument("--ai-base-url", default=os.environ.get("WORKBENCH_AI_BASE_URL", ""))
    parser.add_argument("--ai-model", default=os.environ.get("WORKBENCH_AI_MODEL", ""))
    parser.add_argument("--ai-api-key", default=os.environ.get("WORKBENCH_AI_API_KEY", ""))
    parser.add_argument("--desktop", action="store_true", help="桌面窗口模式(默认网页)")
    parser.add_argument("--port", type=int, default=8550, help="网页模式端口")
    args = parser.parse_args()
    _SERVICE = WorkspaceService.open(WorkspaceStorage(Path(args.vault)))
    _LIBRARY = PromptLibrary(PROMPTS_ROOT)
    _WATCH_DIR = Path(args.watch_dir) if args.watch_dir else None
    if args.provider == "openai" and not (args.ai_base_url and args.ai_model):
        parser.error("--provider openai 需要 --ai-base-url 与 --ai-model")
    _RUNTIME = (
        OpenAITextRuntime(args.ai_base_url, args.ai_model, args.ai_api_key)
        if args.provider == "openai"
        else FakePromptRuntime()
    )
    view = ft.AppView.FLET_APP if args.desktop else ft.AppView.WEB_BROWSER
    ft.app(main, view=view, port=args.port)
