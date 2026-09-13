#!/usr/bin/env python3
"""Verify magazine scientific identifiers against authoritative registries.

This command is deliberately read-only with respect to published HTML. It uses
Crossref/DataCite for DOI metadata and NCBI E-utilities for PMID metadata, then
writes a verification report that can drive title-by-title remediation.

A DOI/PMID being syntactically present is NOT treated as bibliographically
verified until an authoritative registry returns a matching record.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts" / "audit_magazine_sources_v202.py"
DEFAULT_OUTPUT = ROOT / "data" / "magazine-bibliography-verification.json"
USER_AGENT = "RawafidMagazineAudit/2026 (+https://healthrenewal.org/; mailto:contact@healthrenewal.org)"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("rawafid_magazine_source_audit", AUDIT_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to import {AUDIT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def request_json(url: str, *, timeout: float = 15.0, retries: int = 2) -> tuple[int, dict[str, Any] | list[Any] | None]:
    last_status = 0
    for attempt in range(retries + 1):
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=timeout) as response:
                last_status = int(getattr(response, "status", 200))
                raw = response.read().decode("utf-8", errors="replace")
                return last_status, json.loads(raw)
        except HTTPError as exc:
            last_status = exc.code
            if exc.code in {404, 400}:
                return last_status, None
            if exc.code == 429 or 500 <= exc.code < 600:
                time.sleep(0.6 * (attempt + 1))
                continue
            return last_status, None
        except (URLError, TimeoutError, json.JSONDecodeError):
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            return last_status, None
    return last_status, None


def first_text(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
    return None


def date_parts_to_iso(parts: Any) -> str | None:
    try:
        values = parts[0]
        if not values:
            return None
        year = int(values[0])
        month = int(values[1]) if len(values) > 1 else 1
        day = int(values[2]) if len(values) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (TypeError, ValueError, IndexError):
        return None


@dataclass
class DOIRecord:
    doi: str
    status: str
    registry: str | None = None
    title: str | None = None
    publisher: str | None = None
    container_title: str | None = None
    published: str | None = None
    canonical_url: str | None = None
    http_status: int | None = None
    error: str | None = None


def verify_doi_crossref(doi: str) -> DOIRecord | None:
    url = "https://api.crossref.org/works/" + quote(doi, safe="")
    status, payload = request_json(url)
    if status != 200 or not isinstance(payload, dict):
        return None
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    returned = str(message.get("DOI") or doi).lower()
    if returned != doi.lower():
        return None
    published = None
    for key in ("published-print", "published-online", "published", "issued", "created"):
        value = message.get(key)
        if isinstance(value, dict):
            published = date_parts_to_iso(value.get("date-parts"))
            if published:
                break
    return DOIRecord(
        doi=doi,
        status="verified",
        registry="crossref",
        title=first_text(message.get("title")),
        publisher=first_text(message.get("publisher")),
        container_title=first_text(message.get("container-title")),
        published=published,
        canonical_url=first_text(message.get("URL")) or f"https://doi.org/{doi}",
        http_status=status,
    )


def verify_doi_datacite(doi: str) -> DOIRecord | None:
    url = "https://api.datacite.org/dois/" + quote(doi, safe="")
    status, payload = request_json(url)
    if status != 200 or not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    attrs = data.get("attributes")
    if not isinstance(attrs, dict):
        return None
    returned = str(attrs.get("doi") or data.get("id") or doi).lower()
    if returned != doi.lower():
        return None
    titles = attrs.get("titles")
    title = None
    if isinstance(titles, list):
        for item in titles:
            if isinstance(item, dict) and item.get("title"):
                title = str(item["title"]).strip()
                break
    publisher = attrs.get("publisher")
    if isinstance(publisher, dict):
        publisher = publisher.get("name")
    published = first_text(attrs.get("published") or attrs.get("publicationYear"))
    if published and len(published) == 4 and published.isdigit():
        published += "-01-01"
    return DOIRecord(
        doi=doi,
        status="verified",
        registry="datacite",
        title=title,
        publisher=first_text(publisher),
        container_title=first_text(attrs.get("container")),
        published=published,
        canonical_url=first_text(attrs.get("url")) or f"https://doi.org/{doi}",
        http_status=status,
    )


def doi_resolves(doi: str, *, timeout: float = 15.0) -> tuple[bool, int | None, str | None]:
    req = Request(
        f"https://doi.org/{quote(doi, safe='/')}",
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        method="HEAD",
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            return 200 <= status < 400, status, response.geturl()
    except HTTPError as exc:
        # Some publishers reject HEAD even though the DOI is valid. Retry GET.
        if exc.code not in {403, 405}:
            return False, exc.code, None
    except (URLError, TimeoutError):
        return False, None, None

    req = Request(
        f"https://doi.org/{quote(doi, safe='/')}",
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            response.read(1024)
            return 200 <= status < 400, status, response.geturl()
    except HTTPError as exc:
        return False, exc.code, None
    except (URLError, TimeoutError):
        return False, None, None


def verify_doi(doi: str) -> DOIRecord:
    record = verify_doi_crossref(doi)
    if record:
        return record
    record = verify_doi_datacite(doi)
    if record:
        return record
    resolves, status, target = doi_resolves(doi)
    if resolves:
        return DOIRecord(
            doi=doi,
            status="resolvable_only",
            registry="doi_resolver",
            canonical_url=target or f"https://doi.org/{doi}",
            http_status=status,
            error="DOI resolves but no Crossref/DataCite metadata was obtained",
        )
    return DOIRecord(
        doi=doi,
        status="unverified",
        http_status=status,
        error="No authoritative DOI metadata record and DOI resolver did not confirm resolution",
    )


@dataclass
class PMIDRecord:
    pmid: str
    status: str
    title: str | None = None
    source: str | None = None
    pubdate: str | None = None
    doi: str | None = None
    canonical_url: str | None = None
    error: str | None = None


def verify_pmids(pmids: list[str], batch_size: int = 100) -> dict[str, PMIDRecord]:
    unique_pmids = list(dict.fromkeys(pmids))
    out: dict[str, PMIDRecord] = {}
    for start in range(0, len(unique_pmids), batch_size):
        batch = unique_pmids[start : start + batch_size]
        query = urlencode({"db": "pubmed", "id": ",".join(batch), "retmode": "json", "tool": "rawafid", "email": "contact@healthrenewal.org"})
        status, payload = request_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + query, timeout=20.0)
        if status != 200 or not isinstance(payload, dict):
            for pmid in batch:
                out[pmid] = PMIDRecord(pmid=pmid, status="unverified", error=f"NCBI ESummary HTTP {status or 'error'}")
            continue
        result = payload.get("result")
        if not isinstance(result, dict):
            for pmid in batch:
                out[pmid] = PMIDRecord(pmid=pmid, status="unverified", error="NCBI ESummary returned no result object")
            continue
        for pmid in batch:
            item = result.get(pmid)
            if not isinstance(item, dict):
                out[pmid] = PMIDRecord(pmid=pmid, status="unverified", error="PMID absent from NCBI response")
                continue
            doi = None
            for article_id in item.get("articleids") or []:
                if isinstance(article_id, dict) and str(article_id.get("idtype", "")).lower() == "doi":
                    doi = first_text(article_id.get("value"))
                    break
            out[pmid] = PMIDRecord(
                pmid=pmid,
                status="verified",
                title=first_text(item.get("title")),
                source=first_text(item.get("fulljournalname")) or first_text(item.get("source")),
                pubdate=first_text(item.get("pubdate")),
                doi=doi.lower() if doi else None,
                canonical_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            )
    return out


def verify_all(dois: list[str], pmids: list[str], workers: int) -> tuple[dict[str, DOIRecord], dict[str, PMIDRecord]]:
    doi_records: dict[str, DOIRecord] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(verify_doi, doi): doi for doi in dois}
        for future in as_completed(futures):
            doi = futures[future]
            try:
                doi_records[doi] = future.result()
            except Exception as exc:  # defensive: report rather than abort all pages
                doi_records[doi] = DOIRecord(doi=doi, status="unverified", error=f"{type(exc).__name__}: {exc}")
    pmid_records = verify_pmids(pmids)
    return doi_records, pmid_records


def page_verification(page: dict[str, Any], doi_records: dict[str, DOIRecord], pmid_records: dict[str, PMIDRecord]) -> dict[str, Any]:
    page_dois = [str(x).lower() for x in page.get("doi") or []]
    page_pmids = [str(x) for x in page.get("pmid") or []]
    doi_data = [asdict(doi_records[d]) for d in page_dois if d in doi_records]
    pmid_data = [asdict(pmid_records[p]) for p in page_pmids if p in pmid_records]

    verified_dois = [r for r in doi_data if r["status"] == "verified"]
    verified_pmids = [r for r in pmid_data if r["status"] == "verified"]
    resolvable_dois = [r for r in doi_data if r["status"] == "resolvable_only"]

    if verified_dois or verified_pmids:
        status = "verified_identifier"
    elif resolvable_dois:
        status = "resolvable_identifier_manual_metadata_review"
    elif page.get("source_urls"):
        status = "source_url_manual_review"
    else:
        status = "missing_or_unverified_source"

    primary = None
    if verified_dois:
        primary = {"kind": "doi", **verified_dois[0]}
    elif verified_pmids:
        primary = {"kind": "pmid", **verified_pmids[0]}
    elif resolvable_dois:
        primary = {"kind": "doi", **resolvable_dois[0]}

    return {
        "path": page.get("path"),
        "url": page.get("url"),
        "rawafid_title": page.get("title"),
        "page_contract": page.get("page_contract"),
        "source_contract": page.get("source_contract"),
        "bibliographic_verification": status,
        "primary_source": primary,
        "doi_records": doi_data,
        "pmid_records": pmid_data,
        "source_urls": page.get("source_urls") or [],
        "issues": page.get("issues") or [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--strict", action="store_true", help="Fail if any study page lacks a verified bibliographic identifier")
    args = ap.parse_args()

    audit = load_audit_module()
    manifest = audit.build_manifest()
    pages = manifest.get("pages") or []
    dois = list(dict.fromkeys(d.lower() for p in pages for d in (p.get("doi") or [])))
    pmids = list(dict.fromkeys(str(x) for p in pages for x in (p.get("pmid") or [])))

    doi_records, pmid_records = verify_all(dois, pmids, args.workers)
    verified_pages = [page_verification(p, doi_records, pmid_records) for p in pages]

    counts: dict[str, int] = {}
    for page in verified_pages:
        key = page["bibliographic_verification"]
        counts[key] = counts.get(key, 0) + 1

    report = {
        "schema_version": 2,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authority": {
            "doi": ["Crossref", "DataCite", "doi.org resolver fallback"],
            "pmid": ["NCBI PubMed ESummary"],
        },
        "summary": {
            "study_pages": len(verified_pages),
            "unique_dois": len(dois),
            "unique_pmids": len(pmids),
            "doi_verified": sum(r.status == "verified" for r in doi_records.values()),
            "doi_resolvable_only": sum(r.status == "resolvable_only" for r in doi_records.values()),
            "doi_unverified": sum(r.status == "unverified" for r in doi_records.values()),
            "pmid_verified": sum(r.status == "verified" for r in pmid_records.values()),
            "pmid_unverified": sum(r.status == "unverified" for r in pmid_records.values()),
            "page_status_counts": counts,
        },
        "pages": verified_pages,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")

    gaps = sum(v for k, v in counts.items() if k != "verified_identifier")
    return 2 if args.strict and gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
