import pytest
from pathlib import Path
from tests.conftest import write_component
from chassis.selector import select


def test_select_returns_match(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git", "commit"], body="Git instructions")
    results = select("please git commit my changes", project_root=project_root)
    assert len(results) == 1
    assert results[0].component.name == "git"
    assert results[0].component.body == "Git instructions"


def test_select_no_match_returns_empty(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git", "commit"])
    results = select("unrelated prompt about lunch", project_root=project_root)
    assert results == []


def test_gate_enabled_globally_overrides_component(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=False)
    (home_dir / ".chassis" / "config.toml").write_text("[gate]\nenabled = true\n")
    results = select("git commit", project_root=project_root)
    assert results[0].requires_gate is True


def test_component_gate_respected_when_global_gate_off(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=True)
    results = select("git commit", project_root=project_root)
    assert results[0].requires_gate is True


def test_component_gate_false_when_global_gate_off(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], gate=False)
    results = select("git commit", project_root=project_root)
    assert results[0].requires_gate is False


def test_select_uses_project_component_over_global(home_dir, project_root):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Global body")
    write_component(project_root / ".components", "git", ["git"], body="Project body")
    results = select("git commit", project_root=project_root)
    assert len(results) == 1
    assert results[0].component.body == "Project body"


def test_phase2_falls_back_to_phase1_when_fastembed_missing(home_dir, project_root, monkeypatch):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    (home_dir / ".chassis" / "config.toml").write_text("[selector]\nphase = 2\n")

    import sys
    import chassis.embedder
    # Reset cached model so _get_model() will attempt a fresh import
    monkeypatch.setattr(chassis.embedder, "_embedding_model", None)
    # Simulate fastembed being absent by blocking the import
    monkeypatch.setitem(sys.modules, "fastembed", None)

    results = select("git commit", project_root=project_root)
    assert len(results) == 1
    assert results[0].phase == 1
