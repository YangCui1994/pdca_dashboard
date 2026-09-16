"""Fully fictional demo workspace for the spike.

Every project, person, file path, and intranet link below is invented.
No real company data, real names, real paths, or credentials appear here.
Dates are computed relative to today so behavior tests stay deterministic.
"""

from __future__ import annotations

from datetime import date, timedelta

from workbench.domain.models import (
    CANCELLED,
    COMPLETED,
    CONTENT_UPDATED,
    DECISION_CONFIRMED,
    DEFERRED,
    IN_PROGRESS,
    PAGE_VIEWED,
    PENDING,
    PROPOSAL_ACCEPTED,
    RESOURCE_ADDED,
    TASK_COMPLETED,
    WAITING,
    Action,
    ActivityEvent,
    DayRecord,
    OutlineNode,
    PlanItem,
    Project,
    Resource,
)

_TODAY = date.today()


def _days_ago(days: int) -> date:
    return _TODAY - timedelta(days=days)


def _atlas_outline() -> tuple[OutlineNode, ...]:
    return (
        OutlineNode(
            node_id="node-goal",
            project_id="proj-atlas",
            title="目标与边界",
            kind="goal",
            note="整理星图演示库;不含真实客户数据。",
        ),
        OutlineNode(
            node_id="node-people",
            project_id="proj-atlas",
            title="参与者与职责",
            kind="people",
            note="林演示负责整理,陈示例负责复核。",
        ),
        OutlineNode(
            node_id="node-progress",
            project_id="proj-atlas",
            title="当前进展",
            kind="progress",
            note="已归档 120 条演示条目。",
        ),
        OutlineNode(
            node_id="node-decisions",
            project_id="proj-atlas",
            title="关键判断",
            kind="decision",
            note="演示条目一律使用虚构命名。",
        ),
        OutlineNode(
            node_id="node-tests",
            project_id="proj-atlas",
            title="测试资源",
            kind="test",
            note="样片自检清单见测试目录。",
            resources=_tests_resources(),
        ),
        OutlineNode(
            node_id="node-resources",
            project_id="proj-atlas",
            title="资料与链接",
            kind="resource",
            note="演示链接:https://wiki.internal.example.net/atlas(虚构)",
            resources=_links_resources(),
        ),
        OutlineNode(
            node_id="node-next",
            project_id="proj-atlas",
            title="待推进事项",
            kind="next",
            note="补充北风档案的交叉引用。",
        ),
    )


def _atlas_actions() -> tuple[Action, ...]:
    return (
        Action(
            action_id="act-001",
            project_id="proj-atlas",
            title="梳理星图目录结构",
            status=IN_PROGRESS,
            last_meaningful_update_at=_days_ago(3),
        ),
        Action(
            action_id="act-002",
            project_id="proj-atlas",
            title="清理重复演示条目",
            status=IN_PROGRESS,
            last_meaningful_update_at=_days_ago(20),
        ),
        Action(
            action_id="act-003",
            project_id="proj-atlas",
            title="等待复核反馈",
            status=WAITING,
            last_meaningful_update_at=_days_ago(20),
        ),
        Action(
            action_id="act-004",
            project_id="proj-atlas",
            title="建立演示命名规范",
            status=COMPLETED,
            last_meaningful_update_at=_days_ago(10),
        ),
        Action(
            action_id="act-005",
            project_id="proj-atlas",
            title="延后:批量导入工具选型",
            status=DEFERRED,
            last_meaningful_update_at=_days_ago(20),
        ),
        Action(
            action_id="act-006",
            project_id="proj-atlas",
            title="取消:旧索引迁移",
            status=CANCELLED,
            last_meaningful_update_at=_days_ago(30),
        ),
    )


def _boreas_actions() -> tuple[Action, ...]:
    return (
        Action(
            action_id="act-101",
            project_id="proj-boreas",
            title="盘点北风档案清单",
            status=IN_PROGRESS,
            last_meaningful_update_at=_days_ago(17),
        ),
        Action(
            action_id="act-102",
            project_id="proj-boreas",
            title="编写档案说明页",
            status=PENDING,
            last_meaningful_update_at=_days_ago(2),
        ),
    )


