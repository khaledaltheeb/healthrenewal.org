#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "content" / "v302" / "special-needs-providers-ar.json"
VERSION = 308
PHONE_RE = re.compile(r"^\+[0-9]{7,15}$")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def is_https(value: Any) -> bool:
    parsed = urlparse(str(value))
    return parsed.scheme == "https" and bool(parsed.netloc)


def parse_date(value: Any, field: str, provider_id: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise SystemExit(f"Invalid {field} date for {provider_id}: {value}") from exc


def validate_provider_data(data: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    if data.get("version") != 302 or data.get("governance_version") != VERSION:
        raise SystemExit("Provider directory governance version contract failed")
    providers = data.get("providers")
    if not isinstance(providers, list):
        raise SystemExit("Provider directory must contain a providers list")
    allowed_types = set(data.get("allowed_types", []))
    allowed_specialties = set(data.get("allowed_specialties", []))
    allowed_statuses = set(data.get("allowed_verification_statuses", []))
    allowed_disclosures = set(data.get("allowed_listing_disclosures", []))
    required = tuple(data.get("required_fields_for_publication", []))
    if not allowed_types or not allowed_specialties or allowed_statuses != {"pending", "verified", "expired", "rejected"}:
        raise SystemExit("Provider directory allowed-value contract failed")
    if allowed_disclosures != {"editorial", "sponsored"}:
        raise SystemExit("Provider disclosure values are incomplete")

    ids: set[str] = set()
    counts = {status: 0 for status in allowed_statuses}
    published = 0
    sponsored = 0
    expiring_within_30_days = 0
    for item in providers:
        if not isinstance(item, dict):
            raise SystemExit("Provider records must be objects")
        provider_id = str(item.get("id", "")).strip()
        if not provider_id or provider_id in ids:
            raise SystemExit(f"Duplicate or missing provider id: {provider_id}")
        ids.add(provider_id)
        if item.get("type") not in allowed_types:
            raise SystemExit(f"Invalid provider type: {provider_id}")
        specialties = item.get("specialties")
        if not isinstance(specialties, list) or not specialties or any(value not in allowed_specialties for value in specialties):
            raise SystemExit(f"Invalid provider specialties: {provider_id}")
        status = item.get("verification_status")
        if status not in allowed_statuses:
            raise SystemExit(f"Invalid verification status: {provider_id}")
        counts[status] += 1
        disclosure = item.get("listing_disclosure")
        if disclosure is not None and disclosure not in allowed_disclosures:
            raise SystemExit(f"Invalid listing disclosure: {provider_id}")
        if item.get("sponsored") not in (None, True, False):
            raise SystemExit(f"Sponsored must be a boolean: {provider_id}")
        if item.get("phone_uri") and not PHONE_RE.fullmatch(str(item["phone_uri"])):
            raise SystemExit(f"Phone URI must use international E.164 digits: {provider_id}")
        for key in ("website", "maps_url", "whatsapp_uri"):
            if item.get(key) and not is_https(item[key]):
                raise SystemExit(f"Invalid secure URL {key}: {provider_id}")

        if item.get("published") is not True:
            continue
        missing = [key for key in required if item.get(key) in (None, "", [])]
        if missing:
            raise SystemExit(f"Published provider is missing required fields: {provider_id}/{missing}")
        if status != "verified":
            raise SystemExit(f"Only verified providers may be published: {provider_id}")
        verified_at = parse_date(item["verified_at"], "verified_at", provider_id)
        contacted_at = parse_date(item["last_contact_verified_at"], "last_contact_verified_at", provider_id)
        expires_at = parse_date(item["verification_expires_at"], "verification_expires_at", provider_id)
        if not (verified_at <= contacted_at <= today <= expires_at):
            raise SystemExit(
                f"Provider verification dates are not current: {provider_id}/"
                f"{verified_at}/{contacted_at}/{today}/{expires_at}"
            )
        evidence = item.get("verification_evidence")
        if not isinstance(evidence, list) or not evidence or any(not is_https(url) for url in evidence):
            raise SystemExit(f"Published provider needs HTTPS verification evidence: {provider_id}")
        if not str(item.get("registration_authority", "")).strip() or not str(item.get("registration_reference", "")).strip():
            raise SystemExit(f"Published provider needs registration details: {provider_id}")
        is_sponsored = item.get("sponsored") is True
        if (disclosure == "sponsored") != is_sponsored:
            raise SystemExit(f"Sponsored disclosure mismatch: {provider_id}")
        published += 1
        sponsored += int(is_sponsored)
        expiring_within_30_days += int((expires_at - today).days <= 30)

    return {
        "version": VERSION,
        "status": "passed",
        "checked_at": today.isoformat(),
        "record_count": len(providers),
        "published_count": published,
        "sponsored_count": sponsored,
        "expiring_within_30_days": expiring_within_30_days,
        "status_counts": dict(sorted(counts.items())),
        "provider_source": PROVIDERS.relative_to(ROOT).as_posix(),
    }


def publish(site: Path, today: date | None = None) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    report = validate_provider_data(read_json(PROVIDERS), today=today)
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-provider-governance-v308.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
