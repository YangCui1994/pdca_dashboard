# Archify

Reference notes for the [Archify](https://github.com/tt-a1i/archify) agent skill: what it is, where it is installed, how it is invoked, and how its code is organised.

This file documents a third-party tool. It is not part of the workbench runtime.

## What It Is

Archify is a **Node.js rendering and validation system** for coding agents. The agent authors a small typed JSON intermediate representation (IR); Archify deterministically compiles that JSON into a self-contained, interactive HTML/SVG artifact.

- **Five diagram types**: `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`.
- **Four visual presets**: `classic` (default), `signal-flow`, `blueprint`, `editorial`, plus independent dark/light color modes.
- **Self-contained output**: one HTML file with inline SVG, theme switching, pan/zoom, search, focus, relationship tracing, semantic views, presentation mode, and exports (PNG, JPEG, WebP, SVG, WebM, 1200×630 share cards).
- **Atomic validation before delivery**: schema, layout, HTML/SVG, route, and label-to-route clearance checks must all pass before an artifact replaces the last known good output.
- **Typed JSON IR**: every renderer-backed mode has a schema and a reproducible source, so the same JSON always renders the same artifact.
- **MIT licensed**. Not an official DeepSeek or workbench product.

The distinction that matters: Archify is **not** a drawing editor and **not** a Mermaid theme. It is not a generic auto-layout engine either — the agent makes the layout judgment (hierarchy, spacing, routes, emphasis) and Archify compiles and verifies it.

## Install Status

Archify is installed **globally as a DSH filesystem skill**, not as a workbench dependency:

```text
C:\Users\yangc\.dsh\skills\archify
```

| Fact | Value |
|---|---|
| Location | `C:\Users\yangc\.dsh\skills\archify` (DSH user skill root, discovery rank 400) |
| Source | Upstream release bundle `archify.zip`, not the development tree |
| Contents | 79 files, ~6.5 MB |
| Scope | All DSH sessions and projects |
| Version | Skill `2.17.0-dev.1` |
| Repo impact | None — no third-party files are committed to this repository |

### Why not the upstream `dsh plugin` route

Archify's README documents a DeepSeek Harness install:

```bash
dsh plugin --profile web add @tt-a1i/archify-dsh@0.1.0
```

That route is not usable in this environment:

- The command hard-requires **`pnpm`**, which is not installed (only `corepack` is present).
- The published adapter pins compatibility to `@deepseek-ai/dsh@0.1.0-rc.6` and bundles skill **2.14.0**; the local DSH is `0.1.5-rc.1`.
- The newer adapter (v0.2.0, targeting `dsh@0.1.2-rc.1`) is **not published to npm**.

Archify's own integration notes describe the DSH adapter as *skill-only* — it "inserts one filesystem Skill provider". Since DSH already scans `~/.dsh/skills` and `<project>/.agents/skills`, placing the skill files directly is functionally equivalent, version-agnostic, and needs no package manager.

### Verify the install

```powershell
node "C:\Users\yangc\.dsh\skills\archify\bin\archify.mjs" doctor
```

Expected: 15 `[ok]` lines ending in `Archify is ready.` Requires Node `>=18` (local: v24.11.1).

### Uninstall

```powershell
Remove-Item "C:\Users\yangc\.dsh\skills\archify" -Recurse -Force
```

### Update

Archify ships an optional, notification-only update checker. It reports a newer release but never downloads or installs one. To disable its network access entirely:

```powershell
$env:ARCHIFY_UPDATE_CHECK_DISABLED = "1"
```

To update manually, replace the skill directory with a newer upstream `archify.zip`.

## How It Is Invoked

The skill is model-invoked — name it in a request and DSH loads `SKILL.md` as instructions:

```text
Use the archify skill to draw: Browser -> API -> Redis cache -> PostgreSQL fallback.
```

To map a real codebase, combine it with repository inspection:

```text
Analyze this repository, then use archify to create a high-level runtime architecture diagram.
Show 8-12 core components, one primary path, external dependencies, and trust boundaries.
Put supporting detail in cards instead of adding more edges.
```

### Choosing a diagram type

| Type | Use for |
|---|---|
| `architecture` | Components, services, storage, cloud/security boundaries, infrastructure |
| `workflow` | Processes, approval gates, tool calls, runbooks, CI/CD |
| `sequence` | API call chains, request lifecycles, async traces, returns |
| `dataflow` | Pipelines, ETL/ELT, lineage, governance, consumers |
| `lifecycle` | State/status transitions, retries, waiting and terminal states |

When the type is ambiguous, ask the bundled triage CLI:

```powershell
node "C:\Users\yangc\.dsh\skills\archify\bin\archify.mjs" guide "Show an API request with Redis cache miss" --json
```

## Code Architecture

### Command surface

`bin/archify.mjs` is the single CLI entry point. It validates arguments, resolves the per-type renderer module, and spawns it as a Node subprocess (`runNode` → `spawnSync`), so each render is an isolated process.

| Command | Purpose |
|---|---|
| `render <type> <in.json> [out.html]` | Compile JSON IR to HTML |
| `validate <type> <in.json>` | Run the artifact gates without writing output |
| `deliver <type> <in.json> [out.html]` | Validate, then atomically commit the HTML |
| `preview <type> <in.json> [out.html]` | Loopback-only desktop watch loop |
| `visual-check <out.html>` | Collect browser evidence from a delivered file |
| `compare architecture <base> <head> [out.html]` | Architecture Delta: Before / Delta / After |
| `migrate workflow <old> <new> --to-schema 2` | Workflow schema v1 → v2 |
| `inspect <type> <in.json>` / `check <out.html>` | Structural inspection |
| `guide [scenario]` / `brands [name]` / `brands capture <url>` | Scenario routing and brand marks |
| `examples` / `doctor` / `demo [dir]` | Self-documentation and environment checks |

Common flags: `--quality standard|showcase`, `--json`, `--repo-root <path>` (architecture only), `--open`, `--no-open`, `--layout-json`.

### Render pipeline

Every renderer follows the same shape:

```text
typed JSON IR
  -> schema validation      (schemas/*.schema.json via generated-validators.mjs)
  -> layout + geometry      (renderers/shared/geometry.mjs and per-type layout)
  -> artifact gates         (crossings, label clearance, route rhythm, spacing)
  -> SVG injected into      (assets/template.html)
  -> atomic commit          (renderers/shared/output-path.mjs)
```

Key properties:

- **No dependencies at runtime.** Validation uses a bundled standalone validator; `package.json` devDependencies (`ajv`, `parse5`, `saxes`, `simple-icons`) are build-time only.
- **Fail-closed schemas.** Every level sets `additionalProperties: false`, so unknown fields are rejected rather than silently ignored.
- **Machine-readable failures.** `validate --json` and `deliver --json` emit stable rule codes with `subject`, measured `evidence`, and supported repair controls — not a Node stack trace.

### Module map

```text
bin/archify.mjs                  CLI dispatch (2101 lines)
bin/preview.mjs                  Watch loop, loopback-only, keeps last-good output
bin/visual-check.mjs             Headless browser evidence collection
bin/open-artifact.mjs            Post-commit file opener

renderers/<type>/render-<type>.mjs   One renderer per diagram type
renderers/architecture/grid.mjs      Grid placement helpers
renderers/workflow/workflow-compiler.mjs   Workflow v2 constraint solver (largest module)

renderers/shared/geometry.mjs        Routing, endpoint sides, port spread, crossing and
                                     label-clearance detection (the core layout engine)
renderers/shared/cli.mjs             Diagram/template loading, brand-mark merge, output
renderers/shared/validator.mjs       Schema validation entry point
renderers/shared/diagnostics.mjs     Diagnostic construction and throwing
renderers/shared/legend.mjs          Legend resolution, footprint, obstacle geometry
renderers/shared/text-fit.mjs        CJK-aware text measurement and font fitting
renderers/shared/layout-report.mjs   Box and path primitives
renderers/shared/output-path.mjs     Output-path safety and atomic commit
renderers/shared/i18n.mjs            Viewer UI localization (en, zh-CN)
renderers/shared/brand-marks.mjs     Brand mark resolution and rendering
renderers/shared/engineering-profiles.mjs  Optional deployment-ownership profile
renderers/shared/repository-evidence.mjs   Git-verified source badges (SRC n)
renderers/shared/repository-location.mjs   Repo root discovery
renderers/shared/desktop-readability.mjs   Minimum readable source text
renderers/shared/utils.mjs           Escaping and SVG primitives

delta/architecture-delta.mjs     Architecture snapshot comparison
recipes/scenarios.mjs            `guide` scenario router
migrations/workflow-v2.mjs       Workflow schema migration

schemas/*.schema.json            Five diagram schemas + common.schema.json ($defs only)
brand-marks/catalog.json         Built-in brand catalog
assets/template.html             Viewer shell that generated artifacts embed
references/*.md                  Progressive-disclosure contracts loaded on demand
scripts/check-update.mjs         Notification-only update checker
scripts/check-render-output.mjs  Build-time render regression verifier
scripts/render-examples.mjs      Example regeneration
scripts/update-contract.mjs      Update-contract handling
```

### Generated files — do not hand-edit

These are build outputs committed into the bundle. Editing them by hand will be overwritten:

```text
renderers/shared/generated-validators.mjs    (~431 KB)
renderers/shared/generated-brand-marks.mjs   (~163 KB)
assets/template.html                         (~774 KB)
brand-marks/catalog.json
```

### Progressive disclosure

`SKILL.md` is the only always-loaded file (16 KB). Everything else is loaded on demand, and `SKILL.md` explicitly forbids reading renderer internals before a first candidate exists:

- `references/authoring-contract.md` — field enums, spacing math, geometry repair rules
- `references/delivery-contract.md` — receipt fields, coverage, manual review recording
- `references/viewer-runtime.md` — share cards, motion, stories, deep links
- `references/brand-marks.md` — brand capture workflow
- `schemas/README.md` and `renderers/*/README.md` — per-renderer layout budgets

## Data Contract

Every diagram document requires `schema_version`, `diagram_type`, `meta.title`, and the type's structural arrays. Structural arrays per schema:

| Schema | Structural arrays |
|---|---|
| `architecture` | `components`, `boundaries`, `connections` |
| `workflow` | `lanes`, `phases`, `groups`, `mainPath`, `nodes`, `edges` |
| `sequence` | `participants`, `segments`, `messages`, `activations` |
| `dataflow` | `stages`, `nodes`, `flows` |
| `lifecycle` | `lanes`, `states`, `transitions` |

Notable `meta` fields:

| Field | Effect |
|---|---|
| `quality_profile` | `standard` (default) or `showcase`. Showcase turns several warnings into hard failures and requires all 9 artifact checks. |
| `locale` | `en` or `zh-CN`. Localizes **viewer-owned UI only** — never authored content. Other languages fall back to English and must be disclosed. |
| `visual_preset` | Omitted by default so diagrams open in `classic`. Independent of dark/light. |
| `animation` | `"trace"` opts into finite SVG/CSS motion. Omitted means static. |
| `legend` | `mode: auto\|all\|hidden` plus per-kind `label` / `visible` overrides. |
| `views` | Up to five curated guided-story chapters. |
| `engineering_profile` | `deployment-ownership` fails closed unless authored owners, regions, and crossings are all present. Never implicit. |
| `column_fit` | Sequence only: `fixed` (default, stable coordinates) or `spread`. |

## Delivery and Verification

Three claims are deliberately kept separate:

| Claim | Proven by |
|---|---|
| Deterministic artifact checks (schema, layout, SVG, routes, labels) | `deliver` |
| Bounded behavior in a real browser | `visual-check` |
| Perceptual polish | An actual human or image-capable reviewer |

`deliver` freezes the exact specification bytes into a private same-directory snapshot, renders and checks that snapshot, atomically commits the HTML, and reports SHA-256 plus byte counts for both the spec and the artifact. A failed delivery preserves the previous output — so run `visual-check` only on the delivered path.

Repair discipline: change only the diagnosed `subject`, verify `evidence`, choose from `supportedFixes`, and keep correcting while the error count reaches a new minimum. Two consecutive rounds without improvement means stop and report the unresolved diagnostics truthfully.

## Practical Notes For This Repo

- **Run the CLI with absolute paths.** `SKILL.md` examples are written as `node bin/archify.mjs ...` relative to the skill root. The skill root is outside this workspace, so from here always use the full path: `node "C:\Users\yangc\.dsh\skills\archify\bin\archify.mjs" ...`
- **Generated artifacts do not appear in the Web Produced Files strip** when created by shell commands. Ask the agent to return the exact workspace paths of the JSON spec and the HTML artifact, then open them from the workspace.
- **Write artifacts into this workspace** (for example under a scratch or docs assets directory) rather than into the skill directory, so results stay reviewable and version-controllable.
- **Keep this file as the entry point.** Detailed contracts live in the skill's own `references/` and `schemas/README.md`; do not duplicate them here.
- **Prefer the installed skill over vendoring.** Do not copy the skill bundle into this repository; `.gitignore` keeps it out and the global install serves every project.

## Upstream References

- Repository: <https://github.com/tt-a1i/archify>
- Skill contract: `archify/SKILL.md` upstream
- Schema reference: `archify/schemas/README.md` upstream
- Interactive scenario guide and proof lab are linked from the upstream README
- License: MIT (`archify/LICENSE`); third-party notices: `archify/THIRD_PARTY_NOTICES.md`
