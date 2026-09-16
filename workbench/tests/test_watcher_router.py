"""FileWatcher + file_route 路由:去重、变更重处理、决策解析、fake 路由。

实现住 workbench/services 与 workbench/runtime;text_runtime 的壳在
prototypes/uxbase(原型零改动),本文件直接测正式家。
"""

import tempfile
import unittest
from pathlib import Path

from workbench.domain.fixtures import load_demo_workspace
from workbench.services.file_routing import parse_route_decision, route_file
from workbench.services.file_watcher import FileWatcher
from workbench.services.prompt_library import PROMPTS_ROOT, PromptLibrary
from workbench.runtime.text_runtime import FakePromptRuntime
from workbench.services.workspace_service import WorkspaceService


class FileWatcherTests(unittest.TestCase):
    def test_new_files_processed_once_then_deduped(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = FileWatcher(tmp)
            (Path(tmp) / "note.md").write_text("第一版", encoding="utf-8")

            self.assertEqual([p.name for p in watcher.scan_once()], ["note.md"])
            self.assertEqual(watcher.scan_once(), [])  # mtime 未变 → 去重

    def test_changed_file_reprocessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = FileWatcher(tmp)
            path = Path(tmp) / "note.md"
            path.write_text("第一版", encoding="utf-8")
            watcher.scan_once()

            path.write_text("第二版内容变长了", encoding="utf-8")
            # Windows 上两次快速写入可能共享 mtime 粒度;显式前移时间戳保证确定性
            stamp = path.stat().st_mtime + 10
            import os

            os.utime(path, (stamp, stamp))
            fresh = watcher.scan_once()

            self.assertEqual([p.name for p in fresh], ["note.md"])

    def test_unsupported_suffix_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = FileWatcher(tmp)
            (Path(tmp) / "image.png").write_bytes(b"\x89PNG")
            (Path(tmp) / ".processed.json").write_text("{}", encoding="utf-8")

            self.assertEqual(watcher.scan_once(), [])


class RouteDecisionTests(unittest.TestCase):
    def test_parse_tolerant_json(self):
        decision = parse_route_decision(
            "a.md", '前置说明 {"related_project_id": "proj-atlas", "confidence": "high", "progress_entry": "完成接入", "reason": "命中"} 后置'
        )
        self.assertEqual(decision.project_id, "proj-atlas")
        self.assertTrue(decision.auto_append)

    def test_parse_garbage_routes_to_none(self):
        decision = parse_route_decision("a.md", "不是 JSON")
        self.assertEqual(decision.project_id, "none")
        self.assertFalse(decision.auto_append)

    def test_fake_route_high_and_low_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = WorkspaceService(*load_demo_workspace())
            runtime = FakePromptRuntime()
            library = PromptLibrary(PROMPTS_ROOT)

            high = Path(tmp) / "日报核对.md"
            high.write_text("渠道日报核对完成,口径已对齐。", encoding="utf-8")
            decision = route_file(runtime, library, "proj-atlas 星图", high)
            self.assertEqual(decision.project_id, "proj-atlas")
            self.assertEqual(decision.confidence, "high")
            self.assertTrue(decision.auto_append)

            low = Path(tmp) / "随手记.md"
            low.write_text("[低置信] 一些不成形的念头", encoding="utf-8")
            decision = route_file(runtime, library, "proj-atlas 星图", low)
            self.assertEqual(decision.confidence, "low")
            self.assertFalse(decision.auto_append)

            # 高置信分支真的能追加进度并撤销(服务层回环)
            entry = service.append_project_progress("proj-atlas", decision.progress_entry)
            decision_high = route_file(runtime, library, "proj-atlas 星图", high)
            entry2 = service.append_project_progress("proj-atlas", decision_high.progress_entry)
            self.assertIsNotNone(entry)
            self.assertIsNotNone(entry2)
            self.assertTrue(service.remove_project_progress("proj-atlas", entry2))


if __name__ == "__main__":
    unittest.main()
