#!/usr/bin/env python3
"""Build internal Thoth-candidate and translation-queue staging files.

These files are internal readiness projections only. They are deliberately not
serialized as Thoth API payloads, because external field mapping must be verified
against the live Thoth schema before transmission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
BOOKS_DIR = BASE / "books"
RIGHTS_DIR = BASE / "rights"
TRANSLATIONS_DIR = BASE / "translations"
THOTH_STAGE = BASE / "thoth-staging.json"
TRANSLATION_QUEUE = BASE / "translation-queue.json"

THOTH_STATES = {
    "ready-for-thoth",
    "thoth-published",
    "thoth-verified",
    "distributed",
    "corrected",
    "new-edition",
}
LITERARY_TYPES = {"literary-fiction", "literary-nonfiction"}
ACTIVE_TRANSLATION_STATES = {
    "candidate",
    "rights-review",
    "authorized",
    "translation",
    "review",
    "metadata",
    "ready-to-publish",
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def records(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []
    return [load(path) for path in sorted(directory.glob("*.json"))]


def rights_index() -> dict[str, dict[str, Any]]:
    return {record.get("id", ""): record for record in records(RIGHTS_DIR) if record.get("id")}


def translation_index() -> dict[str, dict[str, Any]]:
    return {record.get("id", ""): record for record in records(TRANSLATIONS_DIR) if record.get("id")}


def required_gates_passed(book: dict[str, Any]) -> bool:
    gates = book.get("workflow", {}).get("gates", {})
    for name in ("rights", "editorial", "accessibility", "metadata", "files"):
        if gates.get(name) != "passed":
            return False
    if book.get("review", {}).get("model") == "scholarly-peer-review":
        return gates.get("scientific") == "passed"
    return True


def translation_ready(record: dict[str, Any]) -> bool:
    if record.get("rights", {}).get("translation_allowed") is not True:
        return False
    review = record.get("review", {})
    for name in ("terminology", "language", "rights", "accessibility"):
        if review.get(name) != "passed":
            return False
    if review.get("subject") not in {"passed", "not-applicable"}:
        return False
    return record.get("workflow", {}).get("status") in {"ready-to-publish", "published"}


def thoth_candidate(book: dict[str, Any], rights: dict[str, dict[str, Any]], translations: dict[str, dict[str, Any]]) -> bool:
    if book.get("record_type") == "discovery-only":
        return False
    if book.get("work_type") in LITERARY_TYPES:
        return False
    if book.get("thoth", {}).get("upload_allowed") is not True:
        return False
    if book.get("thoth", {}).get("eligibility") != "eligible":
        return False
    if book.get("workflow", {}).get("current_state") not in THOTH_STATES:
        return False
    if not required_gates_passed(book):
        return False
    rights_id = book.get("rights", {}).get("rights_record_id")
    rights_record = rights.get(rights_id)
    if not rights_record or rights_record.get("status") != "cleared":
        return False
    if rights_record.get("metadata_rights") != "cleared":
        return False
    if rights_record.get("thoth_metadata_cc0_acknowledged") is not True:
        return False
    if book.get("record_type") == "licensed-translation":
        translation_id = book.get("rights", {}).get("translation_record_id")
        translation = translations.get(translation_id)
        if not translation or not translation_ready(translation):
            return False
    return True


def thoth_projection(book: dict[str, Any]) -> dict[str, Any]:
    return {
        "book_id": book["id"],
        "slug": book["slug"],
        "record_type": book["record_type"],
        "work_type": book["work_type"],
        "title": book["title"],
        "language": book["language"],
        "original_language": book.get("original_language"),
        "contributors": book["contributors"],
        "publication": book["publication"],
        "identifiers": book.get("identifiers", {}),
        "subjects": book["subjects"],
        "rights_record_id": book["rights"]["rights_record_id"],
        "review": book["review"],
        "accessibility": book["accessibility"],
        "relationships": book.get("relationships", {}),
        "workflow_state": book["workflow"]["current_state"],
        "local_canonical": f"https://healthrenewal.org/open-books/{book['slug']}/",
    }


def translation_blockers(record: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if record.get("rights", {}).get("translation_allowed") is not True:
        blockers.append("translation-rights-not-cleared")
    review = record.get("review", {})
    for name in ("terminology", "language", "rights", "accessibility"):
        if review.get(name) != "passed":
            blockers.append(f"{name}-review-not-passed")
    if review.get("subject") not in {"passed", "not-applicable"}:
        blockers.append("subject-review-not-passed")
    return blockers


def translation_projection(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "translation_id": record["id"],
        "source_work": record["source_work"],
        "target": record["target"],
        "contributors": record["contributors"],
        "workflow": record["workflow"],
        "ready_for_publication": translation_ready(record),
        "blocked_reasons": translation_blockers(record),
    }


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    rights = rights_index()
    translations = translation_index()
    books = records(BOOKS_DIR)

    candidates = [thoth_projection(book) for book in books if thoth_candidate(book, rights, translations)]
    active_translations = [
        translation_projection(record)
        for record in translations.values()
        if record.get("workflow", {}).get("status") in ACTIVE_TRANSLATION_STATES
    ]
    candidates.sort(key=lambda item: item["book_id"])
    active_translations.sort(key=lambda item: item["translation_id"])

    thoth = {
        "schema_version": "1.0.0",
        "publisher": "Health Renewal / Rawafid",
        "purpose": "internal-readiness-staging",
        "external_payload_status": "not-a-thoth-api-payload",
        "mapping_rule": "Verify the current live Thoth schema before transforming or transmitting any candidate.",
        "literary_policy": "hold-for-thoth-confirmation",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    queue = {
        "schema_version": "1.0.0",
        "publisher": "Health Renewal / Rawafid",
        "purpose": "authorized-arabic-translation-workflow",
        "record_count": len(active_translations),
        "records": active_translations,
    }
    return thoth, queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if committed staging files are stale.")
    args = parser.parse_args()

    thoth, queue = build()
    expected = {THOTH_STAGE: dump(thoth), TRANSLATION_QUEUE: dump(queue)}
    stale: list[str] = []
    for path, content in expected.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

    if args.check and stale:
        print("Generated publishing staging files are stale:")
        for item in stale:
            print(f"- {item}")
        return 1

    print(f"Publishing staging is current: {len(thoth['candidates'])} Thoth candidates, {len(queue['records'])} active translations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
