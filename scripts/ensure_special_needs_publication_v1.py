#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BASE_URL = "https://healthrenewal.org"
REPORT_PATH = Path("api/special-needs-publication-inventory-v1.json")
V281_PAYLOAD_PATH = Path("content/v281/conditions-50-ar.json.zlib.b64")

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
        self.refreshes: list[str] = []

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
        elif lowered == "meta":
            if values.get("name", "").lower() == "robots":
                self.robots.append(values.get("content", "").lower())
            if values.get("http-equiv", "").lower() == "refresh":
                self.refreshes.append(values.get("content", ""))


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
        path for path in capability_pages
        if path.parent != root / "capabilities"
        and path.parent.name not in CAPABILITY_NON_CONDITION_SLUGS
    ]
    groups = {
        "capability_pages": capability_pages,
        "capability_condition_pages": capability_conditions,
        "special_needs_practical_guides": sorted((root / "special-needs" / "practical").glob("*/index.html")),
        "family_condition_guides": sorted((root / "family-guide" / "conditions").glob("*/index.html")),
        "family_tools": sorted((root / "family-guide" / "tools").glob("*/index.html")),
        "learning_paths": sorted((root / "learning-paths").glob("*/index.html")),
        "child_guides": sorted((root / "sectors" / "child" / "guides").glob("*/index.html")),
        "family_guides": sorted((root / "sectors" / "family" / "guides").glob("*/index.html")),
        "home_guides": sorted((root / "sectors" / "home" / "guides").glob("*/index.html")),
    }
    counts = {name: len(paths) for name, paths in groups.items()}
    routes = {name: [_route_for(path, root) for path in paths] for name, paths in groups.items()}
    missing_roots = [relative for relative in REQUIRED_ROOTS if not (root / relative).is_file()]
    return Inventory(counts=counts, routes=routes, missing_roots=missing_roots)


def validate_counts(counts: dict[str, int], minimums: dict[str, int] | None = None) -> dict[str, dict[str, int]]:
    minimums = minimums or MINIMUM_COUNTS
    return {
        name: {"actual": int(counts.get(name, 0)), "minimum": minimum}
        for name, minimum in minimums.items()
        if int(counts.get(name, 0)) < minimum
    }


