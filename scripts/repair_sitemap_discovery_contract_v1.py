#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_complete_sitemap_v360.py"

OLD = '''    robots = (\n        "User-agent: *\\n"\n        "Allow: /\\n\\n"\n        f"Sitemap: {BASE_URL}sitemap.xml\\n"\n    ).encode("utf-8")\n'''
NEW = '''    robots = (\n        "User-agent: *\\n"\n        "Allow: /\\n\\n"\n        f"Sitemap: {BASE_URL}sitemap-index.xml\\n"\n        f"Sitemap: {BASE_URL}sitemap.xml\\n"\n    ).encode("utf-8")\n'''


def main() -> int:
    source = PUBLISHER.read_text(encoding="utf-8")
    if NEW not in source:
        if OLD not in source:
            raise SystemExit("Expected robots publisher block was not found")
        PUBLISHER.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")

    subprocess.run(
        ["python", "scripts/publish_complete_sitemap_v360.py", ".", "--minimum-urls", "1"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["python", "scripts/validate_sitemap_discovery_contract.py"],
        cwd=ROOT,
        check=True,
    )
    print("sitemap discovery contract repair applied and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())