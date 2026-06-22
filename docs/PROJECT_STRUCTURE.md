# Project Structure

## Runtime

```text
app/backend/server.py
```

Python standard-library HTTP server. Serves static files from `app/frontend/` and JSON APIs under `/api/*`.

```text
app/backend/app_state.py
```

Workflow layer. Registers prompt actions and delegates storage/AI provider work.

```text
app/backend/storage.py
```

Markdown vault persistence. Creates task folders, reads/saves editable Markdown files, generates card summaries, and renders agent context.

```text
app/backend/ai.py
```

AI provider abstraction. `FakeAIProvider` is the default safe provider for setup/testing. `HermesCLIProvider` calls a local Hermes CLI.

```text
app/backend/models.py
app/backend/markdown.py
app/backend/prompts.py
```

Domain dataclasses, Markdown rendering helpers, and prompt template rendering.

## Frontend

```text
app/frontend/index.html
app/frontend/app.js
```

All-items board. Calls `/api/work-items` and renders status columns.

```text
app/frontend/today.html
app/frontend/today.js
```

Daily PDCA page. Shows this week's items and submits capture actions such as `pdca_gate`.

```text
app/frontend/detail.html
app/frontend/detail.js
```

Task detail editor. Edits `task.md`, `context.md`, `ai-notes.md`, and `events.md`. Can request `/api/agent-context`.

```text
app/frontend/styles.css
```

Shared styling for board, daily page, and detail page.

## Prompts And Skills

```text
app/prompts/
```

Prompt templates used by the app's AI actions.

```text
.agents/skills/pdca-gate/SKILL.md
```

Project-local skill for agent-side PDCA review.

## Vault

```text
data-issue-vault/
```

Local Markdown vault. Only status folders and `.gitkeep` files should be tracked.

Task folder shape:

```text
data-issue-vault/inbox/2026-06-22-example-task/
  task.md
  context.md
  ai-notes.md
  events.md
  assets/
```

## Tests

```text
tests/test_storage.py
```

Storage shape, task folder behavior, summaries, and agent context.

```text
tests/test_server.py
```

HTTP route behavior.

```text
tests/test_frontend_static.py
```

Static frontend contracts for required pages and DOM hooks.

```text
tests/test_ai.py
tests/test_agent_modes.py
tests/test_markdown.py
tests/test_models.py
tests/test_project_skill.py
```

Prompt rendering, agent mode plans, Markdown rendering, model validation, and project skill checks.
