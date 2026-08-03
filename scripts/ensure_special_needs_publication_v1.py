#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

BASE_URL = "https://healthrenewal.org"
REPORT_PATH = Path("api/special-needs-publication-inventory-v1.json")

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

REQUIRED_ROOTS = (
    "special-needs/index.html",
    "family-guide/index.html",
    "family-guide/tools/index.html",
    "learning-paths/index.html",
    "capabilities/index.html",
    "capabilities/registry/index.html",
    "capabilities/expanded/index.html",
)

CAPABILITY_NON_CONDITION_SLUGS = {"registry", "expanded", "methodology", "sources"}
TARGET_PREFIXES = (
    "/capabilities/",
    "/special-needs/practical/",
    "/family-guide/conditions/",
    "/family-guide/tools/",
    "/learning-paths/",
    "/sectors/child/guides/",
    "/sectors/family/guides/",
    "/sectors/home/guides/",
)


@dataclass(frozen=True)
class Inventory:
    counts: dict[str, int]
    routes: dict[str, list[str]]
    missing_roots: list[str]


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.canonicals: list[str] = []
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        values = {name.lower(): (value or "").strip() for name, value in attrs}
        if lowered == "h1":
            self.h1_count += 1
        elif lowered == "link":
            rel_tokens = {token.lower() for token in values.get("rel", "").split()}
            href = values.get("href", "")
            if "canonical" in rel_tokens and href:
                self.canonicals.append(href)
        elif lowered == "meta" and values.get("name", "").lower() == "robots":
            self.robots.append(values.get("content", "").lower())


