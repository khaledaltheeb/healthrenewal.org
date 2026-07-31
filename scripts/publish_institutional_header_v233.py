from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path

VERSION = 233
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_PATH = "/"

SECTION_LINKS = (
    ("ابدأ من هنا", "start-here/"),
    ("الموسوعة", "encyclopedia/"),
    ("المقارنات", "comparisons/"),
    ("المكتبة", "library/"),
    ("أدلة التعامل", "care-guides/"),
    ("ذوو الاحتياجات الخاصة", "special-needs/"),
    ("الطفل", "sectors/child/"),
    ("الأسرة", "sectors/family/"),
    ("العائلة", "sectors/home/"),
    ("منصة التقييم", "provider-assessment-demo/"),
    ("API", "api/"),
    ("الثقة والمنهجية", "trust/"),
)

LANGUAGE_LINKS = (
    ("العربية", BASE_PATH, "ar", "rtl", True),
    ("English", BASE_PATH + "en/", "en", "ltr", False),
    ("Español", BASE_PATH + "es/", "es", "ltr", False),
)

STYLE = r'''<style id="institutional-header-v233-styles">
header.institutional-header{position:sticky;inset-block-start:0;z-index:80;border-block-end:1px solid #bfded9;background:rgba(255,255,255,.97);box-shadow:0 8px 28px rgba(16,76,76,.08);backdrop-filter:blur(16px)}
.institutional-header .header-shell{display:flex;align-items:center;justify-content:space-between;gap:22px;min-height:78px;padding-block:10px}
.institutional-header .institutional-brand{display:flex;align-items:center;gap:12px;min-width:0;color:var(--ink,#103e43);text-decoration:none}
.institutional-header .institutional-brand img{flex:0 0 auto;width:52px;height:52px}
.institutional-header .brand-copy{display:grid;min-width:0;line-height:1.35}
.institutional-header .brand-copy strong{font-size:clamp(.96rem,1.5vw,1.12rem);font-weight:900}
.institutional-header .brand-copy small{color:var(--muted,#526f73);font-size:.78rem;font-weight:700}
.institutional-nav{display:flex;align-items:center;justify-content:flex-end;gap:10px;flex:0 0 auto}
.header-menu{position:relative}
.header-menu>summary{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:46px;padding:9px 15px;border:1px solid #b7d9d4;border-radius:13px;background:#fff;color:var(--ink,#103e43);font-weight:900;cursor:pointer;list-style:none;user-select:none;transition:border-color .18s ease,background .18s ease,box-shadow .18s ease}
.header-menu>summary::-webkit-details-marker{display:none}
.header-menu>summary:hover,.header-menu[open]>summary{border-color:#55bfb7;background:#effaf8;box-shadow:0 8px 22px rgba(16,76,76,.09)}
.header-menu>summary:focus-visible{outline:3px solid #0a8b82;outline-offset:3px}
.menu-caret{font-size:1.08rem;line-height:1;transition:transform .18s ease}
.header-menu[open] .menu-caret{transform:rotate(180deg)}
.language-summary{display:grid;text-align:start;line-height:1.15}
.language-summary small{color:var(--muted,#526f73);font-size:.7rem;font-weight:700}
.language-summary strong{font-size:.9rem}
.header-menu-panel{position:absolute;inset-block-start:calc(100% + 11px);inset-inline-end:0;z-index:95;padding:18px;border:1px solid #b9ddd8;border-radius:18px;background:#fff;box-shadow:0 24px 60px rgba(14,63,67,.18)}
.sections-panel{width:min(760px,calc(100vw - 36px))}
.language-panel{width:230px}
.menu-heading{margin:0 0 12px;color:var(--muted,#526f73);font-size:.86rem;font-weight:800}
.sections-list,.language-list{margin:0;padding:0;list-style:none}
.sections-list{display:grid;grid-template-columns:repeat(2,minmax(230px,1fr));gap:7px}
.sections-list a,.language-list a{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:44px;padding:10px 12px;border-radius:11px;color:var(--ink,#103e43);font-weight:850;text-decoration:none}
.sections-list a::after{content:"←";color:#168f88;font-weight:900}
.sections-list a:hover,.language-list a:hover,.sections-list a:focus-visible,.language-list a:focus-visible{background:#effaf8;color:#075f5b;outline:none}
.language-list{display:grid;gap:5px}
.language-list a[aria-current="page"]{background:#effaf8;color:#075f5b}
.language-list a[aria-current="page"]::after{content:"✓";font-weight:900}
@media(max-width:900px){
  .institutional-header .header-shell{display:grid;grid-template-columns:1fr;gap:9px;padding-block:9px 12px}
  .institutional-header .institutional-brand{justify-content:center;text-align:center}
  .institutional-nav{display:grid;grid-template-columns:minmax(0,1fr) minmax(150px,.56fr);width:100%;gap:8px}
  .header-menu>summary{width:100%}
  .header-menu-panel{inset-inline:0;width:100%;max-height:min(66vh,540px);overflow:auto}
  .sections-list{grid-template-columns:1fr}
  .language-panel{width:100%}
}
@media(max-width:520px){
  .institutional-header .institutional-brand img{width:46px;height:46px}
  .institutional-header .brand-copy strong{font-size:.9rem}
  .institutional-header .brand-copy small{font-size:.7rem}
  .institutional-nav{grid-template-columns:1fr}
  .header-menu-panel{position:relative;inset:auto;margin-block-start:8px;box-shadow:0 12px 32px rgba(14,63,67,.14)}
}
@media(prefers-reduced-motion:reduce){.header-menu>summary,.menu-caret{transition:none}}
</style>'''


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_section_links() -> str:
    return "".join(
        f'<li><a href="{BASE_PATH}{esc(route)}">{esc(label)}</a></li>'
        for label, route in SECTION_LINKS
    )


