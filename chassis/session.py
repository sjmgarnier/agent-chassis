import json
from pathlib import Path
from typing import Optional


def _session_path(project_root: Optional[Path] = None) -> Path:
    if project_root:
        path = project_root / ".chassis" / "session.json"
    else:
        path = Path.home() / ".chassis" / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_session(project_root: Optional[Path] = None) -> dict:
    path = _session_path(project_root)
    if not path.exists():
        return {"injected": [], "turn": 0}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"injected": [], "turn": 0}


def save_session(state: dict, project_root: Optional[Path] = None) -> None:
    path = _session_path(project_root)
    try:
        path.write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def should_inject(name: str, state: dict) -> bool:
    return name not in state.get("injected", [])


def mark_injected(name: str, state: dict) -> dict:
    injected = state.get("injected", [])
    if name not in injected:
        injected = injected + [name]
    return {"injected": injected, "turn": state.get("turn", 0) + 1}
