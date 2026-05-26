# Chassis — Plan 1: Core Library

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `chassis` Python package — data models, config loading, component loader, Phase 1 keyword matcher, gate logic, selector orchestration, session state, CLI entry point, and optional Phase 2 embedding matcher.

**Architecture:** A layered Python package where each module has one responsibility. `selector.py` orchestrates the pipeline: load config → load components → match → apply gate logic → return results. The CLI entry point (`__main__.py`) calls the selector, filters already-injected components via session state, and prints output to stdout for consumption by hook shims and the MCP server.

**Tech Stack:** Python 3.9+, PyYAML, tomli (Python <3.11 only), fastembed + numpy (optional, Phase 2), pytest

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, deps, optional extras |
| `chassis/__init__.py` | Package version |
| `chassis/__main__.py` | CLI entry point: `python -m chassis select "<prompt>"` |
| `chassis/models.py` | Dataclasses: `Component`, `MatchResult`, `Config` |
| `chassis/config.py` | Load and merge `config.toml` from global + project |
| `chassis/loader.py` | Discover, parse, and merge `COMPONENT-*.md` files |
| `chassis/matcher.py` | Phase 1: substring keyword/topic matching |
| `chassis/embedder.py` | Phase 2: fastembed-based semantic matching |
| `chassis/selector.py` | Orchestrate loader → matcher/embedder → gate logic |
| `chassis/session.py` | Read/write `.chassis/session.json` |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/test_models.py` | Model construction and defaults |
| `tests/test_config.py` | Config loading and two-level merge |
| `tests/test_loader.py` | Component discovery, parsing, and override logic |
| `tests/test_matcher.py` | Keyword matching, ranking, edge cases |
| `tests/test_selector.py` | Full pipeline integration: prompt in, results out |
| `tests/test_session.py` | Session state read/write, corruption handling |
| `tests/test_cli.py` | CLI stdout/stderr output and exit codes |
| `tests/test_embedder.py` | Phase 2 matching (skipped if fastembed not installed) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `chassis/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "chassis"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "pyyaml>=6.0",
    "tomli>=2.0; python_version < '3.11'",
]

[project.optional-dependencies]
embeddings = [
    "fastembed>=0.3",
    "numpy>=1.24",
]

[project.scripts]
chassis = "chassis.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `chassis/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 4: Create `tests/conftest.py`**

```python
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
```

- [ ] **Step 5: Install in editable mode and run an empty test suite**

```bash
pip install -e ".[embeddings]"
pytest
```

Expected: `no tests ran` or `0 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml chassis/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold chassis package"
```

---

## Task 2: Data Models

**Files:**
- Create: `chassis/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from chassis.models import Component, MatchResult, Config


def test_component_defaults():
    comp = Component(name="git", description="Git stuff", body="# Git")
    assert comp.gate is False
    assert comp.keywords == []
    assert comp.topics == []
    assert comp.source == "global"


def test_match_result_fields():
    comp = Component(name="git", description="", body="")
    result = MatchResult(component=comp, score=2.0, requires_gate=False, phase=1)
    assert result.phase == 1


def test_config_defaults():
    config = Config()
    assert config.selector_phase == 1
    assert config.threshold == 0.5
    assert config.gate_enabled is False
    assert config.notify_enabled is True
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'Component'`

- [ ] **Step 3: Create `chassis/models.py`**

```python
from dataclasses import dataclass, field


@dataclass
class Component:
    name: str
    description: str
    body: str
    gate: bool = False
    keywords: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    source: str = "global"


@dataclass
class MatchResult:
    component: Component
    score: float
    requires_gate: bool
    phase: int


@dataclass
class Config:
    selector_phase: int = 1
    threshold: float = 0.5
    gate_enabled: bool = False
    notify_enabled: bool = True
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add chassis/models.py tests/test_models.py
git commit -m "feat: add data models"
```

---

## Task 3: Config Loading

**Files:**
- Create: `chassis/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'load_config'`

- [ ] **Step 3: Create `chassis/config.py`**

```python
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
```

- [ ] **Step 4: Run to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add chassis/config.py tests/test_config.py
git commit -m "feat: add config loading with two-level merge"
```

---

## Task 4: Component Loader

**Files:**
- Create: `chassis/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loader.py
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


