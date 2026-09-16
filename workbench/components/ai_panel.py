"""Right AI drawer: run review, stream events, confirm or reject proposals.

Pure builder — no streaming logic here. The page controller owns run_task
and rebuilds the panel from :class:`AIPanelState`. Domain rules (proposal
permissions) stay in WorkspaceService; this panel only renders and forwards
explicit user decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import flet as ft

from workbench.components import FONT_SMALL, THEME, badge, card
from workbench.domain.models import Proposal

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_AWAITING = "awaiting"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_FAILED = "failed"

_STATUS_LABEL = {
    STATUS_IDLE: "空闲 · 未运行",
    STATUS_RUNNING: "运行中…",
    STATUS_AWAITING: "待确认 Proposal",
    STATUS_ACCEPTED: "已接受 · 正式状态已更新",
    STATUS_REJECTED: "已拒绝 · 正式状态未变",
    STATUS_FAILED: "运行失败 · 可重试",
}


@dataclass
class AIPanelState:
    """Everything the panel renders; owned by the page controller."""

    status: str = STATUS_IDLE
    current_tool: str = ""
    recent_events: tuple[str, ...] = field(default_factory=tuple)
    event_count: int = 0
    proposal: Proposal | None = None
    note: str = ""


def _legend_row():
    def dot(color):
        return ft.Container(width=8, height=8, border_radius=99, bgcolor=color)

    return ft.Row(
        [
            dot(THEME["green"]),
            ft.Text("已确认", size=FONT_SMALL, color=THEME["text_sub"]),
            dot(THEME["purple"]),
            ft.Text("AI 推荐", size=FONT_SMALL, color=THEME["text_sub"]),
            dot(THEME["blue"]),
            ft.Text("外部知识", size=FONT_SMALL, color=THEME["text_sub"]),
        ],
        spacing=5,
    )


def _bullet(text, color):
    return ft.Row(
        [
            ft.Container(width=6, height=6, border_radius=99, bgcolor=color),
            ft.Text(text, size=FONT_SMALL, color=THEME["text"], expand=True),
        ],
        spacing=8,
    )


def _proposal_block(proposal: Proposal, on_accept, on_reject):
    changes = [
        ft.Row(
            [
                ft.Icon(ft.Icons.ARROW_FORWARD, size=12, color=THEME["purple"]),
                ft.Text(
                    f"{change.field} · {change.target_id}: {change.current_value} → {change.new_value}",
                    size=FONT_SMALL,
                    color=THEME["text"],
                ),
            ],
            spacing=6,
        )
        for change in proposal.changes
    ]
    sections = []
    if proposal.facts:
        sections.append(
            ft.Column(
                [_bullet(fact, THEME["green"]) for fact in proposal.facts],
                spacing=4,
            )
        )
    if proposal.inferences:
        sections.append(
            ft.Column(
                [_bullet(text, THEME["purple"]) for text in proposal.inferences],
                spacing=4,
            )
        )
    if proposal.external_knowledge:
        sections.append(
            ft.Column(
                [
                    _bullet(text, THEME["blue"])
                    for text in proposal.external_knowledge
                ],
                spacing=4,
            )
        )
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "待确认 Proposal",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=THEME["text"],
                    ),
                ]
            ),
            ft.Text(proposal.summary, size=FONT_SMALL, color=THEME["text_sub"]),
            ft.Container(height=6),
            *sections,
            ft.Container(height=8),
            ft.Text("更新范围", size=FONT_SMALL, color=THEME["text_sub"]),
            *changes,
            ft.Container(height=10),
            ft.Row(
                [
                    ft.FilledButton(
                        "确认更新",
                        icon=ft.Icons.CHECK,
                        bgcolor=THEME["purple"],
                        color=ft.Colors.WHITE,
                        on_click=lambda _e: on_accept(proposal),
                    ),
                    ft.OutlinedButton(
                        "暂不更新",
                        on_click=lambda _e: on_reject(proposal),
                    ),
                ],
                spacing=8,
            ),
        ],
        spacing=5,
    )


def build_ai_panel(
    state: AIPanelState,
    on_run_review,
    on_accept,
    on_reject,
    concierge=None,
) -> ft.Control:
    """Right drawer ~280px wide. All buttons forward explicit user actions.

    concierge: ConciergeController(2026-09-16 合并) — 提供阶段动作/
    思考方式点名/草稿卡队列;None 时面板只保留项目审查流。
    """

    header = ft.Row(
        [
            ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color=THEME["purple"]),
            ft.Text("AI 助手", size=14, weight=ft.FontWeight.W_700, color=THEME["text"]),
            ft.Container(expand=True),
            ft.Icon(ft.Icons.CLOSE, size=14, color=THEME["text_faint"]),
        ],
        spacing=6,
    )

    run_button = ft.Row(
        [
            ft.FilledButton(
                "运行项目审查",
                icon=ft.Icons.PLAY_ARROW,
                bgcolor=THEME["purple"],
                color=ft.Colors.WHITE,
                on_click=lambda _e: on_run_review(),
            ),
        ]
    )

    status_color = {
        STATUS_RUNNING: THEME["purple"],
        STATUS_AWAITING: THEME["orange"],
        STATUS_ACCEPTED: THEME["green"],
        STATUS_REJECTED: THEME["text_sub"],
        STATUS_IDLE: THEME["text_faint"],
        STATUS_FAILED: THEME["orange"],
    }[state.status]
    status_line = ft.Row(
        [
            ft.Text("运行状态", size=FONT_SMALL, color=THEME["text_sub"]),
            ft.Container(width=6, height=6, border_radius=99, bgcolor=status_color),
            ft.Text(_STATUS_LABEL[state.status], size=FONT_SMALL, color=THEME["text"]),
            ft.Container(expand=True),
            ft.Text(
                f"{state.event_count} 事件" if state.event_count else "",
                size=FONT_SMALL,
                color=THEME["text_faint"],
            ),
        ],
        spacing=6,
    )

    stream_lines = [
        ft.Text(line, size=FONT_SMALL, color=THEME["text_faint"], selectable=True)
        for line in list(state.recent_events)[-6:]
    ]
    failure_note = (
        ft.Container(
            content=ft.Text(state.note, size=FONT_SMALL, color=THEME["orange"]),
            bgcolor=THEME["orange_soft"],
            padding=ft.Padding(left=8, top=5, right=8, bottom=5),
            border_radius=8,
        )
        if state.note
        else ft.Container()
    )

    stream_block = (
        card(
            ft.Column(
                [
                    ft.Text(
                        f"正在使用工具:{state.current_tool}",
                        size=FONT_SMALL,
                        color=THEME["purple_deep"],
                        weight=ft.FontWeight.W_500,
                    )
                ]
                + stream_lines,
                spacing=3,
            ),
            padding=10,
        )
        if state.status == STATUS_RUNNING or state.recent_events
        else ft.Container()
    )

    proposal_block = (
        card(_proposal_block(state.proposal, on_accept, on_reject))
        if state.status == STATUS_AWAITING and state.proposal is not None
        else ft.Container()
    )

    decision_note = (
        ft.Container(
            content=ft.Text(
                _STATUS_LABEL[state.status],
                size=FONT_SMALL,
                color=THEME["green"] if state.status == STATUS_ACCEPTED else THEME["text_sub"],
            ),
            bgcolor=THEME["green_soft"] if state.status == STATUS_ACCEPTED else THEME["canvas"],
            padding=ft.Padding(left=8, top=5, right=8, bottom=5),
            border_radius=8,
        )
        if state.status in (STATUS_ACCEPTED, STATUS_REJECTED)
        else ft.Container()
    )

    return ft.Container(
        width=280,
        bgcolor=THEME["card"],
        border=ft.Border(
            top=ft.BorderSide(0, THEME["border"]),
            right=ft.BorderSide(0, THEME["border"]),
            bottom=ft.BorderSide(0, THEME["border"]),
            left=ft.BorderSide(1, THEME["border"]),
        ),
        padding=ft.Padding(left=14, top=16, right=14, bottom=14),
        content=ft.Column(
            [
                header,
                ft.Container(height=10),
                _legend_row(),
                ft.Container(height=12),
                run_button,
                ft.Container(height=10),
                status_line,
                ft.Container(height=8),
                failure_note,
                stream_block,
                proposal_block,
                decision_note,
                *(
                    [concierge.sections()]
                    if concierge is not None
                    else []
                ),
                ft.Container(expand=True),
                ft.Text(
                    "输出仅为 Proposal,接受前不改正式状态",
                    size=FONT_SMALL,
                    color=THEME["text_faint"],
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
