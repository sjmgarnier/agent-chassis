#!/usr/bin/env bash
# install.sh — chassis bootstrap installer
# Usage: curl -fsSL https://chassis.sh/install | bash
set -euo pipefail

CHASSIS_HOME="$HOME/.chassis"
CHASSIS_VENV="$CHASSIS_HOME/.venv"
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-install.sh}")" 2>/dev/null && pwd || echo "$CHASSIS_HOME")"

header() { echo; echo "==> $*"; }
info()   { echo "    $*"; }
ask()    { printf "    %s [y/N] " "$*"; read -r REPLY; [[ "$REPLY" =~ ^[Yy]$ ]]; }

# ── 1. Check Python ─────────────────────────────────────────────────────────
header "Checking Python"

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Install Python 3.9+ and retry." >&2
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
  echo "Error: Python 3.9+ required (found $PY_VERSION)." >&2
  exit 1
fi

info "Found Python $PY_VERSION"

# ── 2. Install chassis ───────────────────────────────────────────────────────
header "Installing chassis"

INSTALL_EXTRAS="mcp"
USE_EMBEDDINGS=false

if ask "Enable embedding-based matching? (slower but more accurate, ~80 MB download on first use)"; then
  INSTALL_EXTRAS="$INSTALL_EXTRAS,embeddings"
  USE_EMBEDDINGS=true
fi

if command -v pipx &>/dev/null; then
  info "Using pipx"
  pipx install "chassis[$INSTALL_EXTRAS]" --force
  if $USE_EMBEDDINGS; then
    pipx inject chassis fastembed numpy
  fi
  CHASSIS_CMD="$(pipx environment --value PIPX_LOCAL_VENVS)/chassis/bin/chassis"
else
  info "pipx not found — creating virtualenv at $CHASSIS_VENV"
  python3 -m venv "$CHASSIS_VENV"
  "$CHASSIS_VENV/bin/pip" install --quiet "chassis[$INSTALL_EXTRAS]"
  CHASSIS_CMD="$CHASSIS_VENV/bin/chassis"
fi

info "chassis installed at: $CHASSIS_CMD"

# ── 3. Configure gate ────────────────────────────────────────────────────────
header "Configuration"

mkdir -p "$CHASSIS_HOME"
CONFIG_FILE="$CHASSIS_HOME/config.toml"

GATE_ENABLED="false"
if ask "Require approval before loading components? (can also be set per-component)"; then
  GATE_ENABLED="true"
fi

NOTIFY_ENABLED="true"
if ! ask "Show '[chassis] Loading: ...' notifications?"; then
  NOTIFY_ENABLED="false"
fi

SELECTOR_PHASE=1
if $USE_EMBEDDINGS; then
  SELECTOR_PHASE=2
fi

cat > "$CONFIG_FILE" <<TOML
[selector]
phase = $SELECTOR_PHASE
threshold = 0.5

[gate]
enabled = $GATE_ENABLED

[notify]
enabled = $NOTIFY_ENABLED
TOML

info "Config written to $CONFIG_FILE"

# ── 4. Create global components dir ─────────────────────────────────────────
COMP_DIR="$CHASSIS_HOME/components"
mkdir -p "$COMP_DIR"

if [ ! -f "$COMP_DIR/COMPONENT-example.md" ]; then
  cat > "$COMP_DIR/COMPONENT-example.md" <<'MD'
---
name: example
description: An example component — replace with your own
gate: false
triggers:
  keywords: [example, demo]
  topics: []
---

# Example Component

This is a placeholder. Replace with your own instructions.
MD
  info "Created example component at $COMP_DIR/COMPONENT-example.md"
fi

# ── 5. Detect and register platforms ────────────────────────────────────────
header "Platform registration"

DETECTED=()

# Claude Code
if [ -d "$HOME/.claude" ] || command -v claude &>/dev/null; then
  DETECTED+=("Claude Code")
fi

# Claude Desktop (macOS)
if [ -d "$HOME/Library/Application Support/Claude" ]; then
  DETECTED+=("Claude Desktop")
fi

# OpenCode
if command -v opencode &>/dev/null; then
  DETECTED+=("OpenCode")
fi

if [ ${#DETECTED[@]} -eq 0 ]; then
  info "No supported platforms detected. You can register manually later."
else
  info "Detected: ${DETECTED[*]}"
  echo
  echo "    Select platforms to configure (enter numbers separated by spaces):"
  for i in "${!DETECTED[@]}"; do
    echo "      $((i+1)). ${DETECTED[$i]}"
  done
  printf "    Your choice: "
  read -r CHOICES

  for CHOICE in $CHOICES; do
    IDX=$((CHOICE - 1))
    PLATFORM="${DETECTED[$IDX]:-}"
    case "$PLATFORM" in
      "Claude Code")
        if [ -f "$HOOKS_DIR/hooks/register-claude-code.sh" ]; then
          bash "$HOOKS_DIR/hooks/register-claude-code.sh" && info "Claude Code registered."
        else
          info "register-claude-code.sh not found — skipping."
        fi
        ;;
      "Claude Desktop")
        if [ -f "$HOOKS_DIR/hooks/register-claude-desktop.sh" ]; then
          bash "$HOOKS_DIR/hooks/register-claude-desktop.sh" && info "Claude Desktop registered."
        else
          info "register-claude-desktop.sh not found — skipping."
        fi
        ;;
      "OpenCode")
        info "OpenCode registration not yet implemented — skipping."
        ;;
    esac
  done
fi

# ── 6. Summary ───────────────────────────────────────────────────────────────
header "Done"
info "chassis installed and configured."
info "Run 'chassis doctor' to verify your setup."
info "Add components to $COMP_DIR"
info "Project-level components go in <project-root>/.components/COMPONENT-*.md"
echo
