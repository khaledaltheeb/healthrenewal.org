from __future__ import annotations

import json
from pathlib import Path

import publish_care_guides_v246 as implementation
from publish_care_guides_v246 import *  # noqa: F401,F403
from publish_care_guides_v246 import SITE

import care_guides_wave_v400
import care_guides_wave_v401_fixed
import care_guides_wave_v402
import care_guides_wave_v403
import care_guides_wave_v404
import care_guides_wave_v405
import care_guides_wave_v406
import care_guides_wave_v407

ROOT = Path(__file__).resolve().parents[1]
WFADHD_EXPANSION = ROOT / "content/v18/adhd-wfadhd-authorized-expansion-ar.json"
_ORIGINAL_LOAD_LEGACY_GUIDES = implementation.load_legacy_guides


def _merge_unique(existing: list, additions: list) -> list:
    merged = list(existing)
    seen = {json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item).strip().casefold() for item in merged}
    for item in additions:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item).strip().casefold()
        if marker not in seen:
            merged.append(item); seen.add(marker)
    return merged


def _load_wfadhd_expansion() -> dict:
    if not WFADHD_EXPANSION.is_file(): raise FileNotFoundError(f"Missing authorized WFADHD expansion: {WFADHD_EXPANSION}")
    payload = json.loads(WFADHD_EXPANSION.read_text(encoding="utf-8"))
    if payload.get("language") != "ar" or not payload.get("target_slug"): raise ValueError("Invalid WFADHD expansion identity")
    if payload.get("provenance", {}).get("rights_status") != "written-translation-permission-received": raise ValueError("WFADHD expansion is missing the written-permission provenance marker")
    return payload


def _load_legacy_guides_with_review_provenance() -> tuple[dict, list[dict]]:
    primary, guides = _ORIGINAL_LOAD_LEGACY_GUIDES()
    for guide in guides: guide.setdefault("review_status", "internally-reviewed")
    expansion = _load_wfadhd_expansion(); target_slug = expansion["target_slug"]
    target = next((guide for guide in guides if guide.get("slug") == target_slug), None)
    if target is None: raise ValueError(f"WFADHD target guide not found: {target_slug}")
    for section_key, values in expansion.get("sections", {}).items():
        if not isinstance(values, list) or not values: raise ValueError(f"WFADHD section must be a non-empty list: {section_key}")
        target[section_key] = _merge_unique(target.get(section_key, []), values)
    sources_by_url = {source["url"]: source for source in target.get("sources", [])}
    for source in expansion.get("source_additions", []): sources_by_url[source["url"]] = source
    target["sources"] = list(sources_by_url.values()); target["reviewed_at"] = expansion["reviewed_at"]; target["translation_provenance"] = expansion["provenance"]; target["review_status"] = "source-authorized-internally-reviewed"
    return primary, guides


def main() -> dict:
    expansion = _load_wfadhd_expansion()
    implementation.SECTION_LABELS.update(expansion["section_labels"])
    implementation.TRUSTED_SOURCE_HOSTS.update({"www.adhd-federation.org", "adhd-federation.org"})
    implementation.load_legacy_guides = _load_legacy_guides_with_review_provenance
    wave_001_report = care_guides_wave_v400.install(implementation)
    wave_002_report = care_guides_wave_v401_fixed.install(implementation)
    wave_003_report = care_guides_wave_v402.install(implementation)
    wave_004_report = care_guides_wave_v403.install(implementation)
    wave_005_report = care_guides_wave_v404.install(implementation)
    wave_006_report = care_guides_wave_v405.install(implementation)
    wave_007_report = care_guides_wave_v406.install(implementation)
    wave_008_report = care_guides_wave_v407.install(implementation)
    report = implementation.main()
    report["autism_published"] = False; report["core_guides"] = report["source_guides"]
    report["wfadhd_authorized_expansion"] = {"target_slug": expansion["target_slug"], "version": expansion["version"], "sections": len(expansion["sections"]), "source_additions": len(expansion["source_additions"]), "permission_received_at": expansion["provenance"]["permission_received_at"], "rights_status": expansion["provenance"]["rights_status"], "independent_adaptation": True, "federation_endorsement_claimed": False}
    report["care_guides_wave_v400"] = wave_001_report; report["care_guides_wave_v401"] = wave_002_report; report["care_guides_wave_v402"] = wave_003_report; report["care_guides_wave_v403"] = wave_004_report; report["care_guides_wave_v404"] = wave_005_report; report["care_guides_wave_v405"] = wave_006_report; report["care_guides_wave_v406"] = wave_007_report; report["care_guides_wave_v407"] = wave_008_report
    (SITE / "api/care-guides-v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__": main()
