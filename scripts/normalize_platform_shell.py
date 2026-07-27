#!/usr/bin/env python3
"""Apply the shared platform shell to every production HTML page.

The migration is deliberately idempotent. Existing pages keep their content and
local navigation; the script only adds the shared presentation assets, rights
metadata, and a body marker consumed by the global shell.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "platform-normalization.json"
MARKER = "<!-- pt-platform-shell:v1 -->"
SHELL_VERSION = "1.0.0"
EXCLUDED_PARTS = {
    ".git",
    ".github",
    "node_modules",
    "vendor",
    "fixtures",
    "snapshots",
    "coverage",
    "reports",
}

HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
BODY_OPEN_RE = re.compile(r"<body\b(?P<attrs>[^>]*)>", re.IGNORECASE)
CLASS_RE = re.compile(r"\bclass\s*=\s*([\"'])(?P<value>.*?)\1", re.IGNORECASE | re.DOTALL)


@dataclass
class Result:
    path: str
    status: str
    detail: str = ""


def production_html_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*.html")):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        yield path


def relative_prefix(path: Path) -> str:
    depth = len(path.relative_to(ROOT).parent.parts)
    return "../" * depth


def head_injection(path: Path, source: str) -> str:
    prefix = relative_prefix(path)
    items = [MARKER]

    lowered = source.lower()
    if 'name="copyright"' not in lowered and "name='copyright'" not in lowered:
        items.append(
            '<meta name="copyright" content="© 2026 Khaled Altheeb — منصة الصحة النفسية وذوي الاحتياجات الخاصة">'
        )
    if 'name="rights"' not in lowered and "name='rights'" not in lowered:
        items.append('<meta name="rights" content="All rights reserved">')
    if 'rel="license"' not in lowered and "rel='license'" not in lowered:
        items.append(f'<link rel="license" href="{prefix}copyright/">')

    items.extend(
        [
            f'<link rel="stylesheet" href="{prefix}assets/platform/platform-core.css?v={SHELL_VERSION}">',
            f'<script defer src="{prefix}assets/platform/platform-core.js?v={SHELL_VERSION}"></script>',
        ]
    )
    return "\n".join(items) + "\n"


def normalize_body(source: str) -> tuple[str, bool]:
    match = BODY_OPEN_RE.search(source)
    if not match:
        return source, False

    attrs = match.group("attrs")
    class_match = CLASS_RE.search(attrs)
    if class_match:
        classes = class_match.group("value").split()
        if "pt-platform" not in classes:
            classes.append("pt-platform")
        quote = class_match.group(1)
        replacement = f"class={quote}{' '.join(classes)}{quote}"
        attrs = attrs[: class_match.start()] + replacement + attrs[class_match.end() :]
    else:
        attrs = f'{attrs} class="pt-platform"'

    if "data-pt-normalized" not in attrs:
        attrs += f' data-pt-normalized="{SHELL_VERSION}"'

    opening = f"<body{attrs}>"
    return source[: match.start()] + opening + source[match.end() :], True


def normalize_file(path: Path, *, check_only: bool) -> Result:
    relative = path.relative_to(ROOT).as_posix()
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Result(relative, "error", f"not UTF-8: {exc}")

    if MARKER in original:
        normalized, has_body = normalize_body(original)
        if not has_body:
            return Result(relative, "error", "missing <body>")
        if normalized == original:
            return Result(relative, "current")
        if check_only:
            return Result(relative, "needs-update", "body marker drift")
        path.write_text(normalized, encoding="utf-8", newline="\n")
        return Result(relative, "updated", "repaired body marker")

    if not HEAD_CLOSE_RE.search(original):
        return Result(relative, "skipped", "missing </head>")

    normalized, has_body = normalize_body(original)
    if not has_body:
        return Result(relative, "skipped", "missing <body>")

    injection = head_injection(path, normalized)
    normalized = HEAD_CLOSE_RE.sub(injection + "</head>", normalized, count=1)

    if check_only:
        return Result(relative, "needs-update")

    path.write_text(normalized, encoding="utf-8", newline="\n")
    return Result(relative, "updated")


def write_report(results: list[Result], *, check_only: bool) -> None:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    report = {
        "schema_version": 1,
        "shell_version": SHELL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "check" if check_only else "write",
        "root": ".",
        "counts": counts,
        "results": [asdict(result) for result in results],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report pages that need migration without modifying them",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write reports/platform-normalization.json",
    )
    args = parser.parse_args()

    results = [normalize_file(path, check_only=args.check) for path in production_html_files()]
    if not args.no_report:
        write_report(results, check_only=args.check)

    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))

    errors = [result for result in results if result.status == "error"]
    pending = [result for result in results if result.status == "needs-update"]
    if errors:
        for result in errors:
            print(f"ERROR {result.path}: {result.detail}", file=sys.stderr)
        return 2
    if args.check and pending:
        for result in pending[:50]:
            print(f"NEEDS_UPDATE {result.path}", file=sys.stderr)
        if len(pending) > 50:
            print(f"... and {len(pending) - 50} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
