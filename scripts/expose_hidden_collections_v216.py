from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
VERIFY = ROOT / "scripts" / "verify_homepage_v19.py"
BASE = "https://healthrenewal.org/"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source marker, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise SystemExit(f"{label}: expected one regex match, found {count}")
    return updated


def patch_index() -> dict:
    text = INDEX.read_text(encoding="utf-8")

    text = regex_once(
        text,
        r"<title>.*?</title>",
        "<title>منصة روافد | موسوعة ومكتبة ومقارنات عربية</title>",
        "title",
    )
    text = regex_once(
        text,
        r'<meta name="description" content="[^"]+">',
        '<meta name="description" content="منصة عربية مؤسسية للصحة النفسية والأشخاص ذوي الاحتياجات الخاصة، تضم موسوعة ومكتبة أكاديمية ومقارنات وأدلة عملية ومقاييس استكشافية ومحتوى موثقًا يخدم الأسرة والمختص والمعلم.">',
        "description",
    )
    text = regex_once(
        text,
        r'<meta name="keywords" content="[^"]+">',
        '<meta name="keywords" content="الصحة النفسية,علم النفس,مصطلحات علم النفس,الموسوعة النفسية,المكتبة النفسية,المكتبة الأكاديمية,مقارنات نفسية,الفرق بين الاضطرابات النفسية,الأشخاص ذوو الاحتياجات الخاصة,ذوو الاحتياجات الخاصة,التربية الدامجة,التربية الخاصة,الصحة النفسية للطفل,الصحة النفسية للأسرة,التقييم النفسي,التقييم النفسي للأطفال,المقاييس النفسية,الاختبارات النفسية,القدرات المعرفية,العلاج النفسي,العلاج السلوكي المعرفي,الدعم النفسي,الدعم الأسري,التدخل المبكر,التأهيل النفسي,التوحد,اضطراب طيف التوحد,فرط الحركة وتشتت الانتباه,متلازمة داون,صعوبات التعلم,التواصل المعزز والبديل,جودة خدمات التربية الخاصة">',
        "keywords",
    )

    meta_anchor = '<meta name="color-scheme" content="light">'
    meta_block = meta_anchor + "\n" + "\n".join(
        (
            '<meta name="application-name" content="منصة روافد">',
            '<meta name="subject" content="الصحة النفسية وعلم النفس والتربية الدامجة وذوو الاحتياجات الخاصة">',
            '<meta name="audience" content="الأفراد والأسر والمعلمون والمرشدون والمختصون ومقدمو الخدمات">',
            '<meta name="distribution" content="global">',
            '<meta name="referrer" content="strict-origin-when-cross-origin">',
        )
    )
    text = replace_once(text, meta_anchor, meta_block, "institutional metadata")

    search_link = '<link rel="search" type="application/opensearchdescription+xml" title="البحث في منصة روافد" href="/opensearch.xml">'
    search_block = search_link + "\n" + "\n".join(
        (
            f'<link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml">',
            f'<link rel="alternate" type="application/json" title="واجهة بيانات المنصة" href="{BASE}api/v1/platform.json">',
        )
    )
    text = replace_once(text, search_link, search_block, "discovery links")

    text = regex_once(
        text,
        r'<meta property="og:title" content="[^"]+">',
        '<meta property="og:title" content="منصة الصحة النفسية | موسوعة ومكتبة ومقارنات عربية">',
        "Open Graph title",
    )
    text = regex_once(
        text,
        r'<meta property="og:description" content="[^"]+">',
        '<meta property="og:description" content="موسوعة ومكتبة أكاديمية ومقارنات نفسية وأدلة تطبيقية للأسرة والطفل والتربية الدامجة ومنصة تقييم استكشافية ضمن منهج موثق يحترم الإنسان.">',
        "Open Graph description",
    )
    text = regex_once(
        text,
        r'<meta name="twitter:title" content="[^"]+">',
        '<meta name="twitter:title" content="منصة الصحة النفسية | موسوعة ومكتبة ومقارنات عربية">',
        "Twitter title",
    )
    text = regex_once(
        text,
        r'<meta name="twitter:description" content="[^"]+">',
        '<meta name="twitter:description" content="موسوعة ومكتبة ومقارنات وأدلة عربية موثوقة في الصحة النفسية والتربية الدامجة ودعم الأسرة والمختص.">',
        "Twitter description",
    )
    twitter_image = f'<meta name="twitter:image" content="{BASE}assets/brand/social-card.svg">'
    text = replace_once(
        text,
        twitter_image,
        twitter_image + '\n<meta name="twitter:image:alt" content="شعار منصة روافد">',
        "Twitter image alt",
    )

    webapi_node = f'{{"@type":"WebAPI","name":"واجهة بيانات المنصة","url":"{BASE}api/"}}'
    advanced_nodes = "\n".join(
        (
            f'{{"@type":"CollectionPage","name":"مكتبة المقارنات النفسية","url":"{BASE}comparisons/"}},',
            f'{{"@type":"CollectionPage","name":"المكتبة الأكاديمية للصحة النفسية","url":"{BASE}library/"}},',
            f'{{"@type":"CollectionPage","name":"الأسئلة الموجهة للاستكشاف","url":"{BASE}guided-assessment/"}},',
            f'{{"@type":"CollectionPage","name":"المراكز الموضوعية","url":"{BASE}hubs/"}},',
            webapi_node,
        )
    )
    text = replace_once(text, webapi_node, advanced_nodes, "JSON-LD advanced collections")

    nav_prefix = '<nav class="nav" aria-label="التنقل الرئيسي"><a href="start-here/">ابدأ من هنا</a><a href="encyclopedia/">الموسوعة</a>'
    text = replace_once(
        text,
        nav_prefix,
        nav_prefix + '<a href="comparisons/">المقارنات</a><a href="library/">المكتبة</a>',
        "primary navigation",
    )

    text = regex_once(
        text,
        r'<p class="lead">.*?</p>',
        '<p class="lead">تجمع المنصة موسوعة علم النفس والصحة النفسية، ومكتبة أكاديمية، ومقارنات تشرح الفروق بين الحالات، وأدلة التعامل، ودعم الأسرة والطفل، ومسارات الأشخاص ذوي الاحتياجات الخاصة والتربية الدامجة، وأدوات الاستكشاف والتقييم ضمن بنية تربط التعريف بالممارسة والمصادر.</p>',
        "hero lead",
    )
    encyclopedia_action = '<a class="button secondary" href="encyclopedia/">ابحث في الموسوعة</a>'
    text = replace_once(
        text,
        encyclopedia_action,
        encyclopedia_action + '<a class="button secondary" href="comparisons/">استكشف المقارنات</a><a class="button secondary" href="library/">افتح المكتبة</a>',
        "hero actions",
    )
    journey_first = '<li><strong>لفهم مصطلح أو حالة:</strong> استخدم الموسوعة والمراكز الموضوعية.</li>'
    text = replace_once(
        text,
        journey_first,
        journey_first
        + '<li><strong>لمعرفة الفرق بين حالتين:</strong> استخدم مكتبة المقارنات المنظمة.</li>'
        + '<li><strong>للتعلم والقراءة المتعمقة:</strong> انتقل إلى المكتبة الأكاديمية.</li>',
        "journey discovery",
    )

    resources_marker = '<section class="section" aria-labelledby="resources">'
    advanced_section = (
        '<section class="section" aria-labelledby="collections"><p class="eyebrow">بوابات معرفة متقدمة</p>'
        '<h2 id="collections">المكتبة والمقارنات والمسارات المتخصصة</h2>'
        '<p class="section-intro">تجمع هذه البوابات المحتوى المتخصص في مسارات واضحة قابلة للتصفح. كل بوابة تقود إلى صفحات تفصيلية وروابط داخلية مرتبطة بنية بحث محددة.</p>'
        '<div class="cards">'
        '<article class="card"><h3>مكتبة المقارنات النفسية</h3><p>مقارنات منظمة تشرح أوجه التشابه والاختلاف بين الحالات والمفاهيم والأعراض، وتوضح ما لا يمكن حسمه بالمقارنة وحدها.</p><a href="comparisons/">فتح المقارنات</a></article>'
        '<article class="card"><h3>المكتبة الأكاديمية</h3><p>مواد مصنفة للقراءة والتعلم في علم النفس والصحة النفسية والتقييم والعلاج، مع تنظيم موضوعي يسهل اكتشاف المحتوى.</p><a href="library/">فتح المكتبة</a></article>'
        '<article class="card"><h3>الأسئلة الموجهة للاستكشاف</h3><p>أسئلة تعليمية تساعد على جمع السياق وترتيب الملاحظات قبل طلب التقييم، من دون تحويل الإجابات إلى تشخيص آلي.</p><a href="guided-assessment/">فتح الأسئلة الموجهة</a></article>'
        '<article class="card"><h3>المراكز الموضوعية</h3><p>بوابات تربط المصطلحات والأدلة والمقاييس والموضوعات ذات الصلة لتقليل التشتت وتحسين الوصول إلى المعرفة.</p><a href="hubs/">فتح المراكز الموضوعية</a></article>'
        '<article class="card"><h3>مقاييس الاستكشاف العامة</h3><p>صفحات تعريفية واستكشافية تشرح الغرض والحدود وطريقة القراءة الآمنة، مع التأكيد أن النتيجة ليست تشخيصًا مستقلًا.</p><a href="assessments/">فتح المقاييس</a></article>'
        '<article class="card"><h3>الاختبارات والمهام المعرفية</h3><p>مهام تعليمية للانتباه والذاكرة والاستدلال تساعد على فهم القدرات التي تقيسها الأدوات وحدود استخدامها.</p><a href="cognitive-tests/">فتح المهام المعرفية</a></article>'
        '</div></section>\n'
        + resources_marker
    )
    text = replace_once(text, resources_marker, advanced_section, "advanced collection section")

    footer_old = '<div class="footer-links"><a href="start-here/">ابدأ من هنا</a><a href="encyclopedia/">الموسوعة</a>'
    footer_new = footer_old + '<a href="comparisons/">المقارنات</a><a href="library/">المكتبة</a><a href="hubs/">المراكز الموضوعية</a>'
    text = replace_once(text, footer_old, footer_new, "footer discovery")

    if text.count('<h1>') != 1:
        raise SystemExit("Homepage must retain exactly one H1")
    if len(re.findall(r'<h2\b', text)) < 5 or len(re.findall(r'<h3\b', text)) < 22:
        raise SystemExit("Homepage heading hierarchy is incomplete")
    if any(token in text for token in ("قيد الإعداد", "قيد التوسع", "لا نشر قبل البوابات")):
        raise SystemExit("Operational copy leaked into public homepage")

    INDEX.write_text(text, encoding="utf-8")
    description = re.search(r'<meta name="description" content="([^"]+)"', text)
    keywords = re.search(r'<meta name="keywords" content="([^"]+)"', text)
    return {
        "description_chars": len(description.group(1)) if description else 0,
        "keyword_items": len([item for item in keywords.group(1).split(",") if item.strip()]) if keywords else 0,
        "h1": len(re.findall(r'<h1\b', text)),
        "h2": len(re.findall(r'<h2\b', text)),
        "h3": len(re.findall(r'<h3\b', text)),
    }


