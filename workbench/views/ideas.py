"""想法页:按状态分组的想法列表,支持保留/归档/恢复。

想法原文不可编辑(P2′「Capture 原文不可覆盖」契约),只有状态流转;
所有写入经 WorkspaceService.set_idea_status。
"""

from __future__ import annotations

import flet as ft

from workbench.components import FONT_SMALL, FONT_TITLE, THEME, badge, card, section_title
from workbench.domain.models import (
    IDEA_ARCHIVED,
    IDEA_KEPT,
    IDEA_PENDING,
)

_STATUS_LABELS = {
    IDEA_PENDING: "待整理",
    IDEA_KEPT: "已保留",
    IDEA_ARCHIVED: "已归档",
}

_STATUS_TAG = {
    IDEA_PENDING: (THEME["orange"], THEME["orange_soft"]),
    IDEA_KEPT: (THEME["green"], THEME["green_soft"]),
    IDEA_ARCHIVED: (THEME["text_sub"], THEME["dot_empty"]),
}

# 每个状态可流转到的目标:待整理 → 保留/归档;已保留 → 归档/退回;已归档 → 恢复。
_TRANSITIONS = {
    IDEA_PENDING: ((IDEA_KEPT, "保留"), (IDEA_ARCHIVED, "归档")),
    IDEA_KEPT: ((IDEA_ARCHIVED, "归档"), (IDEA_PENDING, "退回待整理")),
    IDEA_ARCHIVED: ((IDEA_PENDING, "恢复待整理"),),
}


def _idea_row(idea, service, on_refresh) -> ft.Control:
    def _set_status(status):
        def handler(_e=None):
            service.set_idea_status(idea.idea_id, status)
            on_refresh()

        return handler

    actions = [
        ft.TextButton(
            label,
            style=ft.ButtonStyle(
                color=THEME["purple_deep"],
                padding=ft.Padding(left=8, top=2, right=8, bottom=2),
            ),
            on_click=_set_status(status),
        )
        for status, label in _TRANSITIONS[idea.status]
    ]
    return ft.Row(
        [
            ft.Icon(ft.Icons.LIGHTBULB_OUTLINED, size=14, color=THEME["purple"]),
            ft.Text(idea.text, size=FONT_SMALL, color=THEME["text"], expand=True),
            badge(_STATUS_LABELS[idea.status], *_STATUS_TAG[idea.status]),
            *actions,
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_ideas(service, on_refresh=None) -> ft.Control:
    def _refresh():
        if on_refresh is not None:
            on_refresh()

    ideas = service.ideas()
    groups = []
    for status in (IDEA_PENDING, IDEA_KEPT, IDEA_ARCHIVED):
        members = [idea for idea in ideas if idea.status == status]
        rows = [_idea_row(idea, service, _refresh) for idea in members]
        if not rows:
            rows = [
                ft.Text(
                    "暂无,用底部快速记录添加想法。"
                    if status == IDEA_PENDING
                    else "暂无。",
                    size=FONT_SMALL,
                    color=THEME["text_faint"],
                )
            ]
        groups.append(
            card(
                ft.Column(
                    [
                        section_title(
                            _STATUS_LABELS[status],
                            ft.Text(
                                f"{len(members)} 条",
                                size=FONT_SMALL,
                                color=THEME["text_faint"],
                            ),
                        ),
                        ft.Container(height=6),
                        *rows,
                    ],
                    spacing=4,
                )
            )
        )

    return ft.Container(
        expand=True,
        padding=ft.Padding(left=22, top=18, right=22, bottom=18),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=20, color=THEME["purple"]),
                        ft.Text(
                            "想法",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=THEME["text"],
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"共 {len(ideas)} 条",
                            size=FONT_SMALL,
                            color=THEME["text_faint"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                *groups,
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
