# PDCA Workbench

Local-first PDCA workbench: daily capture, project tracking, wrap-up wizards, and AI-assisted review, persisted as local Markdown/JSON files. No database, no Node build step, no external service required for the default fake-provider mode.

## Quick Start

Requires Python 3.10+ and `pip install flet`. On Windows use `python` instead of `python3`.

```bash
python -m workbench.main                                   # web mode, demo data, port 8550
python -m workbench.main --ui desktop                      # desktop window
python -m workbench.main --host 0.0.0.0 --port 8550        # intranet deploy (no auth; LAN only)
python -m workbench.main --vault data-issue-vault/v2       # persist edits to the vault
python -m workbench.main --watch-dir some/inbox            # watch .md/.txt, auto-route (undoable)
```

Web mode is the default (company-intranet deployment: single writer, multiple viewers, no auth). Open `http://127.0.0.1:8550`.

Without `--vault` the app runs on a fully fictional demo workspace, so a new machine is testable offline.

## Features

- **Today hub**: resident smart capture bar (`!` plan / `#project` plan / plain idea), rollover bar with batch-undo, four-step wrap-up wizard, AI draft cards (adopt / edit-adopt / dismiss — drafts only, adopt writes).
- **Projects**: card home, then master-detail project page — editable meta, outline, action status blocks with click-to-cycle, stalled list with real day counts, activity heatmap.
- **AI concierge panel** (hidden by default, sidebar toggle): stage actions (今日计划建议 / Check 引导 / 本周复盘)， thinking-mode invocation (brainstorm / grill me / premortem / six hats), draft-card queue. All AI calls run off the UI thread.
- **File watcher**: drop `.md`/`.txt` files into a watched inbox; an AI route decision files them under a project (undoable).
- **Activity**: GitHub-style heatmap, meaningful events, long-stalled list.
- Ideas triage and read-only archive with restore.

UI style baseline: **entp-manual** (blue `#316BEE` family, Microsoft YaHei UI) — decision recorded 2026-09-16, crosswalk in `refs/SOURCES.md`.

## Tests

```bash
python -m unittest discover -s workbench/tests -p 'test_*.py'
```

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

Actual notes under `data-issue-vault/` are ignored by `.gitignore`. The prototype demo vault (`prototypes/ux-2026-09/demo_vault/`) is also local-only: it is regenerable via `python -m prototypes.uxbase.seed_demo` and may contain notes typed during prototype testing.

## Important Docs

- `docs/PROJECT_STRUCTURE.md`: file responsibilities of the workbench app.
- `docs/WORKBENCH_V2_USAGE.md`: usage, CLI flags, and vault migration.
- `docs/NEXT_PLAN.md`: next implementation plan and stopping points.
- `docs/plans/` and `docs/superpowers/plans/`: implementation plans already executed or ready for future work.
- `docs/ARCHIFY.md`, `docs/CODEGRAPH.md`, `docs/PONYTAIL.md`: third-party agent tools — install status and usage notes. Not part of the workbench runtime.
- `docs/architecture.html` + `docs/architecture-spec.json`: repo architecture diagram (produced by the Archify skill).

## Design References

- `prototypes/` contains five runnable Flet UX prototypes (TodayHub, keyboard inbox, review wizard, structure canvas, AI concierge) that were merged into `workbench/`. Reference assets; entry: `prototypes/ux-2026-09/README.md`.
- `refs/SOURCES.md` records downloaded reference material (URL, commit, access date). The `refs/entp-manual/` clone is local-only (gitignored); re-fetch it per that file on a new machine.

## History Note

This repo previously hosted a static-PDCA web app (`app/`, stdlib HTTP server + static frontend) and its `tests/` suite. Both were removed on 2026-09-16 when the repository history was reset for a clean GitHub start; the workbench app above is the sole runtime. The full old history is preserved on the local branch `backup/history-before-github-wipe` (not pushed).
