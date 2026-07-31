from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_CONTRACT = 219
SEO_CONTRACT = 219


def require(text: str, pattern: str, message: str) -> None:
    if not re.search(pattern, text, re.I | re.S):
        raise AssertionError(message)


def visible_word_count(text: str) -> int:
    cleaned = re.sub(r"<(script|style|svg)\b[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    return len(re.findall(r"[\w\u0600-\u06ff]+", cleaned, re.UNICODE))


def write_minimal_sitemap(site: Path) -> None:
    site.mkdir(parents=True, exist_ok=True)
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
        encoding="utf-8",
    )
    (site / "index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head><title>منصة اختبار</title>'
        '<meta name="keywords" content="الصحة النفسية">'
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":"https://healthrenewal.org/#home","hasPart":[]}]}'
        '</script></head><body><nav><a href="provider-assessment-demo/">منصة التقييم</a></nav>'
        '<article><a href="cognitive-tests/">فتح المهام</a></article></body></html>',
        encoding="utf-8",
    )


def finalize_generated_shell(site: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/patch_sleep_svg_export_v65.py"), str(site)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/apply_daily_tools_marshmallow_v219.py"), str(site)],
        check=True,
    )


def verify_generated_page(site: Path) -> int:
    page = site / "daily-tools/sleep-wind-down-plan/index.html"
    if not page.is_file():
        raise AssertionError("sleep log page was not generated")

    text = page.read_text(encoding="utf-8")
    js = (ROOT / "assets/sleep-log-v49.js").read_text(encoding="utf-8")
    require(text, r'<html[^>]+lang="ar"[^>]+dir="rtl"', "Arabic RTL root missing")
    require(text, rf'data-design="marshmallow-v{DESIGN_CONTRACT}"', "marshmallow design contract missing")
    require(text, rf'data-seo="institutional-v{SEO_CONTRACT}"', "institutional SEO contract missing")
    for marker in ("--mint:#e5faf5", "--rose:#fff0f5", "--lilac:#f2edff", "--peach:#fff0e8", "--butter:#fff8d8"):
        require(text, re.escape(marker), f"marshmallow palette marker missing: {marker}")
    for marker, message in (
        (r'<meta name="keywords"', "topic keywords missing"),
        (r'<meta name="robots"', "robots metadata missing"),
        (r'<link rel="manifest"', "manifest discovery missing"),
        (r'<link rel="icon"', "icon discovery missing"),
        (r'<link rel="search"', "OpenSearch discovery missing"),
        (r'<link rel="sitemap"', "sitemap discovery missing"),
        (r'property="og:image"', "Open Graph image missing"),
        (r'name="twitter:card"', "Twitter card missing"),
        (r'name="twitter:image"', "Twitter image missing"),
        (r'type="application/ld\+json"', "structured data missing"),
        (r'"@type":"WebApplication"', "WebApplication schema missing"),
    ):
        require(text, marker, message)
    if text.count('<meta name="description"') != 1:
        raise AssertionError("sleep log must keep exactly one description")
    if text.count('<link rel="canonical"') != 1:
        raise AssertionError("sleep log must keep exactly one canonical")
    if "text-shadow" in text.lower() or "rgba(0,0,0" in text.replace(" ", "").lower():
        raise AssertionError("dark text-box shadow regression detected")
    require(text, r"data-sleep-log", "interactive form missing")
    require(text, r'role="status"[^>]+aria-live="polite"', "live status missing")
    require(text, r"غير تشخيص", "non-diagnostic boundary missing")
    require(text, r"لا تُرسل البيانات إلى خادم", "local privacy statement missing")
    require(text, r"data-delete-sleep", "delete-all control missing")
    require(text, r"data-export-json", "JSON export missing")
    require(text, r"data-export-csv", "CSV export missing")
    require(text, r"data-print-sleep", "print control missing")
    require(text, r"sleep-log-v49\.js", "sleep runtime missing")
    require(text, r"prefers-reduced-motion", "reduced motion support missing")
    require(text, r"@media print", "print stylesheet missing")
    require(text, r"min-height:44px", "touch target baseline missing")
    require(text, r"خدمات الطوارئ المحلية", "urgent-help route missing")
    require(text, r"كيف تقرأ السجل دون مبالغة", "interpretation guidance missing")
    require(text, r"خطة استخدام لمدة أسبوعين", "two-week use plan missing")
    require(text, r"ما الذي يُفعل وما الذي يُتجنب", "do and avoid guidance missing")
    require(text, r"متى تحتاج إلى مساعدة مهنية", "professional-help section missing")
    require(text, r"أسئلة شائعة", "FAQ section missing")
    require(text, r"آخر مراجعة تحريرية:</strong>\s*22 يوليو 2026", "review date missing")
    for source in (
        "nhlbi.nih.gov/resources/sleep-diary",
        "nhlbi.nih.gov/health/insomnia/diagnosis",
        "aasm.org/clinical-resources/practice-standards/practice-guidelines",
        "cdc.gov/sleep/data-research/facts-stats/adults-sleep-facts-and-stats",
    ):
        require(text, re.escape(source), f"authoritative source missing: {source}")
    words = visible_word_count(text)
    if words < 800:
        raise AssertionError(f"sleep log explanatory content remains thin: {words} visible words")
    for field in ("date", "bedtime", "wakeTime", "quality", "energy", "note"):
        require(
            text,
            rf'name="{field}"[^>]+aria-describedby="[^"]+"',
            f"{field} must reference its error message",
        )
        require(text, rf'data-field-error="{field}"', f"{field} error container missing")
    require(js, r"setAttribute\('aria-invalid',\s*'true'\)", "invalid fields must expose aria-invalid")
    require(js, r"firstInvalid\.focus\(\)", "focus must move to the first invalid field")
    require(js, r"data-field-error", "field error rendering missing")
    require(js, r"data-export-sleep-chart", "SVG export control runtime missing")
    require(js, r"sleep-chart-export-privacy", "SVG privacy disclosure binding missing")
    require(js, r"يتضمن ملف SVG تواريخ النوم ومدته ودرجات الجودة والطاقة", "SVG exported fields disclosure missing")
    require(js, r"لا يتضمن الملاحظات النصية", "SVG notes exclusion disclosure missing")
    require(js, r"راجع الملف قبل مشاركته", "SVG review-before-sharing guidance missing")
    require(js, r"المشاركة اختيارية وخارج التخزين المحلي", "optional external sharing boundary missing")
    require(js, r"chartSvgDocument", "SVG generation runtime missing")
    if "fetch(" in js:
        raise AssertionError("network transmission is not allowed")
    return words


def main() -> None:
    production_site = ROOT / "_site"
    production_page = production_site / "daily-tools/sleep-wind-down-plan/index.html"
    if production_page.is_file():
        finalize_generated_shell(production_site)
        verify_generated_page(production_site)

    with tempfile.TemporaryDirectory(prefix="sleep-log-v49-") as tmp:
        site = Path(tmp) / "_site"
        write_minimal_sitemap(site)

        subprocess.run(
            [sys.executable, str(ROOT / "scripts/publish_daily_tools_v24.py"), str(site)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/publish_sleep_log_v49.py"), str(site)],
            check=True,
        )
        finalize_generated_shell(site)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_daily_tools_v24.py"), str(site)],
            check=True,
        )
        words = verify_generated_page(site)

    subprocess.run(["node", str(ROOT / "tests/test_sleep_log_v49.mjs")], check=True)
    print(
        f"sleep-log-v49 verification passed with {words} visible words, "
        f"marshmallow-v{DESIGN_CONTRACT}, and institutional SEO v{SEO_CONTRACT}"
    )


if __name__ == "__main__":
    main()
