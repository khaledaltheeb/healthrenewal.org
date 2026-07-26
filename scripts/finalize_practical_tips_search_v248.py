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


def _style_block() -> str:
    return f"""
{STYLE_START}
<style id="{STYLE_ID}">
[data-search][hidden]{{display:none!important}}
</style>
{STYLE_END}
""".strip()


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

    source = index.read_text(encoding="utf-8")
    source = re.sub(
        re.escape(STYLE_START) + r".*?" + re.escape(STYLE_END),
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

    report = dict(report)
    report["search_visibility_contract"] = CONTRACT
    report["search_visibility_cards"] = card_count
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
