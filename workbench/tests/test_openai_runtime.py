"""OpenAI-compatible runtime tests, fully offline (injected transport)."""

import json
import unittest

from workbench.runtime.contracts import (
    COMPLETED,
    FAILED,
    QUEUED,
    RUNNING,
    RunRequest,
)
from workbench.runtime.openai_runtime import OpenAICompatibleRuntime

_PROPOSAL_JSON = (
    '{"proposal_id":"prop-x1","summary":"恢复等待中的行动",'
    '"changes":[{"field":"action.status","target_id":"proj-atlas:act-003",'
    '"current_value":"waiting","new_value":"in_progress"}],'
    '"facts":["act-003 等待超过 14 天"],"inferences":["反馈应已到位"],'
    '"external_knowledge":["等待项每周复核一次"]}'
)


def _sse_transport(chunks):
    """Build a transport yielding OpenAI SSE lines for the given deltas."""

    calls = {}

    def transport(url, headers, payload, timeout):
        calls["url"], calls["headers"], calls["payload"] = url, headers, payload
        for chunk in chunks:
            yield "data: " + json.dumps(
                {"choices": [{"delta": {"content": chunk}}]}, ensure_ascii=False
            )
        yield "data: [DONE]"

    transport.calls = calls
    return transport


class OpenAIRuntimeTests(unittest.TestCase):
    def _runtime(self, chunks, context_calls=None):
        transport = _sse_transport(chunks)

        def build_context(request):
            if context_calls is not None:
                context_calls.append(request)
            return "项目上下文文本"

        runtime = OpenAICompatibleRuntime(
            base_url="http://127.0.0.1:9999/v1",
            model="demo-model",
            api_key="secret",
            build_context=build_context,
            transport=transport,
        )
        return runtime, transport

    def test_stream_order_and_proposal_parsing(self):
        runtime, transport = self._runtime(list(_PROPOSAL_JSON[i : i + 20] for i in range(0, len(_PROPOSAL_JSON), 20)))

        events = list(runtime.events(RunRequest(kind="project.review", project_id="proj-atlas")))

        self.assertEqual(events[0].state, QUEUED)
        self.assertEqual(events[1].state, RUNNING)
        self.assertEqual(events[-1].state, COMPLETED)
        self.assertEqual([e.seq for e in events], sorted(e.seq for e in events))

        proposal = events[-1].proposal
        self.assertEqual(proposal.summary, "恢复等待中的行动")
        self.assertEqual(proposal.changes[0].target_id, "proj-atlas:act-003")
        self.assertEqual(proposal.changes[0].new_value, "in_progress")
        self.assertEqual(proposal.facts, ("act-003 等待超过 14 天",))

        # 请求形状:URL、鉴权、模型与消息
        self.assertEqual(transport.calls["url"], "http://127.0.0.1:9999/v1/chat/completions")
        self.assertEqual(transport.calls["headers"]["Authorization"], "Bearer secret")
        payload = transport.calls["payload"]
        self.assertEqual(payload["model"], "demo-model")
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["messages"][1]["content"], "项目上下文文本")

    def test_context_builder_receives_request(self):
        context_calls = []
        runtime, _transport = self._runtime([_PROPOSAL_JSON], context_calls)

        list(runtime.events(RunRequest(kind="project.review", project_id="proj-boreas")))

        self.assertEqual(context_calls[0].project_id, "proj-boreas")

    def test_fenced_json_output_is_parsed(self):
        runtime, _transport = self._runtime(
            ["说明文字\n", "```json\n", _PROPOSAL_JSON, "\n```"]
        )

        events = list(runtime.events(RunRequest(kind="project.review", project_id="p")))

        self.assertEqual(events[-1].state, COMPLETED)
        self.assertIsNotNone(events[-1].proposal)

    def test_unparseable_output_yields_failed(self):
        runtime, _transport = self._runtime(["今天天气不错", "不适合输出 JSON"])

        events = list(runtime.events(RunRequest(kind="project.review", project_id="p")))

        self.assertEqual(events[-1].state, FAILED)
        self.assertIn("未包含可解析", events[-1].message)
        self.assertIsNone(events[-1].proposal)

    def test_transport_error_yields_failed_not_completed(self):
        def broken_transport(_url, _headers, _payload, _timeout):
            raise RuntimeError("connection refused")
            yield  # pragma: no cover

        runtime = OpenAICompatibleRuntime(
            base_url="http://127.0.0.1:9/v1",
            model="m",
            transport=broken_transport,
        )

        events = list(runtime.events(RunRequest(kind="project.review", project_id="p")))

        self.assertEqual(events[-1].state, FAILED)
        self.assertIn("connection refused", events[-1].message)


if __name__ == "__main__":
    unittest.main()
