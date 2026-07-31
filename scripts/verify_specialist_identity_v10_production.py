#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get(
    "ACCOUNT_API_BASE",
    "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev",
).rstrip("/")
ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
OUTPUT = os.environ.get("GITHUB_OUTPUT", "")
EXPECTED_VERSION = "10.3.0"
PROBE_USER_AGENT = "pterminology-specialist-deploy-verifier/10.3"
REQUIRED_CHECKS = (
    "database",
    "identitySchema",
    "turnstile",
    "sessionBinding",
    "singleActiveResetLink",
    "truthfulAdminDelivery",
    "manualRecovery",
    "corsPreflight",
    "strictPasswordPolicy",
    "accountPasswordPolicy",
    "protectedDeepHealth",
    "adminProviderStatus",
)
ALLOWED_PROVIDER_CODES = {
    "ready",
    "ready_sending_only",
    "invalid_api_key",
    "authentication_failed",
    "rate_limited",
    "provider_unavailable",
    "provider_rejected",
    "provider_unreachable",
}


def request_json(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{BASE}{path}",
        headers={
            "accept": "application/json",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "user-agent": PROBE_USER_AGENT,
            **(headers or {}),
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read()
    except Exception as error:
        return 0, {"error": "request_failed", "detail": type(error).__name__}
    try:
        value = json.loads(raw.decode("utf-8"))
        return status, value if isinstance(value, dict) else {}
    except Exception:
        return status, {"error": "invalid_json"}


def normal_ok(status: int, data: dict) -> bool:
    checks = data.get("checks") or {}
    return (
        status == 200
        and data.get("ok") is True
        and data.get("version") == EXPECTED_VERSION
        and all(checks.get(name) is True for name in REQUIRED_CHECKS)
    )


def public_deep_ok(status: int, data: dict) -> bool:
    return status == 403 and data.get("error") == "forbidden"


def protected_deep_ok(status: int, data: dict) -> bool:
    provider = data.get("emailProvider") or {}
    return (
        status in {200, 503}
        and data.get("version") == EXPECTED_VERSION
        and provider.get("configured") is True
        and provider.get("code") in ALLOWED_PROVIDER_CODES
    )


def safe_state(status: int, data: dict) -> str:
    provider = data.get("emailProvider") or {}
    return json.dumps(
        {
            "status": status,
            "version": data.get("version"),
            "ok": data.get("ok"),
            "error": data.get("error"),
            "provider_code": provider.get("code"),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def main() -> int:
    if not ADMIN_KEY:
        print("::error::SPECIALISTS_ADMIN_API_KEY is required", file=sys.stderr)
        return 1

    stable = 0
    latest_normal: dict = {}
    latest_deep: dict = {}
    latest_deep_status = 0

    # A connected Cloudflare build can overlap the audited direct deployment.
    # Require the same public and protected contracts to pass three times.
    for attempt in range(1, 241):
        nonce = f"{RUN_ID}-{attempt}-{time.time_ns()}"
        normal_status, normal = request_json(f"/health?release={EXPECTED_VERSION}&probe={nonce}")
        public_status, public = request_json(f"/health?deep=1&public={nonce}")
        deep_status, deep = request_json(
            f"/health?deep=1&release={EXPECTED_VERSION}&probe={nonce}",
            {"x-bootstrap-key": ADMIN_KEY},
        )

        cycle_ok = (
            normal_ok(normal_status, normal)
            and public_deep_ok(public_status, public)
            and protected_deep_ok(deep_status, deep)
        )
        if cycle_ok:
            stable += 1
            latest_normal = normal
            latest_deep = deep
            latest_deep_status = deep_status
            print(f"Propagation cycle {attempt}: stable {stable}/3")
            if stable >= 3:
                break
            time.sleep(3)
        else:
            stable = 0
            print(
                "Propagation cycle "
                f"{attempt}: waiting; normal={safe_state(normal_status, normal)}; "
                f"public={safe_state(public_status, public)}; "
                f"protected={safe_state(deep_status, deep)}"
            )
            time.sleep(5)

    if stable < 3:
        print(f"::error::Specialist identity {EXPECTED_VERSION} did not become stable across all contracts", file=sys.stderr)
        return 1

    Path("/tmp/identity-health.json").write_text(
        json.dumps(latest_normal, ensure_ascii=False), encoding="utf-8"
    )
    Path("/tmp/identity-deep-health.json").write_text(
        json.dumps(latest_deep, ensure_ascii=False), encoding="utf-8"
    )
    if OUTPUT:
        with open(OUTPUT, "a", encoding="utf-8") as output:
            output.write(f"deep_status={latest_deep_status}\n")
    print(f"Specialist identity {EXPECTED_VERSION} is stable across public and protected contracts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
