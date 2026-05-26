import pytest
from pathlib import Path
from tests.conftest import write_component
from chassis.mcp.handlers import handle_load


def test_returns_ungated_component_body(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    result = handle_load("git commit my changes", project_root=project_root)
    assert result["type"] == "content"
    assert "Git instructions" in result["text"]


def test_returns_gated_component_as_confirmation_request(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=True, body="Secret")
    result = handle_load("git commit", project_root=project_root)
    assert result["type"] == "gate"
    assert "git" in result["pending"]
    assert "Secret" not in result["text"]


def test_returns_empty_on_no_match(home_dir, project_root):
    result = handle_load("unrelated topic about lunch", project_root=project_root)
    assert result["type"] == "empty"


def test_global_gate_overrides_component(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=False, body="Instructions")
    (home_dir / ".chassis" / "config.toml").write_text("[gate]\nenabled = true\n")
    result = handle_load("git commit", project_root=project_root)
    assert result["type"] == "gate"


def test_skips_already_injected(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    handle_load("git commit", project_root=project_root)
    result = handle_load("git commit again", project_root=project_root)
    assert result["type"] == "empty"
