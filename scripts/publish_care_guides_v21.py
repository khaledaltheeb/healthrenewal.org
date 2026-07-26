from __future__ import annotations

import json

# Compatibility entrypoint retained because the production workflow invokes this path.
from publish_care_guides_v246 import *  # noqa: F401,F403
from publish_care_guides_v246 import SITE
from publish_care_guides_v246 import main as _main


def main() -> dict:
    report = _main()
    # Preserve the established API meaning: true only when the blocked autism guide was published.
    report["autism_published"] = False
    report_path = SITE / "api/care-guides-v21.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    main()
