"""确定性中文演示 vault:五个原型共用,与真实 data-issue-vault 完全隔离。

用法(python -m,从仓库根目录):
    python -m prototypes.uxbase.seed_demo            # 已存在则跳过
    python -m prototypes.uxbase.seed_demo --reseed   # 删掉重建
默认 vault 根:prototypes/ux-2026-09/demo_vault。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from workbench.domain.fixtures import load_demo_workspace
from workbench.domain.models import (
    CONTENT_UPDATED,
    DayRecord,
    IDEA_ARCHIVED,
    IDEA_KEPT,
    IDEA_PENDING,
    Idea,
    PlanItem,
    TASK_COMPLETED,
    ActivityEvent,
)
from workbench.services.workspace_service import WorkspaceService
from workbench.storage import WorkspaceStorage

DEFAULT_VAULT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "demo_vault"


def build_days(today: date | None = None) -> dict[date, DayRecord]:
    """三天带中文真实感的记录:昨天(有未完成,供向导/顺延用)、前天(完整 PDCA)。"""

    today = today or date.today()
    yesterday = today - timedelta(days=1)
    before = today - timedelta(days=2)
    return {
        yesterday: DayRecord(
            day=yesterday,
            plan=[
                PlanItem(item_id="plan-001", text="核对渠道日报异常波动", done=True, project_id="proj-atlas"),
                PlanItem(item_id="plan-002", text="整理平台故障复盘要点", done=True, project_id=""),
                PlanItem(item_id="plan-003", text="准备用户访谈提纲", done=False, project_id="proj-boreas"),
                PlanItem(item_id="plan-004", text="给运营拉一版周报数据", done=False, project_id=""),
            ],
            worklog=(
                "- 上午核对渠道日报,发现两个渠道的转化数据对不上,已记录。\n"
                "- 下午整理上周平台故障的复盘要点,还差结论部分。\n"
                "- 访谈提纲被临时会议打断,只写了个开头。"
            ),
            check_note="",
            act_note="",
        ),
        before: DayRecord(
            day=before,
            plan=[
                PlanItem(item_id="plan-001", text="修复报表时区偏移", done=True, project_id="proj-atlas"),
                PlanItem(item_id="plan-002", text="评审档案说明页初稿", done=True, project_id="proj-boreas"),
            ],
            worklog=(
                "- 报表时区偏移已修复并补了回归用例。\n"
                "- 档案说明页初稿评审通过,待补充术语表。"
            ),
            check_note="计划粒度合适,两件事都闭环了;评审比预期多花 40 分钟,下次预留缓冲。",
            act_note="术语表排到明天;把「评审预留缓冲」写进后续所有排期。",
        ),
    }


def build_ideas(today: date | None = None) -> list[Idea]:
    """8 条想法:4 待整理 / 2 保留 / 2 已归档,created_at 逐条错开。"""

    today = today or date.today()
    rows = [
        (IDEA_PENDING, "把渠道日报的异常波动自动标注出来,省得每天人眼扫"),
        (IDEA_PENDING, "访谈提纲里加一道竞品对比题"),
        (IDEA_PENDING, "做一个每周停滞项提醒的固定栏目"),
        (IDEA_PENDING, "报表导出加 CSV 格式,运营想自己拉数"),
        (IDEA_KEPT, "把星图的命名规范同步给新同事"),
        (IDEA_KEPT, "北风档案的封面图风格先保持现状"),
        (IDEA_ARCHIVED, "给报表页加个动画(做过一轮,价值不大)"),
        (IDEA_ARCHIVED, "换一个新笔记工具(现有流程已够用)"),
    ]
    return [
        Idea(
            idea_id=f"idea-{idx:03d}",
            text=text,
            status=status,
            created_at=today - timedelta(days=idx % 4),
        )
        for idx, (status, text) in enumerate(rows, start=1)
    ]


def build_recent_activity(today: date | None = None) -> list[ActivityEvent]:
    """近两周确定性的活动事件,让热力图有真实起伏。"""

    today = today or date.today()
    events: list[ActivityEvent] = []
    for offset in range(14, 0, -1):
        day = today - timedelta(days=offset)
        if offset % 3 == 0:
            continue  # 留出空白天,热力图更像真实节奏
        events.append(
            ActivityEvent(day, "proj-atlas", TASK_COMPLETED, f"完成一项计划(day-{offset})")
        )
        if offset % 2 == 0:
            events.append(
                ActivityEvent(day, "proj-boreas", CONTENT_UPDATED, f"推进档案说明页(day-{offset})")
            )
    return events


def seed(vault: Path | str = DEFAULT_VAULT, *, reseed: bool = False) -> WorkspaceService:
    vault = Path(vault)
    if vault.exists() and (vault / "workspace.json").exists() and not reseed:
        return WorkspaceService.open(WorkspaceStorage(vault))
    if vault.exists() and reseed:
        shutil.rmtree(vault)

    projects, activity = load_demo_workspace()
    days = build_days()
    ideas = build_ideas()
    extra_activity = build_recent_activity()

    storage = WorkspaceStorage(vault)
    for project in projects:
        storage.save_project(project)
        for node in project.outline:
            storage.save_node(project.project_id, node)
    for record in days.values():
        storage.save_day(record)
    storage.save_ideas(ideas, next_seq=len(ideas) + 1)
    for event in list(activity) + extra_activity:
        storage.append_activity(event)
    return WorkspaceService.open(storage)


def projects_summary(service: WorkspaceService) -> str:
    """渲染 {{project_brief}}:一行一个项目,含 id/名称/焦点/行动概览。"""

    lines = []
    for project in service.projects():
        open_actions = [
            a for a in project.actions if a.status in ("pending", "in_progress", "waiting")
        ]
        lines.append(
            f"{project.project_id} {project.name}|目标:{project.goal or '未填'}"
            f"|当前焦点:{project.current_focus or '未填'}|进行中行动:"
            + (";".join(a.title for a in open_actions) or "无")
        )
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成演示 vault(不触真实数据)")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT))
    parser.add_argument("--reseed", action="store_true", help="删除现有演示数据重建")
    args = parser.parse_args()
    service = seed(args.vault, reseed=args.reseed)
    print(
        f"vault={args.vault} projects={len(service.projects())} "
        f"ideas={len(service.ideas())} days={len(service.activity())} activity-events"
    )
    sys.exit(0)
