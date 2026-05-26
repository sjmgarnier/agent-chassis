# Chassis — Plan 3: MCP Server

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the chassis MCP server for Claude Desktop: a Python process that exposes a `chassis/load` prompt and a `chassis_load_components` tool, both backed by the chassis core library. In hard-gate mode, the tool presents matched component names for user confirmation before returning their content.

**Architecture:** A single Python MCP server (`chassis/mcp/server.py`) uses the `mcp` SDK and imports directly from the chassis core library (Plan 1). It exposes one prompt (invoked at conversation start) and one tool (callable mid-conversation). Gate behaviour is handled within the tool handler: ungated components are returned immediately, gated components are listed and the user is asked to confirm. Session state is shared with the hook path via `.chassis/session.json`.

**Tech Stack:** Python 3.9+, `mcp` SDK (Anthropic), chassis core library (Plan 1)

**Prerequisite:** Plan 1 (Core Library) must be complete.

---

## File Map

| File | Responsibility |
|---|---|
| `chassis/mcp/__init__.py` | Package marker |
| `chassis/mcp/server.py` | MCP server entry point: registers prompt and tool, starts stdio transport |
| `chassis/mcp/handlers.py` | Prompt and tool handler logic (separated for testability) |
| `tests/test_mcp/__init__.py` | Package marker |
| `tests/test_mcp/test_handlers.py` | Unit tests for handler logic |

---

## Task 1: Add MCP Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `mcp` to a new `mcp` optional extra**

In `pyproject.toml`, add:

```toml
[project.optional-dependencies]
embeddings = [
    "fastembed>=0.3",
    "numpy>=1.24",
]
mcp = [
    "mcp>=1.0",
]

[project.scripts]
chassis = "chassis.__main__:main"
chassis-mcp = "chassis.mcp.server:main"
```

- [ ] **Step 2: Install the extra**

```bash
pip install -e ".[mcp]"
```

- [ ] **Step 3: Verify import**

```bash
python3 -c "import mcp; print(mcp.__version__)"
```

Expected: a version string, no error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add mcp optional dependency"
```

---

## Task 2: Handler Logic

**Files:**
- Create: `chassis/mcp/__init__.py`
- Create: `chassis/mcp/handlers.py`
- Create: `tests/test_mcp/__init__.py`
- Create: `tests/test_mcp/test_handlers.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mcp/test_handlers.py
import pytest
from pathlib import Path
from tests.conftest import write_component
from chassis.mcp.handlers import handle_load


def test_returns_ungated_component_body(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    result = handle_load("git commit my changes", project_root=project_root)
    assert result["type"] == "content"
    assert "Git instructions" in result["text"]


def test_returns_gated_component_as_confirmation_request(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=True, body="Secret")
    result = handle_load("git commit", project_root=project_root)
    assert result["type"] == "gate"
    assert "git" in result["pending"]
    assert "Secret" not in result["text"]


def test_returns_empty_on_no_match(home_dir, project_root):
    result = handle_load("unrelated topic about lunch", project_root=project_root)
    assert result["type"] == "empty"


def test_global_gate_overrides_component(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=False, body="Instructions")
    (home_dir / ".chassis" / "config.toml").write_text("[gate]\nenabled = true\n")
    result = handle_load("git commit", project_root=project_root)
    assert result["type"] == "gate"


def test_skips_already_injected(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    handle_load("git commit", project_root=project_root)
    result = handle_load("git commit again", project_root=project_root)
    assert result["type"] == "empty"
```

- [ ] **Step 2: Run to verify they fail**

```bash
mkdir -p tests/test_mcp && touch tests/test_mcp/__init__.py
pytest tests/test_mcp/test_handlers.py -v
```

Expected: `ImportError: cannot import name 'handle_load'`

- [ ] **Step 3: Create `chassis/mcp/__init__.py`**

Empty file.

- [ ] **Step 4: Create `chassis/mcp/handlers.py`**

```python
from pathlib import Path
from typing import Optional

from ..config import load_config
from ..selector import select
from ..session import load_session, mark_injected, save_session, should_inject


def handle_load(prompt: str, project_root: Optional[Path] = None) -> dict:
    """
    Run the selector for the given prompt and return a structured result.

    Return types:
    - {"type": "content", "text": "..."}  — ungated components ready to inject
    - {"type": "gate", "text": "...", "pending": ["name1", ...]}  — gated, needs user approval
    - {"type": "empty"}  — no matches or all already injected
    """
    if project_root is None:
        project_root = Path.cwd()

    config = load_config(project_root)

    try:
        results = select(prompt, project_root)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("selector failed")
        return {"type": "empty"}

    session = load_session(project_root)
    to_inject = [r for r in results if should_inject(r.component.name, session)]

    if not to_inject:
        return {"type": "empty"}

    gated = [r for r in to_inject if r.requires_gate]
    ungated = [r for r in to_inject if not r.requires_gate]

    parts = []
    for result in ungated:
        parts.append(result.component.body)
        session = mark_injected(result.component.name, session)

    save_session(session, project_root)

    if gated and not ungated:
        names = [r.component.name for r in gated]
        text = (
            f"[chassis] The following components matched but require your approval "
            f"before loading: {', '.join(names)}. "
            f"Reply 'yes' to load them or 'no' to skip."
        )
        return {"type": "gate", "text": text, "pending": names}

    if gated and ungated:
        names = [r.component.name for r in gated]
        gate_notice = (
            f"\n\n[chassis] Additional components require approval: {', '.join(names)}. "
            f"Ask the user if they should be loaded."
        )
        parts.append(gate_notice)

    if config.notify_enabled and ungated:
        loaded_names = ", ".join(r.component.name for r in ungated)
        header = f"[chassis] Loading: {loaded_names}\n\n"
    else:
        header = ""

    return {"type": "content", "text": header + "\n\n".join(parts)}
```

- [ ] **Step 5: Run to verify tests pass**

```bash
pytest tests/test_mcp/test_handlers.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add chassis/mcp/__init__.py chassis/mcp/handlers.py tests/test_mcp/__init__.py tests/test_mcp/test_handlers.py
git commit -m "feat: add MCP handler logic"
```

---

## Task 3: MCP Server

**Files:**
- Create: `chassis/mcp/server.py`

- [ ] **Step 1: Create `chassis/mcp/server.py`**

```python
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .handlers import handle_load

app = Server("chassis")


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="chassis/load",
            description="Load chassis instruction components matching the current context",
            arguments=[
                types.PromptArgument(
                    name="prompt",
                    description="The user's message to match components against",
                    required=True,
                )
            ],
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> types.GetPromptResult:
    if name != "chassis/load":
        raise ValueError(f"Unknown prompt: {name}")

    prompt_text = (arguments or {}).get("prompt", "")
    result = handle_load(prompt_text, project_root=Path.cwd())

    if result["type"] == "empty":
        content = "[chassis] No matching components for this context."
    else:
        content = result["text"]

    return types.GetPromptResult(
        description="Chassis component instructions",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=content),
            )
        ],
    )


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="chassis_load_components",
            description="Load chassis instruction components for the current prompt. Call this when context has shifted and you need fresh instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The current user prompt to match components against",
                    }
                },
                "required": ["prompt"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "chassis_load_components":
        raise ValueError(f"Unknown tool: {name}")

    prompt = arguments.get("prompt", "")
    result = handle_load(prompt, project_root=Path.cwd())

    if result["type"] == "empty":
        text = "[chassis] No matching components for this context."
    else:
        text = result["text"]

    return [types.TextContent(type="text", text=text)]


def main() -> None:
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the server starts without error**

```bash
echo '{}' | timeout 2 python -m chassis.mcp.server 2>&1 || true
```

Expected: no Python import errors (it will exit after 2 seconds due to `timeout`).

- [ ] **Step 3: Commit**

```bash
git add chassis/mcp/server.py
git commit -m "feat: add MCP server for Claude Desktop"
```

---

## Task 4: Claude Desktop Registration

**Files:**
- Create: `hooks/register-claude-desktop.sh`

- [ ] **Step 1: Create `hooks/register-claude-desktop.sh`**

This script adds the chassis MCP server to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS path).

