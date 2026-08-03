#!/usr/bin/env python3
"""Materialize and validate the evidence-based Arabic addiction reference.

The source package is split into small, checksum-protected text chunks so the
static pages can be rebuilt reproducibly inside the canonical deployment job.
The generator never deletes source files and never overwrites an existing
sitemap index; it merges the addiction sitemap into the current index.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import lzma
import shutil
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHUNKS = sorted((REPOSITORY_ROOT / "scripts").glob(".addiction_payload_*"))
EXPECTED_CHUNKS = 7
EXPECTED_XZ_SHA256 = "717927d839784e453091d3086d17ae3689251f93545c1b1222e119473c1f0d63"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_URL = "https://healthrenewal.org/sitemap-addiction.xml"


def fail(message: str) -> None:
    raise SystemExit(message)


def load_payload() -> bytes:
    if len(CHUNKS) != EXPECTED_CHUNKS:
        fail(f"Expected {EXPECTED_CHUNKS} payload chunks, found {len(CHUNKS)}")
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in CHUNKS)
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        fail(f"Invalid addiction payload encoding: {exc}")
    digest = hashlib.sha256(compressed).hexdigest()
    if digest != EXPECTED_XZ_SHA256:
        fail(f"Payload checksum mismatch: {digest}")
    try:
        return lzma.decompress(compressed)
    except lzma.LZMAError as exc:
        fail(f"Unable to decompress addiction payload: {exc}")


def safe_extract(payload: bytes, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()
    extracted: list[str] = []

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                fail(f"Unsafe archive path: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                fail(f"Unsupported archive member: {member.name}")
            if member.name == "sitemap-index.xml":
                continue

            target = (destination / relative).resolve()
            if target != destination_resolved and destination_resolved not in target.parents:
                fail(f"Archive member escapes destination: {member.name}")

            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                fail(f"Unsupported archive member type: {member.name}")

            source = archive.extractfile(member)
            if source is None:
                fail(f"Unable to read archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(member.name)

    return extracted


def merge_sitemap_index(destination: Path) -> None:
    index_path = destination / "sitemap-index.xml"
    ET.register_namespace("", SITEMAP_NAMESPACE)
    qualified = f"{{{SITEMAP_NAMESPACE}}}"

    if index_path.exists():
        try:
            tree = ET.parse(index_path)
        except ET.ParseError as exc:
            fail(f"Existing sitemap-index.xml is invalid: {exc}")
        root = tree.getroot()
        if root.tag not in {"sitemapindex", f"{qualified}sitemapindex"}:
            fail(f"Unexpected sitemap index root: {root.tag}")
    else:
        root = ET.Element(f"{qualified}sitemapindex")
        tree = ET.ElementTree(root)

    existing = {
        (node.text or "").strip()
        for node in root.findall(f"{qualified}sitemap/{qualified}loc")
    }
    if SITEMAP_URL not in existing:
        sitemap = ET.SubElement(root, f"{qualified}sitemap")
        ET.SubElement(sitemap, f"{qualified}loc").text = SITEMAP_URL

    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")
    tree.write(index_path, encoding="utf-8", xml_declaration=True)


def validate(destination: Path) -> dict[str, object]:
    manifest_path = destination / "addiction" / "editorial-manifest.json"
    if not manifest_path.exists():
        fail("Missing addiction/editorial-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    condition_pages = manifest.get("condition_pages", [])
    if len(condition_pages) != 10:
        fail(f"Expected 10 condition pages, found {len(condition_pages)}")
    if manifest.get("reference_count") != 50:
        fail(f"Expected 50 references, found {manifest.get('reference_count')}")
    protocol_total = sum(int(item.get("protocol_count", 0)) for item in condition_pages)
    if protocol_total != 100:
        fail(f"Expected 100 protocols in manifest, found {protocol_total}")

    html_pages = sorted((destination / "addiction").glob("**/index.html"))
    if len(html_pages) != 15:
        fail(f"Expected 15 addiction HTML pages, found {len(html_pages)}")

    required_markers = (
        '<html lang="ar" dir="rtl">',
        "<title>",
        'name="description"',
        'rel="canonical"',
        "<h1",
        'type="application/ld+json"',
    )
    for page in html_pages:
        text = page.read_text(encoding="utf-8")
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            fail(f"{page.relative_to(destination)} missing: {', '.join(missing)}")

    for item in condition_pages:
        page = destination / "addiction" / item["slug"] / "index.html"
        if not page.exists():
            fail(f"Missing condition page: {page.relative_to(destination)}")
        text = page.read_text(encoding="utf-8")
        count = text.count('class="protocol"')
        if count != 10:
            fail(f"{page.relative_to(destination)} has {count} protocols, expected 10")
        if "الطوارئ" not in text:
            fail(f"{page.relative_to(destination)} lacks emergency safety language")

    evidence_text = (
        destination / "addiction" / "evidence-library" / "index.html"
    ).read_text(encoding="utf-8")
    if evidence_text.count('class="source"') != 50:
        fail("Evidence library does not contain exactly 50 source cards")

    ET.parse(destination / "sitemap-addiction.xml")
    ET.parse(destination / "sitemap-index.xml")
    if SITEMAP_URL not in (destination / "sitemap-index.xml").read_text(encoding="utf-8"):
        fail("sitemap-index.xml does not advertise sitemap-addiction.xml")

    banned_fragments = ("جرعة:", " ملغ", " mg ", "خفض الجرعة بنسبة", "تناول حبة")
    corpus = "\n".join(page.read_text(encoding="utf-8") for page in html_pages)
    found = [fragment for fragment in banned_fragments if fragment in corpus]
    if found:
        fail(f"Unsafe self-treatment dosing fragments found: {found}")

    return {
        "schemaVersion": 1,
        "status": "passed",
        "generatedAt": "2026-08-03",
        "htmlPages": len(html_pages),
        "conditionPages": len(condition_pages),
        "protocols": protocol_total,
        "references": manifest["reference_count"],
        "sitemap": "sitemap-addiction.xml",
        "safety": manifest.get("safety_contract", {}),
    }


def materialize(destination: Path) -> dict[str, object]:
    payload = load_payload()
    extracted = safe_extract(payload, destination)
    merge_sitemap_index(destination)
    report = validate(destination)
    report["extractedMembers"] = len(extracted)

    api = destination / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "addiction-reference-v1.json").write_text(
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
        help="Static site output directory (default: _site)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    destination = Path(args.destination)
    if not destination.is_absolute():
        destination = REPOSITORY_ROOT / destination
    report = materialize(destination)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
