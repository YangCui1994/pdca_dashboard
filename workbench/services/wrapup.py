"""昨日收尾向导的领域逻辑(原型 C 收编为正式版,UI 无关纯函数)。

四步向导:①勾昨日完成情况 → ②Check 引导(可跳)→ ③未完成逐条处置
(今日再做/放弃)→ ④Act+生成今日。这里的函数只碰 service 的显式写
方法,不碰任何控件。
"""

from __future__ import annotations

from datetime import date

from workbench.services.workspace_service import WorkspaceService


def plan_summary(record) -> str:
    return "\n".join(f"{'[已完成]' if i.done else '[未完成]'} {i.text}" for i in record.plan)


def apply_marks(service: WorkspaceService, day: date, marks: dict[str, bool]) -> int:
    """把向导里的勾选落到当日计划上;返回实际变更数。"""

    changed = 0
    for item in service.day_record(day).plan:
        wanted = marks.get(item.item_id, item.done)
        if wanted != item.done:
            service.toggle_plan_item(day, item.item_id)
            changed += 1
    return changed


def carry_items(
    service: WorkspaceService, day: date, item_ids: list[str], action: str
) -> tuple[int, int, list]:
    """action="carry":未完成项移到今天;action="drop":放弃(从当日移除)。

    返回 (处理数, 移入今天的数, 被移除的原文列表)——原文列表供撤销时
    整批退回。
    """

    today = date.today()
    carried = dropped = 0
    removed: list = []
    for item_id in item_ids:
        item = next((i for i in service.day_record(day).plan if i.item_id == item_id), None)
        if item is None:
            continue
        if action == "carry":
            service.add_plan_item(today, item.text, item.project_id)
            carried += 1
        service.remove_plan_item(day, item_id)
        removed.append(item)
        dropped += 1
    return dropped, carried, removed


def act_draft(carry_texts: list[str], check_text: str) -> str:
    """Act 草稿:今天要做的事 + Check 里点名的调整,供编辑。"""

    lines = [f"明日优先:{text}" for text in carry_texts]
    if check_text:
        lines.append(f"调整:{check_text}")
    return "\n".join(lines) if lines else ""
