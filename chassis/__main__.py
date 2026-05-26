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
