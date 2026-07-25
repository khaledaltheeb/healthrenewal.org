#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_provider_condition_discovery_v238 as core


def publish(site: Path) -> dict[str, Any]:
    """Compatibility entrypoint retained for the production discovery workflow."""
    return core.publish(site)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
