# Chassis — Plan 4: Bootstrap & Doctor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `install.sh` bootstrap script for new users and the `chassis doctor` command for verifying a working installation. Together these give chassis a complete general-release installation story.

**Architecture:** `install.sh` is a standalone bash script (no chassis pre-installed) that walks the user through installation interactively: Python check, pipx/venv install, optional embeddings, gate/notify config, platform detection and selection, and registration. `chassis doctor` is a Python subcommand added to `chassis/__main__.py` that reads the same config and settings files and reports the health of each component (Python env, hooks, MCP server, component dirs).

**Tech Stack:** Bash (install.sh), Python 3.9+ (doctor command)

**Prerequisite:** Plans 1–3 must be complete.

---

## File Map

| File | Responsibility |
|---|---|
| `install.sh` | Standalone bootstrap: installs chassis and registers it with selected platforms |
| `chassis/doctor.py` | `chassis doctor` subcommand: checks and reports installation health |
| `tests/test_doctor.py` | Unit tests for doctor check functions |

---

## Task 1: `chassis doctor` Command

**Files:**
- Create: `chassis/doctor.py`
- Modify: `chassis/__main__.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_doctor.py
import pytest
from pathlib import Path
from chassis.doctor import (
    check_python_env,
    check_global_components_dir,
    check_project_components_dir,
    check_claude_code_hook,
)


def test_check_python_env_returns_ok():
    result = check_python_env()
    assert result["status"] == "ok"
    assert "version" in result


def test_check_global_components_dir_missing(home_dir, monkeypatch, tmp_path):
    # home_dir fixture sets Path.home() to a tmp home with .chassis/components already created
    # Remove it to simulate missing dir
    import shutil
    shutil.rmtree(home_dir / ".chassis" / "components")
    result = check_global_components_dir()
    assert result["status"] == "missing"


def test_check_global_components_dir_present(home_dir):
    result = check_global_components_dir()
    assert result["status"] == "ok"


def test_check_project_components_dir_missing(project_root):
    result = check_project_components_dir(project_root)
    assert result["status"] == "missing"


def test_check_project_components_dir_present(project_root):
    (project_root / ".components").mkdir(parents=True, exist_ok=True)
    result = check_project_components_dir(project_root)
    assert result["status"] == "ok"


def test_check_claude_code_hook_not_registered(home_dir, tmp_path):
    # No settings.json exists
    settings_path = tmp_path / "claude" / "settings.json"
    result = check_claude_code_hook(settings_path=settings_path)
    assert result["status"] == "missing"


def test_check_claude_code_hook_registered(home_dir, tmp_path):
    import json
    settings_path = tmp_path / "claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": "/some/path/chassis-hook.sh"}]}
            ]
        }
    }))
    result = check_claude_code_hook(settings_path=settings_path)
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_doctor.py -v
```

Expected: `ImportError: cannot import name 'check_python_env'`

- [ ] **Step 3: Create `chassis/doctor.py`**

