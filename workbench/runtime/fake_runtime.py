"""In-memory fake runtime streaming deterministic events; no IO, no waiting."""

from __future__ import annotations

from itertools import count

from workbench.domain.models import Proposal, ProposedChange
from workbench.runtime.contracts import (
    COMPLETED,
    QUEUED,
    RUNNING,
    USING_TOOL,
    RunEvent,
    RunRequest,
)

_REVIEW_TOOLS = (
    "scan_project_outline",
    "read_recent_activity",
    "check_stalled_actions",
    "list_open_decisions",
    "collect_resources",
    "summarize_progress",
    "verify_milestones",
    "draft_proposal",
)

_ROUNDS = 13  # 8 tools x 13 rounds = 104 using_tool events


def _review_tool_stream():
    for round_no in range(1, _ROUNDS + 1):
        for tool in _REVIEW_TOOLS:
            yield f"{tool}[round {round_no}]"


class FakeRuntime:
    """Deterministic stand-in for a real AI runtime.

    Streams enough ordered ``using_tool`` events to exercise streaming UI,
    without sleeping or touching files or network.
    """

    def events(self, request: RunRequest):
        seq = count(start=1)
        yield RunEvent(seq=next(seq), state=QUEUED, message=f"queued {request.kind}")
        yield RunEvent(seq=next(seq), state=RUNNING, message="run started")
        for tool in _review_tool_stream():
            yield RunEvent(seq=next(seq), state=USING_TOOL, tool=tool)
        yield RunEvent(
            seq=next(seq),
            state=COMPLETED,
            message="run completed",
            proposal=_review_proposal(request),
        )


def _review_proposal(request: RunRequest) -> Proposal:
    """A demo proposal; the only way a run can affect formal state."""

    return Proposal(
        proposal_id=f"prop-{request.kind}-{request.project_id}",
        request_kind=request.kind,
        project_id=request.project_id,
        summary="建议恢复一项等待中的行动,并补充一条关键判断记录。",
        changes=(
            ProposedChange(
                field="action.status",
                target_id=f"{request.project_id}:act-003",
                current_value="waiting",
                new_value="in_progress",
            ),
        ),
        facts=(
            "act-003「等待复核反馈」处于 waiting 已超过 14 天。",
            "项目当前焦点是清理重复条目。",
        ),
        inferences=(
            "复核反馈大概率已经到位,恢复进行中比继续等待更合理。",
        ),
        external_knowledge=(
            "同类知识库整理经验:等待项每周复核一次可减少长期停滞。",
        ),
    )
