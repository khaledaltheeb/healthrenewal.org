from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected JSON object: {path}")
    return payload


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    providers_path = root / "specialists-partners/data/providers.json"
    ledger_path = root / "specialists-partners/data/verification-ledger.json"
    schema_path = root / "specialists-partners/data/verification-ledger.schema.json"
    api_path = root / "api/v1/specialists-partners.json"
    platform_path = root / "api/v1/platform.json"
    for path in (providers_path, ledger_path, schema_path, api_path, platform_path):
        if not path.is_file():
            raise AssertionError(f"Missing provider-accuracy file: {path.relative_to(root)}")

    providers = read_object(providers_path)
    ledger = read_object(ledger_path)
    schema = read_object(schema_path)
    api = read_object(api_path)
    platform = read_object(platform_path)

    policy = providers.get("accuracyPolicy", {})
    required_policy = {
        "siteReviewsBeforePublication": True,
        "fieldLevelEvidenceRequired": True,
        "selfReportedInformationIsTreatedAsUnverifiedUntilChecked": True,
        "materialDisputeCausesTemporarySuspension": True,
        "correctionsAndReviewDatesAreRecorded": True,
        "noAbsoluteGuaranteeBeyondAvailableEvidence": True,
    }
    for key, expected in required_policy.items():
        if policy.get(key) is not expected:
            raise AssertionError(f"Invalid accuracy policy: {key}")

    records = ledger.get("records")
    provider_records = providers.get("providers")
    if not isinstance(records, list) or not isinstance(provider_records, list):
        raise AssertionError("Provider directory and verification ledger must contain arrays")
    if "identity-document" not in str(providers.get("privacyNotice", "")):
        raise AssertionError("Provider privacy notice must prohibit sensitive identity documents")
    if schema.get("title") != "Public-safe provider verification ledger":
        raise AssertionError("Unexpected verification-ledger schema")

    provider_by_id = {item.get("id"): item for item in provider_records if isinstance(item, dict)}
    ledger_by_id: dict[str, dict[str, Any]] = {}
    today = date.today()
    for record in records:
        if not isinstance(record, dict):
            raise AssertionError("Verification records must be objects")
        provider_id = record.get("providerId")
        if not isinstance(provider_id, str) or provider_id in ledger_by_id:
            raise AssertionError(f"Invalid or duplicate ledger providerId: {provider_id}")
        if provider_id not in provider_by_id:
            raise AssertionError(f"Ledger record has no provider profile: {provider_id}")
        ledger_by_id[provider_id] = record

    published = 0
    for provider_id, provider in provider_by_id.items():
        if provider.get("publicationStatus") != "published":
            continue
        published += 1
        record = ledger_by_id.get(provider_id)
        if not record or record.get("reviewStatus") != "verified":
            raise AssertionError(f"Published provider lacks verified ledger record: {provider_id}")
        if provider.get("verification", {}).get("status") != "verified":
            raise AssertionError(f"Published provider is not verified: {provider_id}")
        if provider.get("consent", {}).get("publicProfileApproved") is not True:
            raise AssertionError(f"Published provider lacks written consent: {provider_id}")
        reviewed_fields = record.get("reviewedFields")
        if not isinstance(reviewed_fields, list) or not reviewed_fields:
            raise AssertionError(f"Published provider lacks field-level review: {provider_id}")
        if any(field.get("result") in {"unverified", "disputed"} for field in reviewed_fields if isinstance(field, dict)):
            raise AssertionError(f"Published provider has unresolved claims: {provider_id}")
        next_review = record.get("nextReviewAt")
        if not isinstance(next_review, str) or date.fromisoformat(next_review) < today:
            raise AssertionError(f"Published provider verification has expired: {provider_id}")

    rules = api.get("publicationRules", {})
    for key in ("requiresFieldLevelEvidence", "requiresCurrentLedgerRecord", "suspendOnMaterialDispute"):
        if rules.get(key) is not True:
            raise AssertionError(f"API publication rule missing: {key}")
    if rules.get("selfReportedClaimsAutomaticallyVerified") is not False:
        raise AssertionError("Self-reported claims must not be automatically verified")
    if api.get("verificationLedger") is None or api.get("verificationLedgerSchema") is None:
        raise AssertionError("Sector API does not expose the verification ledger contract")

    endpoints = platform.get("endpoints", {})
    if "specialistsPartnersVerificationLedger" not in endpoints:
        raise AssertionError("Platform API is missing verification-ledger endpoint")
    if "specialistsPartnersVerificationLedgerSchema" not in endpoints:
        raise AssertionError("Platform API is missing verification-ledger schema endpoint")

    return {
        "status": "passed",
        "contract": "provider-accuracy-ledger-v1",
        "providerCount": len(provider_records),
        "publishedProviderCount": published,
        "ledgerRecordCount": len(records),
        "fieldLevelEvidenceRequired": True,
        "sensitiveDocumentsPublic": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(Path(".")), ensure_ascii=False, indent=2))
