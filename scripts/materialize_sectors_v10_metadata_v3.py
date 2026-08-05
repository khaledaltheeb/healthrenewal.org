#!/usr/bin/env python3
from __future__ import annotations

"""Stable v3 entrypoint for governed sectors-v10 publication.

The governance, metadata, Schema, practical-question, source-log, and internal-link
rendering contract lives in ``materialize_sectors_v10_compat_v2``. This module
intentionally delegates to that implementation so older automation may call the
v3 filename without applying a second rendering layer or duplicating content.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import materialize_sectors_v10_compat_v2 as compat

base = compat.base
PublicationItem = base.PublicationItem
PublicationError = base.PublicationError


def normalize_payload(payload: dict[str, Any]) -> None:
    compat.normalize_payload(payload)


def validate_source(path: Path, payload: dict[str, Any]) -> None:
    compat.validate_source(path, payload)


def render_page(item: PublicationItem) -> str:
    return compat.render_page(item)


def write_publication(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    return compat.write_publication(repo_root, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize governed sectors-v10 pages through the stable v3 entrypoint."
    )
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = write_publication(args.repo_root.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
