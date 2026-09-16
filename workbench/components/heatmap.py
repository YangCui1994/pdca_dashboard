"""GitHub-style activity heatmap with purple intensity dots."""

from __future__ import annotations

from datetime import date, timedelta

import flet as ft

from workbench.components import FONT_SMALL, THEME


def _dot_color(count: int) -> str:
    if count <= 0:
        return THEME["dot_empty"]
    if count <= 1:
        return THEME["purple_faint"]
    if count <= 2:
        return THEME["purple_mid"]
    if count <= 4:
        return "#8277E8"
    return THEME["purple"]


def _day_cell(day: date, count: int, on_pick_date, compact: bool):
    dot = ft.Container(
        width=12 if compact else 14,
        height=12 if compact else 14,
        border_radius=99,
        bgcolor=_dot_color(count),
        tooltip=f"{day.isoformat()} · {count} 条有意义活动",
    )
    if compact:
        return ft.Column(
            [dot, ft.Container(height=3)],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    return ft.Container(
        content=dot,
        on_click=lambda _e, d=day: on_pick_date(d) if on_pick_date else None,
        ink=on_pick_date is not None,
        padding=2,
        border_radius=8,
    )


def build_heatmap(
    counts: dict,
    today: date | None = None,
    days: int = 14,
    on_pick_date=None,
    compact: bool = False,
    weeks: int = 0,
) -> ft.Control:
    """Render a dot heatmap.

    Default: one row of `days` recent days ending today (compact overview).
    With weeks>0: GitHub-style columns of 7 days (activity page).
    """

    today = today or date.today()
    cells = []

    if weeks > 0:
        total = weeks * 7
        start = today - timedelta(days=total - 1)
        columns = []
        for week in range(weeks):
            col_days = [start + timedelta(days=week * 7 + d) for d in range(7)]
            columns.append(
                ft.Column(
                    [
                        _day_cell(d, counts.get(d, 0), on_pick_date, compact)
                        for d in col_days
                    ],
                    spacing=4,
                )
            )
        grid = ft.Row(columns, spacing=5)
        anchors = []
        for week in range(0, weeks, 2):
            anchor_day = start + timedelta(days=week * 7)
            anchors.append(ft.Text(anchor_day.strftime("%m/%d"), size=FONT_SMALL, color=THEME["text_faint"]))
        legend_row = ft.Row(
            [
                ft.Text("少", size=FONT_SMALL, color=THEME["text_faint"]),
                *[
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=99,
                        bgcolor=_dot_color(c),
                    )
                    for c in (0, 1, 2, 4, 6)
                ],
                ft.Text("多", size=FONT_SMALL, color=THEME["text_faint"]),
            ],
            spacing=4,
        )
        return ft.Column(
            [grid, ft.Container(height=6), legend_row], spacing=0
        )

    start = today - timedelta(days=days - 1)
    day_cells = []
    labels = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        count = counts.get(day, 0)
        day_cells.append(_day_cell(day, count, on_pick_date, compact))
        if offset % 4 == 0 or offset == days - 1:
            labels.append(
                ft.Container(
                    width=12 if compact else 18,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        f"{day.month}/{day.day}" if hasattr(date, "strftime") else "",
                        size=9,
                        color=THEME["text_faint"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )
        else:
            labels.append(
                ft.Container(width=12 if compact else 18)
            )
    legend = ft.Row(
        [
            ft.Text("少", size=FONT_SMALL, color=THEME["text_faint"]),
            *[
                ft.Container(width=10, height=10, border_radius=99, bgcolor=_dot_color(c))
                for c in (0, 1, 2, 4, 6)
            ],
            ft.Text("多", size=FONT_SMALL, color=THEME["text_faint"]),
        ],
        spacing=4,
    )
    return ft.Column(
        [
            ft.Row(day_cells, spacing=6),
            ft.Container(height=2),
            ft.Row(labels, spacing=0),
            ft.Container(height=6),
            legend,
        ],
        spacing=0,
    )
