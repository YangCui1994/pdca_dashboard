# GitHub Sync Notes

## Intended Scope

Sync these categories:

- Workbench app code in `workbench/` and `prototypes/`
- Workbench tests in `workbench/tests/`
- Project instructions: `AGENTS.md`, `CLAUDE.md`
- Docs in `docs/`
- Project-local skills in `.agents/`
- Reference index `refs/SOURCES.md`
- Vault skeleton `.gitkeep` files

Do not sync:

- Real `data-issue-vault/` notes
- `prototypes/ux-2026-09/demo_vault/` (regenerable demo data; may contain real notes)
- `refs/entp-manual/` (third-party clone; re-fetch per `refs/SOURCES.md`)
- Generated artifacts (`workbench/artifacts/`, `docs/architecture.visual-check.*`)
- `.env` files
- Local scratch files
- Runtime caches

> 2026-09-16: GitHub history was reset to a single clean commit and the v1 static-PDCA app (`app/`, `tests/`, `design-demos/`) was removed. The full old history is preserved locally on `backup/history-before-github-wipe` (not pushed).

## First-Time Remote Setup

If the repository has no remote:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

If using HTTPS:

```bash
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

## Clone On Another Computer

```bash
git clone https://github.com/YangCui1994/pdca_dashboard.git
cd pdca_dashboard
pip install flet
python -m unittest discover -s workbench/tests -p 'test_*.py' -v
python -m workbench.main
```

Then open `http://127.0.0.1:8550`.
