import pytest
from pathlib import Path


@pytest.fixture
def home_dir(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".chassis" / "components").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


@pytest.fixture
def project_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    return root


def write_component(directory: Path, name: str, keywords: list, description: str = "", gate: bool = False, body: str = "Instructions.") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: {description}
gate: {"true" if gate else "false"}
triggers:
  keywords: {keywords}
---

{body}
"""
    path = directory / f"COMPONENT-{name}.md"
    path.write_text(content)
    return path
