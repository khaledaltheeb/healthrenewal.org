from __future__ import annotations

import json
import sys
from pathlib import Path

from content_discovery_v219 import publish
from sync_public_api_discovery_v219 import sync

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")


if __name__ == "__main__":
    result = publish(SITE, ROOT)
    result["public_api_report"] = sync(ROOT, SITE, "published")
    print(json.dumps(result, ensure_ascii=False, indent=2))
