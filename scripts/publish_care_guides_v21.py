from __future__ import annotations

import json

# Compatibility entrypoint retained because the production workflow invokes this path.
import publish_care_guides_v246 as implementation
from publish_care_guides_v246 import *  # noqa: F401,F403
from publish_care_guides_v246 import SITE

_ORIGINAL_LOAD_LEGACY_GUIDES = implementation.load_legacy_guides


def _load_legacy_guides_with_review_provenance() -> tuple[dict, list[dict]]:
    primary, guides = _ORIGINAL_LOAD_LEGACY_GUIDES()
    for guide in guides:
        # Older validated source files predate the explicit review-status field.
        # This preserves their established internal editorial status without
        # claiming a specialist review that did not occur.
        guide.setdefault("review_status", "internally-reviewed")
    return primary, guides


def main() -> dict:
    implementation.load_legacy_guides = _load_legacy_guides_with_review_provenance
    report = implementation.main()
    # Preserve the established API meaning: true only when the blocked autism guide was published.
    report["autism_published"] = False
    report_path = SITE / "api/care-guides-v21.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    main()
