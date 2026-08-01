#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERSION = 401
BASE = "https://healthrenewal.org"
REVIEWED_AT = "2026-08-01"
NEXT_REVIEW_DUE = "2027-02-01"
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
FORBIDDEN = re.compile(r"\b(?:معاقين|المعاقين|المعاق)\b", re.IGNORECASE)
EXPECTED_DISTRIBUTION = {"special-needs": 60, "learning-paths": 15, "child": 10, "family": 8, "home": 7}
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "content" / "v401" / "undercovered-content-ar.json"

SOURCES: dict[str, dict[str, str]] = {
    "who-icf": {"title": "WHO — International Classification of Functioning, Disability and Health (ICF)", "url": "https://www.who.int/classifications/international-classification-of-functioning-disability-and-health", "note": "إطار دولي يربط الوظائف والأنشطة والمشاركة بالعوامل البيئية والشخصية."},
    "who-at": {"title": "WHO — Assistive technology", "url": "https://www.who.int/ar/news-room/fact-sheets/detail/assistive-technology", "note": "مرجع عالمي للوصول إلى المنتجات والخدمات المساندة وإشراك المستخدم والأسرة."},
    "unicef-inclusive": {"title": "UNICEF — Guidance on Including Children with Disabilities in Education", "url": "https://www.unicef.org/supply/documents/guidance-including-children-disabilities-education-kit-handbook", "note": "إرشاد عملي للمشاركة الكاملة وتكييف الأنشطة التعليمية والترفيهية."},
    "crpd-9": {"title": "UN CRPD — Article 9: Accessibility", "url": "https://social.desa.un.org/issues/disability/crpd/article-9-accessibility", "note": "حق الوصول إلى البيئة والمواصلات والمعلومات والاتصالات والخدمات."},
    "crpd-19": {"title": "UN CRPD — Article 19: Living independently and inclusion in the community", "url": "https://social.desa.un.org/issues/disability/crpd/article-19-living-independently-and-being-included-in-the-community", "note": "الاختيار والاستقلال والوصول إلى دعم منزلي ومجتمعي غير عازل."},
    "crpd-21": {"title": "UN CRPD — Article 21: Access to information and communication", "url": "https://social.desa.un.org/issues/disability/crpd/article-21-freedom-of-expression-and-opinion-and-access-to-information", "note": "المعلومات الميسرة وقبول وسائل التواصل البديل والمعزز ولغة الإشارة."},
    "crpd-24": {"title": "UN CRPD — Article 24: Education", "url": "https://social.desa.un.org/issues/disability/crpd/article-24-education", "note": "التعليم الدامج والتكييف المعقول والدعم الفردي للمشاركة والتعلم."},
    "crpd-25": {"title": "UN CRPD — Article 25: Health", "url": "https://social.desa.un.org/issues/disability/crpd/article-25-health", "note": "الحق في أعلى مستوى صحي ممكن دون تمييز وعلى أساس الموافقة والكرامة."},
    "crpd-27": {"title": "UN CRPD — Article 27: Work and employment", "url": "https://social.desa.un.org/issues/disability/crpd/article-27-work-and-employment", "note": "الحق في العمل المختار والبيئة المفتوحة والدامجة والميسرة."},
    "w3c-wcag": {"title": "W3C WAI — Web Content Accessibility Guidelines (WCAG) 2.2", "url": "https://www.w3.org/TR/WCAG22/", "note": "معيار دولي للمحتوى الرقمي القابل للإدراك والتشغيل والفهم والمتانة."},
    "w3c-cognitive": {"title": "W3C WAI — Cognitive Accessibility", "url": "https://www.w3.org/WAI/cognitive/", "note": "إرشادات إضافية لتقليل الحواجز المعرفية واللغوية والتعلمية."},
    "asha-aac": {"title": "ASHA — Augmentative and Alternative Communication", "url": "https://www.asha.org/practice-portal/professional-issues/augmentative-and-alternative-communication/", "note": "بوابة مهنية للتواصل المعزز والبديل عبر مراحل العمر والبيئات."},
    "nice-autism": {"title": "NICE CG170 — Autism in under 19s: support and management", "url": "https://www.nice.org.uk/guidance/CG170", "note": "إرشاد مهني للدعم والإدارة والتنسيق والانتقال مع الأطفال والشباب وأسرهم."},
}
PROFILE_SOURCES = {
    "communication": ("who-icf", "asha-aac", "crpd-21"), "education": ("who-icf", "unicef-inclusive", "crpd-24"),
    "sensory": ("who-icf", "crpd-9", "w3c-cognitive"), "behavior": ("who-icf", "nice-autism", "crpd-19"),
    "daily": ("who-icf", "crpd-25", "crpd-19"), "transition": ("who-icf", "crpd-19", "crpd-27"),
    "assistive": ("who-icf", "who-at", "crpd-9", "w3c-wcag"), "coordination": ("who-icf", "crpd-19", "unicef-inclusive"),
    "learning": ("who-icf", "crpd-9", "crpd-24", "w3c-wcag"), "child": ("who-icf", "unicef-inclusive", "crpd-24"),
    "family": ("who-icf", "crpd-19", "crpd-21"), "home": ("who-icf", "crpd-19", "crpd-9"),
}
PROFILE_METHODS = {
    "communication": (["فهم الرسائل", "التعبير والاختيار", "الوصول الحركي والحسي", "استجابة شريك التواصل"], ["إتاحة وسيلة التواصل طوال الوقت", "النمذجة دون اختبار", "الانتظار المنظم", "احترام الرفض", "توفير بدائل عند التعطل", "التعميم بين الشركاء"]),
    "education": (["الوصول إلى التعليمات", "بدء المهمة", "إظهار المعرفة", "المشاركة مع الأقران"], ["تثبيت هدف التعلم", "إزالة العائق غير المقصود", "تنويع العرض", "تنويع الاستجابة", "تجربة التكييف", "مراجعة الاستقلال"]),
    "sensory": (["خصائص المحفز", "شدة التعرض ومدته", "المهمة المتأثرة", "خيارات التنظيم"], ["قياس خط أساس", "تعديل عنصر واحد", "إتاحة انسحاب آمن", "الحفاظ على المشاركة", "تجنب الحرمان", "مراجعة أقل دعم لازم"]),
    "behavior": (["ما يسبق الحدث", "السلوك القابل للملاحظة", "ما يتبعه", "الوظيفة المحتملة"], ["تعريف السلوك دون حكم", "تحديد العلامات المبكرة", "تعديل البيئة", "تعليم بديل وظيفي", "تعزيز الأمان والاختيار", "مراجعة البيانات"]),
    "daily": (["خطوات المهمة", "الألم أو التعب", "الخصوصية والاختيار", "نوع المساعدة"], ["تحليل المهمة", "فحص الخطر", "توفير التواصل", "تقديم المساعدة الدنيا", "حماية الخصوصية", "تدرج الاستقلال"]),
    "transition": (["اختيار الشخص", "المهارات الحالية", "الحواجز البيئية", "الدعم الطبيعي والرسمي"], ["هدف يقوده الشخص", "تجربة واقعية", "تكييف محدد", "تدريب الشركاء", "خفض الدعم تدريجيًا", "مراجعة الرضا"]),
    "assistive": (["المهمة المستهدفة", "خصائص المستخدم", "البيئة", "التدريب والصيانة"], ["تحديد خط أساس", "تجربة خيارات", "تدريب المستخدم", "قياس القبول", "تأمين بديل", "قرار مشترك"]),
    "coordination": (["صوت الشخص", "هدف مشترك", "مسؤوليات واضحة", "بيانات نافعة"], ["صياغة سؤال قرار", "عرض بيانات", "تسجيل رأي الشخص", "تعيين مسؤول", "حماية الخصوصية", "إغلاق المتابعة"]),
    "learning": (["المعرفة السابقة", "المهارة التطبيقية", "سياق التطبيق", "التغذية الراجعة"], ["تحديد ناتج تعلم", "دراسة مثال", "تطبيق أداة", "مراجعة الأثر", "تصحيح الانحياز", "نقل المهارة"]),
    "child": (["نقاط القوة", "المشاركة في الروتين", "العوائق البيئية", "استجابة البالغين"], ["ملاحظة طبيعية", "توفير اختيار", "تقليل حمل المهمة", "إشراك الأسرة", "حماية الكرامة", "إحالة القلق"]),
    "family": (["أولويات الشخص", "موارد الأسرة", "عبء الرعاية", "الدعم الرسمي"], ["اختيار أولوية", "توزيع الأدوار", "إتاحة الراحة", "استخدام مورد", "طلب دعم", "مراجعة الخطة"]),
    "home": (["المهمة المنزلية", "المسار والمكان", "التواصل والتنظيم", "السلامة والمساعدة"], ["مشاهدة المهمة", "إزالة عائق", "تجربة تعديل", "تحديد المساعدة الدنيا", "تدريب بديل", "قياس الاستقلال"]),
}
ROUTE_PREFIX = {"special-needs": "special-needs/practical", "learning-paths": "learning-paths", "child": "sectors/child/guides", "family": "sectors/family/guides", "home": "sectors/home/guides"}
HUB_PATHS = {"special-needs": "special-needs/index.html", "learning-paths": "learning-paths/index.html", "child": "sectors/child/index.html", "family": "sectors/family/index.html", "home": "sectors/home/index.html"}
SECTION_LABELS = {"special-needs": "الأدلة العملية المتقدمة لذوي الاحتياجات الخاصة", "learning-paths": "مسارات التعلم المهنية والتطبيقية", "child": "أدلة قطاع الطفل", "family": "أدلة قطاع الأسرة", "home": "أدلة قطاع المنزل"}
TOPICS: list[dict[str, str]] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["pages"]


