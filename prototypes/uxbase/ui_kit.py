"""原型共用 UI 小件:统一语义色板 + 设计基线里要求的全局行为。

DESIGN_CHECKLIST.md 的落地点:
- 每次写操作统一 snackbar 反馈(tell)
- 危险操作走「执行 + 可撤销 snackbar」而不是弹窗确认(undo_snackbar)
- 空态给引导动作(hint)
"""

from __future__ import annotations

import flet as ft

THEME = {
    "canvas": "#f5f4f1",
    "panel": "#ffffff",
    "ink": "#2b2b28",
    "muted": "#8a8a84",
    "accent": "#d94b26",
    "ok": "#2f7d4f",
    "warn": "#b97a00",
    "info": "#3a6ea5",
    "line": "#e4e2dc",
    "stall": "#c0392b",
}

# 行动状态 → 语义色(与 workbench 语义一致:绿=完成,琥珀=等待,红=停滞)
STATUS_COLORS = {
    "pending": "#8a8a84",
    "in_progress": "#3a6ea5",
    "waiting": "#b97a00",
    "deferred": "#7d6b8f",
    "completed": "#2f7d4f",
    "cancelled": "#b3b3ad",
}
STATUS_LABELS = {
    "pending": "待开始",
    "in_progress": "进行中",
    "waiting": "等待",
    "deferred": "已延后",
    "completed": "已完成",
    "cancelled": "已取消",
}


def tell(page: ft.Page, message: str) -> None:
    """统一写操作反馈:所有落盘动作都通过这里说话。"""

    page.show_dialog(ft.SnackBar(ft.Text(message), bgcolor=THEME["ink"], duration=2200))


def undo_snackbar(page: ft.Page, message: str, undo_label: str, on_undo) -> None:
    """可撤销反馈:删除/自动追加类操作的标准姿势,不打断手。"""

    page.show_dialog(
        ft.SnackBar(
            ft.Row(
                [
                    ft.Text(message, expand=True),
                    ft.TextButton(undo_label, on_click=on_undo, style=ft.ButtonStyle(color=THEME["accent"])),
                ]
            ),
            bgcolor=THEME["ink"],
            duration=6000,
        )
    )


def hint(message: str, action_label: str | None = None, on_action=None) -> ft.Container:
    """空态:说明这里会有什么 + 一个引导动作。"""

    row = ft.Row(
        [ft.Text(message, color=THEME["muted"], size=13)],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    if action_label and on_action is not None:
        row.controls.append(ft.TextButton(action_label, on_click=on_action))
    return ft.Container(
        content=row,
        padding=28,
        alignment=ft.Alignment(0, 0),
        border=ft.Border.all(1, THEME["line"]),
        border_radius=12,
    )
