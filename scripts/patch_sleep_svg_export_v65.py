from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"
SVG_LABEL = "اتجاهات النوم والجودة والطاقة. الوصف النصي المتجدد يظهر قبل الرسم."


def patch_chart_accessibility(text: str) -> tuple[str, bool]:
    old_pattern = re.compile(
        r'(<svg\b(?=[^>]*\bdata-sleep-chart\b)(?=[^>]*\brole="img")[^>]*)'
        r'\s+aria-labelledby="sleep-chart-title sleep-chart-desc"([^>]*>)'
        r'\s*<title\s+id="sleep-chart-title">.*?</title>'
        r'\s*<desc\s+id="sleep-chart-desc">.*?</desc>',
        re.I | re.S,
    )
    replacement = rf'\1 aria-label="{SVG_LABEL}"\2'
    updated, count = old_pattern.subn(replacement, text, count=1)
    if count == 1:
        return updated, True

    current_pattern = re.compile(
        r'<svg\b(?=[^>]*\bdata-sleep-chart\b)(?=[^>]*\brole="img")'
        r'(?=[^>]*\baria-label="' + re.escape(SVG_LABEL) + r'")[^>]*>',
        re.I | re.S,
    )
    if current_pattern.search(text):
        return text, False
    raise SystemExit("Sleep chart accessibility markup is missing or ambiguous")


def patch() -> None:
    if not PAGE.is_file():
        raise SystemExit(f"Missing generated sleep page: {PAGE}")

    text = PAGE.read_text(encoding="utf-8")
    if "sleep-log-v49.js" not in text:
        raise SystemExit("Generated sleep page does not load sleep-log-v49.js")

    text, changed = patch_chart_accessibility(text)
    if 'id="sleep-chart-title"' in text or 'id="sleep-chart-desc"' in text:
        raise SystemExit("Obsolete nested SVG title or description remains")
    if text.count(f'aria-label="{SVG_LABEL}"') != 1:
        raise SystemExit("Sleep chart must expose exactly one accessible name")

    stale_markers = (
        "data-export-svg",
        'id="sleep-svg-export-privacy"',
    )
    if any(marker in text for marker in stale_markers):
        raise SystemExit("Stale static SVG export markup would duplicate JS-managed controls")

    PAGE.write_text(text, encoding="utf-8")
    print({"status": "passed", "chart_accessibility_normalized": True, "changed": changed})


if __name__ == "__main__":
    patch()
