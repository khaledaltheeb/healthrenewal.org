#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = 406
BASE = "https://healthrenewal.org"
REVIEWED_AT = "2026-08-01"
NEXT_REVIEW_DUE = "2027-02-01"
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "content" / "v406" / "women-youth-expansion-ar.json"
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
FORBIDDEN = re.compile(r"\b(?:معاقين|المعاقين|المعاق)\b", re.IGNORECASE)
GENERIC_PHRASES = ("بيئة التطبيق", "يرتبط مباشرة بـ", "قياس بناء")
EXPECTED_DISTRIBUTION = {"women": 15, "youth": 15}
SECTION_LABELS = {"women": "الصحة النفسية للمرأة", "youth": "الصحة النفسية للشباب واليافعين"}
SECTION_INTROS = {
    "women": "مسارات عملية تراعي التحولات الجسدية والاجتماعية وأعباء الرعاية والعمل والعنف والوصول العادل إلى الخدمة، من دون اختزال تجربة المرأة في الهرمونات أو الدور الأسري.",
    "youth": "مسارات عملية تعطي الشاب دورًا في القرار وتربط الصحة النفسية بالأسرة والمدرسة والجامعة والعمل والبيئة الرقمية، مع تصعيد واضح عند الخطر.",
}
AUDIENCES = {
    "women": "المرأة وأسرتها ومقدمو الرعاية الصحية والاجتماعية وأصحاب العمل والجهات المجتمعية",
    "youth": "الشاب أو اليافع وأسرته والمعلمون والمرشدون ومقدمو الخدمات الصحية والاجتماعية",
}
SITEMAPS = {"women": "sitemap-sector-women.xml", "youth": "sitemap-sector-youth.xml"}

SOURCES: dict[str, dict[str, str]] = {
    "who-mental-health": {"title": "WHO — Mental health", "url": "https://www.who.int/health-topics/mental-health", "note": "إطار دولي للصحة النفسية بوصفها حقًا وتفاعلًا بين عوامل فردية وأسرية ومجتمعية وهيكلية."},
    "who-perinatal": {"title": "WHO — Perinatal mental health", "url": "https://www.who.int/teams/mental-health-and-substance-use/promotion-prevention/perinatal-mental-health", "note": "مرجع للصحة النفسية في الحمل والسنة التالية للولادة وعوامل الخطر والتكامل مع رعاية الأم والطفل."},
    "who-perinatal-guide": {"title": "WHO — Guide for integration of perinatal mental health in maternal and child health services", "url": "https://www.who.int/publications/i/item/9789240057142/", "note": "دليل قائم على الدليل لدمج التعزيز والتعرف والاستجابة في خدمات الأم والطفل بصورة تراعي الثقافة والكرامة."},
    "nice-cg192": {"title": "NICE CG192 — Antenatal and postnatal mental health", "url": "https://www.nice.org.uk/guidance/cg192", "note": "إرشاد سريري للتعرف والإحالة وإدارة حالات الصحة النفسية خلال الحمل وبعد الولادة."},
    "acog-perinatal": {"title": "ACOG — Treatment and management of mental health conditions during pregnancy and postpartum", "url": "https://www.acog.org/clinical/clinical-guidance/clinical-practice-guideline/articles/2023/06/treatment-and-management-of-mental-health-conditions-during-pregnancy-and-postpartum", "note": "إرشاد مهني لتقييم الفوائد والمخاطر والمتابعة والإحالة في الصحة النفسية المحيطة بالولادة."},
    "nice-ng23": {"title": "NICE NG23 — Menopause: identification and management", "url": "https://www.nice.org.uk/guidance/ng23", "note": "إرشاد محدث للتعرف والمعلومات والدعم والقرار الفردي في مرحلة ما حول انقطاع الطمث."},
    "who-vaw": {"title": "WHO — Violence against women", "url": "https://www.who.int/news-room/fact-sheets/detail/violence-against-women", "note": "مرجع للصحة العامة وحقوق الإنسان وعواقب العنف الجسدية والنفسية وضرورة الاستجابة الآمنة."},
    "un-women-vaw": {"title": "UN Women — Ending violence against women", "url": "https://www.unwomen.org/en/what-we-do/ending-violence-against-women", "note": "إطار حقوقي ومؤسسي للوقاية والاستجابة ومنع لوم الناجيات."},
    "who-work": {"title": "WHO — Mental health at work", "url": "https://www.who.int/news-room/fact-sheets/detail/mental-health-at-work", "note": "مرجع للمخاطر النفسية الاجتماعية في العمل والتكييفات والإدماج وحماية الخصوصية."},
    "who-disability": {"title": "WHO — Disability and health", "url": "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", "note": "إطار للحواجز الصحية وعدم المساواة والوصول إلى خدمات شاملة وميسرة."},
    "crpd-health": {"title": "UN CRPD — Article 25: Health", "url": "https://social.desa.un.org/issues/disability/crpd/article-25-health", "note": "حق الأشخاص ذوي الإعاقة في أعلى مستوى صحي ممكن دون تمييز وبموافقة حرة ومستنيرة."},
    "who-womens-health": {"title": "WHO — Women’s health", "url": "https://www.who.int/health-topics/women-s-health", "note": "بوابة مؤسسية لصحة المرأة عبر دورة الحياة والعوامل الاجتماعية والحقوقية."},
    "nice-eating": {"title": "NICE NG69 — Eating disorders: recognition and treatment", "url": "https://www.nice.org.uk/guidance/ng69", "note": "إرشاد للتعرف المبكر وتقييم الخطر والعلاج دون الاعتماد على الوزن وحده."},
    "unhcr-mhpss": {"title": "UNHCR — Mental health and psychosocial support", "url": "https://www.unhcr.org/what-we-do/protect-human-rights/public-health/mental-health-and-psychosocial-support", "note": "مرجع للوصول الآمن والمتعدد القطاعات في النزوح واللجوء مع مراعاة الحماية واللغة."},
    "who-adolescent": {"title": "WHO — Mental health of adolescents", "url": "https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health", "note": "مرجع محدث لمحددات صحة المراهقين والاضطرابات الشائعة والمخاطر والوقاية والرعاية القائمة على الحقوق."},
    "who-adolescent-wellbeing": {"title": "WHO — Promoting adolescent well-being", "url": "https://www.who.int/health-topics/adolescent-health/promoting-adolescent-well-being", "note": "إطار يضع الشباب شركاء ويغطي العلاقات الآمنة والمهارات والموارد والحقوق والمشاركة."},
    "who-adolescent-health": {"title": "WHO — Adolescent and young adult health", "url": "https://www.who.int/news-room/fact-sheets/detail/adolescents-health-risks-and-solutions", "note": "مرجع للمخاطر الصحية والسلوكية والمواد والعنف والصحة الإنجابية خلال المراهقة والشباب."},
    "unicef-jordan-youth": {"title": "UNICEF Jordan — Mental health literacy guide for young people", "url": "https://www.unicef.org/jordan/documents/mental-health-literacy-guide-young-people", "note": "دليل عربي تفاعلي للشباب والممارسين في الأردن حول الفهم والحوار وطلب المساعدة."},
    "unicef-cyberbullying": {"title": "UNICEF — Cyberbullying: what is it and how to stop it", "url": "https://www.unicef.org/end-violence/how-to-stop-cyberbullying", "note": "إرشاد للشباب بشأن التعرف إلى التنمر الإلكتروني وحفظ الأدلة وطلب المساعدة والإبلاغ."},
    "nice-depression-youth": {"title": "NICE NG134 — Depression in children and young people", "url": "https://www.nice.org.uk/guidance/ng134", "note": "إرشاد للتعرف والتقييم والعلاج ومشاركة الأسرة والشاب وتقييم الخطر."},
    "nice-self-harm": {"title": "NICE NG225 — Self-harm: assessment, management and preventing recurrence", "url": "https://www.nice.org.uk/guidance/ng225", "note": "إرشاد للتقييم النفسي الاجتماعي والرعاية الفورية والسلامة ومنع التكرار دون عقاب."},
    "nice-psychosis-youth": {"title": "NICE CG155 — Psychosis and schizophrenia in children and young people", "url": "https://www.nice.org.uk/guidance/cg155", "note": "إرشاد للتعرف المبكر والإحالة والتقييم والعلاج بمشاركة الطفل أو الشاب والأسرة."},
    "unodc-youth": {"title": "UNODC — International standards on drug use prevention", "url": "https://www.unodc.org/unodc/en/prevention/prevention-standards.html", "note": "معايير دولية للوقاية القائمة على الدليل والمناسبة للنمو والبيئة والأسرة والمدرسة."},
    "crc-participation": {"title": "UN Convention on the Rights of the Child — Article 12", "url": "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-rights-child", "note": "حق الطفل والشاب في التعبير عن الرأي وإيلائه الوزن المناسب بحسب العمر والنضج."},
}

