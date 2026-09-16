"""PromptLibrary:注册表发现、边界声明、变量渲染、fake 输出。

提示词文件是数据(workbench/prompts/),不是代码;
这里验证"扔进一个 md 即新增模式"的契约。prototypes/uxbase.loader
是它的 re-export 壳(原型零改动),一并在壳层契约里验证。
"""

import tempfile
import unittest
from pathlib import Path

from workbench.services.prompt_library import PROMPTS_ROOT, PromptLibrary

_OFFICIAL_PROMPTS = PROMPTS_ROOT  # workbench/prompts(正式家)
_SHELL = "prototypes.uxbase.loader"


class RepoPromptLibraryTests(unittest.TestCase):
    """仓库自带提示词库的契约(阶段 5 + 思维模式 4)。"""

    def setUp(self):
        self.library = PromptLibrary(_OFFICIAL_PROMPTS)

    def test_stage_registry_complete(self):
        keys = {spec.key for spec in self.library.stages()}
        self.assertEqual(
            keys,
            {"capture_critique", "plan_suggest", "day_check", "weekly_review", "file_route"},
        )

    def test_thinking_registry_discovers_files(self):
        modes = self.library.thinking()
        titles = {spec.title for spec in modes}
        # brainstorm / grill_me / six_hats / premortem 各有中文名
        self.assertGreaterEqual(len(modes), 4)
        self.assertIn("头脑风暴", titles)
        self.assertIn("拷问假设", titles)

    def test_frontmatter_declares_boundaries(self):
        for spec in list(self.library.stages()) + list(self.library.thinking()):
            self.assertTrue(spec.reads, f"{spec.path} 缺 reads 边界声明")
            self.assertTrue(spec.writes, f"{spec.path} 缺 writes 边界声明")

    def test_render_replaces_known_and_keeps_unknown(self):
        spec = self.library.get("stages", "capture_critique")
        rendered = spec.render(idea_text="测试想法", project_brief="proj-atlas 星图")
        self.assertIn("测试想法", rendered)
        self.assertIn("proj-atlas 星图", rendered)

    def test_fake_output_available_offline(self):
        spec = self.library.get("thinking", "grill_me")
        self.assertTrue(spec.fake_output)
        reply = spec.fake_reply(spec.render(target_kind="想法", target_text="x"))
        self.assertTrue(reply)


class DropInModeTests(unittest.TestCase):
    """扔进一个 md 即新增思维模式,不改代码。"""

    def test_new_md_file_appears_in_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "thinking").mkdir()
            (root / "thinking" / "reverse_thinking.md").write_text(
                "---\nname: reverse_thinking\ntitle: 逆向思考\nreads: 目标\nwrites: 草稿\n---\n"
                "反过来想:{{target_text}}\n<fake>\n1. 先想怎么搞砸\n</fake>\n",
                encoding="utf-8",
            )
            library = PromptLibrary(root)

            modes = library.thinking()
            self.assertEqual([m.key for m in modes], ["reverse_thinking"])
            rendered = modes[0].render(target_text="自动标注异常")
            self.assertIn("自动标注异常", rendered)
            self.assertEqual(modes[0].fake_output, "1. 先想怎么搞砸")

    def test_unknown_prompt_raises_key_error(self):
        library = PromptLibrary(_OFFICIAL_PROMPTS)
        with self.assertRaises(KeyError):
            library.get("thinking", "no_such_mode")

    def test_uxbase_shell_reexports_official(self):
        """原型壳与正式实现同源:同一把 key 在两边取到同一文件。"""

        import importlib

        shell = importlib.import_module(_SHELL)
        self.assertIs(shell.PromptLibrary, PromptLibrary)
        shell_library = shell.PromptLibrary()
        self.assertEqual(
            shell_library.get("stages", "day_check").path,
            PromptLibrary(_OFFICIAL_PROMPTS).get("stages", "day_check").path,
        )


if __name__ == "__main__":
    unittest.main()
