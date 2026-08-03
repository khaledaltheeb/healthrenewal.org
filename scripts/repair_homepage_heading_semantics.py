#!/usr/bin/env python3
"""Repair and validate semantic heading structure on the institutional homepage."""
from __future__ import annotations

import argparse
import re
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


def plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def repair(text: str) -> tuple[str, int]:
    changes = 0

    def convert_item_title(match: re.Match[str]) -> str:
        nonlocal changes
        changes += 1
        quote = match.group("quote")
        attrs = match.group("attrs")
        body = match.group("body")
        return f'<h3 class={quote}item-title{quote}{attrs}>{body}</h3>'

    text = ITEM_TITLE_RE.sub(convert_item_title, text)

    occurrences: dict[str, int] = {}

    def disambiguate_heading(match: re.Match[str]) -> str:
        nonlocal changes
        level = match.group("level")
        attrs = match.group("attrs")
        body = match.group("body")
        heading = plain_text(body)
        names = DUPLICATE_RENAMES.get(heading)
        if not names:
            return match.group(0)
        index = occurrences.get(heading, 0)
        occurrences[heading] = index + 1
        replacement = names[min(index, len(names) - 1)]
        if replacement == heading:
            return match.group(0)
        changes += 1
        return f"<h{level}{attrs}>{replacement}</h{level}>"

    text = HEADING_RE.sub(disambiguate_heading, text)
    return text, changes


def validate(text: str) -> None:
    h1_count = len(re.findall(r"<h1\b", text, re.IGNORECASE))
    h2_count = len(re.findall(r"<h2\b", text, re.IGNORECASE))
    h3_count = len(re.findall(r"<h3\b", text, re.IGNORECASE))
    residual_item_paragraphs = len(ITEM_TITLE_RE.findall(text))
    headings = [plain_text(match.group("body")) for match in HEADING_RE.finditer(text)]
    duplicate_headings = sorted({heading for heading in headings if headings.count(heading) > 1})

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
    if duplicate_headings:
        raise SystemExit(f"Homepage contains duplicate heading text: {duplicate_headings}")


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
    print({"status": "passed", "semantic_repairs": changed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
