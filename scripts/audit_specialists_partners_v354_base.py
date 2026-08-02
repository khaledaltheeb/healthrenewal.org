#!/usr/bin/env python3
"""Audit the specialist sector's public, private, data, and safety contracts."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = 354
CORE_ORIGIN = "https://pterminology-specialists.pterminology-826ac349.workers.dev"
IDENTITY_ORIGIN = "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev"
TURNSTILE_ORIGIN = "https://challenges.cloudflare.com"
PWA_REGISTRATION_HASH = "'sha256-BvSDsrK+y6wytL+FTl8l8mf29w+riVmJMj7HpNbYEH0='"

PAGES = {
    "directory": ("specialists-partners/index.html", True, {CORE_ORIGIN}),
    "join": ("specialists-partners/join.html", True, {CORE_ORIGIN, TURNSTILE_ORIGIN}),
    "contact": ("specialists-partners/contact.html", False, {CORE_ORIGIN, TURNSTILE_ORIGIN}),
    "verification": ("specialists-partners/verification.html", True, set()),
    "portal": ("specialists-partners/portal/index.html", False, {CORE_ORIGIN}),
    "account": ("specialists-partners/account/index.html", False, {IDENTITY_ORIGIN, TURNSTILE_ORIGIN}),
    "admin": (
        "specialists-partners/admin/index.html",
        False,
        {CORE_ORIGIN, IDENTITY_ORIGIN, TURNSTILE_ORIGIN},
    ),
    "recover": (
        "specialists-partners/recover/index.html",
        False,
        {IDENTITY_ORIGIN, TURNSTILE_ORIGIN},
    ),
    "password_reset": (
        "specialists-partners/password-reset/index.html",
        False,
        {IDENTITY_ORIGIN},
    ),
}

REQUIRED_DIRECTORY_MARKERS = (
    'data-specialists-quality-v354="1"',
    'id="directory-health"',
    'id="directory-health-label"',
    'id="directory-source"',
    'id="directory-updated"',
    'id="directory-filter-context"',
    'id="provider-empty-detail"',
    "لا توجد ملفات مهنية منشورة حاليًا",
    "لا نعرض أسماء تجريبية",
    "ستة أسئلة قبل حجز الخدمة",
    "مرجعيات المنهج",
    "https://www.who.int/publications/i/item/9789240025707",
    "https://www.hcpc-uk.org/standards/standards-of-conduct-performance-and-ethics/",
    "https://www.asha.org/policy/code-of-ethics/",
    "assets/directory-core.js?v=4.1.0",
    "assets/sector.js?v=4.1.0",
)

REQUIRED_CORE_MARKERS = (
    "normalizeArabic",
    "ageMatches",
    "جميع الأعمار",
    "compareProviders",
    "prepareProviders",
    "filterProviders",
    "specialtyAny",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def content_security_policy(text: str) -> str:
    match = re.search(
        r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"',
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else ""


def directive_tokens(policy: str, name: str) -> list[str]:
    for directive in policy.split(";"):
        parts = directive.strip().split()
        if parts and parts[0].lower() == name.lower():
            return parts[1:]
    return []


def reviewed_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def audit(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    interfaces: list[dict[str, Any]] = []

    for name, (relative, indexable, allowed_origins) in PAGES.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing interface: {relative}")
            interfaces.append({"id": name, "path": relative, "passed": False})
            continue

        text = read_text(path)
        policy = content_security_policy(text)
        connect_tokens = directive_tokens(policy, "connect-src")
        absolute_connect_origins = {
            token for token in connect_tokens if token.startswith("https://")
        }
        page_errors: list[str] = []

        if text.count("<h1") != 1:
            page_errors.append("expected exactly one h1")
        if 'lang="ar"' not in text or 'dir="rtl"' not in text:
            page_errors.append("missing Arabic RTL contract")
        if not policy:
            page_errors.append("missing CSP")
        if "https:" in connect_tokens:
            page_errors.append("broad https: connect source")
        if not absolute_connect_origins <= allowed_origins:
            page_errors.append(
                "unexpected connect origin: "
                + ", ".join(sorted(absolute_connect_origins - allowed_origins))
            )
        if not allowed_origins <= absolute_connect_origins:
            page_errors.append(
                "missing connect origin: "
                + ", ".join(sorted(allowed_origins - absolute_connect_origins))
            )
        if "'none'" not in directive_tokens(policy, "frame-ancestors"):
            page_errors.append("frame embedding is not denied")
        if "'none'" not in directive_tokens(policy, "base-uri"):
            page_errors.append("base URI is not locked")
        if PWA_REGISTRATION_HASH not in directive_tokens(policy, "script-src"):
            page_errors.append("production service-worker registration hash is missing")
        if "upgrade-insecure-requests" not in {
            part.strip().split()[0] for part in policy.split(";") if part.strip()
        }:
            page_errors.append("missing upgrade-insecure-requests")

        robots_match = re.search(
            r'<meta\s+name="robots"\s+content="([^"]+)"',
            text,
            flags=re.IGNORECASE,
        )
        robots = robots_match.group(1).lower() if robots_match else ""
        if indexable and "noindex" in robots:
            page_errors.append("public page is noindex")
        if not indexable and "noindex" not in robots:
            page_errors.append("private or transactional page is indexable")

        if page_errors:
            errors.extend(f"{relative}: {item}" for item in page_errors)
        interfaces.append(
            {
                "id": name,
                "path": relative,
                "indexable": indexable,
                "cspConnectOrigins": sorted(absolute_connect_origins),
                "passed": not page_errors,
            }
        )

    directory_path = root / "specialists-partners/index.html"
    directory_text = read_text(directory_path) if directory_path.is_file() else ""
    missing_directory_markers = [
        marker for marker in REQUIRED_DIRECTORY_MARKERS if marker not in directory_text
    ]
    if missing_directory_markers:
        errors.append(
            "directory quality markers missing: " + ", ".join(missing_directory_markers)
        )
    if directory_text.find("assets/directory-core.js?v=4.1.0") > directory_text.find(
        "assets/sector.js?v=4.1.0"
    ):
        errors.append("directory core must load before sector controller")
    if directory_text.count('class="quality-question"') != 6:
        errors.append("expected exactly six before-booking quality questions")

    core_path = root / "specialists-partners/assets/directory-core.js"
    core_text = read_text(core_path) if core_path.is_file() else ""
    missing_core_markers = [
        marker for marker in REQUIRED_CORE_MARKERS if marker not in core_text
    ]
    if missing_core_markers:
        errors.append("directory core markers missing: " + ", ".join(missing_core_markers))

    providers_path = root / "specialists-partners/data/providers.json"
    ledger_path = root / "specialists-partners/data/verification-ledger.json"
    providers_payload = load_json(providers_path) if providers_path.is_file() else {}
    ledger_payload = load_json(ledger_path) if ledger_path.is_file() else {}
    providers = providers_payload.get("providers", [])
    ledger_records = ledger_payload.get("records", [])
    if not isinstance(providers, list):
        errors.append("providers must be a list")
        providers = []
    if not isinstance(ledger_records, list):
        errors.append("verification ledger records must be a list")
        ledger_records = []

    unsafe_provider_ids: list[str] = []
    ledger_ids = {
        record.get("providerId")
        for record in ledger_records
        if isinstance(record, dict) and record.get("providerId")
    }
    for provider in providers:
        if not isinstance(provider, dict):
            unsafe_provider_ids.append("<invalid-record>")
            continue
        if provider.get("publicationStatus") != "published":
            continue
        provider_id = str(provider.get("id") or "<missing-id>")
        safe = (
            provider.get("verification", {}).get("status") == "verified"
            and provider.get("consent", {}).get("publicProfileApproved") is True
            and provider_id in ledger_ids
        )
        if not safe:
            unsafe_provider_ids.append(provider_id)
    if unsafe_provider_ids:
        errors.append(
            "published providers without complete public proof: "
            + ", ".join(unsafe_provider_ids)
        )

    workflow_path = root / ".github/workflows/audit-specialist-sector-e2e-v9.yml"
    workflow_safety: dict[str, Any]
    if workflow_path.is_file():
        workflow = read_text(workflow_path)
        forbidden = (
            "owner-password-reset",
            "providerMessageId",
            "contents: write",
            "git push",
        )
        present = [marker for marker in forbidden if marker in workflow]
        required = (
            "audit_specialist_sector_e2e_v10.py",
            "SPECIALISTS_ADMIN_API_KEY",
            "upload-artifact@v4",
        )
        missing = [marker for marker in required if marker not in workflow]
        if present:
            errors.append("unsafe live-audit markers present: " + ", ".join(present))
        if missing:
            errors.append("live-audit markers missing: " + ", ".join(missing))
        workflow_safety = {
            "checked": True,
            "passed": not present and not missing,
            "forbiddenMarkersFound": present,
        }
    else:
        workflow_safety = {
            "checked": False,
            "passed": None,
            "reason": "workflow source is not part of the rendered site",
        }

    return {
        "schemaVersion": 1,
        "version": VERSION,
        "status": "passed" if not errors else "failed",
        "reviewedAt": reviewed_at(),
        "sector": "specialists-partners",
        "interfaces": interfaces,
        "interfaceCount": len(interfaces),
        "indexableInterfaceCount": sum(
            1 for item in interfaces if item.get("indexable") is True
        ),
        "privateInterfaceCount": sum(
            1 for item in interfaces if item.get("indexable") is False
        ),
        "publishedProviderCount": sum(
            1
            for provider in providers
            if isinstance(provider, dict)
            and provider.get("publicationStatus") == "published"
        ),
        "verificationLedgerRecordCount": len(ledger_records),
        "unsafePublishedProviderIds": unsafe_provider_ids,
        "directoryCore": {
            "present": core_path.is_file(),
            "missingMarkers": missing_core_markers,
        },
        "qualityQuestions": directory_text.count('class="quality-question"'),
        "workflowSafety": workflow_safety,
        "errors": errors,
        "errorCount": len(errors),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--output",
        help="Output path; defaults to <root>/api/specialists-partners-quality-v354.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    output = (
        Path(args.output).resolve()
        if args.output
        else root / "api/specialists-partners-quality-v354.json"
    )
    report = audit(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
