"""数据驱动 Artifact 生成器:真实数据、离线自包含、转义防注入。"""

import unittest

from workbench.domain.fixtures import load_demo_workspace
from workbench.services.flow_artifact import render_flow_html
from workbench.services.workspace_service import WorkspaceService


def _service():
    projects, activity = load_demo_workspace()
    return WorkspaceService(projects, activity)


class FlowArtifactTests(unittest.TestCase):
    def test_renders_real_workspace_data(self):
        html_text = render_flow_html(_service(), "proj-atlas")

        for needle in (
            "项目流图 · 星图演示库",
            "关键判断",          # decision 节点
            "资料与链接",        # resource 节点
            "待推进事项",        # next 节点
            "梳理星图目录结构",  # 进行中行动
            "proj-atlas",       # 来源可追溯
            "```mermaid",       # Mermaid 源文本
            "graph TD",
        ):
            self.assertIn(needle, html_text)

    def test_stalled_action_marked(self):
        html_text = render_flow_html(_service(), "proj-atlas")
        self.assertIn("停滞", html_text)  # act-002 停滞 20 天

    def test_self_contained_no_external_refs(self):
        html_text = render_flow_html(_service(), "proj-atlas")
        self.assertNotIn('src="http', html_text)
        self.assertNotIn('href="http', html_text)
        self.assertNotIn("//cdn", html_text)

    def test_user_content_is_escaped(self):
        service = _service()
        service.rename_action("proj-atlas", "act-001", "<script>alert(1)</script>")

        html_text = render_flow_html(service, "proj-atlas")

        self.assertNotIn("<script>alert", html_text)
        self.assertIn("&lt;script&gt;", html_text)

    def test_unknown_project_renders_notice(self):
        self.assertIn("项目不存在", render_flow_html(_service(), "proj-none"))


if __name__ == "__main__":
    unittest.main()