PROFILE_STEPS = {
    "perinatal": ["اسألي عن الشعور والوظيفة بلغة غير حكمية", "افحصي النوم والدعم والحالة الطبية", "حددي تاريخ الصحة النفسية والأدوية", "قيّمي السلامة للأم والرضيع", "اتفقي على إحالة وموعد متابعة", "أشركي شخص دعم بموافقة المرأة", "راجعي الخطة مع تغير المرحلة"],
    "trauma": ["ابدئي بالأمان والسيطرة", "اطلبي الإذن قبل الأسئلة", "حددي المحفزات وما يساعد", "وفري خيارات في المكان والفحص", "لا تفرضي سرد التفاصيل", "اربطي بالألم والرعاية الطبية", "راجعي الاستقرار والمتابعة"],
    "grief": ["اعترفي بالفقد كما تسميه المرأة", "اسألي عن الاحتياج الحالي", "احترمي الطقوس والثقافة", "خففي المهام العاجلة", "راقبي الذنب واليأس والخطر", "صليها بدعم مناسب", "راجعي الوظيفة بمرور الوقت"],
    "reproductive": ["حددي سؤال القرار", "افصلي المعلومات الطبية عن الضغط الاجتماعي", "احمي الخصوصية", "قسمي القرارات إلى مراحل", "ناقشي كلفة الوقت والمال", "وفري دعمًا نفسيًا غير مشروط بالنتيجة", "راجعي حق التوقف أو التغيير"],
    "menopause": ["سجلي الأعراض والسياق", "افحصي النوم والمزاج والعمل", "استبعدي التغيرات الطبية المهمة", "قدمي معلومات خيارات واضحة", "احترمي التفضيلات والمخاطر الفردية", "اتفقي على مؤشر نتيجة", "راجعي الأثر والآثار الجانبية"],
    "care-work": ["اكتبي كل مهام الرعاية", "احسبي الوقت والعمل الليلي", "حددي المهام عالية الخطر", "وزعي المسؤوليات", "ثبتي فترات راحة وعلاج", "اطلبي موارد رسمية", "راجعي العدالة والاستدامة"],
    "violence": ["اسألي في مكان خاص وآمن", "صدقي الإفصاح ولا تلومي", "قيّمي الخطر الفوري", "لا تتصلي بالمعتدي", "خططي لقناة اتصال آمنة", "اربطي بخدمة حماية محلية", "راجعي الخطة دون ترك أثر مكشوف"],
    "health-equity": ["اسألي عن الحواجز لا التشخيص فقط", "وفري تواصلًا ميسرًا", "ادمجي الألم والتعب", "نسقي المواعيد", "قللي تكرار الإفصاح", "احمي الموافقة والخصوصية", "راجعي الوصول الفعلي"],
    "body-eating": ["اسألي عن السلوك لا الوزن فقط", "افحصي التقييد والنهم والتعويض", "راجعي العلامات الجسدية", "تجنبي لغة الحمية واللوم", "قيّمي الخطر الطبي والنفسي", "أحيلي مبكرًا", "تابعي المشاركة والأسرة"],
    "sleep": ["سجلي أسبوعًا نموذجيًا", "حددي مسؤوليات الليل", "افحصي الألم والتنفس والأدوية", "غيري عاملًا واحدًا", "احمي وقت الراحة", "راقبي المزاج والنشاط", "أحيلي التغير الحاد"],
    "equity": ["حددي لغة التواصل", "استخدمي مترجمة آمنة مستقلة", "افصلي العلاج عن التخويف القانوني", "قللي كلفة التنقل والرعاية", "افحصي العنف والاستغلال", "اختاري نقطة اتصال موثوقة", "تأكدي من إتمام الإحالة"],
    "literacy": ["ابدئي بمثال يومي", "فرقي بين الشعور والاضطراب", "استخدمي لغة غير وصمية", "اشرحي حدود السرية", "حددي شخصًا آمنًا", "تدربي على عبارة طلب", "راجعي معرفة الطوارئ"],
    "school": ["حددي الموقف المدرسي", "اسألي الشاب عن المثير", "افحصي التنمر والتعلم والصحة", "عدلي عبئًا واحدًا", "خططي عودة تدريجية", "نسقي الأسرة والمدرسة", "راقبي الحضور والضيق"],
    "digital": ["راجعي نمط الاستخدام مع الشاب", "افصلي المحتوى عن الوقت", "افحصي التنمر والابتزاز", "اتفقي على تجربة قصيرة", "عدلي التنبيهات والبيئة", "وفري بدائل اجتماعية", "راجعي النوم والسرية"],
    "safeguarding": ["أوقفي التعرض الحالي", "احفظي الأدلة دون نشرها", "اسألي عن الانتقام والتهديد", "أبلغي عبر قناة مؤسسية", "احمي هوية الشاب", "وفري دعمًا نفسيًا وتعليميًا", "راجعي فعالية الحماية"],
    "social": ["اسألي عن جودة العلاقات", "ميزي الخلاف عن الإقصاء", "حددي شخصًا آمنًا", "ابني فرصة مشاركة صغيرة", "علمي حدودًا وتواصلًا", "راقبي الانسحاب والمزاج", "راجعي اختيار الشاب"],
    "clinical-warning": ["وثقي بداية التغير", "افحصي الوظيفة والنوم", "راجعي الصحة والمواد", "اسألي مباشرة عن الخطر", "لا تجادلي التجارب", "رتبي تقييمًا مختصًا", "حددي متابعة قريبة"],
    "acute-safety": ["عالجي الإصابة أو الخطر الطبي", "اسألي عن النية والخطة", "قللي الوصول إلى الوسائل", "لا تتركي الشاب وحده", "فعلي الطوارئ عند الخطر المباشر", "اكتبي خطة متابعة", "راجعي ما بعد الأزمة"],
    "substance": ["اسألي دون وصم", "حددي المادة والكمية والتوقيت", "افحصي التسمم والانسحاب", "راجعي القيادة والأدوية", "اربطي الاستخدام بالضغط", "اختاري خدمة مناسبة", "تابعي محاولات التغيير"],
    "transition": ["حددي هدف الشاب", "قيسي مهارات الروتين", "جربي البيئة الجديدة", "اختاري تكييفات محددة", "حددي من يفعل ماذا", "اخفضي الدعم تدريجيًا", "راجعي الرضا والاستقلال"],
    "participation": ["قدمي معلومات ميسرة", "تحققي من الفهم", "اسألي عن التفضيل والرفض", "سجلي رأي الشاب", "اشرحي حدود السلامة", "اتخذي قرارًا مشتركًا", "راجعي الأثر معه"],
}

