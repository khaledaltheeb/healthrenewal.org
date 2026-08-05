#!/usr/bin/env python3
"""Institutional expansion, governance, and deduplication for the academic library."""
from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import publish_academic_library_v326 as academic

VERSION = 400
ORIGIN = "https://healthrenewal.org"
REVIEWED_AT = "2026-08-05"
NEXT_REVIEW = "2027-02-05"
MIN_WORDS = 1000
MIN_REFS = 6


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "svg", "template", "noscript"}:
            self.hidden.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and self.hidden[-1] == tag.lower():
            self.hidden.pop()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def words(source: str) -> int:
    parser = VisibleText()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def li(values: list[str]) -> str:
    return "".join(f"<li>{e(value)}</li>" for value in values)


EXTRA_SOURCES = {
    "NICE_BPD": ("NICE", "Borderline personality disorder: recognition and management CG78", "https://www.nice.org.uk/guidance/cg78"),
    "NICE_ALCOHOL": ("NICE", "Alcohol-use disorders: diagnosis, assessment and management CG115", "https://www.nice.org.uk/guidance/cg115"),
    "PRISMA_CHECKLIST": ("PRISMA", "PRISMA 2020 checklist", "https://www.prisma-statement.org/prisma-2020-checklist"),
    "PRISMA_STATEMENT": ("PRISMA", "PRISMA 2020 statement", "https://www.prisma-statement.org/prisma-2020"),
    "EQUATOR_HOME": ("EQUATOR Network", "Reporting guidelines for health research", "https://www.equator-network.org/"),
    "CONSORT_2025": ("CONSORT", "CONSORT 2025 statement", "https://www.equator-network.org/reporting-guidelines/consort/"),
    "STROBE_HOME": ("STROBE Initiative", "STROBE statement", "https://www.strobe-statement.org/"),
    "COSMIN_TOOLS": ("COSMIN", "Measurement-property tools and instrument selection", "https://www.cosmin.nl/cosmin-tools/"),
    "WHO_GUIDELINES": ("منظمة الصحة العالمية", "WHO handbook for guideline development", "https://www.who.int/publications/i/item/9789241548960"),
}
SOURCES = {**academic.SOURCES, **EXTRA_SOURCES}
DEFAULT_REFS = {
    "branches": ["APA_DIV", "APA_ETHICS", "APA_JARS", "TESTING", "COSMIN", "WHO_ICF"],
    "therapies": ["WHO_MHGAP", "COCHRANE", "GRADE", "APA_ETHICS", "AGREE", "WHO_GUIDELINES"],
    "research": ["COCHRANE", "EQUATOR", "APA_JARS", "GRADE", "COSMIN", "TESTING"],
}
SLUG_REFS = {
    "cognitive-behavioral-therapy": ["NICE_DEP", "NICE_GAD", "NICE_OCD", "NICE_PTSD"],
    "dialectical-behavior-therapy": ["NICE_BPD"],
    "motivational-interviewing": ["NICE_ALCOHOL"],
    "exposure-response-prevention": ["NICE_OCD"],
    "eye-movement-desensitization-reprocessing": ["NICE_PTSD"],
    "trauma-focused-cbt": ["NICE_PTSD"],
    "family-therapy": ["NICE_PSY", "NICE_ED"],
    "systematic-review": ["PRISMA_CHECKLIST", "PRISMA_STATEMENT", "EQUATOR_HOME"],
    "meta-analysis": ["PRISMA_CHECKLIST", "PRISMA_STATEMENT"],
    "randomized-controlled-trial": ["CONSORT_2025", "EQUATOR_HOME"],
    "cross-sectional-study": ["STROBE_HOME", "EQUATOR_HOME"],
    "psychometrics": ["COSMIN_TOOLS"],
    "psychometric-validation": ["COSMIN_TOOLS"],
}
EVIDENCE_NOTES = {
    "cognitive-behavioral-therapy": "تظهر صيغ العلاج المعرفي السلوكي في إرشادات للاكتئاب والقلق والوسواس القهري واضطراب ما بعد الصدمة، لكن المكونات والمدة والسكان تختلف؛ لا تنقل توصية من اضطراب إلى آخر تلقائيًا.",
    "dialectical-behavior-therapy": "تذكر NICE في CG78 النظر في برنامج شامل للعلاج السلوكي الجدلي لدى النساء المصابات باضطراب الشخصية الحدية عندما يكون خفض إيذاء النفس المتكرر أولوية، مع مراقبة طيف واسع من النتائج.",
    "motivational-interviewing": "تتضمن NICE CG115 تدخلًا تحفيزيًا في التقييم الأولي لاضطرابات استخدام الكحول بعناصر حل التردد ودعم التغيير بأسلوب غير تصادمي، لكنه لا يغني وحده عن خطة رعاية ملائمة للشدة والحالات المصاحبة.",
    "systematic-review": "PRISMA 2020 معيار للإبلاغ وليس أداةً منفردة للحكم على الجودة؛ يلزم فحص البروتوكول والبحث والاختيار وخطر التحيز وملاءمة التركيب ويقين الدليل.",
    "randomized-controlled-trial": "CONSORT يحسن اكتمال الإبلاغ، لكن صلاحية الاستنتاج تتطلب فحص التسلسل وإخفاء التخصيص والانحرافات والبيانات المفقودة وانتقائية الإبلاغ وعدم الدقة.",
    "psychometrics": "تبدأ منهجية COSMIN بتعريف البنية والغرض والسكان، ثم تفحص صدق المحتوى والبنية والثبات وخطأ القياس والاستجابة للتغير والإنصاف وقابلية التفسير.",
}
ALIASES = {
    "therapies": {
        "إزالة التحسس بحركة العين": "إزالة التحسس وإعادة المعالجة بحركات العين",
        "العلاج القائم على التعاطف": "العلاج المتمركز حول التعاطف",
        "العلاج المخططاتي": "العلاج بالمخططات",
        "العلاج بالقبول والالتزام": "علاج القبول والالتزام",
        "العلاج بين الشخصي": "العلاج النفسي بين الأشخاص",
    },
    "branches": {
        "علم النفس الإكلينيكي": "علم النفس السريري",
        "علم النفس الصحي": "علم نفس الصحة",
        "علم النفس المجتمعي": "علم نفس المجتمع",
    },
    "research": {"التحليل البعدي": "التحليل التلوي"},
}


