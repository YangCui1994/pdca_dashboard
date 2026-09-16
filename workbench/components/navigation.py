"""Left main navigation shared by every page."""

from __future__ import annotations

import flet as ft

from workbench.components import FONT_SMALL, THEME

ROUTE_TODAY = "/today"
ROUTE_IDEAS = "/ideas"
ROUTE_PROJECTS = "/projects"
ROUTE_ACTIVITY = "/activity"
ROUTE_ARCHIVE = "/archive"

# (label, route, material icon) — order matches the approved reference.
MAIN_NAV_ITEMS = (
    ("今天", ROUTE_TODAY, ft.Icons.TODAY),
    ("想法", ROUTE_IDEAS, ft.Icons.LIGHTBULB_OUTLINE),
    ("项目", ROUTE_PROJECTS, ft.Icons.FOLDER_OPEN),
    ("活动", ROUTE_ACTIVITY, ft.Icons.TIMELINE),
    ("归档", ROUTE_ARCHIVE, ft.Icons.ARCHIVE_OUTLINED),
)


def _nav_item(label, route, icon, active, on_route):
    is_active = route == active
    row = ft.Row(
        [
            ft.Icon(icon, size=18, color=THEME["purple"] if is_active else THEME["text_sub"]),
            ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                color=THEME["purple_deep"] if is_active else THEME["text_sub"],
            ),
        ],
        spacing=10,
    )
    return ft.Container(
        content=row,
        bgcolor=THEME["purple_soft"] if is_active else None,
        border_radius=8,
        padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        on_click=lambda _e, r=route: on_route(r),
        ink=True,
    )


def build_main_nav(
    active_route: str,
    on_route,
    ai_open: bool = False,
    on_toggle_ai=None,
    ai_attention: bool = False,
) -> ft.Control:
    """Fixed-width left nav; on_route(route) is invoked on item click.

    AI 助手是独立开关项(2026-09-16 用户定:面板默认收起,点开才出现),
    不进 MAIN_NAV_ITEMS(导航五项契约保持);ai_attention=有待确认 Proposal
    且面板收起时亮小圆点。
    """

    items = [
        _nav_item(label, route, icon, active_route, on_route)
        for label, route, icon in MAIN_NAV_ITEMS
    ]

    ai_toggle = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.AUTO_AWESOME,
                    size=18,
                    color=THEME["purple"] if ai_open else THEME["text_sub"],
                ),
                ft.Text(
                    "AI 助手",
                    size=13,
                    weight=ft.FontWeight.W_600 if ai_open else ft.FontWeight.W_400,
                    color=THEME["purple_deep"] if ai_open else THEME["text_sub"],
                ),
                ft.Container(expand=True),
                *(
                    [
                        ft.Container(
                            width=7,
                            height=7,
                            border_radius=99,
                            bgcolor=THEME["stall"],
                        )
                    ]
                    if ai_attention
                    else []
                ),
            ],
            spacing=10,
        ),
        bgcolor=THEME["purple_soft"] if ai_open else None,
        border_radius=8,
        padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        on_click=lambda _e: on_toggle_ai() if on_toggle_ai is not None else None,
        ink=True,
    )

    return ft.Container(
        width=190,
        bgcolor=THEME["card"],
        border=ft.Border(
            top=ft.BorderSide(0, THEME["border"]),
            right=ft.BorderSide(1, THEME["border"]),
            bottom=ft.BorderSide(0, THEME["border"]),
            left=ft.BorderSide(0, THEME["border"]),
        ),
        padding=ft.Padding(left=12, top=18, right=12, bottom=14),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=26,
                            height=26,
                            bgcolor=THEME["purple"],
                            border_radius=7,
                            content=ft.Icon(
                                ft.Icons.WORKSPACES_OUTLINED,
                                size=15,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "个人工作台",
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=THEME["text"],
                                ),
                                ft.Text("v2 样片", size=FONT_SMALL, color=THEME["text_faint"]),
                            ],
                            spacing=1,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=18),
                *items,
                ft.Container(expand=True),
                ai_toggle,
                ft.Container(height=6),
                ft.Text("本地运行 · 无外部服务", size=FONT_SMALL, color=THEME["text_faint"]),
            ],
            spacing=4,
        ),
    )


def _capture_bar(on_capture) -> ft.Control:
    """全局底部快速记录条:回车与按钮走同一回调,回调内零领域规则。

    提交后由组合层决定是否重渲染(整页重建即自然清空输入框)。
    """

    def _submit(_e=None):
        text = (field.value or "").strip()
        if not text:
            return
        on_capture(text)

    field = ft.TextField(
        hint_text="快速记录:想法、笔记、待办…(回车提交)",
        expand=True,
        border_color=THEME["border"],
        border_radius=10,
        content_padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        text_size=13,
        on_submit=_submit,
    )
    return ft.Container(
        bgcolor=THEME["card"],
        border=ft.Border(
            top=ft.BorderSide(1, THEME["border"]),
            right=ft.BorderSide(0, THEME["border"]),
            bottom=ft.BorderSide(0, THEME["border"]),
            left=ft.BorderSide(0, THEME["border"]),
        ),
        padding=ft.Padding(left=16, top=10, right=16, bottom=10),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.EDIT_NOTE, size=20, color=THEME["purple"]),
                field,
                ft.FilledButton(
                    "记录",
                    bgcolor=THEME["purple"],
                    color=ft.Colors.WHITE,
                    on_click=_submit,
                ),
            ],
            spacing=10,
        ),
    )


def build_page(
    active_route: str,
    on_route,
    content,
    ai_panel=None,
    on_capture=None,
    ai_open: bool = False,
    on_toggle_ai=None,
    ai_attention: bool = False,
) -> ft.Control:
    """Compose one full page: nav | content (| AI drawer), plus capture bar.

    on_capture(text) 存在时,每个页面底部都有全局快速记录条。
    ai_panel=None 时右侧 AI 面板收起(侧栏开关项仍可见)。
    """

    row = [
        build_main_nav(
            active_route,
            on_route,
            ai_open=ai_open,
            on_toggle_ai=on_toggle_ai,
            ai_attention=ai_attention,
        ),
        content,
    ]
    if ai_panel is not None:
        row.append(ai_panel)
    children = [ft.Row(row, spacing=0, expand=True)]
    if on_capture is not None:
        children.append(_capture_bar(on_capture))
    return ft.Container(
        bgcolor=THEME["canvas"],
        expand=True,
        content=ft.Column(children, spacing=0),
    )
