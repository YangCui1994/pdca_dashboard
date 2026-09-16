"""版本 D「结构画布」:archify 思路的产品内实现——项目即卡片,空间即结构。

交互哲学:
- 项目是画布上的卡片,可拖拽排布(布局持久化到 ux-2026-09/canvas_layout.json);
  「适应窗口」一键回到网格,画布不提供 minimap(原型阶段砍掉)。
- 点卡片看项目详情,两种形态(--detail 参数,供对比试验):
    side   默认;右侧固定详情栏,点卡片栏内切换,无任何弹层
    expand 点中的卡片原位展开成大卡(大纲+行动内嵌),再点收起
- 行动状态色块点击直接循环切换(set_action_status,不经 AI);停滞 15 天的
  行动标红并显示真实停滞天数。
- 卡片元信息行:最近活跃日期 / 进行中行动数 / 停滞数——数据都来自活动流,
  宁空勿假。
- 零 AI:这个版本验证"空间总览能否替代列表导航"。

运行:python -m prototypes.d_structure_canvas.app --vault prototypes/ux-2026-09/demo_vault
     [--detail side|expand] [--port 8550]
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import flet as ft

from prototypes.uxbase.seed_demo import DEFAULT_VAULT
from prototypes.uxbase.ui_kit import STATUS_COLORS, STATUS_LABELS, THEME, hint, tell
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import WorkspaceStorage

LAYOUT_PATH = Path(__file__).resolve().parents[1] / "ux-2026-09" / "canvas_layout.json"
CARD_W, CARD_H = 240, 150
EXPAND_W, EXPAND_H = 430, 470

# --- 纯函数(冒烟测试覆盖) ---------------------------------------------------

_STATUS_CYCLE = ("pending", "in_progress", "waiting", "deferred", "completed")


def next_status(status: str) -> str:
    """点色块循环切换的目标状态(completed 后回到 pending 重新开始)。"""

    return _STATUS_CYCLE[(_STATUS_CYCLE.index(status) + 1) % len(_STATUS_CYCLE)] if status in _STATUS_CYCLE else "pending"


def load_layout(path: Path) -> dict[str, dict[str, float]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_layout(path: Path, layout: dict) -> None:
    path.write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf-8")


def grid_positions(count: int, cols: int = 3, x0: float = 40, y0: float = 30,
                   dx: float = CARD_W + 60, dy: float = CARD_H + 50) -> list[dict]:
    return [{"x": x0 + (i % cols) * dx, "y": y0 + (i // cols) * dy} for i in range(count)]


def merge_layout(project_ids: list[str], stored: dict) -> dict[str, dict[str, float]]:
    """Stored 优先,缺失的用网格补齐(新项目也能出现在画布上)。"""

    grid = grid_positions(len(project_ids))
    merged = {}
    for idx, project_id in enumerate(project_ids):
        pos = stored.get(project_id) or grid[idx]
        merged[project_id] = {"x": float(pos.get("x", grid[idx]["x"])), "y": float(pos.get("y", grid[idx]["y"]))}
    return merged


def project_meta(service: WorkspaceService, project, today: date | None = None) -> dict:
    """卡片元信息:全部来自活动流与行动状态,不编造。"""

    today = today or date.today()
    activity_days = [e.occurred_at for e in service.activity() if e.project_id == project.project_id]
    open_count = sum(1 for a in project.actions if a.status in ("pending", "in_progress", "waiting"))
    stalled = service.stalled_actions(project.project_id, today=today)
    return {
        "last_active": max(activity_days).isoformat() if activity_days else "",
        "open": open_count,
        "stalled": len(stalled),
    }


# --- UI ----------------------------------------------------------------------

class StructureCanvas:
    def __init__(self, page: ft.Page, service: WorkspaceService, detail_mode: str = "side"):
        self.page = page
        self.service = service
        self.today = date.today()
        self.detail_mode = detail_mode
        self.selected_project_id: str | None = None
        self.layout = merge_layout([p.project_id for p in service.projects()], load_layout(LAYOUT_PATH))
        self.canvas = ft.Stack(height=620, expand=True)

    # -- 卡片与画布 ---------------------------------------------------------

    def _meta_row(self, project) -> ft.Row:
        meta = project_meta(self.service, project, self.today)
        bits = [
            ft.Text(f"活跃 {meta['last_active'] or '—'}", size=11, color=THEME["muted"]),
            ft.Text(f"进行中 {meta['open']}", size=11, color=THEME["info"]),
        ]
        if meta["stalled"]:
            bits.append(ft.Text(f"停滞 {meta['stalled']}", size=11, color=THEME["stall"], weight=ft.FontWeight.BOLD))
        return ft.Row(bits, spacing=10)

    def _action_row(self, project, action, stalled_ids) -> ft.Row:
        is_stalled = action.action_id in stalled_ids
        return ft.Row(
            [
                ft.Container(
                    ft.Text(STATUS_LABELS[action.status], size=10, color=ft.Colors.WHITE),
                    bgcolor=THEME["stall"] if is_stalled else STATUS_COLORS[action.status],
                    border_radius=8,
                    padding=ft.Padding.only(left=8, right=8, top=2, bottom=2),
                    on_click=self.make_cycle(project.project_id, action),
                    tooltip="点击切换状态",
                ),
                ft.Text(
                    action.title + (f" ⚠ 停滞 {(self.today - action.last_meaningful_update_at).days} 天" if is_stalled else ""),
                    expand=True, size=12,
                ),
            ],
            spacing=8,
        )

    def card(self, project) -> ft.GestureDetector:
        pos = self.layout[project.project_id]
        meta = project_meta(self.service, project, self.today)
        body = ft.Container(
            ft.Column(
                [
                    ft.Text(project.name, size=15, weight=ft.FontWeight.BOLD),
                    ft.Text(project.goal or "未填目标", size=11, color=THEME["muted"], max_lines=2),
                    self._meta_row(project),
                    ft.Text(f"焦点:{project.current_focus or '未填'}", size=11, max_lines=1),
                    ft.Text("点击看详情", size=10, color=THEME["muted"]),
                ],
                spacing=5,
            ),
            width=CARD_W,
            height=CARD_H,
            bgcolor=THEME["panel"],
            border=ft.Border.all(2, THEME["stall"] if meta["stalled"] else THEME["line"]),
            border_radius=14,
            padding=12,
        )

        def on_pan(event: ft.DragUpdateEvent):
            # 钳制在可视区内:卡片永远不会被拖丢
            max_x = (self.page.window.width or 1440) - CARD_W - 40
            max_y = (self.page.window.height or 900) - CARD_H - 120
            card.left = min(max(0, card.left + event.local_delta.x), max(0, max_x))
            card.top = min(max(0, card.top + event.local_delta.y), max(0, max_y))
            self.layout[project.project_id] = {"x": card.left, "y": card.top}
            self.page.update()

        def on_pan_end(event):
            save_layout(LAYOUT_PATH, self.layout)

        def on_tap(event):
            self.select_project(project.project_id)

        card = ft.GestureDetector(
            content=body,
            left=pos["x"],
            top=pos["y"],
            drag_interval=10,
            on_pan_update=on_pan,
            on_pan_end=on_pan_end,
            on_tap=on_tap,
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        return card

    def expanded_card(self, project) -> ft.Container:
        """expand 形态:选中的卡片原位展开(展开即聚焦,不再拖拽)。"""

        pos = self.layout[project.project_id]
        stalled_ids = {a.action_id for a in self.service.stalled_actions(project.project_id, today=self.today)}
        rows = [
            ft.Row(
                [
                    ft.Text(project.name, size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.TextButton("收起", on_click=lambda e: self.collapse()),
                ]
            ),
            ft.Text(f"阶段:{project.phase} · 里程碑:{project.next_milestone or '未填'}", size=11, color=THEME["muted"]),
            ft.Text("大纲", weight=ft.FontWeight.BOLD, size=12),
        ]
        for node in project.outline[:6]:
            rows.append(
                ft.Container(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION, size=13, color=THEME["muted"]),
                            ft.Text(node.title, size=12, expand=True),
                            ft.Text(f"{len(node.resources)} 资源", size=10, color=THEME["muted"]),
                        ]
                    ),
                    bgcolor="#f6f5f2", border_radius=8, padding=ft.Padding.only(left=8, right=8, top=4, bottom=4),
                )
            )
        rows.append(ft.Text("行动(点色块切换状态)", weight=ft.FontWeight.BOLD, size=12))
        for action in project.actions:
            rows.append(self._action_row(project, action, stalled_ids))
        body = ft.Container(
            ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO),
            width=EXPAND_W,
            height=EXPAND_H,
            bgcolor=THEME["panel"],
            border=ft.Border.all(2, THEME["accent"]),
            border_radius=14,
            padding=14,
        )
        return ft.Container(body, left=pos["x"], top=pos["y"])

    def collapse(self):
        self.selected_project_id = None
        self.rebuild()

    def rebuild(self):
        cards = []
        for project in self.service.projects():
            if self.detail_mode == "expand" and project.project_id == self.selected_project_id:
                cards.append(self.expanded_card(project))
            else:
                cards.append(self.card(project))
        self.canvas.controls = cards
        if hasattr(self, "toolbar_row"):
            self.toolbar_row.controls[1] = ft.Text(
                f"{len(self.layout)} 个项目 · 拖拽排布,点击看详情({self.detail_mode} 形态)",
                size=12, color=THEME["muted"],
            )
        if self.detail_mode == "side":
            self.rebuild_detail()
        self.page.update()

    def select_project(self, project_id: str):
        if self.detail_mode == "side":
            self.selected_project_id = project_id
            self.rebuild()
        else:
            self.selected_project_id = None if self.selected_project_id == project_id else project_id
            self.rebuild()

    def fit_window(self, event):
        self.layout = merge_layout(
            [p.project_id for p in self.service.projects()], {}
        )
        save_layout(LAYOUT_PATH, self.layout)
        self.rebuild()
        tell(self.page, "已恢复网格布局")

    # -- 详情(side 形态的右栏 / expand 形态内嵌) ----------------------------

    def detail_rows(self, project) -> list[ft.Control]:
        rows = [
            ft.Text(project.name, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(f"阶段:{project.phase} · 里程碑:{project.next_milestone or '未填'}", size=11, color=THEME["muted"]),
            ft.Text("大纲", weight=ft.FontWeight.BOLD, size=12),
        ]
        for node in project.outline:
            rows.append(
                ft.Container(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION, size=13, color=THEME["muted"]),
                            ft.Text(node.title, size=12, expand=True),
                            ft.Text(f"{len(node.resources)} 资源", size=10, color=THEME["muted"]),
                        ]
                    ),
                    bgcolor="#f6f5f2", border_radius=8, padding=ft.Padding.only(left=8, right=8, top=4, bottom=4),
                )
            )
        rows.append(ft.Text("行动(点色块切换状态)", weight=ft.FontWeight.BOLD, size=12))
        stalled_ids = {a.action_id for a in self.service.stalled_actions(project.project_id, today=self.today)}
        for action in project.actions:
            rows.append(self._action_row(project, action, stalled_ids))
        return rows

    def rebuild_detail(self):
        project = self.service.project(self.selected_project_id) if self.selected_project_id else None
        if project is None:
            self.detail_panel.content = hint("点画布上的卡片,在这里看结构")
        else:
            self.detail_panel.content = ft.Column(self.detail_rows(project), spacing=8, scroll=ft.ScrollMode.AUTO)

    def make_cycle(self, project_id: str, action):
        def handler(event):
            new_status = next_status(action.status)
            if self.service.set_action_status(project_id, action.action_id, new_status):
                tell(self.page, f"「{action.title[:16]}」→ {STATUS_LABELS[new_status]}")
                self.rebuild()
            else:
                tell(self.page, "状态未变化")

        return handler

    def build(self):
        self.toolbar_row = ft.Row(
            [
                ft.Text("项目结构画布", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(self.layout)} 个项目 · 拖拽排布,点击看详情({self.detail_mode} 形态)", size=12, color=THEME["muted"]),
                ft.Container(expand=True),
                ft.TextButton("适应窗口(重置布局)", on_click=self.fit_window),
            ]
        )
        if self.detail_mode == "side":
            self.detail_panel = ft.Container(
                width=340,
                bgcolor=THEME["panel"],
                border=ft.Border.all(1, THEME["line"]),
                border_radius=14,
                padding=14,
                content=hint("点画布上的卡片,在这里看结构"),
            )
        self.rebuild()
        scrollable = ft.Column([self.canvas], scroll=ft.ScrollMode.AUTO, expand=True)
        if self.detail_mode == "side":
            return ft.Column(
                [
                    self.toolbar_row,
                    ft.Row(
                        [scrollable, ft.VerticalDivider(width=1), self.detail_panel],
                        spacing=12,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ],
                spacing=10,
                expand=True,
            )
        return ft.Column([self.toolbar_row, scrollable], spacing=10, expand=True)


def main(page: ft.Page):
    if os.environ.get("UX_SHOT"):
        page.enable_screenshots = True  # 须在页面注册前设置
    page.title = f"D · 结构画布({_DETAIL})"
    page.padding = 18
    page.bgcolor = THEME["canvas"]
    app = StructureCanvas(page, _SERVICE, detail_mode=_DETAIL)
    page.add(app.build())
    page.update()

    async def _ux_shot_task():
        import asyncio as _asyncio
        await _asyncio.sleep(1.0)
        png = await page.take_screenshot(pixel_ratio=2, delay=ft.Duration(milliseconds=400))
        shot_path = os.environ["UX_SHOT"]
        Path(shot_path).write_bytes(png)
        print("saved", shot_path, flush=True)
        try:
            page.window.destroy()
        except Exception:
            pass

    if os.environ.get("UX_SHOT"):
        page.run_task(_ux_shot_task)


_SERVICE: WorkspaceService | None = None
_DETAIL = "side"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="原型 D · 结构画布")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT))
    parser.add_argument("--detail", choices=("side", "expand"), default="side",
                        help="详情形态:side=右栏固定 expand=卡片原位展开")
    parser.add_argument("--desktop", action="store_true", help="桌面窗口模式(默认网页)")
    parser.add_argument("--port", type=int, default=8550, help="网页模式端口")
    args = parser.parse_args()
    _DETAIL = args.detail
    _SERVICE = WorkspaceService.open(WorkspaceStorage(Path(args.vault)))
    view = ft.AppView.FLET_APP if args.desktop else ft.AppView.WEB_BROWSER
    ft.app(main, view=view, port=args.port)
