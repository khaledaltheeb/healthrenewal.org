#!/usr/bin/env python3
"""Publish the evidence-bounded capabilities library (v280).

The section does not treat illness, pain, crisis, or disability as a gift.
It turns possible strengths into person-specific, falsifiable hypotheses and
tests them with accessible tasks, safety limits, and shared decisions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v280" / "capabilities-100-ar.json"
PROFILE_DIR = ROOT / "content" / "v280" / "profiles"
EVIDENCE_DIR = ROOT / "content" / "v280" / "evidence"
PROFILE_FILES = (
    ROOT / "content" / "v280" / "profiles" / "chronic-health.json",
    ROOT / "content" / "v280" / "profiles" / "genetic-metabolic.json",
    ROOT / "content" / "v280" / "profiles" / "motor-neurological.json",
    ROOT / "content" / "v280" / "profiles" / "neurodevelopmental-learning.json",
    ROOT / "content" / "v280" / "profiles" / "progressive-psychosocial.json",
    ROOT / "content" / "v280" / "profiles" / "sensory-communication.json",
)
EVIDENCE_FILES = (
    ROOT / "content" / "v280" / "evidence" / "chronic-health-ar.json",
    ROOT / "content" / "v280" / "evidence" / "genetic-metabolic-ar.json",
    ROOT / "content" / "v280" / "evidence" / "motor-neurological-ar.json",
    ROOT
    / "content"
    / "v280"
    / "evidence"
    / "neurodevelopmental-learning-ar.json",
    ROOT
    / "content"
    / "v280"
    / "evidence"
    / "progressive-psychosocial-ar.json",
    ROOT / "content" / "v280" / "evidence" / "sensory-communication-ar.json",
)
OUTSIDE_THE_BOX_DATA_PATH = (
    ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
)
CSS_PATH = ROOT / "assets" / "css" / "capabilities-v280.css"
JS_PATH = ROOT / "assets" / "js" / "capabilities-v280.js"

VERSION = 280
UPDATED = "2026-07-27"
# Use the latest verification date that had fully elapsed in every timezone
# when this evidence wave was published. This avoids treating same-day
# verification in Asia/Amman as a future date on UTC CI runners.
SOURCE_VERIFIED_THROUGH = "2026-07-26"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_ORIGIN = "https://khaledaltheeb.github.io"
BASE_PATH = "/pterminology-site/"
SECTION = "capabilities"
SITEMAP_NAME = "sitemap-capabilities.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
BRIDGE_START = "<!-- capabilities-v280:start -->"
BRIDGE_END = "<!-- capabilities-v280:end -->"

SOURCE_FIELDS = {
    "id",
    "publisher",
    "title",
    "url",
    "year",
    "source_type",
    "verified_at",
    "claims_supported",
    "status",
}
EVIDENCE_CLAIM_TYPES = (
    "profile-boundary",
    "access-and-intervention",
    "safety-and-differential",
)
EVIDENCE_CLAIM_FIELDS = {
    "id",
    "type",
    "statement",
    "what_it_supports",
    "what_it_does_not_support",
    "evidence_character",
    "source_ids",
}
EVIDENCE_CLAIM_TITLES = {
    "profile-boundary": "حدود ملف الحالة",
    "access-and-intervention": "الوصول والتدخل",
    "safety-and-differential": "الأمان والتشخيص التفريقي",
}
EVIDENCE_CHARACTER_TITLES = {
    "official-current-guidance": "إرشاد رسمي حالي",
    "guideline-backed": "توصية إرشادية",
    "expert-reviewed-living-reference": "مرجع سريري خبير ومحدّث",
    "systematic-review-direct-heterogeneous": "مراجعة مباشرة متغايرة",
    "systematic-review-limited-directness": "مراجعة محدودة المباشرة",
    "mixed-sources-no-causal-inference": "مصادر مختلطة بلا استدلال سببي",
}

CATEGORY_AUTHORITIES = {
    "neurodevelopmental-learning": {
        "publisher": "Eunice Kennedy Shriver National Institute of Child Health and Human Development",
        "title": "Intellectual and Developmental Disabilities",
        "url": "https://www.nichd.nih.gov/health/topics/idds",
    },
    "genetic-metabolic": {
        "publisher": "U.S. National Library of Medicine",
        "title": "MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/",
    },
    "motor-neurological": {
        "publisher": "National Institute of Neurological Disorders and Stroke",
        "title": "Health Information — Disorders",
        "url": "https://www.ninds.nih.gov/health-information/disorders",
    },
    "sensory-communication": {
        "publisher": "National Institute on Deafness and Other Communication Disorders",
        "title": "Health Information",
        "url": "https://www.nidcd.nih.gov/health",
    },
    "chronic-health": {
        "publisher": "U.S. National Library of Medicine",
        "title": "MedlinePlus Health Topics",
        "url": "https://medlineplus.gov/healthtopics.html",
    },
    "progressive-psychosocial": {
        "publisher": "National Institutes of Health",
        "title": "Health Information",
        "url": "https://www.nih.gov/health-information",
    },
}

CATEGORY_ADAPTATIONS = {
    "neurodevelopmental-learning": [
        "تعليمات قصيرة وواضحة مع مثال أو نموذج، ووقت معالجة لا يُفسر كغياب للفهم.",
        "تقسيم المهمة مع إبقاء الهدف النهائي ظاهرًا، وخفض التلميحات وفق بيانات لا انطباع.",
        "إتاحة الكلام والصورة والكتابة وAAC والفعل بحسب هدف القياس.",
        "تدريب المهارة في الروتين الحقيقي ثم اختبار انتقالها إلى مثال أو شريك جديد.",
    ],
    "genetic-metabolic": [
        "اختيار قناة تواصل واستجابة لا تجعل الكلام أو الحركة الدقيقة شرطًا لإظهار الفهم.",
        "ربط الجرعة والمدة بالاستقرار الصحي والطاقة، مع إبقاء خطة العلاج خارج التجريب.",
        "استخدام صور أو نمذجة أو أدوات تنظيم عند ثبوت فائدتها للشخص لا لمجرد التشخيص.",
        "تنسيق الهدف بين الأسرة والتعليم أو العمل والفريق الصحي من دون تداول بيانات غير لازمة.",
    ],
    "motor-neurological": [
        "فصل صاحب القرار وصاحب الفكرة عن منفذ الحركة، وتوثيق دور كل شريك.",
        "ضبط الوضعية والوصول والتقنية قبل تقييم اليد أو الكلام أو السرعة.",
        "تقليل الطاقة المطلوبة للمهمة واستخدام كرسي أو أداة أو إدخال بديل بوصفه نجاحًا لا فشلًا.",
        "إعداد نظام وصول احتياطي وصيانة وتدريب للشركاء عند الاعتماد على التقنية.",
    ],
    "sensory-communication": [
        "إتاحة المعلومة بالقناة اللغوية والحسية الأقوى للشخص مع بديل عند التعب أو تغير البيئة.",
        "منع استخدام غياب الاستجابة في قناة غير متاحة دليلًا على غياب الفهم.",
        "اختبار عامل بيئي واحد في كل مرة مثل الإضاءة أو الضوضاء أو التباين أو المسافة.",
        "تدريب الشركاء على الانتظار والوصف والترجمة أو اللمس المتفق عليه وعدم التلقين.",
    ],
    "chronic-health": [
        "جدولة مرنة وفواصل وخيار عمل غير متزامن أو عن بعد عندما يثبت أنه يحمي الصحة.",
        "قياس الأثر المتأخر بعد المهمة، لا جودة الأداء اللحظي فقط.",
        "إعداد خطة لأيام التفاقم والغياب والعودة من دون عقوبة أو كشف صحي زائد.",
        "تقييم الناتج والاستقلال بدل الحضور المتواصل أو القدرة على دفع الجسم عبر الأعراض.",
    ],
    "progressive-psychosocial": [
        "تثبيت الوصول والتواصل والتفضيلات مبكرًا وإعادة التقييم مع تغير الوظيفة.",
        "استخدام جرعات مهام قابلة للعكس وخطة بديلة عند التفاقم أو الأزمة.",
        "حماية النوم والطاقة والاستقرار النفسي وعدم مكافأة الإفراط أو إخفاء الأعراض.",
        "دعم التعليم أو العمل أو الدور الاجتماعي المختار مع قرار مشترك وخطة انتكاس أو انتقال.",
    ],
}

OUTSIDE_THE_BOX_ALIASES = {
    "dyslexia": "specific-learning-disorder-reading",
    "written-expression-difficulty": "specific-learning-disorder-written-expression",
    "dyscalculia": "specific-learning-disorder-mathematics",
    "tourette-tic-disorders": "tic-disorder-tourette",
    "22q11-deletion-syndrome": "22q11-2-deletion-syndrome",
    "congenital-hypothyroidism": "congenital-hypothyroidism-developmental-support",
    "traumatic-brain-injury": "acquired-brain-injury",
    "charcot-marie-tooth-disease": "charcot-marie-tooth",
    "arthrogryposis": "arthrogryposis-multiplex-congenita",
    "low-vision": "vision-impairment-low-vision",
    "hearing-loss": "hearing-loss-deafness",
}

DIRECT_AUTHORITY_OVERRIDES = {
    "joubert-syndrome": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Joubert syndrome — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/joubert-syndrome/",
    },
    "mitochondrial-diseases": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Mitochondrial Diseases — MedlinePlus",
        "url": "https://medlineplus.gov/mitochondrialdiseases.html",
    },
    "epilepsy": {
        "publisher": "World Health Organization",
        "title": "Epilepsy",
        "url": "https://www.who.int/news-room/fact-sheets/detail/epilepsy",
    },
    "stroke": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Stroke",
        "url": "https://www.cdc.gov/stroke/about/index.html",
    },
    "becker-muscular-dystrophy": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Duchenne and Becker muscular dystrophy — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/duchenne-and-becker-muscular-dystrophy/",
    },
    "friedreich-ataxia": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Friedreich ataxia — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/friedreich-ataxia/",
    },
    "hereditary-spastic-paraplegia": {
        "publisher": "National Institute of Neurological Disorders and Stroke",
        "title": "Hereditary Spastic Paraplegia",
        "url": "https://www.ninds.nih.gov/health-information/disorders/hereditary-spastic-paraplegia",
    },
    "myasthenia-gravis": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Myasthenia Gravis — MedlinePlus",
        "url": "https://medlineplus.gov/myastheniagravis.html",
    },
    "dystonia": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Dystonia — MedlinePlus",
        "url": "https://medlineplus.gov/dystonia.html",
    },
    "severe-burns-contractures": {
        "publisher": "World Health Organization",
        "title": "Burns",
        "url": "https://www.who.int/news-room/fact-sheets/detail/burns",
    },
    "blindness": {
        "publisher": "World Health Organization",
        "title": "Blindness and vision impairment",
        "url": "https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment",
    },
    "deafness": {
        "publisher": "World Health Organization",
        "title": "Deafness and hearing loss",
        "url": "https://www.who.int/news-room/fact-sheets/detail/deafness-and-hearing-loss",
    },
    "optic-nerve-hypoplasia": {
        "publisher": "American Association for Pediatric Ophthalmology and Strabismus",
        "title": "Optic Nerve Hypoplasia",
        "url": "https://aapos.org/glossary/optic-nerve-hypoplasia",
    },
    "aphasia": {
        "publisher": "National Institute on Deafness and Other Communication Disorders",
        "title": "Aphasia",
        "url": "https://www.nidcd.nih.gov/health/aphasia",
    },
    "acquired-apraxia-of-speech": {
        "publisher": "National Institute on Deafness and Other Communication Disorders",
        "title": "Apraxia of Speech",
        "url": "https://www.nidcd.nih.gov/health/apraxia-speech",
    },
    "dysarthria": {
        "publisher": "American Speech-Language-Hearing Association",
        "title": "Dysarthria",
        "url": "https://www.asha.org/public/speech/disorders/dysarthria/",
    },
    "moebius-syndrome": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Moebius syndrome — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/moebius-syndrome/",
    },
    "cleft-lip-palate-communication": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "Cleft Lip and Cleft Palate",
        "url": "https://www.cdc.gov/birth-defects/about/cleft-lip-cleft-palate.html",
    },
    "cystic-fibrosis": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Cystic Fibrosis",
        "url": "https://www.cdc.gov/cystic-fibrosis/about/index.html",
    },
    "sickle-cell-disease": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Sickle Cell Disease",
        "url": "https://www.cdc.gov/sickle-cell/about/index.html",
    },
    "hemophilia": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Hemophilia",
        "url": "https://www.cdc.gov/hemophilia/about/index.html",
    },
    "type-1-diabetes": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Type 1 Diabetes",
        "url": "https://www.cdc.gov/diabetes/about/about-type-1-diabetes.html",
    },
    "chronic-kidney-disease": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Chronic Kidney Disease",
        "url": "https://www.cdc.gov/kidney-disease/about/index.html",
    },
    "congenital-heart-disease": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Congenital Heart Defects",
        "url": "https://www.cdc.gov/heart-defects/about/index.html",
    },
    "systemic-lupus-erythematosus": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Systemic Lupus Erythematosus",
        "url": "https://www.cdc.gov/lupus/about/index.html",
    },
    "inflammatory-bowel-disease": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Inflammatory Bowel Disease",
        "url": "https://www.cdc.gov/inflammatory-bowel-disease/about/index.html",
    },
    "severe-asthma": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About Asthma",
        "url": "https://www.cdc.gov/asthma/about/index.html",
    },
    "severe-food-allergy": {
        "publisher": "U.S. Food and Drug Administration",
        "title": "Food Allergies",
        "url": "https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies",
    },
    "childhood-cancer-late-effects": {
        "publisher": "U.S. National Cancer Institute",
        "title": "Late Effects of Treatment for Childhood Cancer",
        "url": "https://www.cancer.gov/types/childhood-cancers/late-effects-pdq",
    },
    "me-cfs": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "About ME/CFS",
        "url": "https://www.cdc.gov/me-cfs/about/index.html",
    },
    "long-covid": {
        "publisher": "U.S. Centers for Disease Control and Prevention",
        "title": "Long COVID Basics",
        "url": "https://www.cdc.gov/long-covid/about/index.html",
    },
    "multiple-sclerosis": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Multiple Sclerosis — MedlinePlus",
        "url": "https://medlineplus.gov/multiplesclerosis.html",
    },
    "parkinson-disease": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Parkinson's Disease — MedlinePlus",
        "url": "https://medlineplus.gov/parkinsonsdisease.html",
    },
    "huntington-disease": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Huntington's disease — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/huntingtons-disease/",
    },
    "amyotrophic-lateral-sclerosis": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Amyotrophic Lateral Sclerosis — MedlinePlus",
        "url": "https://medlineplus.gov/amyotrophiclateralsclerosis.html",
    },
    "marfan-syndrome": {
        "publisher": "U.S. National Library of Medicine",
        "title": "Marfan syndrome — MedlinePlus Genetics",
        "url": "https://medlineplus.gov/genetics/condition/marfan-syndrome/",
    },
    "severe-scoliosis": {
        "publisher": "National Institute of Arthritis and Musculoskeletal and Skin Diseases",
        "title": "Scoliosis in Children and Teens",
        "url": "https://www.niams.nih.gov/health-topics/scoliosis",
    },
    "chronic-pain": {
        "publisher": "National Center for Complementary and Integrative Health",
        "title": "Chronic Pain and Complementary Health Approaches",
        "url": "https://www.nccih.nih.gov/health/chronic-pain-and-complementary-health-approaches-usefulness-and-safety",
    },
    "schizophrenia-functional-support": {
        "publisher": "U.S. National Institute of Mental Health",
        "title": "Schizophrenia",
        "url": "https://www.nimh.nih.gov/health/topics/schizophrenia",
    },
    "bipolar-disorder-functional-support": {
        "publisher": "U.S. National Institute of Mental Health",
        "title": "Bipolar Disorder",
        "url": "https://www.nimh.nih.gov/health/topics/bipolar-disorder",
    },
}


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def ul(items: Iterable[str], class_name: str = "") -> str:
    cls = f' class="{e(class_name)}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def source_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in data["sources"]}


def unique_in_order(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def load_profiles(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    if not PROFILE_DIR.is_dir():
        raise ValueError("Missing condition-specific capability profile directory")
    actual_paths = set(PROFILE_DIR.glob("*.json"))
    expected_paths = set(PROFILE_FILES)
    if actual_paths != expected_paths:
        missing = sorted(path.name for path in expected_paths - actual_paths)
        unexpected = sorted(path.name for path in actual_paths - expected_paths)
        raise ValueError(
            f"Capability profile file set mismatch; missing={missing}, "
            f"unexpected={unexpected}"
        )
    records: list[dict[str, str]] = []
    required = {
        "slug",
        "position",
        "ability_focus",
        "access_priority",
        "safety_priority",
        "task_trial",
        "functional_goal",
    }
    condition_categories = {
        item["slug"]: item["category"] for item in data["conditions"]
    }
    for path in PROFILE_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != VERSION or payload.get("language") != "ar":
            raise ValueError(f"Invalid capability profile header: {path.name}")
        category = payload.get("category")
        if category not in data["categories"]:
            raise ValueError(f"Unknown profile category in {path.name}: {category}")
        for profile in payload.get("profiles", []):
            if set(profile) != required:
                raise ValueError(
                    f"Profile contract mismatch for {profile.get('slug')} in {path.name}"
                )
            slug = profile["slug"]
            if condition_categories.get(slug) != category:
                raise ValueError(
                    f"Profile category mismatch for {slug}: "
                    f"{category!r} != {condition_categories.get(slug)!r}"
                )
            for key in required - {"slug"}:
                if len(str(profile[key]).strip()) < 60:
                    raise ValueError(f"Profile field is too shallow: {slug}.{key}")
            records.append(profile)
    expected = [item["slug"] for item in data["conditions"]]
    slugs = [item["slug"] for item in records]
    if len(records) != 100 or len(set(slugs)) != 100:
        raise ValueError(
            f"Exactly 100 unique condition profiles are required, found {len(records)}"
        )
    if set(slugs) != set(expected):
        raise ValueError(
            "Capability profile slugs must match the complete condition registry"
        )
    return {item["slug"]: item for item in records}


def load_evidence_packets(data: dict[str, Any]) -> dict[str, Any]:
    """Load condition-level selected evidence without manufacturing certainty.

    Each selected category must be complete: a file cannot quietly cover only
    its easiest conditions. Every claim declares both its supported use and
    the inference that the cited evidence does not permit.
    """

    if not EVIDENCE_DIR.is_dir():
        raise ValueError("Missing selected-evidence packet directory")
    actual_paths = set(EVIDENCE_DIR.glob("*.json"))
    expected_paths = set(EVIDENCE_FILES)
    if actual_paths != expected_paths:
        missing = sorted(path.name for path in expected_paths - actual_paths)
        unexpected = sorted(path.name for path in actual_paths - expected_paths)
        raise ValueError(
            f"Selected-evidence file set mismatch; missing={missing}, "
            f"unexpected={unexpected}"
        )
    paths = EVIDENCE_FILES

    condition_by_slug = {item["slug"]: item for item in data["conditions"]}
    base_source_ids = {item["id"] for item in data["sources"]}
    records: list[dict[str, Any]] = []
    selected_sources: list[dict[str, Any]] = []
    selection_methods: dict[str, dict[str, Any]] = {}
    character_labels: dict[str, str] | None = None
    covered_categories: set[str] = set()
    evidence_claim_ids: set[str] = set()

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != VERSION or payload.get("language") != "ar":
            raise ValueError(f"Invalid selected-evidence header: {path.name}")
        if payload.get("external_review_completed") is not False:
            raise ValueError(
                f"Selected evidence cannot claim external review: {path.name}"
            )
        if payload.get("search_updated") != UPDATED:
            raise ValueError(
                f"Selected evidence search date must be {UPDATED}: {path.name}"
            )
        category = payload.get("category")
        if category not in data["categories"]:
            raise ValueError(f"Unknown selected-evidence category: {category!r}")
        if category in covered_categories:
            raise ValueError(f"Duplicate selected-evidence category: {category}")
        covered_categories.add(category)

        method = payload.get("selection_method")
        required_method = {
            "scope",
            "selection_order",
            "exclusions",
            "certainty_policy",
            "live_search_boundary",
            "review_boundary",
        }
        if not isinstance(method, dict) or set(method) != required_method:
            raise ValueError(f"Evidence selection method is incomplete: {path.name}")
        if (
            not isinstance(method["selection_order"], list)
            or not isinstance(method["exclusions"], list)
            or len(method["selection_order"]) < 4
            or len(method["exclusions"]) < 4
            or not all(
                isinstance(item, str) and item.strip()
                for item in [
                    method["scope"],
                    method["certainty_policy"],
                    method["live_search_boundary"],
                    method["review_boundary"],
                    *method["selection_order"],
                    *method["exclusions"],
                ]
            )
        ):
            raise ValueError(f"Evidence selection method is too shallow: {path.name}")
        selection_methods[category] = method

        labels = payload.get("evidence_character_labels")
        if (
            not isinstance(labels, dict)
            or set(labels) != set(EVIDENCE_CHARACTER_TITLES)
            or not all(isinstance(item, str) and item.strip() for item in labels.values())
        ):
            raise ValueError(f"Evidence character labels are incomplete: {path.name}")
        if character_labels is None:
            character_labels = labels
        elif labels != character_labels:
            raise ValueError("Evidence character labels must match across category files")

        for source in payload.get("sources", []):
            if set(source) != SOURCE_FIELDS:
                raise ValueError(
                    f"Selected source contract mismatch: {source.get('id')!r}"
                )
            if not re.fullmatch(
                r"[a-z0-9]+(?:-[a-z0-9]+)*", str(source.get("id", ""))
            ):
                raise ValueError(f"Unsafe selected source id: {source.get('id')!r}")
            if not str(source.get("url", "")).startswith("https://"):
                raise ValueError(
                    f"Selected source must use HTTPS: {source.get('id')}"
                )
            if source.get("verified_at") != SOURCE_VERIFIED_THROUGH:
                raise ValueError(
                    "Selected source verification must be "
                    f"{SOURCE_VERIFIED_THROUGH}: "
                    f"{source.get('id')}"
                )
            if source.get("status") != "current":
                raise ValueError(
                    f"Selected source is not current: {source.get('id')}"
                )
            if not isinstance(source.get("year"), int):
                raise ValueError(
                    f"Selected source year must be numeric: {source.get('id')}"
                )
            if (
                not isinstance(source.get("claims_supported"), list)
                or not source["claims_supported"]
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in source["claims_supported"]
                )
            ):
                raise ValueError(
                    f"Selected source needs claim mappings: {source.get('id')}"
                )
            selected_sources.append(source)

        packets = payload.get("evidence_packets", [])
        expected_slugs = {
            item["slug"]
            for item in data["conditions"]
            if item["category"] == category
        }
        packet_slugs = [item.get("slug") for item in packets]
        if len(packet_slugs) != len(set(packet_slugs)):
            raise ValueError(f"Duplicate evidence packet slug in {path.name}")
        if set(packet_slugs) != expected_slugs:
            raise ValueError(
                f"Selected category must cover every condition in {category}; "
                f"missing={sorted(expected_slugs - set(packet_slugs))!r}, "
                f"extra={sorted(set(packet_slugs) - expected_slugs)!r}"
            )
        for packet in packets:
            if set(packet) != {
                "slug",
                "search_updated",
                "review_state",
                "claims",
            }:
                raise ValueError(
                    f"Evidence packet contract mismatch: {packet.get('slug')}"
                )
            slug = packet["slug"]
            if slug not in condition_by_slug:
                raise ValueError(f"Unknown evidence packet condition: {slug}")
            if condition_by_slug[slug]["category"] != category:
                raise ValueError(f"Evidence packet category mismatch: {slug}")
            if packet["search_updated"] != UPDATED:
                raise ValueError(f"Evidence packet search date is stale: {slug}")
            if packet["review_state"] != "curated-not-externally-reviewed":
                raise ValueError(f"Evidence packet review boundary is unclear: {slug}")
            claims = packet["claims"]
            if [item.get("type") for item in claims] != list(EVIDENCE_CLAIM_TYPES):
                raise ValueError(
                    f"Evidence packet needs the three ordered claim types: {slug}"
                )
            claim_ids = [item.get("id") for item in claims]
            if len(claim_ids) != len(set(claim_ids)):
                raise ValueError(f"Duplicate evidence claim id: {slug}")
            duplicates = evidence_claim_ids.intersection(claim_ids)
            if duplicates:
                raise ValueError(
                    f"Evidence claim ids must be globally unique: {sorted(duplicates)!r}"
                )
            evidence_claim_ids.update(claim_ids)
            for claim in claims:
                if set(claim) != EVIDENCE_CLAIM_FIELDS:
                    raise ValueError(
                        f"Evidence claim contract mismatch: {claim.get('id')}"
                    )
                if not re.fullmatch(
                    r"[a-z0-9]+(?:-[a-z0-9]+)*", str(claim.get("id", ""))
                ):
                    raise ValueError(f"Unsafe evidence claim id: {claim.get('id')!r}")
                if claim["evidence_character"] not in labels:
                    raise ValueError(
                        f"Unknown evidence character in {claim['id']}: "
                        f"{claim['evidence_character']}"
                    )
                for key in (
                    "statement",
                    "what_it_supports",
                    "what_it_does_not_support",
                ):
                    if len(str(claim[key]).strip()) < 70:
                        raise ValueError(
                            f"Evidence claim field is too shallow: "
                            f"{claim['id']}.{key}"
                        )
                if (
                    not isinstance(claim["source_ids"], list)
                    or not claim["source_ids"]
                    or not all(
                        isinstance(item, str) and item.strip()
                        for item in claim["source_ids"]
                    )
                ):
                    raise ValueError(
                        f"Evidence claim must cite selected sources: {claim['id']}"
                    )
                if len(claim["source_ids"]) != len(set(claim["source_ids"])):
                    raise ValueError(
                        f"Evidence claim repeats a source: {claim['id']}"
                    )
            records.append(packet)

    selected_ids = [item["id"] for item in selected_sources]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("Selected evidence source ids must be unique")
    duplicates = base_source_ids.intersection(selected_ids)
    if duplicates:
        raise ValueError(
            f"Selected evidence sources duplicate base ids: {sorted(duplicates)!r}"
        )
    all_source_ids = base_source_ids.union(selected_ids)
    for packet in records:
        for claim in packet["claims"]:
            unknown = set(claim["source_ids"]) - all_source_ids
            if unknown:
                raise ValueError(
                    f"Unknown selected sources in {claim['id']}: {sorted(unknown)!r}"
                )
    cited_source_ids = {
        source_id
        for packet in records
        for claim in packet["claims"]
        for source_id in claim["source_ids"]
    }
    unused_selected_ids = set(selected_ids) - cited_source_ids
    if unused_selected_ids:
        raise ValueError(
            "Selected sources cannot be bibliography padding; uncited ids: "
            f"{sorted(unused_selected_ids)!r}"
        )

    packet_slugs = [item["slug"] for item in records]
    if len(packet_slugs) != len(set(packet_slugs)):
        raise ValueError("Selected evidence packet slugs must be unique")
    return {
        "sources": selected_sources,
        "packets": records,
        "selection_methods": selection_methods,
        "character_labels": character_labels or {},
        "covered_categories": sorted(covered_categories),
    }


def load_direct_reference_map(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    reference_map: dict[str, dict[str, str]] = dict(DIRECT_AUTHORITY_OVERRIDES)
    if OUTSIDE_THE_BOX_DATA_PATH.is_file():
        outside = json.loads(
            OUTSIDE_THE_BOX_DATA_PATH.read_text(encoding="utf-8")
        )
        by_slug = {item["slug"]: item for item in outside.get("conditions", [])}
        for condition in data["conditions"]:
            candidate = OUTSIDE_THE_BOX_ALIASES.get(
                condition["slug"], condition["slug"]
            )
            match = by_slug.get(candidate)
            if match and str(match.get("reference_url", "")).startswith("https://"):
                reference_map[condition["slug"]] = {
                    "publisher": "مرجع الحالة في مكتبة مسارات مقدم الخدمة",
                    "title": match["title_ar"],
                    "url": match["reference_url"],
                }
    expected = {condition["slug"] for condition in data["conditions"]}
    if set(reference_map) != expected:
        missing = sorted(expected - set(reference_map))
        extra = sorted(set(reference_map) - expected)
        raise ValueError(
            "Every condition requires one direct authority reference; "
            f"missing={missing!r}, extra={extra!r}"
        )
    return reference_map


def generated_hypotheses(
    condition: dict[str, Any], profile: dict[str, str]
) -> list[dict[str, str]]:
    title = condition["title_ar"]
    return [
        {
            "name": "قدرة مرشحة خاصة بهذا الملف",
            "claim": profile["ability_focus"],
            "microtrial": profile["task_trial"],
            "support": profile["access_priority"],
            "measure": (
                "جودة التنفيذ ونوع المساعدة والزمن عندما يكون ذا معنى، "
                "والتعب أو الألم أو الحمل قبل المهمة وبعدها، ورغبة الشخص في التكرار."
            ),
            "stop_rule": (
                profile["safety_priority"]
                + " تُوقف التجربة عند الخطر أو الرفض أو تصاعد الأعراض."
            ),
        },
        {
            "name": "القدرة بعد إزالة حاجز واحد",
            "claim": (
                f"قد يكون الأداء المرتبط بـ{title} أقل في النسخة القياسية لأن "
                "طريقة الوصول أو البيئة تضيف عبئًا غير داخل في هدف المهمة."
            ),
            "microtrial": (
                "نفذ نسختين متكافئتين من المهمة، وغيّر عامل وصول واحدًا فقط "
                "مثل القناة أو الوضعية أو الضوضاء أو المدة، ثم كرر المقارنة في يوم آخر."
            ),
            "support": profile["access_priority"],
            "measure": (
                "حجم التحسن في الجودة أو الاستقلال مقابل التغير في الطاقة "
                "والألم والضيق وعدد التلميحات."
            ),
            "stop_rule": (
                "لا يعتمد التكييف إذا لم يقدم فائدة قابلة للتكرار، أو زاد الخطر "
                "أو المساعدة أو الوصم أو كلفة ما بعد المهمة."
            ),
        },
        {
            "name": "قابلية التعلم لا الانطباع الأول",
            "claim": (
                "قد تكشف سرعة التعلم أو انخفاض التلميحات قدرةً لا تظهر في "
                "محاولة أولى، بشرط استقرار الصحة وملاءمة التعليم."
            ),
            "microtrial": (
                "درّب المهمة القصيرة نفسها في ثلاث جلسات متباعدة بتغذية راجعة "
                "ثابتة، ثم اختبرها بلا تدريب وبعد فاصل زمني."
            ),
            "support": (
                "نموذج واضح، ممارسة في السياق، خط أساس، وفاصل راحة يحدده "
                "الشخص أو الفريق وفق حالته."
            ),
            "measure": (
                "منحنى الدقة والاستقلال، عدد المحاولات والتلميحات، الاستبقاء، "
                "والقدرة على اكتشاف الخطأ وتصحيحه."
            ),
            "stop_rule": (
                "تتوقف الدورة إذا لم يظهر تعلم ذو معنى بعد تكييف مناسب، "
                "أو إذا أدى التكرار إلى ألم أو تدهور أو فقدان الرغبة."
            ),
        },
        {
            "name": "اهتمام يختاره الشخص وقيمة وظيفية",
            "claim": (
                "قد يزيد الاختيار والمعنى المبادرة والاستمرار، لكن الاهتمام "
                "لا يتحول تلقائيًا إلى مهنة ولا يبرر تجاوز الصحة."
            ),
            "microtrial": (
                "اطلب من الشخص اختيار نشاطين آمنين، ونفذ عينة صغيرة من كل "
                "منهما مع نفس الوقت والدعم، ثم ناقش النتيجة بوسيلة تواصل متاحة."
            ),
            "support": (
                "خيار حقيقي للرفض، تعريف واضح للنهاية، تكييف الوصول، "
                "وتغذية راجعة لا تجعل الإنتاج شرط القبول."
            ),
            "measure": (
                "المبادرة والجودة والاستقلال والرضا والرغبة في التكرار "
                "والأثر في المشاركة أو الحياة اليومية."
            ),
            "stop_rule": (
                "يُرفض المسار إذا لم يختره الشخص، أو إذا حول الاهتمام إلى ضغط "
                "أو استغلال أو منع للنوم والعلاج والعلاقات."
            ),
        },
    ]


def generated_guide(
    data: dict[str, Any],
    condition: dict[str, Any],
    profile: dict[str, str],
) -> dict[str, Any]:
    route = data["evidence_routes"][condition["evidence_route"]]
    category_adaptations = CATEGORY_ADAPTATIONS[condition["category"]]
    return {
        "slug": condition["slug"],
        "title": f"بروتوكول اكتشاف وتنمية القدرات: {condition['title_ar']}",
        "evidence_label": profile["position"],
        "evidence_summary": [
            profile["position"],
            route["meaning"],
            (
                "يُبنى القرار على أداء الشخص في مهام متكررة ومكيّفة وعلى "
                "موافقته وعبء النشاط؛ لا على التشخيص أو قصة نجاح أو افتراض مهني."
            ),
        ],
        "do_not_assume": [
            "أن اسم الحالة يحدد الذكاء أو الشخصية أو المهنة أو القدرة على القرار.",
            "أن طريقة الكلام أو النظر أو الحركة أو السرعة تكشف وحدها مقدار الفهم.",
            "أن الألم أو الأزمة أو النوبة أو فرط النشاط أو الحرمان من النوم مصدر قدرة.",
            "أن قصة نجاح لشخص آخر تثبت الصفة أو التدخل أو المسار لهذا الشخص.",
            "أن أداة الوصول تجعل الإنجاز أقل قيمة أو أن الاستقلال يعني غياب كل دعم.",
        ],
        "health_first": [
            profile["safety_priority"],
            (
                "ثبّت طريقة طلب المساعدة والرفض والتوقف، وخطة الطوارئ ذات الصلة، "
                "قبل تجربة أي مهمة جديدة."
            ),
            (
                "أي فقد مهارة أو تغير وعي أو أعراض جديدة أو تدهور سريع يُعاد "
                "إلى المسار الصحي المناسب قبل تفسيره بوصفه ضعف قدرة."
            ),
        ],
        "hypotheses": generated_hypotheses(condition, profile),
        "adaptations": [
            profile["access_priority"],
            *category_adaptations,
        ],
        "twelve_week_plan": [
            (
                "الأسبوعان 1–2: مراجعة الصحة والتواصل والموافقة وخط الأساس، "
                f"وصياغة الهدف الوظيفي: {profile['functional_goal']}"
            ),
            (
                "الأسابيع 3–4: تنفيذ التجربة المصغرة الخاصة بالحالة في يومين "
                f"مستقرين: {profile['task_trial']}"
            ),
            (
                "الأسابيع 5–7: تعديل عامل وصول واحد، وتكرار المهمة ثلاث مرات "
                "مع قياس الجودة والمساعدة والعبء والاستبقاء."
            ),
            (
                "الأسابيع 8–10: تدريب المهمة الكاملة في سياقها، وخفض التلميحات "
                "غير الضرورية، ثم نقلها إلى شريك أو مكان أو مثال جديد."
            ),
            (
                "الأسبوعان 11–12: مراجعة البيانات ورأي الشخص وقواعد التوقف، "
                "واتخاذ قرار مشترك بالاستمرار أو التعديل أو الإنهاء."
            ),
        ],
        "source_ids": [
            "who-icf-2001",
            "who-rehabilitation-2024",
            "un-crpd-article-26",
            "nice-shared-decision-ng197",
        ],
        "generated_from_profile": True,
    }


def complete_guides(
    data: dict[str, Any],
    profiles: dict[str, dict[str, str]],
    direct_references: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    bespoke = {item["slug"]: item for item in data["guides"]}
    evidence_packets = {
        item["slug"]: item for item in data.get("evidence_packets", [])
    }
    guides: list[dict[str, Any]] = []
    for condition in data["conditions"]:
        profile = profiles[condition["slug"]]
        guide = dict(
            bespoke.get(condition["slug"])
            or generated_guide(data, condition, profile)
        )
        guide["profile"] = profile
        guide["generated_from_profile"] = condition["slug"] not in bespoke
        guide["evidence_packet"] = evidence_packets.get(condition["slug"])
        references = []
        if condition["slug"] in direct_references:
            references.append(direct_references[condition["slug"]])
        references.append(CATEGORY_AUTHORITIES[condition["category"]])
        guide["research_links"] = references
        guides.append(guide)
    return guides


def load_and_validate() -> dict[str, Any]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise ValueError("Capabilities source must declare Arabic version 280")
    if data.get("updated_at") != UPDATED:
        raise ValueError(f"Capabilities source updated_at must be {UPDATED}")
    if data.get("external_review_completed") is not False:
        raise ValueError("External review must remain false until independently documented")
    if "المراجعة السريرية" not in data.get("review_status", ""):
        raise ValueError("Review status must disclose the external clinical review boundary")

    conditions = data.get("conditions", [])
    if len(conditions) != 100:
        raise ValueError(f"Exactly 100 conditions are required, found {len(conditions)}")
    if [item.get("rank") for item in conditions] != list(range(1, 101)):
        raise ValueError("Condition ranks must be contiguous from 1 through 100")
    slugs = [item.get("slug", "") for item in conditions]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Condition slugs must be unique")
    for slug in slugs:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Unsafe condition slug: {slug}")

    categories = data.get("categories", {})
    routes = data.get("evidence_routes", {})
    required_condition_keys = {
        "rank",
        "slug",
        "title_ar",
        "title_en",
        "category",
        "evidence_route",
        "first_wave_guide",
    }
    for condition in conditions:
        missing = required_condition_keys - set(condition)
        if missing:
            raise ValueError(
                f"Condition {condition.get('rank')} missing: {sorted(missing)}"
            )
        if condition["category"] not in categories:
            raise ValueError(f"Unknown category: {condition['category']}")
        if condition["evidence_route"] not in routes:
            raise ValueError(f"Unknown evidence route: {condition['evidence_route']}")

    base_sources = data.get("sources", [])
    if len(base_sources) < 20:
        raise ValueError("At least 20 verified institutional or research sources are required")
    source_ids = [item.get("id") for item in base_sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Source ids must be unique")
    for source in base_sources:
        if set(source) != SOURCE_FIELDS:
            raise ValueError(f"Base source contract mismatch: {source.get('id')!r}")
        if not str(source.get("url", "")).startswith("https://"):
            raise ValueError(f"Source must use HTTPS: {source.get('id')}")
        if source.get("status") != "current":
            raise ValueError(f"Only current sources may support v280: {source.get('id')}")

    selected_evidence = load_evidence_packets(data)
    data["sources"] = [*base_sources, *selected_evidence["sources"]]
    data["evidence_packets"] = selected_evidence["packets"]
    data["evidence_selection_methods"] = selected_evidence["selection_methods"]
    data["evidence_character_labels"] = selected_evidence["character_labels"]
    data["evidence_covered_categories"] = selected_evidence["covered_categories"]
    data["selected_evidence_source_count"] = len(selected_evidence["sources"])
    source_ids = [item["id"] for item in data["sources"]]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Combined base and selected source ids must be unique")

    guides = data.get("guides", [])
    if len(guides) != 5:
        raise ValueError(f"Exactly five complete first-wave guides are required, found {len(guides)}")
    guide_slugs = [item.get("slug") for item in guides]
    flagged = [
        item["slug"] for item in conditions if item.get("first_wave_guide") is True
    ]
    if guide_slugs != flagged:
        raise ValueError("Guide order must match the five first-wave registry entries")
    condition_slugs = set(slugs)
    required_guide_keys = {
        "slug",
        "title",
        "evidence_label",
        "evidence_summary",
        "do_not_assume",
        "health_first",
        "hypotheses",
        "adaptations",
        "twelve_week_plan",
        "source_ids",
    }
    for guide in guides:
        missing = required_guide_keys - set(guide)
        if missing:
            raise ValueError(f"Guide {guide.get('slug')} missing: {sorted(missing)}")
        if guide["slug"] not in condition_slugs:
            raise ValueError(f"Guide has no registry entry: {guide['slug']}")
        if len(guide["hypotheses"]) < 4:
            raise ValueError(f"Guide needs four testable hypotheses: {guide['slug']}")
        for hypothesis in guide["hypotheses"]:
            expected = {"name", "claim", "microtrial", "support", "measure", "stop_rule"}
            if set(hypothesis) != expected:
                raise ValueError(
                    f"Guide hypothesis contract is incomplete: {guide['slug']}"
                )
        unknown = set(guide["source_ids"]) - set(source_ids)
        if unknown:
            raise ValueError(f"Unknown guide sources in {guide['slug']}: {sorted(unknown)}")

    protocol = data.get("protocol", {})
    if len(protocol.get("stages", [])) != 9:
        raise ValueError("The universal protocol must have exactly nine stages")
    if [item.get("number") for item in protocol["stages"]] != list(range(1, 10)):
        raise ValueError("Protocol stages must be ordered from 1 through 9")
    if len(protocol.get("minimum_measures", [])) < 7:
        raise ValueError("The protocol needs a multidimensional minimum measurement set")
    if len(protocol.get("stop_rules", [])) < 5:
        raise ValueError("The protocol needs explicit stop rules")
    return data


def breadcrumbs(items: list[tuple[str, str | None]]) -> tuple[str, dict[str, Any]]:
    html_parts: list[str] = []
    schema_items: list[dict[str, Any]] = []
    for position, (label, path) in enumerate(items, start=1):
        if path:
            html_parts.append(f'<a href="{e(path)}">{e(label)}</a>')
        else:
            html_parts.append(f'<span aria-current="page">{e(label)}</span>')
        schema_items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": label,
            **({"item": BASE_ORIGIN + path} if path else {}),
            }
        )
    return (
        '<nav class="cap-breadcrumb" aria-label="مسار الصفحة">'
        + '<span aria-hidden="true">←</span>'.join(html_parts)
        + "</nav>",
        {"@type": "BreadcrumbList", "itemListElement": schema_items},
    )


def page_shell(
    *,
    title: str,
    description: str,
    canonical_path: str,
    main: str,
    schema_nodes: list[dict[str, Any]],
    current: str = "",
) -> str:
    canonical = BASE + canonical_path.lstrip("/")
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": BASE + "#organization",
                "name": BRAND,
                "url": BASE,
            },
            {
                "@type": "WebSite",
                "@id": BASE + "#website",
                "name": BRAND,
                "url": BASE,
                "inLanguage": "ar",
                "publisher": {"@id": BASE + "#organization"},
            },
            *schema_nodes,
        ],
    }
    nav_items = [
        ("الرئيسية", BASE_PATH),
        ("مركز ذوي الاحتياجات الخاصة", BASE_PATH + "special-needs/"),
        ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
        ("سجل الحالات المئة", BASE_PATH + SECTION + "/registry/"),
        ("البروتوكول العملي", BASE_PATH + SECTION + "/protocol/"),
        ("المنهجية", BASE_PATH + SECTION + "/methodology/"),
        ("الثقة", BASE_PATH + "trust/"),
    ]
    nav = "".join(
        f'<a{" aria-current=\"page\"" if label == current else ""} '
        f'href="{e(url)}">{e(label)}</a>'
        for label, url in nav_items
    )
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{e(title)} | {e(BRAND)}</title>
<meta name="description" content="{e(description)}">
<meta name="keywords" content="ذوو الاحتياجات الخاصة، نقاط القوة الفردية، التأهيل، المشاركة، ICF، تكييف البيئة، قرار مشترك">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{e(canonical)}">
<link rel="alternate" hreflang="ar" href="{e(canonical)}">
<link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg">
<link rel="stylesheet" href="{BASE_PATH}assets/css/capabilities-v280.css">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{BASE}assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{BASE}assets/brand/social-card.svg">
<script type="application/ld+json">{compact_json(schema)}</script>
<script defer src="{BASE_PATH}assets/js/capabilities-v280.js"></script>
</head>
<body class="cap-page">
<a class="cap-skip" href="#main">تجاوز إلى المحتوى الرئيسي</a>
<header class="cap-header"><div class="cap-wrap cap-header-inner">
<a class="cap-brand" href="{BASE_PATH}"><img src="{BASE_PATH}assets/brand/logo-mark.svg" alt=""><span>{e(BRAND)}<small>{e(SLOGAN)}</small></span></a>
<nav class="cap-nav" aria-label="التنقل الرئيسي">{nav}</nav>
</div></header>
<main id="main">{main}</main>
<footer class="cap-footer"><div class="cap-wrap">
<p><strong>{e(BRAND)}</strong> — {e(SLOGAN)}</p>
<p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}special-needs/">المركز الدامج</a> · <a href="{BASE_PATH}outside-the-box/">أفكار خارج الصندوق</a></p>
<p>محتوى تثقيفي وتخطيطي، لا يشخّص ولا يصف علاجًا فرديًا ولا يستبدل الرعاية المهنية أو خطة الطوارئ.</p>
</div></footer>
</body>
</html>
"""


