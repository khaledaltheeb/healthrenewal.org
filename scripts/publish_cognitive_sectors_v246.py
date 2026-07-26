from __future__ import annotations

# Verified compressed source bundle for the institutional cognitive sectors publisher.
import base64
import gzip
import re
from pathlib import Path

_PARTS = tuple(Path(__file__).with_name("v246_cognitive_parts").glob("part*.b85"))
if not _PARTS:
    raise SystemExit("Missing cognitive publisher bundle parts")
payload = "".join(path.read_text(encoding="ascii") for path in sorted(_PARTS))
source = gzip.decompress(base64.b85decode(payload.encode("ascii"))).decode("utf-8")

# v246.1: register only URLs that are not already present in another sitemap.
# The full discovery contract still proves all 63 cognitive URLs are mapped.
_new_sitemap = r'''def sitemap_urls_from_file(path: Path) -> set[str]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return set()
    return {str(node.text).strip() for node in root.findall("{*}url/{*}loc") if node.text and str(node.text).strip()}


def write_sitemap(site: Path, legacy: list[dict[str, Any]], modern: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [(BASE + "cognitive-tests/", "0.90"), (BASE + "cognitive-lab/", "0.95")]
    candidates += [(BASE + "cognitive-tests/" + item["slug"] + "/", "0.78") for item in legacy]
    candidates += [(BASE + "cognitive-lab/" + item["slug"] + "/", "0.82") for item in modern]
    required = list(dict.fromkeys(url for url, _ in candidates))
    target_path = site / "sitemap-cognitive.xml"
    existing_elsewhere: set[str] = set()
    for sitemap in site.glob("sitemap*.xml"):
        if sitemap.resolve() == target_path.resolve() or sitemap.name == "sitemap.xml":
            continue
        existing_elsewhere.update(sitemap_urls_from_file(sitemap))
    unique = [(url, priority) for url, priority in candidates if url not in existing_elsewhere]
    unique = list(dict.fromkeys(unique))
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url, priority in unique:
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = TODAY
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = priority
    ET.ElementTree(root).write(target_path, encoding="utf-8", xml_declaration=True)
    index = site / "sitemap.xml"
    target = BASE + "sitemap-cognitive.xml"
    if index.exists():
        try:
            tree = ET.parse(index)
            top = tree.getroot()
            if top.tag.endswith("sitemapindex"):
                existing = [el.text for el in top.findall("{*}sitemap/{*}loc")]
                if target not in existing:
                    item = ET.SubElement(top, "sitemap")
                    ET.SubElement(item, "loc").text = target
                    tree.write(index, encoding="utf-8", xml_declaration=True)
        except ET.ParseError:
            pass
    robots = site / "robots.txt"
    text = robots.read_text(encoding="utf-8") if robots.exists() else "User-agent: *\nAllow: /\n"
    line = "Sitemap: " + target
    if line not in text:
        text = text.rstrip() + "\n" + line + "\n"
        robots.write_text(text, encoding="utf-8")
    mapped = set(existing_elsewhere)
    mapped.update(url for url, _ in unique)
    unmapped = [url for url in required if url not in mapped]
    return {
        "target_urls": len(unique),
        "required_urls": len(required),
        "mapped_required_urls": len(required) - len(unmapped),
        "unmapped_urls": unmapped,
        "duplicates_avoided": len(candidates) - len(unique),
    }


'''
source, replaced = re.subn(
    r"def write_sitemap\(.*?\n\ndef patch_status_reports",
    lambda _: _new_sitemap + "def patch_status_reports",
    source,
    count=1,
    flags=re.S,
)
if replaced != 1:
    raise SystemExit("Unable to apply sitemap de-duplication patch v246.1")
source = source.replace(
    "def audit(site: Path, legacy: list[dict[str, Any]], modern: list[dict[str, Any]], sitemap_urls: int) -> dict[str, Any]:",
    "def audit(site: Path, legacy: list[dict[str, Any]], modern: list[dict[str, Any]], sitemap: dict[str, Any]) -> dict[str, Any]:",
    1,
)
source = source.replace(
    '    if shallow_legacy_pages:\n        errors.append({"path": "cognitive-tests", "error": f"legacy pages below 550 visible words: {len(shallow_legacy_pages)}"})\n',
    '    if shallow_legacy_pages:\n        errors.append({"path": "cognitive-tests", "error": f"legacy pages below 550 visible words: {len(shallow_legacy_pages)}"})\n    if sitemap.get("unmapped_urls"):\n        errors.append({"path": "sitemap-cognitive.xml", "error": f"unmapped cognitive URLs: {len(sitemap[\'unmapped_urls\'])}"})\n',
    1,
)
source = source.replace(
    '        "sitemap_urls": sitemap_urls,',
    '        "sitemap_urls": int(sitemap["target_urls"]),\n        "sitemap_required_urls": int(sitemap["required_urls"]),\n        "sitemap_mapped_required_urls": int(sitemap["mapped_required_urls"]),\n        "sitemap_duplicates_avoided": int(sitemap["duplicates_avoided"]),\n        "sitemap_unmapped_urls": list(sitemap["unmapped_urls"]),',
    1,
)
source = source.replace(
    '            "sitemap_registered": sitemap_urls == len(legacy) + len(modern) + 2,',
    '            "sitemap_registered": not sitemap.get("unmapped_urls") and int(sitemap.get("mapped_required_urls", 0)) == len(legacy) + len(modern) + 2,',
    1,
)
source = source.replace(
    '    sitemap_urls = write_sitemap(site, legacy, modern)\n    patched_reports = patch_status_reports(site)\n    report = audit(site, legacy, modern, sitemap_urls)',
    '    sitemap = write_sitemap(site, legacy, modern)\n    patched_reports = patch_status_reports(site)\n    report = audit(site, legacy, modern, sitemap)',
    1,
)
source = source.replace(
    '("version", "status", "legacy_sector", "modern_sector", "total_detail_pages", "sitemap_urls", "contracts")',
    '("version", "status", "legacy_sector", "modern_sector", "total_detail_pages", "sitemap_urls", "sitemap_required_urls", "sitemap_mapped_required_urls", "contracts")',
    1,
)
exec(compile(source, __file__, "exec"), {"__name__": __name__, "__file__": __file__})
