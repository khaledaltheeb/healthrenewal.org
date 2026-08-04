#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import ensure_complete_discovery_v1 as complete_discovery
import ensure_special_needs_publication_v1 as special_needs_publication
import generate_sitemap_index_v304_core as core
import normalize_rawafid_production_v1 as rawafid_production
import publish_new_special_needs_conditions_v323 as special_needs_v323
import publish_women_youth_v406 as women_youth_v406
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
    """

    site = site.resolve()
    repo_root = repo_root.resolve()
    if site == repo_root:
        return []

    restored: list[str] = []
    for source in repo_root.rglob("*"):
        if not source.is_file():
            continue

        # Test fixtures and local production artifacts may live below the
        # repository root. Never treat files already inside the destination as
        # source files, otherwise the destination is recursively copied into
        # itself until the operating system rejects the path length.
        try:
            source.relative_to(site)
        except ValueError:
            pass
        else:
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


def recover_previously_published_content(root: Path, repo_root: Path) -> dict[str, object]:
    """Re-materialize reviewed route families lost by historical partial deploys.

    The source checkout must remain clean. Recovery therefore runs only against
    a production-style artifact (normally ``_site`` or a directory containing
    the custom-domain marker) and always uses the existing validated publishers.
    """

    production_artifact = root != repo_root and (root.name == "_site" or (root / "CNAME").is_file())
    if not production_artifact:
        return {"status": "skipped-non-production-artifact", "publishers": {}}

    special_needs_report = special_needs_v323.publish(root)
    women_youth_report = women_youth_v406.publish(root)
    return {
        "status": "published",
        "publishers": {
            "special_needs_v323": {
                "status": special_needs_report["status"],
                "condition_count": special_needs_report["condition_count"],
                "generated_pages": len(special_needs_report["generated_pages"]),
                "external_clinical_review_completed": special_needs_report[
                    "external_clinical_review_completed"
                ],
            },
            "women_youth_v406": {
                "status": women_youth_report["status"],
                "page_count": women_youth_report["page_count"],
                "hub_count": women_youth_report["hub_count"],
                "external_specialist_review_completed": women_youth_report[
                    "external_specialist_review_completed"
                ],
            },
        },
    }


def normalize_production_identity(root: Path, repo_root: Path) -> dict[str, object]:
    production_artifact = root != repo_root and (root.name == "_site" or (root / "CNAME").is_file())
    if not production_artifact:
        return {"status": "skipped-non-production-artifact"}
    return rawafid_production.normalize(root)


def generate(root: Path, base_url: str = BASE_URL) -> dict[str, object]:
    root = root.resolve()
    base_url = base_url.rstrip("/") + "/"

    # Resolve source files from the script location, not the caller's current
    # working directory. CI fixtures and production jobs may invoke this script
    # from another directory; using cwd previously hid shared assets and caused
    # false broken-resource failures.
    repo_root = Path(__file__).resolve().parents[1]

    # Generators executed immediately before this step may prune valid files
    # that are physically present on main. Restore those exact missing files
    # before sitemap generation so repository and production inventories match.
    restored_source_files = restore_missing_public_source(root, repo_root)

    # The capability library is generated into the production artifact rather
    # than stored as 155 source pages. Rebuild it automatically when the chosen
    # baseline artifact is incomplete so a stale baseline can never erase the
    # 150 condition protocols during an otherwise successful deployment.
    special_needs_repair = special_needs_publication.repair_missing_generated_families(
        root,
        repo_root,
    )

    # Re-run the reviewed publishers that were previously released through
    # partial overlays and later disappeared when a complete artifact replaced
    # them. They now become deterministic members of the single-site build.
    recovered_content = recover_previously_published_content(root, repo_root)

    # Build canonical sitemap families from the complete, restored artifact.
    report = core.generate(root, base_url)

    # The legacy v305 contract checks that the enhancement hook remains wired
    # after canonical sitemap generation and before discovery publication. The
    # closure records that contract while deferring execution until the final
    # pages and Rawafid identity have been materialized.
    def enhance_final_artifact() -> dict[str, object]:
        machine = enhance_site(root, base_url)
        return machine

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

    # Normalize every source-authored and generated page after discovery pages
    # have been materialized, so recovered content cannot reintroduce a retired
    # identity or inconsistent application metadata.
    rawafid_identity = normalize_production_identity(root, repo_root)

    # Generate AI-readable surfaces after the discovery pages and identity are
    # final, so search engines and AI clients see the same inventory as users.
    machine = enhance_final_artifact()

    # Compare the final artifact with current main and fail closed on missing
    # public files, broken links/resources, orphan pages, pages without visible
    # cards, missing sitemap URLs, invalid metadata, or canonical conflicts.
    discovery_audit = audit_publication_discovery(root, repo_root)

    # Apply an explicit sector-level contract after sitemap and catalogue
    # generation. The deployment cannot proceed unless every condition,
    # protocol, practical guide, family tool, learning path, and sector guide is
    # present, indexable, canonical, and listed in a sitemap.
    special_needs_inventory = special_needs_publication.validate_publication_inventory(
        root,
        repair=special_needs_repair,
    )

    report["robots_policy"] = "explicit-ai-and-public-crawling"
    report["explicit_ai_user_agents"] = list(AI_USER_AGENTS)
    report["preserved_custom_domain_sitemaps"] = machine["preserved_custom_domain_sitemaps"]
    report["machine_readable"] = {
        key: value
        for key, value in machine.items()
        if key not in {"explicit_ai_user_agents", "preserved_custom_domain_sitemaps"}
    }
    report["restored_source_files"] = restored_source_files
    report["recovered_previously_published_content"] = recovered_content
    report["rawafid_production_identity"] = rawafid_identity
    report["complete_discovery_publication"] = discovery_publication
    report["special_needs_publication_inventory"] = {
        "status": special_needs_inventory["status"],
        "counts": special_needs_inventory["counts"],
        "target_route_count": special_needs_inventory["targetRouteCount"],
        "repair_actions": special_needs_inventory["repair"].get("actions", []),
        "missing_roots": len(special_needs_inventory["missingRoots"]),
        "page_issues": len(special_needs_inventory["pageIssues"]),
        "sitemap_missing_routes": len(special_needs_inventory["sitemapMissingRoutes"]),
    }
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
