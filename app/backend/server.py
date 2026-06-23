from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.backend.ai import FakeAIProvider, HermesCLIProvider
from app.backend.app_state import WorkbenchApp


def build_ai_provider(
    name: str,
    hermes_binary: str = "hermes",
    hermes_timeout: int = 120,
    hermes_model: str = "",
    hermes_provider: str = "",
    hermes_toolsets: str = "",
    hermes_skills: str = "",
):
    if name == "hermes":
        return HermesCLIProvider(
            binary=hermes_binary,
            timeout_seconds=hermes_timeout,
            model=hermes_model,
            inference_provider=hermes_provider,
            toolsets=hermes_toolsets,
            skills=hermes_skills,
        )
    if name == "fake":
        return FakeAIProvider()
    raise ValueError(f"Unsupported provider: {name}")


class WorkbenchHandler(SimpleHTTPRequestHandler):
    app_state: WorkbenchApp
    static_root: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/work-items":
            self._send_json({"items": self.app_state.list_work_item_summaries()})
            return
        if parsed.path == "/api/files":
            self._send_json({"files": self.app_state.list_files()})
            return
        if parsed.path == "/api/work-item":
            path = self._query_value(parsed.query, "path")
            self._send_json(self.app_state.get_work_item(path))
            return
        if parsed.path == "/api/agent-context":
            path = self._query_value(parsed.query, "path")
            self._send_json({"context": self.app_state.render_agent_context(path)})
            return
        if parsed.path == "/api/context-readiness":
            path = self._query_value(parsed.query, "path")
            self._send_json(self.app_state.context_readiness(path))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/capture":
            payload = self._read_json()
            result = self.app_state.capture_with_ai(
                raw_text=payload.get("raw_text", ""),
                action=payload.get("action", "structure_capture"),
                title=payload.get("title", "未命名输入"),
                kind=payload.get("kind", "idea"),
            )
            self._send_json(result)
            return
        if parsed.path == "/api/pdca-entry":
            payload = self._read_json()
            result = self.app_state.analyze_pdca_entry(
                title=payload.get("title", "今日 PDCA 输入"),
                plan=payload.get("plan", ""),
                do=payload.get("do", ""),
                check=payload.get("check", ""),
                act=payload.get("act", ""),
            )
            self._send_json(result)
            return
        if parsed.path == "/api/pdca-review":
            payload = self._read_json()
            result = self.app_state.review_pdca_history(limit=self._int_value(payload.get("limit"), default=20))
            self._send_json(result)
            return
        if parsed.path == "/api/work-item":
            payload = self._read_json()
            self.app_state.save_work_item(
                path=payload.get("path", ""),
                task=payload.get("task", ""),
                context=payload.get("context", ""),
                ai_notes=payload.get("ai_notes", ""),
                events=payload.get("events", ""),
            )
            self._send_json({"ok": True})
            return
        if parsed.path == "/api/document-helper":
            payload = self._read_json()
            result = self.app_state.draft_document_update(
                path=payload.get("path", ""),
                document=payload.get("document", "task"),
                instruction=payload.get("instruction", ""),
                skills=payload.get("skills", ""),
            )
            self._send_json(result)
            return
        if parsed.path == "/api/work-item-status":
            payload = self._read_json()
            result = self.app_state.move_work_item_status(
                path=payload.get("path", ""),
                status=payload.get("status", "inbox"),
            )
            self._send_json(result)
            return
        if parsed.path == "/api/work-item-event":
            payload = self._read_json()
            result = self.app_state.append_work_item_event(
                path=payload.get("path", ""),
                event=payload.get("event", ""),
            )
            self._send_json(result)
            return
        self.send_error(404, "Route not found")

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        relative = parsed.path.lstrip("/") or "index.html"
        return str(self.static_root / relative)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _query_value(self, query: str, key: str) -> str:
        values = parse_qs(query).get(key, [])
        return values[0] if values else ""

    def _int_value(self, value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--provider", choices=["fake", "hermes"], default="fake")
    parser.add_argument("--hermes-binary", default="hermes")
    parser.add_argument("--hermes-timeout", type=int, default=120)
    parser.add_argument("--hermes-model", default="")
    parser.add_argument("--hermes-provider", default="")
    parser.add_argument("--hermes-toolsets", default="")
    parser.add_argument("--hermes-skills", default="")
    parser.add_argument("--vault", default="data-issue-vault")
    args = parser.parse_args()

    WorkbenchHandler.static_root = Path("app/frontend").resolve()
    WorkbenchHandler.app_state = WorkbenchApp(
        vault_root=Path(args.vault),
        ai_provider=build_ai_provider(
            args.provider,
            hermes_binary=args.hermes_binary,
            hermes_timeout=args.hermes_timeout,
            hermes_model=args.hermes_model,
            hermes_provider=args.hermes_provider,
            hermes_toolsets=args.hermes_toolsets,
            hermes_skills=args.hermes_skills,
        ),
    )

    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"Workbench running at http://{args.host}:{args.port}")
    print(f"AI provider: {args.provider}")
    server.serve_forever()


if __name__ == "__main__":
    main()