def review_banner(data: dict[str, Any]) -> str:
    return (
        '<aside class="cap-review" aria-label="حالة المراجعة">'
        "<strong>حالة المراجعة:</strong> "
        + e(data["review_status"])
        + ". <span>لا توجد مصادقة أو مراجعة خارجية مستقلة مسجلة لهذا الإصدار.</span>"
        "</aside>"
    )


def render_hub(data: dict[str, Any], guides: list[dict[str, Any]]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [("الرئيسية", BASE_PATH), ("لنرتقي بقدراتهم", None)]
    )
    category_counts = Counter(item["category"] for item in data["conditions"])
    route_counts = Counter(item["evidence_route"] for item in data["conditions"])
    packet_count = len(data["evidence_packets"])
    evidence_claim_count = sum(
        len(item["claims"]) for item in data["evidence_packets"]
    )
    remaining_evidence_count = len(data["conditions"]) - packet_count
    covered_categories = "، ".join(
        data["categories"][key] for key in data["evidence_covered_categories"]
    )
    if remaining_evidence_count:
        coverage_summary = (
            f"واكتمل الانتقاء البحثي الخاص بالحالة في {packet_count} حالة ضمن "
            f"{e(covered_categories)}؛ ولا نساوي ذلك باكتمال الانتقاء للحالات "
            f"الـ{remaining_evidence_count} المتبقية."
        )
    else:
        coverage_summary = (
            "واكتمل الانتقاء البحثي الداخلي الخاص بالحالة للحالات المئة كلها "
            f"عبر الفئات الست: {e(covered_categories)}."
        )
    highlighted_slugs = {
        item["slug"] for item in data["conditions"] if item["first_wave_guide"]
    }
    guide_by_slug = {
        item["slug"]: item for item in guides if item["slug"] in highlighted_slugs
    }
    guide_cards = []
    condition_by_slug = {item["slug"]: item for item in data["conditions"]}
    for slug, guide in guide_by_slug.items():
        condition = condition_by_slug[slug]
        route = data["evidence_routes"][condition["evidence_route"]]["label"]
        guide_cards.append(
            f"""<article class="cap-card cap-guide-card">
<span class="cap-kicker">{e(route)}</span>
<h3>{e(guide["title"])}</h3>
<p>{e(guide["evidence_label"])}</p>
<a class="cap-text-link" href="{e(slug)}/">اقرأ الخريطة العملية <span aria-hidden="true">←</span></a>
</article>"""
        )
    category_cards = "".join(
        f'<article class="cap-stat"><strong>{category_counts[key]}</strong>'
        f"<span>{e(label)}</span></article>"
        for key, label in data["categories"].items()
    )
    route_cards = "".join(
        f'<article class="cap-route"><h3>{e(route["label"])}</h3>'
        f"<p>{e(route['meaning'])}</p><strong>{route_counts[key]} حالة</strong></article>"
        for key, route in data["evidence_routes"].items()
    )
    main = f"""
<section class="cap-hero"><div class="cap-wrap">
{crumbs}
<p class="cap-eyebrow">مشروع بحثي تطبيقي يحترم الاختلاف ولا يجمّل المعاناة</p>
<h1>{e(data["title"])}</h1>
<p class="cap-lead">{e(data["subtitle"])}</p>
<blockquote>{e(data["core_statement"])}</blockquote>
<div class="cap-actions">
<a class="cap-button" href="registry/">استعرض الحالات المئة</a>
<a class="cap-button cap-button-secondary" href="protocol/">استخدم بروتوكول الاكتشاف</a>
</div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="start-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">الإصدار الأول</p><h2 id="start-title">ماذا نُشر فعلًا؟</h2></div>
<p>لكل حالة من الحالات المئة صفحة بروتوكول كاملة بالموقف العلمي وفحص الأمان وتجارب المهام والتكييف والقياس وخطة 12 أسبوعًا. {coverage_summary}</p></div>
<div class="cap-stats cap-stats-six">
<article class="cap-stat"><strong>100</strong><span>حالة في سجل بحثي منظم</span></article>
<article class="cap-stat"><strong>100</strong><span>بروتوكول حالة كامل ومترابط</span></article>
<article class="cap-stat"><strong>{packet_count}</strong><span>حزمة أدلة منتقاة خاصة بالحالة</span></article>
<article class="cap-stat"><strong>{evidence_claim_count}</strong><span>ادعاءً محدودًا مع ما يدعمه وما لا يدعمه</span></article>
<article class="cap-stat"><strong>{len(data["sources"])}</strong><span>مصدرًا بعقد توثيق على مستوى الادعاء</span></article>
<article class="cap-stat"><strong>9</strong><span>مراحل في البروتوكول المشترك</span></article>
</div>
<p class="cap-evidence-status"><strong>حد التغطية الحالي:</strong> {packet_count} حزمة مكتملة الانتقاء الداخلي و{remaining_evidence_count} صفحة بروتوكول لم يكتمل لها الانتقاء الخاص المكافئ. المراجعة الخارجية المستقلة لم تكتمل لأي حزمة.</p>
<div class="cap-section-heading cap-subheading"><div><p class="cap-eyebrow">خمسة نماذج افتتاحية</p><h2>أمثلة على الخرائط العملية</h2></div>
<p>هذه البطاقات أمثلة للتصفح، وليست الحالات الوحيدة ذات بروتوكول كامل. يوضح سجل الحالات حالة الانتقاء البحثي لكل صفحة.</p></div>
<div class="cap-grid cap-grid-guides">{''.join(guide_cards)}</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="routes-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">حدود الادعاء</p><h2 id="routes-title">ستة مسارات للدليل، لا عبارة واحدة عن «الموهبة»</h2></div>
<p>كل حالة تسلك طريقًا مختلفًا: أحيانًا يوجد دليل ناشئ على نمط قوة سياقي، وأحيانًا لا يوجد إلا واجب كشف القدرة الفردية أو إزالة الحاجز، وأحيانًا تكون الأولوية للاستقرار.</p></div>
<div class="cap-grid cap-grid-routes">{route_cards}</div>
<p><a class="cap-text-link" href="methodology/">اقرأ كيف نمنع التعميم والمبالغة <span aria-hidden="true">←</span></a></p>
</section>
<section class="cap-section" aria-labelledby="coverage-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">تغطية متوازنة</p><h2 id="coverage-title">توزيع الحالات المئة</h2></div>
<p>{e(data["selection_method"]["not_a_ranking"])}</p></div>
<div class="cap-stats cap-stats-six">{category_cards}</div>
</section>
<section class="cap-section cap-callout" aria-labelledby="promise-title">
<div><p class="cap-eyebrow">الوعد الأخلاقي</p><h2 id="promise-title">لا نبحث عن قيمة الشخص في تشخيصه</h2>
<p>{e(data["scope_note"])}</p></div>
<a class="cap-button cap-button-secondary" href="methodology/">الميثاق العلمي والتحريري</a>
</section>
</div>
"""
    return page_shell(
        title=data["title"],
        description=data["subtitle"],
        canonical_path=SECTION + "/",
        main=main,
        current="لنرتقي بقدراتهم",
        schema_nodes=[
            {
                "@type": "CollectionPage",
                "@id": BASE + SECTION + "/#page",
                "url": BASE + SECTION + "/",
                "name": data["title"],
                "description": data["subtitle"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "isPartOf": {"@id": BASE + "#website"},
            },
            crumb_schema,
        ],
    )


def render_methodology(data: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("المنهجية", None),
        ]
    )
    source_by_id = source_map(data)
    foundation_ids = [
        "who-icf-2001",
        "who-rehabilitation-2024",
        "un-crpd-article-26",
        "un-crpd-article-27",
        "nice-shared-decision-ng197",
        "kang-person-centered-goals-2022",
    ]
    sources = "".join(
        f'<li><a href="{e(source_by_id[key]["url"])}" rel="noopener">'
        f'{e(source_by_id[key]["publisher"])} — {e(source_by_id[key]["title"])}</a> '
        f'({e(source_by_id[key]["year"])})</li>'
        for key in foundation_ids
    )
    routes = "".join(
        f'<article class="cap-route" id="{e(key)}"><h3>{e(item["label"])}</h3>'
        f"<p>{e(item['meaning'])}</p></article>"
        for key, item in data["evidence_routes"].items()
    )
    selected_method_sections = "".join(
        f"""<article class="cap-method-wave">
<p class="cap-eyebrow">موجة انتقاء مكتملة للفئة</p>
<h3>{e(data["categories"][category])}</h3>
<p>{e(method["scope"])}</p>
<div class="cap-grid cap-grid-two">
<div><h4>ترتيب اختيار المصادر</h4>
{ul(method["selection_order"], "cap-check-list")}</div>
<div><h4>ما استُبعد من الاستدلال</h4>
{ul(method["exclusions"], "cap-cross-list")}</div>
</div>
<dl class="cap-method-boundaries">
<div><dt>سياسة اليقين</dt><dd>{e(method["certainty_policy"])}</dd></div>
<div><dt>حد البحث الحي</dt><dd>{e(method["live_search_boundary"])}</dd></div>
<div><dt>حد المراجعة</dt><dd>{e(method["review_boundary"])}</dd></div>
</dl>
</article>"""
        for category, method in data["evidence_selection_methods"].items()
    )
    character_cards = "".join(
        f"""<article class="cap-card">
<h3>{e(EVIDENCE_CHARACTER_TITLES[key])}</h3>
<p>{e(label)}</p>
</article>"""
        for key, label in data["evidence_character_labels"].items()
    )
    packet_count = len(data["evidence_packets"])
    claim_count = sum(len(item["claims"]) for item in data["evidence_packets"])
    remaining_count = len(data["conditions"]) - packet_count
    if remaining_count:
        selected_coverage = (
            f"اكتملت هذه الطبقة لـ{packet_count} حالة، بثلاثة ادعاءات محدودة "
            f"لكل حالة، أي {claim_count} ادعاءً. ما زالت {remaining_count} حالة "
            "خارج الانتقاء البحثي المكافئ."
        )
    else:
        selected_coverage = (
            "اكتملت هذه الطبقة للحالات المئة كلها عبر الفئات الست: ثلاثة "
            f"ادعاءات محدودة لكل حالة، أي {claim_count} ادعاءً، مع بقاء "
            "المراجعة الخارجية المستقلة غير مكتملة."
        )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">ميثاق الدليل واللغة</p>
