"""Artifact 契约:自包含、离线、含来源 ID 与交互脚本。"""

import os
import re
import unittest

_ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts",
    "project-flow.html",
)


class ArtifactContractTests(unittest.TestCase):
    def setUp(self):
        with open(_ARTIFACT, encoding="utf-8") as handle:
            self.html = handle.read()

    def test_artifact_file_exists(self):
        self.assertTrue(os.path.isfile(_ARTIFACT))

    def test_no_external_http_or_cdn_references(self):
        # 任何形式的外部资源加载(src/href/css url()/@import)都禁止
        loading_refs = re.findall(
            r'(?:src|href)\s*=\s*["\']\s*(?:https?:)?//[^"\']+["\']', self.html
        )
        self.assertEqual(loading_refs, [])
        self.assertEqual(re.findall(r"url\(\s*['\"]?https?://", self.html), [])
        self.assertNotIn("@import", self.html)
        self.assertNotIn("cdn.", self.html.lower())
        # 文本中允许出现且仅允许出现虚构演示域名 internal.example.net
        url_mentions = set(re.findall(r"https?://[^'\"\s<)]+", self.html))
        fictional = {
            u for u in url_mentions if "internal.example.net" in u
        }
        self.assertEqual(url_mentions, fictional, "出现非虚构域名")

    def test_contains_project_source_id(self):
        self.assertIn("proj-atlas", self.html)

    def test_contains_interactive_script_and_flow_nodes(self):
        self.assertIn("<script>", self.html)
        self.assertIn("onclick", self.html)
        for node_label in ("项目", "决策", "资源", "下一行动"):
            self.assertIn(node_label, self.html)

    def test_contains_mermaid_probe_block_clearly_marked(self):
        self.assertIn("仅用于 Mermaid 能力探测", self.html)
        self.assertIn("```mermaid", self.html)


if __name__ == "__main__":
    unittest.main()
