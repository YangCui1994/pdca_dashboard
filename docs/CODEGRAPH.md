# CodeGraph

Reference notes for the [CodeGraphMCPServer](https://github.com/nahisaho/CodeGraphMCPServer) code-graph MCP server: what it is, how it is installed here, the dependency trap that broke it, and what its index of this repository actually contains.

This file documents a third-party tool. It is not part of the workbench runtime.

## What It Is

CodeGraphMCPServer is a **Python MCP server that builds a queryable knowledge graph of a codebase** and exposes GraphRAG-style retrieval over it.

- **AST parsing via Tree-sitter** across 16 languages (Python, TypeScript, JavaScript, Rust, Go, Java, PHP, C#, C, C++, HCL, Ruby, Kotlin, Swift, Scala, Lua).
- **Graph construction**: entities (module, class, function, method) and typed relations (`calls`, `contains`, `imports`, `inherits`).
- **Community detection** using the Louvain algorithm, for module clustering.
- **GraphRAG search**: `global_search` across community summaries, `local_search` within an entity neighborhood.
- **Self-contained storage**: one SQLite file, no external database.
- **MIT licensed**, by `nahisaho`. Not an official DeepSeek or workbench product.

## Install Status

CodeGraph runs from an **isolated virtual environment**, not from the system Python:

```text
C:\Users\yangc\.codegraph-venv
```

| Fact | Value |
|---|---|
| Location | `C:\Users\yangc\.codegraph-venv` |
| Entry point | `C:\Users\yangc\.codegraph-venv\Scripts\codegraph-mcp.exe` |
| `codegraph-mcp-server` | `0.8.0` (latest on PyPI) |
| `mcp` SDK | `1.30.0` — **pinned below v2 on purpose** |
| Python | 3.13.9 (venv seeded from Anaconda) |
| Graph storage | `<repo>/.codegraph/graph.db` |

### Why not the Anaconda install

`codegraph-mcp-server` is also installed in `C:\Users\yangc\anaconda3`, and that copy **does not work**. Do not point anything at `C:\Users\yangc\anaconda3\Scripts\codegraph-mcp.exe`.

## The `mcp` 2.x Incompatibility

This is the trap that makes the tool look broken when it is only mis-paired.

| Component | Version | Behaviour |
|---|---|---|
| `codegraph-mcp-server` 0.8.0 | declares `mcp>=1.0.0` (no upper bound) | uses the **v1** low-level `Server` decorator API |
| `mcp` SDK (Anaconda) | **2.1.1** | v2 removed `Server.list_tools` and renamed `FastMCP` → `MCPServer` |

Result: `index` and `stats` work (they never touch the MCP layer), but `serve` dies immediately:

```text
Error: 'Server' object has no attribute 'list_tools'
```

The SDK's own error names the fix: `pin 'mcp<2' to keep running v1 code`. Because an unpinned `mcp>=1.0.0` is satisfied by the newer incompatible major, a plain `pip install codegraph-mcp-server` reproduces this failure on any machine with mcp 2.x present.

**The fix used here:** a dedicated venv with `mcp<2` resolved first, leaving Anaconda's `mcp` 2.1.1 untouched for whatever else depends on it.

```powershell
python -m venv C:\Users\yangc\.codegraph-venv
& C:\Users\yangc\.codegraph-venv\Scripts\python.exe -m pip install "mcp<2" codegraph-mcp-server
```

### Verify the install

A process check is not evidence — the server only fails when the MCP layer is exercised. Probe the real stdio handshake instead. A reusable probe lives at `.scratch/probe_codegraph_mcp.py`:

```powershell
python .scratch\probe_codegraph_mcp.py "C:\Users\yangc\.codegraph-venv\Scripts\codegraph-mcp.exe"
```

Expected output:

```text
initialize OK -> {'name': 'codegraph-mcp', 'version': '1.30.0'}
tools: 14
  - query_codebase
  - find_dependencies
  ...
```

Running that same probe against the Anaconda executable is what surfaces the `list_tools` failure.

## DSH Registration

CodeGraph is registered with the harness as an MCP server through `@deepseek-ai/dsh-mcp-client`, configured in the DSH web profile patch layer:

```text
C:\Users\yangc\.dsh\profiles\web\cordis.patch.yml
```

```yaml
- insert:
    - id: mcp-codegraph
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: codegraph
        transport: stdio
        command: 'C:\Users\yangc\.codegraph-venv\Scripts\codegraph-mcp.exe'
        args: ['serve', '--repo', 'D:\2026_agent_work\02_GLM_personal_workbench_glm']
        cwd: 'D:\2026_agent_work\02_GLM_personal_workbench_glm'
        toolCallTimeoutMs: 120000
```

### Tool naming and what actually reaches the model

Configured `serverName: codegraph`, so its tools register as:

```text
mcp__codegraph__query_codebase
mcp__codegraph__find_callers
mcp__codegraph__global_search
...
```

`dsh-mcp-client` **bridges tools only**. Of the server's advertised surface, only the 14 tools arrive:

| Surface | Count | Available in DSH |
|---|---|---|
| Tools | 14 | Yes |
| Resources (`codegraph://...`) | 4 | **No** |
| Prompts | 6 | **No** |

### A restart is required

Editing the patch alone does not activate the server. The harness composes the MCP client row at boot, and a running session's tool catalog is fixed. After editing the patch, **restart the DSH process**; until then no `mcp__codegraph__*` tools exist and no `codegraph` process appears in the process tree.

`failOnStartupError` is deliberately left at its default (`false`), so a codegraph startup failure degrades to "no tools" instead of preventing the harness from booting.

### Switching projects

`--repo` and `cwd` pin the graph to one repository, while the DSH profile is global. To move to another project, change **both** paths together and re-index:

```powershell
& C:\Users\yangc\.codegraph-venv\Scripts\codegraph-mcp.exe index "<repo>" --incremental
```

## CLI Reference

`codegraph-mcp` — global options are `-h` and `--version`.

| Command | Purpose |
|---|---|
| `serve [--repo PATH] [--transport stdio\|sse] [--port N]` | Run the MCP server in the foreground (this is what DSH spawns) |
| `start [--repo PATH] [--transport sse] [--port 8080]` | Run the MCP server in the background |
| `stop` / `status` | Manage the background server |
| `index PATH [--incremental\|--full] [--community\|--no-community]` | Build or update the graph |
| `query "<text>" --repo PATH` | Query the graph from the shell |
| `stats [PATH]` | Entity / relation / community / file counts |
| `community` | Run community detection |
| `watch PATH [--debounce N] [--community]` | Auto-reindex on file changes |

`index` defaults to `--incremental` and `--community`.

## Index Architecture

Storage is a single SQLite database at `<repo>/.codegraph/graph.db` (configurable via `CODEGRAPH_DB_PATH`; the default is relative to the repository root).

| Table | Contents |
|---|---|
| `files` | `path`, `language`, `hash`, `size`, `entity_count`, `indexed_at` — drives incremental reindexing |
| `entities` | `id`, `type`, `name`, `qualified_name`, `file_path`, `start_line`/`end_line`, `signature`, `docstring`, `source_code`, `embedding`, `community_id` |
| `relations` | `source_id`, `target_id`, `type`, `weight` |
| `communities` | `id`, `level`, `name`, `summary`, `member_count`, `parent_id` |

Entity IDs follow the form `<absolute-path>::<name>::<line>`, which is what the `entity_id` argument of the query tools expects.

### Configuration

`Config` resolves from environment variables and an optional TOML file:

| Env var | Effect |
|---|---|
| `CODEGRAPH_REPO_PATH` | Repository root |
| `CODEGRAPH_DB_PATH` | Database path |
| `CODEGRAPH_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `CODEGRAPH_CACHE_ENABLED` | `true` / `false` |

Anything else (`languages`, `llm_enabled`, `embedding_model`, …) has no environment-variable path: `index` exposes no CLI flags for them, and `Config` offers only a TOML loader and direct construction.

## What The Index Of This Repo Actually Contains

Measured after `index --full` on this workspace. Counts drift with every reindex — including this repo's own diagnostic scripts under `.scratch/`, which get indexed too.

| Metric | Value |
|---|---|
| Files | 124 |
| Entities | 1066 |
| Communities | 25 |
| Languages | python 102, javascript 22 |

Relation mix: `contains` 942, `calls` 5313, `imports` 415, `inherits` 10.

### Four caveats that materially affect result quality, most severe first.

**1. Every relational query except containment is inert.** The language extractors emit edge targets as symbolic placeholders — `unresolved::self.ensure_layout` for calls and inheritance, `module::sqlite3` for imports — and **nothing ever rewrites them into entity IDs**. A `resolve_entity_id()` helper exists in `core/graph.py`, but it is called only at *query* time to resolve the caller's argument; there is no indexing-time resolution pass. Measured after a fresh `index --full`:

| Relation | Rows | Resolve to a real entity |
|---|---|---|
| `contains` | 942 | 942 (100%) |
| `calls` | 5313 | **0 (0%)** |
| `imports` | 415 | **0 (0%)** |
| `inherits` | 10 | **0 (0%)** |

The consequence is not degradation but a guaranteed empty result. `find_callers` and `find_callees` join on an exact `r.target_id = <resolved entity id>`; with no resolved `calls` edge, that join can never match, so both return `[]` for **every possible input**. `find_implementations` traverses `inherits` and `find_dependencies` traverses `imports`/`inherits`, so they are equally inert — `find_dependencies` returns the entity itself with an empty `relations` list.

`index --full` does not repair this. The failure is in how edges are stored, not in a stale snapshot, so no reindex or configuration change fixes it. Verified working on this index: `query_codebase`, `analyze_module_structure`, and `read_file_content`.

**2. Gitignored scratch content dominates the graph.** File discovery is *not* driven by `Config.parser.exclude_patterns` — that field is dead configuration. The indexer hardcodes its exclusions and does not read `.gitignore`:

```python
# codegraph_mcp/core/indexer.py
exclude_dirs = {
    ".git", "node_modules", "__pycache__", "venv",
    ".venv", "target", "dist", "build", ".codegraph",
}
for path in repo_path.rglob("*"):
    if any(ex in path.parts for ex in exclude_dirs):
        continue
    if path.suffix.lower() in supported_extensions:
        files.append(path)
```

`.scratch` is absent from that set, so the gitignored agent-config export is indexed as if it were project code:

| Area | Indexed files |
|---|---|
| `.scratch/` (gitignored) | **65 of 124 (52%)** |
| `app/` (runtime) | 14 |
| `tests/` + `workbench/` | 16 |
| `design-demos/`, `docs/` | 0 |

That is **365 of 1066 entities (34%)** — and 18 of the 22 "javascript" files — coming from `.scratch/agent-config-export/`, not from the workbench. Community detection, `global_search`, and any "explain the codebase" query are therefore partly describing third-party skill code.

Because `exclude_dirs` is hardcoded there is no configuration workaround: the only reliable fix is to remove or relocate `.scratch/` before a **full** reindex, or to index a filtered copy of the repo.

**3. No embeddings were produced.** `embedding` is `NULL` for all 1066 entities. The semantic layer expects `sentence-transformers/all-MiniLM-L6-v2`, which is not installed in the venv (only `numpy` is). Vector-backed similarity is therefore inert. This is independent of the unresolved relations in caveat 1 — that failure does not depend on embeddings, and installing the model would not repair it.

**4. No community summaries.** `summary` is empty for all 25 communities, because `semantic.llm_enabled` defaults to `false` and no LLM API key is configured. Community detection itself succeeded (25 communities, up to 315 members), but `global_search` has no summaries to search — expect it to behave as a plain community listing rather than GraphRAG synthesis. Enabling it requires an LLM provider and a TOML config, not an environment variable.

## Practical Notes For This Repo

- **Always invoke the venv executable by absolute path.** `anaconda3\Scripts\codegraph-mcp.exe` is the broken copy.
- **Reindex after structural edits.** The graph is a snapshot; `watch` or a manual `index --incremental` keeps it current. A stale graph silently answers from old code.
- **No self-indexing.** `.codegraph` is in the hardcoded exclusion set, so the database never indexes itself.
- **`stats` is cheap and non-invasive** — use it to confirm what the graph currently believes before trusting a query result.
- **`execute_shell_command` is one of the exposed tools.** It runs shell commands and does not add capability beyond the agent's own shell tool, but it is a second execution path worth knowing about.
- **Pass absolute paths.** `entity_id` and `file_path` arguments are matched against the absolute paths stored in the index. A relative path returns an empty result rather than an error — `analyze_module_structure` with `app/backend/storage.py` gave `entities: []`, while the absolute path returned the full class and method outline.
- **Use the tools that can actually succeed.** `query_codebase` locates an entity, `read_file_content` returns its source, `analyze_module_structure` gives a file outline. Do not spend turns on `find_callers`, `find_callees`, `find_dependencies`, `find_implementations`, or `get_code_snippet` — per caveat 1 they cannot return data on any index this build produces.
- **Treat graph answers as navigation, not verification.** Entity IDs and line numbers come from the index, which may predate the working tree. Confirm against the actual file before asserting a fact.

## Uninstall

```powershell
# Remove the DSH registration: delete the `mcp-codegraph` insert block from
#   C:\Users\yangc\.dsh\profiles\web\cordis.patch.yml
# then restart DSH.

# Remove the tool itself:
Remove-Item "C:\Users\yangc\.codegraph-venv" -Recurse -Force

# Remove the per-repo graph:
Remove-Item "<repo>\.codegraph" -Recurse -Force
```

Removing only the DSH block leaves the executable and any existing graph usable from the CLI.

## Upstream References

- Repository: <https://github.com/nahisaho/CodeGraphMCPServer>
- MCP specification: <https://modelcontextprotocol.io>
- MCP Python SDK v1 → v2 migration (source of the `list_tools` break): <https://py.sdk.modelcontextprotocol.io/v2/migration/>
- License: MIT
- Local probe and fact-collection scripts: `.scratch/probe_codegraph_mcp.py`, `.scratch/codegraph_facts.py`, `.scratch/codegraph_scope.py`, `.scratch/codegraph_resolve.py` (relation resolution rates)
