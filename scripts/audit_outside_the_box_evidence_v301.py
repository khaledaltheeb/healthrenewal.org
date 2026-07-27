from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
INSTRUMENTS = ROOT / "content" / "v254" / "outside-the-box-instruments-ar.json"
STANDARD = ROOT / "api" / "outside-the-box-evidence-standard-v301.json"

TRUSTED_SUFFIXES = (
    "who.int",
    "un.org",
    "ohchr.org",
    "nice.org.uk",
    "cdc.gov",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "asha.org",
    "aaidd.org",
    "ies.ed.gov",
    "ectacenter.org",
    "udlguidelines.cast.org",
    "unicef.org",
    "canchild.ca",
    "perkins.org",
    "rarediseases.info.nih.gov",
    "medlineplus.gov",
    "cosmin.nl",
    "intestcom.org",
    "apa.org",
    "aera.net",
    "ncme.org",
    "gradeworkinggroup.org",
    "specialolympics.org",
    "sciencedirect.com",
    "pmc.ncbi.nlm.nih.gov",
)

BANNED_ABSOLUTES = (
    "كل المصابين",
    "جميع المصابين",
    "كل الأشخاص لديهم",
    "ميزة مؤكدة",
    "تفوق مضمون",
    "عبقرية مرتبطة",
    "شفاء مضمون",
    "نتيجة مضمونة",
    "اعتماد عالمي مكتمل",
)

PROTECTED_TEST_MARKERS = (
    "مفتاح التصحيح:",
    "الإجابة الصحيحة:",
    "الدرجة الخام =",
    "جدول المعايير",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def host_is_trusted(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in TRUSTED_SUFFIXES)


def all_text(value) -> str:
    if isinstance(value, dict):
        return "\n".join(all_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(all_text(v) for v in value)
    return str(value)


def audit() -> dict:
    data = load(CONDITIONS)
    instruments = load(INSTRUMENTS)
    standard = load(STANDARD)

    errors: list[str] = []
    warnings: list[str] = []

    conditions = data.get("conditions", [])
    if len(conditions) != 100:
        errors.append(f"Expected 100 conditions, found {len(conditions)}")

    if standard.get("applies_to", {}).get("condition_count") != 100:
        errors.append("Evidence standard must explicitly apply to 100 conditions")

    source_map = data.get("sources", {})
    for slug, item in ((c.get("slug", "<missing>"), c) for c in conditions):
        keys = item.get("source_keys", [])
        if len(keys) < 2:
            errors.append(f"{slug}: fewer than two source keys")
            continue
        missing = [key for key in keys if key not in source_map]
        if missing:
            errors.append(f"{slug}: missing source keys {missing}")
            continue

        urls = [source_map[key].get("url", "") for key in keys]
        ref = item.get("reference_url", "")
        if ref:
            urls.append(ref)
        if not any(host_is_trusted(url) for url in urls):
            errors.append(f"{slug}: no source from the institutional allow-list")

        text = all_text(item)
        for phrase in BANNED_ABSOLUTES:
            if phrase in text:
                errors.append(f"{slug}: prohibited absolute claim: {phrase}")

    rights_notice = instruments.get("rights_notice", "")
    for marker in ("بنود", "مفاتيح تصحيح", "النسخة الأصلية", "مؤهل"):
        if marker not in rights_notice:
            errors.append(f"Instrument rights notice is missing: {marker}")

    instrument_text = all_text(instruments)
    for marker in PROTECTED_TEST_MARKERS:
        if marker in instrument_text:
            errors.append(f"Potential protected test content published: {marker}")

    for cluster, tools in instruments.get("clusters", {}).items():
        if len(tools) < 4:
            errors.append(f"{cluster}: fewer than four instrument options")
        for tool in tools:
            required = {"name", "owner", "use", "access", "caution"}
            if set(tool) != required:
                errors.append(f"{cluster}/{tool.get('name', '<unnamed>')}: invalid instrument schema")
            access = tool.get("access", "")
            caution = tool.get("caution", "")
            if not any(token in access for token in ("مقيّد", "ترخيص", "مختص", "شروط", "إجراء", "بحسب")):
                warnings.append(f"{cluster}/{tool.get('name')}: access wording needs manual review")
            if not caution.strip():
                errors.append(f"{cluster}/{tool.get('name')}: missing interpretation caution")

    required_source_types = {
        "international_classification",
        "international_standard",
        "international_convention",
        "testing_standard",
        "measurement_methodology",
        "test_adaptation_guideline",
        "evidence_certainty_methodology",
        "official_guideline",
    }
    present_types = {s.get("source_type") for s in standard.get("sources", [])}
    missing_types = sorted(required_source_types - present_types)
    if missing_types:
        errors.append(f"Evidence standard source-type coverage missing: {missing_types}")

    worked = standard.get("worked_examples", [])
    if not any(x.get("topic") == "التوحد والرياضيات أو المنطق" for x in worked):
        errors.append("Missing autism/numeracy anti-stereotype worked example")
    if not any(x.get("topic") == "الأولمبياد الخاص والرياضة الدامجة" for x in worked):
        errors.append("Missing sport/participation worked example")

    return {
        "version": 301,
        "status": "passed" if not errors else "failed",
        "condition_count": len(conditions),
        "source_count_v254": len(source_map),
        "instrument_cluster_count": len(instruments.get("clusters", {})),
        "errors": errors,
        "warnings": warnings,
        "external_clinical_review_completed": False,
        "global_accreditation_claim": False,
        "checked_files": [
            str(CONDITIONS.relative_to(ROOT)),
            str(INSTRUMENTS.relative_to(ROOT)),
            str(STANDARD.relative_to(ROOT)),
        ],
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