ROLE_MAP = {
    "women": ["المرأة: تحدد الأولويات والتفضيلات وحدود المشاركة", "الأسرة أو شخص الدعم: يساعد دون السيطرة أو كشف المعلومات", "الخدمة الصحية أو الاجتماعية: تقيم الخطر وتوفر رعاية مهنية وميسرة", "المؤسسة أو جهة العمل: تزيل الحواجز وتحمي الخصوصية ومنع التمييز"],
    "youth": ["الشاب: يصف التجربة ويشارك في الهدف والقرار", "الأسرة: توفر الأمان والاستماع والدعم العملي", "المدرسة أو الجامعة: تعدل البيئة وتفعل الحماية والإحالة", "الخدمة الصحية أو الاجتماعية: تقيم الحالة والخطر وتنسق المتابعة"],
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def visible_words(source: str) -> int:
    return len(WORD_RE.findall(html.unescape(TAG_RE.sub(" ", source))))


def li(values: list[str] | tuple[str, ...]) -> str:
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def route_for(item: dict[str, Any]) -> str:
    return f"sectors/{item['section']}/guides/{item['slug']}/"


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def validate_catalog(catalog: dict[str, Any]) -> None:
    if catalog.get("version") != VERSION:
        raise ValueError("Unexpected catalog version")
    pages = catalog.get("pages")
    if not isinstance(pages, list) or len(pages) != 30:
        raise ValueError("The v406 catalog must contain exactly 30 pages")
    distribution = Counter(item.get("section") for item in pages)
    if dict(distribution) != EXPECTED_DISTRIBUTION:
        raise ValueError(f"Invalid distribution: {distribution}")
    routes = [route_for(item) for item in pages]
    if len(routes) != len(set(routes)):
        raise ValueError("Duplicate v406 routes")
    titles = [item["title"] for item in pages]
    if len(titles) != len(set(titles)):
        raise ValueError("Duplicate v406 titles")
    for item in pages:
        for field in ("section", "slug", "title", "purpose", "context", "profile", "risk"):
            if not str(item.get(field, "")).strip():
                raise ValueError(f"Missing {field}: {item}")
        if item["profile"] not in PROFILE_STEPS:
            raise ValueError(f"Unknown profile: {item['profile']}")
        if len(item.get("domains", [])) < 5 or len(item.get("metrics", [])) < 4:
            raise ValueError(f"Insufficient topic detail: {item['slug']}")
        source_ids = item.get("sources", [])
        if len(source_ids) < 3 or any(source_id not in SOURCES for source_id in source_ids):
            raise ValueError(f"Invalid sources: {item['slug']}")


def safety_block(item: dict[str, Any]) -> str:
    profile = item["profile"]
    if profile == "violence":
        heading = "تحقق أمان عند العنف أو السيطرة"
        points = ["لا تستخدمي جهازًا أو حسابًا قد يراقبه المعتدي للبحث عن المساعدة أو حفظ الخطة.", "لا تُنصح المواجهة أو إعلان نية المغادرة دون تقييم خطر محلي؛ قد تزيد السيطرة أو التهديد.", "عند خطر مباشر أو سلاح أو تهديد بالقتل أو احتجاز، اتصلي بخدمات الطوارئ والحماية المحلية من قناة آمنة.", "احفظي أقل قدر من المعلومات، وحددي كلمة أو شخصًا أو مكانًا آمنًا للاتصال."]
    elif profile == "acute-safety":
        heading = "تحقق فوري عند خطر إيذاء النفس أو الانتحار"
        points = ["عالج الإصابة والحالة الطبية أولًا، واتصل بالطوارئ عند نزف شديد أو فقد وعي أو تسمم أو خطر مباشر.", "اسأل بوضوح عن النية والخطة والوسائل والمحاولات السابقة؛ السؤال المباشر لا يزرع الفكرة.", "لا تترك الشاب وحده عند خطر وشيك، وقلل الوصول إلى الأدوية والأسلحة والمواد والمرتفعات بوسائل آمنة.", "لا تعتمد على وعد أو عقد عدم إيذاء النفس بدل التقييم وخطة السلامة والمتابعة المهنية."]
    elif profile in {"clinical-warning", "body-eating", "perinatal"}:
        heading = "تحقق سريري وعلامات تصعيد"
        points = [f"الخطر المركزي الذي تمنعه الخطة هو: {item['risk']}.", "اطلب تقييمًا عاجلًا عند تدهور سريع في الوعي أو الوظيفة أو النوم، أو أفكار إيذاء النفس، أو أعراض جسدية خطرة.", "لا توقف دواءً ولا تبدأ علاجًا أو مكملًا بسبب هذه الصفحة؛ القرار يحتاج تقييمًا فرديًا ومراجعة الفوائد والمخاطر.", "ضع موعد متابعة واضحًا، ولا تكتفِ بتسليم قائمة مصادر لشخص لا يستطيع الوصول إلى الخدمة."]
    else:
        heading = "تحقق السلامة وحدود التطبيق"
        points = [f"الخطر المركزي الذي تمنعه الخطة هو: {item['risk']}.", "توقف عن التجربة وأحل إلى جهة مؤهلة عند ألم أو تراجع حاد أو خطر أو فقد وظيفة مستمر.", "لا تستخدم البيانات للعقاب أو الوصم أو كشف معلومات لا يحتاجها الآخرون.", "أي خطة تعليمية أو اجتماعية منخفضة المخاطر لا تلغي الحاجة إلى تقييم صحي أو نفسي عندما تظهر علاماته."]
    return f'<aside class="notice topic-check"><h2>{esc(heading)}</h2><ul>{li(points)}</ul></aside>'


def render_page(item: dict[str, Any]) -> str:
    title, purpose, context = item["title"], item["purpose"], item["context"]
    section, profile = item["section"], item["profile"]
    route = route_for(item)
    canonical = f"{BASE}/{route}"
    description = f"دليل عربي موسع حول {title}: تقييم وظيفي، خطوات تطبيق، مؤشرات قرار، سلامة وإحالة اعتمادًا على مراجع دولية رسمية."
    audience = AUDIENCES[section]
    domains, steps, metrics = item["domains"], PROFILE_STEPS[profile], item["metrics"]
    sources = [SOURCES[source_id] for source_id in item["sources"]]
    domain_cards = "".join(f'<article class="card"><h3>{index}. {esc(domain)}</h3><p>في موضوع «{esc(title)}»، اجمع مثالًا على النجاح وآخر على التعثر في مجال {esc(domain)}. افصل بين قدرة الشخص ومتطلبات {esc(context)}، وسجل الحاجز والميسر ونوع المساعدة ورأي المرأة أو الشاب. لا تحول الملاحظة إلى صفة ثابتة؛ الهدف هو معرفة ما يمكن تغييره لتحقيق «{esc(purpose)}» بأقل تدخل لازم.</p></article>' for index, domain in enumerate(domains, 1))
    step_cards = "".join(f'<article class="card"><h3>الخطوة {index}</h3><p><strong>{esc(step)}.</strong> طبّق هذه الخطوة في موقف محدد من {esc(context)}، وحدد من ينفذها ومتى وما علامة النجاح والتوقف. اربطها مباشرة بهدف الصفحة، ولا تجمع معلومات لا تغير قرارًا أو لا تعود بفائدة على الشخص.</p></article>' for index, step in enumerate(steps, 1))
    role_cards = "".join(f'<article class="card"><h3>{index}. دور واضح</h3><p>{esc(role)}. يجب توثيق حدود الدور وطريقة التواصل وموعد المراجعة حتى لا يتحول التنسيق إلى نقل مسؤولية أو مراقبة زائدة.</p></article>' for index, role in enumerate(ROLE_MAP[section], 1))
    metric_rows = "".join(f'<tr><td>{index}</td><td>{esc(metric)}</td><td>قياس قصير ومتكرر مع السياق ونوع الدعم ورأي الشخص.</td><td>استمرار، أو تعديل عنصر واحد، أو توقف وإحالة.</td></tr>' for index, metric in enumerate(metrics, 1))
    source_items = "".join(f'<li><a href="{esc(source["url"])}" target="_blank" rel="noopener noreferrer">{esc(source["title"])}</a><span>{esc(source["note"])}</span></li>' for source in sources)
    questions = [f"ما النتيجة اليومية التي تعني نجاح «{title}» للشخص نفسه؟", f"متى يظهر التعثر داخل {context}، ومتى يخف؟", "هل توجد علامة صحية أو ألم أو دواء أو مادة أو فقد نوم يفسر التغير؟", "ما المعلومات التي يمكن جمعها بأقل تدخل وأعلى خصوصية؟", "من الشخص الآمن أو الجهة المؤهلة التي ستستلم الإحالة؟", "كيف ستختبر الخطة في موقف ثانٍ دون زيادة الدعم؟"]
    checklist = ["الهدف مكتوب بصوت الشخص ولا يختزل قيمته في الأداء أو الامتثال.", "جُمعت معلومات من أكثر من فرصة وسياق.", "فُحصت العوامل الجسدية والنوم والأدوية والمواد عند صلتها.", "توجد وسيلة للرفض وطلب التوقف أو المساعدة.", "اختير تعديل واحد منخفض المخاطر ويمكن الرجوع عنه.", "المؤشرات تشمل الوظيفة والراحة والاختيار لا الهدوء الظاهري فقط.", "الأدوار والخصوصية وموعد المتابعة محددة.", "علامات الطوارئ والإحالة معروفة قبل بدء الخطة.", "اختُبر النقل إلى وقت أو مكان أو شريك ثانٍ.", "حالة المراجعة الداخلية وحدود الصفحة ظاهرة للقارئ."]
    schema = json.dumps({"@context": "https://schema.org", "@type": "Article", "inLanguage": "ar", "headline": title, "description": description, "mainEntityOfPage": canonical, "datePublished": REVIEWED_AT, "dateModified": REVIEWED_AT, "author": {"@type": "Organization", "name": "Health Renewal"}, "publisher": {"@type": "Organization", "name": "Health Renewal"}, "audience": {"@type": "Audience", "audienceType": audience}, "isAccessibleForFree": True}, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Health Renewal</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}"><script type="application/ld+json">{schema}</script><style>:root{{--bg:#f5f8f7;--ink:#152722;--muted:#526761;--card:#fff;--line:#d2e1dc;--accent:#0c6654;--warn:#8a4f0b;--soft:#e5f3ee}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.95}}a{{color:#075e4b}}header,main,footer{{max-width:1160px;margin:auto;padding:1.2rem}}nav a{{margin-inline-end:1rem}}.hero{{background:linear-gradient(135deg,var(--soft),#fff7e7);border:1px solid var(--line);border-radius:22px;padding:clamp(1.3rem,4vw,3.2rem);margin-block:1rem 2rem}}h1{{font-size:clamp(2rem,5vw,3.45rem);line-height:1.35}}h2{{font-size:1.58rem;margin-top:2.5rem}}h3{{line-height:1.55}}.card,.notice,details{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.2rem;margin:1rem 0}}.notice{{border-inline-start:6px solid var(--warn)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}}.meta,.sources span{{color:var(--muted)}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{border:1px solid var(--line);padding:.72rem;text-align:right;vertical-align:top}}summary{{font-weight:700;cursor:pointer}}.tag{{display:inline-block;background:#dcebe5;border-radius:999px;padding:.25rem .7rem;margin:.2rem}}</style><link rel="stylesheet" href="../../../../assets/platform/platform-core.css?v=1.1.0"><script defer src="../../../../assets/platform/platform-core.js?v=1.1.0"></script></head><body data-content-engine="v406" data-topic="{esc(item['slug'])}" class="pt-platform"><header><nav aria-label="التنقل الأساسي"><a href="/">الرئيسية</a><a href="/sectors/">القطاعات</a><a href="/sectors/{section}/">{esc(SECTION_LABELS[section])}</a><a href="/trust/">الثقة والمنهج</a></nav></header><main id="content"><section class="hero"><p><strong>{esc(SECTION_LABELS[section])}</strong></p><h1>{esc(title)}</h1><p>{esc(purpose)}. يتناول الدليل التطبيق في {esc(context)}، ويخاطب {esc(audience)}.</p><p class="meta">محرك المحتوى v406 · مراجعة داخلية: {REVIEWED_AT} · المراجعة الخارجية المتخصصة موصى بها · المراجعة التالية: {NEXT_REVIEW_DUE}</p></section><section class="notice"><h2>حدود الاستخدام والقرار الآمن</h2><p>هذه الصفحة أداة تثقيف وتخطيط حول <strong>{esc(title)}</strong>، وليست تشخيصًا ولا وصفة دواء أو علاجًا فرديًا ولا بديلًا عن التقييم المهني أو القانون المحلي. يجب مواءمة أي خطوة مع العمر والصحة والتواصل والثقافة والموارد.</p><p><strong>الخطر الذي تمنعه الخطة:</strong> {esc(item['risk'])}. عند خطر مباشر أو إصابة خطرة أو فقد وعي أو صعوبة تنفس أو تسمم أو تهديد جدي للنفس أو الآخرين، تُطلب خدمات الطوارئ والحماية المحلية فورًا.</p></section><section><h2>1. النتيجة ذات المعنى ونطاق الصفحة</h2><p>لا يبدأ موضوع «{esc(title)}» باسم تشخيص، بل بسؤال: ما الذي تغير في الحياة اليومية داخل {esc(context)}، وما النتيجة التي تريدها المرأة أو الشاب؟ الهدف هنا هو <strong>{esc(purpose)}</strong>. هذه الصياغة تربط المعرفة بقرار يمكن ملاحظته ومراجعته.</p><p>قد تختلف القدرة والضيق بين مكان وآخر بسبب النوم والألم واللغة والعلاقات والخصوصية والضغط والموارد. لذلك لا يجوز تعميم موقف واحد أو تحويل استجابة مؤقتة إلى صفة ثابتة. الصفحة تنظم الأسئلة ولا تحسم السبب منفردة.</p></section><section><h2>2. لماذا يحتاج الموضوع إلى خطة مستقلة؟</h2><p>يجمع «{esc(title)}» بين الصحة والوظيفة والحقوق والتواصل والسياق. النصيحة العامة قد تخفي فرقًا بين حاجة منخفضة المخاطر وبين علامة صحية أو نفسية تستدعي تقييمًا سريعًا. الخطة المستقلة تمنع {esc(item['risk'])} وتوضح من يفعل ماذا ومتى.</p><p>القرار الجيد يفصل بين تجربة الشخص، ومتطلبات الموقف، والحواجز المحيطة. إذا كان العائق في الوصول أو المعلومات أو استجابة الشريك فلا يُنسب إلى ضعف الشخص. وإذا ظهر تغير مفاجئ في الوعي أو النوم أو الأكل أو الحركة أو التفكير فلا يُفسر بوصفه كسلًا أو مبالغة.</p></section><section><h2>3. الأساس العلمي والحقوقي</h2><p>تتعامل المراجع الرسمية مع الصحة النفسية كتفاعل بين عوامل فردية وأسرية ومجتمعية وهيكلية. ولذلك يقيس الدليل الوظيفة والراحة والاختيار والوصول، لا عدد الأعراض فقط. كما يرفض الوصم والإكراه والتمييز ويعطي الشخص معلومات ميسرة ودورًا في القرار.</p><p>المصادر في نهاية الصفحة تؤسس المبادئ العامة، لكنها لا تحول الإرشاد الدولي إلى قرار فردي. تطبيق «{esc(title)}» يحتاج معرفة بالسياق المحلي وخدمات الإحالة والتشريعات وحدود كل مهنة.</p></section><section><h2>4. صوت الشخص والموافقة والخصوصية</h2><p>تُشرح الخطة بلغة مفهومة، ويُسأل الشخص عن الأولوية وما لا يريد مشاركته ومن يحق له الاطلاع. عدم الكلام أو صغر العمر لا يعني غياب الرأي؛ يمكن استخدام الكتابة أو الصور أو مترجم مستقل أو شخص دعم يختاره الفرد.</p><p>اجمع أقل قدر من البيانات الضرورية. لا تُرسل تفاصيل حساسة عبر قناة غير آمنة، ولا تكشف تشخيصًا لمدرسة أو جهة عمل أو أسرة ممتدة دون حاجة وموافقة، إلا عندما يفرض خطر مباشر أو قانون محلي إجراء حماية محددًا.</p></section><section><h2>5. أسئلة التقييم قبل التدخل</h2><ul>{li(questions)}</ul><p>تُسجل الإجابات بأمثلة وتواريخ وسياقات، لا بكلمات مثل دائمًا أو أبدًا. سجل أيضًا فرص النجاح؛ فهي تكشف الميسرات التي يمكن نقلها إلى مواقف أخرى.</p></section><section><h2>6. مجالات التقييم الوظيفي</h2><div class="grid">{domain_cards}</div></section><section><h2>7. بناء خط أساس قابل للمقارنة</h2><p>اختر موقفًا متكررًا من {esc(context)}، وحدد بداية الفرصة ونهايتها والنتيجة الناجحة ونوع الدعم. اجمع عدة فرص في أيام مختلفة، وسجل النوم والألم والضغط ومن كان حاضرًا. لا تستخدم مراقبة واسعة تستهلك الخصوصية دون أن تغير القرار.</p><p>بالنسبة لهدف «{esc(purpose)}»، ينبغي أن يصف خط الأساس ما يحدث الآن: ما الذي يستطيع الشخص فعله مستقلًا، وما التكييف الموجود، وما الحاجز، وكم يستغرق الوصول إلى مساعدة. هذا يسمح بمقارنة عادلة بعد التعديل.</p></section><section><h2>8. فرضيات متعددة بدل تفسير واحد</h2><p>ضع عدة تفسيرات قابلة للفحص: عامل صحي أو ألم، قلة نوم، ضغط أسري أو مدرسي، تنمر أو عنف، أثر دواء أو مادة، حاجز لغوي أو مالي، أو نقص معلومات. لا تختَر التفسير الأكثر راحة للمؤسسة قبل فحص البدائل.</p><p>اختبر الفرضية بتغيير آمن صغير أو إحالة مناسبة. إذا تحسنت النتيجة مع إزالة حاجز بيئي فهذا لا يثبت اضطرابًا داخل الشخص. وإذا استمر التدهور أو زاد الخطر فالأولوية للتقييم المهني لا لمزيد من التجارب.</p></section><section><h2>9. بروتوكول التنفيذ المتدرج</h2><div class="grid">{step_cards}</div></section><section><h2>10. خريطة الأدوار والتنسيق</h2><div class="grid">{role_cards}</div><p>يُكتب اسم المسؤول عن المتابعة ووسيلة التواصل والموعد. إذا لم تستجب جهة، يجب أن توجد قناة بديلة؛ الإحالة ليست مكتملة بمجرد تسليم رقم هاتف أو رابط.</p></section><section><h2>11. تكييف البيئة والمعلومات</h2><p>قد تشمل التكييفات وقتًا أكثر، مكانًا خاصًا، موعدًا أقصر، معلومات مكتوبة، مترجمًا مستقلًا، تغيير جدول، تقليل مثير رقمي، شخص دعم، أو عودة تدريجية. يُختار التعديل وفق الحاجز المحدد لا وفق قالب ثابت.</p><p>جرّب عنصرًا واحدًا كل مرة عندما يكون ذلك آمنًا، وحدد مدة التجربة ومؤشر النجاح وعلامة التوقف. التكييف الجيد يزيد المشاركة والاستقلال؛ إذا زاد الاعتماد أو الضيق أو كشف الخصوصية فيجب تعديله.</p></section><section><h2>12. التواصل الذي يقلل الضرر</h2><p>استخدم عبارات تصف الملاحظة: «لاحظت تغير النوم والغياب» بدل «أنت غير متعاون». اسأل «ما الذي يجعل هذا الموقف أصعب؟» و«ما المساعدة المقبولة؟». تجنب المحاضرات واللوم والمقارنة والوعود التي لا تستطيع تنفيذها.</p><p>في «{esc(title)}»، يجب أن توجد عبارة جاهزة لطلب المساعدة وقناة بديلة عند تعذر الكلام. عند الخطر، تُشرح حدود السرية بوضوح: ما المعلومات التي ستشارك، ومع من، ولماذا، وما الذي سيحدث بعد ذلك.</p></section><section><h2>13. العدالة واللغة والثقافة والموارد</h2><p>تتغير قابلية الخطة للتنفيذ بحسب اللغة والدخل والتنقل ورعاية الأطفال والوضع القانوني والإعاقة والثقة بالخدمات. خطة تحتاج موارد غير متاحة ليست خطة عادلة. ابحث عن بديل أقل كلفة وأقرب جغرافيًا ومتاح رقميًا وجسديًا.</p><p>احترم المعاني الثقافية دون استخدام الثقافة لتبرير العنف أو منع الرعاية. استخدم مترجمًا مهنيًا عندما تكون الخصوصية أو السلامة مهمة، ولا تجعل طفلًا أو قريبًا خاضعًا لطرف آخر مترجمًا لمعلومات حساسة.</p></section><section><h2>14. مؤشرات النتيجة وقواعد القرار</h2><table><thead><tr><th>#</th><th>المؤشر</th><th>طريقة المتابعة</th><th>القرار</th></tr></thead><tbody>{metric_rows}</tbody></table><p><strong>استمر</strong> عندما تتحسن الوظيفة والراحة والاختيار. <strong>عدّل عنصرًا واحدًا</strong> عندما لا يظهر أثر بعد فرص كافية. <strong>أوقف وأحل</strong> عند الألم أو الخطر أو التراجع أو رفض الشخص أو تجاوز حدود الاختصاص.</p></section>{safety_block(item)}<section><h2>15. خطة تطبيق خلال 30 يومًا</h2><div class="grid"><article class="card"><h3>الأيام 1–7: الفهم</h3><p>استمع للشخص، وحدد الهدف والسياق، واجمع خط الأساس، وافحص الخطر والعوامل الصحية والحواجز. لا تبدأ تغييرًا واسعًا قبل معرفة ما تريد قياسه.</p></article><article class="card"><h3>الأيام 8–14: التجربة</h3><p>اختر تعديلًا واحدًا منخفض المخاطر، ودرب الأطراف، وحدد علامة نجاح وتوقف، وثبت موعد المتابعة والإحالة عند الحاجة.</p></article><article class="card"><h3>الأيام 15–21: التحقق</h3><p>راجع المؤشرات ورأي الشخص، واختبر موقفًا ثانيًا، وافحص هل تحسن الاستقلال أم نُقلت المشكلة إلى مكان آخر.</p></article><article class="card"><h3>الأيام 22–30: القرار</h3><p>قرر الاستمرار أو التعديل أو التوقف أو الإحالة. اكتب نسخة مختصرة من الخطة، واحذف البيانات غير اللازمة، وحدد موعد المراجعة التالية.</p></article></div></section><section><h2>16. قائمة تحقق قبل اعتماد الخطة</h2><ul>{li(checklist)}</ul></section><section><h2>17. أسئلة شائعة</h2><details><summary>هل تكفي صفحة «{esc(title)}» لاتخاذ قرار علاجي؟</summary><p>لا. الصفحة تنظم الملاحظات والأسئلة والخطوات منخفضة المخاطر، ولا تستبدل تقييمًا فرديًا أو تشخيصًا أو وصف دواء.</p></details><details><summary>هل يعني التحسن في موقف واحد أن المشكلة انتهت؟</summary><p>لا. يجب اختبار النتيجة في وقت أو مكان أو مع شريك ثانٍ، لأن النجاح قد يعتمد على مساعدة كثيفة أو ظرف مؤقت.</p></details><details><summary>متى نغير الخطة؟</summary><p>عندما لا يظهر أثر بعد فرص كافية، أو يزيد الضيق أو الاعتماد، أو يرفض الشخص التعديل، أو تظهر معلومة صحية أو أمنية جديدة.</p></details><details><summary>ماذا نفعل عندما ترفض جهة الإحالة؟</summary><p>وثق سبب الرفض، واطلب قناة بديلة أو مستوى أعلى من الخدمة، ولا تترك الشخص بلا متابعة عند خطر أو تدهور وظيفي.</p></details><details><summary>ما معيار النجاح الأهم؟</summary><p>أن يقترب الشخص من هدفه «{esc(purpose)}» مع كرامة واختيار وأمان وأقل دعم ضروري، لا أن يبدو أكثر هدوءًا أو امتثالًا فقط.</p></details></section><section class="sources"><h2>18. المصادر والمنهج والمراجعة</h2><p>استخدمت الصفحة المصادر الرسمية التالية لتأسيس الإطار العام والحقوق والسلامة. لم تُستخرج منها وصفة فردية؛ جرى تحويل المبادئ إلى أسئلة وخطوات تحتاج مواءمة مهنية. حالة الصفحة: <strong>مراجعة داخلية</strong>، و<strong>المراجعة الخارجية المتخصصة موصى بها ولم تسجل كمكتملة</strong>.</p><ul>{source_items}</ul><p><a href="/source-registry/">سجل المصادر</a> · <a href="/trust/">الثقة والمنهج</a> · <a href="/sectors/{section}/">{esc(SECTION_LABELS[section])}</a></p></section></main><footer><p>© Health Renewal — محتوى تثقيفي قائم على المصادر ولا يحل محل التقييم المهني أو الطوارئ.</p></footer></body></html>'''


def render_hub(section: str, items: list[dict[str, Any]]) -> str:
    label, intro = SECTION_LABELS[section], SECTION_INTROS[section]
    cards = "".join(f'<article class="card"><span class="tag">دليل عملي</span><h2>{esc(item["title"])}</h2><p>{esc(item["purpose"])}.</p><p><strong>السياق:</strong> {esc(item["context"])}.</p><a href="guides/{esc(item["slug"])}/">فتح الدليل ←</a></article>' for item in items)
    schema = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "inLanguage": "ar", "name": label, "url": f"{BASE}/sectors/{section}/", "description": intro, "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [{"@type": "ListItem", "position": index, "name": item["title"], "url": f"{BASE}/{route_for(item)}"} for index, item in enumerate(items, 1)]}}, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(label)} | Health Renewal</title><meta name="description" content="{esc(intro)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/sectors/{section}/"><script type="application/ld+json">{schema}</script><style>:root{{--bg:#f5f8f7;--ink:#152722;--card:#fff;--line:#d2e1dc}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}header,main,footer{{max-width:1180px;margin:auto;padding:1.2rem}}a{{color:#075e4b}}.hero{{background:linear-gradient(135deg,#e4f3ed,#fff4df);border:1px solid var(--line);border-radius:24px;padding:clamp(1.4rem,5vw,3.5rem);margin:1rem 0 2rem}}h1{{font-size:clamp(2.2rem,6vw,4rem);line-height:1.25}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}}.card,.notice{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1.2rem}}.tag{{display:inline-block;background:#dcebe5;border-radius:999px;padding:.25rem .7rem}}.notice{{border-inline-start:6px solid #8a4f0b;margin:1rem 0 2rem}}</style><link rel="stylesheet" href="../../assets/platform/platform-core.css?v=1.1.0"><script defer src="../../assets/platform/platform-core.js?v=1.1.0"></script></head><body data-content-engine="v406" class="pt-platform"><header><nav><a href="/">الرئيسية</a> · <a href="/sectors/">القطاعات</a> · <a href="/trust/">الثقة والمنهج</a></nav></header><main><section class="hero"><p>قطاع متخصص</p><h1>{esc(label)}</h1><p>{esc(intro)}</p><p>يضم المركز {len(items)} دليلًا طويلًا، كل منها يوضح التقييم الوظيفي وخط الأساس وخطوات التطبيق ومؤشرات القرار وحدود السلامة والمصادر.</p></section><aside class="notice"><h2>حدود المركز</h2><p>المحتوى تثقيفي وتخطيطي ولا يثبت تشخيصًا ولا يصف علاجًا فرديًا. عند خطر مباشر أو إصابة أو تهديد للنفس أو الآخرين، تُستخدم خدمات الطوارئ والحماية المحلية فورًا.</p></aside><section><h2>الأدلة المنشورة</h2><div class="grid">{cards}</div></section><section><h2>كيف تستخدم المركز؟</h2><ol><li>ابدأ بالموقف الأقرب لا باسم تشخيص.</li><li>اقرأ حدود الاستخدام وعلامات التصعيد أولًا.</li><li>اختر مؤشرًا واحدًا وخط أساس قصيرًا.</li><li>جرّب تعديلًا منخفض المخاطر وحدد موعد المراجعة.</li><li>أحل إلى جهة مؤهلة عندما تتجاوز الحاجة حدود الدعم التثقيفي.</li></ol></section></main><footer><p>© Health Renewal — مراجعة داخلية، والمراجعة الخارجية المتخصصة موصى بها.</p></footer></body></html>'''


def write_sitemap(site: Path, section: str, items: list[dict[str, Any]]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    urls = [f"{BASE}/sectors/{section}/"] + [f"{BASE}/{route_for(item)}" for item in items]
    for url in urls:
        node = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(node, f"{{{namespace}}}loc").text = url
        ET.SubElement(node, f"{{{namespace}}}lastmod").text = REVIEWED_AT
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(site / SITEMAPS[section], encoding="utf-8", xml_declaration=True)
    return len(urls)


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    catalog = load_catalog()
    validate_catalog(catalog)
    pages = catalog["pages"]
    routes, word_counts, heading_counts, citation_counts, topic_mentions = [], [], [], [], []
    safety_pages = 0
    for item in pages:
        route, source = route_for(item), render_page(item)
        words, headings = visible_words(source), source.count("<h2>")
        citations, mentions = source.count('target="_blank" rel="noopener noreferrer"'), source.count(item["title"])
        if words < 1800: raise ValueError(f"Thin v406 page: {route} ({words})")
        if headings < 18: raise ValueError(f"Insufficient v406 sections: {route} ({headings})")
        if citations < 3: raise ValueError(f"Insufficient v406 citations: {route} ({citations})")
        if mentions < 16: raise ValueError(f"Insufficient topic specificity: {route} ({mentions})")
        if FORBIDDEN.search(source): raise ValueError(f"Forbidden language: {route}")
        if any(phrase in source for phrase in GENERIC_PHRASES): raise ValueError(f"Generic placeholder phrase: {route}")
        if 'class="notice topic-check"' not in source: raise ValueError(f"Missing specialized safety block: {route}")
        safety_pages += 1
        target = site / route / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        routes.append(route); word_counts.append(words); heading_counts.append(headings); citation_counts.append(citations); topic_mentions.append(mentions)
    section_counts, sitemap_counts = {}, {}
    for section in EXPECTED_DISTRIBUTION:
        section_items = [item for item in pages if item["section"] == section]
        hub = site / "sectors" / section / "index.html"
        hub.parent.mkdir(parents=True, exist_ok=True)
        hub.write_text(render_hub(section, section_items), encoding="utf-8")
        section_counts[section] = len(section_items)
        sitemap_counts[SITEMAPS[section]] = write_sitemap(site, section, section_items)
    report = {"version": VERSION, "status": "passed", "review_status": catalog["status"], "external_specialist_review_completed": catalog["external_specialist_review_completed"], "reviewed_at": catalog["reviewed_at"], "next_review_due": catalog["next_review_due"], "page_count": len(routes), "hub_count": 2, "distribution": section_counts, "unique_routes": len(set(routes)), "total_words": sum(word_counts), "minimum_words": min(word_counts), "minimum_h2": min(heading_counts), "minimum_citations": min(citation_counts), "minimum_topic_mentions": min(topic_mentions), "specialized_safety_pages": safety_pages, "source_count": len(SOURCES), "sitemap_counts": sitemap_counts, "routes": routes, "quality_gates": {"catalog_valid": True, "all_routes_unique": len(routes) == len(set(routes)) == 30, "all_pages_long_form": min(word_counts) >= 1800, "all_pages_topic_specific": min(topic_mentions) >= 16, "all_pages_have_safety_block": safety_pages == 30, "all_pages_have_sources": min(citation_counts) >= 3, "women_hub_present": (site / "sectors/women/index.html").is_file(), "youth_hub_present": (site / "sectors/youth/index.html").is_file()}}
    api = site / "api" / "women-youth-expansion-v406.json"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the women and youth expansion v406.")
    parser.add_argument("site", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
