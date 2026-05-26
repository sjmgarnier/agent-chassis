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
