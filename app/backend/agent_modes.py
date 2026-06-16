from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


AgentExecutionMode = Literal["single", "round-table", "approval-chain"]

AGENT_EXECUTION_MODES = {"single", "round-table", "approval-chain"}


@dataclass(frozen=True)
class AgentRole:
    name: str
    responsibility: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Agent role name is required")
        if not self.responsibility.strip():
            raise ValueError("Agent role responsibility is required")


@dataclass(frozen=True)
class AgentExecutionPlan:
    mode: AgentExecutionMode
    prompt: str
    roles: list[AgentRole] = field(default_factory=list)
    approval_steps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in AGENT_EXECUTION_MODES:
            raise ValueError(f"Unsupported agent execution mode: {self.mode}")
        if not self.prompt.strip():
            raise ValueError("Agent execution prompt is required")
        if self.mode == "single" and len(self.roles) != 1:
            raise ValueError("Single agent mode requires exactly one role")
        if self.mode == "round-table" and len(self.roles) < 2:
            raise ValueError("Round table mode requires at least two roles")
        if self.mode == "approval-chain" and not self.approval_steps:
            raise ValueError("Approval chain mode requires at least one approval step")


def create_single_agent_plan(action: str, prompt: str) -> AgentExecutionPlan:
    return AgentExecutionPlan(
        mode="single",
        prompt=prompt,
        roles=[AgentRole(name="executor", responsibility=f"Complete AI action: {action}")],
    )


def create_round_table_plan(prompt: str, roles: list[AgentRole]) -> AgentExecutionPlan:
    return AgentExecutionPlan(mode="round-table", prompt=prompt, roles=roles)


def create_approval_chain_plan(prompt: str, reviewers: list[str]) -> AgentExecutionPlan:
    clean_reviewers = [reviewer.strip() for reviewer in reviewers if reviewer.strip()]
    return AgentExecutionPlan(
        mode="approval-chain",
        prompt=prompt,
        roles=[AgentRole(name="executor", responsibility="Create the first draft")],
        approval_steps=clean_reviewers,
    )
