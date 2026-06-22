import unittest
from pathlib import Path


class ProjectSkillTests(unittest.TestCase):
    def test_pdca_gate_skill_defines_review_contract(self):
        content = Path(".agents/skills/pdca-gate/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: pdca-gate", content)
        self.assertIn("true_do", content)
        self.assertIn("candidate_do", content)
        self.assertIn("not_do", content)
        self.assertIn("bias_or_judgment", content)
        self.assertIn("evidence_needed", content)
        self.assertIn("Plan", content)
        self.assertIn("Do", content)
        self.assertIn("Check", content)
        self.assertIn("Act", content)


if __name__ == "__main__":
    unittest.main()
