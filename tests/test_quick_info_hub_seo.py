from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "quick-info" / "index.html"
MANIFEST = ROOT / "api" / "v1" / "quick-info.json"


def _source() -> str:
    return HUB.read_text(encoding="utf-8")


def test_hub_has_meaningful_heading_hierarchy() -> None:
    source = _source()
    assert source.count("QUICK_INFO_HUB_SEO_V1_START") == 1
    assert "<h2 id=\"quick-info-use-guide\">كيف تستخدم قسم المعلومات السريعة؟</h2>" in source
    assert "<h3>ابدأ بالسؤال الأقرب إلى ما تريد فهمه، ثم انتقل إلى الخطوة التالية</h3>" in source


def test_hub_social_metadata_is_complete() -> None:
    source = _source()
    required = (
        'property="og:url"',
        'property="og:description"',
        'property="og:image:alt"',
        'name="twitter:card"',
        'name="twitter:title"',
        'name="twitter:description"',
        'name="twitter:image"',
        'name="twitter:image:alt"',
    )
    for fragment in required:
        assert fragment in source, fragment


def test_primary_card_images_have_topic_alt_text() -> None:
    source = _source()
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = payload["items"]
    assert payload["count"] == 250
    assert len(items) == 250
    for item in items:
        slug = item["slug"]
        title = item["title"]
        pattern = re.compile(
            rf'<img\b(?=[^>]*src=["\']/assets/quick-info/cards/{re.escape(slug)}\.png["\'])[^>]*alt=["\']بطاقة توضيحية لموضوع: {re.escape(title)}["\'][^>]*>',
            re.I | re.S,
        )
        assert pattern.search(source), slug


def test_no_unmarked_empty_image_alt_remains() -> None:
    source = _source()
    for tag in re.findall(r"<img\b[^>]*>", source, re.I | re.S):
        if re.search(r'\balt=["\']["\']', tag, re.I):
            assert 'role="presentation"' in tag
            assert 'aria-hidden="true"' in tag
