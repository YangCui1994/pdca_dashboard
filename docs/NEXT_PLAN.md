# Next Plan

Current date: 2026-06-22.

The project is now complete through the pre-Round-Table handoff point. The next major stage is to design the Round Table interface, but do not implement simulated multi-agent debate until the user explicitly asks for it.

## Completed Before Round Table

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
