#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 224
MIN_WORDS = 650
MARKER = "data-term-depth-v224"
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")

SOURCES = {
    "clinical": (
        ("منظمة الصحة العالمية — الدليل السريري لـ ICD-11", "https://www.who.int/publications/i/item/9789240077263"),
        ("منظمة الصحة العالمية — الاضطرابات النفسية", "https://www.who.int/news-room/fact-sheets/detail/mental-disorders"),
        ("NICE — الصحة النفسية والحالات النمائية العصبية", "https://www.nice.org.uk/guidance/conditions-and-diseases/mental-health-behavioural-and-neurodevelopmental-conditions"),
    ),
    "cognitive": (
        ("الجمعية الأمريكية لعلم النفس — موضوعات علم النفس", "https://www.apa.org/topics"),
        ("المعهد الوطني للشيخوخة — الصحة المعرفية", "https://www.nia.nih.gov/health/brain-health/cognitive-health-and-older-adults"),
        ("معايير الاختبارات AERA/APA/NCME", "https://www.testingstandards.net/"),
    ),
    "behavioral": (
        ("الجمعية الأمريكية لعلم النفس — موضوعات علم النفس", "https://www.apa.org/topics"),
        ("NICE — الإرشادات الصحية والسلوكية", "https://www.nice.org.uk/guidance"),
        ("دليل كوكرين للمراجعات المنهجية", "https://training.cochrane.org/handbook"),
    ),
    "personality": (
        ("الجمعية الأمريكية لعلم النفس — الشخصية", "https://www.apa.org/topics/personality"),
        ("معايير الاختبارات AERA/APA/NCME", "https://www.testingstandards.net/"),
        ("COSMIN — خصائص أدوات القياس", "https://www.cosmin.nl/"),
    ),
    "intervention": (
        ("NICE — الإرشادات العلاجية", "https://www.nice.org.uk/guidance"),
        ("منظمة الصحة العالمية — التدخلات النفسية", "https://www.who.int/teams/mental-health-and-substance-use/treatment-care/mental-health-gap-action-programme"),
        ("دليل كوكرين للمراجعات المنهجية", "https://training.cochrane.org/handbook"),
    ),
    "measurement": (
        ("معايير الاختبارات AERA/APA/NCME", "https://www.testingstandards.net/"),
        ("COSMIN — خصائص أدوات القياس", "https://www.cosmin.nl/"),
        ("دليل كوكرين للمراجعات المنهجية", "https://training.cochrane.org/handbook"),
    ),
    "psychosocial": (
        ("منظمة الصحة العالمية — تعزيز الصحة النفسية", "https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response"),
        ("منظمة الصحة العالمية — الرعاية الذاتية", "https://www.who.int/health-topics/self-care"),
        ("اليونيسف — الصحة النفسية ورفاه الأسرة", "https://www.unicef.org/parenting/mental-health-and-well-being"),
    ),
}

CATEGORY_PROFILE = {
    "المزاج": "clinical", "القلق والخوف": "clinical", "الوسواس والصدمة": "clinical",
    "الإدراك والذهان": "clinical", "النمو العصبي": "clinical", "النوم والجسد": "clinical",
    "المعرفة والذاكرة": "cognitive", "الدافعية والسلوك": "behavioral", "الشخصية": "personality",
    "العلاج النفسي": "intervention", "البحث والقياس": "measurement", "مدارس ومناهج": "measurement",
    "العلاقات والنمو": "psychosocial", "المهارات الحياتية": "psychosocial",
    "الوقاية والمجتمع": "psychosocial", "العمل والمجتمع": "psychosocial", "الأساسيات": "psychosocial",
}

