import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.backend.ai import FakeAIProvider
from app.backend.app_state import WorkbenchApp
from app.backend.models import Capture
from app.backend.server import WorkbenchHandler


class ServerRouteTests(unittest.TestCase):
    def test_work_item_routes_read_save_and_render_agent_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            folder = app.storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            server = self._start_server(app)
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                encoded_path = quote(str(folder))

                summaries = self._get_json(f"{base_url}/api/work-items")
                self.assertEqual(len(summaries["items"]), 1)
                self.assertEqual(summaries["items"][0]["title"], "炉温跳变")

                item = self._get_json(f"{base_url}/api/work-item?path={encoded_path}")
                self.assertIn("数据跳变", item["task"])

                self._post_json(
                    f"{base_url}/api/work-item",
                    {
                        "path": str(folder),
                        "task": "更新后的任务",
                        "context": "上下文资料",
                        "ai_notes": "AI 记录",
                        "events": "# Events\n\n- 发送了复盘草稿",
                    },
                )

                context = self._get_json(f"{base_url}/api/agent-context?path={encoded_path}")
                self.assertIn("更新后的任务", context["context"])
                self.assertIn("上下文资料", context["context"])
                self.assertIn("AI 记录", context["context"])
                self.assertIn("发送了复盘草稿", context["context"])
            finally:
                server.shutdown()
                server.server_close()

    def test_pdca_entry_and_review_routes_record_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            server = self._start_server(app)
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                entry = self._post_json(
                    f"{base_url}/api/pdca-entry",
                    {
                        "title": "今日 PDCA 输入",
                        "plan": "完成 dashboard v1",
                        "do": "已经完成四输入框设计",
                        "check": "等待测试结果",
                        "act": "根据测试补缺口",
                    },
                )
                self.assertIn("[fake-ai]", entry["ai_output"])
                self.assertTrue(Path(entry["log_path"]).exists())
                self.assertIn("完成 dashboard v1", Path(entry["log_path"]).read_text(encoding="utf-8"))

                review = self._post_json(f"{base_url}/api/pdca-review", {"limit": 10})
                self.assertIn("[fake-ai]", review["ai_output"])
                self.assertTrue(Path(review["review_path"]).exists())
                self.assertIn("完成 dashboard v1", Path(review["review_path"]).read_text(encoding="utf-8"))
            finally:
                server.shutdown()
                server.server_close()

    def test_status_event_and_context_readiness_routes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            folder = app.storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            server = self._start_server(app)
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                moved = self._post_json(
                    f"{base_url}/api/work-item-status",
                    {"path": str(folder), "status": "active"},
                )
                self.assertIn("/active/", moved["path"])

                event = self._post_json(
                    f"{base_url}/api/work-item-event",
                    {"path": moved["path"], "event": "PDCA Review\n\n- true_do: wrote tests"},
                )
                self.assertTrue(event["ok"])

                encoded_path = quote(moved["path"])
                item = self._get_json(f"{base_url}/api/work-item?path={encoded_path}")
                self.assertIn("true_do: wrote tests", item["events"])

                readiness = self._get_json(f"{base_url}/api/context-readiness?path={encoded_path}")
                self.assertFalse(readiness["ready"])
                self.assertIn("missing", readiness)
            finally:
                server.shutdown()
                server.server_close()

    def _start_server(self, app: WorkbenchApp) -> ThreadingHTTPServer:
        class TestHandler(WorkbenchHandler):
            pass

        TestHandler.app_state = app
        TestHandler.static_root = Path("app/frontend").resolve()
        server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def _get_json(self, url: str) -> dict:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
