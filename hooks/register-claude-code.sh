#!/usr/bin/env bash
# register-claude-code.sh — register chassis hook with Claude Code
set -euo pipefail

SHIM_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/chassis-hook.sh"
SETTINGS="$HOME/.claude/settings.json"

if [ ! -f "$SHIM_PATH" ]; then
  echo "Error: hook shim not found at $SHIM_PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "$SETTINGS")"

python3 - "$SETTINGS" "$SHIM_PATH" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
shim_path = sys.argv[2]

if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        settings = {}
else:
    settings = {}

hooks = settings.setdefault("hooks", {})
submit_hooks = hooks.setdefault("UserPromptSubmit", [])

# Check if already registered
already = any(
    h.get("command") == shim_path
    for entry in submit_hooks
    for h in entry.get("hooks", [])
)

if not already:
    submit_hooks.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": shim_path}]
    })
    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"Registered chassis hook in {settings_path}")
else:
    print("chassis hook already registered — no changes made.")
PYEOF