def ref_ids(section: str, item: dict) -> list[str]:
    result: list[str] = []
    for sid in [*item["refs"], *DEFAULT_REFS[section], *SLUG_REFS.get(item["slug"], [])]:
        if sid in SOURCES and sid not in result:
            result.append(sid)
    return result


def refs_html(ids: list[str]) -> str:
    rows = []
    for sid in ids:
        org, title, url = SOURCES[sid]
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit({"invalid_source": sid, "url": url})
        rows.append(f'<li><b>{e(org)}</b>: <a href="{e(url)}" rel="noopener noreferrer">{e(title)}</a> <small>— تحقق {REVIEWED_AT}</small></li>')
    return "".join(rows)


COMMON_PARAGRAPHS = {
    "boundaries": "لا يكفي الاسم وحده لاتخاذ قرار مهني أو سريري أو بحثي. يجب تحديد السكان والسياق والغرض والنتيجة والحدود القانونية والمنهجية. ويجب فصل التثقيف العام عن التقييم الفردي، وفصل النظرية عن الدليل التجريبي، وفصل شيوع الاستخدام عن ثبوت المنفعة.",
    "measurement": "اختيار الأداة يبدأ بتعريف البنية المراد قياسها والغرض والسكان، ثم فحص صدق المحتوى والبنية والثبات وخطأ القياس والاستجابة للتغير والإنصاف والملاءمة اللغوية والثقافية. لا تفسر الدرجة خارج الغرض والسكان اللذين تحققت فيهما خصائص الأداة.",
    "evidence": "تقرأ الأدلة عبر تصميم الدراسة، وخطر التحيز، وحجم الأثر، وفاصل الثقة، والنتائج المطلقة، والانسحاب والأضرار، ومدة المتابعة، واتساق الدراسات وملاءمتها للسياق. الدلالة الإحصائية لا تساوي أهمية عملية، وغياب الدلالة لا يثبت غياب الأثر.",
    "ethics": "تشمل الحوكمة الموافقة المستنيرة والخصوصية وتقليل الضرر والعدالة وعدم التمييز وحدود السرية والإحالة وحماية البيانات. ويجب الإفصاح عن التمويل وتعارض المصالح والانحراف عن الخطة، وإتاحة التصحيح وسجل التحديث.",
    "arabic": "التكييف العربي ليس ترجمة لغوية فقط؛ يلزم فحص معنى المفهوم ومستوى القراءة والاستجابة الاجتماعية وصلاحية المعايير المرجعية وثبات القياس بين المجموعات وإمكان الوصول. يجب إشراك المستفيدين والممارسين وعدم الادعاء بمعيار عربي شامل عندما تكون العينة محلية أو محدودة.",
    "uncertainty": "يجب فصل ما هو مؤكد عما هو مرجح وما لا يزال مجهولًا، وعرض النتائج المتعارضة والفئات قليلة التمثيل والنتائج بعيدة المدى. الصفحة المرجعية الجيدة لا تخفي عدم اليقين، بل تجعله جزءًا من القرار وتحدد متى يلزم تحديث المحتوى.",
}


