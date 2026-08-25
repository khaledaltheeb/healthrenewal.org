from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts/publish_addiction_atlas_v2.py"
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"

spec = importlib.util.spec_from_file_location("rawafid_addiction_atlas_v2", V2)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load addiction atlas v2 publisher")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def registered_wave_paths() -> list[Path]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    routes = payload.get("waves") or []
    if not routes:
        raise RuntimeError("Addiction atlas wave manifest is empty")
    paths: list[Path] = []
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, str) or not route.startswith("/data/addiction-atlas/substances-v") or not route.endswith(".json"):
            raise RuntimeError(f"Invalid wave route: {route!r}")
        if route in seen:
            raise RuntimeError(f"Duplicate wave route: {route}")
        seen.add(route)
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            raise RuntimeError(f"Missing registered wave: {route}")
        paths.append(path)
    return paths


def stable_report(site: Path, wave_paths: list[Path]) -> dict[str, int | str]:
    substances: dict[str, dict] = {}
    unknown_risk_values = 0
    for path in wave_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("substances", []):
            slug = item["slug"]
            if slug in substances:
                raise RuntimeError(f"Duplicate substance slug: {slug}")
            substances[slug] = item
            unknown_risk_values += sum(1 for value in item.get("risk", {}).values() if value is None)

    comparison_payload = json.loads(COMPARISONS.read_text(encoding="utf-8"))
    indexable = [item for item in comparison_payload.get("comparisons", []) if item.get("indexable")]

    missing_substance_pages = [
        slug for slug in substances
        if not (site / "addiction/substances" / slug / "index.html").is_file()
    ]
    missing_comparison_pages = [
        item["slug"] for item in indexable
        if not (site / "addiction/compare" / item["slug"] / "index.html").is_file()
    ]
    if missing_substance_pages or missing_comparison_pages:
        raise RuntimeError(
            "Publication report cannot be finalized with missing pages: "
            f"substances={missing_substance_pages}, comparisons={missing_comparison_pages}"
        )

    return {
        "schemaVersion": 3,
        "status": "passed",
        "registeredWaves": len(wave_paths),
        "substances": len(substances),
        "substancePages": len(substances),
        "indexableComparisons": len(indexable),
        "comparisonPages": len(indexable),
        "unknownRiskValues": unknown_risk_values,
    }


def write_stable_report(site: Path, wave_paths: list[Path]) -> None:
    report = stable_report(site, wave_paths)
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "addiction-atlas-v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Rawafid Addiction Atlas from the registered evidence-wave manifest")
    parser.add_argument("site", nargs="?", default="_site")
    args = parser.parse_args()
    site = Path(args.site)
    wave_paths = registered_wave_paths()
    module.DATA_FILES = wave_paths
    module.publish(site)
    write_stable_report(site, wave_paths)


if __name__ == "__main__":
    main()
