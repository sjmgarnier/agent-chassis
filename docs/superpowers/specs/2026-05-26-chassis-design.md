# Chassis — Design Spec

**Date:** 2026-05-26  
**Status:** Approved

---

## What Is Chassis?

Chassis is a composable agent configuration system. Instead of a monolithic `CLAUDE.md` / `AGENTS.md` that accumulates all context-specific instructions, configuration is split into a minimal stable base and modular instruction files (components) that are injected on demand based on the incoming prompt.

The name comes from the chassis analogy: a permanent structural base that functional modules bolt into. Each module has a distinct purpose. You only mount what the task requires.

---

## Target Platforms

| Platform | Integration | Injection model |
|---|---|---|
| Claude Code | `UserPromptSubmit` hook (bash shim) | Push — before agent sees prompt |
| OpenCode | Equivalent hook (bash shim) — hook API to be confirmed | Push — before agent sees prompt |
| Claude Desktop | MCP server (prompt + tool) | Pull — front-loaded at conversation start |

Push is preferred: the agent can't forget to load context, and instructions are available from the first token. Claude Desktop has no hook mechanism, so MCP prompts are the closest equivalent — an accepted trade-off.

---

## Architecture Overview

Four distinct units:

1. **Core library** (`chassis` Python package) — the selector engine. Loads and merges components from global and project directories, runs matching, applies gate logic, returns ordered results.
2. **Hook shims** (bash scripts) — thin entry points for Claude Code and OpenCode. Call `python -m chassis select "$PROMPT"` and print output to stdout.
3. **MCP server** (Python, reuses core library) — serves Claude Desktop via a prompt endpoint and a callable tool.
4. **Session state** (`.chassis/session.json`) — tracks injected components per session to avoid redundant re-injection.

---

## Components

### Structure

Each component is a markdown file with YAML frontmatter:

```yaml
---
name: git-workflow
description: Git workflow, commit conventions, and PR etiquette
gate: false
triggers:
  keywords: [git, commit, branch, PR, merge, push, rebase]
  topics: [version_control, code_review]
---

# Git Workflow
...instructions...
```

- `name` — unique identifier; used for deduplication and override resolution.
- `description` — semantic summary; used by the embedding matcher (Phase 2).
- `gate` — optional, defaults to `false`. If `true`, requires user approval before injection.
- `triggers.keywords` — substring-matched against the incoming prompt (case-insensitive).
- `triggers.topics` — categorical tags for coarser matching.

Files must be named `COMPONENT-<name>.md` to be picked up by the loader.

### Storage

Components are loaded from two locations in order:

1. `~/.chassis/components/` — global, shared across all projects on the machine.
2. `<project-root>/.components/` — project-local.

If a project component shares a `name` with a global one, the project version replaces it entirely. No partial merging — one file, one source of truth.

---

## Selector Engine

### Phase 1 — Keyword matching (always available)

The selector lowercases the incoming prompt and checks it against each component's `keywords` and `topics` lists using substring matching (`keyword in prompt.lower()`). This catches common variations ("committing" matches "commit", "branches" matches "branch") without extra dependencies.

Components are ranked by number of matched terms, ties broken alphabetically by name.

### Phase 2 — Embedding matching (optional)

When `fastembed` is installed and configured, the selector embeds the prompt and compares it against pre-computed embeddings of each component's `description` field. Components with cosine similarity above a configurable threshold (default `0.5`) are included, ranked by score.

Phase 2 is tried first when available. Phase 1 is the fallback. The active phase is recorded in session state for debugging.

Keywords are not included in embeddings — they are Phase 1's job. Phase 2 embeds descriptions only, keeping the two phases semantically clean.

### Gate logic

Applied after matching, before injection:

1. If global `gate: true` → all matched components require approval, regardless of their own `gate` field.
2. If global `gate` is `false` or unset → each component's own `gate` field decides.
3. Components with `gate: false` (the default) are injected silently (with optional notification).

The selector returns an ordered list of `(component_name, body, requires_gate)` tuples consumed by the hook shim or MCP server.

### Notification

When `notify: true` (default), a brief line is printed to stderr on the hook path, or surfaced as a note on the MCP path:

```
[chassis] Loading: git-workflow, r-packaging
```

