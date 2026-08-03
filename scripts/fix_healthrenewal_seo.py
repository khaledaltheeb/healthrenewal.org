#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
OLD_ORIGIN = "https://healthrenewal.org/"
NEW_ORIGIN = "https://healthrenewal.org"
PUBLIC_SUFFIXES = {".html", ".htm", ".xml", ".json", ".webmanifest", ".txt"}
SKIP_TOP_LEVEL = {
    ".git",
    ".github",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "scripts",
    "tests",
    "docs",
}


class SeoMigrationError(RuntimeError):
    pass


def is_public_text_candidate(path: Path) -> bool:
    if path.resolve() == SELF:
        return False
    relative = path.relative_to(ROOT)
    if relative.parts and relative.parts[0] in SKIP_TOP_LEVEL:
        return False
    return path.suffix.lower() in PUBLIC_SUFFIXES or path.name == "CNAME"


def update_text_file(path: Path, transform) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    updated = transform(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def migrate_origin(text: str) -> str:
    return text.replace(OLD_ORIGIN, NEW_ORIGIN)


def transform_homepage(html: str) -> str:
    html = migrate_origin(html)

    old_h1 = (
        "<h1>المعرفة ليست صفحات مبعثرة.<br>"
        "<span>إنها طريق واضح إلى الخطوة التالية.</span></h1>"
    )
    new_h1 = (
        "<h1>منصة روافد<br>"
        "<span>معرفة موثقة وأدلة وأدوات تقود إلى الخطوة التالية.</span></h1>"
    )
    html = html.replace(old_h1, new_h1)
    html = html.replace(
        '<p class="lead">تجمع المنصة الموسوعة النفسية،',
        '<p class="lead">منصة روافد هي بوابة عربية مؤسسية تجمع الموسوعة النفسية،',
    )

    logo_alt = "شعار منصة روافد"
    html = html.replace('alt="" width="52" height="52"', f'alt="{logo_alt}" width="52" height="52"')
    html = html.replace('alt="" width="54" height="54"', f'alt="{logo_alt}" width="54" height="54"')

    # Card and journey labels are visual labels, not sections in the document outline.
    html = html.replace(".journey h3{", ".journey .item-title{")
    html = html.replace(".card h3{", ".card .item-title{")
    html = html.replace(".principle h3{", ".principle .item-title{")
    if "<h3>" in html:
        html = html.replace("<h3>", '<p class="item-title">').replace("</h3>", "</p>")

    html = html.replace(
        ".footer p{color:var(--muted)}",
        ".footer p{color:var(--muted)}.footer-title{font-weight:900}",
    )
    html = html.replace(
        "<p><strong>منصة روافد</strong><br>",
        '<p><span class="footer-title">منصة روافد</span><br>',
    )

    html = html.replace('href="assessment-lab/">فتح المختبر</a>', 'href="assessment-lab/">فتح مختبر المقاييس</a>')
    html = html.replace('href="cognitive-lab/">فتح المختبر</a>', 'href="cognitive-lab/">فتح مختبر القدرات</a>')

    def rewrite_footer(match: re.Match[str]) -> str:
        prefix, body, suffix = match.groups()
        replacements = {
            ">الموسوعة<": ">دليل الموسوعة<",
            ">ذوو الاحتياجات الخاصة<": ">مركز ذوي الاحتياجات الخاصة<",
            ">المكتبة<": ">المكتبة الأكاديمية<",
            ">مسارات التعلم<": ">دليل مسارات التعلم<",
            ">الفريق والشركاء<": ">بوابة الفريق والشركاء<",
            ">المطورون<": ">بوابة المطورين<",
        }
        for old, new in replacements.items():
            body = body.replace(old, new)
        return prefix + body + suffix

    html = re.sub(
        r'(<nav class="footer-links"[^>]*>)(.*?)(</nav>)',
        rewrite_footer,
        html,
        flags=re.DOTALL,
    )

    if 'data-seo-external-sources="v1"' not in html:
        external_section = '''
<section class="section external-sources" data-seo-external-sources="v1" aria-labelledby="external-sources-title"><p class="eyebrow">مراجع دولية رسمية</p><h2 id="external-sources-title">مصادر موثوقة لمتابعة الأدلة والمعايير</h2><p class="section-intro">تُستخدم هذه المراجع الدولية كبوابات تحقق عامة، بينما توثّق كل صفحة متخصصة مصادرها المباشرة وحدود الاستدلال بها.</p><div class="principles"><article class="principle"><p class="item-title">منظمة الصحة العالمية</p><p>الموضوعات والإرشادات العامة المتعلقة بالصحة النفسية.</p><a href="https://www.who.int/health-topics/mental-health" rel="external noopener noreferrer">مرجع الصحة النفسية لدى منظمة الصحة العالمية</a></article><article class="principle"><p class="item-title">اليونيسف</p><p>موارد الإدماج وحقوق الأطفال ذوي الإعاقة ودعم الأسرة.</p><a href="https://www.unicef.org/disabilities" rel="external noopener noreferrer">موارد الإعاقة والإدماج لدى اليونيسف</a></article><article class="principle"><p class="item-title">الأمم المتحدة</p><p>الإطار الحقوقي الدولي لاتفاقية حقوق الأشخاص ذوي الإعاقة.</p><a href="https://www.un.org/development/desa/disabilities/convention-on-the-rights-of-persons-with-disabilities.html" rel="external noopener noreferrer">اتفاقية حقوق الأشخاص ذوي الإعاقة</a></article></div></section>
'''
        marker = "\n</div></main>"
        if marker not in html:
            raise SeoMigrationError("Could not locate homepage main-content closing marker")
        html = html.replace(marker, external_section + marker, 1)

    if 'name="twitter:image:alt"' not in html:
        html = html.replace(
            '<meta name="twitter:image" content="https://healthrenewal.org/assets/brand/rawafid-social-card.jpg">',
            '<meta name="twitter:image" content="https://healthrenewal.org/assets/brand/rawafid-social-card.jpg">\n'
            '<meta name="twitter:image:alt" content="شعار منصة روافد">',
        )

    return html


def main() -> int:
    changed: list[Path] = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or not is_public_text_candidate(path):
            continue
        transform = transform_homepage if path == ROOT / "index.html" else migrate_origin
        if update_text_file(path, transform):
            changed.append(path)

    robots = ROOT / "robots.txt"
    desired_robots = (
        "# Public crawling and indexing policy\n"
        "User-agent: *\n"
        "Allow: /\n\n"
        "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
    )
    if robots.read_text(encoding="utf-8") != desired_robots:
        robots.write_text(desired_robots, encoding="utf-8")
        if robots not in changed:
            changed.append(robots)

    validator = ROOT / "scripts" / "validate_sitemap_discovery_contract.py"
    if validator.is_file():
        validator_text = validator.read_text(encoding="utf-8")
        validator_updated = validator_text.replace(
            'PUBLIC_ORIGIN = "https://healthrenewal.org"',
            'PUBLIC_ORIGIN = "https://healthrenewal.org"',
        ).replace(
            'BASE_PATH = "/"',
            'BASE_PATH = "/"',
        )
        if validator_updated != validator_text:
            validator.write_text(validator_updated, encoding="utf-8")
            changed.append(validator)

    legacy_hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not is_public_text_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if OLD_ORIGIN in text:
            legacy_hits.append(str(path.relative_to(ROOT)))

    if legacy_hits:
        raise SeoMigrationError(
            "Legacy GitHub Pages origin remains in public files: " + ", ".join(legacy_hits[:30])
        )

    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    required_fragments = [
        '<link rel="canonical" href="https://healthrenewal.org/">',
        '<link rel="alternate" hreflang="ar" href="https://healthrenewal.org/">',
        '<h1>منصة روافد<br>',
        'data-seo-external-sources="v1"',
        'alt="شعار منصة روافد"',
    ]
    missing = [fragment for fragment in required_fragments if fragment not in homepage]
    if missing:
        raise SeoMigrationError("Homepage SEO migration incomplete: " + " | ".join(missing))

    print(f"SEO migration complete; changed {len(changed)} public files.")
    for path in sorted(changed):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
