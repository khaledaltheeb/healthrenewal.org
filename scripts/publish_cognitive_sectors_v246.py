from __future__ import annotations

# Verified compressed source bundle for the institutional cognitive sectors publisher.
import base64
import gzip
import json
import re
import sys
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

LEGACY_ROUTE = "cognitive-tests/verbal-analogies/index.html"
LEGACY_SLUG = "verbal-analogies"
LEGACY_OLD_TITLE = "التناظر اللفظي"
LEGACY_NEW_TITLE = "اختبار التناظر اللفظي التقليدي"
REPORT_PATH = "api/cognitive-sectors-v246.json"


def _replace_first_element_text(source_text: str, tag: str, replacement: str) -> tuple[str, int]:
    pattern = re.compile(rf"(<{tag}\b[^>]*>)(.*?)(</{tag}>)", re.I | re.S)
    return pattern.subn(lambda match: match.group(1) + replacement + match.group(3), source_text, count=1)


def _replace_title_metadata(source_text: str, replacement: str) -> tuple[str, int]:
    changed = 0

    def replace_meta(match: re.Match[str]) -> str:
        nonlocal changed
        tag = match.group(0)
        attrs = {
            key.lower(): value
            for key, _, value in re.findall(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", tag, re.I | re.S)
        }
        if attrs.get("property", "").lower() != "og:title" and attrs.get("name", "").lower() != "twitter:title":
            return tag
        content_match = re.search(r"\bcontent\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
        if not content_match:
            return tag
        changed += 1
        quote = content_match.group(1)
        return tag[: content_match.start()] + f"content={quote}{replacement}{quote}" + tag[content_match.end() :]

    return re.sub(r"<meta\b[^>]*>", replace_meta, source_text, flags=re.I | re.S), changed


def disambiguate_legacy_verbal_analogy(site: Path) -> dict[str, object]:
    site = site.resolve()
    page = site / LEGACY_ROUTE
    report_path = site / REPORT_PATH
    if not page.is_file():
        raise SystemExit(f"Missing legacy verbal analogy page: {page}")
    if not report_path.is_file():
        raise SystemExit(f"Missing cognitive sector report: {report_path}")

    original = page.read_text(encoding="utf-8")
    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", original, re.I | re.S)
    if not title_match:
        raise SystemExit("Legacy verbal analogy page has no title")
    current_full_title = re.sub(r"\s+", " ", title_match.group(1)).strip()
    suffix = current_full_title.split(" | ", 1)[1] if " | " in current_full_title else ""
    new_full_title = LEGACY_NEW_TITLE + (f" | {suffix}" if suffix else "")

    updated, title_count = _replace_first_element_text(original, "title", new_full_title)
    updated, h1_count = _replace_first_element_text(updated, "h1", LEGACY_NEW_TITLE)
    updated, meta_count = _replace_title_metadata(updated, new_full_title)
    updated, json_ld_count = re.subn(
        rf'("name"\s*:\s*")({re.escape(LEGACY_OLD_TITLE)})(")',
        lambda match: match.group(1) + LEGACY_NEW_TITLE + match.group(3),
        updated,
    )

    if title_count != 1 or h1_count != 1:
        raise SystemExit(
            f"Legacy verbal analogy title contract failed: title={title_count}, h1={h1_count}"
        )
    if LEGACY_OLD_TITLE + " | " in updated:
        raise SystemExit("Legacy duplicate title remains after disambiguation")
    if updated.count(f"<title>{new_full_title}</title>") != 1:
        raise SystemExit("Disambiguated legacy title is not unique in the page")
    page.write_text(updated, encoding="utf-8")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    matches = [item for item in report.get("legacy_pages", []) if item.get("slug") == LEGACY_SLUG]
    if len(matches) != 1:
        raise SystemExit(f"Expected one legacy report row for {LEGACY_SLUG}, found {len(matches)}")
    matches[0]["title"] = LEGACY_NEW_TITLE
    contracts = report.setdefault("contracts", {})
    contracts["legacy_verbal_analogy_title_disambiguated"] = True
    report["title_disambiguation_version"] = 314
    report["title_disambiguation"] = {
        "path": LEGACY_ROUTE,
        "slug": LEGACY_SLUG,
        "old_title": LEGACY_OLD_TITLE,
        "new_title": LEGACY_NEW_TITLE,
        "title_updates": title_count,
        "h1_updates": h1_count,
        "social_title_updates": meta_count,
        "json_ld_name_updates": json_ld_count,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return report["title_disambiguation"]


_namespace: dict[str, object] = {
    "__name__": "pterminology_cognitive_sectors_v246_core",
    "__file__": __file__,
}
exec(compile(source, __file__, "exec"), _namespace)


def main() -> int:
    core_main = _namespace.get("main")
    if not callable(core_main):
        raise SystemExit("Cognitive sector core main() was not defined")
    result = core_main()
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    evidence = disambiguate_legacy_verbal_analogy(site)
    print(json.dumps({"title_disambiguation": evidence}, ensure_ascii=False, indent=2))
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
