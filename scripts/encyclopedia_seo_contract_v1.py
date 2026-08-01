#!/usr/bin/env python3
"""Shared SEO and search-intent contract for the 2,000-page encyclopedia.

The module is deterministic and does not add clinical claims. It converts the
existing domain/facet/profile data into page metadata, user-visible search
questions, and matching FAQ structured data.
"""
from __future__ import annotations

from typing import Any

CONTRACT_VERSION = 1
EXPECTED_DETAIL_PAGES = 2000
SEARCH_INTENT_MARKER = 'data-search-intent="encyclopedia-v1"'
FAQ_MARKER = 'data-search-intent-faq="encyclopedia-v1"'

INTENT_PROFILES: dict[str, dict[str, str]] = {
    "definition": {"code": "informational-definition", "ar": "معلوماتية تعريفية", "stage": "الفهم الأولي", "goal": "فهم المعنى الدقيق وحدود المصطلح"},
    "signs": {"code": "informational-signs", "ar": "معلوماتية استكشافية", "stage": "التعرّف إلى العلامات", "goal": "فهم العلامات المحتملة وطريقة ملاحظتها دون تشخيص ذاتي"},
    "factors": {"code": "informational-factors", "ar": "معلوماتية تفسيرية", "stage": "فهم العوامل", "goal": "تمييز عوامل الخطر والمحفزات وعوامل الحماية عن السبب المؤكد"},
    "assessment": {"code": "evaluation-preparation", "ar": "استعدادية للتقييم", "stage": "الاستعداد للمختص", "goal": "معرفة ما يجمعه التقييم المهني وما ينبغي تحضيره"},
    "differential": {"code": "comparative-differential", "ar": "مقارنة وتفريق", "stage": "منع الخلط", "goal": "مقارنة الظواهر المتشابهة وفهم حدود التشخيص التفريقي"},
    "psychotherapy": {"code": "treatment-information", "ar": "معلوماتية علاجية", "stage": "فهم خيارات الدعم", "goal": "فهم أهداف العلاج النفسي وحدوده وكيفية قياس التقدم"},
    "cbt": {"code": "treatment-cbt", "ar": "معلوماتية علاجية متخصصة", "stage": "فهم التدخل", "goal": "فهم المنظور المعرفي السلوكي وتطبيقاته وحدوده"},
    "self_help": {"code": "practical-self-help", "ar": "عملية تطبيقية", "stage": "خطوات آمنة أولية", "goal": "اختيار خطوات دعم ذاتي محدودة وآمنة ومعرفة متى لا تكفي"},
    "coping": {"code": "practical-coping", "ar": "عملية لحل المشكلة", "stage": "التعامل اليومي", "goal": "اختيار استراتيجيات تعامل تقلل الضرر وتحافظ على الوظيفة"},
    "prevention": {"code": "preventive", "ar": "وقائية", "stage": "تقليل المخاطر", "goal": "التعرف إلى الإنذارات المبكرة وتعزيز عوامل الحماية"},
    "early": {"code": "early-intervention", "ar": "تدخل مبكر", "stage": "التحرك المبكر", "goal": "معرفة متى وكيف يبدأ طلب الدعم قبل اتساع الأثر"},
    "children": {"code": "audience-children", "ar": "موجهة للأطفال والأسرة", "stage": "فهم المرحلة العمرية", "goal": "فهم ظهور الموضوع لدى الأطفال ضمن النمو والبيت والمدرسة"},
    "adolescents": {"code": "audience-adolescents", "ar": "موجهة للمراهقين والأسرة", "stage": "فهم المرحلة العمرية", "goal": "فهم الموضوع لدى المراهقين مع مراعاة الهوية والأقران والدراسة والسلامة"},
    "adults": {"code": "audience-adults", "ar": "موجهة للبالغين", "stage": "فهم الأثر الوظيفي", "goal": "فهم أثر الموضوع على العمل والعلاقات والرعاية الذاتية"},
    "older": {"code": "audience-older-adults", "ar": "موجهة لكبار السن", "stage": "فهم العمر والصحة", "goal": "فهم التغيرات النفسية مع مراعاة الصحة والدواء والفقد والعزلة"},
    "family": {"code": "context-family", "ar": "أسرية تطبيقية", "stage": "تنظيم الدعم الأسري", "goal": "فهم دور الأسرة والحدود والتواصل وتوزيع الرعاية"},
    "relationships": {"code": "context-relationships", "ar": "علاقية تطبيقية", "stage": "تحسين التواصل والحدود", "goal": "فهم أثر الموضوع في العلاقات والأمان والاحتياجات المتبادلة"},
    "work": {"code": "context-work", "ar": "مهنية تطبيقية", "stage": "دعم الأداء في العمل", "goal": "فهم أثر الموضوع في العمل والتكيفات والحدود المهنية"},
    "school": {"code": "context-school", "ar": "تعليمية تطبيقية", "stage": "دعم التعلم والمشاركة", "goal": "فهم أثر الموضوع في التعلم والحضور والتواصل مع المدرسة"},
    "quality": {"code": "outcome-quality-of-life", "ar": "موجهة للنتائج", "stage": "تحسين جودة الحياة", "goal": "ربط الدعم بنتائج وظيفية قابلة للمتابعة في الحياة اليومية"},
}

