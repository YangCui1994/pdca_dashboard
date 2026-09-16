"""活动页:GitHub 风格 Heatmap + 当日有意义事件 + 长期停滞列表。"""

from __future__ import annotations

from datetime import date

import flet as ft

from workbench.components import (
    FONT_SMALL,
    FONT_TITLE,
    THEME,
    badge,
    card,
)
from workbench.components.heatmap import build_heatmap
from workbench.domain.models import MEANINGFUL_ACTIVITY_KINDS

_KIND_LABEL = {
    "task_completed": "任务完成",
    "content_updated": "内容更新",
    "resource_added": "资源加入",
    "decision_confirmed": "Decision 确认",
    "proposal_accepted": "Proposal 接受",
}


def build_activity(service, on_pick_date, selected_date: date | None = None) -> ft.Control:
    today = date.today()
    counts = service.heatmap_counts()
    selected = selected_date or today

    day_events = [
        event
        for event in service.activity()
        if event.occurred_at == selected and event.kind in MEANINGFUL_ACTIVITY_KINDS
    ]

    stalled = service.stalled_actions()
    stalled_rows = []
    for action in stalled:
        project = service.project(action.project_id)
        stalled_rows.append(
            ft.Row(
                [
                    ft.Text(
                        f"{project.name if project else '已删除项目'} · {action.title}",
                        size=FONT_SMALL,
                        color=THEME["text"],
                        expand=True,
                    ),
                    badge(
                        f"{(today - action.last_meaningful_update_at).days} 天未更新",
                        THEME["orange"],
                        THEME["orange_soft"],
                    ),
                ],
                spacing=6,
            )
        )

    return ft.Container(
        expand=True,
        padding=ft.Padding(left=22, top=18, right=22, bottom=18),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.TIMELINE, size=20, color=THEME["purple"]),
                        ft.Text(
                            "活动统计",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=THEME["text"],
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            "只统计有意义事件;浏览不计入",
                            size=FONT_SMALL,
                            color=THEME["text_faint"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                card(
                    ft.Column(
                        [
                            ft.Text(
                                "有意义活动热力图(近 8 周,点击日期查看当日事件)",
                                size=FONT_TITLE,
                                weight=ft.FontWeight.W_600,
                                color=THEME["text"],
                            ),
                            ft.Container(height=10),
                            build_heatmap(
                                counts, today=today, weeks=8, on_pick_date=on_pick_date
                            ),
                        ],
                        spacing=0,
                    )
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        ft.Container(
                            expand=True,
                            content=card(
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"当日有意义事件 · {selected.isoformat()}",
                                            size=FONT_TITLE,
                                            weight=ft.FontWeight.W_600,
                                            color=THEME["text"],
                                        ),
                                        ft.Container(height=6),
                                        *(
                                            [
                                                ft.Row(
                                                    [
                                                        badge(
                                                            _KIND_LABEL.get(
                                                                event.kind, event.kind
                                                            ),
                                                            THEME["purple_deep"],
                                                            THEME["purple_soft"],
                                                        ),
                                                        ft.Text(
                                                            f"{event.project_id} · {event.label}",
                                                            size=FONT_SMALL,
                                                            color=THEME["text"],
                                                        ),
                                                    ],
                                                    spacing=8,
                                                )
                                                for event in day_events
                                            ]
                                            or [
                                                ft.Text(
                                                    "当日无有意义事件",
                                                    size=FONT_SMALL,
                                                    color=THEME["text_faint"],
                                                )
                                            ]
                                        ),
                                    ],
                                    spacing=6,
                                )
                            ),
                        ),
                        ft.Container(width=12),
                        ft.Container(
                            width=420,
                            content=card(
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    "长期停滞",
                                                    size=FONT_TITLE,
                                                    weight=ft.FontWeight.W_600,
                                                    color=THEME["text"],
                                                ),
                                                ft.Container(expand=True),
                                                badge(
                                                    f"{len(stalled)}",
                                                    THEME["orange"],
                                                    THEME["orange_soft"],
                                                ),
                                            ]
                                        ),
                                        ft.Text(
                                            "进行中且超过 14 天没有有意义更新",
                                            size=FONT_SMALL,
                                            color=THEME["text_faint"],
                                        ),
                                        ft.Container(height=6),
                                        *(
                                            stalled_rows
                                            or [
                                                ft.Text(
                                                    "无长期停滞项",
                                                    size=FONT_SMALL,
                                                    color=THEME["text_faint"],
                                                )
                                            ]
                                        ),
                                    ],
                                    spacing=6,
                                )
                            ),
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