def test_load_global_components(home_dir, project_root, write_component=None):
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
```

- [ ] **Step 2: Fix the test import — update `tests/conftest.py` so `write_component` can be imported directly**

The tests above import `write_component` from `conftest`. Make it importable by also exporting it at module level (it already is — the fixture and the function are both named `write_component`, which causes a naming conflict). Rename the fixture to avoid this:

```python
# tests/conftest.py  — replace the write_component fixture with a plain function
# (remove the @pytest.fixture decorator)

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
```

- [ ] **Step 3: Run to verify the tests fail**

```bash
pytest tests/test_loader.py -v
```

Expected: `ImportError: cannot import name 'parse_component'`

- [ ] **Step 4: Create `chassis/loader.py`**

```python
import re
from pathlib import Path
from typing import Optional

import yaml

from .models import Component

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)


def parse_component(path: Path, source: str) -> Optional[Component]:
    try:
        text = path.read_text()
    except OSError:
        return None

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None

    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None

    if not meta or "name" not in meta:
        return None

    triggers = meta.get("triggers") or {}
    return Component(
        name=str(meta["name"]),
        description=str(meta.get("description") or ""),
        body=m.group(2).strip(),
        gate=bool(meta.get("gate", False)),
        keywords=[str(k) for k in (triggers.get("keywords") or [])],
        topics=[str(t) for t in (triggers.get("topics") or [])],
        source=source,
    )


def load_components(project_root: Optional[Path] = None) -> list:
    components: dict[str, Component] = {}

    global_dir = Path.home() / ".chassis" / "components"
    if global_dir.exists():
        for path in sorted(global_dir.glob("COMPONENT-*.md")):
            comp = parse_component(path, "global")
            if comp:
                components[comp.name] = comp

    if project_root:
        project_dir = project_root / ".components"
        if project_dir.exists():
            for path in sorted(project_dir.glob("COMPONENT-*.md")):
                comp = parse_component(path, "project")
                if comp:
                    components[comp.name] = comp

    return list(components.values())
```

- [ ] **Step 5: Run to verify they pass**

```bash
pytest tests/test_loader.py -v
```

Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add chassis/loader.py tests/test_loader.py tests/conftest.py
git commit -m "feat: add component loader with two-level merging"
```

---

## Task 5: Phase 1 Keyword Matcher

**Files:**
- Create: `chassis/matcher.py`
- Create: `tests/test_matcher.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_matcher.py
import pytest
from chassis.models import Component
from chassis.matcher import match_keywords


def make_comp(name, keywords=None, topics=None):
    return Component(name=name, description="", body="", keywords=keywords or [], topics=topics or [])


def test_matches_exact_keyword():
    comp = make_comp("git", keywords=["commit"])
    results = match_keywords("I need to commit my changes", [comp])
    assert len(results) == 1
    assert results[0].component.name == "git"
    assert results[0].phase == 1


def test_matches_keyword_as_substring():
    comp = make_comp("git", keywords=["commit"])
    results = match_keywords("reviewing commits today", [comp])
    assert len(results) == 1


def test_case_insensitive():
    comp = make_comp("git", keywords=["Git", "Commit"])
    results = match_keywords("GIT COMMIT", [comp])
    assert len(results) == 1
    assert results[0].score == 2.0


def test_no_match_returns_empty():
    comp = make_comp("r-pkg", keywords=["devtools", "roxygen"])
    results = match_keywords("fix the login bug", [comp])
    assert results == []


def test_ranked_by_score():
    comp_a = make_comp("a", keywords=["git", "commit", "branch"])
    comp_b = make_comp("b", keywords=["git"])
    results = match_keywords("git commit to branch", [comp_a, comp_b])
    assert results[0].component.name == "a"
    assert results[1].component.name == "b"


def test_ties_broken_alphabetically():
    comp_a = make_comp("alpha", keywords=["git"])
    comp_b = make_comp("beta", keywords=["git"])
    results = match_keywords("git stuff", [comp_a, comp_b])
    assert results[0].component.name == "alpha"


def test_topic_match_counts():
    comp = make_comp("git", keywords=["git"], topics=["version_control"])
    results = match_keywords("version_control workflow", [comp])
    assert results[0].score == 1.0


def test_requires_gate_defaults_false():
    comp = make_comp("git", keywords=["git"])
    results = match_keywords("git stuff", [comp])
    assert results[0].requires_gate is False
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_matcher.py -v
```

Expected: `ImportError: cannot import name 'match_keywords'`

