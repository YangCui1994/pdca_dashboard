# PDCA Gate And Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-local `pdca-gate` skill and split the workbench into a daily PDCA entry page plus an all-items card board.

**Architecture:** Keep the current dependency-light Python stdlib backend and static frontend. Add a project-local skill under `.agents/skills/`, add a `pdca_gate` prompt/action to the existing AI prompt map, extend task folders with `events.md`, and expose richer work-item summaries so separate pages can render daily PDCA and all-item status cards without mixing concerns.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS/JavaScript, local Markdown vault files, project-local agent skill files.

---

## Current Baseline

The app already has:

- A Python stdlib HTTP server in `app/backend/server.py`.
- A `WorkbenchApp` workflow layer in `app/backend/app_state.py`.
- Markdown vault storage in `app/backend/storage.py`.
- Static frontend files in `app/frontend/`.
- Editable task detail page in `app/frontend/detail.html` and `app/frontend/detail.js`.
- Task folders with `task.md`, `context.md`, `ai-notes.md`, and `assets/`.
- Agent context rendering through `/api/agent-context`.

This plan keeps those boundaries. It does not add a JavaScript build step, a database, drag-and-drop, account sync, or a real multi-agent Round Table implementation.

## File Structure

Create or modify these files:

```text
.agents/
  skills/
    pdca-gate/
      SKILL.md
app/
  backend/
    app_state.py
    server.py
    storage.py
  frontend/
    app.js
    detail.html
    detail.js
    index.html
    styles.css
    today.html
    today.js
  prompts/
    pdca_gate.md
tests/
  test_frontend_static.py
  test_project_skill.py
  test_server.py
  test_storage.py
```

Responsibilities:

- `.agents/skills/pdca-gate/SKILL.md`: portable project-local instructions for reviewing or generating PDCA content.
- `app/prompts/pdca_gate.md`: AI prompt used by the app when the user submits raw daily/event text for PDCA classification.
- `app/backend/app_state.py`: register `pdca_gate` as an AI action and expose work-item summaries.
- `app/backend/storage.py`: create/read/save `events.md`, render it into agent context, and generate summary dictionaries for cards.
- `app/backend/server.py`: add `/api/work-items` while preserving `/api/files` for compatibility.
- `app/frontend/today.html` and `today.js`: daily/time-scale PDCA entry page.
- `app/frontend/index.html` and `app.js`: all-items card board page.
- `app/frontend/detail.html` and `detail.js`: add editable `events.md`.
- `tests/*`: protect skill content, backend behavior, and required static frontend hooks.

## Task 1: Add Project-Local PDCA Gate Skill

**Files:**
- Create: `.agents/skills/pdca-gate/SKILL.md`
- Create: `tests/test_project_skill.py`

- [ ] **Step 1: Write the failing skill-content test**

Create `tests/test_project_skill.py`:

```python
import unittest
from pathlib import Path


class ProjectSkillTests(unittest.TestCase):
    def test_pdca_gate_skill_defines_review_contract(self):
        content = Path(".agents/skills/pdca-gate/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: pdca-gate", content)
        self.assertIn("true_do", content)
        self.assertIn("candidate_do", content)
        self.assertIn("not_do", content)
        self.assertIn("bias_or_judgment", content)
        self.assertIn("evidence_needed", content)
        self.assertIn("Plan", content)
        self.assertIn("Do", content)
        self.assertIn("Check", content)
        self.assertIn("Act", content)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_project_skill -v
```

Expected: FAIL with `FileNotFoundError` for `.agents/skills/pdca-gate/SKILL.md`.

- [ ] **Step 3: Create the skill**

Create `.agents/skills/pdca-gate/SKILL.md`:

