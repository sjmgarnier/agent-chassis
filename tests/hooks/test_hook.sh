#!/usr/bin/env bash
# test_hook.sh — integration test for chassis-hook.sh
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
# Use full JSON format matching actual Claude Code hook input
INPUT='{"session_id":"test","cwd":"'"$TMPDIR_TEST"'","hook_event_name":"UserPromptSubmit","prompt":"please git commit my changes"}'
OUTPUT=$(printf '%s' "$INPUT" | bash "$SHIM" 2>/dev/null)
if echo "$OUTPUT" | grep -q "Use conventional commits"; then
  pass "matching prompt injects component body"
else
  fail "matching prompt should inject component body, got: $OUTPUT"
fi

# Test 2: non-matching prompt produces no output
INPUT='{"session_id":"test","cwd":"'"$TMPDIR_TEST"'","hook_event_name":"UserPromptSubmit","prompt":"unrelated topic about lunch"}'
OUTPUT=$(printf '%s' "$INPUT" | bash "$SHIM" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "non-matching prompt produces no output"
else
  fail "non-matching prompt should produce no output, got: $OUTPUT"
fi

# Test 3: empty prompt produces no output
INPUT='{"session_id":"test","cwd":"'"$TMPDIR_TEST"'","hook_event_name":"UserPromptSubmit","prompt":""}'
OUTPUT=$(printf '%s' "$INPUT" | bash "$SHIM" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "empty prompt produces no output"
else
  fail "empty prompt should produce no output, got: $OUTPUT"
fi

echo "All hook tests passed."
