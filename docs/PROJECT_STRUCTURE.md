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
It also builds document-helper prompts for unsaved AI Markdown drafts.

```text
app/backend/storage.py
```

Markdown vault persistence. Creates task folders, reads/saves editable Markdown files, generates card summaries, and renders agent context.
It also owns status moves, event appends, PDCA input/review logs, and context readiness checks.

```text
app/backend/ai.py
```

AI provider abstraction. `FakeAIProvider` is the default safe provider for setup/testing. `HermesCLIProvider` calls local Hermes Agent with `hermes -z` and can preload model, provider, toolset, and skill options so the external agent can retain its tool/skill behavior.

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
Includes status/date/tag/blocker filters and status move actions.

```text
app/frontend/today.html
app/frontend/today.js
```

Daily PDCA page. Shows today and this week's items separately, captures Plan/Do/Check/Act inputs, writes PDCA input logs, generates periodic reviews, and can append accepted analysis to a selected task's `events.md`.

```text
app/frontend/detail.html
app/frontend/detail.js
```

Task document editor. The separate document pages edit `task.md`, `context.md`, `ai-notes.md`, and `events.md`. The task page can request `/api/agent-context`, copy/download the rendered context, and display `/api/context-readiness`.
Document pages show HTML rendered from Markdown first; the Markdown editor remains the source of truth.

```text
app/frontend/styles.css
```

Shared styling for board, daily page, and detail page.

## Prompts And Skills

```text
app/prompts/
```

Prompt templates used by the app's AI actions.

Important prompt files:

- `pdca_gate.md`: single PDCA entry review and Do classification.
- `pdca_periodic_review.md`: periodic review over `reviews/pdca-input-log.md`.
- Document-helper prompts are generated in `app/backend/app_state.py` so the route can include the current document and user-requested skills.

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

PDCA log/review files are local user data and should not be committed:

```text
data-issue-vault/reviews/
  pdca-input-log.md
  YYYY-MM-DD-HHMMSS-pdca-review.md
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