def _activity() -> tuple[ActivityEvent, ...]:
    return (
        ActivityEvent(_days_ago(0), "proj-atlas", CONTENT_UPDATED, "更新当前进展节点"),
        ActivityEvent(_days_ago(0), "proj-atlas", PAGE_VIEWED, "查看项目总览"),
        ActivityEvent(_days_ago(1), "proj-atlas", TASK_COMPLETED, "完成演示命名规范"),
        ActivityEvent(_days_ago(1), "proj-boreas", RESOURCE_ADDED, "加入档案清单文件"),
        ActivityEvent(_days_ago(3), "proj-atlas", DECISION_CONFIRMED, "确认虚构命名判断"),
        ActivityEvent(_days_ago(4), "proj-boreas", CONTENT_UPDATED, "修订档案说明草稿"),
        ActivityEvent(_days_ago(6), "proj-atlas", PAGE_VIEWED, "查看节点详情"),
        ActivityEvent(_days_ago(7), "proj-atlas", PROPOSAL_ACCEPTED, "接受整理建议"),
        ActivityEvent(_days_ago(12), "proj-boreas", TASK_COMPLETED, "完成档案盘点初稿"),
    )


def demo_day_seed() -> DayRecord:
    """Today's demo plan/worklog so the Today page opens with content."""

    return DayRecord(
        day=_TODAY,
        plan=[
            PlanItem(item_id="plan-001", text="梳理星图目录结构", done=True, project_id="proj-atlas"),
            PlanItem(item_id="plan-002", text="清理重复演示条目", done=False, project_id="proj-atlas"),
            PlanItem(item_id="plan-003", text="写周报草稿", done=False),
        ],
        # 卡片已有「工作记录」小节标题,正文不再自带一级标题,避免重复且压低正文。
        worklog=(
            "- 上午:复核演示条目命名,统一为「类型-编号-说明」。\n"
            "- 下午:标记两处长期停滞项,等待 AI 建议后确认。\n"
        ),
    )


def _tests_resources() -> tuple[Resource, ...]:
    # 完全虚构的演示元数据;仅展示卡片,不读取任何本机文件。
    return (
        Resource(
            resource_id="res-001",
            name="测试环境清单.xlsx",
            kind="表格",
            tags=("常用", "环境"),
            source="演示链接:https://wiki.internal.example.net/atlas/tests",
        ),
        Resource(
            resource_id="res-002",
            name="评审会议纪要.docx",
            kind="文档",
            tags=("会议", "记录"),
            source="演示链接:https://meet.internal.example.net/demo-0825",
        ),
        Resource(
            resource_id="res-003",
            name="设备权限申请函.pdf",
            kind="文档",
            tags=("申请",),
            source="演示链接:https://its.internal.example.net/form/device",
        ),
    )


def _links_resources() -> tuple[Resource, ...]:
    return (
        Resource(
            resource_id="res-101",
            name="测试数据字典_v1.0.xlsx",
            kind="表格",
            tags=("常用",),
            source="演示链接:https://files.internal.example.net/demo/dict",
        ),
        Resource(
            resource_id="res-102",
            name="外部参考.md",
            kind="笔记",
            tags=("外部",),
            source="演示链接:https://vendor.example.net/api-docs",
        ),
    )


def load_demo_workspace() -> tuple[list[Project], list[ActivityEvent]]:
    """Return (projects, activity) with entirely fictional demo content."""

    atlas = Project(
        project_id="proj-atlas",
        name="星图演示库",
        goal="为工作台样片提供一套可整理的虚构资料库",
        phase="执行期",
        current_focus="清理重复条目并补齐关键判断",
        next_milestone="完成 200 条演示条目归档",
        owner="林演示",
        outline=_atlas_outline(),
        actions=_atlas_actions(),
    )
    boreas = Project(
        project_id="proj-boreas",
        name="北风档案",
        goal="演示第二个项目的交叉引用与活动聚合",
        phase="启动期",
        current_focus="盘点档案清单",
        next_milestone="产出档案说明页",
        owner="陈示例",
        outline=(
            OutlineNode(
                node_id="node-boreas-goal",
                project_id="proj-boreas",
                title="目标与边界",
                kind="goal",
                note="仅覆盖虚构档案演示。",
            ),
        ),
        actions=_boreas_actions(),
    )
    return [atlas, boreas], list(_activity())
