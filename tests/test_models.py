import unittest

from app.backend.models import Capture, Project, Task, normalize_slug


class ModelTests(unittest.TestCase):
    def test_normalize_slug_keeps_chinese_and_ascii_words(self):
        self.assertEqual(normalize_slug("数据异常 Follow Up!"), "数据异常-follow-up")

    def test_task_requires_allowed_status(self):
        with self.assertRaises(ValueError):
            Task(title="Bad status", status="blocked")

    def test_capture_defaults_to_inbox(self):
        capture = Capture(raw_text="温度数据昨天突然跳变")
        self.assertEqual(capture.status, "inbox")
        self.assertEqual(capture.kind, "idea")

    def test_project_folder_name_uses_date_and_slug(self):
        project = Project(title="炉温异常排查", created="2026-06-17")
        self.assertEqual(project.folder_name(), "2026-06-17-炉温异常排查")


if __name__ == "__main__":
    unittest.main()
