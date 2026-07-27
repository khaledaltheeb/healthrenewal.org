#!/usr/bin/env python3
from __future__ import annotations

from special_needs_v322_core import *
from special_needs_v322_render import inject_hub, render_guide

def sitemap_mode(path: Path) -> tuple[ET.ElementTree, ET.Element, str]:
    if not path.is_file():
        raise SystemExit(f"Missing sitemap: {path}")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ET.parse(path)
    root = tree.getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    if mode not in {"urlset", "sitemapindex"}:
        raise SystemExit(f"Unsupported sitemap root: {path}/{mode}")
    return tree, root, mode


def add_urls_to_urlset(path: Path, urls: list[str], lastmod: str) -> int:
    tree, root, mode = sitemap_mode(path)
    if mode != "urlset":
        return 0
    namespace = root.tag.split("}", 1)[0].strip("{") if "}" in root.tag else ""
    def tag(name: str) -> str:
        return f"{{{namespace}}}{name}" if namespace else name
    existing = {(node.text or "").strip() for node in root.findall(f"{tag('url')}/{tag('loc')}")}
    added = 0
    for url in urls:
        if url in existing:
            continue
        row = ET.SubElement(root, tag("url"))
        ET.SubElement(row, tag("loc")).text = url
        ET.SubElement(row, tag("lastmod")).text = lastmod
        added += 1
        existing.add(url)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    _, root2, _ = sitemap_mode(path)
    values = [(node.text or "").strip() for node in root2.findall(f"{tag('url')}/{tag('loc')}")]
    duplicates = [url for url in urls if values.count(url) != 1]
    if duplicates:
        raise SystemExit(f"Sitemap URL multiplicity failed: {path}/{duplicates}")
    return added


def update_sitemaps(site: Path, guides: list[dict[str, Any]], lastmod: str) -> dict[str, Any]:
    urls = [f"{BASE}/special-needs/{guide['slug']}/" for guide in guides]
    special = site / "sitemap-special-needs.xml"
    added_special = add_urls_to_urlset(special, urls, lastmod)
    main = site / "sitemap.xml"
    _, _, mode = sitemap_mode(main)
    added_main = add_urls_to_urlset(main, urls, lastmod) if mode == "urlset" else 0
    return {
        "special_sitemap_added": added_special,
        "main_sitemap_mode": mode,
        "main_sitemap_added": added_main,
        "urls": urls,
    }


def refresh_deployment_evidence(site: Path) -> bool:
    path = site / "deployment.json"
    if not path.is_file():
        return False
    data = read_json(path)
    if data.get("schema_version") != 29:
        raise SystemExit(f"Unsupported deployment schema while refreshing v322 evidence: {data.get('schema_version')}")
    required = ("index.html", "sitemap.xml", "manifest.webmanifest", "sw.js")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(required):
        raise SystemExit("Deployment artifact contract changed before v322 publication")
    refreshed: dict[str, dict[str, Any]] = {}
    for name in required:
        target = site / name
        if not target.is_file():
            raise SystemExit(f"Missing deployment artifact while refreshing v322 evidence: {name}")
        refreshed[name] = {
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
        }
    data["artifacts"] = refreshed
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def validate_page(path: Path, guide: dict[str, Any]) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    canonical = f"{BASE}/special-needs/{guide['slug']}/"
    required = (
        '<html lang="ar" dir="rtl">',
        f'<link rel="canonical" href="{canonical}">',
        '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">',
        'data-special-needs-expansion-v322',
        'pt-platform-shell:v1',
        'platform-core.css?v=1.1.0',
        'حدود الاستخدام:',
        'خطة عمل من ست خطوات',
        'مؤشرات تستدعي تحركًا عاجلًا',
        'المصادر والمنهج وحدود المراجعة',
        'المراجعة الخارجية المتخصصة موصى بها ولم تكتمل',
        f'{BP}special-needs/{guide["related_path_slug"]}/',
    )
    missing = [item for item in required if item not in source]
    if missing:
        raise SystemExit(f"{guide['slug']}: missing page markers {missing}")
    if source.count("<h1") != 1 or len(re.findall(r"<h2\b", source)) < 11:
        raise SystemExit(f"{guide['slug']}: heading hierarchy failed")
    if source.count('rel="noopener noreferrer"') < 4:
        raise SystemExit(f"{guide['slug']}: source citation depth failed")
    if BANNED.search(source):
        raise SystemExit(f"{guide['slug']}: banned terminology rendered")
    if any(token in source for token in FORBIDDEN_RUNTIME):
        raise SystemExit(f"{guide['slug']}: unsafe runtime API detected")
    words = visible_words(source)
    if words < 1200:
        raise SystemExit(f"{guide['slug']}: rendered page too thin ({words})")
    return {
        "slug": guide["slug"],
        "path": path.as_posix(),
        "canonical": canonical,
        "words": words,
        "h2": len(re.findall(r"<h2\b", source)),
        "citations": source.count('rel="noopener noreferrer"'),
    }


def publish(site: Path) -> dict[str, Any]:
    payload = read_json(CONTENT)
    guides = validate_payload(payload)
    output = site / "special-needs"
    output.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    for guide in guides:
        target = output / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_guide(guide, payload), encoding="utf-8")
        page = validate_page(target, guide)
        page["path"] = target.relative_to(site).as_posix()
        pages.append(page)

    hub_links = inject_hub(site, guides, payload)
    discovery = update_sitemaps(site, guides, payload["reviewed_at"])
    deployment_evidence_refreshed = refresh_deployment_evidence(site)
    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": payload["review_status"],
        "external_clinical_review_completed": False,
        "reviewed_at": payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "guide_count": len(guides),
        "guide_slugs": [guide["slug"] for guide in guides],
        "generated_pages": [page["path"] for page in pages],
        "section_count": sum(len(guide["sections"]) for guide in guides),
        "source_count": sum(len(guide["sources"]) for guide in guides),
        "minimum_rendered_words": min(page["words"] for page in pages),
        "minimum_h2": min(page["h2"] for page in pages),
        "minimum_citations": min(page["citations"] for page in pages),
        "hub_links_added": hub_links,
        "hub_marker_count": 1,
        "sitemap_registered": True,
        "deployment_evidence_refreshed": deployment_evidence_refreshed,
        **discovery,
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
        "pages": pages,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-expansion-v322.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
