from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    "adhd/federation-guide/index.html": {
        "min_words": 1100,
        "markers": ("فهم الأسباب", "البيولوجيا العصبية", "تقييم ADHD عبر مراحل العمر", "قائمة مراجعة جودة الرعاية"),
    },
    "adhd/consensus/index.html": {
        "min_words": 800,
        "markers": ("208 استنتاجات", "كيف بُني البيان", "الدماغ والوظائف المعرفية", "سبع خرافات"),
    },
    "adhd/transfer-of-care/index.html": {
        "min_words": 1000,
        "markers": ("الحد الأدنى لملف انتقال", "تقييم المخاطر", "نموذج إحالة عربي", "قائمة الجهة المستقبلة"),
    },
    "adhd/language-guide/index.html": {
        "min_words": 900,
        "markers": ("قاموس إعادة الصياغة", "اللغة داخل الأسرة", "اللغة في العيادة", "كيف تصلح عبارة وصمية"),
    },
    "adhd/adult-coaching/index.html": {
        "min_words": 900,
        "markers": ("ما هو تدريب ADHD", "حدود الدور", "اتفاق تدريب مهني", "علامات خطر في مقدم التدريب"),
    },
    "adhd/expert-questions/index.html": {
        "min_words": 1100,
        "markers": ("42", "كيف نعرف أن العلاج يعمل", "كيف نقرأ إجابة خبير", "إطار لتحويل سؤال عام"),
    },
    "adhd/practice-guidelines/index.html": {
        "min_words": 850,
        "markers": ("مصفوفة مقارنة الإرشادات", "نقاط الاتفاق الواسع", "عقد مؤسسي", "نموذج تدقيق"),
    },
    "adhd/sources-and-rights/index.html": {
        "min_words": 700,
        "markers": ("الإذن الكتابي المحفوظ", "منهج الإثراء العربي", "تصنيف الملكية", "سجل الإثراء المنشور"),
    },
}

ARABIC_WORD_RE = re.compile(r"[\u0600-\u06ff][\u0600-\u06ff\u064b-\u065f\u0670\u0640-\u064a]*")

BANNED_CLINICAL_INSTRUCTIONS = (
    "زد الجرعة",
    "اخفض الجرعة",
    "تناول حبة",
    "ملغ يوميًا",
    "mg daily",
    "اخلط الدواء",
    "أوقف الدواء فورًا دون",
)

REQUIRED_GLOBAL_MARKERS = (
    '<html lang="ar" dir="rtl">',
    'name="description"',
    'rel="canonical"',
    'name="robots"',
    'type="application/ld+json"',
    "adhd-federation.org",
)


def test_adhd_source_pages_are_long_structured_and_attributed() -> None:
    combined: list[str] = []
    for relative, rules in PAGES.items():
        path = ROOT / relative
        assert path.is_file(), relative
        text = path.read_text(encoding="utf-8")
        assert all(marker in text for marker in REQUIRED_GLOBAL_MARKERS), relative
        assert all(marker in text for marker in rules["markers"]), relative
        word_count = len(ARABIC_WORD_RE.findall(text))
        assert word_count >= rules["min_words"], (relative, word_count, rules["min_words"])
        assert 'rel="noopener noreferrer"' in text, relative
        assert "مستقل" in text, relative
        assert any(marker in text for marker in ("اعتماد", "تأييد", "مراجعة الاتحاد", "مؤيد", "تشخيص")), relative
        combined.append(text)

    joined = "\n".join(combined).casefold()
    assert not [item for item in BANNED_CLINICAL_INSTRUCTIONS if item.casefold() in joined]


def test_deep_pages_preserve_source_ownership_boundaries() -> None:
    rights = (ROOT / "adhd/sources-and-rights/index.html").read_text(encoding="utf-8")
    assert "AADPA" in rights
    assert "ADHD Europe" in rights
    assert "CADDRA" in rights
    assert "EAGG" in rights
    assert "AWMF" in rights
    assert "NICE" in rights
    assert "لا نستخدم الشعار" in rights
    assert "لم تُبنَ الصفحات الجديدة على نسخ فقرات طويلة حرفيًا" in rights


def test_interlinked_enrichment_routes_resolve() -> None:
    for relative in PAGES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for href in re.findall(r'href="(/adhd/[a-z0-9-]+/)"', text):
            target = ROOT / href.strip("/") / "index.html"
            assert target.is_file(), (relative, href)
