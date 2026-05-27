#!/usr/bin/env bash
# register-opencode.sh — register chassis hook with OpenCode
#
# STATUS: not supported.
#
# OpenCode uses a TypeScript plugin API (@opencode-ai/plugin).  As of
# 2026-05, the public Hooks interface exposes only:
#   - experimental.session.compacting  (before compaction)
#   - experimental.compaction.autocontinue
#   - experimental.text.complete
#   - tool.definition
#
# None fire before each user message.  There is no per-prompt hook
# equivalent to Claude Code's UserPromptSubmit.
#
# Track issue #28695 for the proposed `prompt.submit` hook + session
# lifecycle context injection — that is the implementation that would
# make chassis work on OpenCode:
#   https://github.com/anomalyco/opencode/issues/28695
#
# When that lands, implement a TypeScript plugin here analogous to
# hooks/chassis-hook.sh: intercept prompt.submit, run `chassis select`
# against the prompt text, and prepend the result to the system array.
set -euo pipefail

echo "OpenCode is not yet supported by chassis." >&2
echo "Track https://github.com/anomalyco/opencode/issues/28695 for progress." >&2
exit 1
