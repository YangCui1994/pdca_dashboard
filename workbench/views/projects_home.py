"""项目首页:全部项目卡片,点击进入单个项目总览。

多项目用「全部显示」而非下拉:项目互相可见、可对比状态,
后续新建项目也挂在同一层。
"""

from __future__ import annotations

from datetime import date, timedelta

import flet as ft

from workbench.components import FONT_SMALL, THEME, badge, card
from workbench.domain.models import IN_PROGRESS, PENDING, WAITING


def _project_card(project, service, on_open_project) -> ft.Control:
    open_count = sum(
        1 for a in project.actions if a.status in (IN_PROGRESS, PENDING, WAITING)
    )
    stalled_ids = {a.action_id for a in service.stalled_actions(project_id=project.project_id)}
    stalled_count = len(stalled_ids)
    since = date.today() - timedelta(days=14)
    active_days = sum(
        count
        for day, count in service.heatmap_counts(project_id=project.project_id).items()
        if day >= since
    )

    return ft.Container(
        width=360,
        height=170,  # 固定高度:目标/焦点截断,多卡片网格对齐
        on_click=lambda _e, pid=project.project_id: on_open_project(pid),
        ink=True,
        content=card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.FOLDER_OPEN, size=18, color=THEME["purple"]
                            ),
                            ft.Text(
                                project.name,
                                size=15,
                                weight=ft.FontWeight.W_700,
                                color=THEME["text"],
                                expand=True,
                            ),
                            badge(project.phase, THEME["purple_deep"], THEME["purple_soft"]),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        project.goal,
                        size=FONT_SMALL,
                        color=THEME["text_sub"],
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        f"当前焦点:{project.current_focus}",
                        size=FONT_SMALL,
                        color=THEME["text"],
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            ft.CircleAvatar(
                                content=ft.Text(project.owner[0], size=10),
                                bgcolor=THEME["purple_soft"],
                                color=THEME["purple_deep"],
                            ),
                            ft.Text(project.owner, size=FONT_SMALL, color=THEME["text_faint"]),
                            ft.Container(expand=True),
                            ft.Text(
                                f"进行中 {open_count}",
                                size=FONT_SMALL,
                                color=THEME["text_sub"],
                            ),
                            ft.Text(
                                f"· 14 天活跃 {active_days} 天",
                                size=FONT_SMALL,
                                color=THEME["text_sub"],
                            ),
                            *(
                                [ft.Text(
                                    f"· 停滞 {stalled_count}",
                                    size=FONT_SMALL,
                                    color=THEME["orange"],
                                )]
                                if stalled_count
                                else []
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
            )
        ),
    )


def _safe_update(control) -> None:
    try:
        control.update()
    except Exception:
        pass


def _new_project_card(on_create, on_done) -> ft.Control:
    """与项目卡同尺寸的「＋ 新建项目」卡,接在现有项目后面。

    点击后原位展开表单;创建成功/取消后回到虚线卡。
    """

    state = {"creating": False}
    box = ft.Container(width=360)  # 编辑态切换为两张卡宽(360*2+12)

    def idle() -> ft.Control:
        return ft.Container(
            width=360,
            height=170,  # 与项目卡同高
            border=ft.Border(
                top=ft.BorderSide(1, THEME["purple_faint"]),
                right=ft.BorderSide(1, THEME["purple_faint"]),
                bottom=ft.BorderSide(1, THEME["purple_faint"]),
                left=ft.BorderSide(1, THEME["purple_faint"]),
            ),
            border_radius=12,
            alignment=ft.Alignment(0, 0),  # 居中
            padding=ft.Padding(left=14, top=14, right=14, bottom=14),
            on_click=lambda _e: enter(),
            ink=True,
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ADD, size=26, color=THEME["purple"]),
                    ft.Text("新建项目", size=13, color=THEME["text_sub"]),
                    ft.Text(
                        "名称必填,其余可后补", size=FONT_SMALL, color=THEME["text_faint"]
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _field(hint: str, autofocus: bool = False) -> ft.TextField:
        return ft.TextField(
            hint_text=hint,
            autofocus=autofocus,
            text_size=13,
            border_color=THEME["border"],
            focused_border_color=THEME["purple"],
            content_padding=ft.Padding(left=10, top=6, right=10, bottom=6),
        )

    name = _field("项目名称(必填)", autofocus=True)
    goal = _field("目标(可选)")
    focus = _field("当前焦点(可选)")
    owner = _field("负责人(可选,默认「我」)")
    error = ft.Text("", size=FONT_SMALL, color=THEME["orange"])

    def submit(_e=None):
        if not name.value or not name.value.strip():
            error.value = "项目名称不能为空"
            _safe_update(error)
            return
        try:
            on_create(
                name=name.value,
                goal=goal.value or "",
                current_focus=focus.value or "",
                owner=owner.value or "",
            )
        except ValueError as exc:
            error.value = str(exc)
            _safe_update(error)
            return
        on_done()

    def restore():
        state["creating"] = False
        box.width = 360
        box.content = idle()
        _safe_update(box)

    def enter():
        if state["creating"]:
            return
        state["creating"] = True
        box.width = 732  # 两张卡宽度,字段分两栏
        box.content = card(
            ft.Column(
                [
                    ft.Text(
                        "新建项目",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=THEME["text"],
                    ),
                    ft.Row(
                        [
                            ft.Column([name, goal], spacing=8, expand=True),
                            ft.Column([focus, owner], spacing=8, expand=True),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    error,
                    ft.Row(
                        [
                            ft.FilledButton(
                                "创建",
                                icon=ft.Icons.CHECK,
                                bgcolor=THEME["purple"],
                                color=ft.Colors.WHITE,
                                on_click=submit,
                            ),
                            ft.OutlinedButton("取消", on_click=lambda _e: restore()),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            )
        )
        _safe_update(box)

    box.content = idle()
    return box


def build_projects_home(service, on_open_project, on_refresh=None, on_create=None) -> ft.Control:
    projects = service.projects()

    def _refresh():
        if on_refresh is not None:
            on_refresh()

    def _default_create(**_fields):
        return None  # 组合层未接线时不提供创建入口

    return ft.Container(
        expand=True,
        padding=ft.Padding(left=22, top=18, right=22, bottom=18),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FOLDER_OPEN, size=20, color=THEME["purple"]),
                        ft.Text(
                            "项目",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=THEME["text"],
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"共 {len(projects)} 个",
                            size=FONT_SMALL,
                            color=THEME["text_faint"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        *[
                            _project_card(project, service, on_open_project)
                            for project in projects
                        ],
                        _new_project_card(on_create or _default_create, _refresh),
                    ],
                    spacing=12,
                    run_spacing=12,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
