# GitHub Sync Notes

## Intended Scope

Sync these categories:

- App code in `app/`
- Tests in `tests/`
- Project instructions: `AGENTS.md`, `CLAUDE.md`
- Docs in `docs/`
- Project-local skills in `.agents/`
- Design references in `design-demos/`
- Vault skeleton `.gitkeep` files

Do not sync:

- Real `data-issue-vault/` notes
- `.env` files
- Local scratch files
- Runtime caches

## First-Time Remote Setup

If the repository has no remote:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin workbench-mvp
```

If using HTTPS:

```bash
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin workbench-mvp
```

## Clone On Another Computer

```bash
git clone git@github.com:OWNER/REPO.git
cd REPO
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m app.backend.server --provider fake --port 8765
```

Then open `http://127.0.0.1:8765/`.
