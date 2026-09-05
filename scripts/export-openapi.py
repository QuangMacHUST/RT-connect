"""Export or verify the stable FastAPI OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = REPOSITORY_ROOT / "apps" / "api" / "src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from rt_connect_api.main import create_app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "docs" / "openapi.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    rendered = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    if arguments.check:
        return 0 if arguments.output.is_file() and arguments.output.read_text(encoding="utf-8") == rendered else 1
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
