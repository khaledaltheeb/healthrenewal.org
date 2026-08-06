#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import publish_self_advocacy_base_v170 as base

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "learning-paths" / "self-advocacy"
HISTORICAL_GOVERNANCE_FILE = "source-verification-initial-audit.json"
VERSION = 171

PUBLIC_PACKAGES = base.PUBLIC_PACKAGES
GOVERNANCE_FILE = base.GOVERNANCE_FILE
TARGET_RELATIVE = base.TARGET_RELATIVE
CANONICAL_ROUTE = base.CANONICAL_ROUTE
CANONICAL_URL = base.CANONICAL_URL
START = base.START
END = base.END


def historical_section(data: dict[str, Any]) -> str:
    selected = {
        key: value
        for key, value in data.items()
        if key in {
            "editorial_scope", "professional_limits", "decision_support_workflow",
            "editorial_claims", "practice_questions", "sources", "claim_governance",
        }
    }
    body = "".join(base.render_value(key, value) for key, value in selected.items())
    return (
        '<section class="self-advocacy-package self-advocacy-governance-history" '
        'data-source-governance="source-verification-initial-audit.json" '
        'aria-labelledby="self-advocacy-governance-history">'
        '<h2 id="self-advocacy-governance-history">السجل المرجعي والادعاءات المدعومة</h2>'
        '<p>يُحفظ التدقيق الأول كسجل تاريخي للمصادر والادعاءات. حالة معالجة ملاحظات الإتاحة يحددها السجل الحالي واختبار الإنتاج، لا الحالة القديمة المحفوظة هنا.</p>'
        f'{body}</section>'
    )


def validate_accessibility_contract(site: Path, page_html: str) -> dict[str, Any]:
    section_details = re.findall(
        r'<section\b[^>]*class=["\'][^"\']*\bdetails\b[^"\']*["\'][^>]*>',
        page_html,
        flags=re.I,
    )
    native_details = len(re.findall(r'<details\b', page_html, flags=re.I))
    native_summaries = len(re.findall(r'<summary\b', page_html, flags=re.I))
    main_has_id = bool(re.search(r'<main\b[^>]*\bid=["\'][^"\']+["\']', page_html, flags=re.I))

    js_path = site / "assets" / "platform" / "platform-core.js"
    css_path = site / "assets" / "platform" / "platform-core.css"
    if not js_path.is_file() or not css_path.is_file():
        raise SystemExit("Missing shared platform accessibility assets in _site")
    js = js_path.read_text(encoding="utf-8", errors="replace")
    css = css_path.read_text(encoding="utf-8", errors="replace")

    checks = {
        "mainHasStableId": main_has_id,
        "unlabelledSectionDetails": len(section_details),
        "nativeDetailsCount": native_details,
        "nativeSummaryCount": native_summaries,
        "nativeDetailsNamed": native_details == native_summaries,
        "skipLinkCreatedByPlatformJs": (
            "doc.querySelector('.pt-skip-link')" in js
            and "body.prepend(skip)" in js
            and "ensureMainId" in js
        ),
        "skipLinkStyledInPlatformCss": (
            ".pt-skip-link" in css and ".pt-skip-link:focus" in css
        ),
    }
    if (
        not checks["mainHasStableId"]
        or checks["unlabelledSectionDetails"] != 0
        or not checks["nativeDetailsNamed"]
        or not checks["skipLinkCreatedByPlatformJs"]
        or not checks["skipLinkStyledInPlatformCss"]
    ):
        raise SystemExit({"selfAdvocacyAccessibilityContract": checks})
    return checks


def publish(site: Path) -> dict[str, Any]:
    historical_path = SOURCE_DIR / HISTORICAL_GOVERNANCE_FILE
    if not historical_path.is_file():
        raise SystemExit(f"Missing historical source governance: {historical_path}")
    historical = base.load_json(historical_path)
    base.validate_package(historical_path, historical)

    report = base.publish(site)
    target = site / base.TARGET_RELATIVE
    page = target.read_text(encoding="utf-8", errors="replace")
    if HISTORICAL_GOVERNANCE_FILE not in page:
        page = page.replace(base.END, historical_section(historical) + "\n" + base.END, 1)
        target.write_text(page, encoding="utf-8")

    accessibility = validate_accessibility_contract(site, page)
    report.update({
        "version": VERSION,
        "sourcePackageCount": len(base.PUBLIC_PACKAGES) + 1,
        "totalEvidenceFiles": len(base.PUBLIC_PACKAGES) + 2,
        "governancePackageCount": 2,
        "historicalGovernancePackageCount": 1,
        "sectionsRendered": len(base.PUBLIC_PACKAGES) + 2,
        "historicalGovernanceRecord": HISTORICAL_GOVERNANCE_FILE,
        "currentGovernanceRecord": base.GOVERNANCE_FILE,
        "accessibilityStatus": "passed",
        "accessibilityChecks": accessibility,
        "outputBytes": len(page.encode("utf-8")),
    })
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    for filename in ("self-advocacy-v170.json", "self-advocacy-v171.json"):
        (api / filename).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
