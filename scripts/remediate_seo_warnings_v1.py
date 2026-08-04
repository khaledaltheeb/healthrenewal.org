#!/usr/bin/env python3
"""Resolve deterministic SEO findings without removing editorial content.

The processor is intentionally additive/conservative. It preserves body copy,
existing routes, source attribution and bespoke page structure while repairing
metadata, crawlability and structured-data contracts detected by the site-wide
audit.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

from social_metadata_v2 import ensure_social_metadata

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"

TITLE_MAP = {
    "family-guide/conditions/neurofibromatosis-type-1/index.html": "الورام الليفي العصبي النوع الأول NF1 | دليل الأسرة",
    "magazine/adhd-personalized-neurofeedback-sham-rct-2026.html": "التغذية الراجعة العصبية وADHD | تجربة عشوائية 2026",
    "magazine/adhd-rhythmic-music-game-rct-2026.html": "لعبة موسيقية إيقاعية لأعراض ADHD | تجربة عشوائية 2026",
    "magazine/autism-behavioral-domains-network-meta-analysis-2026.html": "تدخلات التوحد حسب المجالات السلوكية | تحليل شبكي 2026",
    "magazine/autism-mentorship-program-pilot-rct-2026.html": "برنامج إرشاد للأشخاص ذوي التوحد | دراسة تجريبية 2026",
    "magazine/aya-cancer-digital-mental-health-meta-analysis-2026.html": "الصحة النفسية الرقمية لليافعين المصابين بالسرطان | تحليل 2026",
    "magazine/intellectual-disability-healthcare-transition-review-2026.html": "الانتقال للرعاية الصحية لدى ذوي الإعاقة الذهنية | مراجعة 2026",
    "magazine/neurodevelopmental-disabilities-navigator-act-parent-stress-rct-2026.html": "Navigator ACT لضغط والدي ذوي الإعاقات النمائية | تجربة 2026",
    "trust/index.html": "منهجية الثقة والمصادر والمراجعة | منصة روافد",
    "addiction/emerging/dissociative-drug-related-harms/index.html": "مخاطر الكيتامين والمواد التفارقية | مركز الإدمان",
    "addiction/populations/complex-medical-conditions/index.html": "الإدمان والحالات الطبية المعقدة | مركز التعافي",
    "addiction/populations/rural-remote-limited-resources/index.html": "علاج الإدمان في المناطق الريفية والبعيدة | روافد",
    "addiction/tools/discharge-follow-up-plan/index.html": "خطة المتابعة بعد الخروج من علاج الإدمان | روافد",
    "evidence-guides/body-dysmorphic-disorder-safe-guide/index.html": "اضطراب تشوه صورة الجسد | دليل آمن بلا وصم",
    "evidence-guides/inclusive-digital-safety-and-exploitation-prevention-guide/index.html": "الأمان الرقمي والحماية من الاستغلال | دليل دامج",
    "evidence-guides/pain-distress-communication-support-guide/index.html": "التواصل عن الألم والمرض | خطة للمنزل والمدرسة",
    "evidence-guides/predictable-routines-transitions-guide/index.html": "الروتين المتوقع والانتقالات اليومية | دليل عملي",
    "evidence-guides/school-attendance-distress-support-guide/index.html": "الضيق المرتبط بالمدرسة | خطة دعم للحضور",
    "evidence-guides/supported-decision-making-transition-guide/index.html": "دعم اتخاذ القرار والانتقال إلى الرشد | دليل الأسرة",
    "family-guide/index.html": "دليل الأسرة للرعاية والدعم | 64 حالة و15 أداة عملية",
    "family-guide/tools/school-family-meeting-record/index.html": "محضر اجتماع الأسرة والمدرسة | أداة قابلة للتنفيذ",
    "family-guide/tools/transition-to-adulthood-plan/index.html": "خطة الانتقال إلى الرشد والحياة المجتمعية | دليل الأسرة",
    "learning-paths/postsecondary-transition-planning/index.html": "الانتقال من المدرسة إلى التعليم والعمل | مسار عملي",
    "quick-info/activity-vs-adhd/index.html": "حركة طبيعية أم فرط حركة؟ علامات تستحق الانتباه",
    "quick-info/ambition-vs-overwork/index.html": "طموح أم إفراط في العمل؟ راقب أثر النجاح على صحتك",
    "quick-info/authentic-self-relationship-check/index.html": "هل تستطيع أن تكون نفسك داخل العلاقة؟ 10 أسئلة",
    "quick-info/child-hidden-school-distress-check/index.html": "هل يخفي طفلك ضيقه في المدرسة؟ علامات بعد العودة",
    "quick-info/child-opposition-vs-overwhelm/index.html": "معارضة أم غمر نفسي؟ فهم رفض الطفل",
    "quick-info/child-sleep-evaluation/index.html": "هل يحتاج نوم طفلك إلى تقييم؟ مؤشرات مهمة",
    "quick-info/co-parenting-after-separation/index.html": "تنظيم الأبوة المشتركة بعد الانفصال دون إيذاء الطفل",
    "quick-info/confidence-vs-narcissism/index.html": "ثقة بالنفس أم نرجسية؟ الفرق عند النقد والحدود",
    "quick-info/conflict-repair-check/index.html": "هل تعرفان إصلاح الخلاف؟ خطوات العودة الآمنة",
    "quick-info/digital-boundaries-relationship/index.html": "حدود رقمية صحية في العلاقة | الهاتف والخصوصية",
    "quick-info/emotionally-unavailable-check/index.html": "هل أنت غير متاح عاطفيًا؟ 10 أسئلة للفهم",
    "quick-info/empathy-vs-emotional-absorption/index.html": "تعاطف أم امتصاص لمشاعر الآخرين؟ اعرف الفرق",
    "quick-info/end-relationship-safely/index.html": "كيف تنهي علاقة باحترام وأمان؟ خطوات عملية",
    "quick-info/grief-support-check/index.html": "هل تحتاج دعمًا إضافيًا بعد الفقد؟ مؤشرات عملية",
    "quick-info/language-delay-vs-developmental-difference/index.html": "تأخر لغوي أم اختلاف نمائي؟ متى نطلب التقييم",
    "quick-info/mood-swings-vs-bipolar/index.html": "تقلب مزاج أم اضطراب ثنائي القطب؟ الفروق الأساسية",
    "quick-info/nightmare-sleep-fear-check/index.html": "الخوف من النوم والكوابيس | متى نطلب المساعدة؟",
    "quick-info/normal-forgetting-vs-evaluation/index.html": "نسيان طبيعي أم علامة تستحق التقييم؟ راقب النمط",
    "quick-info/openness-vs-oversharing/index.html": "انفتاح أم إفراط في الإفصاح؟ حدود الصراحة",
    "quick-info/perfectionism-vs-ocd/index.html": "كمالية أم وسواس قهري؟ التشابه لا يعني تشخيصًا",
    "quick-info/post-trauma-caution-vs-ptsd/index.html": "حذر بعد صدمة أم اضطراب ما بعد الصدمة؟",
    "quick-info/repair-after-argument/index.html": "كيف تصلح العلاقة بعد خلاف مؤلم؟ خطوات مسؤولة",
    "quick-info/rest-vs-avoidance/index.html": "راحة أم تجنب؟ هل تعيدك الاستراحة إلى حياتك؟",
    "quick-info/return-social-life-after-isolation/index.html": "العودة إلى الحياة الاجتماعية بعد عزلة طويلة",
    "quick-info/self-care-vs-avoidance/index.html": "عناية بالنفس أم هروب؟ راقب أثر الاستراحة",
    "quick-info/sensitivity-vs-sensory-overload/index.html": "حساسية عاطفية أم فرط استجابة حسية؟",
    "quick-info/sleep-debt-check/index.html": "هل تراكم عليك دين نوم؟ راقب الأداء اليومي",
    "quick-info/social-avoidance-check/index.html": "هل تتجنب الناس بسبب القلق؟ راقب ما تخسره",
    "quick-info/social-media-mood-check/index.html": "هل تضر وسائل التواصل بمزاجك؟ اختبار عملي",
    "quick-info/stuck-after-breakup/index.html": "هل أنت عالق بعد الانفصال؟ 8 علامات مهمة",
    "quick-info/support-partner-with-anxiety/index.html": "دعم شريك يعاني القلق دون طمأنة مستمرة",
    "quick-info/teen-privacy-vs-withdrawal/index.html": "خصوصية المراهق أم انسحاب مقلق؟ علامات فارقة",
    "quick-info/when-getting-back-is-bad/index.html": "متى يكون الرجوع بعد الانفصال فكرة سيئة؟",
}

DESCRIPTION_MAP = {
    "family-guide/tools/appointment-prep/index.html": (
        "قائمة عربية قابلة للطباعة لتحضير موعد الطبيب أو المختص: الأعراض والأدوية "
        "والتغيرات والأسئلة والأهداف، مع تنظيم المعلومات دون استبدال التقييم المهني."
    ),
}

ROBOTS_INDEX_FOLLOW = {
    "addiction/tools/caregiver-wellbeing-plan/index.html",
    "addiction/tools/child-safety-trusted-adult-plan/index.html",
    "addiction/tools/discharge-follow-up-plan/index.html",
    "addiction/tools/family-30-90-day-support-agreement/index.html",
    "addiction/tools/family-boundaries-plan/index.html",
    "addiction/tools/family-financial-exposure-map/index.html",
    "addiction/tools/family-first-conversation-plan/index.html",
    "addiction/tools/family-treatment-communication-log/index.html",
    "addiction/tools/lapse-relapse-response-plan/index.html",
    "addiction/tools/medication-household-safety-inventory/index.html",
    "addiction/tools/overdose-emergency-plan/index.html",
    "addiction/tools/treatment-provider-checklist/index.html",
}

NEEDS_INTERNAL_LINKS = {
    "addiction/tools/caregiver-wellbeing-plan/index.html",
    "addiction/tools/child-safety-trusted-adult-plan/index.html",
    "addiction/tools/family-30-90-day-support-agreement/index.html",
    "addiction/tools/family-financial-exposure-map/index.html",
    "addiction/tools/family-treatment-communication-log/index.html",
    "addiction/tools/medication-household-safety-inventory/index.html",
}


def sitemap_urls(path: Path, seen: set[Path] | None = None) -> list[str]:
    seen = seen or set()
    path = path.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    root = ET.parse(path).getroot()
    urls: list[str] = []
    for node in root.iter():
        if not node.tag.endswith("loc") or not node.text:
            continue
        value = node.text.strip()
        parsed = urlparse(value)
        if parsed.path.endswith(".xml"):
            urls.extend(sitemap_urls(ROOT / unquote(parsed.path.lstrip("/")), seen))
        elif value.startswith(ORIGIN):
            urls.append(value)
    return urls


def url_to_html(url: str) -> Path | None:
    parsed = urlparse(url)
    relative = unquote(parsed.path.lstrip("/"))
    if not relative:
        return ROOT / "index.html"
    if relative.endswith("/"):
        return ROOT / relative / "index.html"
    if relative.endswith(".html"):
        return ROOT / relative
    return None


def mark_empty_alt_decorative(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not re.search(r"\balt\s*=\s*([\"'])\s*\1", tag, flags=re.I):
            return tag
        if re.search(r"\baria-hidden\s*=\s*([\"'])true\1", tag, flags=re.I) or re.search(
            r"\brole\s*=\s*([\"'])(?:presentation|none)\1", tag, flags=re.I
        ):
            return tag
        ending = "/>" if tag.endswith("/>") else ">"
        body = tag[: -len(ending)].rstrip()
        return f'{body} aria-hidden="true" role="presentation"{ending}'

    return re.sub(r"<img\b[^>]*>", replace, source, flags=re.I)


def replace_title(source: str, value: str) -> str:
    source, count = re.subn(
        r"<title>.*?</title>", f"<title>{value}</title>", source, count=1, flags=re.I | re.S
    )
    if count != 1:
        raise RuntimeError("Expected exactly one title element")
    for property_name in ("og:title", "twitter:title", "og:image:alt", "twitter:image:alt"):
        pattern = re.compile(
            rf"(<meta\b(?=[^>]*(?:property|name)=[\"']{re.escape(property_name)}[\"'])[^>]*\bcontent=[\"'])[^\"']*([\"'][^>]*>)",
            flags=re.I,
        )
        source = pattern.sub(lambda match: match.group(1) + value + match.group(2), source, count=1)
    return source


def replace_description(source: str, value: str) -> str:
    for name in ("description", "og:description", "twitter:description"):
        pattern = re.compile(
            rf"(<meta\b(?=[^>]*(?:property|name)=[\"']{re.escape(name)}[\"'])[^>]*\bcontent=[\"'])[^\"']*([\"'][^>]*>)",
            flags=re.I,
        )
        source, count = pattern.subn(lambda match: match.group(1) + value + match.group(2), source, count=1)
        if name == "description" and count != 1:
            raise RuntimeError("Primary meta description was not found")
    return source


def ensure_robots(source: str) -> str:
    value = "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
    pattern = re.compile(
        r"(<meta\b(?=[^>]*\bname=[\"']robots[\"'])[^>]*\bcontent=[\"'])[^\"']*([\"'][^>]*>)",
        flags=re.I,
    )
    source, count = pattern.subn(lambda m: m.group(1) + value + m.group(2), source, count=1)
    if count:
        return source
    marker = re.search(r"</title>", source, flags=re.I)
    if not marker:
        raise RuntimeError("Cannot insert robots metadata without title")
    return source[: marker.end()] + f'<meta name="robots" content="{value}">' + source[marker.end():]


def ensure_internal_links(source: str) -> str:
    marker = 'data-seo-related-links="v1"'
    if marker in source:
        return source
    nav = (
        '<nav data-seo-related-links="v1" aria-label="روابط ذات صلة">'
        '<a href="/addiction/">مركز الإدمان والتعافي</a> · '
        '<a href="/addiction/tools/">أدوات التعافي والأسرة</a> · '
        '<a href="/start-here/">ابدأ من هنا</a>'
        '</nav>'
    )
    if re.search(r"</main>", source, flags=re.I):
        return re.sub(r"</main>", nav + "</main>", source, count=1, flags=re.I)
    return re.sub(r"</body>", nav + "</body>", source, count=1, flags=re.I)


def ensure_aphasia_contract(source: str) -> str:
    canonical = "https://healthrenewal.org/family-guide/conditions/aphasia/"
    if 'hreflang="ar"' not in source:
        alternates = (
            f'<link rel="alternate" hreflang="ar" href="{canonical}">'
            f'<link rel="alternate" hreflang="x-default" href="{canonical}">'
        )
        source = re.sub(
            rf'(<link\s+rel=["\']canonical["\']\s+href=["\']{re.escape(canonical)}["\']\s*/?>)',
            r"\1" + alternates,
            source,
            count=1,
            flags=re.I,
        )
    marker = '"@id":"https://healthrenewal.org/family-guide/conditions/aphasia/#seo-contract"'
    if marker not in source:
        graph = {
            "@context": "https://schema.org",
            "@id": "https://healthrenewal.org/family-guide/conditions/aphasia/#seo-contract",
            "@graph": [
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": "https://healthrenewal.org/"},
                        {"@type": "ListItem", "position": 2, "name": "دليل الأسرة", "item": "https://healthrenewal.org/family-guide/"},
                        {"@type": "ListItem", "position": 3, "name": "الحبسة", "item": canonical},
                    ],
                },
                {
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": "هل العنوان والشرح واضحان دون تبسيط مهين؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "يُراجع النص بلغة مباشرة تحترم الشخص وتفصل صعوبة اللغة عن الذكاء والقدرة على اتخاذ القرار."},
                        },
                        {
                            "@type": "Question",
                            "name": "هل الجمل قصيرة بما يكفي؟ وأين يصبح النص كثيفًا؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "تُقسم المعلومات إلى فكرة واحدة في كل جملة أو خطوة، مع مساحة بيضاء وخيارات محدودة عند الحاجة."},
                        },
                        {
                            "@type": "Question",
                            "name": "هل الأزرار والتنقل وترتيب الأقسام قابل للفهم؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "تستخدم الصفحة تسميات فعلية واضحة، وترتيبًا متوقعًا، وروابط رجوع إلى دليل الأسرة والرئيسية."},
                        },
                        {
                            "@type": "Question",
                            "name": "هل توجد عبارة تفترض عدم الكفاءة أو تقلل من استقلال الشخص؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "المبدأ هو مخاطبة الشخص مباشرة ودعم التعبير بوسائل متعددة دون افتراض غياب الرأي أو الأهلية."},
                        },
                        {
                            "@type": "Question",
                            "name": "ما المعلومة العملية التي تنقص الأسرة أو الشخص نفسه؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "يُستكمل الدليل وفق المراجعة العملية والخبرة المعاشة، مع الحفاظ على مسارات الطوارئ والتقييم والتواصل الداعم."},
                        },
                        {
                            "@type": "Question",
                            "name": "هل اللهجة أو المصطلحات العربية تحتاج بدائل أكثر شيوعًا؟",
                            "acceptedAnswer": {"@type": "Answer", "text": "يمكن تقديم بدائل عربية مألوفة ما دامت دقيقة ولا تغيّر المعنى الطبي أو تقلل احترام الشخص."},
                        },
                    ],
                },
            ],
        }
        block = '<script type="application/ld+json">' + json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "</script>"
        source = re.sub(r"</head>", block + "</head>", source, count=1, flags=re.I)
    return source


def ensure_women_calendar_contract(source: str) -> str:
    expected = "https://healthrenewal.org/sectors/calendars/women/"
    source = re.sub(
        r'(<link\s+rel=["\']canonical["\']\s+href=["\'])https://healthrenewal\.org/sectors/women/daily-calendar/(["\'])',
        rf"\g<1>{expected}\2",
        source,
        count=1,
        flags=re.I,
    )
    source = re.sub(
        r'(<meta\b(?=[^>]*(?:property|name)=["\']og:url["\'])[^>]*\bcontent=["\'])[^"\']*(["\'][^>]*>)',
        rf"\g<1>{expected}\2",
        source,
        count=1,
        flags=re.I,
    )
    marker = '"@id":"https://healthrenewal.org/sectors/calendars/women/#webpage"'
    if marker not in source:
        data = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": "https://healthrenewal.org/sectors/calendars/women/#webpage",
            "url": expected,
            "name": "تقويم المرأة",
            "description": "بوابة تقويم المرأة التفاعلي للمتابعة المحلية والرسائل اليومية وتذكيرات الهاتف.",
            "inLanguage": "ar",
            "isPartOf": {"@type": "WebSite", "name": "منصة روافد", "url": "https://healthrenewal.org/"},
        }
        block = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"
        source = re.sub(r"</head>", block + "</head>", source, count=1, flags=re.I)
    return source


def collect_paths() -> set[Path]:
    index = ROOT / "sitemap-index.xml"
    if not index.is_file():
        index = ROOT / "sitemap.xml"
    paths = {path for url in sitemap_urls(index) if (path := url_to_html(url)) and path.is_file()}
    for relative in set(TITLE_MAP) | set(DESCRIPTION_MAP) | ROBOTS_INDEX_FOLLOW | NEEDS_INTERNAL_LINKS:
        paths.add(ROOT / relative)
    paths.add(ROOT / "family-guide/conditions/aphasia/index.html")
    paths.add(ROOT / "sectors/calendars/women/index.html")
    return {path for path in paths if path.is_file()}


def collect_changes() -> list[tuple[Path, str]]:
    changes: list[tuple[Path, str]] = []
    for path in sorted(collect_paths()):
        current = path.read_text(encoding="utf-8")
        updated = mark_empty_alt_decorative(current)
        relative = path.relative_to(ROOT).as_posix()
        if relative in TITLE_MAP:
            updated = replace_title(updated, TITLE_MAP[relative])
        if relative in DESCRIPTION_MAP:
            updated = replace_description(updated, DESCRIPTION_MAP[relative])
        if relative in ROBOTS_INDEX_FOLLOW:
            updated = ensure_robots(updated)
        if relative in NEEDS_INTERNAL_LINKS:
            updated = ensure_internal_links(updated)
        if relative == "family-guide/conditions/aphasia/index.html":
            updated = ensure_aphasia_contract(updated)
        if relative == "sectors/calendars/women/index.html":
            updated = ensure_women_calendar_contract(updated)
        updated = ensure_social_metadata(updated)
        if updated != current:
            changes.append((path, updated))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    changes = collect_changes()
    if args.check:
        for path, _ in changes:
            print(path.relative_to(ROOT))
        return 1 if changes else 0

    for path, content in changes:
        path.write_text(content, encoding="utf-8")
    print(f"Resolved warning patterns in {len(changes)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
