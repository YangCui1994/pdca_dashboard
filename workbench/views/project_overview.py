"""项目页 = master-detail(D 试用反馈定稿形态)。

左 1/4:全部项目的紧凑卡纵向列表(名称+元信息+停滞红标),
点击选中高亮,详情区原地切换;右 3/4:大详情区 = 可编辑元信息
(目标/阶段/焦点/里程碑/负责人)+ 大纲 + 行动列表(状态色块点按
循环直改,真实停滞天数)+ 14 天活动。自由画布不进正式版。

「今日任务」勾选接 service(修复回弹);行动状态直改等价于接受
一条 action.status 提案(计数为实质更新)。
"""

from __future__ import annotations

from datetime import date

import flet as ft

from workbench.components import (
    FONT_SMALL,
    FONT_TITLE,
    STATUS_COLORS,
    STATUS_LABELS,
    STATUS_SOFT,
    THEME,
    badge,
    card,
)
from workbench.components.editable import build_editable_label
from workbench.components.heatmap import build_heatmap
from workbench.components.project_outline import build_project_outline
from workbench.domain.models import (
    COMPLETED,
    IN_PROGRESS,
    PENDING,
    STALLED_THRESHOLD_DAYS,
    WAITING,
)
from workbench.services.workspace_service import WorkspaceService

_STATUS_TAG = {
    IN_PROGRESS: ("进行中", THEME["green"], THEME["green_soft"]),
    PENDING: ("待办", THEME["text_sub"], THEME["dot_empty"]),
    WAITING: ("等待", THEME["orange"], THEME["orange_soft"]),
}


def _safe_update(control) -> None:
    try:
        control.update()
    except Exception:
        pass


