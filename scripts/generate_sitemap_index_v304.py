#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import ensure_complete_discovery_v1 as complete_discovery
import generate_sitemap_index_v304_core as core
import materialize_addiction_condition_guides_v2 as addiction_condition_guides
from ai_machine_readable_v1 import AI_USER_AGENTS, enhance_site, sync_robots as sync_ai_robots
from audit_publication_discovery_v1 import run as audit_publication_discovery

BASE_URL = core.BASE_URL
EXCLUDED_PARTS = core.EXCLUDED_PARTS
EXCLUDED_FILES = core.EXCLUDED_FILES
PRIMARY_FILENAME = core.PRIMARY_FILENAME
FAMILY_PREFIX = core.FAMILY_PREFIX
INDEX_FILENAME = core.INDEX_FILENAME
REPORT_FILENAME = core.REPORT_FILENAME
FAMILIES = core.FAMILIES
MetadataParser = core.MetadataParser
metadata = core.metadata
is_verification_artifact = core.is_verification_artifact
normalized_url = core.normalized_url
family_for = core.family_for
is_indexable = core.is_indexable
write_urlset = core.write_urlset

PUBLIC_TEXT_SUFFIXES = {
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".webmanifest",
    ".txt",
    ".js",
    ".mjs",
    ".css",
    ".svg",
}
PUBLIC_SKIP_TOP = {
    ".git",
    ".github",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "scripts",
    "tests",
    "docs",
    "reports",
    "content",
    ".v10bundle",
    ".generator-v6",
    "_site",
}
PUBLIC_SKIP_PARTS = {"account-backend", "backend", "migrations"}


def sync_robots(root: Path, base_url: str = BASE_URL) -> list[str]:
    return sync_ai_robots(root, base_url, PRIMARY_FILENAME, INDEX_FILENAME)


def restore_missing_public_source(site: Path, repo_root: Path) -> list[str]:
    """Restore source-published files removed by an earlier content generator.

    The canonical Pages workflow overlays current ``main`` before running the
    generators. Some historical generators prune directories they do not own;
    that previously removed valid source-published learning paths. This step is
    deliberately non-destructive: it copies a source file only when the final
    artifact no longer contains that relative path and never overwrites a page
    produced by a current generator.

    Test fixtures and other output directories may live inside the repository.
    Files already inside ``site`` must therefore be ignored, or the walk would
    recursively copy the output tree into itself.
    """

    site = site.resolve()
    repo_root = repo_root.resolve()
    if site == repo_root:
        return []

    restored: list[str] = []
    for source in repo_root.rglob("*"):
        if not source.is_file():
            continue
        source = source.resolve()
        if source == site or site in source.parents:
            continue
        relative = source.relative_to(repo_root)
        if not relative.parts or relative.parts[0] in PUBLIC_SKIP_TOP:
            continue
        if any(part in PUBLIC_SKIP_PARTS for part in relative.parts):
            continue
        if relative.as_posix() == "deployment.json":
            continue
        if source.suffix.lower() not in PUBLIC_TEXT_SUFFIXES and source.name != "CNAME":
            continue

        destination = site / relative
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        restored.append(relative.as_posix())

    return sorted(restored)


def materialize_addiction_guides(root: Path) -> dict[str, object]:
    """Build detailed guides only when the complete addiction center is present.

    The sitemap engine is also exercised against small synthetic fixtures that
    intentionally contain no addiction center. A fully absent center is a valid
    non-applicable case; a partially present center is an integrity error.
    """

    routes = addiction_condition_guides.AUTHORITATIVE_EXISTING_ROUTES
    present = [relative for relative in routes if (root / relative).is_file()]
    if not present:
        return {
            "schemaVersion": 2,
            "status": "not-applicable",
            "reason": "addiction-center-not-present",
            "conditionPages": 0,
            "detailedProtocols": 0,
        }
    if len(present) != len(routes):
        missing = sorted(set(routes) - set(present))
        raise SystemExit({"partial_addiction_center": True, "missing": missing})
    return addiction_condition_guides.materialize(root)


