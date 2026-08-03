#!/usr/bin/env python3
"""Materialize detailed Arabic addiction condition guides into a static site.

The generated guides extend the existing addiction center without replacing its
hub, protocol atlas, withdrawal guide, recovery roadmap, family guide, or
authoritative source registry.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import lzma
import shutil
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PARTS = sorted(
    (REPOSITORY_ROOT / "content" / "addiction").glob(
        "condition-guides-v2.part*.b64"
    )
)
EXPECTED_PARTS = 2
EXPECTED_XZ_SHA256 = (
    "717927d839784e453091d3086d17ae3689251f93545c1b1222e119473c1f0d63"
)
BASE_URL = "https://healthrenewal.org/"
LAST_MODIFIED = "2026-08-03"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_URL = f"{BASE_URL}sitemap-addiction.xml"

CONDITION_SLUGS = (
    "alcohol-use-disorder",
    "opioid-use-disorder",
    "stimulant-use-disorder",
    "cannabis-use-disorder",
    "nicotine-tobacco-dependence",
    "sedative-benzodiazepine-use-disorder",
    "gambling-related-harms",
    "gaming-disorder",
    "inhalant-use-disorder",
    "polysubstance-use-and-overdose-risk",
)

ALLOWED_ARCHIVE_FILES = {
    "assets/addiction/addiction-core.css",
    "addiction/editorial-manifest.json",
    "addiction/methodology/index.html",
    *(f"addiction/{slug}/index.html" for slug in CONDITION_SLUGS),
}

LINK_REPLACEMENTS = {
    "/addiction/evidence-library/": "/addiction/sources/",
    "/addiction/recovery-plan/": "/addiction/recovery-roadmap/",
}

AUTHORITATIVE_EXISTING_ROUTES = (
    "addiction/index.html",
    "addiction/protocol-atlas/index.html",
    "addiction/withdrawal-safety/index.html",
    "addiction/recovery-roadmap/index.html",
    "addiction/family-guide/index.html",
    "addiction/sources/index.html",
)

NEW_ROUTE_PATHS = (
    "addiction/conditions/index.html",
    "addiction/methodology/index.html",
    *(f"addiction/{slug}/index.html" for slug in CONDITION_SLUGS),
)

BANNED_SELF_TREATMENT_FRAGMENTS = (
    "جرعة:",
    " ملغ",
    " mg ",
    "خفض الجرعة بنسبة",
    "تناول حبة",
)


def fail(message: str) -> None:
    raise SystemExit(message)


def _read_payload() -> bytes:
    if len(PAYLOAD_PARTS) != EXPECTED_PARTS:
        fail(
            f"Expected {EXPECTED_PARTS} condition-guide payload parts, "
            f"found {len(PAYLOAD_PARTS)}"
        )

    encoded = "".join(
        part.read_text(encoding="ascii").strip() for part in PAYLOAD_PARTS
    )
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        fail(f"Invalid condition-guide payload encoding: {exc}")

    digest = hashlib.sha256(compressed).hexdigest()
    if digest != EXPECTED_XZ_SHA256:
        fail(f"Condition-guide payload checksum mismatch: {digest}")

    try:
        return lzma.decompress(compressed)
    except lzma.LZMAError as exc:
        fail(f"Unable to decompress condition-guide payload: {exc}")


def _authoritative_hashes(destination: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in AUTHORITATIVE_EXISTING_ROUTES:
        path = destination / relative
        if not path.is_file():
            fail(f"Missing authoritative addiction-center page: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _write_archive_member(
    destination: Path,
    member: tarfile.TarInfo,
    source: io.BufferedReader,
) -> None:
    target = destination / member.name
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = source.read()

    if member.name.endswith(".html"):
        text = raw.decode("utf-8")
        for old, new in LINK_REPLACEMENTS.items():
            text = text.replace(old, new)
        target.write_text(text, encoding="utf-8")
        return

    if member.name == "addiction/editorial-manifest.json":
        manifest = json.loads(raw.decode("utf-8"))
        manifest["version"] = "2.0.0"
        manifest["integration"] = {
            "extends_existing_center": True,
            "authoritative_source_registry": "/addiction/sources/",
            "authoritative_recovery_roadmap": "/addiction/recovery-roadmap/",
            "existing_center_pages_preserved": list(AUTHORITATIVE_EXISTING_ROUTES),
        }
        manifest["support_pages"] = [
            "withdrawal-safety",
            "recovery-roadmap",
            "methodology",
            "sources",
        ]
        target.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return

    target.write_bytes(raw)


def _extract_selected(payload: bytes, destination: Path) -> list[str]:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    seen: set[str] = set()

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            if member.name not in ALLOWED_ARCHIVE_FILES:
                continue
            if member.name in seen:
                fail(f"Duplicate archive member: {member.name}")
            seen.add(member.name)

            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                fail(f"Unsafe archive path: {member.name}")
            if not member.isfile() or member.issym() or member.islnk() or member.isdev():
                fail(f"Unsupported archive member: {member.name}")

            target = (destination / relative).resolve()
            if target != destination and destination not in target.parents:
                fail(f"Archive member escapes destination: {member.name}")

            source = archive.extractfile(member)
            if source is None:
                fail(f"Unable to read archive member: {member.name}")
            with source:
                _write_archive_member(destination, member, source)
            extracted.append(member.name)

    missing = sorted(ALLOWED_ARCHIVE_FILES - seen)
    if missing:
        fail(f"Condition-guide payload is missing expected files: {missing}")
    return sorted(extracted)


def _qualified(name: str) -> str:
    return f"{{{SITEMAP_NAMESPACE}}}{name}"


def _read_or_create_urlset(path: Path) -> ET.ElementTree:
    ET.register_namespace("", SITEMAP_NAMESPACE)
    if not path.exists():
        return ET.ElementTree(ET.Element(_qualified("urlset")))

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        fail(f"Invalid {path.name}: {exc}")
    root = tree.getroot()
    if root.tag not in {"urlset", _qualified("urlset")}:
        fail(f"Unexpected root in {path.name}: {root.tag}")
    return tree


def _merge_addiction_sitemap(destination: Path) -> None:
    path = destination / "sitemap-addiction.xml"
    tree = _read_or_create_urlset(path)
    root = tree.getroot()

    existing = {
        (item.text or "").strip()
        for item in root.findall(f"{_qualified('url')}/{_qualified('loc')}")
    }
    urls = [
        f"{BASE_URL}addiction/conditions/",
        f"{BASE_URL}addiction/methodology/",
        *(f"{BASE_URL}addiction/{slug}/" for slug in CONDITION_SLUGS),
    ]
    for url in urls:
        if url in existing:
            continue
        item = ET.SubElement(root, _qualified("url"))
        ET.SubElement(item, _qualified("loc")).text = url
        ET.SubElement(item, _qualified("lastmod")).text = LAST_MODIFIED
        ET.SubElement(item, _qualified("changefreq")).text = "monthly"
        ET.SubElement(item, _qualified("priority")).text = (
            "0.9" if url.endswith("/conditions/") else "0.8"
        )

    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _merge_sitemap_index(destination: Path) -> None:
    path = destination / "sitemap-index.xml"
    ET.register_namespace("", SITEMAP_NAMESPACE)
    if path.exists():
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            fail(f"Invalid sitemap-index.xml: {exc}")
        root = tree.getroot()
        if root.tag not in {"sitemapindex", _qualified("sitemapindex")}:
            fail(f"Unexpected sitemap index root: {root.tag}")
    else:
        root = ET.Element(_qualified("sitemapindex"))
        tree = ET.ElementTree(root)

    existing = {
        (item.text or "").strip()
        for item in root.findall(f"{_qualified('sitemap')}/{_qualified('loc')}")
    }
    if SITEMAP_URL not in existing:
        sitemap = ET.SubElement(root, _qualified("sitemap"))
        ET.SubElement(sitemap, _qualified("loc")).text = SITEMAP_URL

    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def merge_discovery(destination: Path) -> None:
    """Re-register the custom addiction sitemap after canonical sitemap rebuilds."""
    destination = destination.resolve()
    _merge_addiction_sitemap(destination)
    _merge_sitemap_index(destination)


def _source_registry_count(destination: Path) -> int:
    source_page = destination / "addiction" / "sources" / "index.html"
    if not source_page.is_file():
        fail("Missing authoritative addiction source registry")
    text = source_page.read_text(encoding="utf-8")
    count = text.count('class="source"')
    if count < 50:
        fail(f"Expected at least 50 source entries, found {count}")
    return count


def validate(destination: Path) -> dict[str, object]:
    destination = destination.resolve()
    manifest_path = destination / "addiction" / "editorial-manifest.json"
    if not manifest_path.is_file():
        fail("Missing addiction/editorial-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    condition_pages = manifest.get("condition_pages", [])
    if len(condition_pages) != 10:
        fail(f"Expected 10 detailed condition pages, found {len(condition_pages)}")
    protocol_total = sum(int(item.get("protocol_count", 0)) for item in condition_pages)
    if protocol_total != 100:
        fail(f"Expected 100 detailed protocols, found {protocol_total}")

    conditions_index = destination / "addiction" / "conditions" / "index.html"
    if not conditions_index.is_file():
        fail("Missing addiction/conditions/index.html")
    index_text = conditions_index.read_text(encoding="utf-8")
    missing_links = [
        slug
        for slug in CONDITION_SLUGS
        if f'/addiction/{slug}/' not in index_text
    ]
    if missing_links:
        fail(f"Condition index is missing guide links: {missing_links}")

    required_markers = (
        '<html lang="ar" dir="rtl">',
        "<title>",
        'name="description"',
        'rel="canonical"',
        "<h1",
        'type="application/ld+json"',
    )
    detailed_texts: list[str] = []
    for slug in CONDITION_SLUGS:
        page = destination / "addiction" / slug / "index.html"
        if not page.is_file():
            fail(f"Missing detailed condition page: {slug}")
        text = page.read_text(encoding="utf-8")
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            fail(f"{page.relative_to(destination)} missing: {', '.join(missing)}")
        count = text.count('class="protocol"')
        if count != 10:
            fail(f"{page.relative_to(destination)} has {count} protocols, expected 10")
        if "الطوارئ" not in text:
            fail(f"{page.relative_to(destination)} lacks emergency safety language")
        if "/addiction/evidence-library/" in text or "/addiction/recovery-plan/" in text:
            fail(f"{page.relative_to(destination)} contains obsolete support links")
        detailed_texts.append(text)

    methodology = destination / "addiction" / "methodology" / "index.html"
    if not methodology.is_file():
        fail("Missing addiction/methodology/index.html")
    methodology_text = methodology.read_text(encoding="utf-8")
    if "الطوارئ" not in methodology_text and "السلامة" not in methodology_text:
        fail("Methodology page lacks explicit safety framing")
    detailed_texts.append(methodology_text)

    found = [
        fragment
        for fragment in BANNED_SELF_TREATMENT_FRAGMENTS
        if fragment in "\n".join(detailed_texts)
    ]
    if found:
        fail(f"Unsafe self-treatment dosing fragments found: {found}")

    for relative in AUTHORITATIVE_EXISTING_ROUTES:
        if not (destination / relative).is_file():
            fail(f"Authoritative center route disappeared: {relative}")

    source_registry = _source_registry_count(destination)
    center_pages = len(list((destination / "addiction").glob("**/index.html")))
    if center_pages < 18:
        fail(f"Expected at least 18 addiction center pages, found {center_pages}")

    merge_discovery(destination)
    ET.parse(destination / "sitemap-addiction.xml")
    ET.parse(destination / "sitemap-index.xml")
    addiction_sitemap = (
        destination / "sitemap-addiction.xml"
    ).read_text(encoding="utf-8")
    for relative in NEW_ROUTE_PATHS:
        route = relative.removesuffix("index.html")
        expected = f"{BASE_URL}{route}"
        if expected not in addiction_sitemap:
            fail(f"Addiction sitemap is missing {expected}")
    if SITEMAP_URL not in (
        destination / "sitemap-index.xml"
    ).read_text(encoding="utf-8"):
        fail("sitemap-index.xml does not register sitemap-addiction.xml")

    return {
        "schemaVersion": 2,
        "status": "passed",
        "generatedAt": LAST_MODIFIED,
        "centerPages": center_pages,
        "conditionPages": len(CONDITION_SLUGS),
        "detailedProtocols": protocol_total,
        "sourceRegistryEntries": source_registry,
        "newRoutes": [
            f"/{relative.removesuffix('index.html')}" for relative in NEW_ROUTE_PATHS
        ],
        "preservedAuthoritativeRoutes": [
            f"/{relative.removesuffix('index.html')}"
            for relative in AUTHORITATIVE_EXISTING_ROUTES
        ],
        "safety": {
            "noIndividualDosing": True,
            "noHomeDetoxPlan": True,
            "emergencyRedFlagsRequired": True,
            "withdrawalIsNotLongTermTreatment": True,
        },
    }


def materialize(destination: Path, *, merge_sitemaps: bool = True) -> dict[str, object]:
    destination = destination.resolve()
    before = _authoritative_hashes(destination)
    extracted = _extract_selected(_read_payload(), destination)
    after = _authoritative_hashes(destination)
    if before != after:
        changed = sorted(path for path in before if before[path] != after[path])
        fail(f"Materializer modified authoritative center pages: {changed}")

    if merge_sitemaps:
        merge_discovery(destination)
    report = validate(destination)
    report["extractedFiles"] = extracted
    report["payloadSha256"] = EXPECTED_XZ_SHA256

    api = destination / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "addiction-condition-guides-v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination",
        nargs="?",
        default="_site",
        type=Path,
        help="Static-site output directory (default: _site)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    destination = args.destination
    if not destination.is_absolute():
        destination = REPOSITORY_ROOT / destination
    report = materialize(destination)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