def render_language_links() -> str:
    links: list[str] = []
    for label, href, language, direction, current in LANGUAGE_LINKS:
        current_attr = ' aria-current="page"' if current else ""
        links.append(
            f'<li><a lang="{language}" dir="{direction}" href="{esc(href)}"{current_attr}>{esc(label)}</a></li>'
        )
    return "".join(links)


def render_header() -> str:
    return f'''<header class="institutional-header" aria-label="الترويسة الرئيسية" data-institutional-header-v233>
  <div class="wrap header-shell">
    <a class="institutional-brand" href="{BASE_PATH}" aria-label="العودة إلى الصفحة الرئيسية لمنصة الصحة النفسية وذوي الاحتياجات الخاصة">
      <img src="{BASE_PATH}assets/brand/logo-mark.svg" width="52" height="52" alt="">
      <span class="brand-copy"><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong><small>مصطلحات علم النفس — معرفة تحترم الإنسان</small></span>
    </a>
    <nav class="institutional-nav" aria-label="التنقل الرئيسي">
      <details class="header-menu sections-menu">
        <summary><span>أقسام المنصة</span><span class="menu-caret" aria-hidden="true">⌄</span></summary>
        <div class="header-menu-panel sections-panel">
          <p class="menu-heading">انتقل مباشرة إلى القسم الذي تحتاجه</p>
          <ul class="sections-list">{render_section_links()}</ul>
        </div>
      </details>
      <details class="header-menu language-menu" data-i18n-switcher-v72>
        <summary><span class="language-summary"><small>اللغة</small><strong>العربية</strong></span><span class="menu-caret" aria-hidden="true">⌄</span></summary>
        <div class="header-menu-panel language-panel">
          <p class="menu-heading">اختر لغة الواجهة</p>
          <ul class="language-list">{render_language_links()}</ul>
        </div>
      </details>
    </nav>
  </div>
</header>'''


def header_pattern() -> re.Pattern[str]:
    return re.compile(
        r'<header\b[^>]*aria-label="الترويسة الرئيسية"[^>]*>.*?</header>',
        re.S,
    )


def validate(text: str) -> dict[str, object]:
    matches = header_pattern().findall(text)
    if len(matches) != 1:
        raise SystemExit(f"Expected one main header, found {len(matches)}")
    header = matches[0]
    errors: list[str] = []
    if 'data-institutional-header-v233' not in header:
        errors.append("institutional header marker is missing")
    if header.count("<details") != 2 or header.count("<summary") != 2:
        errors.append("header must contain exactly two accessible dropdowns")
    if 'data-i18n-switcher-v72' not in header:
        errors.append("language switcher compatibility marker is missing")
    for label, route in SECTION_LINKS:
        href = BASE_PATH + route
        if label not in header or f'href="{href}"' not in header:
            errors.append(f"missing section link: {label} -> {href}")
    for label, href, language, direction, _ in LANGUAGE_LINKS:
        if label not in header or f'href="{href}"' not in header:
            errors.append(f"missing language link: {label}")
        if f'lang="{language}"' not in header or f'dir="{direction}"' not in header:
            errors.append(f"missing language semantics: {label}")
    if '<nav class="nav"' in header:
        errors.append("legacy expanded navigation remains in the header")
    for marker in (
        'id="institutional-header-v233-styles"',
        '.sections-list{display:grid;grid-template-columns:repeat(2',
        '@media(max-width:900px)',
        '@media(max-width:520px)',
        '@media(prefers-reduced-motion:reduce)',
    ):
        if marker not in text:
            errors.append(f"missing responsive style marker: {marker}")
    if errors:
        raise SystemExit("Institutional header v233 validation failed:\n" + "\n".join(errors))
    return {
        "version": VERSION,
        "status": "passed",
        "section_links": len(SECTION_LINKS),
        "language_links": len(LANGUAGE_LINKS),
        "dropdowns": 2,
        "desktop_dropdown_navigation": True,
        "responsive": True,
        "keyboard_native_details": True,
        "reduced_motion_supported": True,
        "i18n_switcher_compatible": True,
    }


def publish(site: Path | str = SITE) -> dict[str, object]:
    target = Path(site).resolve()
    index = target / "index.html"
    if not index.is_file():
        raise SystemExit(f"Missing generated homepage: {index}")
    before = index.read_text(encoding="utf-8")
    pattern = header_pattern()
    if len(pattern.findall(before)) != 1:
        raise SystemExit("Homepage header is missing or ambiguous")
    after = pattern.sub(render_header(), before, count=1)
    if 'id="institutional-header-v233-styles"' not in after:
        if "</head>" not in after:
            raise SystemExit("Homepage head closing tag is missing")
        after = after.replace("</head>", STYLE + "\n</head>", 1)
    report = validate(after)
    report["changed"] = after != before
    report["before_sha256"] = hashlib.sha256(before.encode("utf-8")).hexdigest()
    report["after_sha256"] = hashlib.sha256(after.encode("utf-8")).hexdigest()
    index.write_text(after, encoding="utf-8")
    api = target / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "institutional-header-v233.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(publish(), ensure_ascii=False, indent=2))