```python
import json
import sys
from pathlib import Path
from typing import Optional


def check_python_env() -> dict:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    meets_minimum = sys.version_info >= (3, 9)
    return {
        "status": "ok" if meets_minimum else "error",
        "version": version,
        "message": f"Python {version}" if meets_minimum else f"Python {version} — 3.9+ required",
    }


def check_global_components_dir() -> dict:
    path = Path.home() / ".chassis" / "components"
    if path.exists():
        count = len(list(path.glob("COMPONENT-*.md")))
        return {"status": "ok", "path": str(path), "components": count}
    return {"status": "missing", "path": str(path), "message": "Run: mkdir -p ~/.chassis/components"}


def check_project_components_dir(project_root: Optional[Path] = None) -> dict:
    if project_root is None:
        project_root = Path.cwd()
    path = project_root / ".components"
    if path.exists():
        count = len(list(path.glob("COMPONENT-*.md")))
        return {"status": "ok", "path": str(path), "components": count}
    return {"status": "missing", "path": str(path), "message": "No project-level components (optional)"}


def check_claude_code_hook(settings_path: Optional[Path] = None) -> dict:
    if settings_path is None:
        settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return {"status": "missing", "message": f"No settings.json at {settings_path}"}
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return {"status": "error", "message": "settings.json is not valid JSON"}

    hooks = settings.get("hooks", {}).get("UserPromptSubmit", [])
    for entry in hooks:
        for hook in entry.get("hooks", []):
            if "chassis" in hook.get("command", ""):
                return {"status": "ok", "command": hook["command"]}

    return {"status": "missing", "message": "Run: bash hooks/register-claude-code.sh"}


def check_fastembed() -> dict:
    try:
        import fastembed
        return {"status": "ok", "version": getattr(fastembed, "__version__", "unknown")}
    except ImportError:
        return {"status": "missing", "message": "Phase 2 unavailable — run: pip install 'chassis[embeddings]'"}


def check_chassis_mcp() -> dict:
    import shutil
    if shutil.which("chassis-mcp"):
        return {"status": "ok", "command": shutil.which("chassis-mcp")}
    venv_path = Path.home() / ".chassis" / ".venv" / "bin" / "chassis-mcp"
    if venv_path.exists():
        return {"status": "ok", "command": str(venv_path)}
    return {"status": "missing", "message": "Run: pip install 'chassis[mcp]'"}


def run_doctor(project_root: Optional[Path] = None) -> None:
    checks = [
        ("Python environment", check_python_env()),
        ("Global components dir", check_global_components_dir()),
        ("Project components dir", check_project_components_dir(project_root)),
        ("Claude Code hook", check_claude_code_hook()),
        ("fastembed (Phase 2)", check_fastembed()),
        ("chassis-mcp (Claude Desktop)", check_chassis_mcp()),
    ]

    print("chassis doctor\n" + "=" * 40)
    all_ok = True
    for label, result in checks:
        status = result["status"]
        if status == "ok":
            detail = result.get("version") or result.get("command") or result.get("path") or ""
            print(f"  ✓  {label}: {detail}")
        elif status == "missing":
            print(f"  -  {label}: {result.get('message', 'not found')}")
        else:
            print(f"  ✗  {label}: {result.get('message', 'error')}")
            all_ok = False

    print()
    if all_ok:
        print("All checks passed.")
    else:
        print("Some checks failed. See messages above.")
```

- [ ] **Step 4: Wire `doctor` into `chassis/__main__.py`**

Add the doctor subcommand. In `chassis/__main__.py`, update `main()`:

```python
# Add this import at the top
from .doctor import run_doctor

# In main(), add doctor subcommand after the select subparser:
def main() -> None:
    parser = argparse.ArgumentParser(prog="chassis")
    sub = parser.add_subparsers(dest="command")

    select_parser = sub.add_parser("select", help="Select and print matching components")
    select_parser.add_argument("prompt", help="The incoming user prompt")

    sub.add_parser("doctor", help="Check chassis installation health")

    args = parser.parse_args()
    if args.command == "select":
        cmd_select(args.prompt)
    elif args.command == "doctor":
        run_doctor(project_root=Path.cwd())
    else:
        parser.print_help()
```

- [ ] **Step 5: Run to verify tests pass**

```bash
pytest tests/test_doctor.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Run doctor manually**

```bash
python -m chassis doctor
```

Expected: a table of checks with ✓ / - / ✗ for each.

- [ ] **Step 7: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add chassis/doctor.py chassis/__main__.py tests/test_doctor.py
git commit -m "feat: add chassis doctor command"
```

---

## Task 2: Bootstrap Script

**Files:**
- Create: `install.sh`

- [ ] **Step 1: Create `install.sh`**

```bash
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
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Do a dry-run in a temporary directory to verify the script runs without errors**

```bash
# Run in a subshell with a fake HOME so it doesn't touch your real settings
(
  export HOME="$(mktemp -d)"
  bash install.sh
)
```

Walk through the prompts. Verify:
- Python version is detected correctly.
- `config.toml` is written to `$HOME/.chassis/config.toml`.
- Example component is created.
- No unhandled errors.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add bootstrap install script"
```

---

## Task 3: Final End-to-End Check

- [ ] **Step 1: Run the full test suite one last time**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run `chassis doctor` and verify output**

```bash
python -m chassis doctor
```

Expected: each installed/configured item shows ✓, optional missing items show -.

- [ ] **Step 3: Commit any outstanding changes**

```bash
git status
# Stage and commit anything uncommitted
```

- [ ] **Step 4: Tag the initial release**

```bash
git tag -a v0.1.0 -m "Initial release — core library, hooks, MCP server, bootstrap"
```
