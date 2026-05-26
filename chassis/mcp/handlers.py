from pathlib import Path
from typing import Optional

from ..config import load_config
from ..selector import select
from ..session import load_session, mark_injected, save_session, should_inject


def handle_load(prompt: str, project_root: Optional[Path] = None) -> dict:
    """
    Run the selector for the given prompt and return a structured result.

    Return types:
    - {"type": "content", "text": "..."}  — ungated components ready to inject
    - {"type": "gate", "text": "...", "pending": ["name1", ...]}  — gated, needs user approval
    - {"type": "empty"}  — no matches or all already injected
    """
    if project_root is None:
        project_root = Path.cwd()

    config = load_config(project_root)

    try:
        results = select(prompt, project_root)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("selector failed")
        return {"type": "empty"}

    session = load_session(project_root)
    to_inject = [r for r in results if should_inject(r.component.name, session)]

    if not to_inject:
        return {"type": "empty"}

    gated = [r for r in to_inject if r.requires_gate]
    ungated = [r for r in to_inject if not r.requires_gate]

    parts = []
    for result in ungated:
        parts.append(result.component.body)
        session = mark_injected(result.component.name, session)

    for result in gated:
        session = mark_injected(result.component.name, session)

    save_session(session, project_root)

    if gated and not ungated:
        names = [r.component.name for r in gated]
        text = (
            f"[chassis] The following components matched but require your approval "
            f"before loading: {', '.join(names)}. "
            f"Reply 'yes' to load them or 'no' to skip."
        )
        return {"type": "gate", "text": text, "pending": names}

    if gated and ungated:
        names = [r.component.name for r in gated]
        gate_notice = (
            f"\n\n[chassis] Additional components require approval: {', '.join(names)}. "
            f"Ask the user if they should be loaded."
        )
        parts.append(gate_notice)

    if config.notify_enabled and ungated:
        loaded_names = ", ".join(r.component.name for r in ungated)
        header = f"[chassis] Loading: {loaded_names}\n\n"
    else:
        header = ""

    return {"type": "content", "text": header + "\n\n".join(parts)}
