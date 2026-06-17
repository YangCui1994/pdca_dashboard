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

                item = self._get_json(f"{base_url}/api/work-item?path={encoded_path}")
                self.assertIn("数据跳变", item["task"])

                self._post_json(
                    f"{base_url}/api/work-item",
                    {
                        "path": str(folder),
                        "task": "更新后的任务",
                        "context": "上下文资料",
                        "ai_notes": "AI 记录",
                    },
                )

                context = self._get_json(f"{base_url}/api/agent-context?path={encoded_path}")
                self.assertIn("更新后的任务", context["context"])
                self.assertIn("上下文资料", context["context"])
                self.assertIn("AI 记录", context["context"])
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
