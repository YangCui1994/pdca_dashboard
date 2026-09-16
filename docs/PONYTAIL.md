# Ponytail

Reference notes for the [Ponytail](https://github.com/DietrichGebert/ponytail) lazy-senior-dev ruleset and its skills: what it is, how it is installed into DSH, what each skill does, and the caveats that come with a static always-on install.

This file documents a third-party tool. It is not part of the workbench runtime.

## What It Is

Ponytail is an **agent ruleset plus six skills** that push an agent toward the smallest solution that actually works. It is not a library, CLI, or service — it changes how the agent decides what to build.

- **The ladder**: before writing code, stop at the first rung that holds — does this need to exist at all (YAGNI), is it already in this codebase, does the stdlib do it, does a native platform feature cover it, does an installed dependency solve it, can it be one line, and only then write the minimum.
- **Explicitly not negligent**: trust-boundary validation, data-loss error handling, security, accessibility, and comprehension are never on the chopping block.
- **Modes**: `lite`, `full` (default), `ultra`, plus `off`.
- **Upstream reports ~54% less code, ~22% fewer tokens, ~20% cheaper, ~27% faster** versus the same agent without the skill, measured on 12 feature tasks against a real FastAPI + React repo, with a 100% safety score. Self-reported by the project.
- **MIT licensed**. Upstream `DietrichGebert/ponytail`, installed here at **v4.9.0**. Not an official DeepSeek or workbench product.

Ponytail and this repository's existing `AGENTS.md` share a philosophy — "keep changes small", "prefer editing existing simple modules over adding frameworks" — so the two do not conflict.

## Install Status

Ponytail installs as **two independent pieces**. Neither uses hooks or MCP.

| Piece | Location | Size |
|---|---|---|
| Six skills | `C:\Users\yangc\.dsh\skills\ponytail`, `-audit`, `-debt`, `-gain`, `-help`, `-review` | 17,527 B total |
| Always-on ruleset | `C:\Users\yangc\.dsh\AGENTS.md` | 2,815 B |

| Fact | Value |
|---|---|
| Upstream | `@dietrichgebert/ponytail` v4.9.0 |
| Commit | `356918eba965ee1eac64bd3a7f0dd02108350de5` |
| Ruleset source | Upstream `.agents/rules/ponytail.md` |
| Scope | All projects and sessions (user-global) |
| Repo impact | None — nothing is committed to this repository |

The ruleset is taken from `.agents/rules/ponytail.md`, not the repository-root `AGENTS.md`. The two are byte-identical except that the root file appends a line noting it also applies to the ponytail repo itself — which is meaningless in a foreign global config.

## Why Not The Official Install Paths

Ponytail advertises installers for 20 agents. **DeepSeek Harness is not among them**, and the two primary paths fail here for structural reasons rather than missing support.

### Lifecycle hooks do not transfer

The Claude Code and Codex plugins inject the ruleset every turn through host-specific lifecycle events (`UserPromptSubmit`, `PreToolUse` with a subagent matcher). DSH has no equivalent event, so `hooks/ponytail-*.js` has nothing to attach to. **DSH's per-turn injection point is `AGENTS.md`**, which is what this install uses.

### The MCP server cannot be always-on

Ponytail ships `ponytail-mcp`, which exposes exactly one tool (`ponytail_instructions`) and one prompt (`ponytail`). Both are **pull-based**:

- DSH's `dsh-mcp-client` **bridges tools only and drops prompts**, so the prompt is unavailable. (The same limitation is recorded in `docs/CODEGRAPH.md`.)
- The remaining tool must be invoked by the model, and nothing forces that per turn.

Ponytail's own README concedes the point: *"It is not a replacement for the always-on adapters… there is no portable MCP primitive for 'inject this into every turn'."*

**The mapping that actually works:** hooks → `AGENTS.md`; commands → skills.

## The Always-On Ruleset

Ponytail's ladder is installed as the DSH **user-global** instruction file, `~/.dsh/AGENTS.md` (resolved from `$DSH_HOME`).

`dsh-agent-instructions` builds one baseline message containing the user-global file followed by the project chain — every instruction file from the project root down to the working directory, broad-to-specific. Two consequences:

- **The ruleset applies to every project and every session**, not just this repo.
- **More specific files win.** A project's own `AGENTS.md` is loaded after the global one, so project instructions take precedence where the two disagree.

The default instruction budget is 65,536 bytes; a 2.8 KB ruleset is negligible against it.

The file opens with a provenance comment recording the version, upstream commit, and how to disable it, so a future reader is not left guessing where it came from.

### Live reload

DSH re-reads instruction files on change rather than only at boot: writing `~/.dsh/AGENTS.md` produced an immediate user-global injection, and editing it produced an immediate "this file changed" replacement. A new session is not required.

### The static-full caveat

**The always-on ruleset is permanently at `full` intensity.** Upstream's hooks rewrite the injected text per turn based on `PONYTAIL_DEFAULT_MODE` or `~/.config/ponytail/config.json`; a static file cannot. So:

- `lite` and `ultra` take effect **only** when the `ponytail` skill is loaded explicitly — they change the loaded skill's guidance, not the always-on baseline.
- `PONYTAIL_DEFAULT_MODE` and `~/.config/ponytail/config.json` **have no effect** in this install.

Real per-turn level switching requires a DSH event-injection point that does not currently exist.

## Skills

All six are model-invocable and user-invocable. Frontmatter is `name` + `description`; only `ponytail` adds `argument-hint` and `license`, and DSH tolerates both (as it does archify's `license`).

| Skill | Purpose | Writes? |
|---|---|---|
| `ponytail` | The full ladder, rules, intensity levels, and output discipline. Also the mode switch: `/ponytail [lite\|full\|ultra\|off]` | No |
| `ponytail-review` | Over-engineering review of **the current diff**. Hands back a delete-list | No |
| `ponytail-audit` | The same review across the **whole repository**, ranked biggest cut first | No |
| `ponytail-debt` | Harvests every `ponytail:` comment into a debt ledger | Only if asked |
| `ponytail-gain` | Displays the upstream benchmark scoreboard | No |
| `ponytail-help` | Quick reference for modes, skills, and commands | No |

### Review and audit tags

Both review skills emit one line per finding in a fixed vocabulary, ending with a single metric:

```text
L4:      native:  moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.
L12-38:  stdlib:  27-line validator class. "@" in email, 1 line.
repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second exists.
L52-71:  delete:  retry wrapper around an idempotent local call. Nothing replaces it.
L30-44:  shrink:  manual loop builds dict. dict(zip(keys, values)), 1 line.
net: -140 lines possible.
```

`delete` / `stdlib` / `native` / `yagni` / `shrink`, or `Lean already. Ship.` when there is nothing to cut.

**Scope boundary worth remembering:** both skills cover over-engineering and complexity **only**. Correctness bugs, security holes, and performance are explicitly out of scope and are routed elsewhere. Do not treat a clean `ponytail-review` as a security or correctness review.

### Intensity levels

| Level | Behaviour |
|---|---|
| `lite` | Builds what was asked, names the lazier alternative in one line. The user decides. |
| `full` | The ladder enforced; stdlib and native first; shortest diff, shortest explanation. **Default.** |
| `ultra` | YAGNI extremist. Deletion before addition; ships the one-liner and challenges the rest of the requirement. |

Upstream's own illustration for "add a cache for these API responses":

- `lite` — "Done, cache added. FYI: `functools.lru_cache` covers this in one line if you'd rather not own a cache class."
- `full` — "`@lru_cache(maxsize=1000)` on the fetch function. Skipped custom cache class, add when lru_cache measurably falls short."
- `ultra` — "No cache until a profiler says so. When it does: `@lru_cache`. A hand-rolled TTL cache class is a bug farm with a hit rate."

## Two Conventions It Introduces Into Your Code

Installing the always-on ruleset changes code conventions globally, not just behaviour:

**1. `ponytail:` comments.** Deliberate simplifications that cut a real corner with a known ceiling must be marked with a comment naming the ceiling and the upgrade path:

```python
# ponytail: global lock, per-account locks if throughput matters
```

These accumulate silently unless harvested — `/ponytail-debt` collects them and flags any that name no revisit trigger with a `no-trigger` tag, since those are the ones that rot.

**2. One runnable check.** Non-trivial logic (a branch, a loop, a parser, a money or security path) is expected to leave exactly **one** smallest runnable check behind — an assert-based self-check or one small test file, no frameworks. Trivial one-liners need none.

This aligns with this repository's existing rule to add tests when changing storage, HTTP, or frontend contracts.

## Practical Notes For This Repo

- **Ponytail is active everywhere now.** Every project and session picks up the ladder. That is the intended behaviour, and it is the largest behavioural change in this repository's agent setup.
- **Project instructions still win.** This repo's `AGENTS.md` loads after the global file, so its explicit rules take precedence on conflicts.
- **Output style changes.** Expect code first and at most three short lines of explanation, shaped like `[code] → skipped: [X], add when [Y].` Explicitly requested reports and walkthroughs are still given in full — the rule is only against unrequested prose.
- **Ask for the full version when you want it.** Ponytail builds the requested version on insistence and does not re-argue. The ladder is a default, not a veto.
- **Never rely on it for safety review.** `ponytail-review` and `ponytail-audit` are complexity-only by design.
- **It governs what is built, not how the agent talks.** Upstream pairs it with Caveman for terse prose; ponytail alone does not shorten conversation.

## Disable Or Uninstall

Turn off the always-on ruleset only:

```powershell
Remove-Item "C:\Users\yangc\.dsh\AGENTS.md"
```

The six skills remain available on demand. To remove everything:

```powershell
Remove-Item "C:\Users\yangc\.dsh\skills\ponytail*" -Recurse -Force
```

Inside a session, `stop ponytail` or `normal mode` reverts for that session without touching either file.

To update, re-copy `skills/*` and `.agents/rules/ponytail.md` from a newer upstream checkout. Upstream's `node scripts/check-rule-copies.js` keeps its own agent copies aligned; there is no equivalent check for this global install, so re-copy the ruleset wholesale rather than editing it in place.

## Upstream References

- Repository: <https://github.com/DietrichGebert/ponytail>
- Agent file mapping (which file each host reads): upstream `docs/agent-portability.md`
- Benchmark method and per-task tables: upstream `benchmarks/results/2026-06-18-agentic.md`
- Companion for terse prose, by the same ecosystem: <https://github.com/JuliusBrussee/caveman>
- License: MIT