PRIMARY_QUERY_TEMPLATES: dict[str, str] = {
    "definition": "ما هو {domain} وما المقصود بزاوية {facet}؟",
    "signs": "ما علامات {domain} وكيف تُفهم من زاوية {facet}؟",
    "factors": "ما أسباب وعوامل {domain} وما الذي يفسرها بدقة؟",
    "assessment": "كيف يتم تقييم {domain} وما المعلومات المطلوبة؟",
    "differential": "ما الفرق بين {domain} والحالات أو الظواهر المتشابهة؟",
    "psychotherapy": "كيف يساعد العلاج النفسي في موضوع {domain}؟",
    "cbt": "كيف يُستخدم العلاج المعرفي السلوكي مع {domain}؟",
    "self_help": "ما خطوات الدعم الذاتي الآمنة عند التعامل مع {domain}؟",
    "coping": "كيف أتعامل عمليًا مع {domain} في الحياة اليومية؟",
    "prevention": "كيف يمكن تقليل مخاطر تفاقم {domain}؟",
    "early": "متى نحتاج إلى تدخل مبكر بخصوص {domain}؟",
    "children": "كيف يظهر {domain} لدى الأطفال ومتى يحتاج إلى تقييم؟",
    "adolescents": "كيف يظهر {domain} لدى المراهقين وكيف ندعمهم؟",
    "adults": "كيف يؤثر {domain} في حياة البالغين وعملهم وعلاقاتهم؟",
    "older": "كيف نفهم {domain} لدى كبار السن؟",
    "family": "كيف تتعامل الأسرة مع {domain} دون وصم أو سيطرة؟",
    "relationships": "كيف يؤثر {domain} في العلاقات والتواصل والحدود؟",
    "work": "كيف يؤثر {domain} في العمل وما التكيفات الممكنة؟",
    "school": "كيف يؤثر {domain} في المدرسة والتعلم والمشاركة؟",
    "quality": "كيف يؤثر {domain} في جودة الحياة وكيف نقيس التحسن؟",
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def seo_title(item: dict[str, Any]) -> str:
    """Return a descriptive, human title with the query topic first."""
    title = f"{item['domain_ar']}: {item['facet']['ar']} | الموسوعة النفسية"
    if len(title) <= 78:
        return title
    return f"{item['ar']} | موسوعة الصحة النفسية"


def meta_description(item: dict[str, Any]) -> str:
    """Return a unique, non-promotional description in a safe SERP range."""
    text = (
        f"دليل عربي موسع عن {item['domain_ar']} من زاوية {item['facet']['ar']}: "
        f"{item['facet']['focus']}. يشرح المعنى والفروق والتقييم والخطوات العملية ومتى تُطلب المساعدة."
    )
    if len(text) > 225:
        text = text[:221].rsplit(" ", 1)[0].rstrip("،؛:.-") + "…"
    if len(text) < 90:
        text += " مع مصادر مؤسسية وروابط للتوسع الآمن."
    return text


def search_intent_for(item: dict[str, Any]) -> dict[str, Any]:
    key = str(item["facet"]["key"])
    if key not in INTENT_PROFILES or key not in PRIMARY_QUERY_TEMPLATES:
        raise ValueError(f"Unsupported encyclopedia facet for search intent: {key}")
    profile = INTENT_PROFILES[key]
    domain = str(item["domain_ar"])
    facet = str(item["facet"]["ar"])
    primary = PRIMARY_QUERY_TEMPLATES[key].format(domain=domain, facet=facet)
    queries = _unique(
        [
            primary,
            f"{facet} في {domain}",
            f"دليل {domain} من ناحية {facet}",
            f"كيف أفهم {domain} بصورة صحيحة دون تشخيص ذاتي؟",
            f"متى أطلب مساعدة مختص بخصوص {domain}؟",
            f"{item['domain_en']} {item['facet']['en']}",
        ]
    )
    return {
        "contract": "encyclopedia-search-intent-v1",
        "type": profile["code"],
        "type_ar": profile["ar"],
        "stage": profile["stage"],
        "goal": profile["goal"],
        "primary_query": primary,
        "secondary_queries": queries[1:],
        "all_queries": queries,
        "audience": ["الأفراد", "الأسر", "المعلمون", "المختصون"],
        "answer_scope": item["facet"]["focus"],
    }


def faq_items(item: dict[str, Any], profile: dict[str, Any], intent: dict[str, Any]) -> list[tuple[str, str]]:
    domain = str(item["domain_ar"])
    facet = item["facet"]
    observations = list(profile.get("observations", []))
    distinctions = list(profile.get("distinctions", []))
    actions = list(facet.get("actions", []))
    definition = str(profile.get("definition", "")).strip()
    return [
        (
            str(intent["primary_query"]),
            f"{definition} وتركز هذه الصفحة تحديدًا على {facet['focus']}، مع فصل التثقيف العام عن التقييم الفردي.",
        ),
        (
            f"ما الذي ينبغي ملاحظته عند بحث {facet['ar']} في {domain}؟",
            "تُراجع الملاحظات عبر الزمن والسياق والأثر الوظيفي. ومن النقاط المنظمة: "
            + "، ".join(observations[:3])
            + ".",
        ),
        (
            f"ما الذي يمنع الخلط عند فهم {domain}؟",
            "من المهم عدم الاعتماد على عرض واحد أو موقف منفرد. وتشمل الفروق الأساسية: "
            + "، ".join(distinctions[:2])
            + ".",
        ),
        (
            f"ما أول خطوة عملية مرتبطة بـ{facet['ar']}؟",
            "ابدأ بخطوة محددة قابلة للمتابعة: " + " ثم ".join(actions[:2]) + "، مع مراعاة العمر والسياق والهدف.",
        ),
        (
            f"متى أطلب تقييمًا مهنيًا بخصوص {domain}؟",
            f"اطلب تقييمًا مهنيًا عندما يستمر أثر {domain} أو يتفاقم، أو يعطل النوم أو الدراسة أو العمل أو العلاقات، أو يظهر خطر مباشر أو تغير سريع أو تداخل طبي أو دوائي.",
        ),
    ]
