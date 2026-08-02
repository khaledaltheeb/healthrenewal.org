#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT / "reports/content-expansion-v1.json").read_text(encoding="utf-8"))


def profile_map() -> dict[str, set[str]]:
    return {
        item["path"]: set(item.get("evidenceProfiles") or [])
        for item in REPORT["pages"]
    }


def main() -> None:
    profiles = profile_map()

    assessment_paths = [path for path in profiles if "/guides/assessment/" in path]
    assert len(assessment_paths) == 9
    for path in assessment_paths:
        assert "assessment-functioning" in profiles[path], (path, profiles[path])
        assert "health-access" not in profiles[path], (path, profiles[path])

    required = {
        "special-needs/guides/assessment/shared-decision-making/index.html": {
            "decision-support", "assessment-functioning"
        },
        "special-needs/guides/assessment/supported-decision-making/index.html": {
            "decision-support", "assessment-functioning"
        },
        "special-needs/guides/participation/community-participation/index.html": {
            "participation-community"
        },
        "special-needs/guides/participation/recreation-sport-inclusion/index.html": {
            "participation-community"
        },
        "special-needs/guides/participation/public-transport-access/index.html": {
            "participation-community"
        },
        "special-needs/guides/system-quality/rehabilitation-goal-review/index.html": {
            "service-quality-system"
        },
        "special-needs/guides/system-quality/service-quality-audit/index.html": {
            "service-quality-system"
        },
        "daily-tools/disability-support/service-quality-scorecard/index.html": {
            "service-quality-system"
        },
    }
    for path, expected in required.items():
        assert path in profiles, path
        assert expected.issubset(profiles[path]), (path, expected, profiles[path])

    assert "pain-recognition" in profiles[
        "special-needs/guides/health/pain-recognition-nonspeaking/index.html"
    ]
    assert "feeding-swallowing" in profiles[
        "special-needs/guides/health/swallowing-safety-referral/index.html"
    ]
    assert "epilepsy-safety" in profiles[
        "special-needs/guides/health/epilepsy-safety-plan/index.html"
    ]
    assert "wheelchair-mobility" in profiles[
        "special-needs/guides/mobility-at/wheelchair-seating-service/index.html"
    ]
    assert "inclusive-education-udl" in profiles[
        "special-needs/guides/education/universal-design-for-learning/index.html"
    ]

    print(json.dumps({
        "passed": True,
        "assessmentPages": len(assessment_paths),
        "explicitRoutingChecks": len(required) + 5,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
