#!/usr/bin/env python3
"""Repair and validate semantic heading structure on the institutional homepage."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ITEM_TITLE_RE = re.compile(
    r'<p\s+class=(?P<quote>["\'])item-title(?P=quote)(?P<attrs>[^>]*)>'
    r'(?P<body>.*?)</p\s*>',
    re.IGNORECASE | re.DOTALL,
)


def repair(text: str) -> tuple[str, int]:
    def replacement(match: re.Match[str]) -> str:
        quote = match.group("quote")
        attrs = match.group("attrs")
        body = match.group("body")
        return f'<h3 class={quote}item-title{quote}{attrs}>{body}</h3>'

    return ITEM_TITLE_RE.subn(replacement, text)


def validate(text: str) -> None:
    h1_count = len(re.findall(r"<h1\b", text, re.IGNORECASE))
    h2_count = len(re.findall(r"<h2\b", text, re.IGNORECASE))
    h3_count = len(re.findall(r"<h3\b", text, re.IGNORECASE))
    residual_item_paragraphs = len(ITEM_TITLE_RE.findall(text))

    if h1_count != 1:
        raise SystemExit(f"Expected exactly one homepage H1, found {h1_count}")
    if h2_count < 4:
        raise SystemExit(f"Expected at least four homepage H2 headings, found {h2_count}")
    if h3_count < 16:
        raise SystemExit(f"Expected at least sixteen homepage H3 headings, found {h3_count}")
    if residual_item_paragraphs:
        raise SystemExit(
            f"Homepage still contains {residual_item_paragraphs} paragraph-based item titles"
        )


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
        raise SystemExit(f"Homepage requires {changed} semantic heading repairs")

    validate(text)
    print({"status": "passed", "converted_item_titles": changed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
