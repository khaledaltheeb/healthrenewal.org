#!/usr/bin/env python3
"""Validate Rawafid Publishing Core without third-party dependencies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
PUBLISHER_FILE = BASE / "publisher.json"
CATALOG_FILE = BASE / "catalog.json"
API_FILE = ROOT / "api" / "v1" / "open-books.json"
BOOKS_DIR = BASE / "books"
RIGHTS_DIR = BASE / "rights"
TRANSLATIONS_DIR = BASE / "translations"

THOTH_PUBLIC_STATES = {
    "ready-for-thoth", "thoth-published", "thoth-verified", "distributed",
    "corrected", "new-edition",
}
PUBLIC_WORKFLOW_STATES = {
    "thoth-published", "thoth-verified", "distributed", "corrected", "new-edition",
}
LITERARY_TYPES = {"literary-fiction", "literary-nonfiction"}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def json_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.json")) if path.is_dir() else []


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_publisher(errors: list[str]) -> dict[str, Any]:
    if not PUBLISHER_FILE.is_file():
        fail(errors, "missing data/publishing/publisher.json")
        return {}
    publisher = load(PUBLISHER_FILE)
    p = publisher.get("publisher", {})
    if p.get("display_name") != "Health Renewal / Rawafid":
        fail(errors, "publisher display name must match the activated Thoth publisher")
    if p.get("short_name") != "Rawafid":
        fail(errors, "publisher short name must be Rawafid")
    thoth = publisher.get("thoth", {})
    if set(thoth.get("metadata_management_scope", [])) != {"professional", "scholarly"}:
        fail(errors, "Thoth scope must remain explicitly professional + scholarly")
    if thoth.get("literary_work_policy") != "hold_for_thoth_confirmation":
        fail(errors, "literary works must remain held from Thoth pending confirmation")
    if thoth.get("metadata_public_dedication") != "CC0-1.0":
        fail(errors, "Thoth metadata dedication must be recorded as CC0-1.0")
    if thoth.get("distribution_platforms_observed_on_2026_09_11") != []:
        fail(errors, "baseline must record no distribution platform enabled on 2026-09-11")
    return publisher


def validate_rights(errors: list[str]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in json_files(RIGHTS_DIR):
        record = load(path)
        rid = record.get("id")
        if not rid:
            fail(errors, f"{path}: missing rights id")
            continue
        if rid in records:
            fail(errors, f"duplicate rights id: {rid}")
        records[rid] = record
        if record.get("status") == "cleared":
            for field in ("metadata_rights", "full_text_rights", "distribution_rights"):
                if record.get(field) != "cleared":
                    fail(errors, f"{path}: cleared rights record has {field}={record.get(field)!r}")
            if record.get("thoth_metadata_cc0_acknowledged") is not True:
                fail(errors, f"{path}: Thoth CC0 acknowledgement is required before clearance")
    return records


def validate_translations(errors: list[str]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in json_files(TRANSLATIONS_DIR):
        record = load(path)
        rid = record.get("id")
        if not rid:
            fail(errors, f"{path}: missing translation id")
            continue
        if rid in records:
            fail(errors, f"duplicate translation id: {rid}")
        records[rid] = record
        if record.get("workflow", {}).get("status") in {"authorized", "translation", "review", "metadata", "ready-to-publish", "published"}:
            if record.get("rights", {}).get("translation_allowed") is not True:
                fail(errors, f"{path}: active translation workflow lacks verified translation permission")
    return records


def validate_books(errors: list[str], rights_records: dict[str, dict[str, Any]], translation_records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()

    for path in json_files(BOOKS_DIR):
        book = load(path)
        books.append(book)
        bid = book.get("id")
        slug = book.get("slug")
        if not bid or bid in seen_ids:
            fail(errors, f"{path}: missing or duplicate book id {bid!r}")
        if not slug or slug in seen_slugs:
            fail(errors, f"{path}: missing or duplicate slug {slug!r}")
        if bid:
            seen_ids.add(bid)
        if slug:
            seen_slugs.add(slug)

        required = {
            "schema_version", "id", "slug", "record_type", "work_type", "title",
            "language", "publisher", "contributors", "publication", "subjects",
            "rights", "review", "accessibility", "workflow", "thoth",
            "provenance", "public_visibility",
        }
        missing = sorted(required - set(book))
        if missing:
            fail(errors, f"{path}: missing required top-level keys: {', '.join(missing)}")
            continue

        publisher = book.get("publisher", {})
        if publisher.get("name") != "Health Renewal / Rawafid":
            fail(errors, f"{path}: Rawafid publication record must use the canonical publisher display name")
        if publisher.get("url") != "https://healthrenewal.org/":
            fail(errors, f"{path}: publisher URL must be canonical HTTPS URL")

        rid = book.get("rights", {}).get("rights_record_id")
        rights = rights_records.get(rid)
        if not rights:
            fail(errors, f"{path}: missing referenced rights record {rid!r}")
        elif rights.get("book_id") != bid:
            fail(errors, f"{path}: rights record {rid!r} belongs to another book")

        if book.get("record_type") == "discovery-only" and book.get("thoth", {}).get("upload_allowed"):
            fail(errors, f"{path}: discovery-only records can never be uploaded as Rawafid publisher metadata")

        translation_id = book.get("rights", {}).get("translation_record_id")
        if book.get("record_type") == "licensed-translation":
            if not translation_id or translation_id not in translation_records:
                fail(errors, f"{path}: licensed translation must reference a translation record")
            if rights and rights.get("translation_rights") != "cleared":
                fail(errors, f"{path}: licensed translation lacks cleared translation rights")

        thoth = book.get("thoth", {})
        workflow = book.get("workflow", {})
        gates = workflow.get("gates", {})
        if thoth.get("upload_allowed") is True:
            if book.get("work_type") in LITERARY_TYPES:
                fail(errors, f"{path}: literary work cannot be marked upload_allowed before Thoth confirms scope")
            if workflow.get("current_state") not in THOTH_PUBLIC_STATES:
                fail(errors, f"{path}: Thoth upload allowed before workflow reached ready-for-thoth")
            for gate in ("rights", "editorial", "accessibility", "metadata", "files"):
                if gates.get(gate) != "passed":
                    fail(errors, f"{path}: Thoth upload allowed while {gate} gate is not passed")
            if book.get("review", {}).get("model") == "scholarly-peer-review" and gates.get("scientific") != "passed":
                fail(errors, f"{path}: scholarly peer-reviewed work requires scientific gate passed")
            if not rights or rights.get("status") != "cleared":
                fail(errors, f"{path}: Thoth upload allowed without a cleared rights record")
            if thoth.get("eligibility") != "eligible":
                fail(errors, f"{path}: upload_allowed requires thoth.eligibility=eligible")

        if book.get("public_visibility") is True:
            if book.get("publication", {}).get("status") not in {"forthcoming", "published"}:
                fail(errors, f"{path}: public book has invalid publication status")
            if workflow.get("current_state") not in PUBLIC_WORKFLOW_STATES | {"ready-for-thoth"}:
                fail(errors, f"{path}: public_visibility set before publication-ready workflow state")

    return books


def expected_public_ids(books: list[dict[str, Any]]) -> list[str]:
    return sorted(
        b["id"] for b in books
        if b.get("public_visibility") is True
        and b.get("record_type") != "discovery-only"
        and b.get("workflow", {}).get("current_state") in PUBLIC_WORKFLOW_STATES | {"ready-for-thoth"}
    )


def validate_catalog_and_api(errors: list[str], books: list[dict[str, Any]]) -> None:
    if not CATALOG_FILE.is_file():
        fail(errors, "missing data/publishing/catalog.json")
        return
    if not API_FILE.is_file():
        fail(errors, "missing api/v1/open-books.json")
        return

    catalog = load(CATALOG_FILE)
    api = load(API_FILE)
    expected_ids = expected_public_ids(books)
    catalog_ids = sorted(catalog.get("public_records", []))
    api_ids = sorted(item.get("id") for item in api.get("books", []) if item.get("id"))

    if catalog_ids != expected_ids:
        fail(errors, f"catalog public_records drift: expected {expected_ids}, got {catalog_ids}")
    if api_ids != expected_ids:
        fail(errors, f"public API drift: expected {expected_ids}, got {api_ids}")

    counts = catalog.get("counts", {})
    public_books = [b for b in books if b.get("id") in expected_ids]
    expected_counts = {
        "public_books": len(public_books),
        "rawafid_originals": sum(b.get("record_type") == "rawafid-original" for b in public_books),
        "licensed_translations": sum(b.get("record_type") == "licensed-translation" for b in public_books),
        "authorized_co_managed": sum(b.get("record_type") == "authorized-co-managed" for b in public_books),
    }
    if counts != expected_counts:
        fail(errors, f"catalog counts drift: expected {expected_counts}, got {counts}")


def main() -> int:
    errors: list[str] = []
    validate_publisher(errors)
    rights_records = validate_rights(errors)
    translation_records = validate_translations(errors)
    books = validate_books(errors, rights_records, translation_records)
    validate_catalog_and_api(errors, books)

    if errors:
        print("Rawafid Publishing Core validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Rawafid Publishing Core validation PASSED "
        f"({len(books)} book records, {len(rights_records)} rights records, "
        f"{len(translation_records)} translation records)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
