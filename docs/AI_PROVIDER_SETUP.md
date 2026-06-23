# AI Provider Setup

This app keeps AI behind `app/backend/ai.py`. The frontend only calls local HTTP routes such as `/api/capture`, `/api/pdca-entry`, and `/api/document-helper`.

Do not call company gateways, Codex, Hermes, or OpenCode directly from browser JavaScript. The local Python backend owns all subprocess calls and Markdown file writes.

## Current Local Setup: Codex

Use Codex as the default AI provider on this machine:

```bash
python3 -m app.backend.server \
  --provider codex \
  --codex-cwd /Users/yangcui/Research/pdca_dashboard \
  --port 8768
```

Optional model override:

```bash
python3 -m app.backend.server \
  --provider codex \
  --codex-model gpt-5 \
  --codex-cwd /Users/yangcui/Research/pdca_dashboard \
  --port 8768
```

The provider runs:

```bash
codex exec -C <repo> --sandbox read-only --ask-for-approval never --ephemeral -
```

The prompt is sent through stdin. The read-only sandbox is intentional: AI Helper should return text, not edit files directly. The app saves Markdown only after the user accepts or submits through the UI.

## Internal Windows Setup: OpenCode

On the Windows company environment, keep the same app and switch the provider at startup:

```powershell
python -m app.backend.server `
  --provider opencode `
  --opencode-binary opencode `
  --opencode-model company/MiniMax-M2.7 `
  --vault data-issue-vault `
  --port 8768
```

Other known model ids can be passed to `--opencode-model`, for example:

- `company/DeepSeek-V4-Flash`
- `company/GLM-5.1`
- `company/Kimi-K2.5`
- `company/Kimi-K2.5-nonthinking`
- `company/Kimi-K2.6`
- `company/MiniMax-M2.5`
- `company/MiniMax-M2.7`
- `catl/auto`

The provider runs:

```bash
opencode run --model <model>
```

The prompt is sent through stdin. This is different from `opencode serve --port 4096`: the serve UI is not an OpenAI-compatible `/v1` API and should not be called by this app.

## When To Use Which Provider

- `fake`: setup, tests, and UI/storage debugging.
- `codex`: current local default for this repo.
- `opencode`: company Windows handoff path where OpenCode already has provider credentials.
- `hermes`: fallback for local Hermes Agent experiments.

## Frontend Behavior

Creating a task does not call AI by default. Check `使用 AI 整理` when you want the selected provider to draft structure during capture.

Document pages always use draft-first AI behavior: `/api/document-helper` returns an unsaved Markdown draft, and the user decides whether to apply it.

## Provider Files

To change provider wiring, edit only:

- `app/backend/ai.py`
- `app/backend/server.py`
- `tests/test_ai.py`

Do not change frontend pages when only switching between Codex and OpenCode.
