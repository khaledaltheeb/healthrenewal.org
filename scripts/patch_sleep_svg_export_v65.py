from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"
RUNTIME = SITE / "assets" / "sleep-log-v49.js"
SVG_LABEL = "اتجاهات النوم والجودة والطاقة. الوصف النصي المتجدد يظهر قبل الرسم."
EMPTY_CHART_OLD = "لا توجد بيانات كافية لعرض مخطط الاتجاهات."
EMPTY_CHART_ACCESSIBLE = (
    "اتجاهات النوم والجودة والطاقة: "
    "لا توجد بيانات كافية لعرض مخطط الاتجاهات."
)
STATIC_ARIA_ASSIGNMENT = "chart.setAttribute('aria-label', CHART_ACCESSIBLE_NAME);"
DYNAMIC_ARIA_ASSIGNMENT = "chart.setAttribute('aria-label', description);"
SUMMARY_ASSIGNMENTS = (
    "summaryElement.textContent =",
    "summaryNode.textContent =",
    "document.querySelector('[data-sleep-summary]').textContent =",
)


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


def patch_runtime_accessibility() -> bool:
    if not RUNTIME.is_file():
        raise SystemExit(f"Missing generated sleep runtime: {RUNTIME}")
    source = RUNTIME.read_text(encoding="utf-8")
    changed = False

    if EMPTY_CHART_ACCESSIBLE not in source:
        target = f"return '{EMPTY_CHART_OLD}';"
        replacement = f"return '{EMPTY_CHART_ACCESSIBLE}';"
        if source.count(target) != 1:
            raise SystemExit("Sleep runtime empty-chart description is missing or ambiguous")
        source = source.replace(target, replacement, 1)
        changed = True

    static_count = source.count(STATIC_ARIA_ASSIGNMENT)
    dynamic_count = source.count(DYNAMIC_ARIA_ASSIGNMENT)
    if static_count == 0:
        if dynamic_count != 1:
            raise SystemExit("Sleep runtime dynamic chart label is missing or ambiguous")
        source = source.replace(DYNAMIC_ARIA_ASSIGNMENT, STATIC_ARIA_ASSIGNMENT, 1)
        changed = True
    elif static_count != 1 or dynamic_count:
        raise SystemExit("Sleep runtime stable chart label is duplicated or conflicts with a dynamic label")

    summary_count = sum(source.count(marker) for marker in SUMMARY_ASSIGNMENTS)
    if summary_count != 1:
        raise SystemExit(
            "Sleep runtime summary update must use exactly one supported assignment"
        )

    if changed:
        RUNTIME.write_text(source, encoding="utf-8")
    return changed


def patch() -> None:
    if not PAGE.is_file():
        raise SystemExit(f"Missing generated sleep page: {PAGE}")

    text = PAGE.read_text(encoding="utf-8")
    if "sleep-log-v49.js" not in text:
        raise SystemExit("Generated sleep page does not load sleep-log-v49.js")

    text, page_changed = patch_chart_accessibility(text)
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
    runtime_changed = patch_runtime_accessibility()
    print(
        {
            "status": "passed",
            "chart_accessibility_normalized": True,
            "page_changed": page_changed,
            "runtime_changed": runtime_changed,
            "stable_chart_accessible_name": True,
            "visible_chart_description_updates": True,
            "sleep_summary_preserved": True,
            "summary_assignment_count": 1,
        }
    )


if __name__ == "__main__":
    patch()
