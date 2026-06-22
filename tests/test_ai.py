import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.ai import FakeAIProvider, HermesCLIProvider
from app.backend.prompts import render_prompt


class AITests(unittest.TestCase):
    def test_render_prompt_replaces_input_marker(self):
        prompt = render_prompt(Path("app/prompts/structure_capture.md"), "原始想法")
        self.assertIn("原始想法", prompt)
        self.assertNotIn("{{input}}", prompt)

    def test_fake_provider_returns_predictable_text(self):
        provider = FakeAIProvider()
        self.assertEqual(provider.complete("hello"), "[fake-ai]\nhello")

    def test_hermes_provider_calls_oneshot_mode(self):
        completed = subprocess.CompletedProcess(args=["hermes"], returncode=0, stdout="整理完成\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            provider = HermesCLIProvider(binary="/Users/yang/.local/bin/hermes")
            result = provider.complete("请整理")
        self.assertEqual(result, "整理完成")
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[0], "/Users/yang/.local/bin/hermes")
        self.assertIn("-z", args)

    def test_pdca_gate_prompt_replaces_input_marker(self):
        prompt = render_prompt(Path("app/prompts/pdca_gate.md"), "今天我觉得推进慢，因为对方不配合")
        self.assertIn("今天我觉得推进慢，因为对方不配合", prompt)
        self.assertNotIn("{{input}}", prompt)
        self.assertIn("true_do", prompt)
        self.assertIn("bias_or_judgment", prompt)

    def test_pdca_periodic_review_prompt_replaces_input_marker(self):
        prompt = render_prompt(Path("app/prompts/pdca_periodic_review.md"), "## 2026-06-22 - 今日 PDCA")
        self.assertIn("## 2026-06-22 - 今日 PDCA", prompt)
        self.assertNotIn("{{input}}", prompt)
        self.assertIn("Plan", prompt)
        self.assertIn("Do", prompt)
        self.assertIn("周期 Review", prompt)


if __name__ == "__main__":
    unittest.main()
