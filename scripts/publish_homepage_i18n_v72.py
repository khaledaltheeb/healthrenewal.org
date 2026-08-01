#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "i18n" / "v72" / "homepage.json"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
LOCALES = ("en", "es")

CSS = """
:root{--ink:#173f45;--muted:#496d70;--line:#c9e9e5;--accent:#168f88;--accent2:#9d4168;--pink:#fff0f6;--turq:#e6fbf8;--lilac:#f0edff;--white:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Arial,Tahoma,sans-serif;line-height:1.75;color:var(--ink);background:linear-gradient(145deg,#fff9fc,var(--turq),var(--lilac))}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;inset-inline-start:-9999px;top:8px;background:var(--white);padding:10px 14px;border:2px solid var(--accent);border-radius:12px;z-index:99}.skip:focus{inset-inline-start:8px}header{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:18px 0;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(255,255,255,.94);backdrop-filter:blur(12px);z-index:10}.brand{font-weight:900;text-decoration:none;color:var(--ink)}.nav,.languages,.actions{display:flex;gap:10px;flex-wrap:wrap}.nav a,.languages a{padding:8px 10px;border-radius:12px;text-decoration:none;font-weight:800}.nav a:hover,.languages a:hover{background:var(--turq)}.hero,.section{padding:44px 0 24px}.eyebrow{color:var(--accent2);font-weight:900}.hero h1{font-size:clamp(2.25rem,6vw,4.7rem);line-height:1.15;margin:.16em 0}.lead{font-size:clamp(1.05rem,2vw,1.28rem);max-width:920px;color:var(--muted)}.notice,.availability{padding:17px 20px;border-radius:18px;margin:20px 0}.notice{background:var(--pink);border-inline-start:5px solid var(--accent2)}.availability{background:var(--turq);border-inline-start:5px solid var(--accent)}.stats,.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.stat,.card,.quality div{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:0 16px 42px rgba(42,119,118,.1)}.stat strong{display:block;font-size:2rem;color:var(--accent2)}.card{display:flex;flex-direction:column}.card:nth-child(3n+1){background:linear-gradient(145deg,#fff,var(--pink))}.card:nth-child(3n+2){background:linear-gradient(145deg,#fff,var(--turq))}.card:nth-child(3n){background:linear-gradient(145deg,#fff,var(--lilac))}.card h3{margin-top:0}.card p{color:var(--muted);flex:1}.card a{font-weight:900}.quality{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.section h2{font-size:clamp(1.65rem,4vw,2.45rem)}footer{border-top:1px solid var(--line);padding:30px 0 48px;color:var(--muted)}a:focus-visible{outline:3px solid var(--accent);outline-offset:4px}@media(max-width:900px){header{align-items:flex-start;flex-direction:column}.stats,.cards,.quality{grid-template-columns:1fr}.nav,.languages{max-width:100%;overflow-x:auto;flex-wrap:nowrap}.nav a,.languages a{white-space:nowrap}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
""".strip()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def alternate_links() -> str:
    return (
        f'<link rel="alternate" hreflang="ar" href="{BASE}/">'
        f'<link rel="alternate" hreflang="en" href="{BASE}/en/">'
        f'<link rel="alternate" hreflang="es" href="{BASE}/es/">'
        f'<link rel="alternate" hreflang="x-default" href="{BASE}/">'
    )


