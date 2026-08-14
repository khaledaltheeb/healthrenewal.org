#!/usr/bin/env python3
"""Run the capabilities SEO normalizer as the final pre-deploy publication gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from publish_conditions_v281 import enforce_seo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()

    root = args.site.resolve()
    report = enforce_seo(root)
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    destination = api / "capabilities-seo-v1.json"
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