def build_project_overview(
    service: WorkspaceService,
    project_id: str,
    on_open_node,
    on_open_artifact=None,
    on_refresh=None,
    on_back=None,
) -> ft.Control:
    today = date.today()
    state = {"selected": project_id}
    master_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    detail_box = ft.Container(expand=3)  # 左1/4 master(下面 expand=1) + 右3/4 详情

    def _refresh():
        if on_refresh is not None:
            on_refresh()

    # --- master:项目紧凑卡列表 ----------------------------------------------

    def _stalled_of(pid: str):
        return service.stalled_actions(project_id=pid, today=today)

    def _master_card(project, selected: bool) -> ft.Control:
        stalled = _stalled_of(project.project_id)
        meta_bits = [project.phase]
        if project.current_focus:
            meta_bits.append(project.current_focus)
        items = [
            ft.Row(
                [
                    ft.Text(
                        project.name,
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=THEME["purple_deep"] if selected else THEME["text"],
                        expand=True,
                        max_lines=1,
                    ),
                ],
                spacing=6,
            ),
            ft.Text(
                " · ".join(meta_bits),
                size=11,
                color=THEME["text_sub"],
                max_lines=1,
            ),
        ]
        if stalled:
            worst = max(
                (today - a.last_meaningful_update_at).days for a in stalled
            )
            items.append(
                ft.Row(
                    [
                        ft.Container(
                            width=6, height=6, bgcolor=THEME["stall"], border_radius=99
                        ),
                        ft.Text(
                            f"{len(stalled)} 项停滞 · 最长 {worst} 天",
                            size=11,
                            color=THEME["stall"],
                        ),
                    ],
                    spacing=4,
                )
            )
        return ft.Container(
            content=ft.Column(items, spacing=3),
            bgcolor=THEME["purple_soft"] if selected else THEME["card"],
            border=ft.Border.all(1, THEME["border"]),
            border_radius=10,
            padding=ft.Padding(left=10, top=8, right=10, bottom=8),
            on_click=None if selected else _select(project.project_id),
            ink=not selected,
            tooltip=project.name,
        )

    def _render_master():
        projects = service.projects()
        master_col.controls = [
            ft.Text(
                f"全部项目 · {len(projects)}",
                size=FONT_SMALL,
                color=THEME["text_faint"],
            ),
            *[
                _master_card(p, p.project_id == state["selected"])
                for p in projects
            ],
        ]

    def _select(pid: str):
        def handler(_e=None):
            if service.project(pid) is None:
                return
            state["selected"] = pid
            _render_master()
            _render_detail()
            _safe_update(master_col)
            _safe_update(detail_box)

        return handler

    # --- detail:大详情区 ------------------------------------------------------

    def _status_block(pid: str, action):
        """状态色块:点按循环切换(直改,等价接受 status 提案)。"""

        order = WorkspaceService.ACTION_STATUSES
        label = STATUS_LABELS.get(action.status, action.status)

        def cycle(_e=None):
            nxt = order[(order.index(action.status) + 1) % len(order)]
            if service.set_action_status(pid, action.action_id, nxt):
                _render_detail()
                _safe_update(detail_box)
                _render_master()
                _safe_update(master_col)

        return ft.Container(
            content=badge(
                label,
                STATUS_COLORS.get(action.status, THEME["text_sub"]),
                STATUS_SOFT.get(action.status, THEME["dot_empty"]),
            ),
            on_click=cycle,
            ink=True,
            tooltip="点按切换状态",
        )

    def _detail_view(project) -> ft.Control:
        pid = project.project_id
        stalled = _stalled_of(pid)
        counts = service.heatmap_counts(project_id=pid)

        def _set(field):
            return lambda value: service.set_project_field(pid, field, value)

        def _rename(action_id):
            return lambda value: service.rename_action(pid, action_id, value)

        header = ft.Row(
            [
                *(
                    [
                        ft.TextButton(
                            "‹ 全部项目",
                            style=ft.ButtonStyle(
                                color=THEME["text_sub"],
                                padding=ft.Padding(left=0, top=2, right=4, bottom=2),
                            ),
                            on_click=lambda _e: on_back(),
                        )
                    ]
                    if on_back is not None
                    else []
                ),
                ft.Icon(ft.Icons.FOLDER_OPEN, size=20, color=THEME["purple"]),
                build_editable_label(
                    project.name,
                    _set("name"),
                    size=20,
                    weight=ft.FontWeight.W_700,
                    color=THEME["text"],
                    placeholder="项目名",
                    on_refresh=_refresh,
                ),
                ft.Container(expand=True),
                *(
                    [
                        ft.TextButton(
                            "项目流图",
                            icon=ft.Icons.OPEN_IN_NEW,
                            style=ft.ButtonStyle(color=THEME["purple_deep"]),
                            tooltip="在浏览器打开自包含流程图(project-flow.html)",
                            on_click=lambda _e: on_open_artifact(),
                        )
                    ]
                    if on_open_artifact is not None
                    else []
                ),
            ],
            spacing=6,
        )

        def _meta_cell(label, value, on_commit=None):
            body = (
                build_editable_label(
                    value, on_commit, size=13, weight=ft.FontWeight.W_500,
                    on_refresh=_refresh,
                )
                if on_commit is not None
                else ft.Text(value, size=13, color=THEME["text"], weight=ft.FontWeight.W_500)
            )
            return ft.Column(
                [ft.Text(label, size=FONT_SMALL, color=THEME["text_faint"]), body],
                spacing=3,
            )

        meta = card(
            ft.Row(
                [
                    _meta_cell("项目目标", project.goal, _set("goal")),
                    ft.VerticalDivider(color=THEME["border"], width=1),
                    _meta_cell("当前阶段", project.phase, _set("phase")),
                    ft.VerticalDivider(color=THEME["border"], width=1),
                    _meta_cell("当前焦点", project.current_focus, _set("current_focus")),
                    ft.VerticalDivider(color=THEME["border"], width=1),
                    _meta_cell("下一个里程碑", project.next_milestone, _set("next_milestone")),
                    # 负责人只留姓名圆框(2026-09-16 用户决定);全名放 tooltip。
                    ft.CircleAvatar(
                        content=ft.Text(project.owner[0] if project.owner else "?", size=11),
                        bgcolor=THEME["purple_soft"],
                        color=THEME["purple_deep"],
                        radius=15,
                        tooltip=f"负责人:{project.owner}" if project.owner else "负责人未设置",
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            ),
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
        )

        warn_nodes = {"node-next"} if stalled else set()
        outline_card = card(
            ft.Column(
                [
                    ft.Text(
                        "选择节点查看详情",
                        size=FONT_TITLE,
                        weight=ft.FontWeight.W_600,
                        color=THEME["text"],
                    ),
                    ft.Container(height=10),
                    build_project_outline(
                        project, on_open_node=on_open_node, warn_node_ids=warn_nodes
                    ),
                ],
                spacing=0,
            )
        )

        open_items = [
            ft.Row(
                [
                    _status_block(pid, action),
                    build_editable_label(
                        action.title,
                        _rename(action.action_id),
                        size=FONT_SMALL,
                        on_refresh=_refresh,
                    ),
                    *(
                        [
                            badge(
                                f"{(today - action.last_meaningful_update_at).days} 天未更新",
                                THEME["stall"],
                                THEME["stall_soft"],
                            )
                        ]
                        if (
                            action.status == IN_PROGRESS
                            and (today - action.last_meaningful_update_at).days
                            >= STALLED_THRESHOLD_DAYS
                        )
                        else []
                    ),
                ],
                spacing=8,
            )
            for action in project.actions
            if action.status in (IN_PROGRESS, PENDING, WAITING)
        ]

        today_tasks = [action for action in project.actions if action.status != WAITING]
        done_count = sum(1 for a in today_tasks if a.status == COMPLETED)

        def _toggle_task(action):
            def handler(e):
                target = COMPLETED if e.control.value else PENDING
                if service.set_action_status(pid, action.action_id, target):
                    _render_detail()
                    _safe_update(detail_box)

            return handler

        task_rows = [
            ft.Checkbox(
                label=action.title,
                value=action.status == COMPLETED,
                active_color=THEME["green"],
                label_style=ft.TextStyle(size=FONT_SMALL, color=THEME["text"]),
                on_change=_toggle_task(action),
            )
            for action in today_tasks
        ]

        stalled_rows = [
            ft.Row(
                [
                    ft.Text(
                        f"{action.title}",
                        size=FONT_SMALL,
                        color=THEME["text"],
                        expand=True,
                    ),
                    badge(
                        f"{(today - action.last_meaningful_update_at).days} 天未更新",
                        THEME["stall"],
                        THEME["stall_soft"],
                    ),
                ],
                spacing=6,
            )
            for action in stalled
        ]

        cards_column = ft.Column(
            [
                card(
                    ft.Column(
                        [
                            ft.Text(
                                "当前需要关注",
                                size=FONT_TITLE,
                                weight=ft.FontWeight.W_600,
                                color=THEME["text"],
                            ),
                            ft.Container(height=6),
                            ft.Text(
                                "色块点按循环切换状态",
                                size=11,
                                color=THEME["text_faint"],
                            ),
                            *(open_items or [
                                ft.Text(
                                    "没有进行中的行动",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                )
                            ]),
                        ],
                        spacing=4,
                    )
                ),
                card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "今日任务",
                                        size=FONT_TITLE,
                                        weight=ft.FontWeight.W_600,
                                        color=THEME["text"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Text(
                                        f"{done_count}/{len(today_tasks)}",
                                        size=FONT_SMALL,
                                        color=THEME["text_sub"],
                                    ),
                                ]
                            ),
                            ft.Container(height=4),
                            *(task_rows or [
                                ft.Text(
                                    "暂无任务",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                )
                            ]),
                        ],
                        spacing=0,
                    )
                ),
                card(
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
                                        THEME["stall"],
                                        THEME["stall_soft"],
                                    ),
                                ]
                            ),
                            ft.Container(height=4),
                            *(stalled_rows or [
                                ft.Text(
                                    f"无超过 {STALLED_THRESHOLD_DAYS} 天未更新的进行中行动",
                                    size=FONT_SMALL,
                                    color=THEME["text_faint"],
                                )
                            ]),
                        ],
                        spacing=4,
                    )
                ),
                card(
                    ft.Column(
                        [
                            ft.Text(
                                "14 天活动",
                                size=FONT_TITLE,
                                weight=ft.FontWeight.W_600,
                                color=THEME["text"],
                            ),
                            ft.Container(height=8),
                            build_heatmap(counts, today=today, days=14, compact=True),
                        ],
                        spacing=0,
                    )
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        return ft.Column(
            [
                header,
                meta,
                ft.Row(
                    [
                        ft.Container(content=outline_card, expand=5),
                        ft.Container(width=12),
                        ft.Container(content=cards_column, expand=4),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            # 详情区整体可滚(2026-09-16):矮窗口(如 720 高)下节点树/
            # 关注卡此前被硬裁且无法滚动,演示库 7 节点只露出 2 个。
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _render_detail():
        project = service.project(state["selected"])
        detail_box.content = (
            _detail_view(project)
            if project is not None
            else ft.Text("项目不存在", color=THEME["text_sub"])
        )

    _render_master()
    _render_detail()

    return ft.Container(
        expand=True,
        padding=ft.Padding(left=22, top=18, right=22, bottom=18),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=master_col,
                            expand=1,
                        ),
                        ft.Container(width=12),
                        detail_box,
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )
