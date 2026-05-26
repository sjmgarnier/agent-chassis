#!/usr/bin/env bash
# register-opencode.sh — register chassis hook with OpenCode
#
# STATUS: not supported.
#
# OpenCode uses a TypeScript plugin API (@opencode-ai/plugin).  As of
# the last check (2026-05), the plugin system only exposes
# `experimental.session.compacting` — there is no pre-prompt hook
# equivalent to Claude Code's UserPromptSubmit that would allow
# chassis to inject component content before each user message.
#
# A PromptEditor API (prepend/append) exists in the v2 spec but is
# not yet shipped.  When it lands, a TypeScript plugin can be added
# here to replace this stub.
set -euo pipefail

echo "OpenCode is not yet supported by chassis." >&2
echo "OpenCode's plugin API does not yet expose a pre-prompt injection hook." >&2
echo "Track https://github.com/anomalyco/opencode for updates." >&2
exit 1
