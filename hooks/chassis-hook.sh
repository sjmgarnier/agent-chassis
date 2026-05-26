#!/usr/bin/env bash
# chassis-hook.sh — UserPromptSubmit hook shim for Claude Code and OpenCode
#
# Claude Code hook input format (UserPromptSubmit):
#   stdin JSON: {"session_id": "...", "cwd": "/project/root",
#                "hook_event_name": "UserPromptSubmit", "prompt": "...", ...}
#   stdout: plain text → injected as additional context before agent processes prompt
#   exit 0: allow prompt (with any stdout injected as context)
#   exit 2: block prompt (reason from stdout shown to user)
#
# This shim extracts "prompt" and "cwd" from stdin JSON, calls chassis select,
# and prints matched component bodies to stdout for injection.
#
# Requires: chassis Python package installed (via pipx or ~/.chassis/.venv)
set -euo pipefail

# Resolve the chassis Python entry point
if command -v chassis &>/dev/null; then
  CHASSIS_CMD="chassis"
elif [ -x "$HOME/.chassis/.venv/bin/chassis" ]; then
  CHASSIS_CMD="$HOME/.chassis/.venv/bin/chassis"
elif [ -x "$HOME/.chassis/.venv/bin/python" ]; then
  CHASSIS_CMD="$HOME/.chassis/.venv/bin/python -m chassis"
else
  # chassis not found — fail silently so the agent session is not interrupted
  exit 0
fi

# Read all stdin into a variable (can only read stdin once)
INPUT=$(cat)

# Extract prompt and cwd from stdin JSON
if command -v jq &>/dev/null; then
  PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null) || PROMPT=""
  CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || CWD=""
else
  # Minimal extraction without jq: use Python
  PROMPT=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('prompt', ''))
except Exception:
    pass
" 2>/dev/null) || PROMPT=""
  CWD=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('cwd', ''))
except Exception:
    pass
" 2>/dev/null) || CWD=""
fi

if [ -z "$PROMPT" ]; then
  exit 0
fi

# Change to the session's working directory so chassis finds project-level components
if [ -n "$CWD" ] && [ -d "$CWD" ]; then
  cd "$CWD"
fi

# Call the selector and print output to stdout (injected as context by Claude Code)
$CHASSIS_CMD select "$PROMPT"