PROFILE_COPY = {
    "clinical": {
        "scope": "يُقرأ هذا المفهوم ضمن الزمن والشدة والتكرار والسياق والأثر الوظيفي. قد يكون الاسم تشخيصًا رسميًا في بعض المراجع، أو عرضًا، أو بُعدًا، أو وصفًا عامًا؛ لذلك لا يكفي ظهور سمة واحدة ولا نتيجة اختبار منفردة للحكم.",
        "dimensions": ("البداية والعمر الذي ظهر فيه التغير", "المدة والتكرار والمسار عبر الوقت", "الشدة والضيق والأثر في الدراسة أو العمل والعلاقات والعناية بالنفس", "السياق الطبي والدوائي والنوم والمواد والضغوط", "الحالات المصاحبة وعوامل الحماية والدعم المتاح"),
        "measurement": "يبدأ التقييم بمقابلة وتاريخ زمني وملاحظة للأداء، وقد تستخدم مقاييس فحص أو شدة مناسبة للعمر واللغة. تُفسر الدرجة مع الصدق والثبات ونقطة القطع والخطأ القياسي، ولا تُحوّل آليًا إلى تشخيص.",
        "use": "يفيد المفهوم في تنظيم الملاحظة وصياغة أسئلة أدق وتحديد ما إذا كان الأثر مستمرًا أو متصاعدًا. عند وجود خطر مباشر، أو تغير حاد، أو عجز عن العناية بالنفس، تكون الأولوية لخدمة صحية عاجلة محلية.",
    },
    "cognitive": {
        "scope": "يصف هذا المفهوم وظيفة أو عملية معرفية، وليس قيمة الإنسان ولا مستوى قدرته الكلية. يتغير الأداء تبعًا للعمر والتعليم واللغة والتعب والنوم والحواس والدافعية والقلق وطريقة تقديم المهمة.",
        "dimensions": ("نوع المعلومات أو المهمة المطلوبة", "الدقة والسرعة واستراتيجيات الحل", "الفرق بين القدرة في الحياة اليومية والأداء في الاختبار", "تأثير اللغة والتعليم والحواس والحركة", "ثبات الظروف وإمكان التعلم من التكرار"),
        "measurement": "يستلزم القياس أداة صالحة للغرض والفئة، وتعليمات موحدة، وبيانات معيارية مناسبة. النتيجة الواحدة تقدير مشروط بظروف التطبيق؛ وتحتاج المتابعة إلى مقارنة متكافئة والانتباه لأثر التدريب والخطأ القياسي.",
        "use": "يفيد المفهوم في وصف نقاط القوة والصعوبات واختيار تعديلات تعليمية أو بيئية. لا يجوز استخدامه منفردًا لتحديد الذكاء العام أو الأهلية أو التشخيص أو التنبؤ بمستقبل الشخص.",
    },
    "behavioral": {
        "scope": "يركز هذا المفهوم على علاقة السلوك بالسياق والنتائج والتعلم، لا على وصم الشخصية. الوصف الجيد يحدد ما يحدث قبل السلوك وأثناءه وبعده، وما الوظيفة المحتملة، مع مراعاة التواصل والألم والنوم والبيئة.",
        "dimensions": ("تعريف السلوك بصورة قابلة للملاحظة", "المواقف السابقة والمحفزات والطلبات", "النتائج التي تلي السلوك وقد تزيده أو تخفضه", "البدائل المتاحة ومهارات التواصل والتنظيم", "التكرار والمدة والشدة والأثر"),
        "measurement": "تُستخدم ملاحظات متكررة وسجلات سياقية وأهداف سلوكية محددة. لا تكفي الانطباعات العامة، ويجب التحقق من اتساق المراقبين ومن أن التغير مهم وظيفيًا لا إحصائيًا فقط.",
        "use": "يفيد المفهوم في تصميم بدائل آمنة وتعزيز المهارات وتعديل البيئة. يجب تجنب العقاب أو الحرمان أو الخطط التقييدية غير المتناسبة، وإشراك الشخص في الأهداف كلما أمكن.",
    },
    "personality": {
        "scope": "يصف هذا المفهوم نمطًا أو سمة محتملة عبر مواقف متعددة، ولا يعني حكمًا أخلاقيًا أو هوية ثابتة. تتداخل السمات مع الثقافة والعمر والأدوار والخبرة، وقد يظهر الشخص بصورة مختلفة باختلاف الأمان والضغط.",
        "dimensions": ("الاستقرار النسبي عبر الزمن", "الاتساق والاختلاف بين المواقف", "الدرجة على متصل بدل التصنيف الثنائي", "أثر الثقافة والعمر والدور الاجتماعي", "الفرق بين السمة والاضطراب والأعراض المؤقتة"),
        "measurement": "تُقاس السمات باستبيانات أو مقابلات أو تقديرات متعددة المصادر ذات صدق وثبات مناسبين. ينبغي فحص تحيز الاستجابة والسياق وعينة التقنين، وعدم تفسير الدرجة خارج الغرض الذي صممت له الأداة.",
        "use": "يفيد المفهوم في فهم التفضيلات وأنماط التفاعل وبناء لغة وصفية أكثر دقة. لا ينبغي استخدامه لتبرير التمييز أو توقع السلوك حتميًا أو تثبيت الشخص في ملصق واحد.",
    },
    "intervention": {
        "scope": "يشير هذا المفهوم إلى طريقة أو مكوّن أو علاقة علاجية محتملة. ملاءمته تعتمد على المشكلة والأهداف والتفضيلات والسن والثقافة والتدريب المهني وإتاحة الخدمة، ولا توجد طريقة واحدة مناسبة للجميع.",
        "dimensions": ("الهدف والمشكلة التي دُرست من أجلها الطريقة", "الفئة والسياق وشروط الاستبعاد", "كفاءة الممارس والإشراف والالتزام بالبروتوكول", "حجم الفائدة وعدم اليقين والآثار غير المرغوبة", "التفضيلات والتكلفة والوصول والمتابعة"),
        "measurement": "تُتابع النتائج بمؤشرات متفق عليها قبل التدخل وأثناءه، مع تسجيل الآثار غير المرغوبة والالتزام والتغير الوظيفي. التحسن في مقياس واحد لا يغني عن تجربة الشخص وأدائه وسلامته.",
        "use": "يفيد المفهوم في مناقشة الخيارات واتخاذ قرار مشترك. لا تبدأ أو توقف علاجًا أو دواءً بناء على صفحة تثقيفية، وتحتاج الحالات عالية الخطورة أو المعقدة إلى مختص مؤهل وخطة أمان.",
    },
    "measurement": {
        "scope": "هذا مفهوم علمي أو منهجي؛ قيمته في دقة السؤال والتعريف الإجرائي ونوعية البيانات، لا في المصطلح وحده. يجب الفصل بين الوصف والارتباط والسببية، وبين الدلالة الإحصائية والأهمية العملية.",
        "dimensions": ("سؤال البحث أو غرض القياس", "تعريف المتغير وطريقة تشغيله", "تصميم الدراسة والعينة والمقارنة", "الصدق والثبات والتحيز والخطأ", "حجم الأثر وعدم اليقين وقابلية التطبيق"),
        "measurement": "يُحكم على الأداة أو النتيجة من خلال الأدلة المتراكمة للصدق والثبات والإنصاف، وعينة التقنين، وإجراءات التطبيق والتصحيح. لا يوجد رقم صحيح بمعزل عن الغرض والفئة والسياق.",
        "use": "يفيد المفهوم في قراءة الدراسات والمقاييس نقديًا وتجنب الاستنتاج الزائد. ينبغي مراجعة البروتوكول والبيانات المفقودة وتضارب المصالح وحدود التعميم قبل نقل النتيجة إلى قرار عملي.",
    },
    "psychosocial": {
        "scope": "يصف هذا المفهوم جانبًا من الرفاه أو العلاقات أو التكيف أو الحياة اليومية. يتأثر بالشخص والبيئة والموارد والثقافة والحقوق والفرص، ولا يجوز اختزاله في الإرادة الفردية أو النصائح العامة.",
        "dimensions": ("المعنى الشخصي والهدف المرغوب", "العلاقات والدعم والانتماء", "الموارد والضغوط والحواجز البيئية", "الاختيار والاستقلال والمشاركة", "الاستدامة والتوازن والأثر في جودة الحياة"),
        "measurement": "يمكن متابعته بمقاييس خبرة ذاتية ومؤشرات سلوكية ووظيفية ومصادر متعددة. يجب تحديد الفترة الزمنية والسياق، وتجنب مقارنة أشخاص مختلفين دون مراعاة الفرص والموارد والحواجز.",
        "use": "يفيد المفهوم في وضع هدف صغير واقعي وتحديد ما يمكن تغييره في البيئة أو الروتين أو الدعم. لا ينبغي تحويله إلى لوم للشخص أو وعد بالتحسن، وتلزم المساعدة المهنية عند الضيق المستمر أو التعطيل أو الخطر.",
    },
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == lower:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        cleaned = SPACE_RE.sub(" ", data).strip()
        if cleaned:
            self.parts.append(cleaned)


def visible_words(source: str) -> int:
    parser = VisibleTextParser()
    parser.feed(source)
    return len(WORD_RE.findall(" ".join(parser.parts)))


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def noindex(source: str) -> bool:
    return bool(re.search(r'<meta\b(?=[^>]*name=["\']robots["\'])(?=[^>]*content=["\'][^"\']*noindex)', source, re.I | re.S))


def list_html(items: list[str] | tuple[str, ...], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>"


def related_terms(term: dict[str, Any], by_category: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    peers = [item for item in by_category[term["category"]] if item["slug"] != term["slug"]]
    if not peers:
        return []
    index = next((i for i, item in enumerate(by_category[term["category"]]) if item["slug"] == term["slug"]), 0)
    ordered = peers[index % len(peers):] + peers[:index % len(peers)]
    return ordered[:5]


def source_html(profile: str) -> str:
    return list_html([
        f'<a href="{escape(url)}" rel="noopener noreferrer">{escape(label)}</a>'
        for label, url in SOURCES[profile]
    ])


def build_block(term: dict[str, Any], related: list[dict[str, Any]]) -> str:
    ar = escape(term["ar"])
    en = escape(term["en"])
    category = escape(term["category"])
    description = escape(term["description"])
    profile_name = CATEGORY_PROFILE.get(term["category"], "psychosocial")
    profile = PROFILE_COPY[profile_name]
    relation_links = [
        f'<a href="/terms/{escape(item["slug"])}/">{escape(item["ar"])}</a> — {escape(item["en"])}'
        for item in related
    ]
    dimensions = [escape(item) for item in profile["dimensions"]]
    questions = [
        f"ما التعريف الدقيق لـ {ar} في هذا السياق، وما الذي يقع خارج حدوده؟",
        f"متى بدأ ما يرتبط بـ {ar}، وكم يتكرر، وفي أي مواقف يزيد أو ينخفض؟",
        "ما الأثر الملاحظ في الأداء أو المشاركة أو جودة الحياة، وما الدليل العملي عليه؟",
        "ما التفسيرات البديلة الطبية أو النمائية أو البيئية أو الثقافية التي يجب فحصها؟",
        "ما المعلومة أو الأداة الإضافية التي ستقلل عدم اليقين قبل اتخاذ قرار؟",
    ]
    faq = (
        f'<details><summary>هل {ar} تشخيص مستقل؟</summary><p>لا يمكن الإجابة من الاسم وحده. قد يكون المصطلح تشخيصًا رسميًا في نظام تصنيفي، أو عرضًا، أو سمة، أو مهارة، أو مفهومًا بحثيًا. يُراجع التعريف في المرجع المناسب ويُفحص السياق والأثر والمعايير كاملة.</p></details>'
        f'<details><summary>هل يكفي اختبار واحد لفهم {ar}؟</summary><p>لا. الاختبار يقدّم عينة محدودة من الأداء أو الخبرة، وتتأثر نتيجته باللغة والعمر والتعليم والحالة الصحية وظروف التطبيق. التفسير المسؤول يجمع أكثر من مصدر ويذكر درجة عدم اليقين.</p></details>'
        f'<details><summary>كيف أبحث عن {ar} في المراجع الأجنبية؟</summary><p>ابدأ بالمقابل الإنجليزي <strong dir="ltr">{en}</strong>، ثم أضف نوع السؤال مثل definition أو assessment أو systematic review أو guideline. افحص الجهة الناشرة وتاريخ المراجعة والفئة التي تناولها المصدر.</p></details>'
    )
    reading_plan = list_html([
        f"ابدأ بتثبيت تعريف {ar} من مصدر مؤسسي أو كتاب مرجعي، وسجل اختلاف التعريف إن وجد.",
        "حوّل التعريف إلى أمثلة قابلة للملاحظة وأمثلة مضادة توضح ما لا يشمله المفهوم.",
        "حدد نوع السؤال: تعريف، قياس، سبب، أثر، تدخل، أو خبرة شخصية؛ فلكل سؤال نوع دليل مختلف.",
        "قارن أكثر من مصدر، ودوّن الفئة والسياق والتاريخ وحجم العينة وحدود التعميم.",
        "اختم بدرجة ثقة مؤقتة وما المعلومات الناقصة والخطوة الآمنة التالية.",
    ], ordered=True)
    return f'''<!-- term-depth-v224:start -->
<section class="term-depth-v224" {MARKER}="{escape(term['slug'])}">
<h2>دليل موسع لفهم {ar} <span dir="ltr">({en})</span></h2>
<p><strong>التعريف المختصر:</strong> {description}</p>
<p>ينتمي المصطلح إلى مجال <strong>{category}</strong>. هذا التصنيف يساعد على تنظيم القراءة، لكنه لا يعني أن حدود المفهوم ثابتة بين جميع المدارس أو أن استعماله متطابق في البحث والممارسة والحياة اليومية. عند قراءة أي تعريف، تحقق من الفئة والسياق والهدف والمصدر؛ فالمصطلح نفسه قد يستخدم بوصفه عملية أو سمة أو خبرة أو أداة وصف أو اسمًا سريريًا.</p>
<div class="term-depth-v224__grid">
<section><h3>حدود المفهوم</h3><p>{escape(profile['scope'])}</p><p>لا تُفسر {ar} من كلمة منفردة أو موقف واحد. افصل بين وجود المفهوم بدرجة ما، وبين كونه شديدًا أو مستمرًا أو معطلًا، وبين إمكان استخدامه في تشخيص أو قرار مهني. كذلك افصل بين الوصف والتفسير: ملاحظة نمط لا تثبت سببه.</p></section>
<section><h3>الأبعاد التي تستحق الفحص</h3>{list_html(dimensions)}</section>
<section><h3>أسئلة منهجية قبل الاستنتاج</h3>{list_html(questions, ordered=True)}</section>
<section><h3>القياس والتقييم المسؤول</h3><p>{escape(profile['measurement'])}</p><p>اسأل دائمًا: ما غرض القياس؟ ولمن صُممت الأداة؟ وما أدلة الصدق والثبات والإنصاف؟ وما الفترة التي تغطيها؟ وما مقدار الخطأ المتوقع؟ يجب توثيق ظروف التطبيق وأي تعديل، وتجنب مقارنة نتائج غير متكافئة.</p></section>
<section><h3>الاستخدام العملي والحدود المهنية</h3><p>{escape(profile['use'])}</p><p>حوّل المعرفة إلى خطوة محددة: سجل مثالًا وتاريخه وسياقه وأثره، حدد سؤالًا واحدًا يحتاج إجابة، واختر مصدرًا أو مختصًا مناسبًا. راجع الاستنتاج إذا ظهرت معلومات جديدة بدل تثبيت الشخص في وصف دائم.</p></section>
<section><h3>أخطاء شائعة في الفهم</h3>{list_html([f'اعتبار {ar} صفة كلية تفسر كل السلوك.', 'الاعتماد على مقطع قصير أو قائمة أعراض بلا مصدر أو سياق.', 'الخلط بين الارتباط والسببية وبين المتوسط وحالة الفرد.', 'تجاهل العمر واللغة والثقافة والصحة والبيئة.', 'استخدام النتيجة للوصم أو الحرمان أو اتخاذ قرار عالي الأثر دون تقييم مؤهل.'])}</section>
<section><h3>خطة قراءة متدرجة</h3>{reading_plan}<p>هذه الخطة تمنع الانتقال من تعريف مختصر إلى حكم كبير. المعرفة الجيدة لا تعني جمع أكبر عدد من العلامات، بل تنظيم الأدلة، وفصل الملاحظة عن التفسير، وتحديث الفهم عندما تتغير المعلومات. عند استخدام المصطلح مع شخص، احترم لغته المفضلة وخصوصيته وحقه في الاعتراض على الوصف.</p></section>
<section><h3>مصطلحات مرتبطة للقراءة التالية</h3>{list_html(relation_links) if relation_links else '<p>راجع فهرس الفئة والموسوعة لاختيار المفهوم الأقرب للسؤال.</p>'}</section>
<section><h3>مصادر مؤسسية ومنهجية</h3>{source_html(profile_name)}<p><small>هذه روابط مرجعية عامة. تحقق من الدليل المتخصص بالمصطلح والفئة والغرض، ومن تاريخ المراجعة وشروط الاستخدام.</small></p></section>
</div>
<section><h3>أسئلة شائعة</h3>{faq}</section>
<p class="term-depth-v224__safety"><strong>تنبيه:</strong> المحتوى تثقيفي ولا يثبت تشخيصًا ولا يستبدل التقييم الفردي. عند خطر مباشر أو تغير حاد أو عجز عن العناية بالنفس، استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة.</p>
</section>
<!-- term-depth-v224:end -->'''


def style_tag() -> str:
    return '''<style data-term-depth-v224-style>.term-depth-v224{margin:2rem auto;padding:clamp(1rem,3vw,2rem);border:1px solid #bdded9;border-radius:24px;background:#f6fcfb}.term-depth-v224 h2{color:#075f5b}.term-depth-v224 h3{color:#783252}.term-depth-v224 p,.term-depth-v224 li{line-height:1.95}.term-depth-v224__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.term-depth-v224__grid>section,.term-depth-v224 details{padding:1rem;border:1px solid #d5e9e5;border-radius:16px;background:#fff}.term-depth-v224 details{margin:.7rem 0}.term-depth-v224 summary{font-weight:800;cursor:pointer}.term-depth-v224__safety{border-inline-start:5px solid #8b315c;padding:1rem;background:#fff1f7}@media(max-width:760px){.term-depth-v224__grid{grid-template-columns:1fr}}</style>'''


def enrich_page(path: Path, term: dict[str, Any], related: list[dict[str, Any]]) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    before = visible_words(source)
    result: dict[str, Any] = {"slug": term["slug"], "path": path.as_posix(), "before_words": before}
    if noindex(source):
        return {**result, "status": "skipped_noindex", "after_words": before}
    if MARKER in source:
        return {**result, "status": "already_enriched", "after_words": before, "below_minimum": before < MIN_WORDS}
    if before >= MIN_WORDS:
        return {**result, "status": "sufficient", "after_words": before, "below_minimum": False}
    if "</head>" not in source:
        raise ValueError("missing head")
    if "data-term-depth-v224-style" not in source:
        source = source.replace("</head>", style_tag() + "</head>", 1)
    block = build_block(term, related)
    if "</main>" in source:
        source = source.replace("</main>", block + "</main>", 1)
    elif "</body>" in source:
        source = source.replace("</body>", block + "</body>", 1)
    else:
        raise ValueError("missing insertion point")
    after = visible_words(source)
    path.write_text(source, encoding="utf-8")
    return {**result, "status": "enriched", "after_words": after, "added_words": after - before, "below_minimum": after < MIN_WORDS}


def load_terms(site: Path) -> list[dict[str, Any]]:
    payload = json.loads((site / "api" / "terms.json").read_text(encoding="utf-8"))
    terms = payload.get("terms")
    if not isinstance(terms, list) or len(terms) < 200:
        raise ValueError(f"expected at least 200 terms, found {len(terms) if isinstance(terms, list) else 'invalid'}")
    required = {"ar", "en", "category", "description", "slug"}
    slugs: set[str] = set()
    clean: list[dict[str, Any]] = []
    for item in terms:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("term record is missing required fields")
        slug = str(item["slug"]).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in slugs:
            raise ValueError(f"invalid or duplicate term slug: {slug}")
        slugs.add(slug)
        clean.append({key: str(item[key]).strip() for key in required})
    return clean


def run(site: Path) -> dict[str, Any]:
    site = site.resolve()
    terms = load_terms(site)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for term in terms:
        by_category[term["category"]].append(term)
    for values in by_category.values():
        values.sort(key=lambda item: item["slug"])

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for term in terms:
        page = site / "terms" / term["slug"] / "index.html"
        if not page.is_file():
            failures.append({"slug": term["slug"], "error": "missing term page"})
            continue
        try:
            results.append(enrich_page(page, term, related_terms(term, by_category)))
        except Exception as error:
            failures.append({"slug": term["slug"], "error": f"{type(error).__name__}: {error}"})

    remaining = [item for item in results if item.get("below_minimum")]
    generated_hashes: dict[str, list[str]] = defaultdict(list)
    for term in terms:
        block = build_block(term, related_terms(term, by_category))
        generated_hashes[hashlib.sha256(block.encode("utf-8")).hexdigest()].append(term["slug"])
    duplicate_blocks = [slugs for slugs in generated_hashes.values() if len(slugs) > 1]
    report = {
        "version": VERSION,
        "status": "passed" if not failures and not remaining and not duplicate_blocks else "failed",
        "minimum_words": MIN_WORDS,
        "terms": len(terms),
        "categories": len(by_category),
        "enriched_pages": sum(item["status"] == "enriched" for item in results),
        "sufficient_pages": sum(item["status"] == "sufficient" for item in results),
        "already_enriched_pages": sum(item["status"] == "already_enriched" for item in results),
        "remaining_below_minimum": len(remaining),
        "missing_or_failed": len(failures),
        "duplicate_generated_blocks": len(duplicate_blocks),
        "failures": failures[:200],
        "remaining": remaining[:200],
        "pages": results,
    }
    output = site / "api" / "term-content-depth-v224.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site")
    report = run(Path(parser.parse_args().site))
    print(json.dumps({key: report[key] for key in ("version", "status", "terms", "categories", "enriched_pages", "sufficient_pages", "remaining_below_minimum", "missing_or_failed", "duplicate_generated_blocks")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