<h1>كيف نبحث عن القدرة من دون صناعة أسطورة عن المرض؟</h1>
<p class="cap-lead">نبدأ من الشخص وأهدافه وأدائه، ونضع لكل ادعاء سقفًا يساوي قوة الدليل. قصة نجاح تلهم سؤالًا؛ لا تثبت قاعدة.</p>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="selection-title">
<h2 id="selection-title">{e(data["selection_method"]["title"])}</h2>
{ul(data["selection_method"]["criteria"], "cap-check-list")}
<p class="cap-note"><strong>تنبيه:</strong> {e(data["selection_method"]["not_a_ranking"])}</p>
</section>
<section class="cap-section cap-soft" aria-labelledby="route-title">
<h2 id="route-title">مسارات الدليل الستة</h2>
<p>يظهر المسار في سجل الحالات وفي رأس كل دليل مفصل، كي لا تُقرأ فرضية فردية كأنها حقيقة جماعية.</p>
<div class="cap-grid cap-grid-routes">{routes}</div>
</section>
<section class="cap-section" aria-labelledby="rules-title">
<h2 id="rules-title">قواعد التحرير واتخاذ القرار</h2>
<div class="cap-grid cap-grid-three">
<article class="cap-card"><h3>ما الذي نقبله؟</h3>{ul([
        "نتائج مراجعات منهجية وإرشادات رسمية وبحوث محكّمة مع بيان حدودها.",
        "خبرة الشخص المعاشة بوصفها دليلًا على تفضيله وتجربته، لا على جميع أفراد التشخيص.",
        "تجارب مهام صغيرة قابلة للتكرار والقياس والتوقف.",
        "تقنية مساندة أو تعديل بيئي يكشف القدرة من دون إلغاء حق الشخص."
    ])}</article>