def route_for(item: dict[str, str]) -> str:
    return f"{ROUTE_PREFIX[item['section']]}/{item['slug']}/"


def visible_words(source: str) -> int:
    return len(WORD_RE.findall(html.unescape(TAG_RE.sub(" ", source))))


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def li(values: list[str] | tuple[str, ...]) -> str:
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def render_page(item: dict[str, str]) -> str:
    domains, actions = PROFILE_METHODS[item["profile"]]
    route, title = route_for(item), item["title"]
    canonical = f"{BASE}/{route}"
    description = f"دليل عربي موسع حول {title}، يشرح التقييم الوظيفي والخطوات العملية والقياس والسلامة وحدود الاستخدام اعتمادًا على مراجع دولية موثوقة."
    source_rows = "".join(f'<li><a href="{esc(SOURCES[s]["url"])}" target="_blank" rel="noopener noreferrer">{esc(SOURCES[s]["title"])}</a><span>{esc(SOURCES[s]["note"])}</span></li>' for s in PROFILE_SOURCES[item["profile"]])
    schema = {"@context": "https://schema.org", "@type": "Article", "inLanguage": "ar", "headline": title, "description": description, "mainEntityOfPage": canonical, "datePublished": REVIEWED_AT, "dateModified": REVIEWED_AT, "author": {"@type": "Organization", "name": "Health Renewal"}, "publisher": {"@type": "Organization", "name": "Health Renewal"}, "about": item["objective"], "audience": {"@type": "Audience", "audienceType": item["audience"]}, "isAccessibleForFree": True}
    baseline = [f"عرّف النتيجة المطلوبة في {item['setting']} بفعل يمكن ملاحظته.", "سجّل متى يظهر العائق ومتى يخف ومن كان حاضرًا.", "افصل بين القدرة وبين سهولة البيئة ووضوح التعليمات.", "اجمع عدة فرص حتى لا يُبنى القرار على يوم استثنائي."]
    metrics = [item["measure"], "درجة الاستقلال ونوع المساعدة", "رضا الشخص وعبء التنفيذ", "نقل النتيجة إلى موقف ثانٍ"]
    rules = ["استمر عندما تتحسن النتيجة دون زيادة الضيق أو الاعتماد.", "عدّل عنصرًا واحدًا عندما لا يظهر تغير بعد فرص كافية.", "أوقف التجربة واطلب تقييمًا عند الألم أو الخطر أو التراجع.", "لا تعتبر الهدوء أو الطاعة وحدهما نجاحًا؛ النجاح يشمل الاختيار والمشاركة."]
    safety = [f"الخطر المركزي الواجب منعه: {item['risk']}.", "عند خطر مباشر على الحياة أو التنفس أو البلع أو إصابة خطرة أو اشتباه إساءة تُطلب الطوارئ المحلية فورًا.", "فقدان مهارة أو ألم مستمر أو تغير مفاجئ يستلزم تقييمًا صحيًا مؤهلًا.", "لا يجيز الدليل تعديل دواء أو جهاز طبي أو وضعية علاجية أو استخدام تقييد جسدي."]
    checklist = ["هل اختار الشخص الهدف؟", "هل جُمعت بيانات من أكثر من موقف؟", "هل فُحصت الحواجز قبل لوم الشخص؟", "هل جُرّب تعديل واحد؟", "هل توجد وسيلة للرفض وطلب المساعدة؟", "هل تشمل المقاييس المشاركة والاستقلال والرضا؟", "هل حُدد موعد مراجعة؟", "هل حُفظ الحد الأدنى من البيانات؟", "هل عُرفت علامات الإحالة؟", "هل جُرّبت النتيجة مع شريك ثانٍ؟"]
    errors = [f"حل جاهز قبل فهم {item['objective']}.", "الاعتماد على التشخيص أو الانطباع وحده.", "تغيير عدة عناصر معًا.", "قياس الامتثال بدل المشاركة.", "إبقاء دعم غير مفيد أو سحبه فجأة.", f"تجاهل الخطر: {item['risk']}."]
    domain_cards = "".join(f'<article class="card"><h3>{i+1}. {esc(d)}</h3><p>صف القدرة والعائق والدعم وما يتغير عندما تصبح البيئة أو المهمة أو استجابة الشريك أكثر ملاءمة. اجمع مثالًا ناجحًا وآخر متعثرًا، وحدد الفرق القابل للتعديل بدل الاكتفاء بوصف عام.</p></article>' for i, d in enumerate(domains))
    metric_rows = "".join(f'<tr><td>{esc(m)}</td><td>قياس قصير متكرر مع تسجيل نوع الدعم والسياق.</td><td>هل يتحسن دون ضرر أو عبء غير مقبول؟</td></tr>' for m in metrics)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Health Renewal</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script><style>:root{{--bg:#f7f5ef;--ink:#14221e;--muted:#52635d;--card:#fff;--line:#d8e2dd;--accent:#146b58;--warn:#7d4b0f}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}a{{color:#075e4b}}header,main,footer{{max-width:1120px;margin:auto;padding:1.2rem}}nav a{{margin-inline-end:1rem}}.hero{{background:linear-gradient(135deg,#e7f3ee,#fff8e8);border:1px solid var(--line);border-radius:22px;padding:clamp(1.2rem,4vw,3rem);margin-block:1rem 2rem}}h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.35}}h2{{font-size:1.55rem;margin-top:2.4rem}}.card,.notice{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.2rem;margin:1rem 0}}.notice{{border-inline-start:6px solid var(--warn)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}}.meta,.sources span{{color:var(--muted)}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{border:1px solid var(--line);padding:.7rem;text-align:right;vertical-align:top}}</style></head><body><header><nav aria-label="التنقل الأساسي"><a href="/">الرئيسية</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/source-registry/">سجل المصادر</a><a href="/trust/">الثقة والمنهج</a></nav></header><main id="content">
<section class="hero"><p><strong>{esc(SECTION_LABELS[item['section']])}</strong></p><h1>{esc(title)}</h1><p>{esc(item['objective'])}. صُمم الدليل لبيئة {esc(item['setting'])} ويخاطب {esc(item['audience'])}.</p><p class="meta">مراجعة داخلية: {REVIEWED_AT} · المراجعة الخارجية المتخصصة موصى بها · المراجعة التالية: {NEXT_REVIEW_DUE}</p></section>
<section class="notice"><h2>حدود الاستخدام والقرار الآمن</h2><p><strong>حدود الاستخدام:</strong> هذا محتوى تثقيفي وتخطيطي، وليس تشخيصًا فرديًا ولا علاجًا ولا وصفة طبية ولا بديلًا عن التقييم المهني. تختلف القوانين والموارد والسياقات، ويجب مواءمة الخطوات مع الشخص والبيئة المحلية.</p><p>لا تُستخدم الصفحة لتبرير الإكراه أو الحرمان أو سحب وسيلة تواصل أو تجاهل الألم. القرار الجيد يحافظ على الكرامة والاختيار ويستخدم أقل دعم ضروري، ويُراجع عندما لا يحقق أثرًا وظيفيًا واضحًا.</p></section>
<section><h2>1. المشكلة والنتيجة ذات المعنى</h2><p>يركز الدليل على {esc(item['objective'])} داخل {esc(item['setting'])}. تبدأ الممارسة الجيدة بسؤال: ما المهمة أو المشاركة التي يريدها الشخص، وما الحاجز الذي يمنعها؟ هذا أدق من الاكتفاء باسم حالة أو حكم عام؛ فقد تتغير النتيجة عندما تتغير طريقة العرض أو الوقت أو الضوضاء أو وسيلة التواصل أو استجابة الشريك.</p><p>الخطة لا تُبنى عن الشخص في غيابه. تُتاح المعلومات بطريقة يفهمها، ويُسجل تفضيله، وتُوفر وسيلة للرفض وطلب التوقف. ويجب منع {esc(item['risk'])}؛ لأن التحسن الظاهري لا يبرر ضررًا أو وصمًا أو فقدانًا للاستقلال.</p></section>
<section><h2>2. الإطار العلمي والحقوقي</h2><p>يعتمد البناء على ICF: النتيجة تنشأ من تفاعل وظائف الشخص وأنشطته ومشاركته والعوامل البيئية، لا من التشخيص منفردًا. لذلك يجمع التقييم معلومات عن نقاط القوة ومتطلبات المهمة والدعم والحواجز وأثر التعديل في الحياة الفعلية.</p><p>الوصول إلى المعلومات والبيئة والتعليم والصحة والعمل والمجتمع حق، وليس مكافأة على الأداء. التكييف المعقول والتواصل الميسر والاختيار والخصوصية عناصر جودة أساسية. المراجع في نهاية الصفحة نقطة انطلاق ولا تحول الإرشاد العام إلى توصية فردية.</p></section>
<section><h2>3. التقييم الوظيفي متعدد المجالات</h2><p>اجمع وصفًا قصيرًا لكل مجال مع مثال على النجاح والتعثر. لا تستخدم دائمًا أو أبدًا دون عدد وسياق، ولا تخلط بين عدم الاستجابة وعدم الفهم أو بين البطء ورفض المهمة.</p><div class="grid">{domain_cards}</div><p>افحص الألم والتعب والتغير الحديث والسمع والبصر والنوم والبلع والحركة عند صلتها. وافحص اللغة والثقافة والموارد؛ لأن خطة لا يمكن تنفيذها ليست عادلة حتى لو بدت صحيحة نظريًا.</p></section>
<section><h2>4. خط الأساس قبل التغيير</h2><ul>{li(baseline)}</ul><p>يكفي عدد محدود من المؤشرات الموثوقة بدل مراقبة واسعة. استخدم تعريفًا تشغيليًا مثل بدأ المهمة خلال دقيقتين، وسجل الفرص الناجحة لتحديد الظروف الداعمة. لا تستخدم البيانات للعقاب أو المقارنة المهينة.</p></section>
<section><h2>5. هدف مشترك قابل للقياس</h2><p>يصف الهدف من سيفعل ماذا، وفي أي سياق، وبأي مستوى من الدعم، وخلال أي مدة. مثال: خلال أربعة أسابيع، ينفذ الشخص المهمة المرتبطة بـ{esc(item['objective'])} في أربع من خمس فرص باستخدام الدعم المتفق عليه مع إمكانية طلب التوقف.</p><p>اسأل: هل الهدف مهم للشخص؟ هل يزيد المشاركة أو الاستقلال أو الأمان؟ هل يمكن قياسه دون انتهاك الخصوصية؟ عند التعارض، أعد تصميم الخيارات والمعلومات بدل إلغاء صوت الشخص.</p></section>
<section><h2>6. بروتوكول التنفيذ</h2><ol>{li(actions)}</ol><p>نفذ الخطوات كتجربة منظمة. ابدأ بموقف متكرر، وحدد المسؤول والمواد والمدة. لا تغيّر أكثر من عنصر جوهري معًا. ناقش البيانات أسبوعيًا مع الشخص والأسرة والفريق، وميّز بين عدم ملاءمة الخطة ونقص التدريب أو الوقت.</p><p>ابدأ بخطوة منخفضة المخاطر قابلة للرجوع، مثل إعادة صياغة تعليمات أو إتاحة تواصل أو إزالة عائق. لا تنتقل إلى تدخل أكثر كثافة إلا بعد توثيق الحاجة وفشل البدائل الأقل تقييدًا وبمشاركة مختص مؤهل.</p></section>
<section><h2>7. التكييفات والكرامة والاستقلال</h2><p>التكييف ليس إنجاز المهمة بدل الشخص؛ بل تغيير في البيئة أو الوقت أو المادة أو التواصل يسمح بإظهار القدرة. يجب أن يكون مفهومًا ومتوافرًا وألا يكشف معلومات شخصية أكثر مما يلزم.</p><p>اختبر التكييف مع المستخدم لا عليه. اسأل عن الراحة والقبول وراقب الاعتماد والعزل والوصم. وفر الرفض والاستراحة والمساعدة، ودرب أكثر من شريك حتى لا تعتمد الخطة على شخص واحد.</p></section>
<section><h2>8. مؤشرات النتيجة وقواعد القرار</h2><table><thead><tr><th>المؤشر</th><th>المتابعة</th><th>سؤال القرار</th></tr></thead><tbody>{metric_rows}</tbody></table><ul>{li(rules)}</ul><p>راجع أسبوعيًا في البداية ثم باعد الفترات بعد الاستقرار. لا تعمم النجاح من جلسة إلى الحياة اليومية دون اختبار النقل. إذا تحسن الأداء فقط مع دعم كثيف، حدد الجزء الضروري وما يمكن تخفيفه تدريجيًا.</p></section>
<section><h2>9. السلامة ومتى نطلب مساعدة متخصصة؟</h2><ul>{li(safety)}</ul><p>في غير الطوارئ، اطلب مراجعة اختصاصية عندما تفشل التجارب المنظمة أو تتزايد الشدة أو تتعارض الخطة مع الصحة أو التواصل أو الحركة أو التغذية أو السلامة. أحضر خط الأساس والنتائج والأسئلة المحددة لتسهيل تقييم دقيق.</p></section>
<section><h2>10. التنسيق والخصوصية والمساءلة</h2><p>عيّن منسقًا لا مالكًا للقرار. يسجل الهدف والتكييف والمؤشر وعلامات الإيقاف وموعد المراجعة. يحصل كل طرف على المعلومات اللازمة لدوره فقط، وتُحفظ البيانات الحساسة بموافقة مفهومة ووفق القانون المحلي.</p><p>وفر مسارًا آمنًا للاعتراض والشكوى، ووثق تعارض المصالح مثل توصية جهة بمنتج تبيعه. لا تقيس نجاح الخدمة بعدد الجلسات؛ المعيار هو أثرها في المشاركة والاستقلال والرفاه.</p></section>
<section><h2>11. خطة 30 يومًا</h2><div class="grid"><article class="card"><h3>الأيام 1–7</h3><p>استمع للشخص، عرّف المهمة، اجمع خط الأساس، وافحص الألم والخطر والحواجز.</p></article><article class="card"><h3>الأيام 8–14</h3><p>اختر تعديلًا واحدًا، درب الشركاء، ووثق التوقف وابدأ تجربة قصيرة.</p></article><article class="card"><h3>الأيام 15–21</h3><p>راجع القبول والعبء والمؤشرات، وعدل عنصرًا واحدًا، واختبر سياقًا ثانيًا.</p></article><article class="card"><h3>الأيام 22–30</h3><p>قرر الاستمرار أو التعديل أو الإحالة، واكتب الخطة المختصرة والمراجعة التالية.</p></article></div></section>
<section><h2>12. قائمة تحقق عملية</h2><ul>{li(checklist)}</ul></section>
<section><h2>13. أخطاء شائعة يجب تجنبها</h2><ul>{li(errors)}</ul></section>
<section class="card"><h2>14. نموذج توثيق مختصر</h2><p><strong>هدف الشخص:</strong> ________</p><p><strong>الموقف وخط الأساس:</strong> ________</p><p><strong>العائق والدليل:</strong> ________</p><p><strong>التعديل:</strong> ________</p><p><strong>المؤشر:</strong> {esc(item['measure'])}</p><p><strong>علامات الإيقاف:</strong> ________</p><p><strong>المسؤول والموعد:</strong> ________</p><p><strong>القرار:</strong> استمرار / تعديل / توقف / إحالة</p></section>
<section class="sources"><h2>15. المصادر والمنهج</h2><p>اختيرت المصادر لأنها جهات معيارية أو مهنية دولية، واستخدمت المبادئ العامة مع فصل الإرشاد العام عن القرار الفردي. الحالة: <strong>مراجعة داخلية</strong>؛ <strong>المراجعة الخارجية المتخصصة موصى بها</strong> ولم تسجل كمكتملة.</p><ul>{source_rows}</ul><p><a href="/source-registry/">سجل المصادر</a> · <a href="/trust/">الثقة والمنهج</a> · <a href="/special-needs/">القسم</a></p></section>
</main><footer><p>© Health Renewal — محتوى تثقيفي قائم على المصادر ولا يحل محل التقييم المهني.</p></footer></body></html>'''


def ensure_urlset(path: Path, urls: list[str]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    if path.is_file():
        tree, root = ET.parse(path), ET.parse(path).getroot()
        tree = ET.ElementTree(root)
        if root.tag.rsplit("}", 1)[-1] != "urlset":
            raise SystemExit(f"{path} is not a URL-set sitemap")
    else:
        root = ET.Element(f"{{{namespace}}}urlset")
        tree = ET.ElementTree(root)
    existing = {(row.findtext("{*}loc") or "").strip() for row in root.findall("{*}url")}
    added = 0
    for url in urls:
        if url in existing:
            continue
        row = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(row, f"{{{namespace}}}loc").text = url
        ET.SubElement(row, f"{{{namespace}}}lastmod").text = REVIEWED_AT
        ET.SubElement(row, f"{{{namespace}}}changefreq").text = "monthly"
        ET.SubElement(row, f"{{{namespace}}}priority").text = "0.82"
        existing.add(url); added += 1
    rows = sorted(root.findall("{*}url"), key=lambda row: row.findtext("{*}loc") or "")
    for row in list(root): root.remove(row)
    for row in rows: root.append(row)
    ET.indent(tree, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return added


def inject_hub(site: Path, section: str, items: list[dict[str, str]]) -> int:
    path = site / HUB_PATHS[section]
    if not path.is_file(): raise SystemExit(f"Missing hub for v{VERSION}: {path}")
    source = path.read_text(encoding="utf-8")
    start, end = f"<!-- undercovered-content-v{VERSION}-{section}:start -->", f"<!-- undercovered-content-v{VERSION}-{section}:end -->"
    source = re.sub(rf"{re.escape(start)}.*?{re.escape(end)}", "", source, count=1, flags=re.S)
    cards = "".join(f'<article class="card"><h3><a href="/{esc(route_for(item))}">{esc(item["title"])}</a></h3><p>{esc(item["objective"])}</p><p><small>{esc(item["audience"])}</small></p></article>' for item in items)
    block = f'\n{start}\n<section class="undercovered-v{VERSION}" aria-labelledby="undercovered-v{VERSION}-{section}-title"><h2 id="undercovered-v{VERSION}-{section}-title">{esc(SECTION_LABELS[section])}</h2><p>صفحات موسعة مبنية على إطار وظيفي وحقوقي، مع خطوات قياس وسلامة ومصادر دولية.</p><div class="grid">{cards}</div></section>\n{end}\n'
    if "</main>" in source: source = source.replace("</main>", block + "</main>", 1)
    elif "</body>" in source: source = source.replace("</body>", block + "</body>", 1)
    else: raise SystemExit(f"Cannot find insertion point in {path}")
    path.write_text(source, encoding="utf-8")
    return len(items)


def validate_catalog() -> None:
    if len(TOPICS) != 100: raise SystemExit(f"v{VERSION} must define exactly 100 pages")
    distribution = Counter(item["section"] for item in TOPICS)
    if dict(distribution) != EXPECTED_DISTRIBUTION: raise SystemExit(f"Wrong distribution: {dict(distribution)}")
    if len({item["slug"] for item in TOPICS}) != 100 or len({route_for(item) for item in TOPICS}) != 100 or len({item["title"] for item in TOPICS}) != 100: raise SystemExit("Routes, slugs and titles must be unique")
    required = {"section", "profile", "slug", "title", "objective", "setting", "audience", "risk", "measure"}
    for item in TOPICS:
        if required - set(item): raise SystemExit(f"{item.get('slug')}: missing fields")
        if item["profile"] not in PROFILE_METHODS or item["profile"] not in PROFILE_SOURCES: raise SystemExit(f"{item['slug']}: unknown profile")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["slug"]): raise SystemExit(f"{item['slug']}: invalid slug")


def publish(site: Path) -> dict[str, Any]:
    validate_catalog()
    by_section: dict[str, list[dict[str, str]]] = defaultdict(list)
    generated: list[dict[str, Any]] = []
    for item in TOPICS:
        by_section[item["section"]].append(item)
        route = route_for(item); path = site / route / "index.html"
        if path.parent.exists(): shutil.rmtree(path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        source = render_page(item); words = visible_words(source); h2_count = len(re.findall(r"<h2\b", source)); citations = source.count('rel="noopener noreferrer"')
        if words < 1200: raise SystemExit(f"{route}: thin page ({words})")
        if h2_count < 15: raise SystemExit(f"{route}: shallow hierarchy")
        if citations < 3: raise SystemExit(f"{route}: insufficient citations")
        if FORBIDDEN.search(source): raise SystemExit(f"{route}: prohibited terminology")
        if "مراجعة داخلية" not in source or "المراجعة الخارجية المتخصصة موصى بها" not in source: raise SystemExit(f"{route}: review transparency missing")
        path.write_text(source, encoding="utf-8")
        generated.append({"route": route, "path": path.relative_to(site).as_posix(), "words": words, "h2": h2_count, "citations": citations})
    hub_counts = {section: inject_hub(site, section, items) for section, items in by_section.items()}
    special_urls = [f"{BASE}/{route_for(item)}" for item in by_section["special-needs"]]
    learning_urls = [f"{BASE}/{route_for(item)}" for item in by_section["learning-paths"]]
    sector_urls = [f"{BASE}/{route_for(item)}" for section in ("child", "family", "home") for item in by_section[section]]
    sitemap_updates = {"sitemap-special-needs.xml": ensure_urlset(site / "sitemap-special-needs.xml", special_urls), "sitemap-family-special-needs.xml": ensure_urlset(site / "sitemap-family-special-needs.xml", special_urls), "sitemap-family-learning-paths.xml": ensure_urlset(site / "sitemap-family-learning-paths.xml", learning_urls), "sitemap-family-main.xml": ensure_urlset(site / "sitemap-family-main.xml", sector_urls)}
    report = {"version": VERSION, "status": "passed", "review_status": "internally-reviewed", "external_specialist_review_completed": False, "reviewed_at": REVIEWED_AT, "next_review_due": NEXT_REVIEW_DUE, "page_count": len(generated), "distribution": dict(Counter(item["section"] for item in TOPICS)), "minimum_words": min(row["words"] for row in generated), "total_words": sum(row["words"] for row in generated), "minimum_h2": min(row["h2"] for row in generated), "minimum_citations": min(row["citations"] for row in generated), "unique_routes": len({row["route"] for row in generated}), "hub_counts": hub_counts, "sitemap_updates": sitemap_updates, "source_count": len(SOURCES), "source_hosts": sorted({re.sub(r"^www\.", "", re.match(r"https://([^/]+)", source["url"]).group(1)) for source in SOURCES.values()}), "generated_pages": [row["path"] for row in generated], "routes": [row["route"] for row in generated], "quality_gates": {"functional_icf_frame": True, "rights_based_frame": True, "professional_limits_visible": True, "urgent_escalation_visible": True, "measurement_and_decision_rules": True, "inclusive_language_gate": True, "external_review_not_overstated": True, "no_client_side_network_runtime": True}}
    api = site / "api"; api.mkdir(parents=True, exist_ok=True)
    (api / f"undercovered-content-v{VERSION}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish 100 evidence-grounded Arabic pages for undercovered sectors.")
    parser.add_argument("site", type=Path); args = parser.parse_args(); site = args.site.resolve()
    if not site.is_dir(): raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
