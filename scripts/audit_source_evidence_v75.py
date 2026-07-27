from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SOURCE_TYPES = {
    "official_guideline",
    "systematic_review",
    "primary_research",
    "diagnostic_manual_or_classification",
    "original_instrument",
    "public_health_authority",
    "professional_body_guideline",
    "peer_reviewed_review",
    "institutional_fact_sheet",
}
STATUSES = {"current", "superseded", "withdrawn", "inaccessible", "pending_verification"}
ADVANCED_FIELDS = {"id", "source_type", "verified_at", "claims_supported", "status"}
SOURCE_KEYS = {"publisher", "title", "url", "year"}
TRACEABLE_SUMMARY_FIELDS = {"id", "organization", "title", "url", "level", "reviewed"}
TRACEABLE_LEVELS = {"S1", "S2", "S3", "S4", "S5"}
SOURCE_CONTAINER_KEYS = {"sources", "references", "citations"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUMMARY_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{0,31}$")
YEAR_RE = re.compile(r"^\d{4}$")


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_source_arrays(value: Any, pointer: str = "$") -> Iterable[tuple[str, list[Any]]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}.{key}"
            if key in SOURCE_CONTAINER_KEYS and isinstance(child, list):
                yield child_pointer, child
            yield from walk_source_arrays(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_source_arrays(child, f"{pointer}[{index}]")


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def is_traceable_summary(source: Any) -> bool:
    return (
        isinstance(source, dict)
        and not ADVANCED_FIELDS <= set(source)
        and TRACEABLE_SUMMARY_FIELDS <= set(source)
    )


def is_contract_ready(source: Any) -> bool:
    return isinstance(source, dict) and (ADVANCED_FIELDS <= set(source) or is_traceable_summary(source))


def validate_legacy_url(value: str, pointer: str) -> list[Finding]:
    if not is_https_url(value):
        return [
            Finding(
                "error",
                "non-https-source",
                pointer,
                "Legacy source URL must be an absolute HTTPS URL.",
            )
        ]
    return [
        Finding(
            "warning",
            "legacy-url-only-source",
            pointer,
            "URL-only legacy source is safe to retain during migration but lacks publisher, title, year and claim-level evidence metadata.",
        )
    ]


def validate_year(value: Any, pointer: str, today: date, *, contract_ready: bool) -> list[Finding]:
    findings: list[Finding] = []
    numeric_year: int | None = None
    if isinstance(value, int) and not isinstance(value, bool):
        numeric_year = value
    elif not contract_ready and isinstance(value, str) and YEAR_RE.fullmatch(value.strip()):
        numeric_year = int(value.strip())
        findings.append(
            Finding(
                "warning",
                "legacy-year-string",
                pointer,
                "Legacy source year is stored as a numeric string; migrate it to an integer.",
            )
        )
    elif value is not None:
        findings.append(Finding("error", "invalid-year", pointer, "Source year must be an integer."))

    if numeric_year is not None and (numeric_year < 1800 or numeric_year > today.year + 1):
        findings.append(
            Finding(
                "error",
                "implausible-year",
                pointer,
                f"Source year {numeric_year} is outside the accepted range.",
            )
        )
    return findings


def validate_traceable_summary(source: dict[str, Any], pointer: str, today: date) -> list[Finding]:
    findings: list[Finding] = []
    for field in sorted(TRACEABLE_SUMMARY_FIELDS):
        value = source.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append(Finding("error", "missing-summary-field", pointer, f"Missing required summary field: {field}."))

    source_id = str(source.get("id", "")).strip()
    if not SUMMARY_ID_RE.fullmatch(source_id):
        findings.append(
            Finding(
                "error",
                "invalid-summary-source-id",
                pointer,
                "Traceable summary id must be a stable uppercase citation label such as A1 or D4.",
            )
        )

    if source.get("level") not in TRACEABLE_LEVELS:
        findings.append(
            Finding(
                "error",
                "invalid-evidence-level",
                pointer,
                f"Traceable summary level must be one of {sorted(TRACEABLE_LEVELS)}.",
            )
        )

    reviewed = parse_date(source.get("reviewed"))
    if reviewed is None:
        findings.append(Finding("error", "invalid-reviewed-date", pointer, "reviewed must use YYYY-MM-DD."))
    elif reviewed > today:
        findings.append(Finding("error", "future-reviewed-date", pointer, "reviewed cannot be in the future."))

    if not is_https_url(source.get("url")):
        findings.append(Finding("error", "non-https-source", pointer, "Source URL must be an absolute HTTPS URL."))
    return findings


def validate_source(source: Any, pointer: str, today: date) -> list[Finding]:
    if isinstance(source, str):
        return validate_legacy_url(source, pointer)
    if not isinstance(source, dict):
        return [
            Finding(
                "error",
                "source-not-object",
                pointer,
                "Source record must be an object or a legacy HTTPS URL string.",
            )
        ]

    if is_traceable_summary(source):
        return validate_traceable_summary(source, pointer, today)

    findings: list[Finding] = []
    present_advanced = ADVANCED_FIELDS.intersection(source)
    contract_ready = ADVANCED_FIELDS <= set(source)
    partial_advanced = bool(present_advanced) and not contract_ready
    legacy_name_url = (
        not present_advanced
        and is_https_url(source.get("url"))
        and isinstance(source.get("name"), str)
        and bool(source["name"].strip())
        and not any(source.get(field) not in (None, "") for field in ("publisher", "title", "year"))
    )

    if partial_advanced:
        missing = ", ".join(sorted(ADVANCED_FIELDS - present_advanced))
        findings.append(
            Finding(
                "error",
                "partial-advanced-contract",
                pointer,
                f"Advanced evidence metadata is partial; missing: {missing}.",
            )
        )

    if legacy_name_url:
        findings.append(
            Finding(
                "warning",
                "legacy-name-url-source",
                pointer,
                "Legacy source uses name+url only; retain during migration, then split name into publisher/title and add year and evidence metadata.",
            )
        )
    else:
        for field in sorted(SOURCE_KEYS):
            value = source.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append(Finding("error", "missing-basic-field", pointer, f"Missing required field: {field}."))

    url = str(source.get("url", "")).strip()
    if url and not is_https_url(url):
        findings.append(Finding("error", "non-https-source", pointer, "Source URL must be an absolute HTTPS URL."))

    if not legacy_name_url:
        findings.extend(validate_year(source.get("year"), pointer, today, contract_ready=contract_ready))

    if contract_ready:
        source_id = str(source.get("id", "")).strip()
        if not ID_RE.fullmatch(source_id):
            findings.append(
                Finding(
                    "error",
                    "invalid-source-id",
                    pointer,
                    "Source id must be a stable lowercase kebab-case identifier.",
                )
            )

        source_type = source.get("source_type")
        if source_type not in SOURCE_TYPES:
            findings.append(Finding("error", "invalid-source-type", pointer, f"Unsupported source_type: {source_type!r}."))

        status = source.get("status")
        if status not in STATUSES:
            findings.append(Finding("error", "invalid-source-status", pointer, f"Unsupported status: {status!r}."))

        verified_at = parse_date(source.get("verified_at"))
        if verified_at is None:
            findings.append(Finding("error", "invalid-verified-at", pointer, "verified_at must use YYYY-MM-DD."))
        elif verified_at > today:
            findings.append(Finding("error", "future-verification-date", pointer, "verified_at cannot be in the future."))

        claims = source.get("claims_supported")
        if not isinstance(claims, list) or not claims or not all(isinstance(item, str) and item.strip() for item in claims):
            findings.append(
                Finding(
                    "error",
                    "invalid-claims-supported",
                    pointer,
                    "claims_supported must be a non-empty list of precise claim identifiers or descriptions.",
                )
            )
    elif not legacy_name_url:
        missing = ", ".join(sorted(ADVANCED_FIELDS))
        findings.append(
            Finding(
                "warning",
                "legacy-source-record",
                pointer,
                f"Basic source is valid but not yet contract-ready; add: {missing}.",
            )
        )

    return findings


def source_url(source: Any) -> str:
    if isinstance(source, str):
        return source.strip()
    if isinstance(source, dict) and isinstance(source.get("url"), str):
        return source["url"].strip()
    return ""


def record_format(source: Any) -> str:
    if isinstance(source, str):
        return "url-string"
    if isinstance(source, dict):
        if is_traceable_summary(source):
            return "traceable-summary-object"
        if (
            isinstance(source.get("name"), str)
            and source.get("url")
            and not any(source.get(field) not in (None, "") for field in ("publisher", "title", "year"))
        ):
            return "name-url-object"
        return "object"
    return type(source).__name__


def audit_file(path: Path, root: Path, today: date) -> tuple[list[dict[str, Any]], list[Finding]]:
    relative = path.relative_to(root).as_posix()
    try:
        payload = load_json(path)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [], [Finding("error", "invalid-json", relative, str(exc))]

    records: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for pointer, sources in walk_source_arrays(payload):
        seen_urls: dict[str, int] = {}
        for index, source in enumerate(sources):
            source_pointer = f"{relative}:{pointer}[{index}]"
            source_findings = validate_source(source, source_pointer, today)
            findings.extend(source_findings)
            url = source_url(source)
            if url:
                seen_urls[url] = seen_urls.get(url, 0) + 1

            is_mapping = isinstance(source, dict)
            summary = is_traceable_summary(source)
            reviewed = parse_date(source.get("reviewed")) if is_mapping else None
            records.append(
                {
                    "file": relative,
                    "pointer": f"{pointer}[{index}]",
                    "record_format": record_format(source),
                    "publisher": (
                        source.get("publisher") or source.get("organization") if is_mapping else None
                    ),
                    "title": source.get("title") if is_mapping else None,
                    "legacy_name": source.get("name") if is_mapping else None,
                    "url": url or None,
                    "year": (
                        source.get("year") if is_mapping and not summary else reviewed.year if reviewed else None
                    ),
                    "contract_ready": is_contract_ready(source),
                    "error_count": sum(item.severity == "error" for item in source_findings),
                    "warning_count": sum(item.severity == "warning" for item in source_findings),
                }
            )
        for url, count in seen_urls.items():
            if count > 1:
                findings.append(
                    Finding(
                        "error",
                        "duplicate-source-url",
                        f"{relative}:{pointer}",
                        f"Source URL appears {count} times in the same source list: {url}",
                    )
                )
    return records, findings


def iter_json_files(root: Path) -> Iterable[Path]:
    for directory in ("content", "data"):
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            if path.name == "source-evidence-contract-v75.json":
                continue
            yield path


def audit_repository(root: Path, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    records: list[dict[str, Any]] = []
    findings: list[Finding] = []
    files_with_sources: set[str] = set()

    for path in iter_json_files(root):
        file_records, file_findings = audit_file(path, root, today)
        if file_records:
            files_with_sources.add(path.relative_to(root).as_posix())
        records.extend(file_records)
        findings.extend(file_findings)

    errors = [item.as_dict() for item in findings if item.severity == "error"]
    warnings = [item.as_dict() for item in findings if item.severity == "warning"]
    report = {
        "version": "75-source-evidence",
        "generated_at": today.isoformat(),
        "files_with_source_lists": len(files_with_sources),
        "source_records": len(records),
        "contract_ready_records": sum(bool(item["contract_ready"]) for item in records),
        "traceable_summary_records": sum(item["record_format"] == "traceable-summary-object" for item in records),
        "legacy_object_records": sum(
            item["record_format"] == "object" and not bool(item["contract_ready"]) for item in records
        ),
        "legacy_url_records": sum(item["record_format"] == "url-string" for item in records),
        "legacy_name_url_records": sum(item["record_format"] == "name-url-object" for item in records),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors[:1000],
        "warnings": warnings[:2000],
        "records": records,
        "policy": {
            "legacy_records_are_warnings": True,
            "unsafe_basic_records_fail": True,
            "full_contract_requires_integer_year": True,
            "traceable_summary_requires_level_and_review_date": True,
            "automatic_content_rewrite": False,
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit structured source evidence in repository JSON content.")
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    parser.add_argument("--output", default="artifacts/source-evidence-v75.json")
    arguments = parser.parse_args()

    root = Path(arguments.root).resolve()
    report = audit_repository(root)
    output = root / arguments.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "files_with_source_lists",
                    "source_records",
                    "contract_ready_records",
                    "traceable_summary_records",
                    "legacy_object_records",
                    "legacy_url_records",
                    "legacy_name_url_records",
                    "error_count",
                    "warning_count",
                )
            },
            ensure_ascii=False,
        )
    )
    if report["error_count"]:
        raise SystemExit("\n".join(f"{item['path']}: {item['message']}" for item in report["errors"][:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