- [ ] **Step 3: Create `chassis/matcher.py`**

```python
from .models import Component, MatchResult


def match_keywords(prompt: str, components: list) -> list:
    prompt_lower = prompt.lower()
    results = []

    for comp in components:
        score = 0
        for kw in comp.keywords:
            if kw.lower() in prompt_lower:
                score += 1
        for topic in comp.topics:
            if topic.lower() in prompt_lower:
                score += 1
        if score > 0:
            results.append(MatchResult(
                component=comp,
                score=float(score),
                requires_gate=False,
                phase=1,
            ))

    results.sort(key=lambda r: (-r.score, r.component.name))
    return results
```

- [ ] **Step 4: Run to verify they pass**

```bash
pytest tests/test_matcher.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add chassis/matcher.py tests/test_matcher.py
git commit -m "feat: add Phase 1 keyword matcher"
```

---

## Task 6: Session State

**Files:**
- Create: `chassis/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_session.py
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_session.py -v
```

Expected: `ImportError: cannot import name 'load_session'`

- [ ] **Step 3: Create `chassis/session.py`**

```python
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
```

- [ ] **Step 4: Run to verify they pass**

```bash
pytest tests/test_session.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add chassis/session.py tests/test_session.py
git commit -m "feat: add session state tracking"
```

---

## Task 7: Selector Orchestration

**Files:**
- Create: `chassis/selector.py`
- Create: `tests/test_selector.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selector.py
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_selector.py -v
```

Expected: `ImportError: cannot import name 'select'`

- [ ] **Step 3: Create `chassis/selector.py`**

```python
import logging
from pathlib import Path
from typing import Optional

from .config import load_config
from .loader import load_components
from .matcher import match_keywords
from .models import MatchResult

logger = logging.getLogger(__name__)


def select(prompt: str, project_root: Optional[Path] = None) -> list:
    config = load_config(project_root)
    components = load_components(project_root)

    if config.selector_phase == 2:
        try:
            from .embedder import match_embeddings
            results = match_embeddings(prompt, components, config.threshold)
        except ImportError:
            logger.warning("fastembed not available; falling back to keyword matching")
            results = match_keywords(prompt, components)
    else:
        results = match_keywords(prompt, components)

    for result in results:
        if config.gate_enabled:
            result.requires_gate = True
        else:
            result.requires_gate = result.component.gate

    return results
```

- [ ] **Step 4: Run to verify they pass**

```bash
pytest tests/test_selector.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add chassis/selector.py tests/test_selector.py
git commit -m "feat: add selector orchestration with gate logic"
```

---

## Task 8: CLI Entry Point

**Files:**
- Create: `chassis/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `No module named chassis.__main__` or similar

- [ ] **Step 3: Create `chassis/__main__.py`**

```python
import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .selector import select
from .session import load_session, mark_injected, save_session, should_inject

logging.basicConfig(
    filename=Path.home() / ".chassis" / "chassis.log",
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)


def cmd_select(prompt: str) -> None:
    project_root = Path.cwd()
    config = load_config(project_root)

    try:
        results = select(prompt, project_root)
    except Exception:
        logging.exception("selector failed")
        sys.exit(0)

    session = load_session(project_root)
    to_inject = [r for r in results if should_inject(r.component.name, session)]

    if not to_inject:
        sys.exit(0)

    if config.notify_enabled:
        names = ", ".join(r.component.name for r in to_inject)
        print(f"[chassis] Loading: {names}", file=sys.stderr)

    gated = [r for r in to_inject if r.requires_gate]
    ungated = [r for r in to_inject if not r.requires_gate]

    if gated:
        names = ", ".join(r.component.name for r in gated)
        print(
            f"[chassis] The following components matched but require approval "
            f"before loading: {names}. Please ask the user if they should be loaded."
        )

    for result in ungated:
        print(result.component.body)
        print()
        session = mark_injected(result.component.name, session)

    save_session(session, project_root)


def main() -> None:
    parser = argparse.ArgumentParser(prog="chassis")
    sub = parser.add_subparsers(dest="command")

    select_parser = sub.add_parser("select", help="Select and print matching components")
    select_parser.add_argument("prompt", help="The incoming user prompt")

    args = parser.parse_args()
    if args.command == "select":
        cmd_select(args.prompt)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add chassis/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point"
```

---

## Task 9: Phase 2 Embedding Matcher

**Files:**
- Create: `chassis/embedder.py`
- Create: `tests/test_embedder.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_embedder.py
import pytest

