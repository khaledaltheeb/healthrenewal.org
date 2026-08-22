#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

VERSION = 413
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "RawafidEvidenceAgent/413 (+https://healthrenewal.org/)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def ncbi_params(extra: dict[str, str]) -> dict[str, str]:
    params = dict(extra)
    params["tool"] = "rawafid_evidence_agent"
    email = os.getenv("RESEARCH_CONTACT_EMAIL", "").strip()
    key = os.getenv("NCBI_API_KEY", "").strip()
    if email:
        params["email"] = email
    if key:
        params["api_key"] = key
    return params


def bookshelf_search(query: str, limit: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        params = ncbi_params({"db": "books", "term": query, "retmode": "json", "retmax": str(limit), "sort": "relevance"})
        search = get_json(EUTILS + "esearch.fcgi?" + urllib.parse.urlencode(params))
        ids = list(search.get("esearchresult", {}).get("idlist", []))
        if not ids:
            return [], None
        time.sleep(0.12 if os.getenv("NCBI_API_KEY") else 0.36)
        summary_params = ncbi_params({"db": "books", "id": ",".join(ids), "retmode": "json"})
        summary = get_json(EUTILS + "esummary.fcgi?" + urllib.parse.urlencode(summary_params))
        result = summary.get("result", {})
        records: list[dict[str, Any]] = []
        for uid in result.get("uids", ids):
            item = result.get(str(uid), {})
            title = item.get("title") or item.get("booktitle") or ""
            records.append({
                "book_id": str(uid),
                "title": title,
                "authors": item.get("authors", []),
                "pubdate": item.get("pubdate", ""),
                "url": f"https://www.ncbi.nlm.nih.gov/books/{uid}/",
                "provider": "NCBI Bookshelf",
                "verification_status": "candidate-only",
            })
        return records[:limit], None
    except Exception as exc:
        return [], str(exc)[:400]


def verification_checklist() -> list[str]:
    return [
        "Confirm the source actually addresses the page's user intent and the exact claim under review.",
        "Confirm population, age group, diagnosis/context and setting match the page claim.",
        "Identify whether the item is a guideline, systematic review, textbook chapter, evidence synthesis or narrative reference.",
        "Check publication/update date and whether a newer authoritative guideline supersedes it.",
        "Record material limitations, uncertainty, contraindications and scope boundaries.",
        "Cross-check clinical recommendations against current WHO/NICE/CDC/NIH or relevant specialty guidance where applicable.",
        "For Arabic-facing guidance, assess cultural/contextual applicability rather than assuming direct transferability.",
        "Do not convert candidate evidence into a medical recommendation automatically; require claim-level editorial/specialist verification for high-risk content.",
    ]


def build(dossiers: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for dossier in dossiers:
        query = str(dossier.get("query") or "").strip()
        if not query:
            continue
        books, error = bookshelf_search(query, limit)
        items.append({
            "path": dossier.get("path"),
            "query": query,
            "bookshelf": books,
            "error": error,
            "verification_checklist": verification_checklist(),
            "policy": "NCBI Bookshelf results are candidate reference material, not automatic proof for a claim.",
        })
    return {
        "version": VERSION,
        "status": "passed",
        "provider": "NCBI Bookshelf via NCBI E-utilities",
        "summary": {
            "dossiers": len(items),
            "candidate_books": sum(len(x["bookshelf"]) for x in items),
            "provider_errors": sum(bool(x["error"]) for x in items),
        },
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dossiers", type=Path)
    parser.add_argument("--per-query", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("artifacts/site-quality-agent-v410/bookshelf-evidence-v413.json"))
    args = parser.parse_args()
    dossiers = json.loads(args.dossiers.read_text(encoding="utf-8"))
    result = build(dossiers, max(1, min(args.per_query, 20)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
