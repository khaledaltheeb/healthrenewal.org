#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STYLE_START = "<!-- practical-tips-v248-search-visibility:start -->"
STYLE_END = "<!-- practical-tips-v248-search-visibility:end -->"
STYLE_ID = "practical-tips-v248-search-visibility"
CONTRACT = "hidden-important-v248"
EXPECTED_CARDS = 100
ACCESS_CSS_START = "/* practical-tips-v253-accessibility:start */"
ACCESS_CSS_END = "/* practical-tips-v253-accessibility:end */"
ACCESS_CONTRACT = "contrast-and-scroll-focus-v253"
SAFE_BRAND = "#0b5f59"
SAFE_BADGE_TEXT = "#123d42"
SCROLL_REGION_LABEL = "جدول متابعة قابل للتمرير"


def _style_block() -> str:
    return f"""
{STYLE_START}
<style id="{STYLE_ID}">
[data-search][hidden]{{display:none!important}}
.tip237-badges span,.tip237-card>span{{color:{SAFE_BADGE_TEXT}!important}}
</style>
{STYLE_END}
""".strip()


def _accessibility_css_block() -> str:
    return f"""
{ACCESS_CSS_START}
:root{{--tip237-brand:{SAFE_BRAND}}}
.tip237-table-wrap:focus-visible{{outline:3px solid {SAFE_BRAND};outline-offset:4px}}
{ACCESS_CSS_END}
""".strip()


def _normalize_search_visibility(index: Path) -> tuple[str, int]:
    source = index.read_text(encoding="utf-8")
    source = re.sub(
        r"[ \t]*\n?"
        + re.escape(STYLE_START)
        + r".*?"
        + re.escape(STYLE_END)
        + r"[ \t]*\n?",
        "",
        source,
        flags=re.S,
    )
    if "</head>" not in source.lower():
        raise RuntimeError("Practical tips index head closing tag is missing")
    source = re.sub(r"</head>", _style_block() + "\n</head>", source, count=1, flags=re.I)
    index.write_text(source, encoding="utf-8")

    verified = index.read_text(encoding="utf-8")
    card_count = len(re.findall(r"\bdata-search\s*=", verified, flags=re.I))
    if card_count != EXPECTED_CARDS:
        raise RuntimeError(f"Search visibility requires one hundred cards: {card_count}")
    if verified.count(STYLE_START) != 1 or verified.count(STYLE_END) != 1:
        raise RuntimeError("Search visibility style is missing or duplicated")
    if verified.count(f'id="{STYLE_ID}"') != 1:
        raise RuntimeError("Search visibility style id is missing or duplicated")
    if "[data-search][hidden]{display:none!important}" not in verified:
        raise RuntimeError("Search visibility important rule is missing")
    if f".tip237-badges span,.tip237-card>span{{color:{SAFE_BADGE_TEXT}!important}}" not in verified:
        raise RuntimeError("Practical tips badge contrast rule is missing")
    return verified, card_count


def _normalize_accessibility_css(root: Path) -> None:
    css_path = root / "assets" / "css" / "practical-tips-v237.css"
    if not css_path.is_file():
        raise RuntimeError(f"Practical tips stylesheet is missing: {css_path}")
    source = css_path.read_text(encoding="utf-8")
    source = re.sub(
        r"[ \t]*\n?"
        + re.escape(ACCESS_CSS_START)
        + r".*?"
        + re.escape(ACCESS_CSS_END)
        + r"[ \t]*\n?",
        "",
        source,
        flags=re.S,
    ).rstrip()
    source += "\n" + _accessibility_css_block() + "\n"
    css_path.write_text(source, encoding="utf-8")

    verified = css_path.read_text(encoding="utf-8")
    if verified.count(ACCESS_CSS_START) != 1 or verified.count(ACCESS_CSS_END) != 1:
        raise RuntimeError("Practical tips accessibility CSS is missing or duplicated")
    if f"--tip237-brand:{SAFE_BRAND}" not in verified:
        raise RuntimeError("Practical tips safe link color is missing")


def _focus_scroll_regions(root: Path) -> int:
    region_pattern = re.compile(
        r'<div\b(?=[^>]*\bclass=(["\'])[^"\']*\btip237-table-wrap\b[^"\']*\1)[^>]*>',
        flags=re.I,
    )

    def normalize_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        attributes = (
            ("tabindex", "0"),
            ("role", "region"),
            ("aria-label", SCROLL_REGION_LABEL),
        )
        for name, value in attributes:
            if not re.search(rf"\b{re.escape(name)}\s*=", tag, flags=re.I):
                tag = tag[:-1] + f' {name}="{value}">'
        return tag

    total = 0
    pages = sorted((root / "tips").glob("*/index.html"))
    for page in pages:
        source = page.read_text(encoding="utf-8")
        updated, count = region_pattern.subn(normalize_tag, source)
        if count:
            page.write_text(updated, encoding="utf-8")
            total += count

    for page in pages:
        source = page.read_text(encoding="utf-8")
        for match in region_pattern.finditer(source):
            tag = match.group(0)
            for required in (
                'tabindex="0"',
                'role="region"',
                f'aria-label="{SCROLL_REGION_LABEL}"',
            ):
                if required not in tag:
                    raise RuntimeError(f"Scrollable practical tips region lacks {required}: {page}")
    return total


def finalize(site: Path | str) -> dict:
    root = Path(site)
    index = root / "tips" / "index.html"
    report_path = root / "api" / "practical-tips-v237.json"
    if not index.is_file():
        raise RuntimeError(f"Practical tips index is missing: {index}")
    if not report_path.is_file():
        raise RuntimeError(f"Practical tips report is missing: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_report = {
        "version": 237,
        "status": "passed",
        "guide_count": EXPECTED_CARDS,
        "search_contract": "local-normalized-filter-v248",
        "search_cards": EXPECTED_CARDS,
    }
    for key, expected in expected_report.items():
        if report.get(key) != expected:
            raise RuntimeError(
                f"Search visibility prerequisite failed: key={key}, "
                f"expected={expected!r}, actual={report.get(key)!r}"
            )

    _, card_count = _normalize_search_visibility(index)
    _normalize_accessibility_css(root)
    scroll_regions = _focus_scroll_regions(root)

    report = dict(report)
    report["search_visibility_contract"] = CONTRACT
    report["search_visibility_cards"] = card_count
    report["accessibility_contract"] = ACCESS_CONTRACT
    report["accessibility_link_color"] = SAFE_BRAND
    report["accessibility_badge_text_color"] = SAFE_BADGE_TEXT
    report["accessible_scroll_regions"] = scroll_regions
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    print(json.dumps(finalize(site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
