"""Public runtime contracts shared by the UI and runtime implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Protocol

if TYPE_CHECKING:
    from workbench.domain.models import Proposal

QUEUED = "queued"
RUNNING = "running"
USING_TOOL = "using_tool"
COMPLETED = "completed"
FAILED = "failed"  # 真实 runtime 的显式失败;绝不伪装 completed

RUN_STATES = (QUEUED, RUNNING, USING_TOOL, COMPLETED, FAILED)


@dataclass(frozen=True)
class RunRequest:
    """One runtime invocation, e.g. a project review."""

    kind: str
    project_id: str


@dataclass(frozen=True)
class RunEvent:
    """A single streamed event of one runtime run.

    Only the final ``completed`` event may carry the resulting Proposal;
    no event ever writes to the workspace itself.
    """

    seq: int
    state: str
    tool: str | None = None
    message: str | None = None
    proposal: "Proposal | None" = None


class RuntimeGateway(Protocol):
    """The only surface the UI is allowed to consume a runtime through."""

    def events(self, request: RunRequest) -> Iterator[RunEvent]: ...
