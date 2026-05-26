import os
import subprocess
import sys
import pytest
from pathlib import Path
from tests.conftest import write_component


def run_chassis(args, cwd, env):
    return subprocess.run(
        [sys.executable, "-m", "chassis"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )


def make_env(home_dir):
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    return env


def test_select_no_match_exits_zero(tmp_path):
    home = tmp_path / "home"
    (home / ".chassis" / "components").mkdir(parents=True)
    result = run_chassis(["select", "unrelated prompt"], cwd=tmp_path, env=make_env(home))
    assert result.returncode == 0
    assert result.stdout == ""


def test_select_prints_body_to_stdout(tmp_path):
    home = tmp_path / "home"
    write_component(home / ".chassis" / "components", "git", ["git"], body="Git instructions here")
    result = run_chassis(["select", "git commit please"], cwd=tmp_path, env=make_env(home))
    assert result.returncode == 0
    assert "Git instructions here" in result.stdout


def test_select_prints_notification_to_stderr(tmp_path):
    home = tmp_path / "home"
    write_component(home / ".chassis" / "components", "git", ["git"], body="Git instructions")
    result = run_chassis(["select", "git commit please"], cwd=tmp_path, env=make_env(home))
    assert "[chassis] Loading" in result.stderr
    assert "git" in result.stderr


def test_select_gated_component_prints_preamble_not_body(tmp_path):
    home = tmp_path / "home"
    write_component(home / ".chassis" / "components", "git", ["git"], gate=True, body="Secret instructions")
    result = run_chassis(["select", "git commit please"], cwd=tmp_path, env=make_env(home))
    assert "Secret instructions" not in result.stdout
    assert "require approval" in result.stdout.lower() or "approval" in result.stdout.lower()


def test_select_skips_already_injected(tmp_path):
    home = tmp_path / "home"
    write_component(home / ".chassis" / "components", "git", ["git"], body="Git instructions")
    env = make_env(home)
    run_chassis(["select", "git commit"], cwd=tmp_path, env=env)
    result = run_chassis(["select", "git commit again"], cwd=tmp_path, env=env)
    assert "Git instructions" not in result.stdout


def test_notify_false_suppresses_stderr(tmp_path):
    home = tmp_path / "home"
    write_component(home / ".chassis" / "components", "git", ["git"], body="Git instructions")
    (home / ".chassis" / "config.toml").write_text("[notify]\nenabled = false\n")
    result = run_chassis(["select", "git commit please"], cwd=tmp_path, env=make_env(home))
    assert "[chassis]" not in result.stderr
