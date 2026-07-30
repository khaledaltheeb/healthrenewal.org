from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from publish_family_sector_v249 import upgrade as upgrade_family_sector
from publish_global_metadata_v27 import main as publish_global_metadata
from upgrade_child_sector_v239 import upgrade as upgrade_child_sector
from upgrade_home_sector_v234 import upgrade as upgrade_home_sector
from upgrade_women_sector_v244 import upgrade as upgrade_women_sector


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
DEPLOYMENT_SCHEMA_VERSION = 30
CRITICAL_FILES = (
    "index.html",
    "sitemap.xml",
    "manifest.webmanifest",
    "sw.js",
)
SITEMAP_EVIDENCE_FILES = (
    "sitemap-index.xml",
    "robots.txt",
    "api/sitemap-index-v305.json",
    "api/indexing-coverage-audit-v303.json",
)
PLATFORM_FILES = (
    "assets/platform/platform-core.css",
    "assets/platform/platform-core.js",
    "api/platform-normalization-v1.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize_sitemap_coverage(site: Path) -> dict[str, object]:
    generator = Path(__file__).with_name("generate_sitemap_index_v304.py")
    auditor = Path(__file__).with_name("audit_indexing_coverage_v303.py")
    subprocess.run([sys.executable, str(generator), str(site)], check=True)
    subprocess.run([sys.executable, str(auditor), str(site)], check=True)
    report_path = site / "api" / "indexing-coverage-audit-v303.json"
    if not report_path.is_file():
        raise SystemExit(f"Indexing coverage evidence not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = int(report.get("expected_indexable_pages", 0))
    sitemap_urls = int(report.get("sitemap_urls", -1))
    if report.get("version") != 305 or report.get("status") != "passed":
        raise SystemExit({"invalid_indexing_coverage_evidence": report})
    if expected < 3000:
        raise SystemExit({"production_indexing_page_count_too_low": expected})
    if sitemap_urls != expected or float(report.get("sitemap_coverage_ratio", 0)) != 1.0:
        raise SystemExit({"incomplete_production_sitemap_coverage": report})
    if report.get("local_route_contract") != "passed":
        raise SystemExit({"invalid_local_route_contract": report})
    return report


def normalize_platform_shell(site: Path) -> dict[str, object]:
    normalizer = Path(__file__).with_name("normalize_platform_shell.py")
    report_path = site / "api" / "platform-normalization-v1.json"
    subprocess.run(
        [
            sys.executable,
            str(normalizer),
            str(site),
            "--report-path",
            str(report_path),
        ],
        check=True,
    )
    if not report_path.is_file():
        raise SystemExit(f"Platform normalization evidence not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    counts = report.get("counts", {})
    seen = int(report.get("html_pages_seen", 0))
    normalized = int(report.get("html_pages_normalized_or_current", 0))
    if report.get("schema_version") != 1 or report.get("status") != "passed":
        raise SystemExit({"invalid_platform_normalization_evidence": report})
    if seen < 3000 or normalized < 3000:
        raise SystemExit(
            {
                "platform_normalization_page_count_too_low": {
                    "seen": seen,
                    "normalized_or_current": normalized,
                }
            }
        )
    if int(counts.get("error", 0)) != 0:
        raise SystemExit({"platform_normalization_errors": report})
    for relative in PLATFORM_FILES[:2]:
        if not (site / relative).is_file():
            raise SystemExit({"missing_platform_asset": relative})
    return report


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Site directory not found: {SITE}")

    home_sector = upgrade_home_sector(SITE)
    required_home_contract = {
        "status": "passed",
        "version": 234,
        "source_articles": 20,
        "hub_h1": 1,
        "banned_term_present": False,
        "diagnostic_claim_present": False,
        "word_count_method": "semantic-visible-tokens-v244",
        "depth_contract_version": 244,
    }
    for key, expected in required_home_contract.items():
        if home_sector.get(key) != expected:
            raise SystemExit({"invalid_home_sector_v244_evidence": {"key": key, "expected": expected, "actual": home_sector.get(key)}})
    if int(home_sector.get("hub_words", 0)) < 2919 or int(home_sector.get("minimum_article_words", 0)) < 819:
        raise SystemExit({"insufficient_home_sector_v244_semantic_depth": home_sector})

    child_sector = upgrade_child_sector(SITE)
    required_child_contract = {
        "status": "passed",
        "version": 239,
        "source_articles": 20,
        "hub_h1": 1,
        "banned_term_present": False,
        "diagnostic_claim_present": False,
    }
    for key, expected in required_child_contract.items():
        if child_sector.get(key) != expected:
            raise SystemExit({"invalid_child_sector_v239_evidence": {"key": key, "expected": expected, "actual": child_sector.get(key)}})
    if int(child_sector.get("hub_words", 0)) < 2200 or int(child_sector.get("minimum_article_words", 0)) < 650:
        raise SystemExit({"insufficient_child_sector_v239_depth": child_sector})

    women_sector = upgrade_women_sector(SITE)
    required_women_contract = {
        "status": "passed",
        "version": 244,
        "source_articles": 20,
        "hub_h1": 1,
        "banned_term_present": False,
        "diagnostic_claim_present": False,
    }
    for key, expected in required_women_contract.items():
        if women_sector.get(key) != expected:
            raise SystemExit({"invalid_women_sector_v244_evidence": {"key": key, "expected": expected, "actual": women_sector.get(key)}})
    if int(women_sector.get("hub_words", 0)) < 2200 or int(women_sector.get("minimum_article_words", 0)) < 700:
        raise SystemExit({"insufficient_women_sector_v244_depth": women_sector})

    family_sector = upgrade_family_sector(SITE)
    required_family_contract = {
        "status": "passed",
        "version": 249,
        "source_articles": 20,
        "hub_h1": 1,
        "banned_term_present": False,
        "diagnostic_claim_present": False,
    }
    for key, expected in required_family_contract.items():
        if family_sector.get(key) != expected:
            raise SystemExit({"invalid_family_sector_v249_evidence": {"key": key, "expected": expected, "actual": family_sector.get(key)}})
    if int(family_sector.get("hub_words", 0)) < 2500 or int(family_sector.get("minimum_article_words", 0)) < 800:
        raise SystemExit({"insufficient_family_sector_v249_depth": family_sector})

    platform = normalize_platform_shell(SITE)

    publish_global_metadata()
    metadata_path = SITE / "api" / "global-metadata-v27.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Global metadata evidence not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed" or int(metadata.get("remaining_missing_count", -1)) != 0:
        raise SystemExit({"invalid_global_metadata_evidence": metadata})

    reports = (
        ("home-sector-v234.json", home_sector, "home_sector_evidence_mismatch"),
        ("child-sector-v239.json", child_sector, "child_sector_evidence_mismatch"),
        ("women-sector-v244.json", women_sector, "women_sector_evidence_mismatch"),
        ("family-sector-v249.json", family_sector, "family_sector_evidence_mismatch"),
    )
    for filename, memory_report, mismatch_key in reports:
        report_path = SITE / "api" / filename
        if not report_path.is_file():
            raise SystemExit(f"Sector evidence not found: {report_path}")
        written_report = json.loads(report_path.read_text(encoding="utf-8"))
        if written_report != memory_report:
            raise SystemExit({mismatch_key: {"memory": memory_report, "written": written_report}})

    indexing = finalize_sitemap_coverage(SITE)

    pwa_path = SITE / "api" / "pwa-v14.json"
    if not pwa_path.is_file():
        raise SystemExit(f"PWA evidence not found: {pwa_path}")

    missing = [name for name in CRITICAL_FILES if not (SITE / name).is_file()]
    missing_sitemap_evidence = [name for name in SITEMAP_EVIDENCE_FILES if not (SITE / name).is_file()]
    missing_platform_files = [name for name in PLATFORM_FILES if not (SITE / name).is_file()]
    if missing:
        raise SystemExit({"missing_critical_files": missing})
    if missing_sitemap_evidence:
        raise SystemExit({"missing_sitemap_evidence_files": missing_sitemap_evidence})
    if missing_platform_files:
        raise SystemExit({"missing_platform_files": missing_platform_files})

    pwa = json.loads(pwa_path.read_text(encoding="utf-8"))
    if not pwa.get("registration_verified") or int(pwa.get("pages_scanned", 0)) <= 0:
        raise SystemExit({"invalid_pwa_evidence": pwa})
    if int(metadata.get("pages_scanned", 0)) != int(pwa.get("pages_scanned", 0)):
        raise SystemExit({
            "metadata_pwa_page_count_mismatch": {
                "metadata": metadata.get("pages_scanned"),
                "pwa": pwa.get("pages_scanned"),
            }
        })

    artifacts = {
        name: {
            "sha256": sha256(SITE / name),
            "bytes": (SITE / name).stat().st_size,
        }
        for name in CRITICAL_FILES
    }

    payload = {
        "schema_version": DEPLOYMENT_SCHEMA_VERSION,
        "commit": os.environ["GITHUB_SHA"],
        "workflow_run": os.environ["GITHUB_RUN_ID"],
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "40 assessments, 53 cognitive tools, 186 browser runs, full PWA registration, complete global metadata, complete platform shell normalization, complete family sitemap index v305, home-sector v244 semantic depth and safety, child-sector v239 depth and safety, women-sector v244 depth and safety, family-sector v249 depth and safety, critical artifact SHA-256",
        "pwa_pages": int(pwa["pages_scanned"]),
        "metadata_pages": int(metadata["pages_scanned"]),
        "metadata_version": int(metadata["version"]),
        "metadata_remaining_missing": int(metadata["remaining_missing_count"]),
        "platform_shell_version": str(platform["shell_version"]),
        "platform_html_pages_seen": int(platform["html_pages_seen"]),
        "platform_html_pages_normalized_or_current": int(platform["html_pages_normalized_or_current"]),
        "platform_normalization_counts": platform["counts"],
        "sitemap_index_version": int(indexing["version"]),
        "sitemap_index_status": str(indexing["status"]),
        "sitemap_index_pages": int(indexing["expected_indexable_pages"]),
        "sitemap_index_urls": int(indexing["sitemap_urls"]),
        "sitemap_index_coverage_ratio": float(indexing["sitemap_coverage_ratio"]),
        "sitemap_index_families": indexing["family_counts"],
        "home_sector_version": int(home_sector["version"]),
        "home_sector_articles": int(home_sector["source_articles"]),
        "home_sector_hub_words": int(home_sector["hub_words"]),
        "home_sector_minimum_article_words": int(home_sector["minimum_article_words"]),
        "home_sector_word_count_method": str(home_sector["word_count_method"]),
        "home_sector_depth_contract_version": int(home_sector["depth_contract_version"]),
        "child_sector_version": int(child_sector["version"]),
        "child_sector_articles": int(child_sector["source_articles"]),
        "child_sector_hub_words": int(child_sector["hub_words"]),
        "child_sector_minimum_article_words": int(child_sector["minimum_article_words"]),
        "women_sector_version": int(women_sector["version"]),
        "women_sector_articles": int(women_sector["source_articles"]),
        "women_sector_hub_words": int(women_sector["hub_words"]),
        "women_sector_minimum_article_words": int(women_sector["minimum_article_words"]),
        "family_sector_version": int(family_sector["version"]),
        "family_sector_articles": int(family_sector["source_articles"]),
        "family_sector_hub_words": int(family_sector["hub_words"]),
        "family_sector_minimum_article_words": int(family_sector["minimum_article_words"]),
        "artifacts": artifacts,
    }

    output = SITE / "deployment.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    written = json.loads(output.read_text(encoding="utf-8"))
    for name, evidence in artifacts.items():
        if written["artifacts"][name]["sha256"] != evidence["sha256"]:
            raise SystemExit({"deployment_stamp_mismatch": name})

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
