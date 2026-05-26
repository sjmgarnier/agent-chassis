import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .doctor import run_doctor
from .selector import select
from .session import load_session, mark_injected, save_session, should_inject

_log_dir = Path.home() / ".chassis"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=_log_dir / "chassis.log",
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

    gated = [r for r in to_inject if r.requires_gate]
    ungated = [r for r in to_inject if not r.requires_gate]

    if config.notify_enabled and ungated:
        names = ", ".join(r.component.name for r in ungated)
        print(f"[chassis] Loading: {names}", file=sys.stderr)

    if gated:
        names = ", ".join(r.component.name for r in gated)
        print(
            f"[chassis] The following components matched but require approval "
            f"before loading: {names}. Please ask the user if they should be loaded."
        )
        for result in gated:
            session = mark_injected(result.component.name, session)

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

    sub.add_parser("doctor", help="Check chassis installation health")

    args = parser.parse_args()
    if args.command == "select":
        cmd_select(args.prompt)
    elif args.command == "doctor":
        run_doctor(project_root=Path.cwd())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