<article class="cap-card"><h3>ما الذي نرفضه؟</h3>{ul([
        "القول إن كل حالة هبة أو إن كل شخص يملك موهبة مرتبطة بتشخيصه.",
        "تحويل الألم أو الذهان أو الهوس أو النوبات أو الحرمان من النوم إلى ميزة.",
        "اختيار مهنة من اسم الحالة أو قصة شخص ناجح.",
        "إخفاء الضرر أو العلاج المطلوب كي تبدو الرسالة إيجابية."
    ])}</article>
<article class="cap-card"><h3>ما الذي يجب توثيقه؟</h3>{ul([
        "صوت الشخص وموافقته وطريقة التواصل وإشارات التوقف.",
        "المهمة والسياق والتكييف وخط الأساس ومدة التجربة.",
        "الجودة والاستقلال والتعب والألم والرغبة والتعميم.",
        "ما لم ينجح وما تغيّر ولماذا اتُخذ قرار الاستمرار أو التوقف."
    ])}</article>
</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="translation-title">
<h2 id="translation-title">من الدراسة إلى توصية عملية</h2>
<ol class="cap-process">
<li><strong>سؤال محدد:</strong> ما القدرة أو الحاجز الذي نريد فهمه؟</li>
<li><strong>أفضل دليل متاح:</strong> إرشاد أو مراجعة، ثم دراسة فردية عند الحاجة.</li>
<li><strong>فحص الانطباق:</strong> العمر، اللغة، شدة الاحتياج، السياق، وقيود الدراسة.</li>
<li><strong>فرضية فردية:</strong> صياغة يمكن أن تثبت أو تُرفض.</li>
<li><strong>تجربة آمنة:</strong> مهمة حقيقية وتكييف واحد أو أكثر وقياس متعدد الأبعاد.</li>
<li><strong>قرار مشترك:</strong> استمرار أو تعديل أو توقف وفق البيانات ورأي الشخص.</li>
</ol>
</section>
<section class="cap-section" aria-labelledby="selected-method-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">انتقاء على مستوى الادعاء</p>
<h2 id="selected-method-title">كيف بُنيت حزم الأدلة الخاصة بالحالات؟</h2></div>
<p>{selected_coverage}</p></div>
{selected_method_sections}
</section>
<section class="cap-section cap-soft" aria-labelledby="character-title">
<h2 id="character-title">وصف طبيعة الدليل بدل اختراع درجة يقين</h2>
<p>هذه الأوصاف تبين نوع المصدر ومباشرته وحدوده. لا تعيد المنصة إجراء GRADE ولا تنسب لنفسها درجة توصية لم تمنحها الجهة المؤلفة.</p>
<div class="cap-grid cap-grid-three">{character_cards}</div>
</section>
<section class="cap-section" aria-labelledby="foundation-title">
<h2 id="foundation-title">الأساس المرجعي للمنهج</h2>
<p>يعتمد الإطار على الأداء والمشاركة والبيئة، وعلى التأهيل المتمحور حول الشخص والقرار المشترك والحقوق. التفاصيل الخاصة بكل حالة تظهر في مصادر دليلها.</p>
<ol class="cap-sources">{sources}</ol>
</section>
</div>
"""
    return page_shell(
        title="المنهجية العلمية لمشروع لنرتقي بقدراتهم",
        description="ميثاق يمنع تعميم نقاط القوة، ويفصل بين الدليل والخبرة والفرضية الفردية، ويوثق حدود المراجعة.",
        canonical_path=SECTION + "/methodology/",
        main=main,
        current="المنهجية",
        schema_nodes=[
            {
                "@type": "WebPage",
                "@id": BASE + SECTION + "/methodology/#page",
                "url": BASE + SECTION + "/methodology/",
                "name": "المنهجية العلمية لمشروع لنرتقي بقدراتهم",
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "isPartOf": {"@id": BASE + "#website"},
            },
            crumb_schema,
        ],
    )


def render_protocol(data: dict[str, Any]) -> str:
    protocol = data["protocol"]
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("البروتوكول العملي", None),
        ]
    )
    stages = "".join(
        f"""<article class="cap-stage">
