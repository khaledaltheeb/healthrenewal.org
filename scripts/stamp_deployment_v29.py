from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from publish_global_metadata_v27 import main as publish_global_metadata
from upgrade_child_sector_v239 import upgrade as upgrade_child_sector
from upgrade_home_sector_v234 import upgrade as upgrade_home_sector
from upgrade_women_sector_v244 import upgrade as upgrade_women_sector


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
CRITICAL_FILES = (
    "index.html",
    "sitemap.xml",
    "manifest.webmanifest",
    "sw.js",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    publish_global_metadata()
    metadata_path = SITE / "api" / "global-metadata-v27.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Global metadata evidence not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed" or int(metadata.get("remaining_missing_count", -1)) != 0:
        raise SystemExit({"invalid_global_metadata_evidence": metadata})

    home_report_path = SITE / "api" / "home-sector-v234.json"
    if not home_report_path.is_file():
        raise SystemExit(f"Home-sector evidence not found: {home_report_path}")
    written_home_sector = json.loads(home_report_path.read_text(encoding="utf-8"))
    if written_home_sector != home_sector:
        raise SystemExit({"home_sector_evidence_mismatch": {"memory": home_sector, "written": written_home_sector}})

    child_report_path = SITE / "api" / "child-sector-v239.json"
    if not child_report_path.is_file():
        raise SystemExit(f"Child-sector evidence not found: {child_report_path}")
    written_child_sector = json.loads(child_report_path.read_text(encoding="utf-8"))
    if written_child_sector != child_sector:
        raise SystemExit({"child_sector_evidence_mismatch": {"memory": child_sector, "written": written_child_sector}})

    women_report_path = SITE / "api" / "women-sector-v244.json"
    if not women_report_path.is_file():
        raise SystemExit(f"Women-sector evidence not found: {women_report_path}")
    written_women_sector = json.loads(women_report_path.read_text(encoding="utf-8"))
    if written_women_sector != women_sector:
        raise SystemExit({"women_sector_evidence_mismatch": {"memory": women_sector, "written": written_women_sector}})

    pwa_path = SITE / "api" / "pwa-v14.json"
    if not pwa_path.is_file():
        raise SystemExit(f"PWA evidence not found: {pwa_path}")

    missing = [name for name in CRITICAL_FILES if not (SITE / name).is_file()]
    if missing:
        raise SystemExit({"missing_critical_files": missing})

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
        "schema_version": 29,
        "commit": os.environ["GITHUB_SHA"],
        "workflow_run": os.environ["GITHUB_RUN_ID"],
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "40 assessments, 53 cognitive tools, 186 browser runs, full PWA registration, complete global metadata, home-sector v244 semantic depth and safety, child-sector v239 depth and safety, women-sector v244 depth and safety, critical artifact SHA-256",
        "pwa_pages": int(pwa["pages_scanned"]),
        "metadata_pages": int(metadata["pages_scanned"]),
        "metadata_version": int(metadata["version"]),
        "metadata_remaining_missing": int(metadata["remaining_missing_count"]),
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
