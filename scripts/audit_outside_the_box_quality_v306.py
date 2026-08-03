#!/usr/bin/env python3
"""Audit and publish the post-publication quality report for outside-the-box v306.

The auditor runs after the v254 condition publisher, v302 ten-plan publisher,
v303 reference publisher and v305 scientific-review publisher. It verifies the
rendered output, not only source JSON. Scientific gaps remain disclosed warnings;
they are never converted into false approval or accreditation claims.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
SECTION = "outside-the-box"
ROUTE = "quality-audit"
VERSION = 306
UPDATED = "2026-07-27"
SITEMAP_NAME = "sitemap-outside-the-box.xml"
HUB_START = "<!-- outside-the-box-quality-audit-v306-hub:start -->"
HUB_END = "<!-- outside-the-box-quality-audit-v306-hub:end -->"
REVIEW_START = "<!-- outside-the-box-quality-audit-v306-review:start -->"
REVIEW_END = "<!-- outside-the-box-quality-audit-v306-review:end -->"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def replace_marker(text: str, start: str, end: str, block: str) -> str:
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f"Malformed marker block: {start}")
        left, rest = text.split(start, 1)
        _, right = rest.split(end, 1)
        return left + block + right
    if "</main>" not in text:
        raise ValueError("Page main element was not found")
    return text.replace("</main>", block + "\n</main>", 1)


def internal_target(site: Path, page: Path, href: str) -> Path | None:
    value = html.unescape(href).strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"}:
        if not value.startswith(BASE):
            return None
        raw = parsed.path
    elif parsed.scheme or parsed.netloc:
        return None
    else:
        raw = parsed.path
    raw = unquote(raw)
    if not raw:
        return None
    if raw.startswith(BASE_PATH):
        target = site / raw[len(BASE_PATH):]
    elif raw.startswith("/"):
        return None
    else:
        target = page.parent / raw
    if raw.endswith("/") or target.is_dir() or not target.suffix:
        target = target / "index.html"
    return target.resolve()


def required_reference_routes() -> tuple[str, ...]:
    return (
        "index.html",
        "methodology/index.html",
        "monitoring-matrix/index.html",
        "ten-plan-methodology/index.html",
        "instruments/index.html",
        "evidence-standard/index.html",
        "review-governance/index.html",
        "quality-audit/index.html",
    )


def condition_contract_errors(text: str, condition: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if len(re.findall(r"<h1\b", text)) != 1:
        failures.append("h1-count")
    if '<html lang="ar" dir="rtl">' not in text:
        failures.append("arabic-document-shell")
    if text.count('rel="canonical"') != 1:
        failures.append("canonical-count")
    expected = BASE + SECTION + "/" + condition["slug"] + "/"
    match = re.search(r'<link rel="canonical" href="([^"]+)"', text)
    if not match or match.group(1) != expected:
        failures.append("canonical-value")
    if not re.search(r'<meta name="description" content="[^"].+?"', text):
        failures.append("meta-description")
    if "application/ld+json" not in text:
        failures.append("structured-data")
    if text.count('data-ten-plan="') != 10:
        failures.append("ten-plan-count")
    if text.count("outside-the-box-review-governance-v305-condition:start") != 1:
        failures.append("review-governance-marker")
    if f"../review-governance/#condition-{condition['slug']}" not in text:
        failures.append("review-governance-link")
    for marker in (
        "متى تستخدم؟",
        "متى لا تستخدم؟",
        "خط الأساس",
        "الجرعة أو الوتيرة",
        "جودة التنفيذ",
        "قاعدة التوقف أو التصعيد",
        "موعد إعادة القرار",
    ):
        if text.count(marker) < 10:
            failures.append("missing-plan-field:" + marker)
    forbidden = (
        "معاقين",
        "شفاء مضمون",
        "نتيجة مضمونة",
        "اعتماد عالمي مكتمل",
        "مراجعة خارجية مكتملة",
        "كل المصابين متفوقون",
        "الخطة تصلح للجميع",
    )
    found = [term for term in forbidden if term in text]
    if found:
        failures.append("unsafe-language:" + ",".join(found))
    return failures


def scan_links(site: Path, pages: Iterable[Path]) -> tuple[int, list[dict[str, str]]]:
    checked = 0
    broken: list[dict[str, str]] = []
    site_root = site.resolve()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            checked += 1
            target = internal_target(site, page, href)
            if target is None:
                continue
            try:
                target.relative_to(site_root)
            except ValueError:
                broken.append({"page": page.relative_to(site).as_posix(), "href": href})
                continue
            if not target.is_file():
                broken.append({"page": page.relative_to(site).as_posix(), "href": href})
    return checked, broken


def audit(site: Path) -> dict[str, Any]:
    site = site.resolve()
    source = load_json(CONDITIONS_PATH)
    conditions = source["conditions"]
    root = site / SECTION
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for relative in required_reference_routes():
        if not (root / relative).is_file():
            errors.append({"code": "missing-reference-route", "path": f"{SECTION}/{relative}"})

    canonical_seen: dict[str, str] = {}
    metrics: list[dict[str, Any]] = []
    for condition in conditions:
        path = root / condition["slug"] / "index.html"
        if not path.is_file():
            errors.append({"code": "missing-condition-page", "slug": condition["slug"]})
            continue
        text = path.read_text(encoding="utf-8")
        failures = condition_contract_errors(text, condition)
        canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        canonical = canonical_match.group(1) if canonical_match else ""
        if canonical in canonical_seen:
            failures.append("duplicate-canonical")
        elif canonical:
            canonical_seen[canonical] = condition["slug"]
        if failures:
            errors.append({"code": "condition-page-contract", "slug": condition["slug"], "failures": failures})
        metrics.append(
            {
                "rank": condition["rank"],
                "slug": condition["slug"],
                "title_ar": condition["title_ar"],
                "plans": text.count('data-ten-plan="'),
                "review_marker": text.count("outside-the-box-review-governance-v305-condition:start"),
                "canonical": canonical,
                "errors": failures,
            }
        )

    pages = sorted(path for path in root.rglob("index.html") if path.parent.name != ROUTE)
    links_checked, broken_links = scan_links(site, pages)
    if broken_links:
        errors.append({"code": "broken-internal-links", "count": len(broken_links), "examples": broken_links[:25]})

    hub_path = root / "index.html"
    hub = hub_path.read_text(encoding="utf-8") if hub_path.is_file() else ""
    missing_conditions = [item["slug"] for item in conditions if f'href="{item["slug"]}/"' not in hub]
    if missing_conditions:
        errors.append({"code": "missing-hub-condition-links", "count": len(missing_conditions), "examples": missing_conditions[:20]})
    for route in ("ten-plan-methodology/", "instruments/", "evidence-standard/", "review-governance/", "quality-audit/"):
        if route not in hub:
            errors.append({"code": "missing-hub-reference-link", "route": route})

    review_path = root / "review-governance/index.html"
    review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    if review_text.count("data-review-condition=") != 100:
        errors.append({"code": "review-dashboard-row-count", "count": review_text.count("data-review-condition=")})
    if "../quality-audit/" not in review_text:
        errors.append({"code": "review-dashboard-quality-link"})

    api254 = load_json(site / "api/outside-the-box-v254.json")
    api302 = load_json(site / "api/outside-the-box-ten-plans-v302.json")
    api303 = load_json(site / "api/outside-the-box-reference-assets-v303.json")
    api301 = load_json(site / "api/outside-the-box-evidence-standard-v301.json")
    api305 = load_json(site / "api/outside-the-box-review-governance-v305.json")
    api_checks = {
        "v254_condition_count": api254.get("condition_count") == 100 and len(api254.get("conditions", [])) == 100,
        "v302_plan_count": api302.get("condition_count") == 100 and api302.get("total_plan_instances") == 1000,
        "v303_reference_assets": api303.get("status") == "passed" and int(api303.get("instrument_count", 0)) > 0,
        "v301_evidence_standard": api301.get("applies_to", {}).get("condition_count") == 100,
        "v305_review_register": api305.get("claim_review_count") == 600 and api305.get("plan_review_count") == 1000,
        "v305_honest_status": api305.get("independent_reviews_recorded") == 0 and api305.get("external_review_completed") is False,
    }
    failed_api = [name for name, passed in api_checks.items() if not passed]
    if failed_api:
        errors.append({"code": "api-parity", "failures": failed_api})

    sitemap_path = site / SITEMAP_NAME
    sitemap_urls: list[str] = []
    if not sitemap_path.is_file():
        errors.append({"code": "missing-sitemap", "path": SITEMAP_NAME})
    else:
        sitemap_urls = [
            (node.text or "").strip()
            for node in ET.parse(sitemap_path).getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        if len(sitemap_urls) != len(set(sitemap_urls)):
            errors.append({"code": "duplicate-sitemap-urls"})
        expected_urls = {
            BASE + SECTION + "/",
            BASE + SECTION + "/ten-plan-methodology/",
            BASE + SECTION + "/instruments/",
            BASE + SECTION + "/evidence-standard/",
            BASE + SECTION + "/review-governance/",
            BASE + SECTION + "/quality-audit/",
            *{BASE + SECTION + "/" + item["slug"] + "/" for item in conditions},
        }
        missing_urls = sorted(expected_urls - set(sitemap_urls))
        if missing_urls:
            errors.append({"code": "missing-sitemap-urls", "count": len(missing_urls), "examples": missing_urls[:20]})

    css = site / "assets/css/outside-the-box-review-governance-v305.css"
    if not css.is_file() or "@media(max-width" not in css.read_text(encoding="utf-8"):
        errors.append({"code": "responsive-review-css"})

    migration = api305.get("source_contract_migration", {})
    missing_metadata = int(migration.get("records_missing_full_contract_metadata", 0))
    if missing_metadata:
        warnings.append(
            {
                "code": "source-contract-migration-incomplete",
                "count": missing_metadata,
                "message": "المصادر مرتبطة بالمحتوى، لكن بعض سجلاتها تحتاج سنة ونوع مصدر وتاريخ تحقق وحالة وادعاءات مدعومة."
            }
        )
    warnings.append(
        {
            "code": "independent-review-incomplete",
            "count": 100,
            "message": "المراجعة التخصصية المستقلة لكل حالة وخطة لم تكتمل بعد، ولا يحول التدقيق التقني المحتوى إلى اعتماد سريري."
        }
    )

    return {
        "version": VERSION,
        "updated_at": UPDATED,
        "status": "passed-with-disclosed-warnings" if not errors else "failed",
        "critical_error_count": len(errors),
        "warning_count": len(warnings),
        "condition_count": len(conditions),
        "condition_pages_audited": len(metrics),
        "outside_the_box_pages_audited": len(pages),
        "plan_cards_audited": sum(item["plans"] for item in metrics),
        "review_markers_audited": sum(item["review_marker"] for item in metrics),
        "internal_links_checked": links_checked,
        "broken_internal_link_count": len(broken_links),
        "unique_canonical_count": len(canonical_seen),
        "sitemap_url_count": len(sitemap_urls),
        "api_checks": api_checks,
        "errors": errors,
        "warnings": warnings,
        "condition_metrics": metrics,
        "external_review_completed": False,
        "global_accreditation_claim": False,
    }


def render_warning_cards(warnings: list[dict[str, Any]]) -> str:
    return "".join(
        f'<article class="rg-card"><span class="rg-risk high">فجوة معلنة</span><h3>{e(item["code"])}</h3><p>{e(item["message"])}</p><p><strong>العدد:</strong> {e(item["count"])}</p></article>'
        for item in warnings
    )


def render_page(report: dict[str, Any]) -> str:
    api_rows = "".join(
        f'<tr><td>{e(name)}</td><td>{"ناجح" if passed else "فاشل"}</td></tr>'
        for name, passed in report["api_checks"].items()
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "headline": "تدقيق الجودة والتنسيق والربط لمسارات 100 حالة",
        "dateModified": UPDATED,
        "inLanguage": "ar",
        "url": BASE + SECTION + "/" + ROUTE + "/",
    }
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>تدقيق الجودة والربط | مسارات 100 حالة</title><meta name="description" content="تقرير شفاف يفحص 100 حالة و1000 خطة والروابط وSEO والإتاحة وتطابق واجهات البيانات وخرائط الموقع.">
<meta name="robots" content="index,follow"><link rel="canonical" href="{BASE}{SECTION}/{ROUTE}/"><link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-review-governance-v305.css"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head>
<body class="rg-page"><a class="rg-skip" href="#main">تجاوز إلى المحتوى</a><header class="rg-header"><div class="rg-wrap rg-header-inner"><a class="rg-brand" href="{BASE_PATH}">منصة روافد</a><nav class="rg-nav" aria-label="التنقل"><a href="../">المسارات</a><a href="../review-governance/">المراجعة العلمية</a><a aria-current="page" href="./">تدقيق الجودة</a></nav></div></header>
<main id="main"><section class="rg-hero"><div class="rg-wrap"><p class="rg-kicker">فحص بعد الحقن والربط</p><h1>تدقيق الجودة والتنسيق والربط لمسارات 100 حالة</h1><p class="rg-lead">يفحص التقرير المخرج المنشور نفسه، لا ملفات المصدر فقط. نجاحه يعني اكتمال العقد التقني والمنهجي المحدد، ولا يعني اعتمادًا سريريًا أو مراجعة تخصصية مستقلة.</p>
<div class="rg-notice"><strong>النتيجة:</strong> {e(report['status'])}. الأخطاء الحرجة: {report['critical_error_count']}، والتحذيرات المعلنة: {report['warning_count']}.</div>
<div class="rg-metrics"><div><strong>{report['condition_pages_audited']}</strong><span>صفحة حالة</span></div><div><strong>{report['plan_cards_audited']}</strong><span>بطاقة خطة</span></div><div><strong>{report['outside_the_box_pages_audited']}</strong><span>صفحة في القسم</span></div><div><strong>{report['broken_internal_link_count']}</strong><span>رابط داخلي مكسور</span></div><div><strong>{report['unique_canonical_count']}</strong><span>Canonical فريد للحالات</span></div></div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">تطابق الآلات</p><h2>واجهات البيانات والعقود</h2><div class="rg-table-wrap"><table class="rg-table"><thead><tr><th>الفحص</th><th>النتيجة</th></tr></thead><tbody>{api_rows}</tbody></table></div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">ثغرات لا تُخفى</p><h2>التحذيرات العلمية المتبقية</h2><div class="rg-grid">{render_warning_cards(report['warnings'])}</div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">نطاق الفحص</p><h2>ما الذي تم تدقيقه؟</h2><article class="rg-card"><ul><li>عدد الحالات والخطط وحقول التشغيل وحالة المراجعة.</li><li>H1 والوصف وCanonical والبيانات المنظمة واللغة والاتجاه.</li><li>الروابط الداخلية والبوابة والصفحات المرجعية وخرائط الموقع.</li><li>تطابق APIs للإصدارات 254 و301 و302 و303 و305.</li><li>اللغة المسؤولة ومنع الادعاءات المطلقة والاعتماد الزائف.</li><li>التصميم المتجاوب وربط المراجعة والتصحيح القابل للتتبع.</li></ul></article></div></section></main>
<footer class="rg-footer"><div class="rg-wrap"><p>آخر تدقيق: {UPDATED}. <a href="../review-governance/">سجل المراجعة العلمية</a> · <a href="../evidence-standard/">معيار الأدلة</a> · <a href="../instruments/">سجل الأدوات</a></p></div></footer></body></html>"""


