import pytest
import json
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


def test_check_global_components_dir_missing(home_dir):
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


def test_check_claude_code_hook_not_registered(tmp_path):
    settings_path = tmp_path / "claude" / "settings.json"
    result = check_claude_code_hook(settings_path=settings_path)
    assert result["status"] == "missing"


def test_check_claude_code_hook_registered(tmp_path):
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
