from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
from pathlib import Path

RELATIVE_PATH = "specialists-partners/data/provider-import-template.csv"
LIVE_URL = "https://healthrenewal.org/" + RELATIVE_PATH
EXPECTED_HEADERS = (
    "id",
    "entityType",
    "displayName",
    "professionalTitle",
    "centerType",
    "specialties",
    "services",
    "ageGroups",
    "serviceModes",
    "languages",
    "location.country",
    "location.city",
    "location.area",
    "shortBio",
    "contact.website",
    "contact.publicPhone",
    "contact.publicEmail",
    "verification.status",
    "verification.lastVerifiedAt",
    "verification.nextReviewAt",
    "publicationStatus",
    "consent.publicProfileApproved",
    "consent.approvedAt",
)


def validate_text(text: str) -> dict[str, object]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        raise AssertionError("Provider import template must contain a header and an example row")

    headers = tuple(item.strip() for item in rows[0])
    if headers != EXPECTED_HEADERS:
        missing = [item for item in EXPECTED_HEADERS if item not in headers]
        unexpected = [item for item in headers if item not in EXPECTED_HEADERS]
        raise AssertionError(
            f"Provider CSV headers do not match the nested JSON contract; "
            f"missing={missing}, unexpected={unexpected}, headers={headers}"
        )

    if len(headers) != len(set(headers)):
        raise AssertionError("Provider CSV headers must be unique")

    example = rows[1]
    if len(example) != len(headers):
        raise AssertionError(
            f"Provider CSV example row has {len(example)} columns; expected {len(headers)}"
        )

    index = {name: position for position, name in enumerate(headers)}
    if example[index["publicationStatus"]] != "draft":
        raise AssertionError("The import example must remain a draft")
    if example[index["verification.status"]] != "pending":
        raise AssertionError("The import example must remain pending verification")
    if example[index["consent.publicProfileApproved"]].lower() != "false":
        raise AssertionError("The import example must not imply publication consent")
    if example[index["consent.approvedAt"]].strip():
        raise AssertionError("Consent approval date must be blank until explicit consent exists")

    forbidden_headers = {
        "patientName",
        "clientName",
        "childName",
        "diagnosis",
        "medicalRecord",
        "nationalId",
        "identityDocument",
    }
    leaked = sorted(forbidden_headers.intersection(headers))
    if leaked:
        raise AssertionError(f"Sensitive case-data columns are prohibited: {leaked}")

    return {
        "status": "passed",
        "contract": "specialists-partners-import-template-v1",
        "header_count": len(headers),
        "nested_location": True,
        "nested_contact": True,
        "nested_verification": True,
        "nested_consent": True,
        "safe_example": True,
    }


def read_local(root: Path) -> str:
    path = root.resolve() / RELATIVE_PATH
    if not path.is_file():
        raise AssertionError(f"Missing provider import template: {path}")
    return path.read_text(encoding="utf-8-sig")


def read_live(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Cache-Control": "no-cache",
            "User-Agent": "specialists-partners-import-template-verifier",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the specialists-partners CSV import contract.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--url", default=LIVE_URL)
    args = parser.parse_args()

    text = read_live(args.url) if args.live else read_local(Path(args.root))
    print(json.dumps(validate_text(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