<span class="cap-stage-number" aria-hidden="true">{stage["number"]}</span>
<div><h3>المرحلة {stage["number"]}: {e(stage["title"])}</h3>
{ul(stage["actions"])}
<p class="cap-output"><strong>المخرج:</strong> {e(stage["output"])}</p></div>
</article>"""
        for stage in protocol["stages"]
    )
    worksheet_rows = "".join(
        f"<tr><th scope=\"row\">{number}. {e(stage['title'])}</th>"
        "<td></td><td></td><td></td></tr>"
        for number, stage in enumerate(protocol["stages"], start=1)
    )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">أداة تخطيط غير تشخيصية</p>
<h1>{e(protocol["title"])}</h1>
<p class="cap-lead">مسار من الأمان وصوت الشخص إلى تجربة صغيرة وقرار قابل للمراجعة. لا يقيس «قيمة» الإنسان ولا يتنبأ بمهنته.</p>
<div class="cap-actions"><button class="cap-button cap-print-button" type="button" data-cap-print>طباعة البروتوكول</button>
<a class="cap-button cap-button-secondary" href="../registry/">اختيار حالة من السجل</a></div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="principles-title">
<h2 id="principles-title">مبادئ لا يجوز تجاوزها</h2>
{ul(protocol["principles"], "cap-check-list")}
</section>
<section class="cap-section cap-soft" aria-labelledby="stages-title">
<h2 id="stages-title">المراحل التسع</h2>
<div class="cap-stages">{stages}</div>
</section>
<section class="cap-section" aria-labelledby="measure-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="measure-title">الحد الأدنى للقياس</h2>{ul(protocol["minimum_measures"], "cap-measure-list")}</article>
<article class="cap-danger"><h2>قواعد التوقف</h2>{ul(protocol["stop_rules"])}</article>
</div>
</section>
<section class="cap-section cap-worksheet" aria-labelledby="worksheet-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">ورقة عمل قابلة للطباعة</p><h2 id="worksheet-title">سجل قرار واحد</h2></div>
<p>استخدم سطرًا واحدًا موجزًا لكل مرحلة. لا تسجل بيانات تعريفية أو صحية أكثر مما يلزم، واحفظ الورقة وفق سياسة الخصوصية في مؤسستك.</p></div>
<div class="cap-form-grid">
<label>اسم الهدف لا اسم التشخيص<input aria-label="اسم الهدف" type="text"></label>
<label>تاريخ البداية<input aria-label="تاريخ البداية" type="text"></label>
<label>طريقة موافقة الشخص أو رفضه<input aria-label="طريقة الموافقة أو الرفض" type="text"></label>
<label>موعد المراجعة<input aria-label="موعد المراجعة" type="text"></label>
</div>
<div class="cap-table-wrap"><table><thead><tr><th>المرحلة</th><th>ما عرفناه</th><th>ما سنجرّبه أو نعدّله</th><th>الدليل والقرار</th></tr></thead>
<tbody>{worksheet_rows}</tbody></table></div>
<div class="cap-grid cap-grid-two cap-signoff">
<label>رأي الشخص في الاستمرار أو التعديل أو التوقف<textarea aria-label="رأي الشخص"></textarea></label>
<label>قواعد التوقف الخاصة بهذه التجربة<textarea aria-label="قواعد التوقف الخاصة"></textarea></label>
</div>
</section>
</div>
"""
    return page_shell(
        title="بروتوكول اكتشاف وتنمية القدرة",
        description="بروتوكول عملي من تسع مراحل لاختبار القدرات الفردية بأمان وقياس الاستقلال والرضا والتعب والتعميم.",
        canonical_path=SECTION + "/protocol/",
        main=main,
        current="البروتوكول العملي",
        schema_nodes=[
            {
                "@type": "HowTo",
                "@id": BASE + SECTION + "/protocol/#howto",
                "url": BASE + SECTION + "/protocol/",
                "name": protocol["title"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "step": [
                    {
                        "@type": "HowToStep",
                        "position": stage["number"],
                        "name": stage["title"],
                        "text": " ".join(stage["actions"]),
                    }
                    for stage in protocol["stages"]
                ],
            },
            crumb_schema,
        ],
    )


def render_registry(
    data: dict[str, Any], guides: list[dict[str, Any]]
) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("سجل الحالات المئة", None),
        ]
    )
    guide_slugs = {item["slug"] for item in guides}
    evidence_slugs = {item["slug"] for item in data["evidence_packets"]}
    evidence_count = len(evidence_slugs)
    remaining_count = len(data["conditions"]) - evidence_count
    if remaining_count:
        coverage_status = (
            f"100 بروتوكول كامل؛ {evidence_count} حزمة أدلة منتقاة خاصة بالحالة، "
            f"و{remaining_count} بروتوكولًا لم يكتمل له بعد الانتقاء البحثي المكافئ."
        )
    else:
        coverage_status = (
            "100 بروتوكول كامل و100 حزمة أدلة منتقاة خاصة بالحالة؛ تغطي الطبقة "
            "البحثية الداخلية السجل كله، مع بقاء المراجعة الخارجية المستقلة مطلوبة."
        )
    cards: list[str] = []
    for condition in data["conditions"]:
        route = data["evidence_routes"][condition["evidence_route"]]
        category = data["categories"][condition["category"]]
        evidence_state = (
            "selected" if condition["slug"] in evidence_slugs else "not-selected"
        )
        evidence_status = (
            "حزمة أدلة منتقاة"
            if evidence_state == "selected"
            else "البروتوكول منشور؛ الانتقاء البحثي لم يكتمل"
        )
        link = (
            f'<a class="cap-text-link" href="../{e(condition["slug"])}/">'
            'البروتوكول الكامل <span aria-hidden="true">←</span></a>'
            if condition["slug"] in guide_slugs
            else '<span class="cap-registry-only">مدرج في سجل البحث والمنهج</span>'
        )
        cards.append(
            f"""<article class="cap-condition" data-cap-condition
 data-slug="{e(condition["slug"])}"
 data-category="{e(condition["category"])}"
 data-route="{e(condition["evidence_route"])}"
 data-evidence="{e(evidence_state)}"
 data-search="{e(condition["title_ar"])} {e(condition["title_en"])}">
<div class="cap-condition-top"><span class="cap-rank">{condition["rank"]:02d}</span>
<span class="cap-route-badge">{e(route["label"])}</span></div>
<h2>{e(condition["title_ar"])}</h2>
<p lang="en" dir="ltr">{e(condition["title_en"])}</p>
<small>{e(category)}</small>
<span class="cap-evidence-badge cap-evidence-badge-{e(evidence_state)}">{e(evidence_status)}</span>
{link}
</article>"""
        )
    category_options = "".join(
        f'<option value="{e(key)}">{e(label)}</option>'
        for key, label in data["categories"].items()
    )
    route_options = "".join(
        f'<option value="{e(key)}">{e(item["label"])}</option>'
        for key, item in data["evidence_routes"].items()
    )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">نطاق بحث منظم لا ترتيب للقيمة</p>
