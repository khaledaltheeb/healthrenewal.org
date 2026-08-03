#!/usr/bin/env python3
"""Backward-compatible entry point for the Rawafid brand normalizer."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from rawafid_brand_runner import normalize_root


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = normalize_root(root, fix=True, production=False)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
