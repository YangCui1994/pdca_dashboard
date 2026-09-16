"""组合与启动:路由、AI 流式消费、Artifact 外开、--vault 落盘。不承载领域规则。"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date
from pathlib import Path

import flet as ft

from workbench.components import THEME
from workbench.components.ai_panel import (
    AIPanelState,
    STATUS_ACCEPTED,
    STATUS_AWAITING,
    STATUS_REJECTED,
    STATUS_RUNNING,
    build_ai_panel,
)
from workbench.components.concierge import ConciergeController
from workbench.components.feedback import tell, undo_snackbar
from workbench.components.navigation import (
    ROUTE_ACTIVITY,
    ROUTE_ARCHIVE,
    ROUTE_IDEAS,
    ROUTE_PROJECTS,
    ROUTE_TODAY,
    build_page,
)
from workbench.domain.fixtures import load_demo_workspace
from workbench.components.ai_panel import STATUS_FAILED as AI_STATUS_FAILED
from workbench.runtime.contracts import (
    COMPLETED,
    FAILED,
    RunRequest,
)
from workbench.runtime.fake_runtime import FakeRuntime
from workbench.runtime.openai_runtime import OpenAICompatibleRuntime
from workbench.runtime.text_runtime import FakePromptRuntime, OpenAITextRuntime
from workbench.services.file_routing import route_file
from workbench.services.file_watcher import FileWatcher
from workbench.services.flow_artifact import render_flow_html
from workbench.services.prompt_library import PromptLibrary, projects_summary
from workbench.services.workspace_service import WorkspaceService
from workbench.views.activity import build_activity
from workbench.views.archive import build_archive
from workbench.views.ideas import build_ideas
from workbench.views.node_detail import build_node_detail
from workbench.views.project_overview import build_project_overview
from workbench.views.projects_home import build_projects_home
from workbench.views.today import build_today

_ARTIFACT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "artifacts", "project-flow.html"
)


def _parse_project_route(route: str) -> tuple[str | None, str | None]:
    """'/projects' → (None, None);'/projects/pid' → (pid, None);
    '/projects/pid/node/nid' → (pid, nid)。"""

    if not route or not route.startswith(ROUTE_PROJECTS):
        return None, None
    rest = route[len(ROUTE_PROJECTS):].strip("/")
    if not rest:
        return None, None
    parts = rest.split("/")
    pid = parts[0]
    nid = parts[2] if len(parts) >= 3 and parts[1] == "node" else None
    return pid, nid


class WorkbenchApp:
    """Owns UI state; formal state stays inside WorkspaceService."""

    def __init__(self, page: ft.Page, service: WorkspaceService, runtime):
        self.page = page
        self.service = service
        self.runtime = runtime
        self.ai_state = AIPanelState()
        self.concierge = ConciergeController(service, page=page)
        self.ai_open = False  # 右侧 AI 面板默认收起,侧栏「AI 助手」点开
        self.selected_date: date | None = None
        self.page.on_route_change = lambda _e: self.render()

    # --- navigation --------------------------------------------------------

    def go(self, route: str):
        self.page.go(route)

    def _create_project(self, **fields):
        """新建项目并直接进入该项目(表单验证失败会抛给调用方显示)。"""

        project = self.service.create_project(**fields)
        self.open_project(project.project_id)
        return project

    def open_project(self, project_id: str):
        self.go(f"{ROUTE_PROJECTS}/{project_id}")

    def open_node(self, project_id: str, node_id: str):
        self.go(f"{ROUTE_PROJECTS}/{project_id}/node/{node_id}")

    def _current_project_id(self) -> str | None:
        pid, _nid = _parse_project_route(self.page.route or "")
        if pid is not None and self.service.project(pid) is not None:
            return pid
        return next((p.project_id for p in self.service.projects()), None)

    # --- AI panel actions ----------------------------------------------------

    def run_review(self):
        """Start a fake run; streaming happens in a background task."""
        self.ai_state = AIPanelState(status=STATUS_RUNNING)
        self.render()
        self.page.run_task(self._consume_review)

    async def _consume_review(self):
        request = RunRequest(
            kind="project.review", project_id=self._current_project_id() or ""
        )
        recent: list[str] = []
        count = 0
        last_event = None
        for event in self.runtime.events(request):
            last_event = event
            count += 1
            if event.tool:
                recent.append(f"#{event.seq} {event.tool}")
            elif event.message:
                recent.append(f"#{event.seq} {event.message}")
            self.ai_state.current_tool = event.tool or ""
            self.ai_state.event_count = count
            self.ai_state.recent_events = tuple(recent)
            if count % 6 == 0 or event.state == COMPLETED:
                self.render()
            await asyncio.sleep(0.015)
        self.ai_state.current_tool = ""
        if last_event is not None and last_event.state == FAILED:
            self.ai_state.status = AI_STATUS_FAILED
            self.ai_state.note = last_event.message or "运行失败"
            self.ai_state.proposal = None
        else:
            self.ai_state.status = STATUS_AWAITING
            self.ai_state.note = ""
            self.ai_state.proposal = last_event.proposal if last_event else None
        self.render()

    def accept_proposal(self, proposal):
        self.service.accept_proposal(proposal)
        self.ai_state.status = STATUS_ACCEPTED
        self.render()

    def reject_proposal(self, proposal):
        self.service.reject_proposal(proposal)
        self.ai_state.status = STATUS_REJECTED
        self.render()

    # --- artifact -------------------------------------------------------------

    def open_artifact(self, artifact_path: str):
        target = artifact_path
        if _VAULT:  # 落盘模式:每次打开用真实数据重新生成到 vault 的 .artifacts/
            pid = self._current_project_id()
            if pid:
                out = Path(_VAULT) / ".artifacts" / "project-flow.html"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(render_flow_html(self.service, pid), encoding="utf-8")
                target = str(out)
        url = Path(target).resolve().as_uri()  # Windows 下 file:// 手拼会错
        self.page.launch_url(url)

    def toggle_ai(self, _e=None):
        """侧栏 AI 开关:打开时把思考方式目标预选为当前项目。"""

        self.ai_open = not self.ai_open
        if self.ai_open:
            pid = self._current_project_id()
            if pid is not None and self.service.project(pid) is not None:
                self.concierge.preset_project(pid)
        self.render()

    def quick_capture(self, text: str):
        """底部捕获条的唯一接线点;规则都在 WorkspaceService。"""
        self.service.quick_capture(text)
        self.render()

    # --- rendering ---------------------------------------------------------------

    def render(self):
        route = self.page.route or ROUTE_PROJECTS
        self.page.controls.clear()
        rerender = lambda: self.render()

        self.concierge.set_providers(_LIBRARY, _TEXT_RUNTIME)
        ai_panel = None
        if self.ai_open:
            ai_panel = build_ai_panel(
                self.ai_state,
                on_run_review=lambda _e=None: self.run_review(),
                on_accept=lambda proposal: self.accept_proposal(proposal),
                on_reject=lambda proposal: self.reject_proposal(proposal),
                concierge=self.concierge,
            )

        if route.startswith(ROUTE_TODAY):
            content = build_today(
                self.service,
                on_refresh=rerender,
                page=self.page,
                library=_LIBRARY,
                runtime=_TEXT_RUNTIME,
            )
            active = ROUTE_TODAY
        elif route.startswith(ROUTE_IDEAS):
            content = build_ideas(self.service, on_refresh=rerender)
            active = ROUTE_IDEAS
        elif route.startswith(ROUTE_ARCHIVE):
            content = build_archive(self.service, on_refresh=rerender)
            active = ROUTE_ARCHIVE
        elif route.startswith(ROUTE_ACTIVITY):
            content = build_activity(
                self.service,
                on_pick_date=self._pick_date,
                selected_date=self.selected_date,
            )
            active = ROUTE_ACTIVITY
        elif route.startswith(ROUTE_PROJECTS):
            pid, nid = _parse_project_route(route)
            if pid is not None and self.service.project(pid) is None:
                pid, nid = None, None  # 未知项目回落到项目首页
            if nid is not None:
                content = build_node_detail(
                    self.service,
                    pid,
                    nid,
                    on_back=lambda _e=None: self.open_project(pid),
                    on_open_node=lambda n, pid=pid: self.open_node(pid, n),
                    on_refresh=rerender,
                )
            elif pid is not None:
                content = build_project_overview(
                    self.service,
                    pid,
                    on_open_node=lambda n, pid=pid: self.open_node(pid, n),
                    on_open_artifact=lambda: self.open_artifact(_ARTIFACT_PATH),
                    on_refresh=rerender,
                    on_back=lambda _e=None: self.go(ROUTE_PROJECTS),
                )
            else:
                content = build_projects_home(
                    self.service,
                    on_open_project=lambda pid: self.open_project(pid),
                    on_refresh=rerender,
                    on_create=self._create_project,
                )
            active = ROUTE_PROJECTS
        else:
            content = build_projects_home(
                self.service,
                on_open_project=lambda pid: self.open_project(pid),
                on_refresh=rerender,
                on_create=self._create_project,
            )
            active = ROUTE_PROJECTS

        self.page.add(
            build_page(
                active,
                lambda r: self.go(r),
                content,
                ai_panel,
                # Today 页有自己的常驻智能捕获条;全局底栏只服务其他页面。
                on_capture=(
                    None if route.startswith(ROUTE_TODAY) else self.quick_capture
                ),
                ai_open=self.ai_open,
                on_toggle_ai=self.toggle_ai,
                ai_attention=(
                    not self.ai_open
                    and self.ai_state.status == STATUS_AWAITING
                ),
            )
        )
        self.page.update()

    def _pick_date(self, day: date):
        self.selected_date = day
        self.go(ROUTE_ACTIVITY)


def _scene_task(app: "WorkbenchApp"):
    """Env-driven navigation for evidence screenshots (composition only)."""

    async def _task():
        scene = os.environ.get("SPIKE_SCENE", "")
        shot = os.environ.get("SPIKE_SHOT", "")
        if not scene and not shot:
            return
        await asyncio.sleep(1.2)
        if scene == "node":
            app.open_node("proj-atlas", "node-tests")
        elif scene == "today":
            app.go(ROUTE_TODAY)
        elif scene == "activity":
            app.go(ROUTE_ACTIVITY)
        elif scene == "project":
            app.open_project("proj-atlas")
        elif scene == "boreas":
            app.open_project("proj-boreas")
        elif scene == "create-project":
            app.go(ROUTE_PROJECTS)

            def _find_new_card(node):
                if node is None or isinstance(node, (str, int, float, bool)):
                    return None
                if isinstance(node, (list, tuple)):
                    for item in node:
                        found = _find_new_card(item)
                        if found is not None:
                            return found
                    return None
                texts = []
                for attr in ("content", "controls"):
                    texts.append(getattr(node, attr, None))
                if isinstance(node, ft.Container) and node.on_click is not None:
                    flat = _flatten_texts(node)
                    if "新建项目" in flat:
                        return node
                for attr in ("content", "controls"):
                    found = _find_new_card(getattr(node, attr, None))
                    if found is not None:
                        return found
                return None

            def _flatten_texts(node):
                out = []
                def walk(n):
                    if n is None or isinstance(n, (str, int, float, bool)):
                        if isinstance(n, str):
                            out.append(n)
                        return
                    if isinstance(n, (list, tuple)):
                        for item in n:
                            walk(item)
                        return
                    if isinstance(n, ft.Text) and n.value:
                        out.append(str(n.value))
                    for attr in ("content", "controls"):
                        walk(getattr(n, attr, None))
                walk(node)
                return out

            card = _find_new_card(app.page)
            if card is not None:
                card.on_click(None)
        elif scene == "ideas":
            app.go(ROUTE_IDEAS)
        elif scene == "archive":
            app.go(ROUTE_ARCHIVE)
        elif scene == "ai-running":
            app.run_review()
        elif scene == "ai-running-node":
            app.run_review()
            await asyncio.sleep(0.9)
            app.open_node("proj-atlas", "node-tests")  # 流式期间切换节点,验证界面不阻塞
        elif scene == "ai-awaiting":
            app.run_review()
        elif scene == "artifact":
            app.open_artifact(_ARTIFACT_PATH)
        if shot:
            # 内置 Screenshot 服务自截,不依赖 OS 屏幕录制权限
            await asyncio.sleep(0.8)
            png = await app.page.take_screenshot(pixel_ratio=2, delay=0.4)
            with open(shot, "wb") as f:
                f.write(png)
            print("saved", shot, flush=True)
            if _UI == "desktop":  # 网页模式没有窗口句柄,destroy 仅桌面有效
                try:
                    await app.page.window.destroy()
                except RuntimeError:
                    pass  # 会话先于 destroy 关闭(自截即退),窗口随进程退出

    return _task


def _review_context(service: WorkspaceService):
    """把项目状态压成审查上下文;runtime 不直接接触 workspace 写接口。"""

    def build(request: RunRequest) -> str:
        project = service.project(request.project_id)
        if project is None:
            return f"项目 {request.project_id} 不存在。"
        lines = [
            f"项目:{project.name}({project.project_id})",
            f"目标:{project.goal}",
            f"阶段:{project.phase} · 当前焦点:{project.current_focus} · 里程碑:{project.next_milestone}",
            "行动:",
        ]
        for action in project.actions:
            idle = (date.today() - action.last_meaningful_update_at).days
            lines.append(
                f"- {action.action_id} {action.title} [{action.status}] 最后实质更新 {idle} 天前"
            )
        stalled = service.stalled_actions(project_id=project.project_id)
        if stalled:
            lines.append(
                "长期停滞(15 天以上未实质更新):"
                + ",".join(a.action_id for a in stalled)
            )
        recent = [
            e
            for e in service.activity()
            if e.project_id in ("", project.project_id)
        ][-10:]
        if recent:
            lines.append("最近活动:")
            lines.extend(f"- {e.occurred_at.isoformat()} {e.kind} {e.label}" for e in recent)
        return "\n".join(lines)

    return build


def _build_runtime(provider: str, service: WorkspaceService, args) -> object:
    if provider != "openai":
        return FakeRuntime()
    return OpenAICompatibleRuntime(
        base_url=args.ai_base_url,
        model=args.ai_model,
        api_key=args.ai_api_key,
        build_context=_review_context(service),
    )


def _build_service(vault: str | None) -> WorkspaceService:
    """--vault 显式指定才落盘;不带参数保持内存演示(不触真实 vault)。"""

    if vault is None:
        projects, activity = load_demo_workspace()
        return WorkspaceService(projects, activity)

    from workbench.domain.fixtures import demo_day_seed
    from workbench.storage import WorkspaceStorage

    storage = WorkspaceStorage(Path(vault))
    service = WorkspaceService.open(storage)
    if service.projects():
        return service
    # 全新 vault:写入演示工作区作为可编辑起点(此后归用户所有)。
    projects, activity = load_demo_workspace()
    seed = demo_day_seed()
    service = WorkspaceService(
        projects, activity, days={seed.day: seed}, storage=storage
    )
    for project in projects:
        storage.save_project(project)
        for node in project.outline:
            storage.save_node(project.project_id, node)
    storage.save_day(seed)
    return service


def _handle_watched_file(app: "WorkbenchApp", path: Path):
    """监听文件 → file_route:高置信自动追加(可撤销),低置信提示待确认。

    只做 CPU/IO 的部分在 watch 循环里已放到线程;本函数内的 UI 反馈
    经 page 的 snackbar,可跨线程发送。
    """

    service = app.service
    decision = route_file(
        _TEXT_RUNTIME, _LIBRARY, projects_summary(service), path
    )
    if decision.auto_append:
        entry = service.append_project_progress(
            decision.project_id, decision.progress_entry
        )
        project = service.project(decision.project_id)
        name = project.name if project else decision.project_id

        def undo(_e):
            service.remove_project_progress(decision.project_id, entry)
            tell(app.page, "已撤销自动追加的进度")
            app.page.update()

        undo_snackbar(
            app.page,
            f"《{path.name}》已自动归档到「{name}」进度",
            "撤销",
            undo,
        )
    elif decision.confidence == "low":
        tell(
            app.page,
            f"《{path.name}》低置信,未写入,请手动确认:"
            + (decision.progress_entry or decision.reason),
        )
    # confidence == none:与本工作区无关,留痕活动流之外,不打扰。


def _watch_task(app: "WorkbenchApp"):
    """--watch-dir 的轮询循环;每 5 秒扫描一次新文件。

    route_file 可能阻塞(openai 端点),放线程执行,不冻结事件循环;
    目录被移除等 OSError 只提示一次,不杀循环。
    """

    watcher = FileWatcher(_WATCH_DIR)
    warned = {"scan": False}

    async def _loop():
        while True:
            await asyncio.sleep(5)
            try:
                fresh = watcher.scan_once()
                warned["scan"] = False
            except OSError as exc:
                if not warned["scan"]:
                    warned["scan"] = True
                    tell(app.page, f"监听目录不可用:{exc}")
                continue
            for path in fresh:
                await asyncio.to_thread(_handle_watched_file, app, path)

    return _loop


def main(page: ft.Page):
    page.title = "个人工作台 v2"
    page.padding = 0
    page.bgcolor = THEME["canvas"]
    # 字体:Microsoft YaHei UI(entp-manual 基准);捆绑 Noto 作为离线兜底。
    page.fonts = {"Workbench": "/NotoSansSC-VF.ttf"}
    page.theme = ft.Theme(font_family="Microsoft YaHei UI")
    if _UI == "desktop":  # page.window.* 仅桌面有效,web 路径守卫
        page.window.width = 1440
        page.window.height = 900
    if os.environ.get("SPIKE_SHOT"):
        page.enable_screenshots = True  # 必须在 page.add 之前设置
    app = WorkbenchApp(page, _SERVICE, _RUNTIME)
    app.render()
    if _WATCH_DIR is not None and _LIBRARY is not None and _TEXT_RUNTIME is not None:
        page.run_task(_watch_task(app))
    if os.environ.get("SPIKE_SCENE") or os.environ.get("SPIKE_SHOT"):
        page.run_task(_scene_task(app))


_VAULT: str | None = None
_RUNTIME = None
_TEXT_RUNTIME = None
_LIBRARY: PromptLibrary | None = None
_SERVICE: WorkspaceService | None = None
_UI = "web"  # 运行形态;__main__ 里按 --ui 覆盖
_WATCH_DIR: Path | None = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="个人工作台 v2(Flet)")
    parser.add_argument(
        "--vault",
        help="数据目录(如 data-issue-vault/v2);不指定则运行内存演示数据",
    )
    parser.add_argument(
        "--provider",
        choices=("fake", "openai"),
        default="fake",
        help="AI runtime:fake(默认,离线演示)或 openai(OpenAI 兼容端点)",
    )
    parser.add_argument("--ai-base-url", default=os.environ.get("WORKBENCH_AI_BASE_URL", ""))
    parser.add_argument("--ai-model", default=os.environ.get("WORKBENCH_AI_MODEL", ""))
    parser.add_argument("--ai-api-key", default=os.environ.get("WORKBENCH_AI_API_KEY", ""))
    parser.add_argument(
        "--ui",
        choices=("web", "desktop"),
        default="web",
        help="运行形态:web(默认,浏览器访问,公司内网部署)或 desktop(桌面窗口)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="web 模式监听地址;公司部署在办公机/服务器时用 0.0.0.0",
    )
    parser.add_argument("--port", type=int, default=8550, help="web 模式端口")
    parser.add_argument(
        "--watch-dir",
        default="",
        help="监听目录:新 .md/.txt 经 file_route 自动归档(高置信可撤销);缺省不监听",
    )
    _args = parser.parse_args()
    _VAULT = _args.vault
    _UI = _args.ui
    _WATCH_DIR = Path(_args.watch_dir) if _args.watch_dir else None
    if _args.provider == "openai" and not (_args.ai_base_url and _args.ai_model):
        parser.error("--provider openai 需要 --ai-base-url 与 --ai-model(或对应环境变量)")
    # service 只建一次:app 与 AI 审查上下文共享同一份正式状态。
    _SERVICE = _build_service(_VAULT)
    _RUNTIME = _build_runtime(_args.provider, _SERVICE, _args)
    # 提示词库 + 草稿文本运行时(TodayHub 用);与审查 runtime 是两条线。
    _LIBRARY = PromptLibrary()
    _TEXT_RUNTIME = (
        OpenAITextRuntime(_args.ai_base_url, _args.ai_model, _args.ai_api_key)
        if _args.provider == "openai"
        else FakePromptRuntime()
    )
    view = ft.AppView.FLET_APP if _UI == "desktop" else ft.AppView.WEB_BROWSER
    ft.run(main, view=view, host=_args.host, port=_args.port, assets_dir="fonts")
