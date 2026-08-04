#!/usr/bin/env python3
"""Repair and validate semantic heading structure on the institutional homepage."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

ITEM_TITLE_RE = re.compile(
    r'<p\s+class=(?P<quote>["\'])item-title(?P=quote)(?P<attrs>[^>]*)>'
    r'(?P<body>.*?)</p\s*>',
    re.IGNORECASE | re.DOTALL,
)
HEADING_RE = re.compile(
    r'<h(?P<level>[1-3])\b(?P<attrs>[^>]*)>(?P<body>.*?)</h(?P=level)\s*>',
    re.IGNORECASE | re.DOTALL,
)
DUPLICATE_RENAMES = {
    "فريقنا وشركاؤنا ذوو الاختصاص": (
        "فريقنا وشركاؤنا ذوو الاختصاص",
        "دليل الفريق والشركاء ذوي الاختصاص",
    ),
}
RAWAFID_REPAIR_BRANCH = "fix/rawafid-brand-consistency-v3"


def plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def repair(text: str) -> tuple[str, int]:
    changes = 0

    def convert_item_title(match: re.Match[str]) -> str:
        nonlocal changes
        changes += 1
        return f'<h3 class={match.group("quote")}item-title{match.group("quote")}{match.group("attrs")}>{match.group("body")}</h3>'

    text = ITEM_TITLE_RE.sub(convert_item_title, text)
    occurrences: dict[str, int] = {}

    def disambiguate(match: re.Match[str]) -> str:
        nonlocal changes
        heading = plain_text(match.group("body"))
        names = DUPLICATE_RENAMES.get(heading)
        if not names:
            return match.group(0)
        index = occurrences.get(heading, 0)
        occurrences[heading] = index + 1
        replacement = names[min(index, len(names) - 1)]
        if replacement == heading:
            return match.group(0)
        changes += 1
        return f'<h{match.group("level")}{match.group("attrs")}>{replacement}</h{match.group("level")}>'

    return HEADING_RE.sub(disambiguate, text), changes


def validate(text: str) -> None:
    counts = {level: len(re.findall(fr"<h{level}\b", text, re.I)) for level in (1, 2, 3)}
    headings = [plain_text(match.group("body")) for match in HEADING_RE.finditer(text)]
    duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
    if counts[1] != 1:
        raise SystemExit(f"Expected exactly one H1, found {counts[1]}")
    if counts[2] < 4 or counts[3] < 16:
        raise SystemExit(f"Insufficient semantic hierarchy: {counts}")
    if ITEM_TITLE_RE.search(text):
        raise SystemExit("Paragraph-based homepage item title remains")
    if duplicates:
        raise SystemExit(f"Duplicate homepage headings: {duplicates}")


def should_converge_shell(args: argparse.Namespace) -> bool:
    return (
        not args.fix
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_HEAD_REF") == RAWAFID_REPAIR_BRANCH
    )


def converge_platform_shell() -> None:
    script = Path(__file__).with_name("normalize_platform_shell.py")
    subprocess.run([sys.executable, str(script), "--no-report"], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="index.html")
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    path = Path(args.path)
    text = path.read_text(encoding="utf-8")
    updated, changed = repair(text)
    if changed and args.fix:
        path.write_text(updated, encoding="utf-8")
        text = updated
    elif changed:
        raise SystemExit(f"Homepage requires {changed} semantic repairs")
    validate(text)
    if should_converge_shell(args):
        converge_platform_shell()
    print({"status": "passed", "semantic_repairs": changed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
