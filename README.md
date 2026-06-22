# PDCA Dashboard

Local-first Markdown workbench for daily PDCA, task context, and agent handoff.

The current app is intentionally small: a Python standard-library HTTP server, static frontend files, and a Markdown vault. It is designed to run on another computer without installing a database, Node packages, or a frontend build tool.

## Quick Start

```bash
python3 -m app.backend.server --provider fake --port 8765
```

Open:

- `http://127.0.0.1:8765/` for the all-items board.
- `http://127.0.0.1:8765/today.html` for the daily PDCA entry.

Use `--provider fake` when setting up a new machine or when the available model is weak/unreliable. It keeps the UI and storage path testable without external AI.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected result at the time of this handoff: 30 tests passing.

## What Is Implemented

- Capture raw input and save it as a Markdown task folder.
- Run prompt actions through a provider abstraction.
- `pdca_gate` prompt for classifying Plan/Do/Check/Act and detecting judgment disguised as Do.
- Editable task detail page with:
  - `task.md`
  - `context.md`
  - `ai-notes.md`
  - `events.md`
  - `assets/`
- All-items card board grouped by vault status.
- Daily PDCA page for today/week-scale input.
- Agent context rendering for downstream agents.
- Project-local `pdca-gate` skill in `.agents/skills/pdca-gate/SKILL.md`.

## Repository Data Policy

Real user work data is not meant to sync to GitHub.

The vault skeleton is tracked:

```text
data-issue-vault/
  inbox/.gitkeep
  active/.gitkeep
  waiting/.gitkeep
  done/.gitkeep
  archive/.gitkeep
```

Actual notes under `data-issue-vault/` are ignored by `.gitignore`.

## Important Docs

- `AGENTS.md`: project instructions for coding agents.
- `CLAUDE.md`: Claude-compatible entry point.
- `docs/PROJECT_STRUCTURE.md`: file responsibilities.
- `docs/WEAK_MODEL_CONSTRAINTS.md`: rules for DeepSeek/GLM/other weaker models.
- `docs/NEXT_PLAN.md`: next implementation plan and stopping points.
- `docs/superpowers/plans/`: detailed implementation plans already executed or ready for future work.

## Design References

`design-demos/` contains static HTML design explorations. They are reference assets, not the production app.