```bash
#!/usr/bin/env bash
# register-claude-desktop.sh — register chassis MCP server with Claude Desktop
set -euo pipefail

# Resolve chassis-mcp entry point
if command -v chassis-mcp &>/dev/null; then
  MCP_CMD="chassis-mcp"
elif [ -x "$HOME/.chassis/.venv/bin/chassis-mcp" ]; then
  MCP_CMD="$HOME/.chassis/.venv/bin/chassis-mcp"
else
  echo "Error: chassis-mcp command not found. Is chassis installed?" >&2
  exit 1
fi

# Claude Desktop config path (macOS)
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

mkdir -p "$(dirname "$CONFIG")"

python3 - "$CONFIG" "$MCP_CMD" <<'PYEOF'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
mcp_cmd = sys.argv[2]

if config_path.exists():
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        config = {}
else:
    config = {}

servers = config.setdefault("mcpServers", {})

if "chassis" in servers:
    print("chassis MCP server already registered — no changes made.")
else:
    servers["chassis"] = {
        "command": mcp_cmd,
        "args": []
    }
    config_path.write_text(json.dumps(config, indent=2))
    print(f"Registered chassis MCP server in {config_path}")
    print("Restart Claude Desktop to activate.")
PYEOF
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x hooks/register-claude-desktop.sh
```

- [ ] **Step 3: Test registration**

```bash
bash hooks/register-claude-desktop.sh
```

Expected: confirmation message and the entry in `~/Library/Application Support/Claude/claude_desktop_config.json`.

- [ ] **Step 4: Verify idempotency**

```bash
bash hooks/register-claude-desktop.sh
```

Expected: `chassis MCP server already registered — no changes made.`

- [ ] **Step 5: Commit**

```bash
git add hooks/register-claude-desktop.sh
git commit -m "feat: add Claude Desktop MCP registration script"
```

---

## Task 5: Full Test Suite Check

- [ ] **Step 1: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass (embedder tests skip if fastembed not installed).

- [ ] **Step 2: Manually verify end-to-end with Claude Desktop**

1. Register the MCP server: `bash hooks/register-claude-desktop.sh`
2. Add a test component to `~/.chassis/components/COMPONENT-test.md`:

```markdown
---
name: test-component
description: A test component for verifying chassis works
gate: false
triggers:
  keywords: [chassis, test]
---

# Test Component
Chassis is working correctly.
```

3. Restart Claude Desktop.
4. Start a new conversation and use the `chassis/load` prompt with prompt text `chassis test`.
5. Verify "Chassis is working correctly." appears in the injected context.