def panel(anchor: str, title: str, content: str, klass: str = "panel") -> str:
    return f'<section class="{klass}" id="{e(anchor)}"><h2>{e(title)}</h2>{content}</section>'


def branch_content(item: dict) -> tuple[str, list[tuple[str, str]]]:
    sections = [
        ("definition", "التعريف والنطاق", f"<p>{e(item['definition'])}</p><p>{COMMON_PARAGRAPHS['boundaries']}</p>"),
        ("questions", "الأسئلة المركزية", f"<ul>{li(item['focus'])}</ul><p>تحول الأسئلة الواسعة إلى فرضيات أو أسئلة قابلة للاختبار تحدد السكان والمتغيرات والزمن والسياق. وكلما اتسع الادعاء وجب توسيع المنهج والعينة والمقارنة قبل التعميم.</p>"),
        ("theory", "الأطر النظرية ومستويات التفسير", "<p>قد يفسر المجال الظاهرة على مستوى الفرد أو العلاقة أو المؤسسة أو الثقافة أو الجهاز العصبي. لا يلغي مستوىٌ مستوىً آخر. وتقارن النظريات بوضوح مفاهيمها وقابليتها للقياس والتنبؤ والدحض والتكرار، لا بشهرتها التاريخية.</p>"),
        ("methods", "مناهج البحث والقياس", f"<ul>{li(item['methods'])}</ul><p>{COMMON_PARAGRAPHS['measurement']}</p>"),
        ("applications", "التطبيقات المؤسسية", f"<ul>{li(item['uses'])}</ul><p>التطبيق الجيد يحدد المشكلة وخط الأساس ومؤشرات النجاح والمسؤول والموارد والأثر غير المقصود وموعد المراجعة، ويختبر قابلية النقل بدل افتراض أن ما نجح في بيئة سينجح في كل بيئة.</p>"),
        ("training", "التأهيل والكفاءة", "<p>المعرفة بالمجال لا تساوي الترخيص بالممارسة. يتطلب العمل المهني تأهيلًا معترفًا به، وتدريبًا عمليًا وإشرافًا وكفاءة في الأخلاقيات والتقييم والتواصل والإحالة والتوثيق. تختلف المتطلبات النظامية بين الدول ويجب التحقق منها محليًا.</p>"),
        ("ethics", "الأخلاقيات والإنصاف", f"<p>{COMMON_PARAGRAPHS['ethics']}</p><p>يجب فحص التحيز في العينات والمقاييس والخوارزميات، وتجنب تحويل فرق جماعي إلى حكم فردي أو استخدام مصطلح علمي لتبرير الوصم.</p>"),
        ("limits", "الحدود والأخطاء الشائعة", f"<ul>{li(item['limits'])}</ul><p>من الأخطاء مساواة الارتباط بالسببية، واعتبار أداة واحدة تشخيصًا، وتجاهل معدلات الخطأ، وتعميم نتيجة من عينة ضيقة، وانتقاء الدراسات التي توافق موقفًا مسبقًا.</p>"),
        ("arabic", "السياق العربي والتكييف", f"<p>{COMMON_PARAGRAPHS['arabic']}</p>"),
        ("evidence", "حالة الدليل", f"<p>{COMMON_PARAGRAPHS['evidence']}</p>"),
        ("agenda", "أجندة البحث المفتوحة", f"<p>تشمل الأولويات دراسات طولية أكبر، وتكرار النتائج، وتمثيل المجتمعات العربية، وقياس الوظيفة وجودة الحياة لا الأعراض فقط، واختبار الإنصاف والآليات والتطبيق الواقعي.</p><p>{COMMON_PARAGRAPHS['uncertainty']}</p>"),
    ]
    return "".join(panel(*s) for s in sections), [(a, t) for a, t, _ in sections]


