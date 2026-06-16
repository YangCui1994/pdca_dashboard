import unittest

from app.backend.markdown import render_capture_markdown, render_project_home
from app.backend.models import Capture, Project


class MarkdownTests(unittest.TestCase):
    def test_render_capture_markdown_contains_frontmatter_and_raw_text(self):
        capture = Capture(
            title="炉温跳变",
            kind="data-issue",
            raw_text="昨晚炉温数据突然跳变",
            ai_output="建议先问平台是否有清洗逻辑变更",
            tags=["炉温", "平台核实"],
        )
        markdown = render_capture_markdown(capture, created="2026-06-17")
        self.assertIn("type: data-issue", markdown)
        self.assertIn("status: inbox", markdown)
        self.assertIn("- 炉温", markdown)
        self.assertIn("## 原始输入", markdown)
        self.assertIn("昨晚炉温数据突然跳变", markdown)
        self.assertIn("## AI 整理结果", markdown)

    def test_render_project_home_prioritizes_progress_context(self):
        project = Project(title="炉温异常排查", created="2026-06-17", tags=["炉温"])
        markdown = render_project_home(project)
        self.assertTrue(markdown.startswith("---"))
        self.assertIn("# 炉温异常排查", markdown)
        self.assertLess(markdown.index("## 任务看板"), markdown.index("## 项目背景"))
        self.assertIn("## 下一步行动项讨论", markdown)


if __name__ == "__main__":
    unittest.main()
