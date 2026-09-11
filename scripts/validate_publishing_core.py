#!/usr/bin/env python3
"""Validate Rawafid Publishing Core without third-party dependencies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
PUBLISHER_FILE = BASE / "publisher.json"
THOTH_CONTRACT_FILE = BASE / "thoth-schema-contract.json"
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


def metadata_essential_blockers(book: dict[str, Any]) -> list[str]:
    """Derive the minimum OA-book metadata blockers from the record itself.

    This intentionally does not trust workflow labels. A record cannot become
    Thoth-ready merely because somebody changed metadata/files gates to passed.
    """
    blockers: list[str] = []
    title = book.get("title", {})
    if not str(title.get("primary") or "").strip():
        blockers.append("missing-title")

    contributors = book.get("contributors") or []
    if not contributors:
        blockers.append("missing-contributors")
    elif any(not str(item.get("name") or "").strip() or not item.get("roles") for item in contributors):
        blockers.append("incomplete-contributor")

    publication = book.get("publication", {})
    if not publication.get("publication_date"):
        blockers.append("missing-publication-date")
    formats = publication.get("formats") or []
    open_full_text = [
        item for item in formats
        if item.get("access_status") == "open" and str(item.get("access_url") or "").strip()
    ]
    if not open_full_text:
        blockers.append("missing-open-full-text-url")

    identifiers = book.get("identifiers") or {}
    has_pid = bool(str(identifiers.get("doi") or "").strip()) or any(
        str(item.get("isbn") or "").strip() for item in formats
    )
    if not has_pid:
        blockers.append("missing-persistent-identifier")

    subjects = book.get("subjects") or []
    if not subjects or any(not str(item.get("value") or "").strip() for item in subjects):
        blockers.append("missing-subject-metadata")

    text_license = book.get("rights", {}).get("text_license", {})
    if not str(text_license.get("name") or "").strip() or not str(text_license.get("url") or "").strip():
        blockers.append("missing-license-metadata")

    publisher = book.get("publisher", {})
    if publisher.get("name") != "Health Renewal / Rawafid" or publisher.get("url") != "https://healthrenewal.org/":
        blockers.append("invalid-publisher-metadata")

    return blockers


def validate_publisher(errors: list[str]) -> dict[str, Any]:
    if not PUBLISHER_FILE.is_file():
        fail(errors, "missing data/publishing/publisher.json")
        return {}
    publisher = load(PUBLISHER_FILE)
    p = publisher.get("publisher", {})
    if p.get("display_name") != "Health Renewal / Rawafid":
        fail(errors, "publisher display name must match the canonical local publisher identity")
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
        fail(errors, "2026-09-11 baseline must preserve the observed empty distribution-platform snapshot")
    if thoth.get("test_instance_available") is not False:
        fail(errors, "Thoth onboarding contract must record that no test instance is available")
    if thoth.get("metadata_visibility_on_creation") != "public":
        fail(errors, "Thoth metadata visibility must be treated as public from record creation")
    if thoth.get("record_deletion_requires_thoth_super_user") is not True:
        fail(errors, "Thoth deletion safeguard must record super-user intervention")
    if thoth.get("graphql_schema_observed") != "1.0.0":
        fail(errors, "observed Thoth GraphQL schema must remain pinned to 1.0.0 until re-verified")
    if thoth.get("api_mutation_policy") != "disabled-until-authenticated-mapping-verified":
        fail(errors, "Thoth API mutations must remain disabled until authenticated mapping is verified")
    required_capabilities = {"manual-metadata-entry", "bulk-upload-csv", "bulk-upload-onix-3.0"}
    if not required_capabilities.issubset(set(thoth.get("capabilities_observed_on_2026_09_11", []))):
        fail(errors, "Thoth onboarding capabilities snapshot is incomplete")
    return publisher


def validate_thoth_contract(errors: list[str]) -> dict[str, Any]:
    if not THOTH_CONTRACT_FILE.is_file():
        fail(errors, "missing data/publishing/thoth-schema-contract.json")
        return {}
    contract = load(THOTH_CONTRACT_FILE)
    thoth = contract.get("thoth", {})
    if contract.get("purpose") != "offline-dry-run-mapping-only":
        fail(errors, "Thoth schema contract must remain dry-run only")
    if thoth.get("graphql_schema_version") != "1.0.0":
        fail(errors, "Thoth schema contract must be pinned to verified GraphQL 1.0.0")
    if thoth.get("mutation_execution") != "disabled":
        fail(errors, "Thoth mutation execution must remain disabled in repository automation")
    secret_policy = str(thoth.get("authentication_secret_policy") or "").lower()
    if "never" not in secret_policy or "committed" not in secret_policy or "ci" not in secret_policy:
        fail(errors, "Thoth authentication secret policy must explicitly prohibit repository/CI storage")

    mappings = contract.get("safe_local_mappings", {})
    if mappings.get("work_type", {}).get("scholarly-monograph") != "MONOGRAPH":
        fail(errors, "verified scholarly-monograph -> MONOGRAPH mapping is missing")
    if mappings.get("work_type", {}).get("textbook") != "TEXTBOOK":
        fail(errors, "verified textbook -> TEXTBOOK mapping is missing")
    if set(mappings.get("work_type_forbidden_pending_thoth_confirmation", [])) != LITERARY_TYPES:
        fail(errors, "literary work types must remain forbidden pending Thoth confirmation")
    if mappings.get("language", {}).get("ar") != "ARA" or mappings.get("language", {}).get("en") != "ENG":
        fail(errors, "verified Arabic/English language mappings are incomplete")
    return contract


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
        essential_blockers = metadata_essential_blockers(book)

        if gates.get("metadata") == "passed" and essential_blockers:
            fail(errors, f"{path}: metadata gate marked passed with blockers: {', '.join(essential_blockers)}")
        if gates.get("accessibility") == "passed" and book.get("accessibility", {}).get("status") not in {"validated", "known-limitations"}:
            fail(errors, f"{path}: accessibility gate passed without an assessed accessibility status")
        if gates.get("rights") == "passed" and (not rights or rights.get("status") != "cleared"):
            fail(errors, f"{path}: rights gate passed without a cleared rights record")
        if workflow.get("current_state") in THOTH_PUBLIC_STATES and essential_blockers:
            fail(errors, f"{path}: Thoth-ready workflow state has metadata blockers: {', '.join(essential_blockers)}")

        if thoth.get("upload_allowed") is True:
            if book.get("work_type") in LITERARY_TYPES:
                fail(errors, f"{path}: literary work cannot be marked upload_allowed before Thoth confirms scope")
            if workflow.get("current_state") not in THOTH_PUBLIC_STATES:
                fail(errors, f"{path}: Thoth upload allowed before workflow reached ready-for-thoth")
            for gate in ("rights", "editorial", "accessibility", "metadata", "files"):
                if gates.get(gate) != "passed":
                    fail(errors, f"{path}: Thoth upload allowed while {gate} gate is not passed")
            if book.get("review", {}).get("status") != "completed":
                fail(errors, f"{path}: Thoth upload allowed before editorial/scientific review is completed")
            if book.get("review", {}).get("model") == "scholarly-peer-review" and gates.get("scientific") != "passed":
                fail(errors, f"{path}: scholarly peer-reviewed work requires scientific gate passed")
            if not rights or rights.get("status") != "cleared":
                fail(errors, f"{path}: Thoth upload allowed without a cleared rights record")
            if thoth.get("eligibility") != "eligible":
                fail(errors, f"{path}: upload_allowed requires thoth.eligibility=eligible")
            if essential_blockers:
                fail(errors, f"{path}: Thoth upload allowed with metadata blockers: {', '.join(essential_blockers)}")

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
    validate_thoth_contract(errors)
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