def therapy_content(item: dict) -> tuple[str, list[tuple[str, str]]]:
    note = EVIDENCE_NOTES.get(item["slug"], COMMON_PARAGRAPHS["evidence"])
    sections = [
        ("definition", "التعريف والحدود السريرية", f"<p>{e(item['definition'])}</p><p>{COMMON_PARAGRAPHS['boundaries']}</p>"),
        ("model", "نموذج التغير وصياغة الحالة", f"<ul>{li(item['focus'])}</ul><p>تربط صياغة الحالة بين المشكلة والعوامل المهيئة والمطلقة والمحافظة وعوامل الحماية، وتحولها إلى أهداف قابلة للملاحظة والقياس. النموذج فرضية عمل مشتركة تراجع مع البيانات وليس حكمًا نهائيًا على الشخص.</p>"),
        ("assessment", "التقييم قبل العلاج", "<p>يشمل التقييم سبب طلب المساعدة وشدة الأعراض والأداء وإيذاء النفس أو الآخرين وتعاطي المواد والصحة الجسدية والأدوية والصدمات والدعم والعوائق. ويحدد الحاجة العاجلة والتشخيص التفريقي وما إذا كان التدخل منفردًا أو ضمن فريق متعدد التخصصات.</p>"),
        ("structure", "البنية والمكونات", f"<ul>{li(item['methods'])}</ul><p>تحدد الخطة الأهداف والأدوار والمدة وطريقة متابعة النتائج وما سيحدث عند التدهور أو الانقطاع. العلاقة العلاجية والموافقة والوضوح والالتزام بالنموذج مع مرونة مسؤولة عناصر أساسية وليست إضافات شكلية.</p>"),
        ("uses", "الاستخدامات وحدود التعميم", f"<ul>{li(item['uses'])}</ul><p>وجود استخدام شائع لا يثبت الملاءمة لكل عمر أو شدة أو حالة مصاحبة. يجب الرجوع إلى الإرشاد الخاص بالحالة وفحص المقارنة والنتيجة والمتابعة وعدم تعميم دليل بالغين على الأطفال أو نتيجة أعراض على جودة الحياة بلا سند.</p>"),
        ("evidence", "حالة الدليل", f"<p>{e(note)}</p><p>{COMMON_PARAGRAPHS['evidence']}</p>"),
        ("safety", "السلامة والاحتياطات", "<p>تحتاج الخطة إلى مسار لتقييم الخطر والاستجابة للتدهور وتنسيق الرعاية عند وجود دواء أو مرض جسدي أو تعاطٍ أو عنف أو احتياج اجتماعي. توثق المنافع والأضرار والحضور والانقطاع والتغير الوظيفي، وتراجع الخطة عند غياب التقدم أو ظهور ضرر.</p>"),
        ("adaptation", "التكييف والإتاحة", f"<p>{COMMON_PARAGRAPHS['arabic']}</p><p>قد يلزم تبسيط اللغة أو استخدام مواد بصرية أو تعديل السرعة والمدة أو إشراك داعم بموافقة الشخص. يحافظ التكييف على الوظيفة العلاجية الأساسية ولا يتحول إلى حذف عشوائي للمكونات.</p>"),
        ("decision", "القرار المشترك والبدائل", "<p>تناقش المنافع وعدم اليقين والبدائل والوقت والتكلفة والخصوصية ومتطلبات المشاركة وخيارات التوقف. الموافقة عملية مستمرة وتجدد عند تغير الخطة أو المخاطر أو طريقة التقديم.</p>"),
        ("competence", "كفاءة مقدم الخدمة", "<p>يتطلب التطبيق تدريبًا نظريًا وعمليًا وإشرافًا ومراجعة للالتزام والكفاءة ومعرفة بالمخاطر والإحالة. لا تكفي قراءة دليل أو دورة قصيرة لتقديم تدخل معقد أو العمل مع خطر مرتفع.</p>"),
        ("limits", "الموانع النسبية والأخطاء", f"<ul>{li(item['limits'])}</ul><p>ومن الأخطاء تقديم العلاج كوصفة واحدة، وتجاهل رغبة الشخص، واستخدام التعرض أو معالجة الصدمة دون إعداد وأمان، وقياس الأعراض دون الوظيفة، وإخفاء ضعف الدليل، أو الاستمرار رغم الضرر.</p>"),
        ("implementation", "التنفيذ ومؤشرات الجودة", "<p>يحدد البرنامج السكان ومعايير الدخول والخروج ومسار الأزمات والإشراف ومقاييس النتائج والأضرار والعدالة وأوقات الانتظار. تفسر البيانات المفقودة والانقطاع، وتراجع الجودة من منظور المستفيدين ومقدمي الخدمة.</p>"),
        ("uncertainty", "الفجوات وعدم اليقين", f"<p>{COMMON_PARAGRAPHS['uncertainty']}</p><p>قد تبقى أسئلة عن الجرعة والمكونات الفعالة والنتائج بعيدة المدى والفئات قليلة التمثيل والتطبيق الرقمي والتكلفة والمقارنات المباشرة.</p>"),
    ]
    return "".join(panel(a, t, c, "panel limits" if a == "limits" else "panel") for a, t, c in sections), [(a, t) for a, t, _ in sections]


