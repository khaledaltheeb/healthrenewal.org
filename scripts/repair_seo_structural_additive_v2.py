#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_TARGETS = (
    Path("learning-paths/all-pages/index.html"),
    Path("sectors/all-pages/index.html"),
    Path("special-needs/all-pages/index.html"),
)
REFERENCE = Path("special-needs/reference/index.html")
H1_RE = re.compile(r"(<h1\b[^>]*>.*?</h1\s*>)", re.I | re.S)
H2_RE = re.compile(r"<h2\b", re.I)
HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.I)
JSONLD_RE = re.compile(r"<script\b[^>]*type=[\"']application/ld\+json[\"']", re.I)

INDEX_INSERTION = (
    '<section class="directory-intro" data-seo-structural-v2="true">'
    '<h2>دليل الصفحات المنشورة</h2>'
    '<p>تصفح البطاقات التالية للوصول إلى الصفحات المنشورة ضمن هذا القسم. يحافظ هذا الفهرس على الروابط الأصلية ويضيف مستوى عنوان واضحًا لتنظيم بنية الصفحة.</p>'
    '</section>'
)

REFERENCE_JSONLD = (
    '<script type="application/ld+json" data-seo-structural-v2="true">'
    '{"@context":"https://schema.org","@type":"CollectionPage",'
    '"name":"المراجع الأساسية في الإعاقة والتربية الخاصة والدمج",'
    '"url":"https://healthrenewal.org/special-needs/reference/",'
    '"inLanguage":"ar",'
    '"isPartOf":{"@type":"WebSite","name":"منصة روافد","url":"https://healthrenewal.org/"}}'
    '</script>'
)


def add_index_structure(source: str) -> tuple[str, bool, str]:
    if H2_RE.search(source):
        return source, False, "h2-already-present"
    match = H1_RE.search(source)
    if not match:
        return source, False, "missing-h1-anchor"
    updated = source[:match.end()] + INDEX_INSERTION + source[match.end():]
    # Strict additive invariant: removing our exact insertion must reproduce input.
    if updated.replace(INDEX_INSERTION, "", 1) != source:
        raise RuntimeError("additive invariant failed for directory index")
    return updated, True, "inserted-h2-directory-intro"


def add_reference_schema(source: str) -> tuple[str, bool, str]:
    if JSONLD_RE.search(source):
        return source, False, "jsonld-already-present"
    match = HEAD_CLOSE_RE.search(source)
    if not match:
        return source, False, "missing-head-anchor"
    updated = source[:match.start()] + REFERENCE_JSONLD + source[match.start():]
    if updated.replace(REFERENCE_JSONLD, "", 1) != source:
        raise RuntimeError("additive invariant failed for reference schema")
    return updated, True, "inserted-collectionpage-jsonld"


def process(path: Path, check: bool) -> dict[str, object]:
    full = ROOT / path
    if not full.is_file():
        return {"path": path.as_posix(), "status": "missing"}
    source = full.read_text(encoding="utf-8")
    if path == REFERENCE:
        updated, changed, detail = add_reference_schema(source)
    else:
        updated, changed, detail = add_index_structure(source)
    if changed and not check:
        full.write_text(updated, encoding="utf-8")
    return {"path": path.as_posix(), "status": "needs-update" if changed and check else "updated" if changed else "current", "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    results = [process(path, args.check) for path in (*INDEX_TARGETS, REFERENCE)]
    print(json.dumps({"version": 2, "mode": "check" if args.check else "write", "results": results}, ensure_ascii=False, indent=2))
    if any(item["status"] == "missing" for item in results):
        return 2
    if args.check and any(item["status"] == "needs-update" for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
