"""wrapup:昨日收尾向导的领域逻辑(勾选落盘/顺延处置/Act 草稿/摘要)。"""

import unittest
from datetime import date, timedelta

from workbench.domain.fixtures import demo_day_seed
from workbench.services.wrapup import act_draft, apply_marks, carry_items, plan_summary
from workbench.services.workspace_service import WorkspaceService


def _service_with_yesterday_plan() -> tuple[WorkspaceService, date]:
    service = WorkspaceService()  # 内存模式,demo 种子
    yesterday = date.today() - timedelta(days=1)
    service.add_plan_item(yesterday, "已完成的甲", "")
    service.add_plan_item(yesterday, "没做完的乙", "proj-atlas" if service.projects() else "")
    service.toggle_plan_item(yesterday, "plan-001")
    return service, yesterday


class ApplyMarksTests(unittest.TestCase):
    def test_marks_flip_only_changed_items(self):
        service, yesterday = _service_with_yesterday_plan()
        changed = apply_marks(
            service, yesterday, {"plan-001": False, "plan-002": True}
        )
        self.assertEqual(changed, 2)
        record = service.day_record(yesterday)
        self.assertEqual([item.done for item in record.plan], [False, True])


class CarryItemsTests(unittest.TestCase):
    def test_carry_moves_to_today_and_returns_originals(self):
        service, yesterday = _service_with_yesterday_plan()
        dropped, carried, removed = carry_items(
            service, yesterday, ["plan-002"], "carry"
        )
        self.assertEqual((dropped, carried), (1, 1))
        self.assertEqual([item.text for item in removed], ["没做完的乙"])
        today_texts = [item.text for item in service.day_record(date.today()).plan]
        self.assertIn("没做完的乙", today_texts)
        self.assertNotIn("没做完的乙", [i.text for i in service.day_record(yesterday).plan])

    def test_drop_removes_without_moving(self):
        service, yesterday = _service_with_yesterday_plan()
        dropped, carried, removed = carry_items(
            service, yesterday, ["plan-002"], "drop"
        )
        self.assertEqual((dropped, carried), (1, 0))
        self.assertEqual([item.text for item in removed], ["没做完的乙"])
        self.assertNotIn(
            "没做完的乙", [i.text for i in service.day_record(date.today()).plan]
        )

    def test_unknown_id_is_noop(self):
        service, yesterday = _service_with_yesterday_plan()
        dropped, carried, removed = carry_items(service, yesterday, ["nope"], "carry")
        self.assertEqual((dropped, carried, removed), (0, 0, []))


class ActDraftAndSummaryTests(unittest.TestCase):
    def test_act_draft_combines_carry_and_check(self):
        draft = act_draft(["写周报"], "时间估得太乐观")
        self.assertIn("明日优先:写周报", draft)
        self.assertIn("调整:时间估得太乐观", draft)

    def test_act_draft_empty_inputs(self):
        self.assertEqual(act_draft([], ""), "")

    def test_plan_summary_marks_done(self):
        seed = demo_day_seed()
        summary = plan_summary(seed)
        for line in summary.splitlines():
            self.assertTrue(line.startswith(("[已完成]", "[未完成]")))


if __name__ == "__main__":
    unittest.main()