def _run_script(repo_root: Path, script_name: str, *args: str | Path) -> None:
    script = repo_root / "scripts" / script_name
    if not script.is_file():
        raise FileNotFoundError(f"Required publication script is missing: {script}")
    completed = subprocess.run(
        [sys.executable, str(script), *(str(argument) for argument in args)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code {completed.returncode}.\n"
            f"stdout:\n{completed.stdout.strip()}\nstderr:\n{completed.stderr.strip()}"
        )


def _publish_v281_conditions(repo_root: Path, site_root: Path) -> list[str]:
    payload = repo_root / V281_PAYLOAD_PATH
    if payload.exists() and not payload.is_file():
        raise RuntimeError(f"v281 payload path is not a regular file: {payload}")
    previous_payload = payload.read_bytes() if payload.is_file() else None
    actions: list[str] = []
    try:
        _run_script(repo_root, "build_conditions_v281_data.py")
        actions.append("build_conditions_v281_data.py")
        if not payload.is_file() or payload.stat().st_size == 0:
            raise RuntimeError(f"v281 builder did not create a non-empty payload: {payload}")
        _run_script(repo_root, "publish_conditions_v281.py", site_root)
        actions.append("publish_conditions_v281.py")
        return actions
    finally:
        if previous_payload is None:
            payload.unlink(missing_ok=True)
        else:
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_bytes(previous_payload)


def _capability_repair_required(inventory: Inventory) -> bool:
    return any(
        inventory.counts.get(name, 0) < MINIMUM_COUNTS[name]
        for name in ("capability_pages", "capability_condition_pages")
    )


def repair_missing_generated_families(root: Path, repo_root: Path) -> dict[str, object]:
    root = root.resolve()
    repo_root = repo_root.resolve()
    before = collect_inventory(root)
    actions: list[str] = []
    if root != repo_root:
        if _capability_repair_required(before):
            _run_script(repo_root, "publish_capabilities_v280.py", root)
            actions.append("publish_capabilities_v280.py")
            actions.extend(_publish_v281_conditions(repo_root, root))
        _run_script(repo_root, "publish_family_guide_special_education_tools_v1.py", root)
        actions.append("publish_family_guide_special_education_tools_v1.py")
    after = collect_inventory(root)
    return {"actions": actions, "before": before.counts, "after": after.counts}


def _read_sitemap_urls(root: Path) -> set[str]:
    urls: set[str] = set()
    for path in sorted(root.glob("sitemap*.xml")):
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise SystemExit({"invalid_sitemap": str(path), "error": str(exc)}) from exc
        if tree.getroot().tag.rsplit("}", 1)[-1] != "urlset":
            continue
        for node in tree.getroot().findall("{*}url/{*}loc"):
            value = (node.text or "").strip()
            if value:
                urls.add(value.rstrip("/") + "/")
    return urls


def _parse_page(path: Path) -> tuple[list[str], PageMetadataParser]:
    problems: list[str] = []
    parser = PageMetadataParser()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["not_utf8"], parser
    if len(text.encode("utf-8")) < 500:
        problems.append("too_small")
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        problems.append("invalid_html_parse")
    return problems, parser


def _intentional_internal_alias(parser: PageMetadataParser, route: str) -> bool:
    """Return True only for an explicit noindex redirect/canonical alias to this site.

    Historical merged routes are intentionally kept reachable for users and old links,
    but must not be forced back into the index or sitemap. Requiring all three signals
    prevents an accidental noindex on a normal content page from being silently ignored.
    """
    if not any("noindex" in directive for directive in parser.robots):
        return False
    expected = (BASE_URL + route).rstrip("/")
    targets = [value.rstrip("/") for value in parser.canonicals]
    internal_targets = [
        value for value in targets
        if urlparse(value).scheme in {"http", "https"}
        and urlparse(value).netloc == urlparse(BASE_URL).netloc
        and value != expected
    ]
    return bool(internal_targets and parser.refreshes)


def _validate_page(path: Path, route: str) -> tuple[list[str], bool]:
    problems, parser = _parse_page(path)
    if problems and "invalid_html_parse" in problems:
        return problems, False
    if _intentional_internal_alias(parser, route):
        if parser.h1_count == 0:
            problems.append("missing_h1")
        return problems, True
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
    return problems, False


def validate_publication_inventory(root: Path, *, repair: dict[str, object] | None = None) -> dict[str, object]:
    root = root.resolve()
    inventory = collect_inventory(root)
    count_failures = validate_counts(inventory.counts)
    all_target_routes = sorted({
        route for routes in inventory.routes.values() for route in routes
        if route.startswith(TARGET_PREFIXES)
    })

    page_issues: dict[str, list[str]] = {}
    intentional_aliases: list[str] = []
    for route in all_target_routes:
        page = root / route.strip("/") / "index.html"
        problems, intentional_alias = _validate_page(page, route)
        if intentional_alias:
            intentional_aliases.append(route)
        if problems:
            page_issues[route] = problems

    sitemap_urls = _read_sitemap_urls(root)
    indexable_target_routes = [route for route in all_target_routes if route not in intentional_aliases]
    sitemap_missing = [
        route for route in indexable_target_routes
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
        "schemaVersion": 2,
        "status": status,
        "minimumCounts": MINIMUM_COUNTS,
        "counts": inventory.counts,
        "requiredRoots": list(REQUIRED_ROOTS),
        "missingRoots": inventory.missing_roots,
        "repair": repair or {"actions": []},
        "targetRouteCount": len(all_target_routes),
        "indexableTargetRouteCount": len(indexable_target_routes),
        "intentionalAliasCount": len(intentional_aliases),
        "intentionalAliases": intentional_aliases,
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
