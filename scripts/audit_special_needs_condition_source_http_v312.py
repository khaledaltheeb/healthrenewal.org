#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONDITION_FILES = (
    ROOT / "content" / "v302" / "autism-ar.json",
    ROOT / "content" / "v302" / "down-syndrome-ar.json",
)
OVERRIDE_FILE = ROOT / "content" / "v312" / "special-needs-condition-source-url-overrides.json"
VERSION = 312
HEALTHY_STATUSES = set(range(200, 400))
RESTRICTED_STATUSES = {401, 403, 405, 406, 407, 418, 425, 429}
BROKEN_STATUSES = {404, 410}
LEGAL_RESTRICTION_STATUSES = {451}
USER_AGENT = (
    "Mozilla/5.0 (compatible; PTerminologySourceAudit/312; "
    "+https://healthrenewal.org/)"
)


@dataclass(frozen=True)
class Attempt:
    method: str
    status: int | None
    final_url: str | None
    content_type: str | None
    elapsed_ms: int
    error: str | None


@dataclass(frozen=True)
class SourceProbe:
    condition: str
    source_id: str
    organization: str
    title: str
    original_url: str
    classification: str
    blocking: bool
    reason: str
    attempts: tuple[Attempt, ...]


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def normalized_host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_organization_domain(organization: str, old_url: str, new_url: str) -> bool:
    """Allow an explicitly verified official subdomain without allowing a third party."""
    old_host = normalized_host(old_url)
    new_host = normalized_host(new_url)
    if not old_host or not new_host:
        return False
    if old_host == new_host:
        return True
    if organization == "ASHA":
        return (
            (old_host == "asha.org" or old_host.endswith(".asha.org"))
            and (new_host == "asha.org" or new_host.endswith(".asha.org"))
        )
    return False


def load_url_overrides() -> dict[str, dict[str, str]]:
    data = read_json(OVERRIDE_FILE)
    overrides = data.get("overrides")
    if data.get("version") != VERSION or data.get("language") != "ar" or not isinstance(overrides, dict):
        raise SystemExit("Source URL override contract failed")

    result: dict[str, dict[str, str]] = {}
    for source_id, item in overrides.items():
        if not isinstance(item, dict):
            raise SystemExit(f"Source URL override must be an object: {source_id}")
        required = ("from", "to", "title", "organization", "reason", "verification_method")
        missing = [key for key in required if not str(item.get(key, "")).strip()]
        if missing:
            raise SystemExit(f"Source URL override is incomplete: {source_id}/{missing}")

        old = str(item["from"])
        new = str(item["to"])
        organization = str(item["organization"])
        if (
            urlparse(old).scheme != "https"
            or urlparse(new).scheme != "https"
            or not is_organization_domain(organization, old, new)
        ):
            raise SystemExit(
                f"Source URL override must remain on the same verified HTTPS official domain family: {source_id}"
            )
        result[str(source_id)] = {key: str(item[key]) for key in required}
    return result


def load_sources() -> list[dict[str, str]]:
    overrides = load_url_overrides()
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    applied_overrides: set[str] = set()

    for path in CONDITION_FILES:
        payload = read_json(path)
        slug = str(payload.get("slug", "")).strip()
        sources = payload.get("sources")
        if slug not in {"autism", "down-syndrome"} or not isinstance(sources, list):
            raise SystemExit(f"Invalid condition source file: {path}")

        for source in sources:
            if not isinstance(source, dict):
                raise SystemExit(f"Source entries must be objects: {path}")
            source_id = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            organization = str(source.get("organization", "")).strip()
            title = str(source.get("title", "")).strip()
            if not all((source_id, url, organization, title)):
                raise SystemExit(f"Incomplete source row: {slug}/{source_id}")

            override = overrides.get(source_id)
            if override:
                if url != override["from"]:
                    raise SystemExit(f"Source URL override no longer matches its declared original: {source_id}")
                if organization != override["organization"]:
                    raise SystemExit(f"Source URL override organization mismatch: {source_id}")
                url = override["to"]
                title = override["title"]
                applied_overrides.add(source_id)

            if source_id in seen_ids:
                raise SystemExit(f"Duplicate source id across condition pages: {source_id}")
            pair = (slug, url)
            if pair in seen_pairs:
                raise SystemExit(f"Duplicate source URL inside condition: {slug}/{url}")
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise SystemExit(f"External source URL must use HTTPS: {slug}/{source_id}/{url}")

            seen_ids.add(source_id)
            seen_pairs.add(pair)
            rows.append(
                {
                    "condition": slug,
                    "source_id": source_id,
                    "organization": organization,
                    "title": title,
                    "url": url,
                }
            )

    unused_overrides = sorted(set(overrides) - applied_overrides)
    if unused_overrides:
        raise SystemExit(f"Unused source URL overrides must be removed: {unused_overrides}")
    return sorted(rows, key=lambda row: (row["condition"], row["source_id"]))


