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
