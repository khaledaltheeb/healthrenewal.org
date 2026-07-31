#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import publish_autism_clinical_pathways_v324_core as core
from publish_autism_clinical_pathways_v324_core import *  # noqa: F401,F403

ROOT = Path(__file__).resolve().parents[1]
PART_RELATIVE_PATHS = (
    "content/v324/autism-clinical-pathways-ar.parts/part-01.b64",
    "content/v324/autism-clinical-pathways-ar.parts/part-02.b64",
    "content/v324/autism-clinical-pathways-ar.parts/part-03.b64",
    "content/v324/autism-clinical-pathways-ar.parts/part-04.b64",
    "content/v324/autism-clinical-pathways-ar.parts/part-05.b64",
)
PART_PATHS = tuple(ROOT / relative for relative in PART_RELATIVE_PATHS)
PARTS_DIR = ROOT / "content" / "v324" / "autism-clinical-pathways-ar.parts"
PART_NAMES = tuple(path.name for path in PART_PATHS)
EXPECTED_B64_LENGTH = 24652
EXPECTED_B64_SHA256 = "3a1b4b14d25d67b6f72a50d42d45cabc26382f5841fbd4a7e2d7c11e4a44f2eb"
EXPECTED_GZIP_SHA256 = "3350205c4f20177d4cb10fc80c5c9058abffc50c3092f1a60efbc9e96913db5b"
EXPECTED_JSON_SHA256 = "0afeb714ceb04a83b0c2debce97004f87aa104328a7d0070d892b437adc66c17"

SHELL_MARKER = "<!-- pt-platform-shell:v1 -->"
SHELL_HEAD = """<!-- pt-platform-shell:v1 -->
<meta name="copyright" content="© 2026 Khaled Altheeb — منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta name="rights" content="All rights reserved">
<link rel="license" href="/copyright/">
<link rel="stylesheet" href="/assets/platform/platform-core.css?v=1.1.0">
<script defer src="/assets/platform/platform-core.js?v=1.1.0"></script>
"""