def render(locale: str, page: dict) -> str:
    nav = page["navigation"]
    cards = "".join(
        f'<article class="card"><h3>{esc(title)}</h3><p>{esc(text)}</p><a lang="ar" dir="rtl" href="{esc(href)}">{esc(label)}</a></article>'
        for title, text, label, href in page["sections"]["cards"]
    )
    stats = "".join(
        f'<div class="stat"><strong>{esc(number)}</strong><span>{esc(label)}</span></div>'
        for number, label in page["stats"]
    )
    quality = "".join(
        f'<div><strong>{esc(title)}</strong><br>{esc(description)}</div>'
        for title, description in page["sections"]["quality"]
    )
    canonical = f"{BASE}/{locale}/"
    other_locale = "es" if locale == "en" else "en"
    other_name = "Español" if locale == "en" else "English"
    skip = "Skip to main content" if locale == "en" else "Saltar al contenido principal"
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page["title"],
        "description": page["description"],
        "inLanguage": locale,
        "url": canonical,
        "isPartOf": {
            "@type": "WebSite",
            "name": "مصطلحات علم النفس",
            "url": f"{BASE}/",
        },
    }
    schema_json = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="{locale}" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(page['title'])}</title>
<meta name="description" content="{esc(page['description'])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="theme-color" content="#72d8cf">
<meta name="color-scheme" content="light">
<link rel="canonical" href="{canonical}">
{alternate_links()}
<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta property="og:type" content="website">
<meta property="og:locale" content="{'en_US' if locale == 'en' else 'es_ES'}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{esc(page['title'])}">
<meta property="og:description" content="{esc(page['description'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(page['title'])}">
<meta name="twitter:description" content="{esc(page['description'])}">
<script type="application/ld+json">{schema_json}</script>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">{esc(skip)}</a>
<div class="wrap">
<header>
<a class="brand" href="{BASE_PATH}{locale}/">{esc(page['brand'])}</a>
<nav class="nav" aria-label="{esc(nav['primary_label'])}">
<a href="{BASE_PATH}{locale}/">{esc(nav['home'])}</a>
<a lang="ar" dir="rtl" href="{BASE_PATH}encyclopedia/">{esc(nav['encyclopedia'])}</a>
<a lang="ar" dir="rtl" href="{BASE_PATH}tips/">{esc(nav['guides'])}</a>
<a lang="ar" dir="rtl" href="{BASE_PATH}assessment-lab/">{esc(nav['assessments'])}</a>
<a lang="ar" dir="rtl" href="{BASE_PATH}cognitive-lab/">{esc(nav['cognitive'])}</a>
</nav>
<div class="languages" aria-label="{esc(nav['languages_label'])}">
<a lang="ar" dir="rtl" href="{BASE_PATH}">العربية</a>
<a lang="{other_locale}" href="{BASE_PATH}{other_locale}/">{esc(other_name)}</a>
</div>
</header>
<main id="main">
<section class="hero">
<p class="eyebrow">{esc(page['eyebrow'])}</p>
<h1>{esc(page['heading'])}</h1>
<p class="lead">{esc(page['lead'])}</p>
<div class="notice" role="note">{esc(page['notice'])}</div>
<div class="availability" role="note">{esc(page['availability_note'])}</div>
</section>
<section class="stats" aria-label="Platform size">{stats}</section>
<section class="section" aria-labelledby="discover-{locale}">
<h2 id="discover-{locale}">{esc(page['sections']['discover_title'])}</h2>
<p>{esc(page['sections']['discover_intro'])}</p>
<div class="cards">{cards}</div>
</section>
<section class="section" aria-labelledby="quality-{locale}">
<h2 id="quality-{locale}">{esc(page['sections']['quality_title'])}</h2>
<div class="quality">{quality}</div>
</section>
<section class="section" aria-labelledby="media-{locale}">
<h2 id="media-{locale}">{esc(page['sections']['media_title'])}</h2>
<p>{esc(page['sections']['media_intro'])}</p>
<div class="actions"><a href="https://www.youtube.com/@psychology-term" rel="me noopener">YouTube</a><a href="https://www.instagram.com/pterminology/" rel="me noopener">Instagram</a></div>
</section>
</main>
<footer><p>{esc(page['footer'])}</p></footer>
</div>
</body>
</html>'''


def patch_arabic_homepage() -> dict[str, bool]:
    path = SITE / "index.html"
    if not path.is_file():
        raise SystemExit("Missing generated Arabic homepage")
    text = path.read_text(encoding="utf-8")
    alternates_added = False
    switcher_added = False
    if 'hreflang="en"' not in text:
        text = text.replace("</head>", alternate_links() + "</head>", 1)
        alternates_added = True
    if 'data-i18n-switcher-v72' not in text:
        switcher = (
            '<div class="nav" data-i18n-switcher-v72 aria-label="اللغات">'
            f'<a lang="ar" dir="rtl" href="{BASE_PATH}">العربية</a>'
            f'<a lang="en" dir="ltr" href="{BASE_PATH}en/">English</a>'
            f'<a lang="es" dir="ltr" href="{BASE_PATH}es/">Español</a>'
            "</div>"
        )
        if "</header>" not in text:
            raise SystemExit("Arabic homepage header closing tag not found")
        text = text.replace("</header>", switcher + "</header>", 1)
        switcher_added = True
    path.write_text(text, encoding="utf-8")
    return {"alternates_added": alternates_added, "switcher_added": switcher_added}


def write_sitemaps(updated_at: str) -> str:
    urls = [f"{BASE}/{locale}/" for locale in LOCALES]
    sitemap_i18n = SITE / "sitemap-i18n.xml"
    entries = "".join(
        f"<url><loc>{esc(url)}</loc><lastmod>{esc(updated_at)}</lastmod><changefreq>weekly</changefreq></url>"
        for url in urls
    )
    sitemap_i18n.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + entries
        + "</urlset>\n",
        encoding="utf-8",
    )

    index_path = SITE / "sitemap.xml"
    if not index_path.is_file():
        raise SystemExit("Missing sitemap.xml")
    text = index_path.read_text(encoding="utf-8")
    target = f"{BASE}/sitemap-i18n.xml"
    if "<sitemapindex" in text:
        if target not in text:
            payload = f"<sitemap><loc>{target}</loc></sitemap>"
            text = text.replace("</sitemapindex>", payload + "</sitemapindex>", 1)
        mode = "sitemapindex"
    elif "<urlset" in text:
        for url in urls:
            if url not in text:
                text = text.replace("</urlset>", f"<url><loc>{url}</loc></url></urlset>", 1)
        mode = "urlset"
    else:
        raise SystemExit("Unsupported sitemap root")
    index_path.write_text(text, encoding="utf-8")
    return mode


def validate_data(data: dict) -> None:
    if data.get("entity_id") != "page.home" or data.get("source_locale") != "ar":
        raise SystemExit("Invalid homepage translation entity contract")
    allowed = set(data["allowed_statuses"])
    required = set(data["required_fields"])
    for locale in LOCALES:
        page = data["locales"][locale]
        missing = sorted(field for field in required if not page.get(field))
        if page.get("status") not in allowed - {"draft"} or missing:
            raise SystemExit(
                f"Refusing locale {locale}: status={page.get('status')!r}, missing={missing}"
            )
        if page.get("verification", {}).get("human_review_recorded") is not False:
            raise SystemExit("Human review must not be claimed without a verified record")
        if len(page["sections"]["cards"]) != 6 or len(page["sections"]["quality"]) != 4:
            raise SystemExit(f"Structural parity failed for locale {locale}")


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site output: {SITE}")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate_data(data)
    generated = []
    for locale in LOCALES:
        target = SITE / locale / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(locale, data["locales"][locale]), encoding="utf-8")
        generated.append(str(target.relative_to(SITE)))
    arabic = patch_arabic_homepage()
    sitemap_mode = write_sitemaps(data["updated_at"])
    report = {
        "version": 72,
        "entity_id": data["entity_id"],
        "locales": list(LOCALES),
        "generated_pages": generated,
        "generated_page_count": len(generated),
        "arabic_homepage": arabic,
        "sitemap_mode": sitemap_mode,
        "sitemap_file": "sitemap-i18n.xml",
        "human_review_claimed": False,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-i18n-v72.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()