<h1>سجل الحالات المئة</h1>
<p class="cap-lead">اختيرت الحالات لأنها قد تُخفي قدرة بسبب حاجز في التعلم أو التواصل أو الحركة أو الصحة أو المشاركة. وجود الحالة في السجل لا يعني أن لها فائدة أو نمط موهبة ثابتًا.</p>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="filter-title">
<h2 id="filter-title">ابحث وصفِّ السجل</h2>
<p class="cap-evidence-status"><strong>حالة التغطية:</strong> {coverage_status}</p>
<form class="cap-filters" data-cap-filters>
<label>بحث بالاسم العربي أو الإنجليزي
<input type="search" data-cap-search autocomplete="off" placeholder="مثال: التوحد أو cerebral palsy"></label>
<label>المجال<select data-cap-category><option value="">كل المجالات</option>{category_options}</select></label>
<label>مسار الدليل<select data-cap-route><option value="">كل مسارات الدليل</option>{route_options}</select></label>
<label>حالة الانتقاء<select data-cap-evidence>
<option value="">كل الحالات</option>
<option value="selected">حزمة أدلة منتقاة</option>
<option value="not-selected">البروتوكول فقط دون حزمة منتقاة</option>
</select></label>
<button type="reset" class="cap-reset" data-cap-reset>مسح المرشحات</button>
</form>
<p class="cap-result-status" role="status" aria-live="polite"><strong data-cap-count>100</strong> حالة ظاهرة من 100.</p>
<div class="cap-registry" data-cap-registry>{''.join(cards)}</div>
<p class="cap-empty" data-cap-empty hidden>لا توجد نتيجة مطابقة. جرّب كلمة أو مرشحًا آخر.</p>
</section>
</div>
"""
    return page_shell(
        title="سجل الحالات المئة — لنرتقي بقدراتهم",
        description="سجل بحثي قابل للبحث يضم مئة حالة موزعة بحسب المجال ومسار الدليل من دون تعميم موهبة أو اختزال الشخص.",
        canonical_path=SECTION + "/registry/",
        main=main,
        current="سجل الحالات المئة",
        schema_nodes=[
            {
                "@type": "CollectionPage",
                "@id": BASE + SECTION + "/registry/#page",
                "url": BASE + SECTION + "/registry/",
                "name": "سجل الحالات المئة",
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": 100,
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": item["rank"],
                            "name": item["title_ar"],
                        }
                        for item in data["conditions"]
                    ],
                },
            },
            crumb_schema,
        ],
    )


def render_sources(data: dict[str, Any], ids: list[str]) -> str:
    sources = source_map(data)
    return "".join(
        f'<li id="source-{e(key)}"><a href="{e(sources[key]["url"])}" rel="noopener">'
        f'{e(sources[key]["publisher"])} — {e(sources[key]["title"])}</a> '
        f'({e(sources[key]["year"])}؛ تحقق {e(sources[key]["verified_at"])})</li>'
        for key in ids
    )


def render_selected_evidence(data: dict[str, Any], guide: dict[str, Any]) -> str:
    packet = guide["evidence_packet"]
    if packet is None:
        return """
