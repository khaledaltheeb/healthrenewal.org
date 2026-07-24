#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
NAV_ID = "hidden-collection-links-v217"
BREADCRUMB_MARKER = "data-hidden-collection-breadcrumb-v217"
EXPECTED_MINIMUMS = {
    "comparisons": 101,
    "library": 61,
    "guided-assessment": 101,
    "hubs": 201,
    "assessments": 4,
    "cognitive-tests": 9,
    "sections": 1,
}
REQUIRED_KEYWORDS = {
    "comparisons": {"مقارنات نفسية", "الفرق بين الاضطرابات النفسية"},
    "library": {"المكتبة النفسية", "المكتبة الأكاديمية"},
    "guided-assessment": {"أسئلة التقييم النفسي", "الاستكشاف النفسي"},
    "hubs": {"مراكز موضوعية نفسية", "موضوعات علم النفس"},
    "assessments": {"المقاييس النفسية", "الاختبارات النفسية"},
    "cognitive-tests": {"الاختبارات المعرفية", "القدرات المعرفية"},
    "sections": {"أقسام الصحة النفسية", "دليل منصة الصحة النفسية"},
}
BANNED = (
    "مولدة أثناء البناء", "مولّد أثناء البناء", "لا تظهر في القوائم",
    "خطة العمل", "ما تم إنجازه", "سيتم إنجازه", "قيد التطوير",
    "قيد الإعداد", "قيد التوسع", "لا نشر قبل البوابات",
)


def keyword_values(source: str) -> list[str]:
    match = re.search(
        r'<meta\b[^>]*name=(["\'])keywords\1[^>]*content=(["\'])(.*?)\2',
        source,
        re.I | re.S,
    )
    if not match:
        return []
    return [item.strip() for item in match.group(3).replace("،", ",").split(",") if item.strip()]


def main() -> None:
    report_path = SITE / "api" / "hidden-collections-seo-v217.json"
    if not report_path.is_file():
        raise SystemExit("Hidden collections SEO report is missing")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed" or report.get("version") != 217:
        raise SystemExit(f"Unexpected hidden collections report: {report}")

    errors: list[str] = []
    pages_checked = 0
    breadcrumb_scripts = 0
    for root, minimum in EXPECTED_MINIMUMS.items():
        pages = sorted((SITE / root).rglob("*.html"))
        if len(pages) < minimum:
            errors.append(f"{root}: expected at least {minimum} pages, found {len(pages)}")
        for page in pages:
            relative = page.relative_to(SITE).as_posix()
            source = page.read_text(encoding="utf-8")
            keywords = keyword_values(source)
            if len(keywords) < 7:
                errors.append(f"{relative}: only {len(keywords)} keyword phrases")
            if len(keywords) != len(set(keywords)):
                errors.append(f"{relative}: duplicate keyword phrases")
            if not REQUIRED_KEYWORDS[root].intersection(keywords):
                errors.append(f"{relative}: route-specific keywords missing")
            if source.count(f'id="{NAV_ID}"') != 1:
                errors.append(f"{relative}: related navigation count is not one")
            if source.count(BREADCRUMB_MARKER) != 1:
                errors.append(f"{relative}: breadcrumb marker count is not one")
            if f'rel="up" href="https://khaledaltheeb.github.io/pterminology-site/{root}/"' not in source:
                errors.append(f"{relative}: rel=up is missing")
            if 'title="دليل أقسام المنصة"' not in source or 'api/v1/sections.json' not in source:
                errors.append(f"{relative}: sections API discovery link is missing")
            if any(phrase in source for phrase in BANNED):
                errors.append(f"{relative}: operational copy leaked")
            match = re.search(
                rf'<script\b[^>]*{BREADCRUMB_MARKER}[^>]*>(.*?)</script>',
                source,
                re.I | re.S,
            )
            if match:
                try:
                    payload = json.loads(match.group(1))
                    if payload.get("@type") != "BreadcrumbList" or len(payload.get("itemListElement", [])) < 2:
                        errors.append(f"{relative}: breadcrumb schema is incomplete")
                except json.JSONDecodeError as exc:
                    errors.append(f"{relative}: invalid breadcrumb JSON-LD: {exc}")
                breadcrumb_scripts += 1
            pages_checked += 1

    if pages_checked != report.get("pages_scanned"):
        errors.append(f"Report pages_scanned={report.get('pages_scanned')} but verifier found {pages_checked}")
    if breadcrumb_scripts != pages_checked:
        errors.append(f"Breadcrumb scripts {breadcrumb_scripts} != pages {pages_checked}")
    if errors:
        raise SystemExit("\n".join(errors[:200]))

    verification = {
        "version": 217,
        "status": "passed",
        "collections": len(EXPECTED_MINIMUMS),
        "pages_checked": pages_checked,
        "breadcrumb_scripts": breadcrumb_scripts,
        "keyword_contract": True,
        "related_navigation_contract": True,
        "operational_copy_absent": True,
    }
    (SITE / "api" / "hidden-collections-seo-v217-verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
