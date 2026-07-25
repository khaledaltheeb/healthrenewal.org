from __future__ import annotations

import argparse
import json
from pathlib import Path

import enrich_lab_content_v193_core_v235 as core

for _name in dir(core):
    if not _name.startswith("_"):
        globals().setdefault(_name, getattr(core, _name))

SOURCE_MARKER = "data-lab-source-v235"


def enrich_page(path: Path, kind: str, contract: dict) -> bool:
    source = path.read_text(encoding="utf-8")
    if SOURCE_MARKER in source:
        return False
    core.enrich_page(path, kind, contract)
    return True


def enrich(site: Path) -> dict:
    contract = core.load_contract()
    assessment = sorted((site / "assessment-lab").glob("*/index.html"))
    cognitive = sorted((site / "cognitive-lab").glob("*/index.html"))
    fallback = 0
    source_integrated = 0

    for path in assessment:
        if SOURCE_MARKER in path.read_text(encoding="utf-8"):
            source_integrated += 1
        elif enrich_page(path, "assessment", contract):
            fallback += 1
    for path in cognitive:
        if SOURCE_MARKER in path.read_text(encoding="utf-8"):
            source_integrated += 1
        elif enrich_page(path, "cognitive", contract):
            fallback += 1

    report = {
        "status": "built-not-published",
        "version": 193,
        "assessment_pages_enriched": len(assessment),
        "cognitive_pages_enriched": len(cognitive),
        "total_pages_enriched": len(assessment) + len(cognitive),
        "minimum_visible_words": contract["scope"]["minimum_visible_words"],
        "review": contract["status"],
        "risk_level": contract["risk_level"],
        "source_integration_version": 235,
        "source_integrated_pages": source_integrated,
        "fallback_pages_enriched": fallback,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-depth-v193.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(enrich(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