def research_content(item: dict) -> tuple[str, list[tuple[str, str]]]:
    note = EVIDENCE_NOTES.get(item["slug"], COMMON_PARAGRAPHS["evidence"])
    sections = [
        ("definition", "التعريف والسؤال المناسب", f"<p>{e(item['definition'])}</p><p>{COMMON_PARAGRAPHS['boundaries']}</p>"),
        ("concepts", "المفاهيم والأسئلة", f"<ul>{li(item['focus'])}</ul><p>تحدد الوحدة التحليلية والسكان والتعرض أو التدخل والمقارنة والنتيجة والزمن والسياق قبل جمع البيانات. ويفصل التحليل التأكيدي عن الاستكشافي وتحدد النتائج الأساسية مسبقًا عند الملاءمة.</p>"),
        ("workflow", "سير العمل", "<ol><li>تحديد السؤال والمبرر.</li><li>اختيار التصميم والتحليل.</li><li>تعريف السكان والمتغيرات والنتائج.</li><li>تقدير العينة والموارد.</li><li>الموافقة والتسجيل.</li><li>جمع البيانات وضبط الجودة.</li><li>التحليل والحساسية.</li><li>الإبلاغ والمواد القابلة للمشاركة.</li></ol><p>أي تعديل بعد رؤية النتائج يوثق ويبرر.</p>"),
        ("sampling", "العينة والقوة", "<p>توضح طريقة الوصول وإطار المعاينة ومعايير الاشتمال والاستبعاد والاستجابة والانسحاب. العينة الكبيرة لا تصلح تحيز الاختيار. يعتمد الحجم على الأثر ذي المعنى والتباين والتصميم والفقد والدقة، وتعرض فواصل الثقة بدل استخدام القوة اللاحقة.</p>"),
        ("measurement", "المتغيرات والقياس", f"<ul>{li(item['methods'])}</ul><p>{COMMON_PARAGRAPHS['measurement']}</p>"),
        ("bias", "التحيز والإرباك", "<p>تفحص أخطاء الاختيار والقياس والتذكر والمراقب والانحراف والبيانات المفقودة وانتقائية النتائج. يحدد اتجاه التحيز المتوقع، وتستخدم معرفة سببية لتجنب الضبط الآلي لكل متغير أو الضبط لوسيط أو مصادم.</p>"),
        ("analysis", "التحليل والافتراضات", "<p>تختار الطريقة وفق نوع النتيجة وبنية البيانات والعناقيد والتكرار والزمن. تفحص الافتراضات وتبلغ التحويلات والتفاعلات والتحليلات الفرعية، ويعرض التقدير وحجم الأثر وفاصل الثقة والمخاطر المطلقة عند الملاءمة.</p>"),
        ("missing", "البيانات المفقودة", "<p>يبلغ مقدار الفقد وأسبابه وتوقيته واختلافه بين المجموعات. تناقش آلية الفقد وتجرى تحليلات حساسية. الحذف الكامل قد يسبب تحيزًا وفقد قوة، وقد تناسب الإكمالات المتعددة أو النماذج الأخرى عندما تكون افتراضاتها معقولة.</p>"),
        ("interpretation", "التفسير وحدود الاستنتاج", f"<ul>{li(item['uses'])}</ul><p>{e(note)}</p><p>{COMMON_PARAGRAPHS['evidence']}</p>"),
        ("reporting", "الإبلاغ والشفافية", "<p>تستخدم إرشادات EQUATOR المناسبة للتصميم، وينشر البروتوكول وخطة التحليل والانحرافات. إرشادات الإبلاغ لا تصلح تصميمًا ضعيفًا؛ تجمع مع تقييم خطر التحيز وملاءمة التحليل ويقين الدليل وقابلية التكرار.</p>"),
        ("example", "مثال تطبيقي", f"<p>في سؤال متعلق بـ«{e(item['title'])}» يحدد الباحث السكان والنتيجة والزمن، ويختار التصميم الذي يسمح بالاستنتاج المطلوب، ويوثق الاستبعاد والقياس والتحليل الأساسي والبيانات المفقودة. بعد التحليل يعرض التقدير وعدم اليقين ويصوغ خلاصة لا تتجاوز البيانات.</p>"),
        ("limits", "الأخطاء الشائعة", f"<ul>{li(item['limits'])}</ul><p>ومن الأخطاء تغيير النتيجة بعد رؤية البيانات، وتعدد الاختبارات بلا شفافية، وإخفاء الانسحابات، واستخدام لغة سببية في تصميم لا يسمح بها، وعدم نشر النتائج غير المرغوبة.</p>"),
        ("checklist", "قائمة فحص الاعتماد", "<ul><li>هل السؤال والتصميم متطابقان؟</li><li>هل العينة واختيارها واضحان؟</li><li>هل القياس صالح؟</li><li>هل التحيز والإرباك والفقد عولجت؟</li><li>هل التحليل مخطط وافتراضاته مفحوصة؟</li><li>هل عرض الأثر وعدم اليقين؟</li><li>هل الخلاصة لا تتجاوز الدليل؟</li><li>هل اتبعت إرشادات الإبلاغ؟</li></ul>"),
        ("arabic", "التكييف والسياق العربي", f"<p>{COMMON_PARAGRAPHS['arabic']}</p>"),
    ]
    return "".join(panel(a, t, c, "panel limits" if a == "limits" else "panel") for a, t, c in sections), [(a, t) for a, t, _ in sections]


