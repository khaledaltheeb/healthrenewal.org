from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
OPTIONAL_LINKS = (
    ("/care-guides/", "care-guides/index.html"),
    ("/daily-tools/", "daily-tools/index.html"),
)


def finalize(site: Path = SITE) -> dict[str, object]:
    page = site / "trust" / "index.html"
    if not page.is_file():
        raise SystemExit("Missing generated trust center page")
    text = page.read_text(encoding="utf-8")
    removed: list[str] = []
    for href, target in OPTIONAL_LINKS:
        if (site / target).is_file():
            continue
        pattern = re.compile(rf'<a\s+href="{re.escape(href)}"[^>]*>.*?</a>', re.S)
        text, count = pattern.subn("", text, count=1)
        if count:
            removed.append(href)
    page.write_text(text, encoding="utf-8")
    return {"removed_optional_links": removed, "remaining_links": text.count("<a ")}


if __name__ == "__main__":
    print(finalize())