def _route_for(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "index.html":
        return "/"
    return "/" + path.parent.relative_to(root).as_posix().strip("/") + "/"


def _index_pages(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.rglob("index.html"))


def collect_inventory(root: Path) -> Inventory:
    root = root.resolve()

    capability_pages = _index_pages(root / "capabilities")
    capability_conditions = [
        path
        for path in capability_pages
        if path.parent != root / "capabilities"
        and path.parent.name not in CAPABILITY_NON_CONDITION_SLUGS
    ]
    practical = sorted((root / "special-needs" / "practical").glob("*/index.html"))
    family_conditions = sorted((root / "family-guide" / "conditions").glob("*/index.html"))
    family_tools = sorted((root / "family-guide" / "tools").glob("*/index.html"))
    learning_paths = sorted((root / "learning-paths").glob("*/index.html"))
    child_guides = sorted((root / "sectors" / "child" / "guides").glob("*/index.html"))
    family_guides = sorted((root / "sectors" / "family" / "guides").glob("*/index.html"))
    home_guides = sorted((root / "sectors" / "home" / "guides").glob("*/index.html"))

    groups = {
        "capability_pages": capability_pages,
        "capability_condition_pages": capability_conditions,
        "special_needs_practical_guides": practical,
        "family_condition_guides": family_conditions,
        "family_tools": family_tools,
        "learning_paths": learning_paths,
        "child_guides": child_guides,
        "family_guides": family_guides,
        "home_guides": home_guides,
    }
    counts = {name: len(paths) for name, paths in groups.items()}
    routes = {name: [_route_for(path, root) for path in paths] for name, paths in groups.items()}
    missing_roots = [relative for relative in REQUIRED_ROOTS if not (root / relative).is_file()]
    return Inventory(counts=counts, routes=routes, missing_roots=missing_roots)


def validate_counts(
    counts: dict[str, int], minimums: dict[str, int] | None = None
) -> dict[str, dict[str, int]]:
    minimums = minimums or MINIMUM_COUNTS
    failures: dict[str, dict[str, int]] = {}
    for name, minimum in minimums.items():
        actual = int(counts.get(name, 0))
        if actual < minimum:
            failures[name] = {"actual": actual, "minimum": minimum}
    return failures


def _run_publisher(repo_root: Path, script_name: str, site_root: Path) -> None:
    script = repo_root / "scripts" / script_name
    if not script.is_file():
        raise SystemExit({"missing_repair_publisher": str(script)})
    subprocess.run(
        [sys.executable, str(script), str(site_root)],
        cwd=repo_root,
        check=True,
    )


def repair_missing_generated_families(root: Path, repo_root: Path) -> dict[str, object]:
    root = root.resolve()
    repo_root = repo_root.resolve()
    before = collect_inventory(root)
    actions: list[str] = []

    # Never materialize generated production families into the source checkout.
    # The canonical Pages workflow passes a separate _site directory here.
    if root != repo_root and before.counts["capability_pages"] < MINIMUM_COUNTS["capability_pages"]:
        _run_publisher(repo_root, "publish_capabilities_v280.py", root)
        actions.append("publish_capabilities_v280.py")
        _run_publisher(repo_root, "publish_conditions_v281.py", root)
        actions.append("publish_conditions_v281.py")

    after = collect_inventory(root)
    return {
        "actions": actions,
        "before": before.counts,
        "after": after.counts,
    }


def _read_sitemap_urls(root: Path) -> set[str]:
    urls: set[str] = set()
    for path in sorted(root.glob("sitemap*.xml")):
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise SystemExit({"invalid_sitemap": str(path), "error": str(exc)}) from exc
        root_tag = tree.getroot().tag.rsplit("}", 1)[-1]
        if root_tag != "urlset":
            continue
        for node in tree.getroot().findall("{*}url/{*}loc"):
            value = (node.text or "").strip()
            if value:
                urls.add(value.rstrip("/") + "/")
    return urls


def _validate_page(path: Path, route: str) -> list[str]:
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["not_utf8"]

    if len(text.encode("utf-8")) < 500:
        problems.append("too_small")

    parser = PageMetadataParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        return [*problems, "invalid_html_parse"]

    if parser.h1_count == 0:
        problems.append("missing_h1")
    if any("noindex" in directive for directive in parser.robots):
        problems.append("noindex")

    expected = (BASE_URL + route).rstrip("/")
    normalized_canonicals = [value.rstrip("/") for value in parser.canonicals]
    if not normalized_canonicals:
        problems.append("missing_canonical")
    elif expected not in normalized_canonicals:
        problems.append("canonical_mismatch")
    if len(set(normalized_canonicals)) > 1:
        problems.append("conflicting_canonicals")

    return problems


def validate_publication_inventory(
    root: Path,
    *,
    repair: dict[str, object] | None = None,
) -> dict[str, object]:
    root = root.resolve()
    inventory = collect_inventory(root)
    count_failures = validate_counts(inventory.counts)

    all_target_routes = sorted(
        {
            route
            for routes in inventory.routes.values()
            for route in routes
            if route.startswith(TARGET_PREFIXES)
        }
    )

    page_issues: dict[str, list[str]] = {}
    for route in all_target_routes:
        page = root / route.strip("/") / "index.html"
        problems = _validate_page(page, route)
        if problems:
            page_issues[route] = problems

    sitemap_urls = _read_sitemap_urls(root)
    sitemap_missing = [
        route
        for route in all_target_routes
        if (BASE_URL + route).rstrip("/") + "/" not in sitemap_urls
    ]

    failures = {
        "count_failures": count_failures,
        "missing_roots": inventory.missing_roots,
        "page_issues": page_issues,
        "sitemap_missing_routes": sitemap_missing,
    }
    status = "passed" if not any(failures.values()) else "failed"
    report: dict[str, object] = {
        "schemaVersion": 1,
        "status": status,
        "minimumCounts": MINIMUM_COUNTS,
        "counts": inventory.counts,
        "requiredRoots": list(REQUIRED_ROOTS),
        "missingRoots": inventory.missing_roots,
        "repair": repair or {"actions": []},
        "targetRouteCount": len(all_target_routes),
        "routes": inventory.routes,
        "pageIssues": page_issues,
        "sitemapMissingRoutes": sitemap_missing,
        "sitemapUrlCount": len(sitemap_urls),
    }

    destination = root / REPORT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if status != "passed":
        raise SystemExit({"special_needs_publication_inventory": failures})
    return report


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    repo_root = Path.cwd()
    repair = repair_missing_generated_families(root, repo_root)
    report = validate_publication_inventory(root, repair=repair)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
