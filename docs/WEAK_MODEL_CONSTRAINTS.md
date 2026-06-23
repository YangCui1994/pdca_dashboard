# Weak Model Constraints

This file is for agents using weaker models such as DeepSeek, GLM, Minimax, or small local models.

## Operating Rules

1. Read files before changing them.
2. Change one small behavior at a time.
3. Add or update a test before changing backend behavior.
4. Do not add dependencies unless the user explicitly approves.
5. Do not introduce a database, Node build step, React/Vue app, or package manager.
6. Keep the app runnable with `python3 -m app.backend.server --provider fake --port 8765`.
7. Do not sync real `data-issue-vault/` content to GitHub.
8. The main future task for weak models is AI provider wiring and AI output handling, not broad code structure changes.

## Current Weak-Model Scope

The app structure is intentionally stable. Do not refactor the backend/frontend layout, replace the Markdown vault, add a build step, or redesign routing unless the user explicitly asks for that specific change.

Expected weak-model work:

- Connect or adjust an AI provider behind `app/backend/ai.py`; prefer Hermes Agent one-shot mode (`hermes -z`) when skills/tools are required.
- Keep `/api/document-helper` as a draft-only flow: AI returns Markdown, the user reviews it, then the user saves it.
- Improve prompt text or provider error messages when needed.
- Add focused tests for provider selection, route behavior, and draft output.

Out of scope unless explicitly requested:

- Replacing the Python standard-library server.
- Adding a database or syncing real vault contents.
- Moving to React/Vue or adding a Node build pipeline.
- Simulating multi-agent Round Table behavior with one weak model.

## Safe Test Command

Always use:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Do not rely on:

```bash
python3 -m unittest discover -v
```

It may report zero tests.

## Editing Strategy

For backend changes:

- Storage shape changes go in `app/backend/storage.py`.
- Workflow action changes go in `app/backend/app_state.py`.
- HTTP route changes go in `app/backend/server.py`.
- Prompt files go in `app/prompts/`.
- Status moves use `/api/work-item-status`.
- Appending accepted PDCA analysis to a task uses `/api/work-item-event`.
- Agent context readiness uses `/api/context-readiness`.
- Do not hand-edit the PDCA input log format unless tests are updated first.

For frontend changes:

- All-items board: `app/frontend/index.html` and `app/frontend/app.js`.
- Daily PDCA page: `app/frontend/today.html` and `app/frontend/today.js`.
- Task document pages: `app/frontend/task.html`, `context.html`, `events.html`, `ai-notes.html`, and `document.js`.
- Shared visual rules: `app/frontend/styles.css`.

For agent behavior:

- App prompt behavior belongs in `app/prompts/`.
- Agent instruction behavior belongs in `.agents/skills/`.
- Project-wide agent rules belong in `AGENTS.md`.

## PDCA Gate Standard

When reviewing a user note, do not treat every sentence as a valid Do.

A true Do must say, or strongly imply:

- actor
- time/session
- object
- action
- checkable result or evidence

Use these labels:

- `true_do`
- `candidate_do`
- `not_do`

Flag unsupported judgments with:

- `bias_or_judgment`
- `evidence_needed`
- `scope_unclear`
- `next_action_missing`

## Common Mistakes To Avoid

- Do not overwrite `data-issue-vault` with sample data.
- Do not display `data-issue-vault/reviews/pdca-input-log.md` on the dashboard; it stores private initial thoughts.
- Do not remove legacy single Markdown file support from storage.
- Do not rename API fields casually; frontend tests depend on them.
- Do not treat design demos as production code.
- Do not claim tests pass without running the explicit command above.
- Do not implement Round Table mode yet; stop at interfaces and planning unless the user asks for it.