```markdown
---
name: pdca-gate
description: Review raw work notes, daily plans, and task events against PDCA. Classify Plan/Do/Check/Act, detect whether Do entries are concrete actions or personal judgments, and produce repair suggestions.
---

# PDCA Gate

Use this skill when the user asks to review, clean, classify, or generate PDCA content for daily work, weekly work, task events, or project progress notes.

## Core Contract

Treat PDCA as an evidence discipline, not a writing format.

- `Plan`: an intended outcome, constraint, hypothesis, priority, or next action before execution.
- `Do`: a concrete action already performed by a specific actor on a specific object at a specific time or in a specific session.
- `Check`: an observation, measurement, comparison, result, feedback, or evidence after doing.
- `Act`: an adjustment, standardization, escalation, decision, or next-cycle change based on Check.

## Do Classification

Classify every claimed Do as one of:

- `true_do`: a concrete action happened and the statement includes enough object/result detail to verify it.
- `candidate_do`: an action probably happened, but time, object, result, or evidence is missing.
- `not_do`: the statement is a belief, interpretation, emotion, preference, plan, or conclusion rather than an action.

## Bias And Evidence Flags

Flag these issues when present:

- `bias_or_judgment`: the sentence asserts a cause, motive, quality, priority, or blame without evidence.
- `evidence_needed`: the sentence needs a number, artifact, link, screenshot, decision record, query, message, or file reference.
- `scope_unclear`: the task, object, owner, or time window is ambiguous.
- `next_action_missing`: the note cannot produce a concrete next action.

## Review Output

When reviewing user input, output:

```markdown
## PDCA 分类

| 原句 | 分类 | Do 级别 | 问题标记 | 理由 |
| --- | --- | --- | --- | --- |

## 需要改写的 Do

- 原句：
- 问题：
- 更好的写法：
- 需要补充的证据：

## 可执行下一步

- 下一步动作：
- 需要的上下文：
- 可验证产出物：
```

## Generation Rules

- Prefer concrete verbs: sent, opened, compared, wrote, tested, asked, changed, saved, reviewed.
- Avoid pretending judgments are actions.
- Keep personal feelings only as context, not as Do.
- If evidence is missing, ask for the smallest useful artifact.
- Keep the user moving: every review should end with one concrete next action.
```

- [ ] **Step 4: Run the test and verify it passes**

Run:

```bash
python3 -m unittest tests.test_project_skill -v
```

Expected: PASS.

## Task 2: Add PDCA Gate Prompt Action

**Files:**
- Create: `app/prompts/pdca_gate.md`
- Modify: `app/backend/app_state.py`
- Modify: `tests/test_ai.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write the failing prompt-render test**

Append this test to `AITests` in `tests/test_ai.py`:

```python
    def test_pdca_gate_prompt_replaces_input_marker(self):
        prompt = render_prompt(Path("app/prompts/pdca_gate.md"), "今天我觉得推进慢，因为对方不配合")
        self.assertIn("今天我觉得推进慢，因为对方不配合", prompt)
        self.assertNotIn("{{input}}", prompt)
        self.assertIn("true_do", prompt)
        self.assertIn("bias_or_judgment", prompt)
```

- [ ] **Step 2: Run the prompt test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_ai.AITests.test_pdca_gate_prompt_replaces_input_marker -v
```

Expected: FAIL with `FileNotFoundError` for `app/prompts/pdca_gate.md`.

- [ ] **Step 3: Create the prompt template**

Create `app/prompts/pdca_gate.md`:

```markdown
你是一个严格但务实的 PDCA Gate Reviewer。请审查下面的工作输入。

你的目标不是润色，而是判断输入是否符合 PDCA，尤其要判断用户声称的 Do 是否真的是已经发生的具体行动。

## 判断标准

- Plan：计划、目标、假设、约束、优先级、准备做的下一步。
- Do：已经发生的具体行动。必须能回答：谁，在什么时候，对什么对象，做了什么，留下了什么可检查结果。
- Check：观察、数据、反馈、对比、验证结果。
- Act：基于 Check 做出的调整、标准化、升级、暂停、继续或下一轮计划。

## Do 级别

- true_do：确实是行动，且对象、动作、结果基本可验证。
- candidate_do：像行动，但缺少时间、对象、结果或证据。
- not_do：不是行动，而是判断、情绪、偏见、计划、解释或结论。

## 问题标记

- bias_or_judgment：缺少证据的个人判断、归因、评价或偏见。
- evidence_needed：需要补充链接、文件、截图、数据、消息、会议记录、查询结果或产出物。
- scope_unclear：对象、范围、责任人或时间窗口不清楚。
- next_action_missing：无法推出下一步行动。

## 输出格式

请严格输出：

### PDCA 分类表

| 原句 | 分类 | Do 级别 | 问题标记 | 理由 |
| --- | --- | --- | --- | --- |

### 需要改写的 Do

- 原句：
- 问题：
- 更好的写法：
- 需要补充的证据：

### 下一步

- 下一步动作：
- 需要的上下文：
- 可验证产出物：

原始输入：
{{input}}
```

