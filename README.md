# agent-chassis

Push-based instruction injection for Claude Code, Claude Desktop, and OpenCode. Components are markdown files that get injected into the agent's context *before* it processes your prompt — automatically, on every turn, without the agent having to ask.

```
~/.chassis/components/
  COMPONENT-git.md       # injected when prompt mentions git, commit, branch…
  COMPONENT-r-pkg.md     # injected when prompt mentions devtools, roxygen…

<project>/.components/
  COMPONENT-git.md       # project-level override of the global git component
```

---

## Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/sjmgarnier/agent-chassis/main/install.sh)
```

The installer checks your Python version, installs chassis, writes `~/.chassis/config.toml`, and registers the hook for your platform.

**Manual install:**

```bash
pip install agent-chassis[mcp]                 # core + Claude Desktop MCP server
pip install agent-chassis[mcp,embeddings]      # + Phase 2 semantic matching (~80 MB)
```

---

## Quick start

### 1. Create a component

```markdown
---
name: git-workflow
description: Git commit conventions for this project
gate: false
triggers:
  keywords: [git, commit, branch, push]
  topics: [version control]
---

# Git Workflow

- Use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- Squash before merging
- Never force-push to main
```

Save as `~/.chassis/components/COMPONENT-git.md` (global) or `<project>/.components/COMPONENT-git.md` (project-specific).

### 2. Register the hook

**Claude Code:**
```bash
bash hooks/register-claude-code.sh
```

**Claude Desktop:**
```bash
bash hooks/register-claude-desktop.sh
```

### 3. Verify

```bash
chassis doctor
```

```
chassis doctor
========================================
  ✓  Python environment: 3.12.0
  ✓  Global components dir: /Users/you/.chassis/components (1 component)
  -  Project components dir: No project-level components (optional)
  ✓  Claude Code hook: /path/to/chassis-hook.sh
  -  fastembed (Phase 2): unavailable — run: pip install 'agent-chassis[embeddings]'
  ✓  chassis-mcp (Claude Desktop): chassis-mcp

All checks passed.
```

---

## Component format

```markdown
---
name: my-component           # required, unique identifier
description: What this does  # used for Phase 2 semantic matching
gate: false                  # true = ask user before injecting
triggers:
  keywords: [word1, word2]   # substring-matched against the prompt (case-insensitive)
  topics: [topic1]           # same matching, semantic grouping only
---

Your markdown instructions here.
```

**Search order:** Project-level (`.components/`) overrides global (`~/.chassis/components/`) by name.

---

## Configuration

`~/.chassis/config.toml` (global, created by the installer):

```toml
[selector]
phase = 1        # 1 = keyword matching, 2 = semantic (requires [embeddings])
threshold = 0.5  # cosine similarity threshold for Phase 2

[gate]
enabled = false  # true = require approval before loading any component

[notify]
enabled = true   # show "[chassis] Loading: <names>" in agent context
```

Project-level overrides: `<project>/.chassis/config.toml` — same format, merged over global.

**Gate behaviour:** `gate.enabled = true` overrides all per-component `gate:` settings — everything requires approval when the global gate is on.

---

## Platforms

| Platform | Mechanism | Notes |
|---|---|---|
| Claude Code | `UserPromptSubmit` hook | ✅ Fully automatic — components injected before every prompt |
| Claude Desktop | MCP `/chassis/load` slash command + `chassis_load_components` tool | ⚠️ Manual — user invokes `/chassis/load` before a task, or the model calls the tool |
| OpenCode | MCP `chassis_load_components` tool only (no slash command for MCP prompts) | ⚠️ Manual — model must call the tool explicitly; no automatic trigger |

Claude Code is the only platform where injection is truly push-based. On Claude Desktop and OpenCode, chassis components are available on demand but won't fire automatically on every turn.

---

## Phase 2: Semantic matching

```bash
pip install agent-chassis[embeddings]
```

Set `phase = 2` in your config. On first use, chassis downloads `BAAI/bge-small-en-v1.5` (~80 MB). Components are matched by cosine similarity between the prompt and each component's `description` field, rather than substring keywords.

---

## How it differs from skills

Both chassis and skills inject instructions into agent context. The key differences:

| | Skills | Chassis |
|---|---|---|
| **Trigger** | Agent decides to invoke | Hook fires automatically before every prompt |
| **Scope** | Universal workflow methodology | Your environment's specific conventions |
| **After compaction** | Lost — agent must re-invoke | Re-injected automatically on every prompt |
| **Authorship** | Shared, version-controlled | Personal, lives in `~/.chassis/` |

Skills are *how to approach a class of problem* — TDD, debugging, brainstorming. Chassis is *the rules for your specific environment* — this repo's commit format, this API's auth quirks, this project's testing patterns.

They complement each other: a session might load the TDD skill when you ask it to add a feature, while chassis has already injected your project's testing conventions and git workflow.

| Layer | Mechanism | What it carries |
|---|---|---|
| `CLAUDE.md` | Always loaded | Universal, stable rules |
| Skills | Agent-pull | Workflow methodology |
| Chassis | Hook-push | Domain-specific instructions |

---

## License

MIT — see [LICENSE](LICENSE)
