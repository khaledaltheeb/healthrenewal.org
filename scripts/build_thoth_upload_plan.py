#!/usr/bin/env python3
"""Build a deterministic, non-executable Thoth upload plan.

The plan is deliberately offline. It never performs network requests, never
loads authentication material, and never creates a real Thoth record. Its only
purpose is to make field mapping and blockers reviewable before a human uses the
current Thoth bulk-uploader template or an explicitly approved authenticated
integration.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import build_publishing_staging as staging

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
CONTRACT_FILE = BASE / "thoth-schema-contract.json"
PUBLISHER_FILE = BASE / "publisher.json"
OUTPUT_FILE = BASE / "thoth-upload-plan.json"
BOOKS_DIR = BASE / "books"

DOI_RE = re.compile(
    r"^(?:(?:https?://)?(?:www\.)?(?:dx\.)?doi\.org/)?"
    r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9<>+\[\]]+)$",
    re.IGNORECASE,
)
ORCID_RE = re.compile(r"^https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def normalize_doi(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    match = DOI_RE.fullmatch(raw)
    if not match:
        return None
    return f"https://doi.org/{match.group(1)}"


def isbn13_valid(value: Any) -> bool:
    if value is None:
        return False
    digits = re.sub(r"[-\s]", "", str(value))
    if not re.fullmatch(r"\d{13}", digits):
        return False
    total = sum((1 if index % 2 == 0 else 3) * int(char) for index, char in enumerate(digits[:12]))
    check = (10 - (total % 10)) % 10
    return check == int(digits[-1])


def integer_edition(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not re.fullmatch(r"[1-9]\d*", raw):
        return None
    return int(raw)


def mapped(mapping: dict[str, Any], section: str, value: Any) -> str | None:
    return mapping.get(section, {}).get(str(value))


def title_full(title: dict[str, Any]) -> str:
    primary = str(title.get("primary") or "").strip()
    subtitle = str(title.get("subtitle") or "").strip()
    return primary if not subtitle else f"{primary}: {subtitle}"


def publication_accessibility(
    book: dict[str, Any], mapping: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    accessibility = book.get("accessibility", {})
    accessibility_map = mapping.get("accessibility_standard", {})
    recognised: list[tuple[str, str]] = []
    omitted: list[str] = []

    for item in accessibility.get("conforms_to", []) or []:
        raw = str(item).strip()
        if not raw:
            continue
        mapped_value = accessibility_map.get(raw)
        if mapped_value:
            recognised.append((raw, mapped_value))
        else:
            omitted.append(raw)

    result: dict[str, Any] = {
        "accessibilityReportUrl": accessibility.get("statement_url"),
    }
    if recognised:
        result["accessibilityStandard"] = recognised[0][1]
    if len(recognised) > 1:
        result["accessibilityAdditionalStandard"] = recognised[1][1]
    for raw, _ in recognised[2:]:
        omitted.append(f"recognised-but-no-third-thoth-slot:{raw}")
    return result, omitted


def role_main_decisions(contributor: dict[str, Any], index: int) -> tuple[dict[str, bool | None], list[str]]:
    roles = [str(role) for role in (contributor.get("roles") or [])]
    details = contributor.get("role_details") or []
    blockers: list[str] = []
    decisions: dict[str, bool | None] = {}

    if not roles:
        blockers.append(f"contributor-{index}-missing-roles")
        return decisions, blockers

    if details:
        seen: set[str] = set()
        for detail_index, detail in enumerate(details, start=1):
            role = str(detail.get("role") or "").strip()
            if not role:
                blockers.append(f"contributor-{index}-role-detail-{detail_index}-missing-role")
                continue
            if role not in roles:
                blockers.append(f"contributor-{index}-role-detail-not-listed-in-roles:{role}")
                continue
            if role in seen:
                blockers.append(f"contributor-{index}-duplicate-role-detail:{role}")
                continue
            seen.add(role)
            main_value = detail.get("main_contribution")
            if not isinstance(main_value, bool):
                blockers.append(f"contributor-{index}-role-{role}-missing-main-contribution-decision")
                decisions[role] = None
            else:
                decisions[role] = main_value
        for role in roles:
            if role not in decisions:
                blockers.append(f"contributor-{index}-role-{role}-missing-role-detail")
                decisions[role] = None
        return decisions, blockers

    if len(roles) > 1:
        blockers.append(f"contributor-{index}-multiple-roles-require-role-details")
        return {role: None for role in roles}, blockers

    main_value = contributor.get("main_contribution")
    if not isinstance(main_value, bool):
        blockers.append(f"contributor-{index}-missing-main-contribution-decision")
        main_value = None
    decisions[roles[0]] = main_value
    return decisions, blockers


def map_contributors(book: dict[str, Any], mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    operations: list[dict[str, Any]] = []
    blockers: list[str] = []

    for index, contributor in enumerate(book.get("contributors", []), start=1):
        family_name = str(contributor.get("family_name") or "").strip()
        given_name = str(contributor.get("given_name") or "").strip()
        full_name = str(contributor.get("name") or "").strip()
        if not family_name:
            blockers.append(f"contributor-{index}-missing-verified-family-name")

        roles = contributor.get("roles", []) or []
        role_decisions, decision_blockers = role_main_decisions(contributor, index)
        blockers.extend(decision_blockers)

        role_values: list[tuple[str, str]] = []
        for role in roles:
            mapped_role = mapped(mapping, "contributor_role", role)
            if not mapped_role:
                blockers.append(f"contributor-{index}-unmapped-role:{role}")
            else:
                role_values.append((str(role), mapped_role))

        orcid = contributor.get("orcid")
        if orcid and not ORCID_RE.fullmatch(str(orcid)):
            blockers.append(f"contributor-{index}-invalid-orcid")

        contributor_ref = f"$contributor[{index}].contributorId"
        contributor_data: dict[str, Any] = {
            "firstName": given_name or None,
            "lastName": family_name or None,
            "fullName": full_name,
            "orcid": orcid or None,
            "website": contributor.get("website"),
        }
        operations.append({
            "operation": "createContributor",
            "result_ref": contributor_ref,
            "data": contributor_data,
        })

        for role_index, (local_role, role_value) in enumerate(role_values, start=1):
            operations.append({
                "operation": "createContribution",
                "data": {
                    "workId": "$work.workId",
                    "contributorId": contributor_ref,
                    "contributionType": role_value,
                    "mainContribution": role_decisions.get(local_role),
                    "firstName": given_name or None,
                    "lastName": family_name or None,
                    "fullName": full_name,
                    "contributionOrdinal": index * 100 + role_index,
                },
            })

    return operations, blockers


def map_languages(book: dict[str, Any], mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    operations: list[dict[str, Any]] = []
    blockers: list[str] = []
    primary = str(book.get("language") or "").strip().lower()
    primary_code = mapped(mapping, "language", primary)
    if not primary_code:
        blockers.append(f"unmapped-language:{primary or 'missing'}")
        return operations, blockers

    if book.get("record_type") == "licensed-translation":
        original = str(book.get("original_language") or "").strip().lower()
        original_code = mapped(mapping, "language", original)
        if not original_code:
            blockers.append(f"licensed-translation-unmapped-original-language:{original or 'missing'}")
        operations.append({
            "operation": "createLanguage",
            "data": {
                "workId": "$work.workId",
                "languageCode": primary_code,
                "languageRelation": "TRANSLATED_INTO",
            },
        })
        if original_code:
            operations.append({
                "operation": "createLanguage",
                "data": {
                    "workId": "$work.workId",
                    "languageCode": original_code,
                    "languageRelation": "TRANSLATED_FROM",
                },
            })
    else:
        operations.append({
            "operation": "createLanguage",
            "data": {
                "workId": "$work.workId",
                "languageCode": primary_code,
                "languageRelation": "ORIGINAL",
            },
        })
    return operations, blockers


def map_subjects(book: dict[str, Any], mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    operations: list[dict[str, Any]] = []
    blockers: list[str] = []
    omitted: list[dict[str, Any]] = []

    for index, subject in enumerate(book.get("subjects", []), start=1):
        scheme = subject.get("scheme")
        subject_type = mapped(mapping, "subject_scheme", scheme)
        if not subject_type:
            omitted.append(subject)
            continue
        code = str(subject.get("code") or "").strip()
        if not code:
            blockers.append(f"subject-{index}-{scheme}-missing-explicit-code")
            continue
        operations.append({
            "operation": "createSubject",
            "data": {
                "workId": "$work.workId",
                "subjectType": subject_type,
                "subjectCode": code,
                "subjectOrdinal": index,
            },
        })

    if not operations:
        blockers.append("no-exportable-coded-subject")
    return operations, blockers, omitted


def map_publications(book: dict[str, Any], mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    operations: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    accessibility_data, omitted_a11y = publication_accessibility(book, mapping)
    warnings.extend(f"unmapped-accessibility-standard:{item}" for item in omitted_a11y)
    location_platform = mapping.get("publisher_full_text_location")
    if not location_platform:
        blockers.append("missing-publisher-full-text-location-mapping")

    formats = book.get("publication", {}).get("formats", []) or []
    for index, item in enumerate(formats, start=1):
        local_format = item.get("format")
        publication_type = mapped(mapping, "publication_format", local_format)
        if not publication_type:
            blockers.append(f"format-{index}-requires-explicit-thoth-publication-type:{local_format}")
            continue

        isbn = item.get("isbn")
        if isbn and not isbn13_valid(isbn):
            blockers.append(f"format-{index}-invalid-isbn13")

        publication_ref = f"$publication[{index}].publicationId"
        publication_data: dict[str, Any] = {
            "publicationType": publication_type,
            "workId": "$work.workId",
            "isbn": isbn or None,
            **accessibility_data,
        }
        operations.append({
            "operation": "createPublication",
            "result_ref": publication_ref,
            "data": publication_data,
        })

        access_url = str(item.get("access_url") or "").strip()
        if item.get("access_status") == "open" and not access_url:
            blockers.append(f"format-{index}-open-without-full-text-url")
        checksum = str(item.get("checksum_sha256") or "").strip().lower()
        if checksum and not SHA256_RE.fullmatch(checksum):
            blockers.append(f"format-{index}-invalid-sha256-checksum")

        if access_url and location_platform:
            location_data: dict[str, Any] = {
                "publicationId": publication_ref,
                "landingPage": f"https://healthrenewal.org/open-books/{book['slug']}/",
                "fullTextUrl": access_url,
                "locationPlatform": location_platform,
                "canonical": True,
            }
            if checksum and SHA256_RE.fullmatch(checksum):
                location_data["checksum"] = checksum
                location_data["checksumAlgorithm"] = "SHA256"
            operations.append({
                "operation": "createLocation",
                "data": location_data,
            })
    return operations, blockers, warnings


def map_book(book: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    mapping = contract.get("safe_local_mappings", {})
    blockers: list[str] = []
    warnings: list[str] = []
    operations: list[dict[str, Any]] = []

    work_type = mapped(mapping, "work_type", book.get("work_type"))
    if not work_type:
        if book.get("work_type") in set(mapping.get("work_type_forbidden_pending_thoth_confirmation", [])):
            blockers.append(f"work-type-forbidden-pending-thoth-confirmation:{book.get('work_type')}")
        else:
            blockers.append(f"work-type-requires-explicit-mapping:{book.get('work_type')}")

    local_status = book.get("publication", {}).get("status")
    work_status = mapped(mapping, "work_status", local_status)
    if not work_status:
        blockers.append(f"unmapped-work-status:{local_status}")

    edition = integer_edition(book.get("publication", {}).get("edition"))
    if edition is None:
        blockers.append("edition-must-be-explicit-positive-integer-for-thoth")

    doi_raw = book.get("identifiers", {}).get("doi")
    doi = normalize_doi(doi_raw)
    if doi_raw and not doi:
        blockers.append("invalid-doi")

    title_language = str(book.get("title", {}).get("primary_language") or book.get("language") or "").strip().lower()
    locale = mapped(mapping, "locale", title_language)
    if not locale:
        blockers.append(f"unmapped-title-locale:{title_language or 'missing'}")

    work_data = {
        "workType": work_type,
        "workStatus": work_status,
        "reference": book.get("id"),
        "edition": edition,
        "imprintId": "$THOTH_IMPRINT_ID",
        "doi": doi,
        "publicationDate": book.get("publication", {}).get("publication_date"),
        "license": book.get("rights", {}).get("text_license", {}).get("url"),
        "copyrightHolder": book.get("rights", {}).get("copyright_holder"),
        "landingPage": f"https://healthrenewal.org/open-books/{book['slug']}/",
    }
    operations.append({"operation": "createWork", "result_ref": "$work.workId", "data": work_data})

    if locale:
        operations.append({
            "operation": "createTitle",
            "extra_args": {"markupFormat": "PLAIN_TEXT"},
            "data": {
                "workId": "$work.workId",
                "localeCode": locale,
                "fullTitle": title_full(book.get("title", {})),
                "title": book.get("title", {}).get("primary"),
                "subtitle": book.get("title", {}).get("subtitle"),
                "canonical": True,
            },
        })
        abstract = str(book.get("abstract") or "").strip()
        if abstract:
            operations.append({
                "operation": "createAbstract",
                "extra_args": {"markupFormat": "PLAIN_TEXT"},
                "data": {
                    "workId": "$work.workId",
                    "content": abstract,
                    "localeCode": locale,
                    "abstractType": "LONG",
                    "canonical": True,
                },
            })

    contributor_ops, contributor_blockers = map_contributors(book, mapping)
    language_ops, language_blockers = map_languages(book, mapping)
    subject_ops, subject_blockers, omitted_subjects = map_subjects(book, mapping)
    publication_ops, publication_blockers, publication_warnings = map_publications(book, mapping)
    operations.extend(contributor_ops)
    operations.extend(language_ops)
    operations.extend(subject_ops)
    operations.extend(publication_ops)
    blockers.extend(contributor_blockers)
    blockers.extend(language_blockers)
    blockers.extend(subject_blockers)
    blockers.extend(publication_blockers)
    warnings.extend(publication_warnings)

    if omitted_subjects:
        warnings.append(f"local-only-subjects-omitted:{len(omitted_subjects)}")

    blockers = unique(blockers)
    warnings = unique(warnings)
    return {
        "book_id": book["id"],
        "slug": book["slug"],
        "ready_for_offline_template_review": not blockers,
        "transmission_permitted": False,
        "external_prerequisites": [
            "verify-current-thoth-bulk-template-or-live-schema",
            "verify-activated-publisher-and-imprint",
            "human-review-generated-plan",
        ],
        "blockers": blockers,
        "warnings": warnings,
        "omitted_local_subjects": omitted_subjects,
        "operations": operations,
    }


def build() -> dict[str, Any]:
    contract = load(CONTRACT_FILE)
    publisher = load(PUBLISHER_FILE)
    rights = staging.rights_index()
    translations = staging.translation_index()
    books = staging.records(BOOKS_DIR)
    candidates = [book for book in books if staging.thoth_candidate(book, rights, translations)]
    plans = [map_book(book, contract) for book in candidates]
    plans.sort(key=lambda item: item["book_id"])
    ready = sum(item["ready_for_offline_template_review"] for item in plans)

    return {
        "schema_version": "1.0.0",
        "publisher": publisher.get("publisher", {}).get("display_name"),
        "generated_from": "data/publishing/books + rights + translations via local Thoth eligibility gates",
        "mapping_contract": "data/publishing/thoth-schema-contract.json",
        "thoth_graphql_schema": contract.get("thoth", {}).get("graphql_schema_version"),
        "execution_enabled": False,
        "transmission_permitted": False,
        "credential_inputs": [],
        "final_authority": "Current Thoth bulk-uploader CSV/ONIX 3.0 template or live schema immediately before upload.",
        "candidate_count": len(plans),
        "ready_plan_count": ready,
        "blocked_plan_count": len(plans) - ready,
        "plans": plans,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if committed upload plan is stale.")
    args = parser.parse_args()

    content = dump(build())
    current = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else ""
    if args.check:
        if current != content:
            print(f"Generated Thoth upload plan is stale: {OUTPUT_FILE.relative_to(ROOT)}")
            return 1
        print("Thoth upload plan is current and remains non-executable.")
        return 0

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print("Thoth upload plan regenerated; transmission remains disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
