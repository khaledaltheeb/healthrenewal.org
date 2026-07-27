#!/usr/bin/env python3
"""Audit, coordinate and publish the outside-the-box quality report v306.

The auditor runs after v254, v302, v303 and v305. It verifies structural completeness,
API parity, links, SEO, accessibility basics, responsible language and live-build readiness.
Disclosed scientific gaps remain warnings rather than being hidden or mislabeled as approval.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
SECTION = "outside-the-box"
ROUTE = "quality-audit"
VERSION = 306
UPDATED = "2026-07-27"
HUB_START = "<!-- outside-the-box-quality-audit-v306-hub:start -->"
HUB_END = "<!-- outside-the-box-quality-audit-v306-hub:end -->"
REVIEW_START = "<!-- outside-the-box-quality-audit-v306-review:start -->"
REVIEW_END = "<!-- outside-the-box-quality-audit-v306-review:end -->"
SITEMAP_NAME = "sitemap-outside-the-box.xml"


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
    href = html.unescape(href).strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlsplit(href)
    if parsed.scheme in {"http", "https"}:
        if not href.startswith(BASE):
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
        relative = raw[len(BASE_PATH):]
        target = site / relative
    elif raw.startswith("/"):
        return None
    else:
        target = page.parent / raw
    if raw.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.suffix:
        target = target / "index.html"
    return target.resolve()


def audit(site: Path) -> dict[str, Any]:
    source = load_json(CONDITIONS_PATH)
    conditions = source["conditions"]
    api254 = load_json(site / "api/outside-the-box-v254.json")
    api302 = load_json(site / "api/outside-the-box-ten-plans-v302.json")
    api303 = load_json(site / "api/outside-the-box-reference-assets-v303.json")
    api301 = load_json(site / "api/outside-the-box-evidence-standard-v301.json")
    api305 = load_json(site / "api/outside-the-box-review-governance-v305.json")

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    condition_metrics: list[dict[str, Any]] = []
    root = site / SECTION
    required_routes = [
        "index.html",
        "methodology/index.html",
        "monitoring-matrix/index.html",
        "ten-plan-methodology/index.html",
        "instruments/index.html",
        "evidence-standard/index.html",
        "review-governance/index.html",
    ]
    for relative in required_routes:
        if not (root / relative).is_file():
            errors.append({"code": "missing-reference-route", "path": f"{SECTION}/{relative}"})

    canonical_seen: dict[str, str] = {}
    forbidden = (
        "معاقين",
        "شفاء مضمون",
        "نتيجة مضمونة",
        "اعتماد عالمي مكتمل",
        "مراجعة خارجية مكتملة",
        "كل المصابين متفوقون",
        "الخطة تصلح للجميع",
    )
    for condition in conditions:
        path = root / condition["slug"] / "index.html"
        if not path.is_file():
            errors.append({"code": "missing-condition-page", "slug": condition["slug"]})
            continue
        text = path.read_text(encoding="utf-8")
        page_errors: list[str] = []
        if text.count("<h1") != 1:
            page_errors.append("h1-count")
        if '<html lang="ar" dir="rtl">' not in text:
            page_errors.append("arabic-document-shell")
        if text.count('rel="canonical"') != 1:
            page_errors.append("canonical-count")
        expected_canonical = BASE + SECTION + "/" + condition["slug"] + "/"
        match = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        canonical = match.group(1) if match else ""
        if canonical != expected_canonical:
            page_errors.append("canonical-value")
        if canonical and canonical in canonical_seen:
            page_errors.append("duplicate-canonical")
        if canonical:
            canonical_seen[canonical] = condition["slug"]
        if not re.search(r'<meta name="description" content="[^"].+?"', text):
            page_errors.append("meta-description")
        if "application/ld+json" not in text:
            page_errors.append("structured-data")
        if text.count('data-ten-plan="') != 10:
            page_errors.append("ten-plan-count")
        if text.count("outside-the-box-review-governance-v305-condition:start") != 1:
            page_errors.append("review-governance-marker")
        if f"../review-governance/#condition-{condition['slug']}" not in text:
            page_errors.append("review-governance-link")
        if "قاعدة التوقف" not in text or "موعد إعادة القرار" not in text:
            page_errors.append("operational-plan-fields")
        bad_terms = [term for term in forbidden if term in text]
        if bad_terms:
            page_errors.append("unsafe-language:" + ",".join(bad_terms))
        if page_errors:
            errors.append({"code": "condition-page-contract", "slug": condition["slug"], "failures": page_errors})
        condition_metrics.append(
            {
                "rank": condition["rank"],
                "slug": condition["slug"],
                "title_ar": condition["title_ar"],
                "plans": text.count('data-ten-plan="'),
                "review_marker": text.count("outside-the-box-review-governance-v305-condition:start"),
                "canonical": canonical,
                "errors": page_errors,
            }
        )

    html_pages = sorted(path for path in root.rglob("index.html") if path.parent.name != ROUTE)
    broken_links: list[dict[str, str]] = []
    outside_root = site.resolve()
    for page in html_pages:
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            target = internal_target(site, page, href)
            if target is None:
                continue
            try:
                target.relative_to(outside_root)
            except ValueError:
                broken_links.append({"page": page.relative_to(site).as_posix(), "href": href})
                continue
            if not target.is_file():
                broken_links.append({"page": page.relative_to(site).as_posix(), "href": href})
    if broken_links:
        errors.append({"code": "broken-internal-links", "count": len(broken_links), "examples": broken_links[:25]})

    hub = (root / "index.html").read_text(encoding="utf-8") if (root / "index.html").is_file() else ""
    missing_hub_links = [condition["slug"] for condition in conditions if f'href="{condition["slug"]}/"' not in hub]
    if missing_hub_links:
        errors.append({"code": "missing-hub-condition-links", "count": len(missing_hub_links), "examples": missing_hub_links[:20]})
    for route in ("ten-plan-methodology/", "instruments/", "evidence-standard/", "review-governance/"):
        if route not in hub:
            errors.append({"code": "missing-hub-reference-link", "route": route})

    review_page = (root / "review-governance/index.html").read_text(encoding="utf-8") if (root / "review-governance/index.html").is_file() else ""
    if review_page.count("data-review-condition=") != 100:
        errors.append({"code": "review-dashboard-row-count", "count": review_page.count("data-review-condition=")})

    api_checks = {
        "v254_condition_count": api254.get("condition_count") == 100 and len(api254.get("conditions", [])) == 100,
        "v302_plan_count": api302.get("condition_count") == 100 and api302.get("total_plan_instances") == 1000,
        "v303_reference_assets": api303.get("status") == "passed" and int(api303.get("instrument_count", 0)) > 0,
        "v301_evidence_standard": api301.get("applies_to", {}).get("condition_count") == 100,
        "v305_review_register": api305.get("claim_review_count") == 600 and api305.get("plan_review_count") == 1000,
        "v305_honest_status": api305.get("independent_reviews_recorded") == 0 and api305.get("external_review_completed") is False,
    }
    failed_api = [key for key, passed in api_checks.items() if not passed]
    if failed_api:
        errors.append({"code": "api-parity", "failures": failed_api})

    sitemap_path = site / SITEMAP_NAME
    if not sitemap_path.is_file():
        errors.append({"code": "missing-sitemap", "path": SITEMAP_NAME})
        sitemap_urls: list[str] = []
    else:
        sitemap_urls = [(node.text or "").strip() for node in ET.parse(sitemap_path).getroot().findall("{*}url/{*}loc") if node.text]
        if len(sitemap_urls) != len(set(sitemap_urls)):
            errors.append({"code": "duplicate-sitemap-urls"})
        expected = {
            BASE + SECTION + "/",
            BASE + SECTION + "/ten-plan-methodology/",
            BASE + SECTION + "/instruments/",
            BASE + SECTION + "/evidence-standard/",
            BASE + SECTION + "/review-governance/",
            *{BASE + SECTION + "/" + condition["slug"] + "/" for condition in conditions},
        }
        missing = sorted(expected - set(sitemap_urls))
        if missing:
            errors.append({"code": "missing-sitemap-urls", "count": len(missing), "examples": missing[:20]})

    css = site / "assets/css/outside-the-box-review-governance-v305.css"
    if not css.is_file() or "@media(max-width" not in css.read_text(encoding="utf-8"):
        errors.append({"code": "responsive-review-css"})

    source_migration = api305.get("source_contract_migration", {})
    if int(source_migration.get("records_missing_full_contract_metadata", 0)) > 0:
        warnings.append(
            {
                "code": "source-contract-migration-incomplete",
                "count": int(source_migration["records_missing_full_contract_metadata"]),
                "message": "المصادر مرتبطة بالمحتوى، لكن بعض سجلاتها ما يزال يحتاج سنة ونوع مصدر وتاريخ تحقق وحالة وادعاءات مدعومة."
            }
        )
    if api305.get("external_review_completed") is False:
        warnings.append(
            {
                "code": "independent-review-incomplete",
                "count": 100,
                "message": "المراجعة التخصصية المستقلة لكل حالة وخطة لم تكتمل بعد، ولا يجوز تحويل نجاح التدقيق التقني إلى ادعاء اعتماد سريري."
            }
        )

    return {
        "version": VERSION,
        "updated_at": UPDATED,
        "status": "passed-with-disclosed-warnings" if not errors else "failed",
        "critical_error_count": len(errors),
        "warning_count": len(warnings),
        "condition_count": len(conditions),
        "condition_pages_audited": len(condition_metrics),
        "outside_the_box_pages_audited": len(html_pages),
        "plan_cards_audited": sum(item["plans"] for item in condition_metrics),
        "review_markers_audited": sum(item["review_marker"] for item in condition_metrics),
        "internal_links_checked": sum(len(re.findall(r'href="([^"]+)"', page.read_text(encoding="utf-8"))) for page in html_pages),
        "broken_internal_link_count": len(broken_links),
        "unique_canonical_count": len(canonical_seen),
        "sitemap_url_count": len(sitemap_urls),
        "api_checks": api_checks,
        "errors": errors,
        "warnings": warnings,
        "condition_metrics": condition_metrics,
        "external_review_completed": False,
        "global_accreditation_claim": False,
    }


def render_page(report: dict[str, Any]) -> str:
    warning_cards = "".join(
        f'<article class="rg-card"><span class="rg-risk high">فجوة معلنة</span><h3>{e(item["code"])}</h3><p>{e(item["message"])}</p><p><strong>العدد:</strong> {e(item["count"])}</p></article>'
        for item in report["warnings"]
    ) or '<article class="rg-card"><h3>لا توجد تحذيرات معلنة</h3></article>'
    api_rows = "".join(
        f'<tr><td>{e(key)}</td><td>{"ناجح" if value else "فاشل"}</td></tr>'
        for key, value in report["api_checks"].items()
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
<title>تدقيق الجودة والربط | مسارات 100 حالة</title><meta name="description" content="تقرير آلي شفاف يفحص اكتمال 100 حالة و1000 خطة والروابط والبيانات المنظمة وSEO والإتاحة وتطابق واجهات البيانات وخرائط الموقع.">
<meta name="robots" content="index,follow"><link rel="canonical" href="{BASE}{SECTION}/{ROUTE}/"><link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-review-governance-v305.css"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script></head>
<body class="rg-page"><a class="rg-skip" href="#main">تجاوز إلى المحتوى</a><header class="rg-header"><div class="rg-wrap rg-header-inner"><a class="rg-brand" href="{BASE_PATH}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="rg-nav"><a href="../">المسارات</a><a href="../review-governance/">المراجعة العلمية</a><a aria-current="page" href="./">تدقيق الجودة</a></nav></div></header>
<main id="main"><section class="rg-hero"><div class="rg-wrap"><p class="rg-kicker">فحص بعد الحقن والربط</p><h1>تدقيق الجودة والتنسيق والربط لمسارات 100 حالة</h1><p class="rg-lead">يفحص هذا التقرير المخرج المنشور نفسه، لا ملفات المصدر فقط. نجاحه يعني اكتمال العقد التقني والمنهجي المحدد، ولا يعني اعتمادًا سريريًا أو مراجعة تخصصية مستقلة.</p>
<div class="rg-notice"><strong>النتيجة:</strong> {e(report['status'])}. الأخطاء الحرجة: {report['critical_error_count']}، والتحذيرات المعلنة: {report['warning_count']}.</div>
<div class="rg-metrics"><div><strong>{report['condition_pages_audited']}</strong><span>صفحة حالة</span></div><div><strong>{report['plan_cards_audited']}</strong><span>بطاقة خطة</span></div><div><strong>{report['outside_the_box_pages_audited']}</strong><span>صفحة في القسم</span></div><div><strong>{report['broken_internal_link_count']}</strong><span>رابط داخلي مكسور</span></div><div><strong>{report['unique_canonical_count']}</strong><span>Canonical فريد للحالات</span></div></div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">تطابق الآلات</p><h2>واجهات البيانات والعقود</h2><div class="rg-table-wrap"><table class="rg-table"><thead><tr><th>الفحص</th><th>النتيجة</th></tr></thead><tbody>{api_rows}</tbody></table></div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">ثغرات لا تُخفى</p><h2>التحذيرات العلمية المتبقية</h2><div class="rg-grid">{warning_cards}</div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">ماذا شمل التدقيق؟</p><h2>نطاق الفحص</h2><article class="rg-card"><ul><li>عدد الحالات والخطط وحقول التشغيل وحالة المراجعة.</li><li>العناوين وH1 والوصف وCanonical والبيانات المنظمة واللغة والاتجاه.</li><li>الروابط الداخلية والبوابة والصفحات المرجعية وخرائط الموقع.</li><li>تطابق APIs للإصدارات 254 و301 و302 و303 و305.</li><li>اللغة المسؤولة ومنع الادعاءات المطلقة أو الاعتماد الزائف.</li><li>التصميم المتجاوب ووجود بوابة مراجعة وتصحيح قابلة للتتبع.</li></ul></article></div></section></main>
<footer class="rg-footer"><div class="rg-wrap"><p>آخر تدقيق: {UPDATED}. <a href="../review-governance/">فتح سجل المراجعة العلمية</a> · <a href="../evidence-standard/">معيار الأدلة</a> · <a href="../instruments/">سجل الأدوات</a></p></div></footer></body></html>"""


