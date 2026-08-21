#!/usr/bin/env python3
"""Validate the platform-wide reduced-motion contract."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

BRAND_CSS = Path("assets/brand/rawafid-brand.css")
REQUIRED = (
    "@media (prefers-reduced-motion: reduce)",
    "scroll-behavior:auto!important",
    "animation-duration:.01ms!important",
    "animation-iteration-count:1!important",
    "transition-duration:.01ms!important",
    ".journey:hover",
    ".pt-back-to-top.is-visible",
    "[data-motion]:hover",
    "transform:none!important",
)


def validate(root: Path) -> list[str]:
    path = root / BRAND_CSS
    try:
        css = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"missing file: {BRAND_CSS}"]

    errors: list[str] = []
    for marker in REQUIRED:
        if marker not in css:
            errors.append(f"missing reduced-motion contract marker: {marker}")

    media_start = css.find("@media (prefers-reduced-motion: reduce)")
    if media_start < 0:
        return errors
    reduced_block = css[media_start:]
    if "transform:none!important" not in reduced_block:
        errors.append("spatial transforms must be disabled inside the reduced-motion media query")
    if "scroll-behavior:auto!important" not in reduced_block:
        errors.append("smooth scrolling must be disabled inside the reduced-motion media query")
    return errors


def run_self_test() -> int:
    valid_css = (
        "@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto!important}"
        "*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;"
        "transition-duration:.01ms!important}.journey:hover,.pt-back-to-top.is-visible,[data-motion]:hover"
        "{transform:none!important}}"
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / BRAND_CSS
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(valid_css, encoding="utf-8")
        if errors := validate(root):
            print("valid fixture failed:", *errors, sep="\n- ", file=sys.stderr)
            return 1
        path.write_text(valid_css.replace("transform:none!important", ""), encoding="utf-8")
        if not validate(root):
            print("self-test failed to reject missing transform override", file=sys.stderr)
            return 1
    print("reduced-motion validator self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    errors = validate(args.root.resolve())
    if errors:
        print("reduced-motion validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("reduced-motion validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
