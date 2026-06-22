## Guidance Expectations

- The user is still learning Codex concepts such as AGENTS.md, skills, MCP, plugins, and agent workflows.
- If the user proposes an inefficient, fragile, or conceptually wrong approach, state that directly and briefly.
- Do not merely accommodate the proposed approach when there is a clearly better workflow.
- Explain the reason in one or two sentences, then suggest the practical alternative.
- Favor actionable next steps over broad tutorials.

## Project Purpose

This repository is a local-first PDCA workbench. It captures daily work notes, task context, event logs, and AI-generated reviews into Markdown task folders so the project can later be continued by different agents or weaker local/open-source models.

The app intentionally uses a small stack:

- Python standard library backend.
- Static HTML/CSS/JavaScript frontend.
- Markdown files as the persistence layer.
- No database, package manager, bundler, or external service required for the default fake-provider mode.

## Data Boundary

- Do not commit real user work content from `data-issue-vault/`.
- Only commit the vault folder skeleton and `.gitkeep` files.
- The `.gitignore` rule for `data-issue-vault/**/*` is intentional.
- Generated smoke-test task folders must be removed before committing unless the user explicitly asks to keep them.

## Development Commands

Run the local app:

```bash
python3 -m app.backend.server --provider fake --port 8765
```

Run the full test suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The default `python3 -m unittest discover -v` may find zero tests because this repo keeps tests in the `tests/` directory without package markers. Use the explicit command above.

## Current Product Shape

- `/` is the all-items board.
- `/today.html` is the daily/time-scale PDCA entry.
- `/detail.html?path=...` edits one task folder.
- `/api/work-items` returns card summaries.
- `/api/capture` runs a prompt action and saves a task folder.
- `/api/agent-context` renders `task.md`, `context.md`, `ai-notes.md`, `events.md`, and asset names for an agent.

## Agent Workflow Rules

- Keep changes small and testable.
- Prefer editing existing simple modules over adding frameworks.
- When adding a new page, add a static frontend test in `tests/test_frontend_static.py`.
- When changing storage shape, add tests in `tests/test_storage.py` and preserve legacy single-Markdown-file behavior.
- When changing HTTP behavior, add tests in `tests/test_server.py`.
- If a local server test binds a port and the sandbox blocks it, rerun with the required permission rather than skipping it.

## Weak Model Handoff

For weaker models, read these files before editing code:

1. `README.md`
2. `docs/PROJECT_STRUCTURE.md`
3. `docs/WEAK_MODEL_CONSTRAINTS.md`
4. `docs/NEXT_PLAN.md`
5. `docs/superpowers/plans/2026-06-22-pdca-gate-and-pages.md`

Do not infer architecture from memory. Inspect the files first, then make the smallest change that satisfies the requested task.
