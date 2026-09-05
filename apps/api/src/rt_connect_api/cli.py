"""Operational commands that run inside the API image without deployment credentials."""

from __future__ import annotations

import argparse

from rt_connect_api.db.session import get_engine, get_session
from rt_connect_api.seed import seed_synthetic_foundation


def seed_synthetic() -> int:
    if get_engine() is None:
        raise RuntimeError("DATABASE_URL is required for synthetic seed.")
    session_generator = get_session()
    session = next(session_generator)
    try:
        seed_synthetic_foundation(session)
    finally:
        session_generator.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="rt-connect-api")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("seed-synthetic")
    arguments = parser.parse_args()
    if arguments.command == "seed-synthetic":
        return seed_synthetic()
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
