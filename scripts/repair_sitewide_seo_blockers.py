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

QUESTION_HEADING_REWRITES = {
    "evidence-guides/aac-home-school-guide/index.html": {
        "1. وسيلة التواصل حق وليست مكافأة": "لماذا تُعد وسيلة التواصل حقًا وليست مكافأة؟",
        "2. خطة مشتركة بين المنزل والمدرسة ومقدم الخدمة": "كيف تُبنى خطة مشتركة بين المنزل والمدرسة ومقدم الخدمة؟",
    },
    "evidence-guides/inclusive-digital-safety-and-exploitation-prevention-guide/index.html": {
        "1. خطة أمان رقمي مشتركة بين المنزل والمدرسة دون حرمان من التقنية": "كيف نبني خطة أمان رقمي مشتركة بين المنزل والمدرسة دون حرمان من التقنية؟",
        "2. علامات الاستدراج والابتزاز والاستغلال الرقمي وكيفية الاستجابة": "كيف نميّز علامات الاستدراج والابتزاز والاستغلال الرقمي ونستجيب لها؟",
    },
    "evidence-guides/inclusive-toileting-personal-care-guide/index.html": {
        "1. قبل التدريب: الاستعداد وفحص الألم والإمساك والمشكلات الطبية": "متى يكون الطفل مستعدًا للتدريب وما الذي يجب فحصه أولًا؟",
        "2. روتين تدريجي وتواصل وتكييف حسي دون إكراه": "كيف نبني روتينًا تدريجيًا مع تكييف حسي دون إكراه؟",
    },
    "evidence-guides/puberty-body-safety-inclusive-guide/index.html": {
        "1. الاستعداد للبلوغ بلغة واضحة ومناسبة للنمو": "كيف نستعد للبلوغ بلغة واضحة ومناسبة للنمو؟",
        "2. الخصوصية والموافقة والحدود دون تعليم الطاعة العمياء": "كيف نعلّم الخصوصية والموافقة والحدود دون طاعة عمياء؟",
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

    # Modernize only publication semantics; do not alter the legacy source record.
    source = re.sub(r'<meta\s+name=["\']keywords["\'][^>]*>', '', source, count=1, flags=re.I)
    if not re.search(r'<h3\b', source, flags=re.I):
        if not re.search(r'</h2>', source, flags=re.I):
            raise RuntimeError("Rendered ADHD guide has no H2 for deep-content hierarchy")
        source = re.sub(
            r'</h2>',
            '</h2><h3>كيف تستخدم الأسرة هذا الجزء عمليًا؟</h3>',
            source,
            count=1,
            flags=re.I,
        )

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


def replace_heading_text(source: str, old: str, new: str, level: int = 2, new_level: int | None = None) -> str:
    tag = f"h{level}"
    replacement_tag = f"h{new_level or level}"
    pattern = rf'(<{tag}\b[^>]*>)\s*{re.escape(old)}\s*(</{tag}>)'
    match = re.search(pattern, source, flags=re.I)
    if not match:
        # Idempotence: accept the already-rewritten semantic heading.
        if re.search(rf'<{replacement_tag}\b[^>]*>\s*{re.escape(new)}\s*</{replacement_tag}>', source, flags=re.I):
            return source
        raise RuntimeError(f"Expected heading not found: {old}")
    attrs = re.match(rf'<{tag}\b([^>]*)>', match.group(1), flags=re.I)
    attr_text = attrs.group(1) if attrs else ""
    replacement = f'<{replacement_tag}{attr_text}>{new}</{replacement_tag}>'
    return source[:match.start()] + replacement + source[match.end():]


def repair_heading_contract_drift() -> None:
    # Evidence guides already have deep H3 structure. Convert two existing section
    # headings per guide into genuine user questions instead of appending generic SEO text.
    for relative, rewrites in QUESTION_HEADING_REWRITES.items():
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        for old, new in rewrites.items():
            source = replace_heading_text(source, old, new, level=2)
        path.write_text(source, encoding="utf-8")

    # Accessible travel already contains many visible questions; it only lacked H3 depth.
    travel = ROOT / "guides/accessible-travel-planning/index.html"
    source = travel.read_text(encoding="utf-8")
    source = replace_heading_text(source, "أسئلة الإقامة قبل الحجز", "أسئلة الإقامة قبل الحجز", level=2, new_level=3)
    travel.write_text(source, encoding="utf-8")

    # The all-pages index is a navigation surface; add concise, page-specific guidance
    # rather than changing the names of the 149 linked resources.
    special_index = ROOT / "special-needs/all-pages/index.html"
    source = special_index.read_text(encoding="utf-8")
    marker = 'data-seo-index-guidance="special-needs-v1"'
    if marker not in source:
        pattern = r'(<h2\b[^>]*>\s*كل الصفحات المنشورة في مركز ذوي الاحتياجات الخاصة\s*</h2>)'
        guidance = (
            r'\1<section data-seo-index-guidance="special-needs-v1">'
            '<h3>كيف تستخدم هذا الفهرس للوصول إلى الدليل المناسب؟</h3>'
            '<p>ابدأ بالمجال الأقرب لاحتياجك، ثم افتح الصفحة المتخصصة بدل التنقل العشوائي بين العناوين.</p>'
            '<h3>كيف تختار بين الأدلة والخدمات والحقوق والتقنيات المساعدة؟</h3>'
            '<p>اختر نوع الصفحة بحسب هدفك: فهم الموضوع، اتخاذ خطوة عملية، مراجعة حق أو خدمة، أو مقارنة خيار تقني.</p>'
            '</section>'
        )
        source, count = re.subn(pattern, guidance, source, count=1, flags=re.I)
        if count != 1:
            raise RuntimeError("Special-needs all-pages H2 not found for guidance insertion")
    special_index.write_text(source, encoding="utf-8")

    # Communication guide is already an index of six focused guides. Promote the first
    # two navigation headings into a natural question hierarchy without adding filler.
    communication = ROOT / "special-needs/guides/communication/index.html"
    source = communication.read_text(encoding="utf-8")
    source = replace_heading_text(source, "تقييم إتاحة التواصل", "كيف نبدأ بتقييم إتاحة التواصل؟", level=2)
    source = replace_heading_text(
        source,
        "تقييم الحاجة إلى التواصل المعزز والبديل AAC",
        "متى نقيّم الحاجة إلى التواصل المعزز والبديل AAC؟",
        level=2,
        new_level=3,
    )
    communication.write_text(source, encoding="utf-8")


def main() -> int:
    materialize_adhd_family_guide()
    for relative, cfg in HUBS.items():
        repair_hub(relative, cfg)
    repair_heading_contract_drift()
    repaired = [
        "care-guides/adhd-family-practical-guide/index.html",
        *HUBS.keys(),
        *QUESTION_HEADING_REWRITES.keys(),
        "guides/accessible-travel-planning/index.html",
        "special-needs/guides/communication/index.html",
    ]
    print({"repaired": repaired})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
