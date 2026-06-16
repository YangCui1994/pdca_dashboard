import unittest

from app.backend.agent_modes import (
    AgentRole,
    create_approval_chain_plan,
    create_round_table_plan,
    create_single_agent_plan,
)


class AgentModeTests(unittest.TestCase):
    def test_single_agent_plan_has_one_executor_role(self):
        plan = create_single_agent_plan(action="structure_capture", prompt="整理这段输入")
        self.assertEqual(plan.mode, "single")
        self.assertEqual([role.name for role in plan.roles], ["executor"])
        self.assertEqual(plan.approval_steps, [])

    def test_round_table_requires_at_least_two_roles(self):
        with self.assertRaises(ValueError):
            create_round_table_plan(
                prompt="是否推进这个项目",
                roles=[AgentRole(name="product", responsibility="判断用户价值")],
            )

    def test_round_table_keeps_role_responsibilities(self):
        plan = create_round_table_plan(
            prompt="是否推进这个项目",
            roles=[
                AgentRole(name="product", responsibility="判断用户价值"),
                AgentRole(name="engineering", responsibility="判断实现成本"),
                AgentRole(name="risk", responsibility="指出推进风险"),
            ],
        )
        self.assertEqual(plan.mode, "round-table")
        self.assertEqual(plan.roles[1].responsibility, "判断实现成本")

    def test_approval_chain_preserves_ordered_review_steps(self):
        plan = create_approval_chain_plan(
            prompt="生成领导反馈草稿",
            reviewers=["risk-review", "final-editor"],
        )
        self.assertEqual(plan.mode, "approval-chain")
        self.assertEqual(plan.approval_steps, ["risk-review", "final-editor"])


if __name__ == "__main__":
    unittest.main()
