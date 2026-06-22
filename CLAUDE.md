# Claude Project Instructions

Read `AGENTS.md` first. It is the canonical project instruction file.

For this repository, Claude should behave conservatively:

- Inspect the current files before editing.
- Preserve the local-first, no-build-step architecture.
- Do not commit real content from `data-issue-vault/`.
- Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` after code changes.
- For weak-model handoff work, also read `docs/WEAK_MODEL_CONSTRAINTS.md`.

If AGENTS.md and this file conflict, follow `AGENTS.md`.
