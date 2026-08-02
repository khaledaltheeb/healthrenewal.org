from __future__ import annotations

import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = Path(__file__).with_name("rebuild_encyclopedia_v13.py")
spec = importlib.util.spec_from_file_location("encyclopedia_v13", SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load v13 encyclopedia builder")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


ENCYCLOPEDIA_HERO_CONTRAST_CSS = r"""
/* Encyclopedia hero contrast guard — loaded after the generated theme layers. */
.ency-v13 .ency-v13__hero,
.ency-topic-v2 .ency-topic-v2__hero {
  color: #17383d !important;
}

.ency-v13 .ency-v13__hero h1,
.ency-v13 .ency-v13__hero p,
.ency-v13 .ency-v13__hero strong,
.ency-topic-v2 .ency-topic-v2__hero h1,
.ency-topic-v2 .ency-topic-v2__hero p,
.ency-topic-v2 .ency-topic-v2__hero strong {
  color: #17383d !important;
  text-shadow: none !important;
}

.ency-v13 .ency-v13__hero p,
.ency-v13 .ency-v13__hero p[lang="en"],
.ency-topic-v2 .ency-topic-v2__hero p,
.ency-topic-v2 .ency-topic-v2__hero p[lang="en"] {
  color: #3d6268 !important;
}

.ency-v13 .ency-v13__tag,
.ency-topic-v2 .ency-topic-v2__badge {
  color: #174b52 !important;
  text-shadow: none !important;
}

.ency-topic-v2 .ency-topic-v2__button {
  color: #ffffff !important;
}

.ency-topic-v2 .ency-topic-v2__button--secondary {
  color: #116d69 !important;
}
""".strip() + "\n"

ENCYCLOPEDIA_HERO_CONTRAST_STYLESHEET = "encyclopedia-hero-contrast-fix.css"
ENCYCLOPEDIA_HERO_CONTRAST_MARKER = 'data-encyclopedia-hero-contrast="v1"'


def fix_homepage_heading_hierarchy(site: Path) -> None:
    homepage = site / "index.html"
    text = homepage.read_text(encoding="utf-8")
    starts = list(re.finditer(r"<h1(?P<attrs>\s[^>]*)?>", text, flags=re.I))
    if len(starts) <= 1:
        return
    second = starts[1]
    open_tag = second.group(0)
    replacement = re.sub(r"^<h1", "<h2", open_tag, flags=re.I)
    text = text[:second.start()] + replacement + text[second.end():]
    close = re.search(r"</h1>", text[second.start() + len(replacement):], flags=re.I)
    if close is None:
        raise SystemExit("Second homepage h1 has no closing tag")
    close_start = second.start() + len(replacement) + close.start()
    close_end = second.start() + len(replacement) + close.end()
    text = text[:close_start] + "</h2>" + text[close_end:]
    homepage.write_text(text, encoding="utf-8")


def apply_encyclopedia_hero_contrast(site: Path, base: str) -> dict[str, object]:
    css_path = site / "assets" / "css" / ENCYCLOPEDIA_HERO_CONTRAST_STYLESHEET
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text(ENCYCLOPEDIA_HERO_CONTRAST_CSS, encoding="utf-8")

    stylesheet_url = (
        base.rstrip("/")
        + "/assets/css/"
        + ENCYCLOPEDIA_HERO_CONTRAST_STYLESHEET
        + "?v=1"
    )
    stylesheet_link = (
        f'<link rel="stylesheet" href="{stylesheet_url}" '
        f'{ENCYCLOPEDIA_HERO_CONTRAST_MARKER}>'
    )

    candidates = sorted(
        {
            *site.glob("encyclopedia/**/*.html"),
            *site.glob("hubs/**/*.html"),
        }
    )
    eligible: list[Path] = []
    updated = 0

    for page in candidates:
        text = page.read_text(encoding="utf-8")
        if (
            "ency-v13__hero" not in text
            and "ency-topic-v2__hero" not in text
        ):
            continue

        eligible.append(page)
        if ENCYCLOPEDIA_HERO_CONTRAST_MARKER in text:
            continue
        if "</head>" not in text:
            raise SystemExit(f"Encyclopedia page has no closing head tag: {page}")

        page.write_text(
            text.replace("</head>", stylesheet_link + "</head>", 1),
            encoding="utf-8",
        )
        updated += 1

    if not eligible:
        raise SystemExit("No encyclopedia hero pages were found for contrast repair")

    missing = [
        str(page.relative_to(site))
        for page in eligible
        if ENCYCLOPEDIA_HERO_CONTRAST_MARKER
        not in page.read_text(encoding="utf-8")
    ]
    if missing:
        raise SystemExit(
            f"Encyclopedia hero contrast stylesheet missing from {len(missing)} pages"
        )

    return {
        "status": "passed",
        "stylesheet": str(css_path.relative_to(site)),
        "eligible_pages": len(eligible),
        "updated_pages": updated,
        "dark_text": "#17383d",
        "muted_text": "#3d6268",
        "light_background_safe": True,
    }


def normalize_hubs_sitemap_namespace(site: Path) -> dict[str, object]:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = site / "sitemap-hubs.xml"
    if not sitemap.is_file():
        raise SystemExit(f"Missing hubs sitemap: {sitemap}")

    ET.register_namespace("", namespace)
    tree = ET.parse(sitemap)
    root = tree.getroot()
    if root.tag != f"{{{namespace}}}urlset":
        raise SystemExit(f"Unexpected hubs sitemap root: {root.tag}")

    url_count = len(root.findall(f"{{{namespace}}}url"))
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    serialized = sitemap.read_text(encoding="utf-8")
    if "ns0:" in serialized:
        raise SystemExit("Prefixed sitemap namespace remains after normalization")
    if f'xmlns="{namespace}"' not in serialized:
        raise SystemExit("Default sitemap namespace is missing")
    if serialized.count("<url>") != url_count:
        raise SystemExit(
            {
                "hubs_sitemap_serialization_mismatch": {
                    "semantic_urls": url_count,
                    "serialized_urls": serialized.count("<url>"),
                }
            }
        )
    return {
        "status": "passed",
        "url_count": url_count,
        "default_namespace": True,
        "prefixed_namespace_removed": True,
    }


def audit_encyclopedia_surface(site: Path) -> dict[str, object]:
    detail_pages = sorted((site / "encyclopedia").glob("concept-*/index.html"))
    if len(detail_pages) != 2000:
        raise SystemExit(f"Expected 2000 encyclopedia detail pages, found {len(detail_pages)}")
    audit = json.loads((site / "api/encyclopedia-audit-v13.json").read_text(encoding="utf-8"))
    seo = json.loads((site / "api/encyclopedia-seo-search-intent-v1.json").read_text(encoding="utf-8"))
    required = {
        "concept_pages": 2000,
        "unique_seo_titles": 2000,
        "unique_descriptions": 2000,
        "unique_primary_queries": 2000,
        "seo_complete_pages": 2000,
        "search_intent_sections": 2000,
        "faq_schema_pages": 2000,
    }
    for key, value in required.items():
        if audit.get(key) != value:
            raise SystemExit(f"Encyclopedia audit mismatch: {key}={audit.get(key)!r}, expected {value!r}")
    if seo.get("status") != "passed" or seo.get("pages") != 2000 or len(seo.get("items", [])) != 2000:
        raise SystemExit("Encyclopedia SEO/search-intent manifest is incomplete")
    sitemap_counts = {}
    for name in ("sitemap-terms-1.xml", "sitemap-terms-2.xml"):
        root = ET.parse(site / name).getroot()
        urls = [node.text for node in root.findall("{*}url/{*}loc") if node.text]
        sitemap_counts[name] = len(urls)
        if len(urls) != 1000 or len(set(urls)) != 1000:
            raise SystemExit(f"Invalid {name} URL inventory")
        for url in urls:
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            if not (site / "encyclopedia" / slug / "index.html").is_file():
                raise SystemExit(f"Sitemap URL has no encyclopedia target: {url}")
    return {
        "status": "passed",
        "detail_pages": len(detail_pages),
        "seo_complete_pages": audit["seo_complete_pages"],
        "search_intent_sections": audit["search_intent_sections"],
        "faq_schema_pages": audit["faq_schema_pages"],
        "sitemap_counts": sitemap_counts,
    }


build_report = module.build()

TOPIC_SOURCE = Path(__file__).with_name("publish_encyclopedia_topic_hubs_v2.py")
topic_spec = importlib.util.spec_from_file_location("encyclopedia_topic_hubs_v2", TOPIC_SOURCE)
if topic_spec is None or topic_spec.loader is None:
    raise SystemExit("Unable to load encyclopedia topic-hub publisher")
topic_module = importlib.util.module_from_spec(topic_spec)
topic_spec.loader.exec_module(topic_module)
topic_report = topic_module.publish(module)
sitemap_report = normalize_hubs_sitemap_namespace(module.SITE)

fix_homepage_heading_hierarchy(module.SITE)
hero_contrast_report = apply_encyclopedia_hero_contrast(module.SITE, module.BASE)

audit_report = audit_encyclopedia_surface(module.SITE)

print(
    json.dumps(
        {
            "encyclopedia": build_report,
            "topic_hubs": topic_report,
            "hubs_sitemap": sitemap_report,
            "hero_contrast": hero_contrast_report,
            "encyclopedia_audit": audit_report,
        },
        ensure_ascii=False,
        indent=2,
    )
)