def _attempt(url: str, method: str, timeout: float) -> Attempt:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json,application/pdf;q=0.9,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.8,ar;q=0.6",
        "Cache-Control": "no-cache",
    }
    # Read only the first bytes from a normal GET. Some official CDNs return a
    # false 404 for Range requests even though the ordinary public page works.
    request = urllib.request.Request(url, headers=headers, method=method)
    started = time.monotonic()
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            if method == "GET":
                response.read(4096)
            elapsed = round((time.monotonic() - started) * 1000)
            return Attempt(
                method=method,
                status=int(response.status),
                final_url=response.geturl(),
                content_type=response.headers.get_content_type(),
                elapsed_ms=elapsed,
                error=None,
            )
    except urllib.error.HTTPError as exc:
        elapsed = round((time.monotonic() - started) * 1000)
        return Attempt(
            method=method,
            status=int(exc.code),
            final_url=exc.geturl(),
            content_type=exc.headers.get_content_type() if exc.headers else None,
            elapsed_ms=elapsed,
            error=f"HTTP {exc.code}",
        )
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        elapsed = round((time.monotonic() - started) * 1000)
        reason = getattr(exc, "reason", exc)
        return Attempt(
            method=method,
            status=None,
            final_url=None,
            content_type=None,
            elapsed_ms=elapsed,
            error=f"{type(reason).__name__}: {reason}",
        )


def classify_attempts(attempts: list[Attempt]) -> tuple[str, bool, str]:
    if not attempts:
        return "indeterminate", False, "no-attempts"

    for attempt in attempts:
        if attempt.final_url and urlparse(attempt.final_url).scheme.lower() != "https":
            return "insecure-redirect", True, f"redirected-to-non-https:{attempt.final_url}"

    successful = [attempt for attempt in attempts if attempt.status in HEALTHY_STATUSES]
    if successful:
        status = successful[-1].status
        return "reachable", False, f"http-{status}"

    get_attempts = [attempt for attempt in attempts if attempt.method == "GET"]
    decisive = get_attempts[-1] if get_attempts else attempts[-1]
    status = decisive.status
    if status in BROKEN_STATUSES:
        return "broken", True, f"http-{status}"
    if status in LEGAL_RESTRICTION_STATUSES:
        return "legally-restricted", False, f"http-{status}"
    if status in RESTRICTED_STATUSES:
        return "access-restricted", False, f"http-{status}"
    if status is not None and 500 <= status <= 599:
        return "server-error", False, f"http-{status}"
    if status is not None:
        return "unexpected-http-status", False, f"http-{status}"
    return "transport-indeterminate", False, decisive.error or "transport-error"


def probe_source(row: dict[str, str], timeout: float) -> SourceProbe:
    attempts = [_attempt(row["url"], "HEAD", timeout)]
    if attempts[0].status not in HEALTHY_STATUSES:
        attempts.append(_attempt(row["url"], "GET", timeout))
        if attempts[-1].status is None:
            attempts.append(_attempt(row["url"], "GET", timeout))
    classification, blocking, reason = classify_attempts(attempts)
    return SourceProbe(
        condition=row["condition"],
        source_id=row["source_id"],
        organization=row["organization"],
        title=row["title"],
        original_url=row["url"],
        classification=classification,
        blocking=blocking,
        reason=reason,
        attempts=tuple(attempts),
    )


def audit(timeout: float = 18.0, workers: int = 4) -> dict[str, Any]:
    rows = load_sources()
    results: list[SourceProbe] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(probe_source, row, timeout): row for row in rows}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    SourceProbe(
                        condition=row["condition"],
                        source_id=row["source_id"],
                        organization=row["organization"],
                        title=row["title"],
                        original_url=row["url"],
                        classification="probe-exception",
                        blocking=False,
                        reason=f"{type(exc).__name__}: {exc}",
                        attempts=(),
                    )
                )

    results.sort(key=lambda result: (result.condition, result.source_id))
    counts: dict[str, int] = {}
    for result in results:
        counts[result.classification] = counts.get(result.classification, 0) + 1
    blocking = [result.source_id for result in results if result.blocking]
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    override_count = len(load_url_overrides())
    return {
        "version": VERSION,
        "status": "failed" if blocking else "passed-with-observations",
        "checked_at": checked_at,
        "check_type": "live-http",
        "condition_count": len({row["condition"] for row in rows}),
        "source_count": len(rows),
        "source_url_override_count": override_count,
        "source_url_override_source": OVERRIDE_FILE.relative_to(ROOT).as_posix(),
        "blocking_count": len(blocking),
        "blocking_source_ids": blocking,
        "classification_counts": dict(sorted(counts.items())),
        "policy": {
            "blocking": ["broken-404", "broken-410", "redirect-to-non-https"],
            "non_blocking_observations": [
                "access-restricted",
                "legally-restricted",
                "server-error",
                "unexpected-http-status",
                "transport-indeterminate",
                "probe-exception",
            ],
            "note": "Bot blocking, rate limiting, server errors and transient transport failures are reported but do not automatically invalidate an authoritative source.",
        },
        "results": [
            {
                **{key: value for key, value in asdict(result).items() if key != "attempts"},
                "attempts": [asdict(attempt) for attempt in result.attempts],
            }
            for result in results
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "_audit" / "special-needs-condition-source-http-v312.json",
    )
    parser.add_argument("--timeout", type=float, default=18.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--fail-on-broken", action="store_true")
    args = parser.parse_args()
    report = audit(timeout=max(2.0, args.timeout), workers=max(1, args.workers))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_on_broken and report["blocking_count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
