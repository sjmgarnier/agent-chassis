# Chassis — Plan 2: Hook Shims

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create bash hook shims that integrate the chassis core library with Claude Code and OpenCode via their `UserPromptSubmit` hook mechanisms, enabling push-based component injection before the agent sees each prompt.

**Architecture:** A single parameterised bash shim reads the prompt from hook-supplied JSON on stdin, calls `python -m chassis select`, and prints matched component content to stdout (injected into agent context). A separate registration script wires the shim into Claude Code's `settings.json`. OpenCode registration follows the same pattern once its hook API is confirmed.

**Tech Stack:** Bash, Python 3.9+ (via chassis package from Plan 1), jq (for JSON parsing in the shim), Claude Code `settings.json`

**Prerequisite:** Plan 1 (Core Library) must be complete and `chassis` installed.

---

## File Map

| File | Responsibility |
|---|---|
| `hooks/chassis-hook.sh` | The shim: reads prompt from stdin JSON, calls chassis, prints output |
| `hooks/register-claude-code.sh` | Registers the shim in `~/.claude/settings.json` |
| `hooks/register-opencode.sh` | Registers the shim for OpenCode (API to be confirmed before implementing) |
| `tests/hooks/test_hook.sh` | Bash integration test for the shim |

---

## Task 1: Investigate Claude Code Hook Input Format

**Files:**
- No files created — research task

- [ ] **Step 1: Check Claude Code hook documentation**

Open `~/.claude/settings.json` (if it exists) and inspect any existing `hooks` configuration. Also check [Claude Code docs on hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) for the exact stdin format and environment variables provided to `UserPromptSubmit` hooks.

Verify:
- Is the prompt passed as JSON on stdin, or as an environment variable?
- What is the JSON schema? (e.g. `{"prompt": "...", "session_id": "..."}`)
- Is stdout injected verbatim into context, or wrapped?

- [ ] **Step 2: Record findings**

Add a comment block at the top of `hooks/chassis-hook.sh` (created in Task 2) documenting the confirmed input format. If the format differs from the plan's assumption (`{"prompt": "..."}` on stdin), update Task 2 accordingly before implementing.

---

## Task 2: The Hook Shim

**Files:**
- Create: `hooks/chassis-hook.sh`

- [ ] **Step 1: Write a failing integration test**

```bash
# tests/hooks/test_hook.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHIM="$SCRIPT_DIR/../../hooks/chassis-hook.sh"
TMPDIR_TEST=$(mktemp -d)

cleanup() { rm -rf "$TMPDIR_TEST"; }
trap cleanup EXIT

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

# Set up a fake HOME with one component
export HOME="$TMPDIR_TEST/home"
mkdir -p "$HOME/.chassis/components"
cat > "$HOME/.chassis/components/COMPONENT-git.md" <<'EOF'
---
name: git-workflow
description: Git workflow
gate: false
triggers:
  keywords: [git, commit]
---

# Git Workflow
Use conventional commits.
EOF

# Test 1: matching prompt produces output
INPUT='{"prompt": "please git commit my changes"}'
OUTPUT=$(echo "$INPUT" | bash "$SHIM" 2>/dev/null)
if echo "$OUTPUT" | grep -q "Use conventional commits"; then
  pass "matching prompt injects component body"
else
  fail "matching prompt should inject component body, got: $OUTPUT"
fi

# Test 2: non-matching prompt produces no output
INPUT='{"prompt": "unrelated topic about lunch"}'
OUTPUT=$(echo "$INPUT" | bash "$SHIM" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "non-matching prompt produces no output"
else
  fail "non-matching prompt should produce no output, got: $OUTPUT"
fi

echo "All hook tests passed."
```

- [ ] **Step 2: Run to verify the test fails (shim doesn't exist yet)**

```bash
mkdir -p tests/hooks
cp /dev/null tests/hooks/test_hook.sh  # placeholder so the path exists
bash tests/hooks/test_hook.sh 2>&1 || true
```

Expected: error that `hooks/chassis-hook.sh` does not exist.

- [ ] **Step 3: Create `hooks/chassis-hook.sh`**

```bash
#!/usr/bin/env bash
# chassis-hook.sh — UserPromptSubmit hook shim for Claude Code and OpenCode
#
# Input:  JSON on stdin, e.g. {"prompt": "the user's message"}
# Output: matched component bodies on stdout (injected into agent context)
#         notification on stderr
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

# Extract prompt from stdin JSON
# Falls back to empty string if jq is absent or parsing fails
if command -v jq &>/dev/null; then
  PROMPT=$(jq -r '.prompt // empty' 2>/dev/null) || PROMPT=""
else
  # Minimal extraction without jq: grab value of "prompt" key
  PROMPT=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('prompt', ''))
except Exception:
    pass
" 2>/dev/null) || PROMPT=""
fi

if [ -z "$PROMPT" ]; then
  exit 0
fi

# Call the selector and print output to stdout
$CHASSIS_CMD select "$PROMPT"
```

- [ ] **Step 4: Make it executable**

```bash
chmod +x hooks/chassis-hook.sh
```

- [ ] **Step 5: Write the actual test file**

Replace the placeholder created in Step 2 with the full test from Step 1.

- [ ] **Step 6: Run the test**

```bash
bash tests/hooks/test_hook.sh
```

Expected:
```
PASS: matching prompt injects component body
PASS: non-matching prompt produces no output
All hook tests passed.
```

- [ ] **Step 7: Commit**

```bash
git add hooks/chassis-hook.sh tests/hooks/test_hook.sh
git commit -m "feat: add UserPromptSubmit hook shim"
```

---

## Task 3: Claude Code Registration Script

**Files:**
- Create: `hooks/register-claude-code.sh`

- [ ] **Step 1: Create `hooks/register-claude-code.sh`**

This script adds the chassis hook to `~/.claude/settings.json`. It reads the existing file (if any), merges in the hook entry, and writes it back. Uses Python for JSON manipulation to avoid `jq` as a hard dependency.

```bash
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
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x hooks/register-claude-code.sh
```

- [ ] **Step 3: Test registration manually**

```bash
# Back up settings first if they exist
[ -f ~/.claude/settings.json ] && cp ~/.claude/settings.json ~/.claude/settings.json.bak

bash hooks/register-claude-code.sh

# Verify the hook appears in settings
python3 -c "
import json
from pathlib import Path
s = json.loads(Path('$HOME/.claude/settings.json').read_text())
hooks = s.get('hooks', {}).get('UserPromptSubmit', [])
print('Hook entries:', json.dumps(hooks, indent=2))
"
```

Expected: the shim path appears under `UserPromptSubmit`.

- [ ] **Step 4: Run registration a second time to verify idempotency**

```bash
bash hooks/register-claude-code.sh
```

Expected: `chassis hook already registered — no changes made.`

- [ ] **Step 5: Commit**

```bash
git add hooks/register-claude-code.sh
git commit -m "feat: add Claude Code hook registration script"
```

---

## Task 4: OpenCode Registration (Stub)

**Files:**
- Create: `hooks/register-opencode.sh`

- [ ] **Step 1: Create stub pending API confirmation**

```bash
#!/usr/bin/env bash
# register-opencode.sh — register chassis hook with OpenCode
#
# STATUS: stub — OpenCode hook API not yet confirmed.
# See: https://github.com/sst/opencode (check docs/hooks or similar)
# Once the hook mechanism is confirmed, implement analogously to
# hooks/register-claude-code.sh.
set -euo pipefail

echo "OpenCode hook registration is not yet implemented." >&2
echo "Once the OpenCode hook API is confirmed, update this script." >&2
exit 1
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x hooks/register-opencode.sh
```

- [ ] **Step 3: Commit**

```bash
git add hooks/register-opencode.sh
git commit -m "chore: stub OpenCode registration (pending API confirmation)"
```
