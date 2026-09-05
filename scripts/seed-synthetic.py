"""Insert the P1 synthetic organization/site/machine fixture into a configured development DB."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "apps" / "api" / "src"))

from rt_connect_api.db.session import get_engine
from rt_connect_api.db.session import get_session
from rt_connect_api.seed import seed_synthetic_foundation


def main() -> int:
    if get_engine() is None:
        raise SystemExit("DATABASE_URL is required; never seed a database by accident.")
    session_generator = get_session()
    session = next(session_generator)
    try:
        seed_synthetic_foundation(session)
    finally:
        session_generator.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
