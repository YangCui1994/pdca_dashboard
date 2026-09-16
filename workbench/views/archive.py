"""归档页:已归档想法(可恢复)+ 已完成/已取消行动(只读)。

归档是查看与恢复的地方,不提供编辑;行动状态仍只经 AI 提案通道变化。
"""

from __future__ import annotations

import flet as ft

from workbench.components import FONT_SMALL, FONT_TITLE, THEME, badge, card, section_title
from workbench.domain.models import (
    CANCELLED,
    COMPLETED,
    IDEA_PENDING,
)


def build_archive(service, on_refresh=None) -> ft.Control:
    def _refresh():
        if on_refresh is not None:
            on_refresh()

    archived_ideas = [idea for idea in service.ideas() if idea.status == "archived"]
    idea_rows = []
    for idea in archived_ideas:
        idea_rows.append(
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIGHTBULB_OUTLINED, size=14, color=THEME["text_faint"]
                    ),
                    ft.Text(
                        idea.text, size=FONT_SMALL, color=THEME["text_sub"], expand=True
                    ),
                    ft.TextButton(
                        "恢复待整理",
                        style=ft.ButtonStyle(
                            color=THEME["purple_deep"],
                            padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                        ),
                        on_click=lambda _e, idea_id=idea.idea_id: (
                            service.set_idea_status(idea_id, IDEA_PENDING),
                            _refresh(),
                        ),
                    ),
                ],
                spacing=8,
            )
        )

    closed_actions = [
        (project, action)
        for project in service.projects()
        for action in project.actions
        if action.status in (COMPLETED, CANCELLED)
    ]
    action_rows = [
        ft.Row(
            [
                ft.Container(
                    width=7, height=7, border_radius=99, bgcolor=THEME["green"]
                    if action.status == COMPLETED
                    else THEME["text_faint"]
                ),
                ft.Text(action.title, size=FONT_SMALL, color=THEME["text"], expand=True),
                ft.Text(project.name, size=FONT_SMALL, color=THEME["text_faint"]),
                badge(
                    "已完成" if action.status == COMPLETED else "已取消",
                    THEME["text_sub"],
                    THEME["dot_empty"],
                ),
            ],
            spacing=8,
        )
        for project, action in closed_actions
    ]

    return ft.Container(
        expand=True,
        padding=ft.Padding(left=22, top=18, right=22, bottom=18),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ARCHIVE_OUTLINED, size=20, color=THEME["purple"]),
                        ft.Text(
                            "归档",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=THEME["text"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                card(
                    ft.Column(
                        [
                            section_title(
                                "已归档想法",
                                ft.Text(
                                    f"{len(archived_ideas)} 条",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                ),
                            ),
                            ft.Container(height=6),
                            *(idea_rows or [
                                ft.Text(
                                    "暂无已归档想法。",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                )
                            ]),
                        ],
                        spacing=4,
                    )
                ),
                ft.Container(height=12),
                card(
                    ft.Column(
                        [
                            section_title(
                                "已完成 / 已取消行动",
                                ft.Text(
                                    f"{len(action_rows)} 条",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                ),
                            ),
                            ft.Container(height=6),
                            *(action_rows or [
                                ft.Text(
                                    "暂无。",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                )
                            ]),
                        ],
                        spacing=4,
                    )
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