def load_discovery_publication_report(root: Path) -> tuple[Path, dict[str, object]]:
    """Load the report written by ``ensure_complete_discovery_v1.run``.

    The publisher intentionally writes its result as an artifact and prints it,
    but does not return a Python value. Loading the artifact keeps the public
    report as the single source of truth and avoids a false deployment failure
    after successful card and catalogue generation.
    """

    report_path = root / "api" / "discovery-publication-v1.json"
    if not report_path.is_file():
        raise SystemExit(f"Missing discovery publication report: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if payload.get("status") != "published":
        raise SystemExit({"invalid_discovery_publication_report": payload})
    return report_path, payload


def generate(root: Path, base_url: str = BASE_URL) -> dict[str, object]:
    root = root.resolve()
    base_url = base_url.rstrip("/") + "/"
    repo_root = Path.cwd().resolve()

    # Generators executed immediately before this step may prune valid files
    # that are physically present on main. Restore those exact missing files
    # before sitemap generation so repository and production inventories match.
    restored_source_files = restore_missing_public_source(root, repo_root)

    # Extend the already-published addiction center with ten detailed condition
    # guides. The materializer checks its signed payload and verifies that the
    # hub, protocol atlas, withdrawal guide, recovery roadmap, family guide, and
    # 53-source registry are byte-for-byte untouched. Synthetic sitemap fixtures
    # without an addiction center are intentionally treated as not applicable.
    addiction_condition_report = materialize_addiction_guides(root)

    # Build canonical sitemap families from the complete, restored artifact.
    report = core.generate(root, base_url)

    # The canonical generator rebuilds sitemap-index.xml. Re-register the
    # dedicated addiction sitemap without replacing any generated family map.
    if addiction_condition_report.get("status") == "passed":
        addiction_condition_guides.merge_discovery(root)

    # Learning paths include both generated paths and source-authored paths.
    # Add the family to the static catalogue set so every restored route is
    # represented by a visible HTML card rather than merely existing on disk.
    complete_discovery.CATALOG_FAMILIES = tuple(
        dict.fromkeys((*complete_discovery.CATALOG_FAMILIES, "learning-paths"))
    )

    # Expose every published route through static HTML cards and complete
    # section catalogues after all other content generators have finished.
    complete_discovery.run(root)
    discovery_report_path, discovery_publication = load_discovery_publication_report(root)
    discovery_publication["restoredSourceFiles"] = restored_source_files
    discovery_publication["restoredSourceFileCount"] = len(restored_source_files)
    discovery_report_path.write_text(
        json.dumps(discovery_publication, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Generate AI-readable surfaces after the discovery pages exist so search
    # engines and AI clients see the same final route inventory as users.
    machine = enhance_site(root, base_url)

    # Compare the final artifact with current main and fail closed on missing
    # public files, broken links/resources, orphan pages, pages without visible
    # cards, missing sitemap URLs, invalid metadata, or canonical conflicts.
    discovery_audit = audit_publication_discovery(root, repo_root)

    report["robots_policy"] = "explicit-ai-and-public-crawling"
    report["explicit_ai_user_agents"] = list(AI_USER_AGENTS)
    report["preserved_custom_domain_sitemaps"] = machine["preserved_custom_domain_sitemaps"]
    report["machine_readable"] = {
        key: value
        for key, value in machine.items()
        if key not in {"explicit_ai_user_agents", "preserved_custom_domain_sitemaps"}
    }
    report["restored_source_files"] = restored_source_files
    report["addiction_condition_guides"] = addiction_condition_report
    report["complete_discovery_publication"] = discovery_publication
    report["publication_discovery_audit"] = {
        "status": discovery_audit["status"],
        "source_public_files": discovery_audit["sourcePublicFiles"],
        "missing_source_files": len(discovery_audit["missingSourceFiles"]),
        "published_html_routes": discovery_audit["publishedHtmlRoutes"],
        "indexable_html_routes": discovery_audit["indexableHtmlRoutes"],
        "broken_internal_links": len(discovery_audit["brokenInternalLinks"]),
        "broken_internal_resources": len(discovery_audit["brokenInternalResources"]),
        "orphan_indexable_routes": len(discovery_audit["orphanIndexableRoutes"]),
        "routes_without_visible_cards": len(discovery_audit["indexableRoutesWithoutVisibleCard"]),
        "sitemap_missing_routes": len(discovery_audit["sitemapMissingIndexableRoutes"]),
        "metadata_issues": len(discovery_audit["metadataIssues"]),
        "canonical_issues": len(discovery_audit["canonicalIssues"]),
    }
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_FILENAME).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    print(json.dumps(generate(args.root, args.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