def governance(section: str, refs: list[str]) -> str:
    return panel("governance", "بطاقة التحرير والحوكمة العلمية", f'''<dl class="governance-grid"><div><dt>المسؤول التحريري</dt><dd>هيئة تحرير منصة روافد</dd></div><div><dt>حالة المراجعة</dt><dd>مراجعة داخلية؛ المراجعة الخارجية المستقلة لم تكتمل</dd></div><div><dt>آخر بحث وتحقق</dt><dd>{REVIEWED_AT}</dd></div><div><dt>المراجعة التالية</dt><dd>{NEXT_REVIEW} أو عند تغير جوهري</dd></div><div><dt>نوع الصفحة</dt><dd>{e(academic.SECTIONS[section]['title'])}</dd></div><div><dt>المراجع الأساسية</dt><dd>{len(refs)}</dd></div></dl><p><b>المنهج:</b> تعريف منضبط، وأسئلة وحدود، وتطبيق أو تصميم، ثم ربط بمصادر مؤسسية أصلية. لا يوصف الادعاء بأنه مؤكد إلا بما تسمح به جودة الدليل واتساقه ودقته.</p><p><b>الاستقلال التحريري:</b> لا توجد رعاية تجارية. يمكن الإبلاغ عن خطأ من صفحة <a href="/trust/">منهج الثقة والمراجعة</a>.</p>''', "panel governance")


