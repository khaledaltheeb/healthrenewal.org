from __future__ import annotations

import json
from pathlib import Path

# Compatibility entrypoint retained because the production workflow invokes this path.
import publish_care_guides_v246 as implementation
from publish_care_guides_v246 import *  # noqa: F401,F403
from publish_care_guides_v246 import SITE

ROOT = Path(__file__).resolve().parents[1]
WFADHD_EXPANSION = ROOT / "content/v18/adhd-wfadhd-authorized-expansion-ar.json"
_ORIGINAL_LOAD_LEGACY_GUIDES = implementation.load_legacy_guides


def _merge_unique(existing: list, additions: list) -> list:
    merged = list(existing)
    seen = {
        json.dumps(item, ensure_ascii=False, sort_keys=True)
        if isinstance(item, (dict, list))
        else str(item).strip().casefold()
        for item in merged
    }
    for item in additions:
        marker = (
            json.dumps(item, ensure_ascii=False, sort_keys=True)
            if isinstance(item, (dict, list))
            else str(item).strip().casefold()
        )
        if marker not in seen:
            merged.append(item)
            seen.add(marker)
    return merged


def _load_wfadhd_expansion() -> dict:
    if not WFADHD_EXPANSION.is_file():
        raise FileNotFoundError(f"Missing authorized WFADHD expansion: {WFADHD_EXPANSION}")
    payload = json.loads(WFADHD_EXPANSION.read_text(encoding="utf-8"))
    if payload.get("language") != "ar" or not payload.get("target_slug"):
        raise ValueError("Invalid WFADHD expansion identity")
    if payload.get("provenance", {}).get("rights_status") != "written-translation-permission-received":
        raise ValueError("WFADHD expansion is missing the written-permission provenance marker")
    return payload


def _load_legacy_guides_with_review_provenance() -> tuple[dict, list[dict]]:
    primary, guides = _ORIGINAL_LOAD_LEGACY_GUIDES()
    for guide in guides:
        # Older validated source files predate the explicit review-status field.
        # This preserves their established internal editorial status without
        # claiming a specialist review that did not occur.
        guide.setdefault("review_status", "internally-reviewed")

    expansion = _load_wfadhd_expansion()
    target_slug = expansion["target_slug"]
    target = next((guide for guide in guides if guide.get("slug") == target_slug), None)
    if target is None:
        raise ValueError(f"WFADHD target guide not found: {target_slug}")

    for section_key, values in expansion.get("sections", {}).items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"WFADHD section must be a non-empty list: {section_key}")
        target[section_key] = _merge_unique(target.get(section_key, []), values)

    sources_by_url = {source["url"]: source for source in target.get("sources", [])}
    for source in expansion.get("source_additions", []):
        sources_by_url[source["url"]] = source
    target["sources"] = list(sources_by_url.values())
    target["reviewed_at"] = expansion["reviewed_at"]
    target["translation_provenance"] = expansion["provenance"]
    target["review_status"] = "source-authorized-internally-reviewed"
    return primary, guides


def main() -> dict:
    expansion = _load_wfadhd_expansion()
    implementation.SECTION_LABELS.update(expansion["section_labels"])
    implementation.TRUSTED_SOURCE_HOSTS.update(
        {"www.adhd-federation.org", "adhd-federation.org"}
    )
    implementation.load_legacy_guides = _load_legacy_guides_with_review_provenance
    report = implementation.main()
    # Preserve established API meanings consumed by later production publishers.
    report["autism_published"] = False
    report["core_guides"] = report["source_guides"]
    report["wfadhd_authorized_expansion"] = {
        "target_slug": expansion["target_slug"],
        "version": expansion["version"],
        "sections": len(expansion["sections"]),
        "source_additions": len(expansion["source_additions"]),
        "permission_received_at": expansion["provenance"]["permission_received_at"],
        "rights_status": expansion["provenance"]["rights_status"],
        "independent_adaptation": True,
        "federation_endorsement_claimed": False,
    }
    report_path = SITE / "api/care-guides-v21.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    main()
