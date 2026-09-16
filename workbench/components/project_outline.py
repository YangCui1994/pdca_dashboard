"""Vertical project outline with connecting line, like the reference design."""

from __future__ import annotations

import flet as ft

from workbench.components import THEME

_NODE_ICONS = {
    "goal": ft.Icons.FLAG_OUTLINED,
    "people": ft.Icons.GROUP_OUTLINED,
    "progress": ft.Icons.TRENDING_UP,
    "decision": ft.Icons.GAVEL,
    "test": ft.Icons.SCIENCE_OUTLINED,
    "resource": ft.Icons.LINK,
    "next": ft.Icons.CHECKLIST,
}


def build_project_outline(
    project, on_open_node, active_node_id: str | None = None, warn_node_ids=()
) -> ft.Control:
    """Clickable outline nodes with icons, captions, chevrons, warn dots."""

    rows = []
    for index, node in enumerate(project.outline):
        is_active = node.node_id == active_node_id
        has_warning = node.node_id in warn_node_ids
        head = ft.Row(
            [
                ft.Container(
                    width=26,
                    height=26,
                    border_radius=13,
                    bgcolor=THEME["purple_soft"] if is_active else THEME["canvas"],
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(
                        _NODE_ICONS.get(node.kind, ft.Icons.CIRCLE),
                        size=14,
                        color=THEME["purple"] if is_active else THEME["text_sub"],
                    ),
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    node.title,
                                    size=13,
                                    weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500,
                                    color=THEME["purple_deep"] if is_active else THEME["text"],
                                ),
                                *(
                                    [ft.Container(
                                        width=7,
                                        height=7,
                                        border_radius=99,
                                        bgcolor=THEME["orange"],
                                        tooltip="该节点下有待处理警示",
                                    )]
                                    if has_warning
                                    else []
                                ),
                            ],
                            spacing=6,
                        ),
                        ft.Text(
                            node.note[:18] + ("…" if len(node.note) > 18 else ""),
                            size=11,
                            color=THEME["text_faint"],
                        ),
                    ],
                    spacing=1,
                ),
                ft.Container(expand=True),
                # 文本字形而非 Icon:CHEVRON_RIGHT 的字形墨迹仅约半个字面框,
                # size=14 时实际约 7px,在 13px 标题旁像渲染损坏。
                ft.Text(
                    "›",
                    size=18,
                    weight=ft.FontWeight.W_400,
                    color=THEME["purple"] if is_active else THEME["text_faint"],
                ),
            ],
            spacing=10,
        )
        rows.append(
            ft.Container(
                content=head,
                bgcolor=THEME["purple_soft"] if is_active else None,
                border_radius=10,
                padding=ft.Padding(left=6, top=7, right=8, bottom=7),
                on_click=lambda _e, nid=node.node_id: on_open_node(nid),
                ink=True,
            )
        )
        if index != len(project.outline) - 1:
            rows.append(
                ft.Container(
                    width=2,
                    height=8,
                    bgcolor=THEME["border"],
                    margin=ft.Margin(left=17, top=0, right=0, bottom=0),
                )
            )
    return ft.Column(rows, spacing=2)