def patch_verifier() -> dict:
    text = VERIFY.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '    "provider-assessment-demo/",\n    "trust/",',
        '    "provider-assessment-demo/",\n    "comparisons/",\n    "library/",\n    "guided-assessment/",\n    "hubs/",\n    "assessments/",\n    "cognitive-tests/",\n    "trust/",',
        "verifier required links",
    )
    text = replace_once(
        text,
        '    assert \'<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>\' in source\n',
        '    assert \'<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>\' in source\n'
        '    assert "مكتبة المقارنات النفسية" in source, "Comparisons collection is not visibly described"\n'
        '    assert "المكتبة الأكاديمية" in source, "Academic library is not visibly described"\n',
        "verifier visible collections",
    )
    text = replace_once(
        text,
        '    assert len(re.findall(r"<h2\\b", source)) >= 4, "Homepage needs structured H2 sections"\n    assert len(re.findall(r"<h3\\b", source)) >= 16, "Homepage needs discoverable H3 cards"',
        '    assert len(re.findall(r"<h2\\b", source)) >= 5, "Homepage needs structured H2 sections"\n    assert len(re.findall(r"<h3\\b", source)) >= 22, "Homepage needs discoverable H3 cards"',
        "verifier headings",
    )
    text = replace_once(
        text,
        '    assert description and 100 <= len(description.group(1)) <= 220',
        '    assert description and 120 <= len(description.group(1)) <= 220',
        "verifier description",
    )
    text = replace_once(
        text,
        '    assert len(keyword_items) >= 12, "Homepage keyword coverage is too narrow"\n    assert {"الصحة النفسية", "علم النفس", "التربية الدامجة"}.issubset(keyword_items)',
        '    assert len(keyword_items) >= 24, "Homepage keyword coverage is too narrow"\n'
        '    assert {"الصحة النفسية", "علم النفس", "التربية الدامجة", "المكتبة النفسية", "مقارنات نفسية", "الاختبارات النفسية"}.issubset(keyword_items)',
        "verifier keywords",
    )
    text = replace_once(
        text,
        '        \'<link rel="search" type="application/opensearchdescription+xml"\',',
        '        \'<link rel="search" type="application/opensearchdescription+xml"\',\n'
        f'        \'<link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml">\',',
        "verifier sitemap metadata",
    )
    text = replace_once(
        text,
        '    assert any(part.get("@type") == "WebAPI" for part in collection.get("hasPart", []))',
        '    parts = collection.get("hasPart", [])\n'
        '    assert any(part.get("@type") == "WebAPI" for part in parts)\n'
        '    part_urls = {part.get("url") for part in parts}\n'
        f'    assert "{BASE}comparisons/" in part_urls\n'
        f'    assert "{BASE}library/" in part_urls\n'
        f'    assert "{BASE}guided-assessment/" in part_urls',
        "verifier JSON-LD collections",
    )
    text = replace_once(
        text,
        '                "contract": "institutional-home-api-brand-v215",',
        '                "contract": "institutional-home-discovery-seo-v216",',
        "verifier contract",
    )
    text = replace_once(
        text,
        '                "operational_copy_hidden": True,',
        '                "comparisons_linked": True,\n'
        '                "library_linked": True,\n'
        '                "guided_assessment_linked": True,\n'
        '                "operational_copy_hidden": True,',
        "verifier report flags",
    )

    VERIFY.write_text(text, encoding="utf-8")
    return {
        "contract": "institutional-home-discovery-seo-v216",
    }


def main() -> None:
    if not INDEX.is_file() or not VERIFY.is_file():
        raise SystemExit("Required homepage source or verifier is missing")
    report = {
        "version": 216,
        "homepage": patch_index(),
        "verifier": patch_verifier(),
        "collections": [
            "comparisons/",
            "library/",
            "guided-assessment/",
            "hubs/",
            "assessments/",
            "cognitive-tests/",
        ],
        "status": "patched",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