- [ ] **Step 4: Register the action**

In `app/backend/app_state.py`, change `PROMPT_MAP` to:

```python
PROMPT_MAP = {
    "idea_critique": Path("app/prompts/idea_critique.md"),
    "structure_capture": Path("app/prompts/structure_capture.md"),
    "daily_review": Path("app/prompts/daily_review.md"),
    "pdca_gate": Path("app/prompts/pdca_gate.md"),
}
```

- [ ] **Step 5: Add the app workflow test**

Append this test to `WorkbenchAppTests` in `tests/test_storage.py`:

```python
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
```

- [ ] **Step 6: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_ai tests.test_storage -v
```

Expected: PASS.

## Task 3: Add Events File To Task Folders And Agent Context

**Files:**
- Modify: `app/backend/storage.py`
- Modify: `app/backend/server.py`
- Modify: `tests/test_storage.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing storage tests for events**

Add these assertions to `StorageTests.test_save_capture_writes_task_folder_to_inbox` in `tests/test_storage.py`:

```python
            self.assertTrue((folder / "events.md").exists())
            self.assertIn("# Events", (folder / "events.md").read_text(encoding="utf-8"))
```

Add this assertion to `StorageTests.test_read_work_item_returns_editable_task_folder_content`:

```python
            self.assertEqual(item["events"], "# Events\n\n")
```

Add this assertion to `StorageTests.test_save_work_item_updates_editable_markdown_files` after the save call:

```python
            self.assertEqual((folder / "events.md").read_text(encoding="utf-8"), "# Events\n\n- did one thing")
```

Change that save call to:

```python
            storage.save_work_item(
                folder,
                task="更新后的任务正文",
                context="更新后的上下文",
                ai_notes="更新后的 AI notes",
                events="# Events\n\n- did one thing",
            )
```

Add this assertion to `StorageTests.test_render_agent_context_includes_task_files_and_assets`:

```python
            self.assertIn("## events.md", context)
```

- [ ] **Step 2: Update server test payload for events**

In `tests/test_server.py`, change the work-item save payload to:

```python
                    {
                        "path": str(folder),
                        "task": "更新后的任务",
                        "context": "上下文资料",
                        "ai_notes": "AI 记录",
                        "events": "# Events\n\n- 发送了复盘草稿",
                    },
```

Add this assertion after reading agent context:

```python
                self.assertIn("发送了复盘草稿", context["context"])
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_storage tests.test_server -v
```

Expected: FAIL because `events.md` is not created/read/saved/rendered yet.

- [ ] **Step 4: Implement events in storage**

In `app/backend/storage.py`, update `save_capture` to write `events.md`:

```python
        (folder / "events.md").write_text("# Events\n\n", encoding="utf-8")
```

In `read_work_item`, add the events field for folder items:

```python
                "events": self._read_optional_text(item_path / "events.md"),
```

In the legacy-file branch of `read_work_item`, add:

```python
            "events": "",
```

Change `save_work_item` signature to:

```python
    def save_work_item(self, path: Path | str, task: str, context: str, ai_notes: str, events: str = "") -> None:
```

Inside the folder branch of `save_work_item`, add:

```python
            (item_path / "events.md").write_text(events, encoding="utf-8")
```

In `render_agent_context`, add this section between `ai-notes.md` and `assets`:

```python
## events.md

{item["events"]}
```

- [ ] **Step 5: Pass events through app and server**

In `app/backend/app_state.py`, change `save_work_item` to:

```python
    def save_work_item(self, path: str, task: str, context: str, ai_notes: str, events: str = "") -> None:
        self.storage.save_work_item(path, task=task, context=context, ai_notes=ai_notes, events=events)
```

In `app/backend/server.py`, change the `/api/work-item` save call to:

```python
            self.app_state.save_work_item(
                path=payload.get("path", ""),
                task=payload.get("task", ""),
                context=payload.get("context", ""),
                ai_notes=payload.get("ai_notes", ""),
                events=payload.get("events", ""),
            )
```

- [ ] **Step 6: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_storage tests.test_server -v
```

Expected: PASS.

## Task 4: Add Work-Item Summary API

**Files:**
- Modify: `app/backend/storage.py`
- Modify: `app/backend/app_state.py`
- Modify: `app/backend/server.py`
- Modify: `tests/test_storage.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing storage summary test**

Add this test to `StorageTests` in `tests/test_storage.py`:

```python
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
```

- [ ] **Step 2: Write failing server summary test**

Add this request to `ServerRouteTests.test_work_item_routes_read_save_and_render_agent_context` after `base_url` is created:

```python
                summaries = self._get_json(f"{base_url}/api/work-items")
                self.assertEqual(len(summaries["items"]), 1)
                self.assertEqual(summaries["items"][0]["title"], "炉温跳变")
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_storage tests.test_server -v
```

Expected: FAIL because `list_work_item_summaries` and `/api/work-items` do not exist.

- [ ] **Step 4: Implement summary extraction**

Add these methods to `VaultStorage` in `app/backend/storage.py`:

```python
    def list_work_item_summaries(self) -> list[dict[str, Any]]:
        summaries = []
        for path in self.list_work_items():
            item = self.read_work_item(path)
            summaries.append(
                {
                    "path": item["path"],
                    "title": item["title"],
                    "status": item["status"],
                    "created": self._created_from_path(Path(item["path"])),
                    "blocker": self._extract_section_first_line(item["task"], "当前卡点"),
                    "basis": self._extract_section_first_line(item["task"], "已有基础")
                    or self._first_non_empty_line(item["context"]),
                    "last_event": self._last_event_line(item.get("events", "")),
                }
            )
        return summaries

    def _created_from_path(self, path: Path) -> str:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})-", path.stem if path.is_file() else path.name)
        return match.group(1) if match else ""

    def _extract_section_first_line(self, markdown: str, heading: str) -> str:
        lines = markdown.splitlines()
        inside = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                inside = stripped == f"## {heading}"
                continue
            if inside and stripped and not stripped.startswith("#"):
                return stripped.removeprefix("- ").strip()
        return ""

    def _first_non_empty_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped.removeprefix("- ").strip()
        return ""

    def _last_event_line(self, text: str) -> str:
        events = [
            line.strip().removeprefix("- ").strip()
            for line in text.splitlines()
            if line.strip().startswith("- ")
        ]
        return events[-1] if events else ""
```

- [ ] **Step 5: Expose summaries through app and server**

In `app/backend/app_state.py`, add:

```python
    def list_work_item_summaries(self) -> list[dict]:
        return self.storage.list_work_item_summaries()
```

In `app/backend/server.py`, add this route before `/api/files`:

```python
        if parsed.path == "/api/work-items":
            self._send_json({"items": self.app_state.list_work_item_summaries()})
            return
```

- [ ] **Step 6: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_storage tests.test_server -v
```

Expected: PASS.

## Task 5: Add Editable Events To Detail Page

**Files:**
- Modify: `app/frontend/detail.html`
- Modify: `app/frontend/detail.js`
- Create: `tests/test_frontend_static.py`

- [ ] **Step 1: Write failing static frontend test**

Create `tests/test_frontend_static.py`:

```python
import unittest
from pathlib import Path


class FrontendStaticTests(unittest.TestCase):
    def test_detail_page_has_events_editor(self):
        html = Path("app/frontend/detail.html").read_text(encoding="utf-8")
        js = Path("app/frontend/detail.js").read_text(encoding="utf-8")
        self.assertIn("eventsEditor", html)
        self.assertIn("#eventsEditor", js)
        self.assertIn("events: eventsEditor.value", js)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_frontend_static.FrontendStaticTests.test_detail_page_has_events_editor -v