def render(section_slug: str, section: dict, item: dict) -> tuple[str, int, int]:
    canonical = f"{ORIGIN}/library/{section_slug}/{item['slug']}/"
    description = f"مرجع عربي مؤسسي موسع حول {item['title']} ({item['english']}): التعريف والمنهج والتطبيق والدليل والأخلاقيات والحدود والمراجع الأصلية."
    refs = ref_ids(section_slug, item)
    if len(refs) < MIN_REFS:
        raise SystemExit({"few_references": item["slug"], "count": len(refs)})
    content_fn = {"branches": branch_content, "therapies": therapy_content, "research": research_content}[section_slug]
    content, toc_items = content_fn(item)
    toc_items.extend([("governance", "الحوكمة"), ("sources", "المراجع"), ("revision", "سجل الإصدار")])
    toc = "".join(f'<a href="#{e(anchor)}">{e(label)}</a>' for anchor, label in toc_items)
    schema = {"@context": "https://schema.org", "@graph": [{"@type": "Article", "@id": canonical + "#article", "headline": item["title"], "alternativeHeadline": item["english"], "description": description, "url": canonical, "inLanguage": "ar", "datePublished": REVIEWED_AT, "dateModified": REVIEWED_AT, "author": {"@type": "Organization", "name": "هيئة تحرير منصة روافد", "url": ORIGIN + "/trust/"}, "publisher": {"@type": "Organization", "name": "منصة روافد", "url": ORIGIN + "/"}, "citation": [SOURCES[sid][2] for sid in refs]}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": ORIGIN + "/"}, {"@type": "ListItem", "position": 2, "name": "المكتبة", "item": ORIGIN + "/library/"}, {"@type": "ListItem", "position": 3, "name": section["title"], "item": f"{ORIGIN}/library/{section_slug}/"}, {"@type": "ListItem", "position": 4, "name": item["title"], "item": canonical}]}]}
    clinical = '<div class="notice"><b>حدود سريرية:</b> لا تختار الصفحة علاجًا لشخص بعينه ولا تجيز التطبيق دون تقييم وتدريب وإشراف وخطة سلامة.</div>' if section_slug == "therapies" else ""
    source_box = panel("sources", "المراجع والمعايير الأصلية", f'<p>رتبت الأولوية للمصادر المؤسسية والإرشادات والمعايير. وجود المصدر لا يعني أنه يؤيد كل تطبيق محلي؛ ارجع إلى النص الأصلي وتحديثاته.</p><ol class="sources">{refs_html(refs)}</ol>', "source-box")
    revision = panel("revision", "سجل الإصدار", f"<p><b>v{VERSION} — {REVIEWED_AT}:</b> توسعة المدخل إلى قالب مرجعي، وإضافة حوكمة ودليل وأخلاقيات وتكييف عربي ومراجع قابلة للتتبع. المراجعة الخارجية المتخصصة ما زالت مطلوبة قبل اعتماده مادة تدريبية رسمية.</p>")
    body = f'''<body>{academic.site_header()}<main id="content"><section class="hero"><div class="wrap"><p class="crumbs"><a href="/library/">المكتبة</a> ← <a href="/library/{e(section_slug)}/">{e(section['title'])}</a></p><div class="meta"><span class="tag">مرجع مؤسسي v{VERSION}</span><span class="tag">آخر تحقق: {REVIEWED_AT}</span><span class="tag">المراجعة التالية: {NEXT_REVIEW}</span></div><h1>{e(item['title'])}</h1><p class="english">{e(item['english'])}</p><p class="lead">{e(item['definition'])}</p>{clinical}</div></section><div class="wrap layout"><aside class="panel toc"><b>محتويات الصفحة</b>{toc}<a href="/library/{e(section_slug)}/">العودة إلى القسم</a></aside><article class="stack">{content}{governance(section_slug, refs)}{source_box}{revision}</article></div></main>{academic.footer()}'''
    page = academic.head(item["title"], description, canonical, schema) + body
    count = words(page)
    if count < MIN_WORDS or page.count("<h1") != 1 or page.count("governance-grid") != 1:
        raise SystemExit({"reference_page_failed": canonical, "words": count})
    return page, count, len(refs)


def h1(source: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", source, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(match.group(1)))).strip() if match else ""


def redirect_page(old_title: str, target_title: str, target: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تم دمج المدخل | منصة روافد</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="{ORIGIN}{e(target)}"><meta http-equiv="refresh" content="0;url={e(target)}"><style>{academic.STYLE}</style><script>location.replace({json.dumps(target, ensure_ascii=False)});</script></head><body>{academic.site_header()}<main id="content"><section class="hero"><div class="wrap"><h1>تم دمج هذا المدخل</h1><p class="lead">أصبح «{e(old_title)}» اسمًا بديلًا داخل الصفحة المرجعية «{e(target_title)}» لمنع التكرار وتعارض التحديثات.</p><a class="button" href="{e(target)}">فتح الصفحة المرجعية</a></div></section></main>{academic.footer()}'''


def deduplicate(site: Path) -> list[dict[str, str]]:
    redirects = []
    for section_slug, section in academic.SECTIONS.items():
        title_map = {item["title"]: item for item in section["entries"]}
        for path in sorted((site / "library" / section_slug).glob(f"{section_slug}-*/index.html")):
            old = h1(path.read_text(encoding="utf-8"))
            target_title = old if old in title_map else ALIASES.get(section_slug, {}).get(old)
            if not target_title or target_title not in title_map:
                continue
            target = f"/library/{section_slug}/{title_map[target_title]['slug']}/"
            path.write_text(redirect_page(old, target_title, target), encoding="utf-8")
            redirects.append({"source": "/" + path.parent.relative_to(site).as_posix().strip("/") + "/", "title": old, "target": target, "canonical_title": target_title})
    return redirects


def description(source: str) -> str:
    match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', source, flags=re.I)
    return html.unescape(match.group(1)).strip() if match else "مدخل عربي من المكتبة الأكاديمية لمنصة روافد."


def rebuild_all_pages(site: Path) -> int:
    entries = []
    for section_slug in academic.SECTIONS:
        for path in sorted((site / "library" / section_slug).glob("*/index.html")):
            source = path.read_text(encoding="utf-8")
            if 'name="robots" content="noindex' in source:
                continue
            title = h1(source)
            if title:
                entries.append({"title": title, "route": "/" + path.parent.relative_to(site).as_posix().strip("/") + "/", "description": description(source)})
    evidence = site / "library" / "evidence-literacy"
    if evidence.is_dir():
        for path in sorted(evidence.glob("*/index.html")):
            source = path.read_text(encoding="utf-8")
            title = h1(source)
            if title:
                entries.append({"title": title, "route": "/" + path.parent.relative_to(site).as_posix().strip("/") + "/", "description": description(source)})
    entries = sorted({item["route"]: item for item in entries}.values(), key=lambda item: (item["title"], item["route"]))
    cards = "".join(f'<article class="card" data-search="{e(item["title"] + " " + item["description"])}"><h2>{e(item["title"])}</h2><p>{e(item["description"])}</p><a class="button" href="{e(item["route"])}">فتح الصفحة المرجعية</a></article>' for item in entries)
    canonical = ORIGIN + "/library/all-pages/"
    desc = f"الفهرس المنقح للمكتبة الأكاديمية: {len(entries)} صفحة فريدة بعد دمج المسارات المكررة وربط الأسماء البديلة بصفحات مرجعية واحدة."
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "الفهرس الكامل للمكتبة الأكاديمية", "description": desc, "url": canonical, "inLanguage": "ar", "dateModified": REVIEWED_AT, "numberOfItems": len(entries)}
    page = academic.head("الفهرس الكامل: المكتبة الأكاديمية", desc, canonical, schema) + f'''<body>{academic.site_header()}<main id="content"><section class="hero"><div class="wrap"><p class="crumbs"><a href="/library/">العودة إلى المكتبة</a></p><span class="tag">منقح v{VERSION}</span><h1>الفهرس الكامل للمكتبة الأكاديمية</h1><p class="lead">جميع الصفحات الفريدة بعد دمج العناوين المتطابقة والمتغيرات اللغوية الواضحة. العدد: <b>{len(entries)}</b>.</p><label for="all-search"><b>ابحث داخل الفهرس</b></label><br><input id="all-search" class="search" type="search" placeholder="اكتب مصطلحًا عربيًا أو إنجليزيًا"></div></section><section class="wrap grid" id="cards">{cards}</section></main><script>const q=document.getElementById('all-search'),cards=[...document.querySelectorAll('[data-search]')];q?.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase();cards.forEach(c=>c.hidden=v&&!c.dataset.search.toLowerCase().includes(v));}});</script>{academic.footer()}'''
    target = site / "library" / "all-pages" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return len(entries)


def enhance(site: Path) -> dict:
    site = site.resolve()
    word_map = {}
    ref_map = {}
    for section_slug, section in academic.SECTIONS.items():
        for item in section["entries"]:
            path = site / "library" / section_slug / item["slug"] / "index.html"
            if not path.parent.is_dir():
                raise SystemExit({"missing_entry": str(path.parent)})
            page, count, refs = render(section_slug, section, item)
            path.write_text(page, encoding="utf-8")
            route = f"/library/{section_slug}/{item['slug']}/"
            word_map[route] = count
            ref_map[route] = refs
    redirects = deduplicate(site)
    unique_pages = rebuild_all_pages(site)
    expected = sum(len(section["entries"]) for section in academic.SECTIONS.values())
    report = {
        "version": VERSION,
        "status": "passed",
        "reviewed_at": REVIEWED_AT,
        "next_review_due": NEXT_REVIEW,
        "generated_reference_pages": len(word_map),
        "minimum_entry_words": min(word_map.values()),
        "minimum_references": min(ref_map.values()),
        "duplicate_and_alias_redirects": len(redirects),
        "redirects": redirects,
        "all_pages_unique_entries": unique_pages,
        "source_registry_size": len(SOURCES),
        "external_specialist_review_completed": False,
        "editorial_governance_present": True,
    }
    if len(word_map) != expected or report["minimum_entry_words"] < MIN_WORDS or report["minimum_references"] < MIN_REFS:
        raise SystemExit({"academic_reference_contract_failed": report})
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "academic-library-reference-v400.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(enhance(args.site), ensure_ascii=False, indent=2))
