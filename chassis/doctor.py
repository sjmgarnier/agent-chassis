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