```

Expected: FAIL because the events editor is absent.

- [ ] **Step 3: Add events editor markup**

In `app/frontend/detail.html`, add this label after the AI notes editor:

```html
        <label>
          事件记录
          <textarea id="eventsEditor" rows="12"></textarea>
        </label>
```

- [ ] **Step 4: Wire events in detail JavaScript**

In `app/frontend/detail.js`, add:

```javascript
const eventsEditor = document.querySelector("#eventsEditor");
```

In `loadWorkItem`, add:

```javascript
  eventsEditor.value = item.events || "";
```

In the save payload, add:

```javascript
      events: eventsEditor.value
```

- [ ] **Step 5: Run frontend static test**

Run:

```bash
python3 -m unittest tests.test_frontend_static -v
```

Expected: PASS.

## Task 6: Split All-Items Board From Daily PDCA Page

**Files:**
- Modify: `app/frontend/index.html`
- Modify: `app/frontend/app.js`
- Create: `app/frontend/today.html`
- Create: `app/frontend/today.js`
- Modify: `app/frontend/styles.css`
- Modify: `tests/test_frontend_static.py`

- [ ] **Step 1: Add failing static tests for two pages**

Append these tests to `FrontendStaticTests`:

```python
    def test_index_is_all_items_board(self):
        html = Path("app/frontend/index.html").read_text(encoding="utf-8")
        js = Path("app/frontend/app.js").read_text(encoding="utf-8")
        self.assertIn("全部事项", html)
        self.assertIn("/today.html", html)
        self.assertIn("/api/work-items", js)
        self.assertIn("board-card-blocker", js)
        self.assertNotIn("rawInput", html)

    def test_today_page_has_pdca_entry(self):
        html = Path("app/frontend/today.html").read_text(encoding="utf-8")
        js = Path("app/frontend/today.js").read_text(encoding="utf-8")
        self.assertIn("今日 PDCA", html)
        self.assertIn("data-action=\"pdca_gate\"", html)
        self.assertIn("/api/capture", js)
        self.assertIn("today-list", html)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_frontend_static -v
```

Expected: FAIL because `today.html` and `today.js` do not exist and `index.html` still contains capture inputs.

- [ ] **Step 3: Replace index with all-items board shell**

Replace `app/frontend/index.html` with:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>全部事项 - Personal Workbench</title>
    <link rel="stylesheet" href="/styles.css?v=pdca-pages">
  </head>
  <body>
    <main class="page-shell">
      <header class="topbar">
        <div>
          <h1>全部事项</h1>
          <p>按状态查看卡点、已有基础和最近事件。</p>
        </div>
        <nav class="topbar-actions" aria-label="页面导航">
          <a class="nav-button" href="/today.html">今日 PDCA</a>
          <button id="refreshItems" type="button">刷新</button>
        </nav>
      </header>
      <section class="board-panel is-full">
        <div class="board-grid" id="boardGrid"></div>
      </section>
    </main>
    <script src="/app.js?v=pdca-pages"></script>
  </body>
</html>
```

- [ ] **Step 4: Replace app.js with summary-board rendering**

Replace `app/frontend/app.js` with:

```javascript
const boardGrid = document.querySelector("#boardGrid");
const refreshItems = document.querySelector("#refreshItems");

const boardStatuses = ["inbox", "active", "waiting", "done", "archive"];
const statusLabels = {
  inbox: "收件箱",
  active: "推进中",
  waiting: "等待",
  done: "完成",
  archive: "归档"
};

function detailUrl(path) {
  return `/detail.html?path=${encodeURIComponent(path)}`;
}

function emptyText(value, fallback) {
  return value && value.trim() ? value : fallback;
}

async function refreshBoard() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  renderBoard(payload.items || []);
}

function renderBoard(items) {
  const grouped = Object.fromEntries(boardStatuses.map((status) => [status, []]));
  for (const item of items) {
    const status = boardStatuses.includes(item.status) ? item.status : "inbox";
    grouped[status].push(item);
  }

  boardGrid.innerHTML = "";
  for (const status of boardStatuses) {
    const column = document.createElement("section");
    column.className = "board-column";

    const heading = document.createElement("div");
    heading.className = "board-column-header";
    heading.innerHTML = `<span>${statusLabels[status]}</span><strong>${grouped[status].length}</strong>`;
    column.appendChild(heading);

    const cards = document.createElement("div");
    cards.className = "board-cards";
    for (const item of grouped[status]) {
      const card = document.createElement("a");
      card.className = "board-card";
      card.href = detailUrl(item.path);

      const title = document.createElement("h2");
      title.textContent = item.title;

      const blocker = document.createElement("p");
      blocker.className = "board-card-blocker";
      blocker.textContent = `卡点：${emptyText(item.blocker, "未填写")}`;

      const basis = document.createElement("p");
      basis.textContent = `基础：${emptyText(item.basis, "未填写")}`;

      const event = document.createElement("p");
      event.textContent = `最近：${emptyText(item.last_event, "暂无事件")}`;

      card.append(title, blocker, basis, event);
      cards.appendChild(card);
    }
    column.appendChild(cards);
    boardGrid.appendChild(column);
  }
}

refreshItems.addEventListener("click", refreshBoard);
refreshBoard();
```

- [ ] **Step 5: Create today page**

Create `app/frontend/today.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>今日 PDCA - Personal Workbench</title>
    <link rel="stylesheet" href="/styles.css?v=pdca-pages">
  </head>
  <body>
    <main class="page-shell">
      <header class="topbar">
        <div>
          <h1>今日 PDCA</h1>
          <p>把当天和本周事项转成可检查的 Plan、Do、Check、Act。</p>
        </div>
        <nav class="topbar-actions" aria-label="页面导航">
          <a class="nav-button" href="/">全部事项</a>
          <button id="refreshToday" type="button">刷新</button>
        </nav>
      </header>
      <section class="today-grid">
        <section class="panel">
          <h2>今日/本周事项</h2>
          <div id="todayList" class="today-list"></div>
        </section>
        <section class="panel">
          <label>
            标题
            <input id="titleInput" type="text" value="今日 PDCA 输入">
          </label>
          <label>
            原始输入
            <textarea id="rawInput" rows="14" placeholder="写下今天计划、已经做过的动作、观察到的结果、需要调整的下一步"></textarea>
          </label>
          <div class="actions">
            <button data-action="pdca_gate" type="button">PDCA Gate</button>
            <button data-action="daily_review" type="button">生成日复盘</button>
            <button data-action="structure_capture" type="button">整理成卡片</button>
          </div>
          <div id="statusText" class="status-text">等待输入。</div>
          <label>
            AI 输出
            <textarea id="aiOutput" rows="16"></textarea>
          </label>
          <div class="saved-path" id="savedPath"></div>
        </section>
      </section>
    </main>
    <script src="/today.js?v=pdca-pages"></script>
  </body>
</html>
```

- [ ] **Step 6: Create today JavaScript**

Create `app/frontend/today.js`:

```javascript
const titleInput = document.querySelector("#titleInput");
const rawInput = document.querySelector("#rawInput");
const aiOutput = document.querySelector("#aiOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const todayList = document.querySelector("#todayList");
const refreshToday = document.querySelector("#refreshToday");

function detailUrl(path) {
  return `/detail.html?path=${encodeURIComponent(path)}`;
}

function isThisWeek(dateText) {
  if (!dateText) {
    return false;
  }
  const itemDate = new Date(`${dateText}T00:00:00`);
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay() + 1);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 7);
  return itemDate >= start && itemDate < end;
}

async function refreshTodayList() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  const items = (payload.items || []).filter((item) => item.status !== "archive" && isThisWeek(item.created));
  renderTodayList(items);
}

function renderTodayList(items) {
  todayList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "本周还没有事项。";
    todayList.appendChild(empty);
    return;
  }
  for (const item of items) {
    const link = document.createElement("a");
    link.className = "today-item";
    link.href = detailUrl(item.path);
    link.innerHTML = `<strong>${item.title}</strong><span>${item.status} · ${item.created || "无日期"}</span>`;
    todayList.appendChild(link);
  }
}

async function runAction(action) {
  const rawText = rawInput.value.trim();
  if (!rawText) {
    statusText.textContent = "请先输入内容。";
    return;
  }
  statusText.textContent = "AI 正在处理。";
  savedPath.textContent = "";
  const response = await fetch("/api/capture", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      title: titleInput.value.trim() || "今日 PDCA 输入",
      kind: "task",
      raw_text: rawText,
      action
    })
  });
  if (!response.ok) {
    statusText.textContent = `请求失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  aiOutput.value = payload.ai_output;
  savedPath.textContent = `已保存：${payload.path}`;
  statusText.textContent = "完成。";
  await refreshTodayList();
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

