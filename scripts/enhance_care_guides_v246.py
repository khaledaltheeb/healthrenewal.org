from __future__ import annotations

from pathlib import Path

import enhance_care_guides_v234 as base

RELEASE_DATE = "2026-07-26"
ENHANCEMENT_VERSION = 246

CATEGORY_RULES = (
    ("crisis", "الأزمات والسلامة", ("انتحار", "أزمة", "طوارئ", "هلع", "هياج", "صدمة", "عنف", "ضياع", "استرجاع", "crisis", "panic", "trauma", "wandering")),
    ("addictions", "استخدام المواد والسلوكيات الإدمانية", ("كحول", "مادة", "أفيون", "جرعة", "إدمان", "مقامرة", "ألعاب", "نيكوتين", "alcohol", "opioid", "gambling", "gaming", "substance")),
    ("older", "كبار السن والقدرات المعرفية", ("خرف", "هذيان", "كبار السن", "إدراكي", "وحدة", "dementia", "delirium", "older", "cognitive")),
    ("services", "العلاج والخدمات والحقوق", ("مختص", "موعد", "علاج نفسي", "دواء", "مستشفى", "خصوصية", "رأي ثان", "حقوق", "service", "therapy", "medication", "hospital")),
    ("children", "الأطفال والمراهقون", ("طفل", "مراهق", "مدرسة", "تنمر", "امتحان", "انفصال", "school", "child", "teen", "adolescent", "bullying")),
    ("neurodevelopment", "النمو العصبي وذوو الاحتياجات الخاصة", ("احتياجات خاصة", "نمائي", "داون", "شلل دماغي", "تعلم", "عسر القراءة", "لغة", "حسي", "توريت", "ريت", "فقدان السمع", "فقدان البصر", "AAC", "decision", "developmental", "sensory", "disability")),
    ("mood", "المزاج والقلق", ("قلق", "اكتئاب", "مزاج", "رهاب", "ما بعد الولادة", "كمالية", "غضب", "ثنائي القطب", "anxiety", "depression", "mood", "bipolar")),
    ("daily", "النوم والعمل والمرض المزمن", ("نوم", "أرق", "كوابيس", "ألم مزمن", "مرض مزمن", "العمل", "sleep", "insomnia", "pain", "workplace")),
)


def enhance(site: Path) -> None:
    base.RELEASE_DATE = RELEASE_DATE
    base.ENHANCEMENT_VERSION = ENHANCEMENT_VERSION
    base.CATEGORY_RULES = CATEGORY_RULES
    base.enhance(site)
