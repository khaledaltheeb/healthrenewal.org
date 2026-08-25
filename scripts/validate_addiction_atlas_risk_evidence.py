from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/addiction-atlas"
SUBSTANCE_MANIFEST = DATA / "substance-waves.json"
RISK_MANIFEST = DATA / "risk-evidence-manifest.json"
RISK_KEYS = {
    "acute_toxicity",
    "overdose_risk",
    "dependence",
    "withdrawal_medical_risk",
    "neuro_harm",
    "cardio_harm",
    "respiratory_harm",
    "polysubstance_risk",
}
GRADES = {"A", "B", "C", "U"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise AssertionError(message)


def source_ids() -> set[str]:
    ids: set[str] = set()
    for path in sorted(DATA.glob("source-registry-v*.json")):
        for source in load(path).get("sources", []):
            sid = source.get("id")
            if not sid:
                fail(f"{path.name}: source missing id")
            if sid in ids:
                fail(f"duplicate source id across registries: {sid}")
            ids.add(sid)
    if not ids:
        fail("no registered evidence sources")
    return ids


def wave_slug_map() -> dict[str, dict[str, dict]]:
    payload = load(SUBSTANCE_MANIFEST)
    out: dict[str, dict[str, dict]] = {}
    for route in payload.get("waves") or []:
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            fail(f"missing registered substance wave: {route}")
        wave = path.stem.replace("substances-", "")
        records: dict[str, dict] = {}
        for item in load(path).get("substances", []):
            slug = item.get("slug")
            if not slug:
                fail(f"{path.name}: missing slug")
            records[slug] = item
        out[wave] = records
    return out


def main() -> None:
    registered_sources = source_ids()
    substances_by_wave = wave_slug_map()
    manifest = load(RISK_MANIFEST)
    routes = manifest.get("waves") or []
    if not routes:
        fail("risk evidence manifest has no waves")

    covered: set[tuple[str, str]] = set()
    dimension_records = 0
    numeric_dimensions = 0
    unknown_dimensions = 0
    grade_counts = {grade: 0 for grade in sorted(GRADES)}

    for route in routes:
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            fail(f"missing risk evidence file: {route}")
        payload = load(path)
        wave = payload.get("wave")
        if wave not in substances_by_wave:
            fail(f"{path.name}: unknown substance wave {wave!r}")
        expected_slugs = set(substances_by_wave[wave])
        records = payload.get("records") or []
        record_slugs = [record.get("substance_slug") for record in records]
        if any(not slug for slug in record_slugs):
            fail(f"{path.name}: record missing substance_slug")
        if len(record_slugs) != len(set(record_slugs)):
            fail(f"{path.name}: duplicate substance records")
        if set(record_slugs) != expected_slugs:
            fail(
                f"{path.name}: coverage mismatch missing={sorted(expected_slugs-set(record_slugs))} "
                f"extra={sorted(set(record_slugs)-expected_slugs)}"
            )

        for record in records:
            slug = record["substance_slug"]
            key = (wave, slug)
            if key in covered:
                fail(f"duplicate risk evidence record: {wave}/{slug}")
            covered.add(key)
            substance = substances_by_wave[wave][slug]
            dimensions = record.get("dimensions") or {}
            if set(dimensions) != RISK_KEYS:
                fail(f"{path.name}:{slug}: risk evidence dimensions must exactly match methodology")

            for dim, evidence in dimensions.items():
                dimension_records += 1
                original_score = substance["risk"][dim]
                if evidence.get("score") != original_score:
                    fail(
                        f"{path.name}:{slug}:{dim}: evidence score {evidence.get('score')!r} "
                        f"does not match substance score {original_score!r}"
                    )
                grade = evidence.get("evidence_grade")
                if grade not in GRADES:
                    fail(f"{path.name}:{slug}:{dim}: invalid evidence_grade={grade!r}")
                grade_counts[grade] += 1
                ids = evidence.get("source_ids") or []
                if not ids:
                    fail(f"{path.name}:{slug}:{dim}: source_ids required even for unknown dimensions")
                if len(ids) != len(set(ids)):
                    fail(f"{path.name}:{slug}:{dim}: duplicate source_ids")
                unknown_sources = sorted(set(ids) - registered_sources)
                if unknown_sources:
                    fail(f"{path.name}:{slug}:{dim}: unknown source_ids {unknown_sources}")
                context = str(evidence.get("context_ar") or "").strip()
                rationale = str(evidence.get("rationale_ar") or "").strip()
                if len(context) < 20:
                    fail(f"{path.name}:{slug}:{dim}: context_ar too short")
                if len(rationale) < 35:
                    fail(f"{path.name}:{slug}:{dim}: rationale_ar too short")

                if original_score is None:
                    unknown_dimensions += 1
                    if grade != "U":
                        fail(f"{path.name}:{slug}:{dim}: null score requires evidence_grade U")
                else:
                    numeric_dimensions += 1
                    if grade == "U":
                        fail(f"{path.name}:{slug}:{dim}: numeric score cannot use evidence_grade U")
                    if type(original_score) is not int or not 1 <= original_score <= 5:
                        fail(f"{path.name}:{slug}:{dim}: invalid numeric score={original_score!r}")

    print(json.dumps({
        "status": "passed",
        "riskEvidenceWaves": len(routes),
        "coveredSubstances": len(covered),
        "dimensionRecords": dimension_records,
        "numericDimensions": numeric_dimensions,
        "unknownDimensions": unknown_dimensions,
        "gradeCounts": grade_counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
