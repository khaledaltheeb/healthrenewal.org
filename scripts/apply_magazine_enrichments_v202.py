#!/usr/bin/env python3
"""Append evidence-backed completion sections to explicit magazine pages.

The enrichment registry is source-first and page-specific. This script never
replaces existing prose: it inserts one marked semantic section immediately
before the final article/main/body closing tag. The operation is idempotent and
fails closed when a target page or safe insertion point is missing.

It is designed for build workspaces so historical source HTML remains reviewable
while the production build receives additive scientific completion. Once an
individual page is regenerated from structured content, its registry entry can
be retired without changing the editorial contract.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "magazine-enrichments-v202-batch1.json"
ALLOWED_SECTION_KEYS = {
    "research_question",
    "design",
    "sample",
    "exposure_or_intervention",
    "results",
    "interpretation",
    "limitations",
    "generalizability",
    "rawafid_reading",
    "practical_implications",
    "not_proven",
    "references",
}


def load_registry(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected registry JSON object: {path}")
    batch = str(data.get("batch") or "").strip()
    records = data.get("records")
    if not batch or not isinstance(records, list) or not records:
        raise SystemExit("Enrichment registry requires non-empty batch and records")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise SystemExit("Every enrichment record must be an object")
        rel = str(record.get("path") or "").strip()
        if not rel.startswith("magazine/") or ".." in Path(rel).parts:
            raise SystemExit(f"Invalid magazine enrichment path: {rel}")
        if rel in seen:
            raise SystemExit(f"Duplicate magazine enrichment path: {rel}")
        seen.add(rel)
        source = record.get("source")
        if not isinstance(source, dict) or not source.get("title") or not source.get("url"):
            raise SystemExit(f"Missing source metadata for {rel}")
        source_url = str(source["url"])
        if not source_url.startswith("https://"):
            raise SystemExit(f"Source URL must use HTTPS for {rel}: {source_url}")
        sections = record.get("sections")
        if not isinstance(sections, list) or not sections:
            raise SystemExit(f"No enrichment sections for {rel}")
        section_keys: set[str] = set()
        for section in sections:
            if not isinstance(section, dict):
                raise SystemExit(f"Invalid section object in {rel}")
            key = str(section.get("key") or "").strip()
            heading = str(section.get("heading") or "").strip()
            paragraphs = section.get("paragraphs")
            if key not in ALLOWED_SECTION_KEYS:
                raise SystemExit(f"Unknown section key {key!r} in {rel}")
            if key in section_keys:
                raise SystemExit(f"Duplicate section key {key!r} in {rel}")
            section_keys.add(key)
            if not heading or not isinstance(paragraphs, list) or not paragraphs:
                raise SystemExit(f"Incomplete section {key!r} in {rel}")
            if any(not isinstance(p, str) or len(p.strip()) < 25 for p in paragraphs):
                raise SystemExit(f"Thin/invalid paragraph in {rel} section {key!r}")
    return data


def source_links(source: dict[str, Any]) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    doi = str(source.get("doi") or "").strip()
    pmid = str(source.get("pmid") or "").strip()
    url = str(source.get("url") or "").strip()
    if doi:
        links.append((f"DOI: {doi}", "https://doi.org/" + quote(doi, safe="/()_-.:;")))
    if pmid:
        links.append((f"PMID: {pmid}", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"))
    if url and all(url != href for _, href in links):
        links.append(("المصدر الأصلي", url))
    return links


def render_record(record: dict[str, Any], batch: str) -> str:
    source = record["source"]
    parts = [
        f'\n<section class="rawafid-evidence-enrichment" data-rawafid-enrichment="{html.escape(batch, quote=True)}">',
        "  <header>",
        "    <p class=\"eyebrow\">استكمال منهجي موثّق</p>",
        "    <h2>قراءة علمية مكملة من المصدر الأصلي</h2>",
        "    <p>أضيف هذا القسم لتمييز تصميم الدليل وحدود التعميم وما يمكن وما لا يمكن استنتاجه، مع الحفاظ على النص المنشور سابقًا دون حذف أو اختصار.</p>",
        "  </header>",
    ]
    for section in record["sections"]:
        key = html.escape(str(section["key"]), quote=True)
        heading = html.escape(str(section["heading"]))
        parts.append(f'  <section class="rawafid-evidence-block" data-evidence-section="{key}">')
        parts.append(f"    <h3>{heading}</h3>")
        for paragraph in section["paragraphs"]:
            parts.append(f"    <p>{html.escape(str(paragraph).strip())}</p>")
        parts.append("  </section>")

    source_title = html.escape(str(source["title"]))
    source_type = html.escape(str(source.get("type") or "scientific_source"))
    parts.extend([
        '  <section class="rawafid-evidence-source" data-evidence-section="references">',
        "    <h3>المصدر الذي بُني عليه هذا الاستكمال</h3>",
        f"    <p><strong>{source_title}</strong></p>",
        f"    <p>نوع الدليل: {source_type}</p>",
        "    <ul>",
    ])
    for label, href in source_links(source):
        parts.append(
            f'      <li><a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer external">{html.escape(label)}</a></li>'
        )
    parts.extend([
        "    </ul>",
        "  </section>",
        "</section>\n",
    ])
    return "\n".join(parts)


def safe_insert(text: str, block: str, marker: str, rel_path: str) -> tuple[str, str]:
    if marker in text:
        return text, "already_applied"
    candidates = ["</article>", "</main>", "</body>"]
    for closing in candidates:
        idx = text.lower().rfind(closing)
        if idx >= 0:
            return text[:idx] + block + text[idx:], f"inserted_before:{closing}"
    raise SystemExit(f"No safe closing tag found for enrichment target: {rel_path}")


def apply_registry(magazine_dir: Path, registry: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    batch = str(registry["batch"])
    marker = f'data-rawafid-enrichment="{batch}"'
    results: list[dict[str, Any]] = []
    changed = 0
    for record in registry["records"]:
        rel_repo = Path(str(record["path"]))
        rel_magazine = Path(*rel_repo.parts[1:])
        target = magazine_dir / rel_magazine
        if not target.is_file():
            if strict:
                raise SystemExit(f"Enrichment target is missing: {target}")
            results.append({"path": str(rel_repo), "status": "missing", "sections": 0})
            continue
        original = target.read_text(encoding="utf-8", errors="strict")
        block = render_record(record, batch)
        updated, status = safe_insert(original, block, marker, str(rel_repo))
        if updated != original:
            target.write_text(updated, encoding="utf-8")
            changed += 1
        results.append(
            {
                "path": str(rel_repo),
                "status": status,
                "sections": len(record["sections"]),
                "source": record["source"].get("url"),
            }
        )
    return {
        "schema_version": 1,
        "batch": batch,
        "records": len(registry["records"]),
        "changed_pages": changed,
        "non_destructive": True,
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("magazine_dir", nargs="?", type=Path, default=ROOT / "magazine")
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--non-strict", action="store_true")
    args = ap.parse_args()
    registry = load_registry(args.registry)
    report = apply_registry(args.magazine_dir.resolve(), registry, strict=not args.non_strict)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