refreshToday.addEventListener("click", refreshTodayList);
refreshTodayList();
```

- [ ] **Step 7: Add page layout styles**

Append these styles to `app/frontend/styles.css`:

```css
.page-shell {
  min-height: 100vh;
  background: #eef2f6;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid #d9e2ec;
  background: #ffffff;
  padding: 16px 20px;
}

.topbar p {
  margin: 6px 0 0;
  color: #627386;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-button {
  border: 1px solid #9aa6b2;
  border-radius: 6px;
  background: #ffffff;
  color: #1f2933;
  padding: 9px 12px;
  text-decoration: none;
}

.board-panel.is-full {
  padding: 18px;
}

.today-grid {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(420px, 1fr);
  gap: 1px;
  min-height: calc(100vh - 76px);
  background: #c8d0d8;
}

.today-list {
  display: grid;
  gap: 8px;
}

.today-item {
  display: grid;
  gap: 6px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  background: #ffffff;
  color: inherit;
  padding: 10px;
  text-decoration: none;
}

.today-item span,
.empty-state {
  color: #627386;
  font-size: 13px;
}

@media (max-width: 960px) {
  .topbar,
  .today-grid {
    grid-template-columns: 1fr;
  }

  .topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .topbar-actions {
    flex-wrap: wrap;
  }
}
```

- [ ] **Step 8: Run frontend static tests**

Run:

```bash
python3 -m unittest tests.test_frontend_static -v
```

Expected: PASS.

## Task 7: Full Verification

**Files:**
- No planned file changes.

- [ ] **Step 1: Run the complete Python test suite**

Run:

```bash
python3 -m unittest discover -v
```

Expected: PASS.

- [ ] **Step 2: Start the local server**

Run:

```bash
python3 -m app.backend.server --provider fake --port 8765
```

Expected: server prints:

```text
Workbench running at http://127.0.0.1:8765
AI provider: fake
```

- [ ] **Step 3: Browser smoke test**

Open:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/today.html
```

Expected:

- `/` shows only the all-items board and navigation to `今日 PDCA`.
- `/today.html` shows weekly items, PDCA input, and a `PDCA Gate` action.
- Submitting text through `PDCA Gate` saves a task folder and shows AI output.
- Opening the saved task detail page shows editable `task.md`, `context.md`, `ai-notes.md`, and `events.md`.
- Agent context includes `task.md`, `context.md`, `ai-notes.md`, `events.md`, and asset names.

## Self-Review

Spec coverage:

- Project-local `pdca-gate` skill: Task 1.
- App-level PDCA Gate prompt/action: Task 2.
- Task-folder event context: Task 3.
- All-items card board with blocker and basis fields: Task 4 and Task 6.
- Daily/time-scale PDCA entry page: Task 6.
- Agent-readable task context including events: Task 3.
- No Round Table implementation: explicitly out of scope for this plan.

Placeholder scan:

- No placeholder markers.
- No incomplete code snippets.
- No task relies on a path or function that is unnamed.

Type and interface consistency:

- `events` is optional on save calls so old callers keep working.
- `/api/files` remains available; new pages use `/api/work-items`.
- Work-item summary dictionaries use stable keys: `path`, `title`, `status`, `created`, `blocker`, `basis`, and `last_event`.