def update_sitemap(site: Path) -> None:
    path = site / SITEMAP_NAME
    if not path.is_file():
        raise ValueError("Outside-the-box sitemap is missing")
    tree = ET.parse(path)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].lstrip("{") if root.tag.startswith("{") else "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    q = lambda name: f"{{{namespace}}}{name}"
    target = BASE + SECTION + "/" + ROUTE + "/"
    current = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc") if node.text}
    if target not in current:
        item = ET.SubElement(root, q("url"))
        ET.SubElement(item, q("loc")).text = target
        ET.SubElement(item, q("lastmod")).text = UPDATED
        ET.SubElement(item, q("changefreq")).text = "weekly"
        ET.SubElement(item, q("priority")).text = "0.80"
    tree.write(path, encoding="utf-8", xml_declaration=True)


def patch_summary(site: Path, report: dict[str, Any]) -> None:
    summary = {
        "version": VERSION,
        "route": BASE + SECTION + "/" + ROUTE + "/",
        "status": report["status"],
        "critical_error_count": report["critical_error_count"],
        "warning_count": report["warning_count"],
        "condition_pages_audited": report["condition_pages_audited"],
        "plan_cards_audited": report["plan_cards_audited"],
        "broken_internal_link_count": report["broken_internal_link_count"],
    }
    for relative in (
        "api/outside-the-box-v254.json",
        "api/outside-the-box-ten-plans-v302.json",
        "api/outside-the-box-review-governance-v305.json",
    ):
        path = site / relative
        payload = load_json(path)
        payload["quality_audit"] = summary
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    root = site / SECTION
    if not root.is_dir():
        raise ValueError("Outside-the-box section is missing")

    target = root / ROUTE
    target.mkdir(parents=True, exist_ok=True)
    placeholder = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تدقيق الجودة</title></head><body><main><h1>تدقيق الجودة</h1></main></body></html>'
    if not (target / "index.html").is_file():
        (target / "index.html").write_text(placeholder, encoding="utf-8")

    hub_path = root / "index.html"
    hub_block = f"""{HUB_START}<section class="rg-section" data-quality-audit-v306><div class="rg-wrap"><p class="rg-kicker">تدقيق بعد النشر</p><h2>فحص اكتمال الصفحات والروابط والواجهات</h2><p class="rg-muted">اجتاز القسم تدقيقًا للصفحات المئة والخطط الألف والروابط وSEO والإتاحة وتطابق واجهات البيانات، مع إبقاء الفجوات العلمية معلنة.</p><div class="rg-actions"><a class="rg-button secondary" href="{ROUTE}/">فتح تقرير الجودة</a></div></div></section>{HUB_END}"""
    hub_path.write_text(replace_marker(hub_path.read_text(encoding="utf-8"), HUB_START, HUB_END, hub_block), encoding="utf-8")

    review_path = root / "review-governance/index.html"
    review_block = f"""{REVIEW_START}<section class="rg-section" data-quality-audit-v306><div class="rg-wrap"><p class="rg-kicker">تدقيق التكامل</p><h2>العقد التقني والمنهجي مفحوص</h2><p class="rg-muted">الأخطاء الحرجة في المخرج الحالي: 0. لا يغير ذلك حالة المراجعة التخصصية المستقلة، التي تبقى غير مكتملة ومعلنة.</p><div class="rg-actions"><a class="rg-button secondary" href="../{ROUTE}/">فتح تقرير التدقيق</a></div></div></section>{REVIEW_END}"""
    review_path.write_text(replace_marker(review_path.read_text(encoding="utf-8"), REVIEW_START, REVIEW_END, review_block), encoding="utf-8")
    update_sitemap(site)

    report = audit(site)
    if report["critical_error_count"]:
        raise ValueError(json.dumps(report["errors"], ensure_ascii=False, indent=2))

    quality_html = render_page(report)
    if quality_html.count("<h1") != 1 or 'rel="canonical"' not in quality_html or '<html lang="ar" dir="rtl">' not in quality_html:
        raise ValueError("Quality audit page shell is incomplete")
    (target / "index.html").write_text(quality_html, encoding="utf-8")

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "outside-the-box-quality-audit-v306.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    patch_summary(site, report)

    final = audit(site)
    if final["critical_error_count"]:
        raise ValueError(json.dumps(final["errors"], ensure_ascii=False, indent=2))
    stable_fields = (
        "condition_pages_audited",
        "plan_cards_audited",
        "review_markers_audited",
        "internal_links_checked",
        "broken_internal_link_count",
        "unique_canonical_count",
        "sitemap_url_count",
    )
    if any(final[field] != report[field] for field in stable_fields):
        raise ValueError({field: (report[field], final[field]) for field in stable_fields if report[field] != final[field]})
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(
        json.dumps(
            {
                "version": report["version"],
                "status": report["status"],
                "condition_pages_audited": report["condition_pages_audited"],
                "plan_cards_audited": report["plan_cards_audited"],
                "broken_internal_link_count": report["broken_internal_link_count"],
                "critical_error_count": report["critical_error_count"],
                "warning_count": report["warning_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
