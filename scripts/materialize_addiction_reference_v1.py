#!/usr/bin/env python3
"""Materialize the evidence-based Arabic addiction reference from staged payload chunks."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import lzma
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = sorted((ROOT / "scripts").glob(".addiction_payload_*"))
EXPECTED_CHUNKS = 7
EXPECTED_XZ_SHA256 = "717927d839784e453091d3086d17ae3689251f93545c1b1222e119473c1f0d63"
SELF = ROOT / "scripts" / "materialize_addiction_reference_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "materialize-addiction-reference-v1.yml"


def fail(message: str) -> None:
    raise SystemExit(message)


def safe_extract(payload: bytes) -> list[str]:
    extracted: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                fail(f"Unsafe archive path: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                fail(f"Unsupported archive member: {member.name}")
            target = (ROOT / path).resolve()
            if ROOT.resolve() not in target.parents and target != ROOT.resolve():
                fail(f"Archive member escapes repository: {member.name}")
            extracted.append(member.name)
        archive.extractall(ROOT)
    return extracted


def validate() -> dict[str, object]:
    manifest_path = ROOT / "addiction" / "editorial-manifest.json"
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

    html_pages = sorted((ROOT / "addiction").glob("**/index.html"))
    if len(html_pages) != 15:
        fail(f"Expected 15 addiction HTML pages, found {len(html_pages)}")

    for page in html_pages:
        text = page.read_text(encoding="utf-8")
        required = [
            '<html lang="ar" dir="rtl">',
            "<title>",
            'name="description"',
            'rel="canonical"',
            "<h1",
            'type="application/ld+json"',
        ]
        missing = [marker for marker in required if marker not in text]
        if missing:
            fail(f"{page.relative_to(ROOT)} missing: {', '.join(missing)}")

    for item in condition_pages:
        page = ROOT / "addiction" / item["slug"] / "index.html"
        text = page.read_text(encoding="utf-8")
        count = text.count('class="protocol"')
        if count != 10:
            fail(f"{page.relative_to(ROOT)} has {count} protocols, expected 10")
        if "اطلب الطوارئ" not in text and "الطوارئ" not in text:
            fail(f"{page.relative_to(ROOT)} lacks emergency safety language")

    evidence_text = (ROOT / "addiction" / "evidence-library" / "index.html").read_text(
        encoding="utf-8"
    )
    if evidence_text.count('class="source"') != 50:
        fail("Evidence library does not contain exactly 50 source cards")

    ET.parse(ROOT / "sitemap-addiction.xml")
    ET.parse(ROOT / "sitemap-index.xml")
    if "sitemap-addiction.xml" not in (ROOT / "sitemap-index.xml").read_text(
        encoding="utf-8"
    ):
        fail("sitemap-index.xml does not advertise sitemap-addiction.xml")

    banned_fragments = ["جرعة:", " ملغ", " mg ", "خفض الجرعة بنسبة", "تناول حبة"]
    corpus = "\n".join(page.read_text(encoding="utf-8") for page in html_pages)
    found = [fragment for fragment in banned_fragments if fragment in corpus]
    if found:
        fail(f"Unsafe self-treatment dosing fragments found: {found}")

    return {
        "status": "passed",
        "html_pages": len(html_pages),
        "condition_pages": len(condition_pages),
        "protocols": protocol_total,
        "references": manifest["reference_count"],
        "sitemap": "sitemap-addiction.xml",
    }


def main() -> None:
    if len(CHUNKS) != EXPECTED_CHUNKS:
        fail(f"Expected {EXPECTED_CHUNKS} payload chunks, found {len(CHUNKS)}")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in CHUNKS)
    compressed = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(compressed).hexdigest()
    if digest != EXPECTED_XZ_SHA256:
        fail(f"Payload checksum mismatch: {digest}")

    tar_payload = lzma.decompress(compressed)
    extracted = safe_extract(tar_payload)
    report = validate()

    for path in CHUNKS:
        path.unlink(missing_ok=True)
    SELF.unlink(missing_ok=True)
    WORKFLOW.unlink(missing_ok=True)

    report["extracted_members"] = len(extracted)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
