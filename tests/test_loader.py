import pytest
from pathlib import Path
from chassis.loader import parse_component, load_components


def test_parse_valid_component(tmp_path):
    f = tmp_path / "COMPONENT-git.md"
    f.write_text(
        "---\n"
        "name: git-workflow\n"
        "description: Git stuff\n"
        "gate: false\n"
        "triggers:\n"
        "  keywords: [git, commit]\n"
        "  topics: [vcs]\n"
        "---\n\n"
        "# Git\nUse conventional commits.\n"
    )
    comp = parse_component(f, "global")
    assert comp is not None
    assert comp.name == "git-workflow"
    assert comp.keywords == ["git", "commit"]
    assert comp.topics == ["vcs"]
    assert comp.gate is False
    assert "Use conventional commits" in comp.body
    assert comp.source == "global"


def test_parse_missing_name_returns_none(tmp_path):
    f = tmp_path / "COMPONENT-bad.md"
    f.write_text("---\ndescription: No name here\n---\n\n# Content\n")
    assert parse_component(f, "global") is None


def test_parse_no_frontmatter_returns_none(tmp_path):
    f = tmp_path / "COMPONENT-bad.md"
    f.write_text("# Just markdown\nNo frontmatter at all.\n")
    assert parse_component(f, "global") is None


def test_parse_invalid_yaml_returns_none(tmp_path):
    f = tmp_path / "COMPONENT-bad.md"
    f.write_text("---\n: : invalid yaml :::\n---\n\n# Content\n")
    assert parse_component(f, "global") is None


def test_load_global_components(home_dir, project_root):
    from tests.conftest import write_component
    write_component(home_dir / ".chassis" / "components", "git", ["git", "commit"])
    write_component(home_dir / ".chassis" / "components", "r-pkg", ["devtools"])
    components = load_components(project_root=project_root)
    names = {c.name for c in components}
    assert "git" in names
    assert "r-pkg" in names


def test_project_overrides_global(home_dir, project_root):
    from tests.conftest import write_component
    write_component(
        home_dir / ".chassis" / "components", "git", ["git"],
        body="Global body", description="Global git"
    )
    write_component(
        project_root / ".components", "git", ["git"],
        body="Project body", description="Project git"
    )
    components = load_components(project_root=project_root)
    assert len(components) == 1
    assert components[0].body.strip() == "Project body"
    assert components[0].source == "project"


def test_only_component_files_are_loaded(home_dir, project_root):
    comp_dir = home_dir / ".chassis" / "components"
    (comp_dir / "README.md").write_text("# Not a component")
    (comp_dir / "COMPONENT-git.md").write_text(
        "---\nname: git\ndescription: d\ntriggers:\n  keywords: [git]\n---\n\nBody\n"
    )
    components = load_components(project_root=project_root)
    assert len(components) == 1
