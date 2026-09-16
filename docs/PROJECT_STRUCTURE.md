# Project Structure

The sole runtime is the **workbench v2 Flet app** (`workbench/`, UX-prototype merge landed 2026-09, web mode by default). It persists to the local vault (`data-issue-vault/`) as Markdown/JSON twin files; no database anywhere.

> The earlier static-PDCA web app (`app/` + `tests/`) was removed on 2026-09-16 when GitHub history was reset. Its full history lives on the local branch `backup/history-before-github-wipe`.

Entry point and CLI flags are documented in `docs/WORKBENCH_V2_USAGE.md`; UI style baseline lives in `refs/SOURCES.md`.

```text
workbench/main.py
```

Composition root and launcher: builds routes, consumes AI streaming events, opens the flow-diagram artifact, applies `--vault` / `--ui web|desktop` / `--host` / `--port` / `--watch-dir`. Carries no domain rules.

## Domain

```text
workbench/domain/models.py
workbench/domain/fixtures.py
```

Dataclasses for projects, outline nodes, actions, proposals, and activity; a fully fictional demo workspace used when no `--vault` is given.

## Runtime (AI)

```text
workbench/runtime/contracts.py
workbench/runtime/fake_runtime.py
workbench/runtime/openai_runtime.py
workbench/runtime/text_runtime.py
```

Runtime gateway contracts shared with the UI; an in-memory fake streaming deterministic events (zero IO, offline-testable); an OpenAI-compatible chat-completions SSE runtime (stdlib only); and a draft-text runtime that generates draft cards off the UI thread (`page.run_thread`).

## Services (domain logic, UI-free)

```text
workbench/services/workspace_service.py
workbench/services/capture_routing.py
workbench/services/wrapup.py
workbench/services/prompt_library.py
workbench/services/file_watcher.py
workbench/services/file_routing.py
workbench/services/flow_artifact.py
```

- `workspace_service`: in-memory workspace service, the only writer of formal workspace state; every mutation is an explicit, user-confirmed action.
- `capture_routing`: smart capture bar routing (`!` plan / `#project` plan / plain idea), pure functions.
- `wrapup`: four-step wrap-up wizard logic (check yesterday, Check guidance, disposition of unfinished items), UI-free pure functions.
- `prompt_library`: two-axis prompt registry — one markdown file per stage × thinking mode, home directory `workbench/prompts/`.
- `file_watcher` / `file_routing`: stdlib polling watcher (no watchdog dependency); new `.md`/`.txt` in the watched dir get routed to a project via a tolerant JSON contract (`prompts/stages/file_route.md`).
- `flow_artifact`: renders real workspace data into a self-contained offline HTML flow diagram.

## Storage

```text
workbench/storage/workspace_storage.py
```

Markdown/JSON twin-file persistence under the vault root (usually `data-issue-vault/v2/`).

## Components (reusable UI)

```text
workbench/components/navigation.py
workbench/components/ai_panel.py
workbench/components/concierge.py
workbench/components/feedback.py
workbench/components/wrapup_wizard.py
workbench/components/editable.py
workbench/components/heatmap.py
workbench/components/project_outline.py
```

- `navigation`: left main navigation (five-item contract) plus the "AI 助手" toggle; AI panel is hidden by default.
- `ai_panel`: right AI drawer — run review, stream events, confirm/reject proposals.
- `concierge`: draft-card console inside the AI panel — stage actions (今日计划建议 / Check 引导 / 本周复盘)， thinking-mode invocation, draft queue (adopt / edit-adopt / dismiss; drafts only, adopt writes).
- `feedback`: unified snackbar / undoable feedback / empty states (entp-manual palette).
- `wrapup_wizard`: the wrap-up wizard as a four-step AlertDialog with progress dots.
- `editable`: double-click-to-edit text; `heatmap`: GitHub-style activity heatmap; `project_outline`: vertical outline with connecting line.

## Views (pages)

```text
workbench/views/today.py
workbench/views/projects_home.py
workbench/views/project_overview.py
workbench/views/node_detail.py
workbench/views/activity.py
workbench/views/ideas.py
workbench/views/archive.py
```

- `today` (TodayHub): resident smart capture bar, rollover bar with batch-undo, wrap-up wizard entry, idea touch-once rows, AI draft cards.
- `projects_home` / `project_overview`: project cards, then master-detail — compact project cards on the left (stalled red mark), editable detail, outline, action status blocks, stalled list, heatmap on the right.
- `node_detail`: editable title/notes/resources with tags and relations.
- `activity`: heatmap + meaningful events of the day + long-stalled list.
- `ideas` / `archive`: idea triage by status; read-only archive with restore.

## Prompts, Fonts

```text
workbench/prompts/stages/      capture_critique.md day_check.md file_route.md plan_suggest.md weekly_review.md
workbench/prompts/thinking/    brainstorm.md grill_me.md premortem.md six_hats.md
workbench/fonts/NotoSansSC-VF.ttf
workbench/fonts/FONT_NOTES.md
```

## Agent-Side Skill

```text
.agents/skills/pdca-gate/SKILL.md
```

Project-local skill for agent-side PDCA review of raw work notes.

## Tests

```text
workbench/tests/
```

Run: `python -m unittest discover -s workbench/tests -p 'test_*.py'` (needs `pip install flet`).
Covers storage, workspace service, capture routing, wrap-up, prompt loading, watcher routing, runtimes (fake/openai), flow artifact, UI contract, and main composition.

## Prototypes (`prototypes/`)

Five runnable UX interaction prototypes (A TodayHub / B keyboard inbox / C review wizard / D structure canvas / E AI concierge) plus `uxbase/`, now a re-export shell so the prototypes keep running after the merge. Reference material only — not the production app. Entry: `prototypes/ux-2026-09/README.md`.

`prototypes/ux-2026-09/demo_vault/` is generated, regenerable demo data (`python -m prototypes.uxbase.seed_demo`) and gitignored — it may contain real notes typed during prototype testing.

## References (`refs/`)

```text
refs/SOURCES.md
```

Provenance list for downloaded reference material (URL, commit hash, access date). `refs/entp-manual/` is a local shallow clone of the entp-manual project (the v2 UI style baseline) and is **gitignored** — re-fetch it per `refs/SOURCES.md` on a new machine.

## Vault

```text
data-issue-vault/
```

Local vault. Only status folders and `.gitkeep` files are tracked; the workbench persists under `data-issue-vault/v2/` when `--vault` is passed.

## Generated Artifacts (not tracked)

`workbench/artifacts/visual-check/` and `docs/architecture.visual-check.*` are smoke-test screenshots/verification outputs; they are gitignored and reproducible. `docs/architecture.html` + `docs/architecture-spec.json` (the repo architecture diagram produced by the Archify skill) are tracked.
