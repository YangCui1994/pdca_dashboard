# Next Plan

Current date: 2026-09-16 (UX-prototype merge landed into `workbench/`; Round Table section unchanged since 2026-06-22).

## UX Prototype Merge — LANDED (2026-09-16)

Executed per `docs/plans/2026-09-15-merge-ux-prototypes.md` (full version). Now true in `workbench/`:

- New modules with tests: `services/capture_routing.py`, `services/wrapup.py`,
  `services/prompt_library.py` (+ official `workbench/prompts/` home), `runtime/text_runtime.py`
  (thread-offloaded draft generation), `services/file_watcher.py` + `file_routing.py`,
  `components/feedback.py`, `components/wrapup_wizard.py`. `prototypes/uxbase` is now a
  re-export shell — the five prototypes keep running without code changes.
- Today page = TodayHub: resident smart capture bar (`!` plan / `#project` plan / plain idea),
  rollover bar (batch-undoable) with the four-step wrap-up wizard, idea touch-once rows
  (mouse-first; only arrow-key selection kept from B), draft cards (adopt / edit-adopt /
  dismiss, no card on AI failure). Page-local subtree refresh; global render untouched.
- Project page = master-detail (D's revised form, no free canvas): left 1/4 compact project
  cards (stalled red mark + real days), right 3/4 detail (editable meta, outline, action
  status blocks with click-to-cycle via `set_action_status`, stalled list, heatmap).
- P0 fixes landed: overview today-task checkboxes persist via service; node detail shows a
  real last-update date (or nothing instead of today); dead nav entries (设置/回收站) removed.
- AI calls (draft cards, thinking modes, wizard Check) run on `page.run_thread` — real
  endpoints no longer freeze the UI.
- Deployment form is **web mode by default**: `--ui web|desktop` (default web), `--host/--port`,
  optional `--watch-dir`. Intranet-only, no auth; single-writer / multi-viewer positioning.
- UI style baseline switched to **entp-manual** (user decision 2026-09-16, overrides the old
  purple theme): blue `#316BEE` family, ink/muted grays, semantic green/amber/red, Microsoft
  YaHei UI. Crosswalk: `refs/SOURCES.md`, local clone `refs/entp-manual/`.
- Test status at merge: `python -m unittest discover -s workbench/tests` = 184 green
  (149 baseline + 35 new/updated); the five prototype smokes stay green.

The project remains complete through the pre-Round-Table handoff point; the next major stage
is still the Round Table interface (design only, below).

## Project-Page & AI-Panel Refinement — LANDED (2026-09-16, second round)

User-driven decisions after trying the merged build (all shipped, 193 tests green):

- **AI panel is hidden by default**; the sidebar gets an "AI 助手" toggle (not a nav item —
  the five-item nav contract is unchanged). Opening it from a project route pre-selects that
  project as the thinking-mode target. A red dot on the toggle marks an awaiting Proposal.
- **The panel hosts the E-form draft console** (`components/concierge.py`): stage actions
  (今日计划建议 / Check 引导 / 本周复盘), thinking-mode invocation (mode + target dropdowns),
  and the draft-card queue (adopt / edit-adopt / dismiss). Same red line: drafts only, adopt
  writes. Today-page entries stay.
- **Artifact big card removed** — compressed to a "项目流图" button in the detail header
  (`on_open_artifact`); `components/artifact_panel.py` deleted. Review (Proposal text) and the
  flow diagram (static HTML) stay separate features; only the screen space overlapped.
- **Owner meta cell removed** — just a name avatar circle next to 下一个里程碑, full name in
  tooltip.
- **Detail-area scroll fix**: `_detail_view`'s outer column is scrollable now; at ~720px-high
  windows the node tree was clipped (7 nodes, 2 visible) with no way to scroll. Visual gates
  had only been run at 1440x900+.

## UX Prototype Round Backlog (2026-09-15)

Five runnable interaction prototypes live in `prototypes/` (see `prototypes/ux-2026-09/README.md`).
Independent fresh-context review ranked them **A > C > B > E > D** and produced a merge plan
(`prototypes/ux-2026-09/review/verdicts/_cross_compare.md`, repairs in `review/REPAIRS.md`).
Merge-back work, when the user picks a direction:

- Merge skeleton from A (today hub, smart capture `!`/`#project` routing, rollover), B's keyboard
  layer + focus guard, C's four-step wrap-up wizard (add "already closed today" memory), E's draft
  cards (adopt/edit-adopt/dismiss, no-card-on-AI-failure) and watch_inbox routing; D contributes
  only the stalled highlight + real stall days.
- Before first run against a real AI endpoint: make AI calls async (fake provider hides latency;
  sync call currently freezes the session up to the timeout).
- Service-layer prerequisites already merged with tests: `set_action_status`,
  `DayRecord.check_note/act_note` (+ `days/<date>.md` mirror), `append_project_progress` /
  `remove_project_progress`.
- `docs/architecture.html` (archify) is a one-shot dev doc; regen with `deliver architecture
  docs/architecture-spec.json`; archify stays out of the product runtime.
- Backlog candidates: file routing for PDF/docx (needs parsers = new deps), thinking-mode prompt
  library merge into `workbench/prompts/`, project-structure export artifact, formal-app P0 fixes
  listed in `prototypes/ux-2026-09/DESIGN_CHECKLIST.md`.

## Completed Before Round Table

> Stages 1-4 describe the retired v1 static-PDCA app (`app/` + `tests/`, removed 2026-09-16 when GitHub
> history was reset). Kept as the historical record; the live runtime is `workbench/`.

### Stage 1: GitHub Sync And Portability

- Code, docs, tests, design demos, project instructions, and project-local skills are intended to be tracked.
- Real `data-issue-vault/` content is ignored; only skeleton `.gitkeep` files should be tracked.
- Clone/run instructions live in `README.md` and `docs/GITHUB_SYNC.md`.
- Weak-model operating rules live in `docs/WEAK_MODEL_CONSTRAINTS.md`.

### Stage 2: Daily PDCA Page

- `/today.html` is the strict time-scale PDCA entry.
- It separates today and this-week items.
- It includes status/date filters.
- It has four input boxes: Plan, Do, Check, Act.
- Single-entry AI analysis is recorded to `data-issue-vault/reviews/pdca-input-log.md`.
- Manual periodic review generates timestamped files in `data-issue-vault/reviews/`.
- The PDCA result UI separates Plan, true Do, candidate Do, not Do / judgment, Check, and Act.
- Accepted PDCA analysis can be appended to a selected task folder's `events.md`.

### Stage 3: All-Items Board

- `/` is the all-items card board.
- It shows card status columns.
- Cards expose current blocker, existing basis, latest event, created date, and tags.
- It includes status/date/tag/blocker filters.
- It includes status move actions.
- Empty columns render explicit empty states.

### Stage 4: Agent Context

- Each task folder has separate document pages for `task.md`, `context.md`, `events.md`, and `ai-notes.md`.
- Rendered Agent Context includes task metadata, files, assets, and context readiness.
- Task page can copy/download rendered Agent Context.
- `/api/context-readiness` reports missing context before a downstream agent starts.

## Next Stage: Round Table Interface

Goal: leave a clean interface for future multi-agent decisions.

Build next:

- Define a decision request data shape.
- Define roles and review outputs.
- Save Round Table outputs as Markdown.

Stop here until the user explicitly asks to implement multi-agent debate. The current project should not simulate a real Round Table with one weak model and pretend it is multiple independent agents.
