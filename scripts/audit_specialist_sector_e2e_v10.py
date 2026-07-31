#!/usr/bin/env python3
"""Read-only production audit for specialist pages, registries, APIs, and CORS."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_IDENTITY_VERSION = "10.2.0"
ORIGIN = "https://healthrenewal.org"
READY_PROVIDER_CODES = {"ready", "ready_sending_only"}
ALLOWED_PROVIDER_CODES = READY_PROVIDER_CODES | {
    "invalid_api_key",
    "authentication_failed",
    "rate_limited",
    "provider_unavailable",
    "provider_rejected",
    "provider_unreachable",
}

PAGE_MARKERS = {
    "directory": ("", ('data-specialists-quality-v354="1"', "directory-health")),
    "join": ("join.html", ('id="onboarding-form"',)),
    "contact": ("contact.html", ('id="contact-form"',)),
    "verification": ("verification.html", ("التحقق",)),
    "portal": ("portal/", ("المحادثة",)),
    "account": ("account/", ("حساب المختص",)),
    "admin": ("admin/", ('id="admin-forgot"',)),
    "recover": ("recover/", ("استعادة الحساب",)),
    "password_reset": (
        "password-reset/",
        ("هذه صفحة مستقلة وآمنة", "reset-v10.js?v=10.2.0"),
    ),
}

ASSET_MARKERS = {
    "directory_core": (
        "assets/directory-core.js",
        ("normalizeArabic", "ageMatches", "specialtyAny"),
    ),
    "directory_controller": (
        "assets/sector.js",
        ("live-verified-registry", "core.prepareProviders", "state.matchCriteria"),
    ),
    "runtime_config": (
        "assets/runtime-config.js",
        ('identityVersion: "10.2.0"', "pterminology-specialists"),
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def with_nonce(url: str, nonce: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}audit={urllib.parse.quote(nonce)}"


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, str], bytes, str | None]:
    request_headers = {
        "accept": "application/json,text/html;q=0.9,*/*;q=0.1",
        "cache-control": "no-cache",
        "user-agent": "pterminology-specialist-read-only-audit/10.2",
        **(headers or {}),
    }
    req = urllib.request.Request(
        url,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return (
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
                None,
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            {key.lower(): value for key, value in error.headers.items()},
            error.read(),
            None,
        )
    except Exception as error:
        return 0, {}, b"", type(error).__name__


def decode_text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def decode_json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(decode_text(raw))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def page_checks(site_base: str, nonce: str) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, (path, markers) in PAGE_MARKERS.items():
        status, _, raw, error = request(with_nonce(f"{site_base}/{path}", nonce))
        body = decode_text(raw)
        marker_state = {marker: marker in body for marker in markers}
        checks[name] = {
            "httpStatus": status,
            "markers": marker_state,
            "passed": status == 200 and all(marker_state.values()) and error is None,
            "networkError": error,
        }
    return checks


def asset_checks(site_base: str, nonce: str) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, (path, markers) in ASSET_MARKERS.items():
        status, _, raw, error = request(with_nonce(f"{site_base}/{path}", nonce))
        body = decode_text(raw)
        marker_state = {marker: marker in body for marker in markers}
        checks[name] = {
            "httpStatus": status,
            "markers": marker_state,
            "passed": status == 200 and all(marker_state.values()) and error is None,
            "networkError": error,
        }
    return checks


def health_check(base: str, nonce: str) -> tuple[int, dict[str, Any], str | None]:
    status, _, raw, error = request(with_nonce(f"{base}/health", nonce))
    return status, decode_json(raw), error


def cors_check(url: str, nonce: str) -> dict[str, Any]:
    status, headers, _, error = request(
        with_nonce(url, nonce),
        method="OPTIONS",
        headers={
            "origin": ORIGIN,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type,x-requested-with",
        },
    )
    allow_origin = headers.get("access-control-allow-origin", "")
    allow_methods = headers.get("access-control-allow-methods", "")
    return {
        "httpStatus": status,
        "allowOrigin": allow_origin,
        "allowsPost": "POST" in allow_methods.upper(),
        "passed": status in {200, 204}
        and allow_origin in {ORIGIN, "*"}
        and "POST" in allow_methods.upper()
        and error is None,
        "networkError": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site-base",
        default=os.environ.get(
            "SITE_BASE",
            "https://healthrenewal.org/specialists-partners",
        ),
    )
    parser.add_argument(
        "--identity-api",
        default=os.environ.get(
            "IDENTITY_API",
            "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev",
        ),
    )
    parser.add_argument(
        "--core-api",
        default=os.environ.get(
            "CORE_API",
            "https://pterminology-specialists.pterminology-826ac349.workers.dev",
        ),
    )
    parser.add_argument(
        "--output",
        default=os.environ.get(
            "AUDIT_OUTPUT", "/tmp/specialist-sector-e2e-v10.json"
        ),
    )
    args = parser.parse_args()

    site_base = args.site_base.rstrip("/")
    identity_api = args.identity_api.rstrip("/")
    core_api = args.core_api.rstrip("/")
    nonce = f"{os.environ.get('GITHUB_RUN_ID', 'local')}-{time.time_ns()}"

    pages = page_checks(site_base, nonce)
    assets = asset_checks(site_base, nonce)

    identity_status, identity, identity_error = health_check(identity_api, nonce)
    identity_checks = identity.get("checks") or {}
    identity_passed = (
        identity_status == 200
        and identity.get("ok") is True
        and identity.get("version") == EXPECTED_IDENTITY_VERSION
        and identity_checks.get("protectedDeepHealth") is True
        and identity_error is None
    )

    public_deep_status, _, public_deep_raw, public_deep_error = request(
        with_nonce(f"{identity_api}/health?deep=1", nonce)
    )
    public_deep = decode_json(public_deep_raw)
    public_deep_passed = (
        public_deep_status == 403
        and public_deep.get("error") == "forbidden"
        and public_deep_error is None
    )

    admin_key = (
        os.environ.get("SPECIALISTS_ADMIN_API_KEY")
        or os.environ.get("ADMIN_API_KEY")
        or ""
    )
    protected_deep: dict[str, Any] = {
        "checked": False,
        "httpStatus": None,
        "providerConfigured": None,
        "providerCode": None,
        "providerReady": None,
        "passed": None,
    }
    if admin_key:
        deep_status, _, deep_raw, deep_error = request(
            with_nonce(f"{identity_api}/health?deep=1", nonce),
            headers={"x-bootstrap-key": admin_key},
        )
        deep = decode_json(deep_raw)
        provider = deep.get("emailProvider") or {}
        provider_code = provider.get("code")
        protected_deep = {
            "checked": True,
            "httpStatus": deep_status,
            "version": deep.get("version"),
            "providerConfigured": provider.get("configured"),
            "providerCode": provider_code,
            "providerReady": provider_code in READY_PROVIDER_CODES,
            "passed": deep_status in {200, 503}
            and deep.get("version") == EXPECTED_IDENTITY_VERSION
            and provider.get("configured") is True
            and provider_code in ALLOWED_PROVIDER_CODES
            and deep_error is None,
            "networkError": deep_error,
        }

    core_status, core, core_error = health_check(core_api, nonce)
    core_passed = (
        core_status == 200 and core.get("ok") is True and core_error is None
    )

    registry_status, _, registry_raw, registry_error = request(
        with_nonce(f"{core_api}/v1/providers?limit=250", nonce)
    )
    registry = decode_json(registry_raw)
    live_providers = registry.get("providers")
    live_registry_passed = (
        registry_status == 200
        and isinstance(live_providers, list)
        and registry_error is None
    )

    static_status, _, static_raw, static_error = request(
        with_nonce(f"{site_base}/data/providers.json", nonce)
    )
    static_registry = decode_json(static_raw)
    static_providers = static_registry.get("providers")
    static_registry_passed = (
        static_status == 200
        and isinstance(static_providers, list)
        and static_error is None
    )

    cors = {
        "identityLogin": cors_check(
            f"{identity_api}/v1/auth/password/login", nonce
        ),
        "coreApplication": cors_check(f"{core_api}/v1/applications", nonce),
    }

    functional_without_email = (
        all(item["passed"] for item in pages.values())
        and all(item["passed"] for item in assets.values())
        and identity_passed
        and public_deep_passed
        and core_passed
        and live_registry_passed
        and static_registry_passed
        and all(item["passed"] for item in cors.values())
    )
    fully_operational = (
        functional_without_email
        and protected_deep.get("passed") is True
        and protected_deep.get("providerReady") is True
    )

    report = {
        "schemaVersion": 2,
        "auditVersion": "10.2.0",
        "mode": "read-only",
        "checkedAt": utc_now(),
        "pages": pages,
        "assets": assets,
        "identity": {
            "httpStatus": identity_status,
            "ok": identity.get("ok"),
            "service": identity.get("service"),
            "version": identity.get("version"),
            "requiredChecks": {
                "database": identity_checks.get("database"),
                "identitySchema": identity_checks.get("identitySchema"),
                "protectedDeepHealth": identity_checks.get("protectedDeepHealth"),
                "corsPreflight": identity_checks.get("corsPreflight"),
            },
            "passed": identity_passed,
            "networkError": identity_error,
        },
        "publicDeepHealth": {
            "httpStatus": public_deep_status,
            "error": public_deep.get("error"),
            "passed": public_deep_passed,
            "networkError": public_deep_error,
        },
        "protectedDeepHealth": protected_deep,
        "core": {
            "httpStatus": core_status,
            "ok": core.get("ok"),
            "service": core.get("service"),
            "version": core.get("version"),
            "passed": core_passed,
            "networkError": core_error,
        },
        "registries": {
            "live": {
                "httpStatus": registry_status,
                "providerCount": len(live_providers)
                if isinstance(live_providers, list)
                else None,
                "passed": live_registry_passed,
                "networkError": registry_error,
            },
            "staticFallback": {
                "httpStatus": static_status,
                "providerCount": len(static_providers)
                if isinstance(static_providers, list)
                else None,
                "passed": static_registry_passed,
                "networkError": static_error,
            },
        },
        "cors": cors,
        "functionalWithoutEmail": functional_without_email,
        "fullyOperational": fully_operational,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if functional_without_email else 1


if __name__ == "__main__":
    raise SystemExit(main())
