#!/usr/bin/env python3
"""Build the public Rawafid open-books API and catalog from approved book records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
BOOKS_DIR = BASE / "books"
CATALOG_FILE = BASE / "catalog.json"
API_FILE = ROOT / "api" / "v1" / "open-books.json"

PUBLIC_STATES = {
    "ready-for-thoth",
    "thoth-published",
    "thoth-verified",
    "distributed",
    "corrected",
    "new-edition",
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def public_books() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not BOOKS_DIR.is_dir():
        return records
    for path in sorted(BOOKS_DIR.glob("*.json")):
        book = load(path)
        if not book.get("public_visibility"):
            continue
        if book.get("record_type") == "discovery-only":
            continue
        if book.get("workflow", {}).get("current_state") not in PUBLIC_STATES:
            continue
        records.append(book)
    return records


def public_projection(book: dict[str, Any]) -> dict[str, Any]:
    rights = book.get("rights", {})
    return {
        "id": book["id"],
        "slug": book["slug"],
        "canonical": f"https://healthrenewal.org/open-books/{book['slug']}/",
        "record_type": book["record_type"],
        "work_type": book["work_type"],
        "title": book["title"],
        "language": book["language"],
        "original_language": book.get("original_language"),
        "abstract": book.get("abstract"),
        "publisher": book["publisher"],
        "contributors": book["contributors"],
        "publication": book["publication"],
        "identifiers": book.get("identifiers", {}),
        "subjects": book["subjects"],
        "rights": {
            "copyright_holder": rights.get("copyright_holder"),
            "text_license": rights.get("text_license"),
            "cover_rights_status": rights.get("cover_rights_status"),
        },
        "review": book["review"],
        "accessibility": book["accessibility"],
        "relationships": book.get("relationships", {}),
        "thoth": {
            "work_id": book.get("thoth", {}).get("work_id"),
            "last_verified_at": book.get("thoth", {}).get("last_verified_at"),
        },
        "updated_at": book["provenance"]["updated_at"],
    }


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    books = public_books()
    projected = [public_projection(book) for book in books]
    latest = max([book["provenance"]["updated_at"] for book in books] + ["2026-09-11"])
    catalog = {
        "schema_version": "1.0.0",
        "publisher_id": "rawafid",
        "publisher_name": "Health Renewal / Rawafid",
        "canonical": "https://healthrenewal.org/open-books/",
        "updated_at": latest,
        "public_records": [book["id"] for book in books],
        "counts": {
            "public_books": len(books),
            "rawafid_originals": sum(book["record_type"] == "rawafid-original" for book in books),
            "licensed_translations": sum(book["record_type"] == "licensed-translation" for book in books),
            "authorized_co_managed": sum(book["record_type"] == "authorized-co-managed" for book in books),
        },
        "publication_rule": "Only records with public_visibility=true and a public workflow state may appear in this catalog.",
        "discovery_boundary": "Third-party discovery-only records are not Rawafid publications and must not be counted as Rawafid books.",
    }
    api = {
        "version": 1,
        "generated_at": latest,
        "publisher": {
            "name": "Health Renewal / Rawafid",
            "short_name": "Rawafid",
            "url": "https://healthrenewal.org/",
        },
        "catalog_url": "https://healthrenewal.org/open-books/",
        "books": projected,
    }
    return catalog, api


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if committed generated files are stale.")
    args = parser.parse_args()
    catalog, api = build()
    expected = {CATALOG_FILE: dump(catalog), API_FILE: dump(api)}
    stale: list[str] = []
    for path, content in expected.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    if args.check and stale:
        print("Generated publishing files are stale:")
        for item in stale:
            print(f"- {item}")
        return 1
    print("Publishing catalog is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
