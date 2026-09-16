import unittest

from workbench.runtime.contracts import RunRequest
from workbench.runtime.fake_runtime import FakeRuntime


class FakeRuntimeStateSequenceTests(unittest.TestCase):
    def test_events_follow_queued_running_using_tool_completed_order(self):
        runtime = FakeRuntime()

        events = list(
            runtime.events(
                RunRequest(kind="project.review", project_id="demo-project")
            )
        )

        states = [event.state for event in events]
        self.assertEqual(states[0], "queued")
        self.assertEqual(states[1], "running")
        self.assertEqual(states[-1], "completed")
        self.assertTrue(all(state == "using_tool" for state in states[2:-1]))

    def test_streams_at_least_100_ordered_unique_using_tool_events(self):
        runtime = FakeRuntime()

        events = list(
            runtime.events(
                RunRequest(kind="project.review", project_id="demo-project")
            )
        )

        tool_events = [event for event in events if event.state == "using_tool"]
        self.assertGreaterEqual(len(tool_events), 100)
        seqs = [event.seq for event in events]
        self.assertEqual(len(set(seqs)), len(seqs))
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual([event.state for event in events].count("completed"), 1)


if __name__ == "__main__":
    unittest.main()