fastembed = pytest.importorskip("fastembed", reason="fastembed not installed; skipping Phase 2 tests")

from chassis.models import Component
from chassis.embedder import match_embeddings


def make_comp(name, description):
    return Component(name=name, description=description, body=f"# {name}")


def test_returns_semantically_similar_component():
    components = [
        make_comp("git-workflow", "Git workflow, branching, and commit conventions"),
        make_comp("r-packaging", "R package development with devtools and testthat"),
    ]
    results = match_embeddings("how do I create a git branch", components, threshold=0.3)
    names = [r.component.name for r in results]
    assert "git-workflow" in names


def test_returns_empty_when_nothing_similar():
    components = [
        make_comp("r-packaging", "R package development with devtools and testthat"),
    ]
    results = match_embeddings("unrelated topic about cooking recipes", components, threshold=0.9)
    assert results == []


def test_ranked_by_score():
    components = [
        make_comp("git-workflow", "Git workflow, branching, and commit conventions"),
        make_comp("git-advanced", "Advanced git rebase, cherry-pick, and history editing"),
    ]
    results = match_embeddings("git branching strategy", components, threshold=0.2)
    if len(results) >= 2:
        assert results[0].score >= results[1].score


def test_phase_is_2():
    components = [make_comp("git-workflow", "Git workflow and commits")]
    results = match_embeddings("git commit", components, threshold=0.1)
    if results:
        assert results[0].phase == 2


def test_requires_gate_defaults_false():
    components = [make_comp("git-workflow", "Git workflow and commits")]
    results = match_embeddings("git commit", components, threshold=0.1)
    if results:
        assert results[0].requires_gate is False
```

- [ ] **Step 2: Run to verify the tests skip (not fail) when fastembed is absent, or fail when present**

```bash
pytest tests/test_embedder.py -v
```

Expected: `5 skipped` (if fastembed not installed) or `ImportError` from embedder (if installed).

- [ ] **Step 3: Create `chassis/embedder.py`**

```python
from .models import Component, MatchResult


def match_embeddings(prompt: str, components: list, threshold: float) -> list:
    from fastembed import TextEmbedding
    import numpy as np

    if not components:
        return []

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    descriptions = [c.description for c in components]
    all_texts = [prompt] + descriptions
    embeddings = list(model.embed(all_texts))

    prompt_emb = np.array(embeddings[0])
    desc_embs = [np.array(e) for e in embeddings[1:]]

    results = []
    for comp, emb in zip(components, desc_embs):
        norm = np.linalg.norm(prompt_emb) * np.linalg.norm(emb)
        sim = float(np.dot(prompt_emb, emb) / norm) if norm > 0 else 0.0
        if sim >= threshold:
            results.append(MatchResult(
                component=comp,
                score=sim,
                requires_gate=False,
                phase=2,
            ))

    results.sort(key=lambda r: (-r.score, r.component.name))
    return results
```

- [ ] **Step 4: Install embeddings extra and run tests**

```bash
pip install -e ".[embeddings]"
pytest tests/test_embedder.py -v
```

Expected: `5 passed` (model downloads ~80 MB on first run; subsequent runs are fast).

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add chassis/embedder.py tests/test_embedder.py
git commit -m "feat: add Phase 2 embedding matcher (optional fastembed)"
```

---

## Task 10: Selector Falls Back from Phase 2 to Phase 1

**Files:**
- Modify: `tests/test_selector.py`

- [ ] **Step 1: Add a fallback test**

Add this test to `tests/test_selector.py`:

```python
def test_phase2_falls_back_to_phase1_when_fastembed_missing(home_dir, project_root, monkeypatch):
    write_component(home_dir / ".chassis" / "components", "git", ["git"], body="Git instructions")
    (home_dir / ".chassis" / "config.toml").write_text("[selector]\nphase = 2\n")

    import sys
    # Simulate fastembed being absent by blocking the import
    monkeypatch.setitem(sys.modules, "fastembed", None)

    results = select("git commit", project_root=project_root)
    assert len(results) == 1
    assert results[0].phase == 1
```

- [ ] **Step 2: Run to verify it passes**

```bash
pytest tests/test_selector.py -v
```

Expected: `7 passed`

- [ ] **Step 3: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_selector.py
git commit -m "test: verify Phase 2 → Phase 1 fallback"
```
