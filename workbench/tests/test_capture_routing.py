"""capture_routing:三种落点路由 + 计划建议草稿逐行解析。"""

import unittest

from workbench.services.capture_routing import parse_plan_lines, route_capture

_NAMES = {"星图": "proj-atlas", "Boreas": "proj-boreas"}


class RouteCaptureTests(unittest.TestCase):
    def test_bang_routes_to_plan(self):
        kind, text, project_id = route_capture("!写周报", _NAMES)
        self.assertEqual(kind, "plan")
        self.assertEqual(text, "写周报")
        self.assertEqual(project_id, "")

    def test_hash_with_known_project_routes_to_plan(self):
        kind, text, project_id = route_capture("#星图 跟进口径问题", _NAMES)
        self.assertEqual((kind, text, project_id), ("plan", "跟进口径问题", "proj-atlas"))

    def test_hash_project_only_becomes_plan_with_head_text(self):
        kind, text, project_id = route_capture("#星图", _NAMES)
        self.assertEqual((kind, text, project_id), ("plan", "星图", "proj-atlas"))

    def test_hash_unknown_project_falls_back_to_idea(self):
        kind, text, project_id = route_capture("#不存在的项目 想法", _NAMES)
        self.assertEqual((kind, text, project_id), ("idea", "#不存在的项目 想法", ""))

    def test_plain_text_routes_to_idea(self):
        kind, text, _pid = route_capture("  随手记一条想法 ", _NAMES)
        self.assertEqual((kind, text), ("idea", "随手记一条想法"))

    def test_empty_bang_text_yields_empty_payload(self):
        _kind, text, _pid = route_capture("!", _NAMES)
        self.assertEqual(text, "")


class ParsePlanLinesTests(unittest.TestCase):
    def test_numbered_lines_extracted(self):
        draft = "先做这些:\n1. 写周报\n2、跟进口径 (proj-atlas)\n不是编号行"
        self.assertEqual(
            parse_plan_lines(draft),
            [("写周报", ""), ("跟进口径", "proj-atlas")],
        )

    def test_empty_text_yields_no_items(self):
        self.assertEqual(parse_plan_lines(""), [])


if __name__ == "__main__":
    unittest.main()
