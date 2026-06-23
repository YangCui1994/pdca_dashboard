import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.ai import CodexCLIProvider, FakeAIProvider, HermesCLIProvider, OpenCodeCLIProvider
from app.backend.prompts import render_prompt
from app.backend.server import build_ai_provider


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
            provider = HermesCLIProvider(binary="hermes")
            result = provider.complete("请整理")
        self.assertEqual(result, "整理完成")
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[0], "hermes")
        self.assertIn("-z", args)

    def test_hermes_provider_can_preload_model_toolsets_and_skills(self):
        completed = subprocess.CompletedProcess(args=["hermes"], returncode=0, stdout="Hermes 输出\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            provider = HermesCLIProvider(
                binary="hermes",
                model="company/MiniMax-M2.7",
                inference_provider="company",
                toolsets="mcp,skills",
                skills="pdca-gate,stock-analysis",
            )
            result = provider.complete("请用 pdca-gate 整理")
        self.assertEqual(result, "Hermes 输出")
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ["hermes", "-z"])
        self.assertIn("--model", args)
        self.assertIn("company/MiniMax-M2.7", args)
        self.assertIn("--provider", args)
        self.assertIn("company", args)
        self.assertIn("--toolsets", args)
        self.assertIn("mcp,skills", args)
        self.assertIn("--skills", args)
        self.assertIn("pdca-gate,stock-analysis", args)

    def test_codex_provider_calls_exec_readonly_ephemeral(self):
        completed = subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="Codex 输出\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            provider = CodexCLIProvider(binary="codex", cwd="/tmp/workbench", model="gpt-5")
            result = provider.complete("请整理")
        self.assertEqual(result, "Codex 输出")
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ["codex", "exec"])
        self.assertIn("-C", args)
        self.assertIn("/tmp/workbench", args)
        self.assertIn("--sandbox", args)
        self.assertIn("read-only", args)
        self.assertIn("--ask-for-approval", args)
        self.assertIn("never", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("--model", args)
        self.assertIn("gpt-5", args)
        self.assertEqual(args[-1], "-")
        self.assertEqual(run.call_args.kwargs["input"], "请整理")

    def test_opencode_provider_calls_run_for_windows_handoff(self):
        completed = subprocess.CompletedProcess(args=["opencode"], returncode=0, stdout="OpenCode 输出\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            provider = OpenCodeCLIProvider(binary="opencode", model="company/MiniMax-M2.7")
            result = provider.complete("请整理")
        self.assertEqual(result, "OpenCode 输出")
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ["opencode", "run"])
        self.assertIn("--model", args)
        self.assertIn("company/MiniMax-M2.7", args)
        self.assertEqual(run.call_args.kwargs["input"], "请整理")

    def test_build_ai_provider_passes_hermes_agent_options(self):
        provider = build_ai_provider(
            "hermes",
            hermes_binary="hermes",
            hermes_model="company/MiniMax-M2.7",
            hermes_provider="company",
            hermes_toolsets="mcp,skills",
            hermes_skills="pdca-gate",
        )
        self.assertIsInstance(provider, HermesCLIProvider)
        self.assertEqual(provider.model, "company/MiniMax-M2.7")
        self.assertEqual(provider.inference_provider, "company")
        self.assertEqual(provider.toolsets, "mcp,skills")
        self.assertEqual(provider.skills, "pdca-gate")

    def test_build_ai_provider_supports_codex_and_opencode(self):
        codex = build_ai_provider(
            "codex",
            codex_binary="codex",
            codex_model="gpt-5",
            codex_timeout=180,
            codex_cwd="/tmp/workbench",
        )
        self.assertIsInstance(codex, CodexCLIProvider)
        self.assertEqual(codex.model, "gpt-5")
        self.assertEqual(codex.timeout_seconds, 180)
        self.assertEqual(codex.cwd, "/tmp/workbench")

        opencode = build_ai_provider(
            "opencode",
            opencode_binary="opencode",
            opencode_model="company/MiniMax-M2.7",
            opencode_timeout=240,
        )
        self.assertIsInstance(opencode, OpenCodeCLIProvider)
        self.assertEqual(opencode.model, "company/MiniMax-M2.7")
        self.assertEqual(opencode.timeout_seconds, 240)

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
