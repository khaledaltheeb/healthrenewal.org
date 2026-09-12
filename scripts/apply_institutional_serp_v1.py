#!/usr/bin/env python3
"""Institutional SERP hardening for Rawafid.

This migration is additive and fail-closed. It strengthens the site-name, brand,
organization, favicon, sitemap, primary-hub and internal-link signals used by
search engines without deleting public pages or introducing noindex directives.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org/"
BRAND = "منصة روافد"
HOME_TITLE = "منصة روافد | الصحة النفسية والدمج والتربية الخاصة"
HOME_DESCRIPTION = (
    "منصة روافد مرجع عربي معرفي موثوق للصحة النفسية والتربية الخاصة والدمج "
    "وسرطان الأطفال، يقدم أدلة علمية وعملية ومكتبة معرفية ومسارات للأسر والمختصين."
)
SOCIAL_IMAGE = BASE + "assets/brand/rawafid-social-card.jpg"
LOGO_512 = BASE + "android-chrome-512x512.png"
TODAY = datetime.now(timezone.utc).date().isoformat()

PRIORITY = (
    {
        "name": "الصحة النفسية",
        "path": "/sectors/mental-health/",
        "title": "الصحة النفسية: الأدلة والدعم عبر مراحل الحياة | روافد",
        "description": "بوابة روافد للصحة النفسية عبر مراحل الحياة: فهم الأعراض والسياق، الأدلة الحديثة، الدعم العملي، والسلامة مع مسارات واضحة للأفراد والأسر والمختصين.",
    },
    {
        "name": "ذوو الاحتياجات الخاصة والدمج",
        "path": "/special-needs/",
        "title": "ذوو الاحتياجات الخاصة والتربية الدامجة | منصة روافد",
        "description": "مركز عربي منظم لذوي الاحتياجات الخاصة والتربية الدامجة، يجمع التواصل والتعلم والحواس والحركة والاستقلال والحماية ودعم الأسرة والمدرسة ضمن مسارات عملية موثقة.",
    },
    {
        "name": "سرطان الأطفال",
        "path": "/sectors/pediatric-oncology/",
        "title": "سرطان الأطفال: الأنواع والعلاج والدعم | منصة روافد",
        "description": "مركز معرفي عربي لسرطان الأطفال يشرح الأنواع والتشخيص والعلاج والمتابعة والتغذية والدعم النفسي والأسري، ويربط المحتوى بالأدلة والمصادر العلمية الحديثة.",
    },
    {
        "name": "الأدلة العلمية",
        "path": "/library/",
        "title": "المكتبة الأكاديمية العربية والأدلة العلمية | منصة روافد",
        "description": "المكتبة الأكاديمية في روافد لتنظيم الدراسات والمراجع والأدلة العلمية وقراءة قوة الدليل وحدوده وربط النتائج بالتطبيق في الصحة النفسية والدمج والرعاية.",
    },
    {
        "name": "أدلة التعامل والرعاية",
        "path": "/care-guides/",
        "title": "أدلة التعامل والرعاية: خطط عملية للأسرة والمختصين | روافد",
        "description": "أدلة عربية عملية للتعامل والرعاية تساعد الأسرة والمعلم والمختص على الانتقال من الموقف إلى خطوات قابلة للتطبيق والمتابعة، مع حدود مهنية ومصادر واضحة.",
    },
    {
        "name": "المختصون والشراكات المهنية",
        "path": "/specialists-partners/",
        "title": "المختصون والشراكات المهنية | منصة روافد",
        "description": "بوابة روافد للمختصين والشراكات المهنية: التعريف بالفريق، التحقق من الصفة المهنية، مسارات الانضمام والتواصل والتعاون المؤسسي ضمن حوكمة واضحة.",
    },
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> bool:
    old = read(path) if path.exists() else None
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def upsert_title(html: str, value: str) -> str:
    if re.search(r"<title\b[^>]*>.*?</title\s*>", html, re.I | re.S):
        return re.sub(r"<title\b[^>]*>.*?</title\s*>", f"<title>{value}</title>", html, count=1, flags=re.I | re.S)
    return html.replace("</head>", f"<title>{value}</title>\n</head>", 1)


def upsert_meta(html: str, attr: str, key: str, value: str) -> str:
    patt = re.compile(rf"<meta\b[^>]*\b{re.escape(attr)}\s*=\s*([\"']){re.escape(key)}\1[^>]*>", re.I | re.S)
    tag = f'<meta {attr}="{key}" content="{value}">'
    if patt.search(html):
        return patt.sub(tag, html, count=1)
    return html.replace("</head>", tag + "\n</head>", 1)


def upsert_link(html: str, rel: str, href: str, extra: str = "") -> str:
    patt = re.compile(rf"<link\b[^>]*\brel\s*=\s*([\"']){re.escape(rel)}\1[^>]*>", re.I | re.S)
    tag = f'<link rel="{rel}" {extra + " " if extra else ""}href="{href}">'
    if patt.search(html):
        return patt.sub(tag, html, count=1)
    return html.replace("</head>", tag + "\n</head>", 1)


def ensure_icon_links(html: str) -> str:
    required = (
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/svg+xml" href="/assets/brand/logo-mark.svg">',
        '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">',
        '<link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png">',
        '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/manifest.webmanifest">',
    )
    for tag in required:
        marker = re.search(r'href="([^"]+)"', tag).group(1)
        if marker not in html:
            html = html.replace("</head>", tag + "\n</head>", 1)
    return html


def homepage_schema() -> str:
    parts = [
        {
            "@type": "Organization",
            "@id": BASE + "#organization",
            "name": BRAND,
            "alternateName": ["روافد", "Rawafid", "Rawafid Platform"],
            "url": BASE,
            "description": HOME_DESCRIPTION,
            "slogan": "معرفة موثقة ومسارات عملية",
            "logo": {"@type": "ImageObject", "url": LOGO_512, "contentUrl": LOGO_512, "width": 512, "height": 512},
            "image": SOCIAL_IMAGE,
            "email": "contact@healthrenewal.org",
            "contactPoint": {
                "@type": "ContactPoint",
                "email": "contact@healthrenewal.org",
                "contactType": "general inquiries",
                "availableLanguage": ["Arabic", "English"],
                "areaServed": "Worldwide",
            },
            "sameAs": ["https://www.instagram.com/pterminology/", "https://www.youtube.com/@psychology-term"],
        },
        {
            "@type": "WebSite",
            "@id": BASE + "#website",
            "url": BASE,
            "name": BRAND,
            "alternateName": ["روافد", "Rawafid", "healthrenewal.org"],
            "description": HOME_DESCRIPTION,
            "inLanguage": ["ar", "en", "es"],
            "publisher": {"@id": BASE + "#organization"},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint", "urlTemplate": BASE + "encyclopedia/?q={search_term_string}"},
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@type": "WebPage",
            "@id": BASE + "#webpage",
            "url": BASE,
            "name": HOME_TITLE,
            "description": HOME_DESCRIPTION,
            "isPartOf": {"@id": BASE + "#website"},
            "about": {"@id": BASE + "#organization"},
            "primaryImageOfPage": {"@type": "ImageObject", "url": SOCIAL_IMAGE},
            "inLanguage": "ar",
            "mainEntity": {"@id": BASE + "#primary-sections"},
        },
        {
            "@type": "ItemList",
            "@id": BASE + "#primary-sections",
            "name": "الأقسام الرئيسية في منصة روافد",
            "numberOfItems": len(PRIORITY),
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": item["name"], "url": urljoin(BASE, item["path"].lstrip("/"))}
                for i, item in enumerate(PRIORITY, 1)
            ],
        },
    ]
    return '<script id="institutional-serp-schema" type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@graph": parts}, ensure_ascii=False, separators=(",", ":")
    ) + "</script>"


def replace_primary_schema(html: str) -> str:
    new = homepage_schema()
    marker = re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script\s*>', re.I | re.S)
    matches = list(marker.finditer(html))
    if not matches:
        return html.replace("</head>", new + "\n</head>", 1)
    first = matches[0]
    return html[: first.start()] + new + html[first.end() :]


def normalize_href(href: str) -> str:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return parsed.path or "/"
    path = "/" + href.lstrip("./")
    return path


def prioritize_home_nav(html: str) -> str:
    patt = re.compile(r'(<nav class="nav" aria-label="التنقل الرئيسي">)(.*?)(</nav>)', re.S)
    m = patt.search(html)
    if not m:
        raise RuntimeError("Homepage primary nav was not found")
    anchors = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', m.group(2), re.S)
    priority_paths = {item["path"] for item in PRIORITY}
    out = [f'<a href="{item["path"]}" data-serp-priority="1">{item["name"]}</a>' for item in PRIORITY]
    seen = set(priority_paths)
    for href, label in anchors:
        norm = normalize_href(href)
        if norm in seen:
            continue
        seen.add(norm)
        out.append(f'<a href="{href}">{label}</a>')
    return html[: m.start()] + m.group(1) + "".join(out) + m.group(3) + html[m.end() :]


def priority_section() -> str:
    cards = "".join(
        f'<article class="card"><span class="tag">قسم رئيسي</span><h3 class="item-title">{item["name"]}</h3>'
        f'<p>{item["description"]}</p><a href="{item["path"]}">فتح القسم ←</a></article>'
        for item in PRIORITY
    )
    return (
        '<section class="section" data-institutional-sitelinks-v1 aria-labelledby="primary-sections-title">'
        '<div class="section-head"><div><p class="eyebrow">المداخل المؤسسية الرئيسية</p>'
        '<h2 id="primary-sections-title">الأقسام الرئيسية في منصة روافد</h2>'
        '<p class="section-intro">ستة مسارات مرجعية ثابتة تساعد المستخدم ومحركات البحث على فهم البنية المؤسسية للمنصة والوصول إلى أهم مجالاتها مباشرة.</p>'
        '</div><a class="section-link" href="/sections/">استعرض جميع الأقسام ←</a></div>'
        f'<div class="cards">{cards}</div></section>'
    )


def enhance_homepage() -> bool:
    path = ROOT / "index.html"
    html = read(path)
    html = upsert_title(html, HOME_TITLE)
    for key, value in (
        ("description", HOME_DESCRIPTION),
        ("author", BRAND),
        ("application-name", BRAND),
        ("publisher", BRAND),
        ("subject", "الصحة النفسية والتربية الخاصة والتربية الدامجة وذوو الاحتياجات الخاصة وسرطان الأطفال"),
        ("robots", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"),
        ("googlebot", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"),
        ("twitter:title", HOME_TITLE),
        ("twitter:description", HOME_DESCRIPTION),
        ("twitter:image", SOCIAL_IMAGE),
        ("twitter:image:alt", "شعار منصة روافد"),
    ):
        html = upsert_meta(html, "name", key, value)
    for key, value in (
        ("og:type", "website"), ("og:locale", "ar_AR"), ("og:site_name", BRAND),
        ("og:url", BASE), ("og:title", HOME_TITLE), ("og:description", HOME_DESCRIPTION),
        ("og:image", SOCIAL_IMAGE), ("og:image:alt", "شعار منصة روافد"),
    ):
        html = upsert_meta(html, "property", key, value)
    html = ensure_icon_links(html)
    html = re.sub(r'<link\s+rel="sitemap"[^>]*>', '<link rel="sitemap" type="application/xml" href="https://healthrenewal.org/sitemap-index.xml">', html, count=1, flags=re.I)
    html = replace_primary_schema(html)
    html = prioritize_home_nav(html)
    if "data-institutional-sitelinks-v1" not in html:
        anchor = '<section class="metrics"'
        pos = html.find(anchor)
        if pos < 0:
            raise RuntimeError("Homepage metrics anchor was not found")
        html = html[:pos] + priority_section() + "\n" + html[pos:]
    return write(path, html)


def hub_schema(item: dict[str, str]) -> str:
    canonical = urljoin(BASE, item["path"].lstrip("/"))
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": item["title"],
                "description": item["description"],
                "isPartOf": {"@id": BASE + "#website"},
                "publisher": {"@id": BASE + "#organization"},
                "inLanguage": "ar",
            },
            {
                "@type": "BreadcrumbList",
                "@id": canonical + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": BRAND, "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": item["name"], "item": canonical},
                ],
            },
        ],
    }
    return '<script id="institutional-serp-hub-schema" type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def enhance_hub(item: dict[str, str]) -> bool:
    file_path = ROOT / item["path"].strip("/") / "index.html"
    if not file_path.is_file():
        raise RuntimeError(f"Priority hub missing: {file_path.relative_to(ROOT)}")
    html = read(file_path)
    canonical = urljoin(BASE, item["path"].lstrip("/"))
    html = upsert_title(html, item["title"])
    for key, value in (
        ("description", item["description"]),
        ("author", BRAND),
        ("application-name", BRAND),
        ("robots", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"),
        ("googlebot", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"),
        ("twitter:title", item["title"]),
        ("twitter:description", item["description"]),
        ("twitter:image", SOCIAL_IMAGE),
        ("twitter:image:alt", "شعار منصة روافد"),
    ):
        html = upsert_meta(html, "name", key, value)
    for key, value in (
        ("og:type", "website"), ("og:locale", "ar_AR"), ("og:site_name", BRAND),
        ("og:url", canonical), ("og:title", item["title"]), ("og:description", item["description"]),
        ("og:image", SOCIAL_IMAGE), ("og:image:alt", "شعار منصة روافد"),
    ):
        html = upsert_meta(html, "property", key, value)
    canonical_re = re.compile(r'<link\b[^>]*\brel=["\']canonical["\'][^>]*>', re.I | re.S)
    canonical_tag = f'<link rel="canonical" href="{canonical}">'
    html = canonical_re.sub(canonical_tag, html, count=1) if canonical_re.search(html) else html.replace("</head>", canonical_tag + "\n</head>", 1)
    html = ensure_icon_links(html)
    schema = hub_schema(item)
    schema_re = re.compile(r'<script id="institutional-serp-hub-schema"[^>]*>.*?</script\s*>', re.I | re.S)
    html = schema_re.sub(schema, html, count=1) if schema_re.search(html) else html.replace("</head>", schema + "\n</head>", 1)
    return write(file_path, html)


def update_manifest() -> bool:
    path = ROOT / "manifest.webmanifest"
    data = json.loads(read(path))
    data["name"] = BRAND
    data["short_name"] = "روافد"
    data["description"] = HOME_DESCRIPTION
    data["lang"] = "ar"
    data["dir"] = "rtl"
    data["icons"] = [
        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ]
    data["shortcuts"] = [
        {"name": item["name"], "url": item["path"], "icons": [{"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"}]}
        for item in PRIORITY
    ]
    return write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def update_opensearch() -> bool:
    path = ROOT / "opensearch.xml"
    text = read(path)
    text = re.sub(r"<ShortName>.*?</ShortName>", f"<ShortName>{BRAND}</ShortName>", text, count=1)
    text = re.sub(r"<Description>.*?</Description>", "<Description>بحث عربي في منصة روافد عبر الموسوعة والأدلة والأقسام المعرفية</Description>", text, count=1)
    return write(path, text)


def update_feed() -> bool:
    path = ROOT / "feed.xml"
    if not path.is_file():
        return False
    text = read(path)
    text = re.sub(r"(<channel>\s*<title>).*?(</title>)", rf"\1{HOME_TITLE}\2", text, count=1, flags=re.S)
    return write(path, text)


def update_sitemap() -> bool:
    path = ROOT / "sitemap.xml"
    if not path.is_file():
        raise RuntimeError("sitemap.xml is missing")
    text = read(path)
    additions = []
    for item in PRIORITY:
        url = urljoin(BASE, item["path"].lstrip("/"))
        if url not in text:
            additions.append(f"  <url><loc>{url}</loc><lastmod>{TODAY}</lastmod></url>")
    if additions:
        if "</urlset>" not in text:
            raise RuntimeError("sitemap.xml has no closing urlset")
        text = text.replace("</urlset>", "\n".join(additions) + "\n</urlset>", 1)
    return write(path, text)


def patch_persistence_generators() -> list[str]:
    changed = []
    path = ROOT / "scripts" / "apply_rawafid_brand.py"
    text = read(path)
    original = text
    text = text.replace("منصة روافد | العافية النفسية والدمج والتمكين", HOME_TITLE)
    old_desc = "منصة روافد منصة عربية للعافية النفسية والدمج والتمكين، تقدم موسوعة موثقة، "
    if old_desc in text:
        text = text.replace(old_desc, "منصة روافد مرجع عربي معرفي موثوق للصحة النفسية والتربية الخاصة والدمج وسرطان الأطفال، ")
        text = text.replace("أدلة عملية، أدوات تفاعلية، ومسارات معرفية داعمة للأفراد والأسر والمختصين والمجتمع.", "يقدم أدلة علمية وعملية ومكتبة معرفية ومسارات للأسر والمختصين.")
    text = text.replace('data.update({"name":BRAND_LONG,', 'data.update({"name":BRAND_NAME,')
    text = text.replace('<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">', '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">\n<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">\n<link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png">')
    if text != original:
        write(path, text); changed.append(str(path.relative_to(ROOT)))

    path = ROOT / "scripts" / "rawafid_brand_consistency.py"
    text = read(path); original = text
    text = text.replace("منصة روافد منصة عربية للعافية النفسية والدمج والتمكين، تقدم موسوعة موثقة، ", "منصة روافد مرجع عربي معرفي موثوق للصحة النفسية والتربية الخاصة والدمج وسرطان الأطفال، ")
    text = text.replace("وأدلة عملية، وأدوات تفاعلية، ومسارات معرفية داعمة للأفراد والأسر والمختصين والمجتمع.", "ويقدم أدلة علمية وعملية ومكتبة معرفية ومسارات للأسر والمختصين.")
    text = text.replace('"name": BRAND_LONG_AR,', '"name": BRAND_AR,')
    text = text.replace('<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">', '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">\n<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">\n<link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png">')
    if text != original:
        write(path, text); changed.append(str(path.relative_to(ROOT)))
    return changed


def parse_jsonld(html: str, path: str) -> None:
    for raw in re.findall(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script\s*>', html, re.I | re.S):
        json.loads(raw.strip())


def validate(index_count_before: int) -> dict:
    errors = []
    index_count_after = sum(1 for _ in ROOT.rglob("index.html"))
    if index_count_after != index_count_before:
        errors.append(f"index.html count changed: {index_count_before} -> {index_count_after}")
    home = read(ROOT / "index.html")
    required_home = [HOME_TITLE, HOME_DESCRIPTION, 'name="منصة روافد"', 'alternateName', 'healthrenewal.org', 'data-institutional-sitelinks-v1', '/favicon-48x48.png', '/android-chrome-192x192.png']
    for token in required_home:
        if token not in home:
            errors.append(f"homepage missing token: {token}")
    if re.search(r'<meta\b[^>]*(?:name|property)=["\']robots["\'][^>]*content=["\'][^"\']*noindex', home, re.I):
        errors.append("homepage contains noindex")
    try:
        parse_jsonld(home, "index.html")
    except Exception as exc:
        errors.append(f"homepage JSON-LD invalid: {exc}")
    for item in PRIORITY:
        file_path = ROOT / item["path"].strip("/") / "index.html"
        if not file_path.is_file():
            errors.append(f"missing hub: {file_path.relative_to(ROOT)}")
            continue
        html = read(file_path)
        canonical = urljoin(BASE, item["path"].lstrip("/"))
        for token in (item["title"], item["description"], canonical, BRAND, "institutional-serp-hub-schema"):
            if token not in html:
                errors.append(f"{file_path.relative_to(ROOT)} missing {token}")
        if "noindex" in re.sub(r"\s+", " ", html[:8000]).lower():
            errors.append(f"priority hub contains noindex: {file_path.relative_to(ROOT)}")
        try:
            parse_jsonld(html, str(file_path.relative_to(ROOT)))
        except Exception as exc:
            errors.append(f"{file_path.relative_to(ROOT)} JSON-LD invalid: {exc}")
    manifest = json.loads(read(ROOT / "manifest.webmanifest"))
    if manifest.get("name") != BRAND or manifest.get("short_name") != "روافد":
        errors.append("manifest identity mismatch")
    sitemap = read(ROOT / "sitemap.xml")
    for item in PRIORITY:
        url = urljoin(BASE, item["path"].lstrip("/"))
        if url not in sitemap:
            errors.append(f"sitemap missing {url}")
    diff = subprocess.run(["git", "diff", "--name-status"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    deleted = [line for line in diff.splitlines() if line.startswith("D\t")]
    if deleted:
        errors.append("deleted files detected: " + ", ".join(deleted))
    if errors:
        raise SystemExit("Institutional SERP validation failed:\n- " + "\n- ".join(errors))
    return {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "homepage_title": HOME_TITLE,
        "homepage_description": HOME_DESCRIPTION,
        "priority_hubs": [{"name": i["name"], "url": urljoin(BASE, i["path"].lstrip("/"))} for i in PRIORITY],
        "index_html_count_before": index_count_before,
        "index_html_count_after": index_count_after,
        "deleted_files": [],
        "noindex_added_to_priority_pages": False,
        "sitemap": BASE + "sitemap-index.xml",
        "site_name": BRAND,
        "alternate_site_names": ["روافد", "Rawafid", "healthrenewal.org"],
    }


def main() -> None:
    index_count_before = sum(1 for _ in ROOT.rglob("index.html"))
    changed = []
    if enhance_homepage(): changed.append("index.html")
    for item in PRIORITY:
        if enhance_hub(item): changed.append(item["path"].strip("/") + "/index.html")
    if update_manifest(): changed.append("manifest.webmanifest")
    if update_opensearch(): changed.append("opensearch.xml")
    if update_feed(): changed.append("feed.xml")
    if update_sitemap(): changed.append("sitemap.xml")
    changed.extend(patch_persistence_generators())
    report = validate(index_count_before)
    report["changed_files"] = sorted(set(changed))
    write(ROOT / "reports" / "institutional-serp-v1.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
