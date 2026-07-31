#!/usr/bin/env python3
"""Validate the governed external-source rights registry.

This gate checks internal consistency only. It is not legal advice and does not
replace reviewing the original licence or written permission for each use.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_REGISTRY = Path("api/source-rights-registry.json")

PERMISSION_VALUES = {
    "allowed",
    "not_allowed",
    "permission_required",
    "not_confirmed",
    "not_available",
}

RIGHTS_STATUS_VALUES = {
    "open_reuse",
    "link_only",
    "referral_only",
    "source_specific_review",
    "commercial_agreement_required",
}

PERMISSION_FIELDS = {
    "link",
    "copy",
    "translate",
    "adapt",
    "redistribute",
    "embed",
    "commercial_use",
    "logo_use",
    "automated_catalogue",
}

REQUIRED_SOURCE_FIELDS = {
    "id",
    "name",
    "name_ar",
    "official_url",
    "rights_status",
    "access_mode",
    "relationship_status",
    "licence",
    "permissions",
    "requirements",
    "recommended_platform_use",
    "evidence",
    "review_due",
}

COPYLIKE_FIELDS = {"copy", "translate", "adapt", "redistribute", "embed"}


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_registry(data: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Registry root must be a JSON object."]

    required_top_level = {
        "schema_version",
        "updated_at",
        "relationship_policy",
        "disclaimer_ar",
        "permission_values",
        "rights_status_values",
        "sources",
    }
    missing_top = required_top_level - set(data)
    if missing_top:
        errors.append(f"Missing top-level fields: {sorted(missing_top)}")

    if data.get("relationship_policy") != "independent_source_not_partner":
        errors.append(
            "relationship_policy must be 'independent_source_not_partner'."
        )

    if not _is_iso_date(data.get("updated_at")):
        errors.append("updated_at must be an ISO date (YYYY-MM-DD).")

    if set(data.get("permission_values", [])) != PERMISSION_VALUES:
        errors.append("permission_values must match the published permission enum.")

    if set(data.get("rights_status_values", [])) != RIGHTS_STATUS_VALUES:
        errors.append("rights_status_values must match the published rights enum.")

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array.")
        return errors

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()

    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object.")
            continue

        missing = REQUIRED_SOURCE_FIELDS - set(source)
        if missing:
            errors.append(f"{label} is missing fields: {sorted(missing)}")
            continue

        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{label}.id must be a non-empty string.")
        elif source_id in seen_ids:
            errors.append(f"Duplicate source id: {source_id}")
        else:
            seen_ids.add(source_id)

        official_url = source.get("official_url")
        if not _is_https_url(official_url):
            errors.append(f"{label}.official_url must be an HTTPS URL.")
        elif official_url in seen_urls:
            errors.append(f"Duplicate official_url: {official_url}")
        else:
            seen_urls.add(official_url)

        if source.get("rights_status") not in RIGHTS_STATUS_VALUES:
            errors.append(
                f"{label}.rights_status is not one of {sorted(RIGHTS_STATUS_VALUES)}."
            )

        if source.get("relationship_status") != "independent_source_not_partner":
            errors.append(
                f"{label}.relationship_status must be independent_source_not_partner."
            )

        permissions = source.get("permissions")
        if not isinstance(permissions, dict):
            errors.append(f"{label}.permissions must be an object.")
        else:
            missing_permissions = PERMISSION_FIELDS - set(permissions)
            extra_permissions = set(permissions) - PERMISSION_FIELDS
            if missing_permissions:
                errors.append(
                    f"{label}.permissions is missing: {sorted(missing_permissions)}"
                )
            if extra_permissions:
                errors.append(
                    f"{label}.permissions has unknown fields: {sorted(extra_permissions)}"
                )
            for field_name, value in permissions.items():
                if value not in PERMISSION_VALUES:
                    errors.append(
                        f"{label}.permissions.{field_name} has invalid value {value!r}."
                    )

        licence = source.get("licence")
        if not isinstance(licence, dict):
            errors.append(f"{label}.licence must be an object.")
            licence = {}

        if source.get("rights_status") == "open_reuse":
            if not licence.get("name") or not licence.get("short_name"):
                errors.append(
                    f"{label}: open_reuse requires a named licence and short_name."
                )
            if isinstance(permissions, dict):
                for field_name in {"link", "copy", "redistribute"}:
                    if permissions.get(field_name) != "allowed":
                        errors.append(
                            f"{label}: open_reuse requires {field_name}=allowed."
                        )

        if source.get("rights_status") in {"link_only", "referral_only"}:
            if isinstance(permissions, dict):
                for field_name in COPYLIKE_FIELDS:
                    if permissions.get(field_name) == "allowed":
                        errors.append(
                            f"{label}: {source.get('rights_status')} cannot mark "
                            f"{field_name}=allowed."
                        )

        if source.get("rights_status") == "commercial_agreement_required":
            if isinstance(permissions, dict):
                controlled = {
                    permissions.get(field_name)
                    for field_name in COPYLIKE_FIELDS | {"commercial_use", "logo_use"}
                }
                if "allowed" in controlled:
                    errors.append(
                        f"{label}: commercial_agreement_required cannot expose "
                        "controlled permissions as allowed."
                    )

        requirements = source.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            errors.append(f"{label}.requirements must be a non-empty array.")

        recommended_use = source.get("recommended_platform_use")
        if not isinstance(recommended_use, list) or not recommended_use:
            errors.append(
                f"{label}.recommended_platform_use must be a non-empty array."
            )

        evidence = source.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{label}.evidence must be an object.")
        else:
            for evidence_field in {"type", "confirmed_at", "summary"}:
                if not evidence.get(evidence_field):
                    errors.append(
                        f"{label}.evidence.{evidence_field} must be populated."
                    )
            if evidence.get("confirmed_at") and not _is_iso_date(
                evidence.get("confirmed_at")
            ):
                errors.append(
                    f"{label}.evidence.confirmed_at must be an ISO date."
                )

        if not _is_iso_date(source.get("review_due")):
            errors.append(f"{label}.review_due must be an ISO date.")
        elif _is_iso_date(data.get("updated_at")):
            if date.fromisoformat(source["review_due"]) < date.fromisoformat(
                data["updated_at"]
            ):
                errors.append(
                    f"{label}.review_due cannot be earlier than updated_at."
                )

    return errors


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to source-rights-registry.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the validation result as JSON.",
    )
    args = parser.parse_args()

    try:
        registry = load_registry(args.path)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [f"Unable to read registry: {exc}"]}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["errors"][0])
        return 1

    errors = validate_registry(registry)
    result = {
        "valid": not errors,
        "source_count": len(registry.get("sources", [])),
        "errors": errors,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif errors:
        print("Source rights registry validation failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print(
            "Source rights registry validation passed "
            f"for {result['source_count']} sources."
        )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
