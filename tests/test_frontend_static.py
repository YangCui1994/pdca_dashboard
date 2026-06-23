import unittest
from pathlib import Path


class FrontendStaticTests(unittest.TestCase):
    def test_detail_page_has_events_editor(self):
        html = Path("app/frontend/detail.html").read_text(encoding="utf-8")
        js = Path("app/frontend/detail.js").read_text(encoding="utf-8")
        self.assertIn("eventsEditor", html)
        self.assertIn("#eventsEditor", js)
        self.assertIn("events: eventsEditor.value", js)

    def test_index_is_all_items_board(self):
        html = Path("app/frontend/index.html").read_text(encoding="utf-8")
        js = Path("app/frontend/app.js").read_text(encoding="utf-8")
        self.assertIn("全部事项", html)
        self.assertIn("Quiet Workbench", html)
        self.assertIn("statusOverview", html)
        self.assertIn("vaultOverview", html)
        self.assertIn("statusFilter", html)
        self.assertIn("dateFilter", html)
        self.assertIn("tagFilter", html)
        self.assertIn("blockerFilter", html)
        self.assertIn("newTaskForm", html)
        self.assertIn("newTaskTitle", html)
        self.assertIn("newTaskInput", html)
        self.assertIn("createTaskButton", html)
        self.assertIn("showNewTaskButton", html)
        self.assertLess(html.index("newTaskForm"), html.index("quiet-layout"))
        self.assertIn("/today.html", html)
        self.assertIn("/api/work-items", js)
        self.assertIn("/api/capture", js)
        self.assertIn("createTask", js)
        self.assertIn("focusNewTaskForm", js)
        self.assertIn("/api/work-item-status", js)
        self.assertIn("board-card-blocker", js)
        self.assertIn("board-card-summary", js)
        self.assertIn("item.summary", js)
        self.assertIn("applyFilters", js)
        self.assertIn("moveWorkItemStatus", js)
        self.assertIn("empty-state", js)
        self.assertIn("renderOverview", js)
        self.assertIn("/task.html?path=", js)
        self.assertNotIn("rawInput", html)

    def test_today_page_has_pdca_entry(self):
        html = Path("app/frontend/today.html").read_text(encoding="utf-8")
        js = Path("app/frontend/today.js").read_text(encoding="utf-8")
        self.assertIn("今日 PDCA", html)
        self.assertIn("Quiet Workbench", html)
        self.assertIn("pdcaCallout", html)
        self.assertIn("planInput", html)
        self.assertIn("doInput", html)
        self.assertIn("checkInput", html)
        self.assertIn("actInput", html)
        self.assertIn("analyzePdcaButton", html)
        self.assertIn("reviewPdcaButton", html)
        self.assertIn("targetTaskSelect", html)
        self.assertIn("acceptPdcaButton", html)
        self.assertIn("todayItems", html)
        self.assertIn("weekItems", html)
        self.assertIn("todayStatusFilter", html)
        self.assertIn("todayDateFilter", html)
        self.assertIn("planResult", html)
        self.assertIn("trueDoResult", html)
        self.assertIn("candidateDoResult", html)
        self.assertIn("notDoResult", html)
        self.assertIn("checkResult", html)
        self.assertIn("actResult", html)
        self.assertIn("/api/pdca-entry", js)
        self.assertIn("/api/pdca-review", js)
        self.assertIn("/api/work-item-event", js)
        self.assertIn("plan: planInput.value", js)
        self.assertIn("renderPdcaResultSections", js)
        self.assertIn("acceptPdcaAnalysis", js)
        self.assertNotIn("rawInput", html)
        self.assertIn("today-list", html)

    def test_document_pages_map_to_task_folder_markdown_files(self):
        expected = {
            "task.html": "task",
            "context.html": "context",
            "events.html": "events",
            "ai-notes.html": "ai-notes",
        }
        for filename, document_kind in expected.items():
            html = Path(f"app/frontend/{filename}").read_text(encoding="utf-8")
            self.assertIn(f'data-document-kind="{document_kind}"', html)
            self.assertIn("/document.js", html)
            self.assertIn("documentEditor", html)
            self.assertIn("documentPreview", html)
            self.assertIn("helperInput", html)
            self.assertIn("helperSkills", html)
            self.assertIn("aiHelperButton", html)

        js = Path("app/frontend/document.js").read_text(encoding="utf-8")
        self.assertIn('task: {label: "task.md"', js)
        self.assertIn('context: {label: "context.md"', js)
        self.assertIn('events: {label: "events.md"', js)
        self.assertIn('"ai-notes": {label: "ai-notes.md"', js)
        self.assertIn("/api/agent-context", js)
        self.assertIn("/api/context-readiness", js)
        self.assertIn("copyContextButton", Path("app/frontend/task.html").read_text(encoding="utf-8"))
        self.assertIn("downloadContextButton", Path("app/frontend/task.html").read_text(encoding="utf-8"))
        self.assertIn("contextReadiness", Path("app/frontend/task.html").read_text(encoding="utf-8"))

    def test_document_pages_render_markdown_preview(self):
        js = Path("app/frontend/document.js").read_text(encoding="utf-8")
        self.assertIn("documentPreview", Path("app/frontend/task.html").read_text(encoding="utf-8"))
        self.assertIn("markdown-preview", Path("app/frontend/task.html").read_text(encoding="utf-8"))
        self.assertIn("renderMarkdownPreview", js)
        self.assertIn("escapeHtml", js)
        self.assertIn("documentEditor.addEventListener(\"input\"", js)

    def test_document_pages_have_inline_ai_helper_contract(self):
        html = Path("app/frontend/task.html").read_text(encoding="utf-8")
        js = Path("app/frontend/document.js").read_text(encoding="utf-8")
        self.assertIn("document-tabs", html)
        self.assertNotIn("quiet-sidebar", html)
        self.assertIn("helperDraft", html)
        self.assertIn("applyDraftButton", html)
        self.assertIn("/api/document-helper", js)
        self.assertIn("runDocumentHelper", js)
        self.assertIn("applyHelperDraft", js)


if __name__ == "__main__":
    unittest.main()
