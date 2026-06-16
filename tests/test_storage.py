import tempfile
import unittest
from pathlib import Path

from app.backend.models import Capture, Project
from app.backend.storage import VaultStorage


class StorageTests(unittest.TestCase):
    def test_save_capture_writes_to_inbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            path = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            self.assertEqual(path.parent.name, "inbox")
            self.assertTrue(path.name.endswith("炉温跳变.md"))
            self.assertIn("数据跳变", path.read_text(encoding="utf-8"))

    def test_create_project_writes_project_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.create_project(Project(title="炉温异常排查", created="2026-06-17"))
            self.assertTrue((folder / "project.md").exists())
            self.assertTrue((folder / "tasks.md").exists())
            self.assertTrue((folder / "log.md").exists())
            self.assertTrue((folder / "ai-notes.md").exists())
            self.assertTrue((folder / "assets").is_dir())


if __name__ == "__main__":
    unittest.main()