Users who find this noisy can set `notify: false` in config.

---

## Platform Integration

### Claude Code & OpenCode — Hook shims

A bash script registered as a `UserPromptSubmit` hook calls:

```bash
python -m chassis select "$PROMPT"
```

Behaviour by mode:

- **No gate, notify on:** prints `[chassis] Loading: <names>` to stderr; prints component bodies to stdout (injected into context).
- **Gate required:** prints a preamble to stdout listing matched components and inviting the agent to surface the choice to the user before proceeding. Does not inject component content directly.
- **No match:** prints nothing.

### Claude Desktop — MCP server

Exposes:

- **Prompt** (`chassis/load`) — primary injection mechanism. Returns matched component bodies for the initial user message at conversation start.
- **Tool** (`chassis_load_components`) — callable mid-conversation when context shifts.

Gate behaviour on Claude Desktop: the MCP tool presents matched component names and waits for explicit user confirmation before returning their content.

### Session state

Both the shim and MCP server read and write `.chassis/session.json` in the project root (falling back to `~/.chassis/session.json` when no project root is detected).

- Components already injected this session are skipped.
- On suspected compaction (message history length drops >50% between turns), all components are re-injected to restore context.
- Session state is cleared on session start.

---

## Configuration

All configuration lives in TOML files, following the same two-level pattern as components:

- `~/.chassis/config.toml` — global defaults
- `<project-root>/.chassis/config.toml` — project overrides

Key options:

```toml
[selector]
phase = 2           # 1 = keyword only, 2 = embeddings (requires fastembed)
threshold = 0.5     # cosine similarity threshold for Phase 2

[gate]
enabled = false     # true = always ask, overrides per-component gate field

[notify]
enabled = true      # show [chassis] loading notifications
```

---

## Installation

### Bootstrap script

```bash
curl -fsSL https://chassis.sh/install | bash
```

Steps (interactive):

1. **Check Python** — verifies Python 3.9+ is available; exits with a clear message if not.
2. **Install package** — tries `pipx install chassis` first (isolated, no venv management needed). If pipx is unavailable, creates `~/.chassis/.venv/` and installs there. Hook shims and MCP server reference the resolved Python path.
3. **Embedding support** — asks: *"Do you want embedding-based matching? (slower but more accurate)"* — runs `pipx inject chassis fastembed` or equivalent.
4. **Configure gate** — asks: *"Require approval before loading components?"* — writes to `~/.chassis/config.toml`.
5. **Configure notify** — asks: *"Show a notification when components are loaded?"* — adds to config.
6. **Detect & select platforms** — presents detected platforms (Claude Code, Claude Desktop, OpenCode) with a toggle prompt; wires up only the ones the user selects.
7. **Create global components dir** — `mkdir -p ~/.chassis/components/` with a placeholder `COMPONENT-example.md`.
8. **Confirm** — prints a summary of what was configured and where.

A `chassis install` CLI command re-runs the same flow for users who install via pip or pipx directly.

### `chassis doctor`

Checks and reports:

- Python environment and chassis version
- Hook registration for each configured platform
- MCP server reachability (Claude Desktop)
- Global and project component directories
- Active selector phase and fastembed availability

Doubles as a smoke test after install or after a platform update.

---

## Error Handling

Chassis must never break an agent session. All errors are non-fatal:

| Failure | Behaviour |
|---|---|
| Selector raises an exception | Logs to `~/.chassis/chassis.log`, injects nothing, session continues |
| Component has malformed frontmatter | Skips that component, logs a warning, continues with the rest |
| `fastembed` unavailable but Phase 2 configured | Falls back to Phase 1 silently, logs once per session |
| Session state unreadable or corrupt | Resets to empty state, logs a warning |
| Hook shim: Python not found | Shim exits 0 (no output); `chassis doctor` surfaces the issue |

---

## Testing

Three layers:

- **Unit tests** — selector logic in isolation: keyword matching, embedding matching, gate logic, component loading and merging. No platform dependencies.
- **Integration tests** — full pipeline with fixture components: given a prompt, assert correct components are selected with correct gate flags.
- **Platform smoke tests** — `chassis doctor` verifies hook registration, MCP server reachability, Python environment, and component directories. Intended for users post-install, not CI.
