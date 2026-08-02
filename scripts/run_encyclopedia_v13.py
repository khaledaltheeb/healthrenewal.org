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

GUIDE_SOURCE = Path(__file__).with_name("publish_adjustment_disorder_v335.py")
guide_spec = importlib.util.spec_from_file_location("adjustment_disorder_v335", GUIDE_SOURCE)
if guide_spec is None or guide_spec.loader is None:
    raise SystemExit("Unable to load adjustment-disorder publisher")
guide_module = importlib.util.module_from_spec(guide_spec)
guide_spec.loader.exec_module(guide_module)
guide_report = guide_module.publish(module.SITE)

# Earlier build generations can still carry the retired GitHub Pages origin in
# sitemap indexes. Normalize the assembled site before the integrity audit so
# every workflow validates the production origin, not an intermediate artifact.
NORMALIZER_SOURCE = Path(__file__).with_name("normalize_internal_base_paths_v198.py")
normalizer_spec = importlib.util.spec_from_file_location("internal_base_paths_v198", NORMALIZER_SOURCE)
if normalizer_spec is None or normalizer_spec.loader is None:
    raise SystemExit("Unable to load internal base-path normalizer")
normalizer_module = importlib.util.module_from_spec(normalizer_spec)
normalizer_spec.loader.exec_module(normalizer_module)
normalizer_report = normalizer_module.normalize_site(module.SITE)
if normalizer_report.get("status") != "passed":
    raise SystemExit({"internal_base_path_normalization_failed": normalizer_report})

AUDIT_SOURCE = Path(__file__).with_name("audit_site_integrity_v13.py")
audit_spec = importlib.util.spec_from_file_location("site_integrity_v13", AUDIT_SOURCE)
if audit_spec is None or audit_spec.loader is None:
    raise SystemExit("Unable to load v13 site integrity audit")
audit_module = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(audit_module)
audit_module.SITE = module.SITE
audit_result = audit_module.main()

audit_report = audit_encyclopedia_surface(module.SITE)

print(json.dumps({
    "encyclopedia": build_report,
    "topic_hubs": topic_report,
    "hubs_sitemap": sitemap_report,
    "adjustment_disorder": guide_report,
    "internal_base_paths": normalizer_report,
    "integrity_audit_exit": audit_result,
    "encyclopedia_audit": audit_report,
}, ensure_ascii=False, indent=2))