BOUNDARY_CLARIFICATIONS = (
    (
        "autism-comprehensive-assessment-differential-diagnosis",
        "medical-etiology",
        0,
        "غياب نتيجة جينية لا ينفي التوحد",
        " غياب نتيجة جينية لا ينفي التوحد؛ فالنتيجة الجينية قد تفسر سببًا أو حالة مصاحبة أو تبقى غير حاسمة، بينما يبقى التشخيص قائمًا على النمط النمائي والسلوك الوظيفي.",
    ),
    (
        "autism-aac-assessment-implementation",
        "right-not-reward",
        0,
        "لا يُسحب نظام AAC لإجبار الشخص على الكلام",
        " لا يُسحب نظام AAC لإجبار الشخص على الكلام أو على تنفيذ استجابة يحددها الراشد.",
    ),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply_boundary_clarifications(payload: dict) -> dict:
    """Add explicit clinical guardrails without changing evidence references.

    The compressed source remains byte-verifiable. These narrowly scoped clauses
    make two already-present safety meanings explicit in the rendered Arabic text.
    """
    guides = payload.get("guides")
    if not isinstance(guides, list):
        raise SystemExit("v324 payload guides must be a list")
    guide_index = {guide.get("slug"): guide for guide in guides if isinstance(guide, dict)}
    applied = 0
    for slug, section_id, paragraph_index, marker, sentence in BOUNDARY_CLARIFICATIONS:
        guide = guide_index.get(slug)
        if not isinstance(guide, dict):
            raise SystemExit(f"Missing v324 guide for boundary clarification: {slug}")
        section = next(
            (
                item
                for item in guide.get("sections", [])
                if isinstance(item, dict) and item.get("id") == section_id
            ),
            None,
        )
        if not isinstance(section, dict):
            raise SystemExit(f"Missing v324 section for boundary clarification: {slug}/{section_id}")
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or paragraph_index >= len(paragraphs):
            raise SystemExit(f"Missing v324 paragraph for boundary clarification: {slug}/{section_id}")
        paragraph = str(paragraphs[paragraph_index])
        if marker not in paragraph:
            paragraphs[paragraph_index] = paragraph + sentence
            applied += 1
    payload["boundary_clarifications"] = {
        "status": "applied",
        "count": len(BOUNDARY_CLARIFICATIONS),
        "newly_appended": applied,
        "scope": "explicit-clinical-guardrails-only",
    }
    return payload


def read_payload() -> dict:
    if not PARTS_DIR.is_dir():
        raise SystemExit(f"Missing v324 source-parts directory: {PARTS_DIR}")
    actual = tuple(
        sorted(path.relative_to(ROOT).as_posix() for path in PARTS_DIR.glob("*.b64"))
    )
    if actual != PART_RELATIVE_PATHS:
        raise SystemExit(
            {"v324_source_parts_mismatch": {"expected": PART_RELATIVE_PATHS, "actual": actual}}
        )

    encoded = "".join(
        "".join(path.read_text(encoding="ascii").split())
        for path in PART_PATHS
    )
    encoded_bytes = encoded.encode("ascii")
    if len(encoded) != EXPECTED_B64_LENGTH:
        raise SystemExit(
            {"v324_base64_length_mismatch": {"expected": EXPECTED_B64_LENGTH, "actual": len(encoded)}}
        )
    if sha256(encoded_bytes) != EXPECTED_B64_SHA256:
        raise SystemExit("v324 Base64 source digest mismatch")

    try:
        compressed = base64.b64decode(encoded_bytes, validate=True)
    except Exception as exc:
        raise SystemExit(f"Invalid v324 Base64 source: {exc}") from exc
    if sha256(compressed) != EXPECTED_GZIP_SHA256:
        raise SystemExit("v324 Gzip source digest mismatch")

    try:
        raw = gzip.decompress(compressed)
    except Exception as exc:
        raise SystemExit(f"Invalid v324 Gzip source: {exc}") from exc
    if sha256(raw) != EXPECTED_JSON_SHA256:
        raise SystemExit("v324 JSON source digest mismatch")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid v324 UTF-8 JSON source: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("v324 payload must be a JSON object")
    return apply_boundary_clarifications(payload)


# Keep the full renderer isolated in the core module, but make its source loader
# deterministic and text-transport-safe for GitHub Contents/API workflows.
core.CONTENT = PARTS_DIR
core.read_payload = read_payload


def normalize_page(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if SHELL_MARKER not in source:
        if "</head>" not in source:
            raise SystemExit(f"Missing head in generated v324 page: {path}")
        source = source.replace("</head>", SHELL_HEAD + "</head>", 1)
    source, count = re.subn(
        r"<body(?:\s[^>]*)?>",
        '<body class="pt-platform" data-pt-normalized="1.1.0" data-pt-enhancer="true">',
        source,
        count=1,
        flags=re.I,
    )
    if count != 1 or source.count(SHELL_MARKER) != 1:
        raise SystemExit(f"Platform shell normalization failed: {path}")
    path.write_text(source, encoding="utf-8")


def normalize_sitemap(path: Path) -> None:
    """Write the URL set in a stable order and with stable XML whitespace."""
    if not path.is_file():
        raise SystemExit(f"Missing sitemap for v324 normalization: {path}")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ET.parse(path)
    root = tree.getroot()
    children = list(root)
    if any(child.tag.rsplit("}", 1)[-1] != "url" for child in children):
        raise SystemExit("sitemap-special-needs.xml must remain a URL set")
    children.sort(key=lambda row: (row.findtext("{*}loc") or "").strip())
    root[:] = children
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict:
    report = core.publish(site)
    normalize_sitemap(site / "sitemap-special-needs.xml")
    for relative in report["generated_pages"]:
        normalize_page(site / relative)
    for item in report["pages"]:
        path = site / item["path"]
        source = path.read_text(encoding="utf-8")
        if SHELL_MARKER not in source or 'data-pt-normalized="1.1.0"' not in source:
            raise SystemExit(f"Missing institutional shell after normalization: {item['slug']}")
        item["words"] = core.words(source)
    report["minimum_guide_words"] = min(item["words"] for item in report["pages"])
    report["total_guide_words"] = sum(item["words"] for item in report["pages"])
    report["platform_shell_normalized"] = True
    report["sitemap_canonicalized"] = True
    report["source_part_count"] = len(PART_PATHS)
    report["source_base64_sha256"] = EXPECTED_B64_SHA256
    report["source_gzip_sha256"] = EXPECTED_GZIP_SHA256
    report["source_json_sha256"] = EXPECTED_JSON_SHA256
    report["boundary_clarifications"] = {
        "status": "applied",
        "count": len(BOUNDARY_CLARIFICATIONS),
        "scope": "explicit-clinical-guardrails-only",
    }
    api = site / "api" / "autism-clinical-pathways-v324.json"
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
