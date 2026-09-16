"""Shared visual language for the workbench: light, restrained blue, editorial.

配色与字体基准:entp-manual(https://github.com/TANGuoGUO/entp-manual,
本地 refs/entp-manual/,色板出处 flet_app.py:80-93,完整对照表
refs/SOURCES.md)。键名沿用历史(purple/blue 等仅是"主色/次强调"
语义槽),值已全部换为 entp-manual 色板。
"""

from __future__ import annotations

import flet as ft

# Palette from the entp-manual reference (user-designated style baseline).
THEME = {
    "canvas": "#FBFCFE",       # CANVAS 页面画布
    "card": "#FFFFFF",         # SURFACE 卡片
    "border": "#E7E9EE",       # LINE 边框
    "purple": "#316BEE",       # BLUE 主色
    "purple_deep": "#2457CC",  # BLUE_DARK 主色深
    "purple_soft": "#EEF3FF",  # BLUE_SOFT 主色软底
    "purple_mid": "#6E93F2",   # 主色中间调(热力图中档,同族推导)
    "purple_faint": "#C9D9FB", # 主色浅调(热力图低档,同族推导)
    "green": "#37A46A",
    "green_soft": "#EAF7EF",
    "orange": "#B87818",       # AMBER 等待语义(原型橙弃用)
    "orange_soft": "#FFF6DF",
    "blue": "#316BEE",         # 信息蓝与主色同源
    "blue_soft": "#EEF3FF",
    "stall": "#E45959",        # RED 停滞/错误
    "stall_soft": "#FBE9E9",   # 停滞软底(同族推导)
    "text": "#171A21",         # INK 正文
    "text_sub": "#737986",     # MUTED 次要文字
    "text_faint": "#9BA1AE",   # 更浅的辅助文字(MUTED 同族推导)
    "dot_empty": "#F1F2F5",    # 中性 pill 底
}

# 行动状态 → 语义色(绿=完成、蓝=进行中、琥珀=等待、灰=待开始)。
STATUS_COLORS = {
    "pending": "#737986",
    "in_progress": "#316BEE",
    "waiting": "#B87818",
    "deferred": "#7D6B8F",
    "completed": "#37A46A",
    "cancelled": "#B3B3AD",
}

STATUS_SOFT = {
    "pending": "#F1F2F5",
    "in_progress": "#EEF3FF",
    "waiting": "#FFF6DF",
    "deferred": "#F0EDF4",
    "completed": "#EAF7EF",
    "cancelled": "#F1F2F5",
}

STATUS_LABELS = {
    "pending": "待开始",
    "in_progress": "进行中",
    "waiting": "等待",
    "deferred": "已延后",
    "completed": "已完成",
    "cancelled": "已取消",
}

FONT_SMALL = 12
FONT_BODY = 13
FONT_TITLE = 14
FONT_H = 18

FONT_FAMILY = "Microsoft YaHei UI"  # entp-manual 全局字体
MONO_FAMILY = "Consolas"            # entp-manual 等宽字体


def card(content, padding=14, radius=12):
    """White card with the soft border used across the app."""

    return ft.Container(
        content=content,
        bgcolor=THEME["card"],
        border=ft.Border(
            top=ft.BorderSide(1, THEME["border"]),
            right=ft.BorderSide(1, THEME["border"]),
            bottom=ft.BorderSide(1, THEME["border"]),
            left=ft.BorderSide(1, THEME["border"]),
        ),
        border_radius=radius,
        padding=padding,
    )


def section_title(text, trailing=None):
    row_items = [
        ft.Text(text, size=FONT_TITLE, weight=ft.FontWeight.W_600,
                color=THEME["text"])
    ]
    if trailing is not None:
        row_items.append(ft.Container(expand=True))
        row_items.append(trailing)
    return ft.Row(row_items, spacing=8)


def caption(text):
    return ft.Text(text, size=FONT_SMALL, color=THEME["text_sub"])


def badge(text, fg, bg):
    return ft.Container(
        content=ft.Text(text, size=FONT_SMALL, color=fg, weight=ft.FontWeight.W_500),
        bgcolor=bg,
        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
        border_radius=99,
    )
