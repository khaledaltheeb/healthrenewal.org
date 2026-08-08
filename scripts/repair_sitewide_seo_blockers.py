#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOCIAL_IMAGE = "https://healthrenewal.org/assets/quick-info/quick-info-cover.png"

HUBS = {
    "learning-paths/all-pages/index.html": {
        "title": "الفهرس الكامل لمسارات التعلم العربية | منصة روافد",
        "description": "فهرس شامل للصفحات المنشورة ضمن مسارات التعلم العربية في منصة روافد، مع وصول مباشر إلى الأدلة والموضوعات والمصادر المرتبطة بكل مسار.",
        "h2": "كل الصفحات المنشورة ضمن مسارات التعلم",
        "url": "https://healthrenewal.org/learning-paths/all-pages/",
    },
    "sectors/all-pages/index.html": {
        "title": "الفهرس الكامل لقطاعات الصحة النفسية | منصة روافد",
        "description": "فهرس شامل للصفحات المنشورة في قطاعات الصحة النفسية بمنصة روافد، للوصول المنظم إلى الأدلة والموضوعات والخدمات والمصادر حسب كل قطاع.",
        "h2": "كل الصفحات المنشورة ضمن قطاعات الصحة النفسية",
        "url": "https://healthrenewal.org/sectors/all-pages/",
    },
    "special-needs/all-pages/index.html": {
        "title": "الفهرس الكامل لمركز ذوي الاحتياجات الخاصة | منصة روافد",
        "description": "فهرس شامل للصفحات المنشورة في مركز ذوي الاحتياجات الخاصة بمنصة روافد، يجمع الأدلة والحقوق والتعليم والتأهيل والخدمات والمصادر في مسار واحد.",
        "h2": "كل الصفحات المنشورة في مركز ذوي الاحتياجات الخاصة",
        "url": "https://healthrenewal.org/special-needs/all-pages/",
    },
}


def set_title(source: str, title: str) -> str:
    return re.sub(r"<title>.*?</title>", f"<title>{title}</title>", source, count=1, flags=re.I | re.S)


def set_description(source: str, description: str) -> str:
    tag = f'<meta name="description" content="{description}">'
    pattern = r'<meta\s+name=["\']description["\'][^>]*>'
    if re.search(pattern, source, flags=re.I):
        return re.sub(pattern, tag, source, count=1, flags=re.I)
    return source.replace("</title>", "</title>" + tag, 1)


def add_h2(source: str, heading: str) -> str:
    if re.search(r"<h2\b", source, flags=re.I):
        return source
    match = re.search(r"</h1>", source, flags=re.I)
    if not match:
        raise RuntimeError("No H1 found for H2 insertion")
    return source[: match.end()] + f'<h2 class="seo-index-section-heading">{heading}</h2>' + source[match.end() :]


def social_tags(title: str, description: str, url: str) -> str:
    return (
        f'<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{title}">'
        f'<meta property="og:description" content="{description}">'
        f'<meta property="og:url" content="{url}">'
        f'<meta property="og:image" content="{SOCIAL_IMAGE}">'
        f'<meta property="og:image:alt" content="منصة روافد للصحة النفسية والدمج والتمكين">'
        f'<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{title}">'
        f'<meta name="twitter:description" content="{description}">'
        f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">'
        f'<meta name="twitter:image:alt" content="منصة روافد للصحة النفسية والدمج والتمكين">'
    )


def ensure_social(source: str, title: str, description: str, url: str) -> str:
    required = ["og:title", "og:description", "og:url", "og:type", "og:image", "og:image:alt",
                "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"]
    present = [name for name in required if name in source]
    if present:
        if len(present) != len(required):
            raise RuntimeError(f"Partial social metadata state: {present}")
        return source
    if "</head>" not in source.lower():
        raise RuntimeError("No closing head tag")
    return re.sub(r"</head>", social_tags(title, description, url) + "</head>", source, count=1, flags=re.I)


def repair_hub(relative: str, cfg: dict[str, str]) -> None:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    source = path.read_text(encoding="utf-8")
    source = set_title(source, cfg["title"])
    source = set_description(source, cfg["description"])
    source = add_h2(source, cfg["h2"])
    source = ensure_social(source, cfg["title"], cfg["description"], cfg["url"])
    path.write_text(source, encoding="utf-8")


def materialize_adhd_family_guide() -> None:
    # The legacy ADHD guide predates the later review_status contract. Rendering
    # this one existing source record directly avoids inventing a review status,
    # while still using the exact institutional v246 renderer. Health-publication
    # safety is independently re-checked on the PR before merge.
    scripts = ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    from publish_care_guides_v246 import guide_page  # type: ignore

    payload = json.loads((ROOT / "content/v18/care-guides-adhd-ar.json").read_text(encoding="utf-8"))
    guides = [item for item in payload.get("guides", []) if item.get("slug") == "adhd-family-practical-guide"]
    if len(guides) != 1:
        raise RuntimeError(f"Expected exactly one ADHD family guide source; found {len(guides)}")
    guide = guides[0]
    if guide.get("review_status"):
        raise RuntimeError("Legacy ADHD source unexpectedly gained review_status; use the full publisher instead")
    source = guide_page(guide)
    if "دليل الأسرة العملي لاضطراب نقص الانتباه وفرط النشاط" not in source:
        raise RuntimeError("Rendered ADHD guide lost its expected title")

    if 'property="og:image"' not in source:
        extras = (
            f'<meta property="og:image" content="{SOCIAL_IMAGE}">'
            f'<meta property="og:image:alt" content="دليل الأسرة العملي لاضطراب نقص الانتباه وفرط النشاط ADHD">'
            f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">'
            f'<meta name="twitter:image:alt" content="دليل الأسرة العملي لاضطراب نقص الانتباه وفرط النشاط ADHD">'
        )
        source = re.sub(r"</head>", extras + "</head>", source, count=1, flags=re.I)

    target = ROOT / "care-guides/adhd-family-practical-guide/index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


def main() -> int:
    materialize_adhd_family_guide()
    for relative, cfg in HUBS.items():
        repair_hub(relative, cfg)
    print({"repaired": ["care-guides/adhd-family-practical-guide/index.html", *HUBS.keys()]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
