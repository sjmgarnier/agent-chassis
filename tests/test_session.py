import json
import pytest
from pathlib import Path
from chassis.session import load_session, save_session, should_inject, mark_injected


def test_load_returns_defaults_when_missing(project_root):
    state = load_session(project_root=project_root)
    assert state == {"injected": [], "turn": 0}


def test_save_and_load_roundtrip(project_root):
    state = {"injected": ["git-workflow"], "turn": 1}
    save_session(state, project_root=project_root)
    loaded = load_session(project_root=project_root)
    assert loaded == state


def test_load_returns_defaults_on_corrupt_file(project_root):
    path = project_root / ".chassis" / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json {{{")
    state = load_session(project_root=project_root)
    assert state == {"injected": [], "turn": 0}


def test_should_inject_new_component(project_root):
    state = load_session(project_root=project_root)
    assert should_inject("git-workflow", state) is True


def test_should_not_inject_already_injected():
    state = {"injected": ["git-workflow"], "turn": 1}
    assert should_inject("git-workflow", state) is False


def test_mark_injected_adds_name():
    state = {"injected": [], "turn": 0}
    state = mark_injected("git-workflow", state)
    assert "git-workflow" in state["injected"]


def test_mark_injected_increments_turn():
    state = {"injected": [], "turn": 0}
    state = mark_injected("git-workflow", state)
    assert state["turn"] == 1


def test_mark_injected_idempotent():
    state = {"injected": ["git-workflow"], "turn": 1}
    state = mark_injected("git-workflow", state)
    assert state["injected"].count("git-workflow") == 1


def test_fallback_to_global_when_no_project_root(home_dir):
    state = {"injected": ["git-workflow"], "turn": 1}
    save_session(state, project_root=None)
    loaded = load_session(project_root=None)
    assert loaded["injected"] == ["git-workflow"]
