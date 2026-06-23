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
            self.assertTrue((folder / "events.md").exists())
            self.assertIn("# Events", (folder / "events.md").read_text(encoding="utf-8"))
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
            self.assertEqual(item["events"], "# Events\n\n")
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
                events="# Events\n\n- did one thing",
            )
            self.assertEqual((folder / "task.md").read_text(encoding="utf-8"), "更新后的任务正文")
            self.assertEqual((folder / "context.md").read_text(encoding="utf-8"), "更新后的上下文")
            self.assertEqual((folder / "ai-notes.md").read_text(encoding="utf-8"), "更新后的 AI notes")
            self.assertEqual((folder / "events.md").read_text(encoding="utf-8"), "# Events\n\n- did one thing")

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
            self.assertIn("## events.md", context)
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

    def test_list_work_item_summaries_extracts_card_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            storage.save_work_item(
                folder,
                task="# 炉温跳变\n\n## 当前卡点\n\n等待平台确认清洗口径。\n\n## 已有基础\n\n已有 SQL 初稿。",
                context="字段口径来自平台文档。",
                ai_notes="AI 认为需要补数据截图。",
                events="# Events\n\n- 2026-06-17 对比了两版 SQL。",
            )
            summaries = storage.list_work_item_summaries()
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["title"], "炉温跳变")
            self.assertEqual(summaries[0]["status"], "inbox")
            self.assertEqual(summaries[0]["created"], "2026-06-17")
            self.assertEqual(summaries[0]["blocker"], "等待平台确认清洗口径。")
            self.assertEqual(summaries[0]["basis"], "已有 SQL 初稿。")

    def test_list_work_item_summaries_returns_short_card_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            storage.save_work_item(
                folder,
                task=(
                    "---\n"
                    "type: data-issue\n"
                    "status: inbox\n"
                    "created: 2026-06-17\n"
                    "summary: 炉温口径复核\n"
                    "---\n\n"
                    "# 炉温跳变\n\n"
                    "这是一段很长的任务叙述，主页不应该直接展示整段正文。"
                ),
                context="",
                ai_notes="",
                events="# Events\n\n",
            )
            summary = storage.list_work_item_summaries()[0]
            self.assertEqual(summary["summary"], "炉温口径复核")

    def test_list_work_item_summaries_falls_back_to_truncated_body_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="长任务", raw_text="x"), created="2026-06-17")
            storage.save_work_item(
                folder,
                task=(
                    "# 长任务\n\n"
                    "这是一个特别长的主页说明，包含很多背景、原因、证据、下一步动作和验收口径，"
                    "但看板卡片只应该给出一段短描述。"
                ),
                context="",
                ai_notes="",
                events="# Events\n\n",
            )
            summary = storage.list_work_item_summaries()[0]["summary"]
            self.assertLessEqual(len(summary), 31)
            self.assertTrue(summary.endswith("..."))

    def test_list_work_item_summaries_uses_frontmatter_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(
                Capture(title="炉温跳变", raw_text="数据跳变", tags=["sql", "pdca"]),
                created="2026-06-17",
            )
            (folder / "task.md").write_text(
                """---
type: data-issue
status: inbox
created: 2026-06-18
tags:
  - sql
  - pdca
---

# 炉温跳变

## 当前卡点

等待确认。
""",
                encoding="utf-8",
            )
            summary = storage.list_work_item_summaries()[0]
            self.assertEqual(summary["created"], "2026-06-18")
            self.assertEqual(summary["tags"], ["sql", "pdca"])

    def test_move_work_item_status_moves_folder_between_status_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            moved = storage.move_work_item_status(folder, "active")
            self.assertEqual(moved.parent.name, "active")
            self.assertTrue((moved / "task.md").exists())
            self.assertFalse(folder.exists())

    def test_append_work_item_event_adds_markdown_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            storage.append_work_item_event(folder, "PDCA Review\n\n- Plan: ok", created_at="2026-06-22T09:00:00")
            events = (folder / "events.md").read_text(encoding="utf-8")
            self.assertIn("## 2026-06-22T09:00:00", events)
            self.assertIn("PDCA Review", events)

    def test_context_readiness_reports_missing_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            readiness = storage.context_readiness(folder)
            self.assertFalse(readiness["ready"])
            self.assertIn("context.md lacks non-heading context", readiness["missing"])
            (folder / "context.md").write_text("字段口径来自平台文档。", encoding="utf-8")
            (folder / "events.md").write_text("# Events\n\n- 2026-06-17 对比了 SQL。", encoding="utf-8")
            ready = storage.context_readiness(folder)
            self.assertTrue(ready["ready"])
            self.assertEqual(ready["missing"], [])

    def test_append_pdca_entry_writes_global_input_log(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            log_path = storage.append_pdca_entry(
                title="今日 PDCA 输入",
                plan="完成 dashboard v1",
                do="已经拆出四个输入框",
                check="还没有跑测试",
                act="补测试并收窄范围",
                ai_output="Plan 过于 ambitious",
                created_at="2026-06-22T10:30:00",
            )
            self.assertEqual(log_path, Path(temp_dir) / "reviews" / "pdca-input-log.md")
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("## 2026-06-22T10:30:00 - 今日 PDCA 输入", content)
            self.assertIn("### Plan\n\n完成 dashboard v1", content)
            self.assertIn("### Do\n\n已经拆出四个输入框", content)
            self.assertIn("### AI Analysis\n\nPlan 过于 ambitious", content)

    def test_read_recent_pdca_entries_returns_latest_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            storage.append_pdca_entry("第一条", "p1", "d1", "c1", "a1", "ai1", created_at="2026-06-22T10:00:00")
            storage.append_pdca_entry("第二条", "p2", "d2", "c2", "a2", "ai2", created_at="2026-06-22T11:00:00")
            history = storage.read_recent_pdca_entries(limit=1)
            self.assertNotIn("第一条", history)
            self.assertIn("第二条", history)

    def test_save_pdca_review_writes_timestamped_review_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            review_path = storage.save_pdca_review("Plan 经常过大", created_at="2026-06-22T12:15:00")
            self.assertEqual(review_path, Path(temp_dir) / "reviews" / "2026-06-22-121500-pdca-review.md")
            self.assertEqual(review_path.read_text(encoding="utf-8"), "Plan 经常过大")


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

    def test_document_helper_returns_draft_without_saving(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai("数据跳变", "structure_capture", title="炉温跳变", kind="data-issue")
            path = result["path"]
            before = Path(path, "task.md").read_text(encoding="utf-8")
            helper = app.draft_document_update(
                path=path,
                document="task",
                instruction="压缩成一个可执行任务",
                skills="pdca-gate, stock-analysis",
            )
            after = Path(path, "task.md").read_text(encoding="utf-8")
            self.assertEqual(after, before)
            self.assertIn("[fake-ai]", helper["draft"])
            self.assertIn("pdca-gate, stock-analysis", helper["draft"])
            self.assertIn("压缩成一个可执行任务", helper["draft"])

    def test_capture_with_pdca_gate_action_saves_ai_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai(
                raw_text="今天我觉得推进慢，因为对方不配合",
                action="pdca_gate",
                title="今日 PDCA 输入",
                kind="task",
            )
            saved_folder = Path(result["path"])
            content = (saved_folder / "task.md").read_text(encoding="utf-8")
            self.assertIn("[fake-ai]", content)
            self.assertIn("bias_or_judgment", content)
            self.assertIn("今日 PDCA 输入", content)

    def test_analyze_pdca_entry_records_initial_thoughts_without_creating_task_card(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.analyze_pdca_entry(
                title="今日 PDCA 输入",
                plan="今天完成所有页面",
                do="我觉得推进很慢",
                check="没有量化证据",
                act="拆成两个小动作",
            )
            self.assertIn("[fake-ai]", result["ai_output"])
            self.assertEqual(result["log_path"], str(Path(temp_dir) / "reviews" / "pdca-input-log.md"))
            self.assertEqual(app.list_work_item_summaries(), [])
            self.assertIn("今天完成所有页面", Path(result["log_path"]).read_text(encoding="utf-8"))

    def test_review_pdca_history_saves_periodic_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            app.analyze_pdca_entry("今日 PDCA 输入", "计划很大", "做了讨论", "没有检查", "明天再说")
            result = app.review_pdca_history(limit=5)
            self.assertIn("[fake-ai]", result["ai_output"])
            self.assertTrue(Path(result["review_path"]).exists())
            self.assertIn("计划很大", Path(result["review_path"]).read_text(encoding="utf-8"))

    def test_workbench_updates_status_appends_event_and_checks_context_readiness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai("数据跳变", "structure_capture", title="炉温跳变", kind="data-issue")
            moved = app.move_work_item_status(result["path"], "active")
            self.assertIn("/active/", moved["path"])
            app.append_work_item_event(moved["path"], "PDCA Review\n\n- true_do: wrote tests")
            item = app.get_work_item(moved["path"])
            self.assertIn("true_do: wrote tests", item["events"])
            readiness = app.context_readiness(moved["path"])
            self.assertFalse(readiness["ready"])


if __name__ == "__main__":
    unittest.main()
