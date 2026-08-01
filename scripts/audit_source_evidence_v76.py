from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import audit_source_evidence_v75 as legacy

VERSION = "76-source-evidence-registry"
REGISTRY_FIELDS = {"id", "name", "organization", "url", "type", "scope"}


def is_registry_source(value: Any) -> bool:
    return isinstance(value, dict) and REGISTRY_FIELDS <= set(value)


def validate_registry_source(
    source: dict[str, Any], pointer: str, today: date
) -> list[legacy.Finding]:
    del today
    findings: list[legacy.Finding] = []
    for field in sorted(REGISTRY_FIELDS):
        value = source.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(
                legacy.Finding(
                    "error",
                    "missing-registry-field",
                    pointer,
                    f"Central source registry field must be a non-empty string: {field}.",
                )
            )

    source_id = str(source.get("id", "")).strip()
    if source_id and not legacy.ID_RE.fullmatch(source_id):
        findings.append(
            legacy.Finding(
                "error",
                "invalid-registry-source-id",
                pointer,
                "Central source registry id must use stable lowercase kebab-case.",
            )
        )
    if source.get("url") and not legacy.is_https_url(source.get("url")):
        findings.append(
            legacy.Finding(
                "error",
                "non-https-source",
                pointer,
                "Central source registry URL must be an absolute HTTPS URL.",
            )
        )
    return findings


def registry_for_payload(
    payload: Any, relative: str
) -> tuple[dict[str, dict[str, Any]], list[legacy.Finding]]:
    findings: list[legacy.Finding] = []
    registry: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        return registry, findings

    for index, source in enumerate(payload["sources"]):
        if not is_registry_source(source):
            continue
        source_id = str(source.get("id", "")).strip()
        pointer = f"{relative}:$.sources[{index}]"
        if source_id in registry:
            findings.append(
                legacy.Finding(
                    "error",
                    "duplicate-registry-source-id",
                    pointer,
                    f"Central source registry id is duplicated: {source_id}",
                )
            )
            continue
        registry[source_id] = source
    return registry, findings


def audit_file(
    path: Path, root: Path, today: date
) -> tuple[list[dict[str, Any]], list[legacy.Finding]]:
    relative = path.relative_to(root).as_posix()
    try:
        payload = legacy.load_json(path)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [], [legacy.Finding("error", "invalid-json", relative, str(exc))]

    registry, findings = registry_for_payload(payload, relative)
    records: list[dict[str, Any]] = []

    for pointer, sources in legacy.walk_source_arrays(payload):
        seen_urls: dict[str, int] = {}
        for index, source in enumerate(sources):
            source_pointer = f"{relative}:{pointer}[{index}]"
            registry_record = pointer == "$.sources" and is_registry_source(source)
            reference_record = (
                pointer != "$.sources"
                and isinstance(source, str)
                and not legacy.is_https_url(source)
                and source.strip() in registry
            )

            if registry_record:
                source_findings = validate_registry_source(source, source_pointer, today)
                url = str(source.get("url", "")).strip()
                publisher = source.get("organization")
                title = source.get("name")
                legacy_name = source.get("name")
                record_format = "central-registry-object"
                contract_ready = not any(
                    item.severity == "error" for item in source_findings
                )
                year = None
            elif reference_record:
                source_id = source.strip()
                target = registry[source_id]
                source_findings = []
                url = str(target["url"]).strip()
                publisher = target["organization"]
                title = target["name"]
                legacy_name = None
                record_format = "central-registry-reference"
                contract_ready = True
                year = None
            else:
                source_findings = legacy.validate_source(source, source_pointer, today)
                url = legacy.source_url(source)
                is_mapping = isinstance(source, dict)
                summary = legacy.is_traceable_summary(source)
                reviewed = legacy.parse_date(source.get("reviewed")) if is_mapping else None
                publisher = (
                    source.get("publisher") or source.get("organization")
                    if is_mapping
                    else None
                )
                title = source.get("title") if is_mapping else None
                legacy_name = source.get("name") if is_mapping else None
                record_format = legacy.record_format(source)
                contract_ready = legacy.is_contract_ready(source)
                year = (
                    source.get("year")
                    if is_mapping and not summary
                    else reviewed.year if reviewed else None
                )

            findings.extend(source_findings)
            if url:
                seen_urls[url] = seen_urls.get(url, 0) + 1
            records.append(
                {
                    "file": relative,
                    "pointer": f"{pointer}[{index}]",
                    "record_format": record_format,
                    "publisher": publisher,
                    "title": title,
                    "legacy_name": legacy_name,
                    "url": url or None,
                    "year": year,
                    "contract_ready": contract_ready,
                    "error_count": sum(
                        item.severity == "error" for item in source_findings
                    ),
                    "warning_count": sum(
                        item.severity == "warning" for item in source_findings
                    ),
                }
            )

        for url, count in seen_urls.items():
            if count > 1:
                findings.append(
                    legacy.Finding(
                        "error",
                        "duplicate-source-url",
                        f"{relative}:{pointer}",
                        f"Source URL appears {count} times in the same source list: {url}",
                    )
                )

    # A non-HTTPS string inside a nested source list is only valid when it
    # resolves against the file's central registry. Legacy validation above
    # deliberately rejects unknown identifiers as non-HTTPS sources.
    return records, findings


def audit_repository(root: Path, today: date | None = None) -> dict[str, Any]:
    original = legacy.audit_file
    legacy.audit_file = audit_file
    try:
        report = legacy.audit_repository(root, today=today)
    finally:
        legacy.audit_file = original

    report["version"] = VERSION
    report["central_registry_records"] = sum(
        item["record_format"] == "central-registry-object"
        for item in report["records"]
    )
    report["central_registry_references"] = sum(
        item["record_format"] == "central-registry-reference"
        for item in report["records"]
    )
    report["policy"]["central_registry_references_require_local_resolution"] = True
    report["policy"]["unknown_registry_references_fail"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit structured evidence and central source references."
    )
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--output", default="artifacts/source-evidence-v75.json"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = audit_repository(root)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "version": report["version"],
                "source_records": report["source_records"],
                "central_registry_records": report["central_registry_records"],
                "central_registry_references": report["central_registry_references"],
                "errors": report["error_count"],
                "warnings": report["warning_count"],
                "output": output.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
