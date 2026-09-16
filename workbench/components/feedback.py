"""统一反馈组件:snackbar / 可撤销反馈 / 空态(entp-manual 配色)。

DESIGN_CHECKLIST 的落地点:
- 每次写操作统一 snackbar 反馈(tell)
- 危险操作走「执行 + 可撤销 snackbar」而不是弹窗确认(undo_snackbar)
- 空态给引导动作(hint)
- 错误单独用 error 色调,绝不把失败伪装成正常反馈

Flet 0.86:SnackBar 经 page.show_dialog 弹出(无 page.open)。
"""

from __future__ import annotations

import flet as ft

from workbench.components import THEME

_UNDO_ACCENT = "#A9C4FF"  # 深色 snackbar 上的主色提亮变体,保证对比度


def tell(page: ft.Page | None, message: str) -> None:
    """统一写操作反馈:所有落盘动作都通过这里说话。

    page 为 None(离线构建/测试)时静默跳过,不阻碍逻辑执行。
    """

    if page is None:
        return
    page.show_dialog(ft.SnackBar(ft.Text(message), bgcolor=THEME["text"], duration=2200))


def error(page: ft.Page | None, message: str) -> None:
    """失败反馈:AI 失败/非法输入走这里,与成功反馈可区分。"""

    if page is None:
        return
    page.show_dialog(
        ft.SnackBar(ft.Text(message), bgcolor="#3A2530", duration=4000)
    )


def undo_snackbar(page: ft.Page | None, message: str, undo_label: str, on_undo) -> None:
    """可撤销反馈:删除/自动追加类操作的标准姿势,不打断手。"""

    if page is None:
        return
    page.show_dialog(
        ft.SnackBar(
            ft.Row(
                [
                    ft.Text(message, expand=True),
                    ft.TextButton(
                        undo_label,
                        on_click=on_undo,
                        style=ft.ButtonStyle(color=_UNDO_ACCENT),
                    ),
                ]
            ),
            bgcolor=THEME["text"],
            duration=6000,
        )
    )


def hint(message: str, action_label: str | None = None, on_action=None) -> ft.Container:
    """空态:说明这里会有什么 + 一个引导动作。"""

    row = ft.Row(
        [ft.Text(message, color=THEME["text_sub"], size=13)],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    if action_label and on_action is not None:
        row.controls.append(
            ft.TextButton(
                action_label,
                on_click=on_action,
                style=ft.ButtonStyle(color=THEME["purple"]),
            )
        )
    return ft.Container(
        content=row,
        padding=28,
        alignment=ft.Alignment(0, 0),
        border=ft.Border.all(1, THEME["border"]),
        border_radius=12,
    )
