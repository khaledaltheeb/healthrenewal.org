#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

VERSION = 322
BASE_PATH = "/"
TECHNICAL = {
    ".well-known", "assets", "css", "downloads", "fonts", "images", "js",
    "media", "node_modules", "scripts", "sections", "styles", "coverage",
    "reports", "tmp", "api",
}
REQUIRED_HOME_ROUTES = {
    "start-here/", "encyclopedia/", "terms/", "hubs/", "comparisons/",
    "library/", "magazine/", "outside-the-box/", "care-guides/", "tips/",
    "special-needs/", "sectors/", "guided-assessment/", "assessments/",
    "assessment-lab/", "cognitive-tests/", "cognitive-lab/", "daily-tools/",
    "learning-paths/", "provider-assessment-demo/", "specialists-partners/",
    "partners/", "trust/", "developers/", "api/", "platform/", "copyright/",
    "sections/", "en/", "es/",
}


class PublicationSurfaceError(AssertionError):
    pass


def read(path: Path) -> str:
    if not path.is_file():
        raise PublicationSurfaceError(f"missing required file: {path.as_posix()}")
    return path.read_text(encoding="utf-8")


def is_noindex(source: str) -> bool:
    for tag in re.findall(r"<meta\b[^>]*>", source, flags=re.I | re.S):
        if re.search(r'name\s*=\s*(["\'])robots\1', tag, flags=re.I) and re.search(
            r'content\s*=\s*(["\'])[^"\']*noindex[^"\']*\1', tag, flags=re.I
        ):
            return True
    return False


def top_level_routes(site: Path) -> tuple[set[str], set[str]]:
    public: set[str] = set()
    noindex: set[str] = set()
    for entry in site.iterdir():
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in TECHNICAL:
            continue
        index = entry / "index.html"
        if not index.is_file():
            continue
        route = entry.name + "/"
        if is_noindex(read(index)):
            noindex.add(route)
        else:
            public.add(route)
    # API is a deliberate public top-level route although its directory contains data files.
    if (site / "api/index.html").is_file() and not is_noindex(read(site / "api/index.html")):
        public.add("api/")
    return public, noindex


def normalize_internal_href(value: str) -> str | None:
    value = unescape(value).strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parts = urlsplit(value)
    if parts.scheme and parts.scheme not in {"http", "https"}:
        return None
    if parts.netloc and parts.netloc != "khaledaltheeb.github.io":
        return None
    path = parts.path
    if path.startswith(BASE_PATH):
        path = path[len(BASE_PATH):]
    elif path.startswith("/"):
        return None
    path = path.lstrip("./")
    if not path:
        return ""
    return path


def homepage_links(source: str) -> set[str]:
    output: set[str] = set()
    for value in re.findall(r'<a\b[^>]*\bhref\s*=\s*(["\'])(.*?)\1', source, flags=re.I | re.S):
        normalized = normalize_internal_href(value[1])
        if normalized is not None:
            output.add(normalized)
    return output


def route_is_linked(route: str, links: set[str]) -> bool:
    route = route.strip("/") + "/"
    return any(
        candidate == route
        or candidate == route + "index.html"
        or candidate.startswith(route + "?")
        for candidate in links
    )


def resolve_link(site: Path, value: str) -> Path:
    clean = value.split("?", 1)[0].split("#", 1)[0]
    if clean == "":
        return site / "index.html"
    candidate = site / clean
    if clean.endswith("/"):
        return candidate / "index.html"
    if candidate.is_dir():
        return candidate / "index.html"
    return candidate


def audit(site: Path, *, fail: bool = True) -> dict[str, Any]:
    site = site.resolve()
    home_source = read(site / "index.html")
    directory_source = read(site / "sections/index.html")
    api_payload = json.loads(read(site / "api/v1/section-directory.json"))
    if not isinstance(api_payload, dict) or not isinstance(api_payload.get("items"), list):
        raise PublicationSurfaceError("invalid section-directory API")

    public_routes, noindex_routes = top_level_routes(site)
    directory_routes = {
        item.get("route") for item in api_payload["items"]
        if isinstance(item, dict) and isinstance(item.get("route"), str)
    }
    links = homepage_links(home_source)
    direct_home_routes = {route for route in public_routes if route_is_linked(route, links)}
    directory_only_routes = public_routes - direct_home_routes
    missing_from_directory = public_routes - directory_routes
    stale_directory_routes = directory_routes - public_routes
    missing_critical_home = {
        route for route in REQUIRED_HOME_ROUTES if not route_is_linked(route, links)
    }

    broken_home_links: list[str] = []
    for value in sorted(links):
        if value.startswith(("http://", "https://")):
            continue
        target = resolve_link(site, value)
        if not target.exists():
            broken_home_links.append(value)

    errors: list[str] = []
    if missing_from_directory:
        errors.append(f"public routes missing from directory: {sorted(missing_from_directory)}")
    if stale_directory_routes:
        errors.append(f"directory routes without public index: {sorted(stale_directory_routes)}")
    if missing_critical_home:
        errors.append(f"critical routes missing from homepage: {sorted(missing_critical_home)}")
    if broken_home_links:
        errors.append(f"broken homepage links: {broken_home_links}")
    if "specialists-partners/" not in directory_routes:
        errors.append("specialists-partners route is not registered")
    if 'data-publication-surface="v322"' not in home_source:
        errors.append("homepage v322 marker is missing")
    if "specialists-partners/" not in directory_source:
        errors.append("specialists-partners link is absent from HTML directory")

    html_pages = sorted(site.rglob("*.html"))
    public_pages = 0
    noindex_pages = 0
    for page in html_pages:
        source = read(page)
        if is_noindex(source):
            noindex_pages += 1
        else:
            public_pages += 1

    report = {
        "schema_version": VERSION,
        "status": "failed" if errors else "passed",
        "site": site.as_posix(),
        "html_pages": len(html_pages),
        "public_html_pages": public_pages,
        "noindex_html_pages": noindex_pages,
        "public_top_level_routes": len(public_routes),
        "directory_routes": len(directory_routes),
        "homepage_direct_routes": len(direct_home_routes),
        "directory_only_routes": sorted(directory_only_routes),
        "noindex_top_level_routes": sorted(noindex_routes),
        "missing_from_directory": sorted(missing_from_directory),
        "stale_directory_routes": sorted(stale_directory_routes),
        "missing_critical_home": sorted(missing_critical_home),
        "broken_home_links": broken_home_links,
        "specialists_partners_visible": (
            "specialists-partners/" in directory_routes
            and route_is_linked("specialists-partners/", links)
        ),
        "errors": errors,
    }

    output = site / "api/publication-surface-v322.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if fail and errors:
        raise PublicationSurfaceError("; ".join(errors))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit discoverability of every published top-level section")
    parser.add_argument("site", nargs="?", default="_site")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()
    report = audit(Path(args.site), fail=not args.no_fail)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
