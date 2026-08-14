#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

SECTION_REL = Path("sections/research-evidence-learning")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    section = root / SECTION_REL
    hub = section / "index.html"
    if not hub.exists():
        raise SystemExit(f"missing hub: {hub}")

    child_pages = sorted(section.glob("*/index.html"))
    count = len(child_pages)
    if count < 500:
        raise SystemExit(f"expected at least 500 child pages, found {count}")

    source = hub.read_text(encoding="utf-8")
    source = re.sub(
        r"موسوعة عربية لتعلم قراءة الدراسات وتقييم الدليل:\s*\d+\s*دليل منهجي",
        f"موسوعة عربية لتعلم قراءة الدراسات وتقييم الدليل: {count} دليل منهجي",
        source,
    )
    source = re.sub(
        r"البحث والدليل والتعلم \| \d+ دليل لفهم الدراسات وتقييم الأدلة \| منصة روافد",
        f"البحث والدليل والتعلم | {count} دليل لفهم الدراسات وتقييم الأدلة | منصة روافد",
        source,
    )

    expected_title = f"<title>البحث والدليل والتعلم | {count} دليل لفهم الدراسات وتقييم الأدلة | منصة روافد</title>"
    if expected_title not in source:
        raise SystemExit("hub title was not normalized to the actual child-page count")

    description_match = re.search(r'<meta name="description" content="([^"]+)"', source)
    if not description_match or f"{count} دليل منهجي" not in description_match.group(1):
        raise SystemExit("hub meta description does not expose the actual child-page count")

    item_count = re.search(r'"numberOfItems":(\d+)', source)
    if not item_count or int(item_count.group(1)) != count:
        raise SystemExit("hub ItemList numberOfItems is inconsistent with materialized child pages")

    source = source.replace(
        "<h1>البحث والدليل والتعلم</h1>",
        f'<h1>البحث والدليل والتعلم</h1><p class="note"><strong>{count} دليلًا تعليميًا منشورًا ومفهرسًا داخل هذا القسم.</strong> يُحدَّث هذا الرقم آليًا من الصفحات الفعلية حتى لا تنفصل بيانات SEO عن المحتوى المنشور.</p>',
        1,
    ) if "يُحدَّث هذا الرقم آليًا" not in source else source

    hub.write_text(source, encoding="utf-8")
    print({"hub": str(hub.relative_to(root)), "childPages": count, "status": "normalized"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