def update_sitemap(site: Path) -> None:
    path = site / SITEMAP_NAME
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
        data = load_json(path)
        data["quality_audit"] = summary
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    report = audit(site)
    if report["critical_error_count"]:
        raise ValueError(json.dumps(report["errors"], ensure_ascii=False, indent=2))
    target = site / SECTION / ROUTE
    target.mkdir(parents=True, exist_ok=True)
    (target / "index.html").write_text(render_page(report), encoding="utf-8")
    root = site / SECTION
    hub_path = root / "index.html"
    hub_block = f"""{HUB_START}<section class="rg-section" data-quality-audit-v306><div class="rg-wrap"><p class="rg-kicker">تدقيق بعد النشر</p><h2>فحص اكتمال الصفحات والروابط والواجهات</h2><p class="rg-muted">اجتاز القسم تدقيقًا آليًا للصفحات المئة والخطط الألف والروابط وSEO والإتاحة وتطابق واجهات البيانات، مع إبقاء الفجوات العلمية المتبقية معلنة.</p><div class="rg-actions"><a class="rg-button secondary" href="{ROUTE}/">فتح تقرير الجودة</a></div></div></section>{HUB_END}"""
    hub_path.write_text(replace_marker(hub_path.read_text(encoding="utf-8"), HUB_START, HUB_END, hub_block), encoding="utf-8")
    review_path = root / "review-governance/index.html"
    review_block = f"""{REVIEW_START}<section class="rg-section" data-quality-audit-v306><div class="rg-wrap"><p class="rg-kicker">تدقيق التكامل</p><h2>العقد التقني والمنهجي مفحوص</h2><p class="rg-muted">الأخطاء الحرجة في المخرج الحالي: 0. هذا لا يغير حالة المراجعة التخصصية المستقلة، التي تبقى غير مكتملة ومعلنة.</p><div class="rg-actions"><a class="rg-button secondary" href="../{ROUTE}/">فتح تقرير التدقيق</a></div></div></section>{REVIEW_END}"""
    review_path.write_text(replace_marker(review_path.read_text(encoding="utf-8"), REVIEW_START, REVIEW_END, review_block), encoding="utf-8")
    update_sitemap(site)
    api = site / "api"
    (api / "outside-the-box-quality-audit-v306.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    patch_summary(site, report)
    final = audit(site)
    if final["critical_error_count"]:
        raise ValueError(json.dumps(final["errors"], ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps({
        "version": report["version"],
        "status": report["status"],
        "condition_pages_audited": report["condition_pages_audited"],
        "plan_cards_audited": report["plan_cards_audited"],
        "broken_internal_link_count": report["broken_internal_link_count"],
        "critical_error_count": report["critical_error_count"],
        "warning_count": report["warning_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
