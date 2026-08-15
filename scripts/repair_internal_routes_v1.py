from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from publish_daily_tools_v150 import publish as publish_daily_tools_v150
from repair_internal_routes_core_v1 import apply as apply_core

REPORT = "api/internal-route-repair-v1.json"


def ensure_daily_tools_v150(root: Path) -> dict:
    report = publish_daily_tools_v150(root)
    expected = {
        "status": "passed",
        "edition": 150,
        "tools": 150,
        "existingToolsUpgraded": 100,
        "newToolsAdded": 50,
        "categories": 10,
        "toolsPerCategory": 15,
        "indexableSectionPages": 162,
    }
    failures = {
        key: {"expected": value, "actual": report.get(key)}
        for key, value in expected.items()
        if report.get(key) != value
    }

    minimum_words = int(report.get("minimumToolPageWordCount", 0) or 0)
    if minimum_words < 420:
        failures["minimumToolPageWordCount"] = {
            "expectedAtLeast": 420,
            "actual": minimum_words,
        }

    tool_pages = sorted((root / "daily-tools").glob("*/index.html"))
    if len(tool_pages) != 150:
        failures["toolPageCount"] = {"expected": 150, "actual": len(tool_pages)}

    linking = report.get("contextualLinking") or {}
    linking_expected = {
        "status": "passed",
        "tools": 150,
        "learningPathsEnhanced": 10,
        "toolsLinkedFromLearningPaths": 150,
        "minimumExternalTopicalHubInlinksPerTool": 2,
    }
    linking_failures = {
        key: {"expected": value, "actual": linking.get(key)}
        for key, value in linking_expected.items()
        if linking.get(key) != value
    }
    if linking_failures:
        failures["contextualLinking"] = linking_failures

    if failures:
        raise SystemExit({"dailyToolsV150Contract": failures})

    release_sha = (
        os.environ.get("BUILD_SHA")
        or os.environ.get("RELEASE_SHA")
        or ""
    ).strip()
    release = {
        "schemaVersion": 2,
        "status": "passed",
        "releaseCommit": release_sha,
        "edition": 150,
        "tools": 150,
        "existingToolsUpgraded": 100,
        "newToolsAdded": 50,
        "sectionPages": 162,
        "minimumToolPageWordCount": minimum_words,
        "generatedBy": "institutional-production-sitemap-gate",
    }
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "daily-tools-release-v150.json").write_text(
        json.dumps(release, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        **expected,
        "minimumToolPageWordCount": minimum_words,
        "toolPageCount": len(tool_pages),
        "releaseCommit": release_sha,
        "postLaunchHardening": report.get("postLaunchHardening"),
        "contextualLinking": linking,
    }


def apply(root: Path) -> dict:
    root = Path(root).resolve()
    daily_tools = ensure_daily_tools_v150(root)
    report = apply_core(root)
    report["dailyToolsV150"] = daily_tools

    report_path = root / REPORT
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
