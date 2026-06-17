import tempfile
import unittest
from pathlib import Path

from app.backend.models import Capture, Project
from app.backend.storage import VaultStorage


class StorageTests(unittest.TestCase):
    def test_save_capture_writes_task_folder_to_inbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            self.assertEqual(folder.parent.name, "inbox")
            self.assertEqual(folder.name, "2026-06-17-炉温跳变")
            self.assertTrue((folder / "assets").is_dir())
            self.assertTrue((folder / "context.md").exists())
            self.assertTrue((folder / "ai-notes.md").exists())
            self.assertIn("数据跳变", (folder / "task.md").read_text(encoding="utf-8"))

    def test_list_work_items_includes_task_folders_and_legacy_markdown_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            task_folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            legacy_file = Path(temp_dir) / "inbox" / "2026-06-17-old-note.md"
            legacy_file.write_text("# Old Note\n", encoding="utf-8")
            self.assertEqual(
                storage.list_work_items(),
                [legacy_file, task_folder],
            )

    def test_save_capture_uses_unique_folder_when_title_repeats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            first_folder = storage.save_capture(Capture(title="炉温跳变", raw_text="第一次"), created="2026-06-17")
            (first_folder / "context.md").write_text("人工补充的上下文", encoding="utf-8")
            second_folder = storage.save_capture(Capture(title="炉温跳变", raw_text="第二次"), created="2026-06-17")
            self.assertEqual(first_folder.name, "2026-06-17-炉温跳变")
            self.assertEqual(second_folder.name, "2026-06-17-炉温跳变-2")
            self.assertEqual((first_folder / "context.md").read_text(encoding="utf-8"), "人工补充的上下文")

    def test_read_work_item_returns_editable_task_folder_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            (folder / "context.md").write_text("平台口径背景", encoding="utf-8")
            (folder / "ai-notes.md").write_text("Agent 初步判断", encoding="utf-8")
            (folder / "assets" / "query.sql").write_text("select 1", encoding="utf-8")
            item = storage.read_work_item(folder)
            self.assertEqual(item["path"], str(folder.resolve()))
            self.assertEqual(item["title"], "炉温跳变")
            self.assertEqual(item["status"], "inbox")
            self.assertIn("数据跳变", item["task"])
            self.assertEqual(item["context"], "平台口径背景")
            self.assertEqual(item["ai_notes"], "Agent 初步判断")
            self.assertEqual(item["assets"], ["query.sql"])

    def test_save_work_item_updates_editable_markdown_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            storage.save_work_item(
                folder,
                task="更新后的任务正文",
                context="更新后的上下文",
                ai_notes="更新后的 AI notes",
            )
            self.assertEqual((folder / "task.md").read_text(encoding="utf-8"), "更新后的任务正文")
            self.assertEqual((folder / "context.md").read_text(encoding="utf-8"), "更新后的上下文")
            self.assertEqual((folder / "ai-notes.md").read_text(encoding="utf-8"), "更新后的 AI notes")

    def test_render_agent_context_includes_task_files_and_assets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            (folder / "context.md").write_text("平台口径背景", encoding="utf-8")
            (folder / "ai-notes.md").write_text("Agent 初步判断", encoding="utf-8")
            (folder / "assets" / "query.sql").write_text("select 1", encoding="utf-8")
            context = storage.render_agent_context(folder)
            self.assertIn("# Agent Task Context", context)
            self.assertIn("## task.md", context)
            self.assertIn("数据跳变", context)
            self.assertIn("## context.md", context)
            self.assertIn("平台口径背景", context)
            self.assertIn("## ai-notes.md", context)
            self.assertIn("Agent 初步判断", context)
            self.assertIn("- query.sql", context)

    def test_create_project_writes_project_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.create_project(Project(title="炉温异常排查", created="2026-06-17"))
            self.assertTrue((folder / "project.md").exists())
            self.assertTrue((folder / "tasks.md").exists())
            self.assertTrue((folder / "log.md").exists())
            self.assertTrue((folder / "ai-notes.md").exists())
            self.assertTrue((folder / "assets").is_dir())


from app.backend.ai import FakeAIProvider
from app.backend.app_state import WorkbenchApp


class WorkbenchAppTests(unittest.TestCase):
    def test_capture_with_ai_saves_task_folder_and_ai_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai(
                raw_text="这个炉温跳变可能是平台清洗问题",
                action="structure_capture",
                title="炉温跳变",
                kind="data-issue",
            )
            saved_folder = Path(result["path"])
            self.assertTrue(saved_folder.is_dir())
            content = (saved_folder / "task.md").read_text(encoding="utf-8")
            self.assertIn("[fake-ai]", content)
            self.assertIn("炉温跳变", content)

    def test_workbench_reads_saves_and_renders_agent_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai(
                raw_text="这个炉温跳变可能是平台清洗问题",
                action="structure_capture",
                title="炉温跳变",
                kind="data-issue",
            )
            path = result["path"]
            item = app.get_work_item(path)
            self.assertIn("炉温跳变", item["task"])
            app.save_work_item(path, task="任务正文", context="上下文资料", ai_notes="AI 记录")
            context = app.render_agent_context(path)
            self.assertIn("任务正文", context)
            self.assertIn("上下文资料", context)
            self.assertIn("AI 记录", context)


if __name__ == "__main__":
    unittest.main()
