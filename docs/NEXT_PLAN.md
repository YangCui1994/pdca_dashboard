# Next Plan

Current date: 2026-06-22.

This project is now ready to sync to GitHub as a portable local-first codebase. The next work should proceed in small stages.

## Stage 1: GitHub Sync And Portability

Goal: make the repository usable on another computer by a weaker model.

Checklist:

- Track code, docs, project-local skills, tests, and design demos.
- Do not track real `data-issue-vault/` content.
- Confirm clone/run instructions in `README.md`.
- Confirm weak-model constraints in `docs/WEAK_MODEL_CONSTRAINTS.md`.
- Push branch to GitHub.

## Stage 2: Daily PDCA Page

Goal: make `/today.html` the strict time-scale PDCA entry.

Build next:

- Show today and this week sections separately.
- Add date/status filters.
- Add a PDCA review result section that separates:
  - Plan
  - true Do
  - candidate Do
  - not Do / judgment
  - Check
  - Act
- Save accepted PDCA review output into the task folder's `events.md`.

Stop before:

- Calendar sync.
- Notifications.
- Drag-and-drop scheduling.

## Stage 3: All-Items Board

Goal: make `/` useful for scanning all active work.

Build next:

- Better summary extraction from frontmatter and sections.
- Status move actions.
- Card filters for status, date, tag, and blocker.
- Clear empty states for each column.

Stop before:

- Drag-and-drop.
- Multi-user collaboration.
- Database migration.

## Stage 4: Agent Context

Goal: let an agent reliably pick up one task folder.

Build next:

- Add a copy/download action for rendered agent context.
- Include file metadata and known missing context.
- Add a "context readiness" check.

Stop before:

- Automatic long-running agents.
- External model orchestration.

## Stage 5: Round Table Interface

Goal: leave a clean interface for future multi-agent decisions.

Build next:

- Define a decision request data shape.
- Define roles and review outputs.
- Save Round Table outputs as Markdown.

Stop here until the user explicitly asks to implement multi-agent debate. The current project should not simulate a real Round Table with one weak model and pretend it is multiple independent agents.