<section class="cap-section cap-evidence-status" data-evidence-packet="not-selected"
 aria-labelledby="selected-evidence-title">
<p class="cap-eyebrow">حدّ التغطية البحثية</p>
<h2 id="selected-evidence-title">حالة الانتقاء البحثي لهذه الصفحة</h2>
<p>لم تكتمل لهذه الحالة بعد حزمة أدلة منتقاة مكافئة للحزمة المنشورة في الفئة الأولى. الصفحة الحالية بروتوكول عملي كامل مبني على ملف حالة شرطي والمنهج التأهيلي المشترك، ومعها مرجع سلطة مباشر ومسار بحث حي؛ لكنها لا تُقدَّم بوصفها خلاصة انتقائية مكتملة للدراسات الخاصة بالحالة.</p>
</section>"""

    sources = source_map(data)
    character_labels = data["evidence_character_labels"]
    claim_cards: list[str] = []
    for index, claim in enumerate(packet["claims"], start=1):
        citations = "، ".join(
            f'<a href="#source-{e(source_id)}">'
            f'{e(sources[source_id]["publisher"])} — '
            f'{e(sources[source_id]["title"])}</a>'
            for source_id in claim["source_ids"]
        )
        claim_cards.append(
            f"""<article class="cap-evidence-claim"
 data-evidence-claim-type="{e(claim["type"])}">
<header><span>الادعاء المحدود {index} من 3</span>
<h3>{e(EVIDENCE_CLAIM_TITLES[claim["type"]])}</h3></header>
<p class="cap-evidence-statement">{e(claim["statement"])}</p>
<dl>
<div class="cap-evidence-support"><dt>ما الذي يدعمه الدليل؟</dt>
<dd>{e(claim["what_it_supports"])}</dd></div>
<div class="cap-evidence-boundary"><dt>ما الذي لا يدعمه الدليل؟</dt>
<dd>{e(claim["what_it_does_not_support"])}</dd></div>
<div><dt>طبيعة الدليل وحدوده</dt>
<dd>{e(character_labels[claim["evidence_character"]])}</dd></div>
</dl>
<p class="cap-evidence-citations"><strong>مصادر الادعاء:</strong> {citations}</p>
</article>"""
        )
    return f"""
<section class="cap-section cap-selected-evidence" data-evidence-packet="selected"
 aria-labelledby="selected-evidence-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">انتقاء خاص بالحالة</p>
<h2 id="selected-evidence-title">خلاصة الأدلة المنتقاة</h2></div>
<p>ثلاثة ادعاءات قابلة للتدقيق، حُدِّث بحثها في {e(packet["search_updated"])}. هذا انتقاء وترجمة داخلية، ولم يخضع بعد لمراجعة خارجية مستقلة.</p></div>
<div class="cap-evidence-claims">{''.join(claim_cards)}</div>
</section>"""


def render_guide(data: dict[str, Any], guide: dict[str, Any]) -> str:
    condition = next(
        item for item in data["conditions"] if item["slug"] == guide["slug"]
    )
    route = data["evidence_routes"][condition["evidence_route"]]
    profile = guide["profile"]
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            (condition["title_ar"], None),
        ]
    )
    hypotheses = "".join(
        f"""<article class="cap-hypothesis">
<h3>{index}. {e(item["name"])}</h3>
<dl>
<div><dt>الفرضية المحدودة</dt><dd>{e(item["claim"])}</dd></div>
<div><dt>تجربة مهمة صغيرة</dt><dd>{e(item["microtrial"])}</dd></div>
<div><dt>الدعم أو التكييف</dt><dd>{e(item["support"])}</dd></div>
<div><dt>ما الذي نقيسه؟</dt><dd>{e(item["measure"])}</dd></div>
<div class="cap-stop"><dt>متى نتوقف أو نعيد الصياغة؟</dt><dd>{e(item["stop_rule"])}</dd></div>
</dl></article>"""
        for index, item in enumerate(guide["hypotheses"], start=1)
    )
    plan = "".join(
        f'<li><span>{index}</span><p>{e(item)}</p></li>'
        for index, item in enumerate(guide["twelve_week_plan"], start=1)
    )
    measure_items = data["protocol"]["minimum_measures"]
    stop_items = data["protocol"]["stop_rules"]
    universal_stages = "".join(
        f"""<article class="cap-stage">
<span class="cap-stage-number" aria-hidden="true">{stage["number"]}</span>
<div><h3>المرحلة {stage["number"]}: {e(stage["title"])}</h3>
{ul(stage["actions"])}
<p class="cap-output"><strong>المخرج المطلوب:</strong> {e(stage["output"])}</p></div>
</article>"""
        for stage in data["protocol"]["stages"]
    )
    packet_source_ids = (
        [
            source_id
            for claim in guide["evidence_packet"]["claims"]
            for source_id in claim["source_ids"]
        ]
        if guide["evidence_packet"]
        else []
    )
    guide_source_ids = unique_in_order(
        [*guide["source_ids"], *packet_source_ids]
    )
    source_html = render_sources(data, guide_source_ids)
    selected_evidence_html = render_selected_evidence(data, guide)
    reference_links = "".join(
        f'<li><a href="{e(item["url"])}" rel="noopener">'
        f'{e(item["publisher"])} — {e(item["title"])}</a></li>'
        for item in guide["research_links"]
    )
    query = quote_plus(
        f'"{condition["title_en"]}" AND '
        "(rehabilitation OR participation OR functioning) AND "
        '("systematic review" OR guideline)'
    )
    if guide["evidence_packet"]:
        profile_origin = (
            "حزمة أدلة منتقاة خاصة بالحالة + ملف حالة شرطي "
            "+ المنهج التأهيلي المشترك"
        )
    elif not guide["generated_from_profile"]:
        profile_origin = "مراجعة بحثية خاصة ومباشرة"
    else:
        profile_origin = "ملف حالة شرطي + المنهج التأهيلي المشترك"
    main = f"""
