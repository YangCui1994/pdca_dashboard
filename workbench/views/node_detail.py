"""节点详情:保留主/二级导航,标题/备注/资源可编辑,标签与关系展示。"""

from __future__ import annotations

import flet as ft

from workbench.components import (
    FONT_SMALL,
    FONT_TITLE,
    THEME,
    badge,
    card,
)
from workbench.components.editable import (
    build_add_row,
    build_editable_label,
    build_editable_markdown,
)
from workbench.components.project_outline import build_project_outline

_TAG_STYLES = {
    "常用": (THEME["green"], THEME["green_soft"]),
    "环境": (THEME["blue"], THEME["blue_soft"]),
    "会议": (THEME["purple_deep"], THEME["purple_soft"]),
    "记录": (THEME["text_sub"], THEME["dot_empty"]),
    "申请": (THEME["orange"], THEME["orange_soft"]),
    "外部": (THEME["blue"], THEME["blue_soft"]),
}

_FILE_ICONS = {
    "表格": ft.Icons.TABLE_CHART_OUTLINED,
    "文档": ft.Icons.DESCRIPTION_OUTLINED,
    "笔记": ft.Icons.STICKY_NOTE_2_OUTLINED,
}


def build_node_detail(
    service, project_id: str, node_id: str, on_back, on_open_node, on_refresh=None
) -> ft.Control:
    project = service.project(project_id)
    if project is None or not project.outline:
        return ft.Container(
            padding=ft.Padding(left=22, top=18, right=22, bottom=18),
            content=ft.Text(
                "节点不存在或项目为空",
                size=13,
                color=THEME["text_sub"],
            ),
        )
    node = next(
        (n for n in project.outline if n.node_id == node_id), project.outline[0]
    )

    def _refresh():
        if on_refresh is not None:
            on_refresh()

    def _rename_title(value):
        service.rename_node(project_id, node.node_id, title=value)

    def _save_note(value):
        service.rename_node(project_id, node.node_id, note=value)

    def _rename_resource(resource_id, field):
        def handler(value):
            service.rename_resource(
                project_id, node.node_id, resource_id, **{field: value}
            )

        return handler

    def _remove_resource(resource_id):
        def handler(_e=None):
            service.remove_resource(project_id, node.node_id, resource_id)
            _refresh()

        return handler

    secondary_nav = ft.Column(
        [
            ft.TextButton("返回项目总览", icon=ft.Icons.ARROW_BACK, on_click=lambda _e: on_back()),
            ft.Container(height=4),
            build_project_outline(
                project, on_open_node=on_open_node, active_node_id=node.node_id
            ),
        ],
        spacing=4,
    )

    note_editor = build_editable_markdown(
        node.note,
        _save_note,
        on_refresh=_refresh,
        min_lines=10,
        empty_hint="双击此处写本节点备注(Markdown)",
    )

    resource_cards = []
    for resource in node.resources:
        name_label = build_editable_label(
            resource.name,
            _rename_resource(resource.resource_id, "name"),
            size=13,
            color=THEME["purple_deep"],
            on_refresh=_refresh,
        )
        source_label = build_editable_label(
            resource.source,
            _rename_resource(resource.resource_id, "source"),
            size=FONT_SMALL,
            color=THEME["text_faint"],
            placeholder="补充链接…",
            on_refresh=_refresh,
        )
        remove_btn = ft.IconButton(
            ft.Icons.CLOSE,
            icon_size=13,
            icon_color=THEME["text_faint"],
            tooltip="移除该资源",
            style=ft.ButtonStyle(padding=0),
            on_click=_remove_resource(resource.resource_id),
        )
        resource_cards.append(
            ft.Row(
                [
                    ft.Icon(
                        _FILE_ICONS.get(resource.kind, ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
                        size=16,
                        color=THEME["purple"],
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    name_label,
                                    *[
                                        badge(
                                            tag,
                                            *_TAG_STYLES.get(
                                                tag, (THEME["purple_deep"], THEME["purple_soft"])
                                            ),
                                        )
                                        for tag in resource.tags
                                    ],
                                ],
                                spacing=6,
                            ),
                            source_label,
                        ],
                        spacing=1,
                    ),
                    remove_btn,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    relations = [
        "当前进展 → 测试资源(产出验证依据)",
        "关键判断 → 待推进事项(决定下一步)",
    ]

    breadcrumb = ft.Row(
        [
            ft.Text("项目", size=FONT_SMALL, color=THEME["text_faint"]),
            ft.Text("/", size=FONT_SMALL, color=THEME["text_faint"]),
            ft.Text(project.name, size=FONT_SMALL, color=THEME["purple_deep"]),
            ft.Text("/", size=FONT_SMALL, color=THEME["text_faint"]),
            ft.Text(node.title, size=FONT_SMALL, color=THEME["text_sub"]),
        ],
        spacing=4,
    )

    def _node_last_update(project_id: str, node_title: str):
        """真实最后更新:活动流里最近一条提到本节点标题的事件;无则留空。"""

        last = None
        for event in service.activity():
            if event.project_id != project_id or node_title not in event.label:
                continue
            if last is None or event.occurred_at > last:
                last = event.occurred_at
        return last

    last_update = _node_last_update(project_id, node.title)
    title_row = ft.Row(
        [
            build_editable_label(
                node.title,
                _rename_title,
                size=20,
                weight=ft.FontWeight.W_700,
                color=THEME["text"],
                placeholder="节点标题",
                on_refresh=_refresh,
            ),
            ft.Container(expand=True),
            ft.Text(f"负责人:{project.owner}", size=FONT_SMALL, color=THEME["text_sub"]),
            *(
                [
                    ft.Text(
                        f"最后更新:{last_update.isoformat()}",
                        size=FONT_SMALL,
                        color=THEME["text_faint"],
                    )
                ]
                if last_update is not None
                else []
            ),
        ],
        spacing=8,
    )

    main = ft.Column(
        [
            breadcrumb,
            ft.Container(height=6),
            title_row,
            ft.Container(height=12),
            card(note_editor),
            ft.Container(height=12),
            card(
                ft.Column(
                    [
                        ft.Text(
                            "相关资源",
                            size=FONT_TITLE,
                            weight=ft.FontWeight.W_600,
                            color=THEME["text"],
                        ),
                        ft.Text(
                            "资源卡片可直接编辑;添加后可再补链接",
                            size=FONT_SMALL,
                            color=THEME["text_faint"],
                        ),
                        ft.Container(height=6),
                        *(resource_cards or [
                            ft.Text("暂无资源", size=FONT_SMALL, color=THEME["text_faint"])
                        ]),
                        build_add_row(
                            "资源名称,回车添加",
                            lambda name: service.add_resource(
                                project_id, node.node_id, name
                            ),
                            label="添加资源",
                            on_refresh=_refresh,
                        ),
                    ],
                    spacing=8,
                )
            ),
            ft.Container(height=12),
            card(
                ft.Column(
                    [
                        ft.Text("关系", size=FONT_TITLE, weight=ft.FontWeight.W_600, color=THEME["text"]),
                        ft.Container(height=6),
                        *[
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.SOUTH_EAST, size=12, color=THEME["text_faint"]),
                                    ft.Text(rel, size=FONT_SMALL, color=THEME["text_sub"]),
                                ],
                                spacing=6,
                            )
                            for rel in relations
                        ],
                    ],
                    spacing=4,
                )
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        expand=True,
    )

    return ft.Row(
        [
            ft.Container(
                width=230,
                padding=ft.Padding(left=14, top=16, right=8, bottom=16),
                content=secondary_nav,
            ),
            ft.VerticalDivider(color=THEME["border"], width=1),
            ft.Container(
                expand=True,
                padding=ft.Padding(left=20, top=18, right=20, bottom=18),
                content=main,
            ),
        ],
        spacing=0,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
