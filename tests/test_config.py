import pytest
from pathlib import Path
from chassis.config import load_config


def test_returns_defaults_when_no_files_exist(home_dir, project_root):
    config = load_config(project_root=project_root)
    assert config.selector_phase == 1
    assert config.threshold == 0.5
    assert config.gate_enabled is False
    assert config.notify_enabled is True


def test_loads_global_config(home_dir, project_root):
    (home_dir / ".chassis" / "config.toml").write_text(
        "[selector]\nphase = 2\nthreshold = 0.7\n"
    )
    config = load_config(project_root=project_root)
    assert config.selector_phase == 2
    assert config.threshold == 0.7


def test_project_overrides_global(home_dir, project_root):
    (home_dir / ".chassis" / "config.toml").write_text("[selector]\nphase = 2\n")
    (project_root / ".chassis").mkdir()
    (project_root / ".chassis" / "config.toml").write_text("[selector]\nphase = 1\n")
    config = load_config(project_root=project_root)
    assert config.selector_phase == 1


def test_gate_config(home_dir, project_root):
    (home_dir / ".chassis" / "config.toml").write_text("[gate]\nenabled = true\n")
    config = load_config(project_root=project_root)
    assert config.gate_enabled is True


def test_notify_config(home_dir, project_root):
    (home_dir / ".chassis" / "config.toml").write_text("[notify]\nenabled = false\n")
    config = load_config(project_root=project_root)
    assert config.notify_enabled is False
