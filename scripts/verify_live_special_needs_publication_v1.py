#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://healthrenewal.org"
INVENTORY_ROUTE = "/api/special-needs-publication-inventory-v1.json"
MINIMUM_COUNTS: dict[str, int] = {
    "capability_pages": 155,
    "capability_condition_pages": 150,
    "special_needs_practical_guides": 60,
    "family_condition_guides": 64,
    "family_tools": 15,
    "learning_paths": 15,
    "child_guides": 10,
    "family_guides": 8,
    "home_guides": 7,
}
REQUIRED_ROOT_ROUTES = (
    "/special-needs/",
    "/family-guide/",
    "/family-guide/tools/",
    "/learning-paths/",
    "/capabilities/",
    "/capabilities/registry/",
    "/capabilities/expanded/",
)
SOFT_404_MARKERS = (
    "404 not found",
    "page not found",
    "الصفحة غير موجودة",
    "الصفحة المطلوبة غير موجودة",
)


class PageContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.canonicals: list[str] = []
        self.noindex = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): (value or "").strip() for name, value in attrs}
        lowered = tag.lower()
        if lowered == "h1":
            self.h1_count += 1
        elif lowered == "link":
            rel = {token.lower() for token in values.get("rel", "").split()}
            if "canonical" in rel and values.get("href"):
                self.canonicals.append(values["href"])
        elif lowered == "meta" and values.get("name", "").lower() == "robots":
            self.noindex = "noindex" in values.get("content", "").lower()


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    body: bytes
    content_type: str


def cache_busted(url: str, nonce: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["publication-proof"] = nonce
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def fetch(
    url: str,
    *,
    timeout: float,
    retries: int,
    max_bytes: int = 768 * 1024,
) -> FetchResult:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request_url = cache_busted(url, f"{time.time_ns()}-{attempt}")
        request = Request(
            request_url,
            headers={
                "User-Agent": "RawafidPublicationProof/1.0 (+https://healthrenewal.org/)",
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.5",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                status = int(getattr(response, "status", response.getcode()))
                body = response.read(max_bytes)
                return FetchResult(
                    url=url,
                    status=status,
                    body=body,
                    content_type=response.headers.get("Content-Type", ""),
                )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 ** (attempt - 1), 4))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def validate_inventory(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if payload.get("status") != "passed":
        problems.append(f"inventory status is {payload.get('status')!r}, expected 'passed'")

    counts = payload.get("counts")
    if not isinstance(counts, dict):
        return [*problems, "inventory counts are missing or invalid"]

    for name, minimum in MINIMUM_COUNTS.items():
        actual = counts.get(name)
        if not isinstance(actual, int) or actual < minimum:
            problems.append(f"{name}: {actual!r} < {minimum}")

    for field in ("missingRoots", "pageIssues", "sitemapMissingRoutes"):
        value = payload.get(field)
        if value not in ([], {}):
            problems.append(f"{field} is not empty")
    return problems


def inventory_routes(payload: dict[str, Any]) -> list[str]:
    routes_payload = payload.get("routes")
    if not isinstance(routes_payload, dict):
        raise ValueError("inventory routes are missing or invalid")

    routes = set(REQUIRED_ROOT_ROUTES)
    for group, values in routes_payload.items():
        if not isinstance(values, list):
            raise ValueError(f"route group {group!r} is not a list")
        for route in values:
            if not isinstance(route, str) or not route.startswith("/") or not route.endswith("/"):
                raise ValueError(f"invalid route in {group!r}: {route!r}")
            routes.add(route)
    return sorted(routes)


def validate_live_page(base_url: str, route: str, *, timeout: float, retries: int) -> dict[str, Any] | None:
    expected_url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
    try:
        result = fetch(expected_url, timeout=timeout, retries=retries)
    except RuntimeError as exc:
        return {"route": route, "problems": [str(exc)]}

    problems: list[str] = []
    if result.status != 200:
        problems.append(f"HTTP {result.status}")

    text = result.body.decode("utf-8", errors="ignore")
    lowered = text.lower()
    for marker in SOFT_404_MARKERS:
        if marker in lowered:
            problems.append(f"soft 404 marker: {marker}")
            break

    parser = PageContractParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # pragma: no cover - defensive against malformed live HTML
        problems.append(f"HTML parse failure: {exc}")

    if parser.h1_count == 0:
        problems.append("missing h1")
    if parser.noindex:
        problems.append("noindex")

    expected_canonical = expected_url.rstrip("/")
    canonicals = {value.rstrip("/") for value in parser.canonicals}
    if expected_canonical not in canonicals:
        problems.append(f"canonical mismatch: {sorted(canonicals)!r}")
    if len(canonicals) > 1:
        problems.append(f"conflicting canonicals: {sorted(canonicals)!r}")

    if problems:
        return {
            "route": route,
            "url": expected_url,
            "status": result.status,
            "contentType": result.content_type,
            "problems": problems,
        }
    return None


def run(base_url: str, *, timeout: float, retries: int, workers: int) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    inventory_url = urljoin(base_url + "/", INVENTORY_ROUTE.lstrip("/"))
    inventory_result = fetch(inventory_url, timeout=timeout, retries=retries)
    try:
        payload = json.loads(inventory_result.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit({"invalid_live_inventory_json": str(exc), "url": inventory_url}) from exc
    if not isinstance(payload, dict):
        raise SystemExit({"invalid_live_inventory_payload": type(payload).__name__})

    inventory_problems = validate_inventory(payload)
    if inventory_problems:
        raise SystemExit({"live_inventory_contract_failed": inventory_problems})

    routes = inventory_routes(payload)
    target_route_count = payload.get("targetRouteCount")
    if isinstance(target_route_count, int) and len(routes) < target_route_count:
        raise SystemExit(
            {
                "route_inventory_incomplete": {
                    "unique_routes": len(routes),
                    "target_route_count": target_route_count,
                }
            }
        )

    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                validate_live_page,
                base_url,
                route,
                timeout=timeout,
                retries=retries,
            ): route
            for route in routes
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                failures.append(result)

    failures.sort(key=lambda item: item["route"])
    report = {
        "schemaVersion": 1,
        "status": "passed" if not failures else "failed",
        "baseUrl": base_url,
        "inventoryUrl": inventory_url,
        "counts": payload["counts"],
        "targetRouteCount": target_route_count,
        "verifiedUniqueRoutes": len(routes),
        "failedRoutes": len(failures),
        "failures": failures[:50],
    }
    if failures:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that every special-needs publication route is live and indexable."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    report = run(
        args.base_url,
        timeout=args.timeout,
        retries=max(1, args.retries),
        workers=max(1, args.workers),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