<section class="cap-page-hero cap-guide-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">الدليل التفصيلي {condition["rank"]:02d} من سجل المئة</p>
<h1>{e(guide["title"])}</h1>
<p class="cap-lead">{e(guide["evidence_label"])}</p>
<div class="cap-evidence-chip"><strong>{e(route["label"])}</strong><span>{e(route["meaning"])}</span></div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="profile-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">طبقة الحالة الخاصة</p><h2 id="profile-title">ما الذي يختلف في هذا البروتوكول؟</h2></div>
<p><strong>طريقة البناء:</strong> {e(profile_origin)}. لا تتحول المعلومة الخاصة بالحالة إلى توصية إلا بعد اختبارها عند الشخص ومرورها عبر المراحل التسع.</p></div>
<div class="cap-grid cap-grid-three cap-profile-grid">
<article class="cap-card"><h3>الموقف العلمي</h3><p>{e(profile["position"])}</p></article>
<article class="cap-card"><h3>سؤال القدرة</h3><p>{e(profile["ability_focus"])}</p></article>
<article class="cap-card"><h3>أولوية الوصول</h3><p>{e(profile["access_priority"])}</p></article>
<article class="cap-card"><h3>فحص الأمان</h3><p>{e(profile["safety_priority"])}</p></article>
<article class="cap-card"><h3>التجربة المصغرة</h3><p>{e(profile["task_trial"])}</p></article>
<article class="cap-card"><h3>مثال هدف وظيفي</h3><p>{e(profile["functional_goal"])}</p></article>
</div>
</section>
<section class="cap-section" aria-labelledby="evidence-title">
<h2 id="evidence-title">ماذا يقول الدليل، وماذا لا يقول؟</h2>
{ul(guide["evidence_summary"], "cap-evidence-list")}
</section>
{selected_evidence_html}
<section class="cap-section cap-soft" aria-labelledby="assume-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="assume-title">لا تفترض</h2>{ul(guide["do_not_assume"], "cap-cross-list")}</article>
<article class="cap-health"><h2>الصحة والأمان أولًا</h2>{ul(guide["health_first"])}</article>
</div>
</section>
<section class="cap-section" aria-labelledby="hypothesis-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">اختبار لا تصنيف</p><h2 id="hypothesis-title">فرضيات قدرة قابلة للدحض</h2></div>
<p>هذه ليست صفات لازمة للحالة. اختر فرضية واحدة فقط إذا وافق عليها الشخص وكانت ذات معنى له، ثم اختبرها في أكثر من يوم.</p></div>
<div class="cap-hypotheses">{hypotheses}</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="full-protocol-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">البروتوكول الكامل لهذه الحالة</p><h2 id="full-protocol-title">من الأمان إلى القرار المشترك</h2></div>
<p>تنفذ المراحل بالترتيب، وتوثق مخرجاتها في ورقة البروتوكول. لا تبدأ تجربة القدرة قبل تثبيت الصحة وطريقة الرفض، ولا تعتمدها قبل قياس التعميم والعبء.</p></div>
<div class="cap-stages">{universal_stages}</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="adapt-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="adapt-title">تكييفات تكشف القدرة</h2>{ul(guide["adaptations"], "cap-check-list")}</article>
<article><h2>قياس النجاح كاملًا</h2>{ul(measure_items, "cap-measure-list")}</article>
</div>
</section>
<section class="cap-section" aria-labelledby="plan-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">دورة أولى قابلة للتعديل</p><h2 id="plan-title">خطة 12 أسبوعًا</h2></div>
<p>الأسابيع إطار مراجعة لا وصفة علاج. يحدد الفريق المؤهل الجرعة والوسيلة، ويستطيع الشخص التوقف في أي وقت.</p></div>
<ol class="cap-timeline">{plan}</ol>
</section>
<section class="cap-section cap-danger" aria-labelledby="stop-title">
<h2 id="stop-title">قواعد توقف عامة</h2>{ul(stop_items)}
<p>تُضاف إليها قواعد خاصة بالحالة وبالشخص وخطة الطوارئ المعتمدة لدى فريقه.</p>
</section>
<section class="cap-section" aria-labelledby="sources-title">
<h2 id="sources-title">المصادر التي تسند هذا الدليل</h2>
<ol class="cap-sources">{source_html}</ol>
<p class="cap-note">تاريخ التحقق يعني مراجعة الرابط وبيانات المصدر، ولا يعني اعتماد المحتوى من الجهة الناشرة للمصدر.</p>
</section>
<section class="cap-section cap-soft" aria-labelledby="research-title">
<h2 id="research-title">تحقق خاص بالحالة ومسار للبحث الأحدث</h2>
<p>الروابط التالية تساعد المراجع المتخصص على تدقيق معلومات الحالة وتحديث البحث. رابط PubMed يعرض نتائج متغيرة، لذلك لا يُعد بمفرده مصدرًا مختارًا أو دليلًا على فعالية تدخل.</p>
<ul class="cap-sources">{reference_links}
<li><a href="https://pubmed.ncbi.nlm.nih.gov/?term={e(query)}" rel="noopener">بحث PubMed محدث: {e(condition["title_en"])} + التأهيل والمشاركة والمراجعات أو الإرشادات</a></li>
</ul>
</section>
<nav class="cap-next" aria-label="خطوات تالية">
<a href="../protocol/">استخدم ورقة البروتوكول</a>
<a href="../registry/">ارجع إلى سجل الحالات المئة</a>
</nav>
</div>
"""
    return page_shell(
        title=guide["title"],
        description=guide["evidence_label"],
        canonical_path=SECTION + "/" + guide["slug"] + "/",
        main=main,
        schema_nodes=[
            {
                "@type": "Article",
                "@id": BASE + SECTION + "/" + guide["slug"] + "/#article",
                "url": BASE + SECTION + "/" + guide["slug"] + "/",
                "headline": guide["title"],
                "description": guide["evidence_label"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "publisher": {"@id": BASE + "#organization"},
                "citation": [
                    source_map(data)[key]["url"] for key in guide_source_ids
                ],
            },
            crumb_schema,
        ],
    )


def write_page(site: Path, route: str, body: str) -> Path:
    target = site / SECTION / route / "index.html" if route else site / SECTION / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def gateway_block(context: str) -> str:
    copy = {
        "home": (
            "لنرتقي بقدراتهم",
            "مئة بروتوكول حالة كامل: أمان ووصول وتجارب مهام وقياس وخطة مراجعة، من دون تجميل المرض أو تعميم الموهبة.",
        ),
        "special-needs": (
            "من الاحتياج إلى فرصة قابلة للقياس",
            "اكتشف قسم «لنرتقي بقدراتهم»: صوت الشخص أولًا، تعديل الحواجز، وتجارب صغيرة تقيس الاستقلال والرضا والسلامة.",
        ),
        "outside-the-box": (
            "طبقة تكميلية لاختبار القدرات",
            "بعد التقييم الوظيفي، استخدم بروتوكول «لنرتقي بقدراتهم» لصياغة فرضيات محدودة واختبارها بدل تحويل التشخيص إلى مهنة.",
        ),
    }[context]
    return f"""{BRIDGE_START}
<style data-capabilities-v280-bridge>
.capabilities-v280-bridge{{margin:2rem auto;padding:1.4rem;border:1px solid #bfded7;border-radius:20px;background:#f5fbf8;color:#173f3a;box-shadow:0 8px 24px rgba(23,63,58,.08)}}.capabilities-v280-bridge h2{{margin:.15rem 0 .55rem;color:#154f49}}.capabilities-v280-bridge p{{max-width:72ch}}.capabilities-v280-bridge a{{display:inline-block;margin-top:.35rem;padding:.72rem 1rem;border-radius:999px;background:#0f766e;color:#fff;text-decoration:none;font-weight:800}}.capabilities-v280-bridge a:focus-visible{{outline:3px solid #d4a72c;outline-offset:3px}}
</style>
<section class="capabilities-v280-bridge" aria-labelledby="capabilities-v280-{e(context)}-title">
<p><strong>لنرتقي بقدراتهم</strong> · 100 حالة · 100 بروتوكول كامل · 9 مراحل مشتركة</p>
<h2 id="capabilities-v280-{e(context)}-title">{e(copy[0])}</h2>
<p>{e(copy[1])}</p>
<a href="{BASE_PATH}{SECTION}/">ادخل إلى القسم</a>
</section>
{BRIDGE_END}"""


def patch_gateway(path: Path, context: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing gateway page: {path}")
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END),
        flags=re.DOTALL,
    )
    block = gateway_block(context)
    matches = pattern.findall(text)
    if matches:
        if len(matches) != 1:
            raise ValueError(f"Duplicate capability gateway markers: {path}")
        updated = pattern.sub(block, text)
        path.write_text(updated, encoding="utf-8")
        return
    if "</main>" in text:
        text = text.replace("</main>", block + "\n</main>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", block + "\n</body>", 1)
    else:
        raise ValueError(f"Gateway lacks main/body closing tag: {path}")
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


def write_sitemap(site: Path, paths: list[str]) -> None:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for index, path in enumerate(paths):
        item = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(item, f"{{{SITEMAP_NS}}}loc").text = BASE + path
        ET.SubElement(item, f"{{{SITEMAP_NS}}}lastmod").text = UPDATED
        ET.SubElement(item, f"{{{SITEMAP_NS}}}changefreq").text = (
            "monthly" if index < 4 else "yearly"
        )
        ET.SubElement(item, f"{{{SITEMAP_NS}}}priority").text = (
            "0.9" if index == 0 else "0.8"
        )
    ET.ElementTree(root).write(
        site / SITEMAP_NAME, encoding="utf-8", xml_declaration=True
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def register_root_sitemap(site: Path, paths: list[str]) -> None:
    sitemap_index = site / "sitemap.xml"
    if not sitemap_index.is_file():
        raise FileNotFoundError("Missing root sitemap.xml")
    tree = ET.parse(sitemap_index)
    root = tree.getroot()
    root_type = local_name(root.tag)
    if root_type == "sitemapindex":
        target = BASE + SITEMAP_NAME
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
            if node.text
        }
        if target not in existing:
            item = ET.SubElement(root, qualify(root, "sitemap"))
            ET.SubElement(item, qualify(root, "loc")).text = target
    elif root_type == "urlset":
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if node.text
        }
        for path in paths:
            target = BASE + path
            if target in existing:
                continue
            item = ET.SubElement(root, qualify(root, "url"))
            ET.SubElement(item, qualify(root, "loc")).text = target
            existing.add(target)
    else:
        raise ValueError(f"Unsupported sitemap root: {root_type}")
    tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)


def register_robots(site: Path) -> None:
    path = site / "robots.txt"
    if not path.is_file():
        raise FileNotFoundError("Missing robots.txt")
    line = f"Sitemap: {BASE}{SITEMAP_NAME}"
    lines = [item.rstrip() for item in path.read_text(encoding="utf-8").splitlines()]
    lines = [item for item in lines if item != line]
    lines.append(line)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    data = load_and_validate()
    profiles = load_profiles(data)
    direct_references = load_direct_reference_map(data)
    guides = complete_guides(data, profiles, direct_references)
    if len(guides) != 100:
        raise ValueError(f"Exactly 100 complete guides are required, found {len(guides)}")
    if not site.is_dir():
        raise FileNotFoundError(f"Missing site output: {site}")
    for source in (CSS_PATH, JS_PATH):
        if not source.is_file():
            raise FileNotFoundError(f"Missing capability asset: {source}")

    write_page(site, "", render_hub(data, guides))
    write_page(site, "methodology", render_methodology(data))
    write_page(site, "protocol", render_protocol(data))
    write_page(site, "registry", render_registry(data, guides))
    for guide in guides:
        write_page(site, guide["slug"], render_guide(data, guide))

    asset_css = site / "assets" / "css"
    asset_js = site / "assets" / "js"
    asset_css.mkdir(parents=True, exist_ok=True)
    asset_js.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_PATH, asset_css / CSS_PATH.name)
    shutil.copy2(JS_PATH, asset_js / JS_PATH.name)

    patch_gateway(site / "index.html", "home")
    patch_gateway(site / "special-needs" / "index.html", "special-needs")
    patch_gateway(site / "outside-the-box" / "index.html", "outside-the-box")

    paths = [
        SECTION + "/",
        SECTION + "/methodology/",
        SECTION + "/protocol/",
        SECTION + "/registry/",
        *[SECTION + "/" + item["slug"] + "/" for item in guides],
    ]
    write_sitemap(site, paths)
    register_root_sitemap(site, paths)
    register_robots(site)

    evidence_packet_count = len(data["evidence_packets"])
    evidence_claim_count = sum(
        len(item["claims"]) for item in data["evidence_packets"]
    )
    report = {
        "version": VERSION,
        "status": "passed",
        "updated_at": UPDATED,
        "condition_count": len(data["conditions"]),
        "detailed_guide_count": len(guides),
        "bespoke_research_synthesis_count": len(data["guides"]),
        "condition_profile_count": len(profiles),
        "direct_condition_reference_count": len(direct_references),
        "generated_page_count": len(paths),
        "sitemap_url_count": len(paths),
        "protocol_stage_count": len(data["protocol"]["stages"]),
        "source_count": len(data["sources"]),
        "curated_evidence_packet_count": evidence_packet_count,
        "curated_evidence_claim_count": evidence_claim_count,
        "curated_evidence_source_count": data["selected_evidence_source_count"],
        "curated_evidence_remaining_count": (
            len(data["conditions"]) - evidence_packet_count
        ),
        "curated_evidence_covered_categories": data[
            "evidence_covered_categories"
        ],
        "external_clinical_review_completed": False,
        "diagnostic_automation": False,
        "condition_implies_strength": False,
        "stability_first_routes": sum(
            item["evidence_route"] == "stability-first"
            for item in data["conditions"]
        ),
        "review_status": data["review_status"],
        "categories": data["categories"],
        "evidence_routes": data["evidence_routes"],
        "protocol": data["protocol"],
        "conditions": data["conditions"],
        "guides": guides,
        "evidence_packets": data["evidence_packets"],
        "evidence_selection_methods": data["evidence_selection_methods"],
        "evidence_character_labels": data["evidence_character_labels"],
        "sources": data["sources"],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "capabilities-v280.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    report = publish(args.site.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
