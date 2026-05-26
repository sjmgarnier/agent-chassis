from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .models import Config


def _load_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load_config(project_root: Optional[Path] = None) -> Config:
    data: dict = {}

    global_path = Path.home() / ".chassis" / "config.toml"
    data.update(_load_toml(global_path))

    if project_root:
        project_path = project_root / ".chassis" / "config.toml"
        _merge(data, _load_toml(project_path))

    return Config(
        selector_phase=data.get("selector", {}).get("phase", 1),
        threshold=data.get("selector", {}).get("threshold", 0.5),
        gate_enabled=data.get("gate", {}).get("enabled", False),
        notify_enabled=data.get("notify", {}).get("enabled", True),
    )


def _merge(base: dict, override: dict) -> None:
    for key, val in override.items():
        if isinstance(val, dict) and key in base and isinstance(base[key], dict):
            _merge(base[key], val)
        else:
            base[key] = val
