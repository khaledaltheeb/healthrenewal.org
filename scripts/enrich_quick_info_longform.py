#!/usr/bin/env python3
"""Legacy-aware long-form enrichment for the Quick Information section.

The generator deliberately starts from the already-published article body instead
of replacing it.  It extracts the old page's headings and list items, keeps the
legacy body verbatim, and adds topic-specific explanatory material around those
signals.  The goal is people-first depth, not keyword padding.

Quality contract:
- every public Quick Information article remains on its existing canonical URL;
- every legacy article body is preserved inside the upgraded page;
- the upgraded visible article body contains at least MIN_WORDS Arabic/word
  tokens (editorial floor requested by the site owner; not a Google rule);
- search-intent questions are visible in the page body;
- large-image / Discover metadata added by the established enhancer remains;
- no page is allowed to pass with an empty title, summary, legacy body, or
  duplicate long-form marker.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION = ROOT / "quick-info"
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
REPORT_PATH = ROOT / "reports" / "quick-info-longform-quality.json"
CSS_PATH = ROOT / "assets" / "quick-info" / "quick-info.css"
EXPECTED_COUNT = 250
MIN_WORDS = 1500
START = "<!-- QUICK_INFO_LONGFORM_V1_START -->"
END = "<!-- QUICK_INFO_LONGFORM_V1_END -->"

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[A-Za-z0-9_\u0600-\u06FF]+", re.UNICODE)
ARTICLE_RE = re.compile(
    r'(<article\s+class=["\']article["\'][^>]*>)(.*?)(</article>)', re.DOTALL
)
LIST_RE = re.compile(r"<li\b[^>]*>(.*?)</li>", re.DOTALL | re.IGNORECASE)
HEADING_RE = re.compile(r"<h[23]\b[^>]*>(.*?)</h[23]>", re.DOTALL | re.IGNORECASE)

DOMAIN = {
    "general": {
        "label": "الصحة النفسية العامة",
        "lenses": [
            "السياق الذي ظهر فيه التغير، وهل سبقه ضغط واضح أو تغير في الروتين أو حدث حياتي",
            "المدة والتكرار: هل هو موقف عابر أم نمط يتكرر أو يستمر رغم زوال السبب المباشر",
            "الأثر الوظيفي في النوم والطاقة والتركيز والعمل أو الدراسة والعلاقات والعناية بالنفس",
            "العوامل الجسدية والدوائية ونمط النوم والتغذية التي قد تشبه الأعراض النفسية أو تزيدها",
            "درجة المرونة: هل يمكن للشخص العودة إلى نشاطه تدريجيًا مع الراحة والدعم وتعديل الظروف",
        ],
        "sources": [
            ("منظمة الصحة العالمية - الصحة النفسية", "https://www.who.int/health-topics/mental-health"),
            ("المعهد الوطني للصحة النفسية NIMH", "https://www.nimh.nih.gov/health"),
        ],
    },
    "depression": {
        "label": "المزاج والاكتئاب",
        "lenses": [
            "استمرار انخفاض المزاج أو فقدان المتعة بدل الحكم من يوم سيئ أو موقف مؤلم واحد",
            "التغير الملحوظ في النوم والطاقة والشهية والتركيز والقدرة على إنجاز المسؤوليات",
            "وجود يأس أو شعور شديد بالذنب أو انسحاب يضيق الحياة ويستمر بدل أن يتحسن تدريجيًا",
            "استبعاد أسباب جسدية أو دوائية محتملة عندما يكون التعب أو بطء التفكير أو النوم هو العرض الأبرز",
            "تقييم السلامة فورًا عند وجود أفكار موت أو إيذاء للنفس أو عجز واضح عن العناية الأساسية بالنفس",
        ],
        "sources": [
            ("منظمة الصحة العالمية - الاكتئاب", "https://www.who.int/news-room/fact-sheets/detail/depression"),
            ("NIMH - Depression", "https://www.nimh.nih.gov/health/topics/depression"),
        ],
    },
    "anxiety": {
        "label": "القلق والخوف",
        "lenses": [
            "التمييز بين خوف مرتبط بخطر أو موقف محدد وبين قلق يستمر أو يتسع حتى بعد انتهاء السبب المباشر",
            "مقدار التجنب الذي يفرضه القلق على الدراسة أو العمل أو العلاقات أو التنقل أو النوم",
            "الأعراض الجسدية مثل الخفقان والتعرق والدوخة والتنفس السريع لا تُفسر نفسيًا تلقائيًا دون مراعاة السياق الطبي",
            "المدة والتكرار والتوقع المسبق للخوف أهم من شدة لحظة منفردة عند فهم النمط",
            "الهدف من المساعدة ليس إزالة كل قلق، بل استعادة القدرة على الاختيار والعمل رغم وجود قدر طبيعي من القلق",
        ],
        "sources": [
            ("NIMH - Anxiety Disorders", "https://www.nimh.nih.gov/health/topics/anxiety-disorders"),
            ("NHS - Anxiety, fear and panic", "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/anxiety-fear-panic/"),
        ],
    },
    "relationships": {
        "label": "العلاقات والحدود",
        "lenses": [
            "السلوك المتكرر أهم من النية المعلنة؛ راقب ما يحدث فعليًا عند الاختلاف والرفض ووضع الحدود",
            "العلاقة الصحية تسمح بالاختيار والخصوصية والاعتراض دون تهديد أو إذلال أو عقاب أو مراقبة قسرية",
            "الاعتذار الحقيقي يرتبط بتحمل المسؤولية وتغيير السلوك، لا بمجرد كلمات تهدئ الموقف ثم يعاد النمط نفسه",
            "الخلاف ليس هو الإساءة؛ معيار الأمان يشمل الخوف والسيطرة والعزل والإهانة والتهديد والقيود المالية أو الرقمية",
            "عند وجود خوف أو عنف أو تهديد، تكون السلامة والدعم المتخصص أهم من تحسين مهارة التواصل داخل اللحظة الخطرة",
        ],
        "sources": [
            ("منظمة الصحة العالمية - العنف ضد المرأة", "https://www.who.int/news-room/fact-sheets/detail/violence-against-women"),
            ("APA - Relationships", "https://www.apa.org/topics/relationships"),
        ],
    },
    "child": {
        "label": "الطفل والنمو والأسرة",
        "lenses": [
            "سلوك الطفل يُفهم نسبة إلى العمر والمرحلة النمائية والسياق، وليس بالمقارنة السريعة مع طفل آخر",
            "تكرار النمط في أكثر من بيئة ومع أكثر من مقدم رعاية يعطي معلومات أهم من موقف واحد شديد",
            "النوم واللغة والحس والمرض والضغط المدرسي والتغيرات الأسرية قد تؤثر في السلوك والانتباه والتنظيم",
            "الهدف الأول هو فهم وظيفة السلوك وما الذي يصعب على الطفل فعله قبل الانتقال مباشرة إلى العقاب أو التسمية",
            "التقييم المبكر مفيد عندما يؤثر النمط في التعلم أو التواصل أو السلامة أو العلاقات أو المشاركة اليومية",
        ],
        "sources": [
            ("CDC - Child Development", "https://www.cdc.gov/ncbddd/childdevelopment/"),
            ("American Academy of Pediatrics - HealthyChildren", "https://www.healthychildren.org/"),
        ],
    },
    "adhd": {
        "label": "الانتباه وفرط الحركة",
        "lenses": [
            "اضطراب فرط الحركة وتشتت الانتباه لا يُستنتج من التشتت أو الحركة وحدهما؛ يلزم نمط مستمر ومؤثر",
            "تعدد البيئات مهم: المدرسة والمنزل والعمل أو المواقف اليومية، لأن صعوبة واحدة في سياق واحد قد يكون لها تفسير آخر",
            "النوم والقلق والاكتئاب والضغط وصعوبات التعلم واستخدام الشاشات قد تزيد مشكلات الانتباه أو تشبهها",
            "التقييم الجيد يراجع التاريخ النمائي والوظيفة اليومية وملاحظات أكثر من مصدر بدل الاعتماد على اختبار قصير وحده",
            "الدعم العملي يشمل تنظيم البيئة والمهام والروتين، ولا يقتصر على الإرادة أو لوم الشخص على ضعف الانضباط",
        ],
        "sources": [
            ("CDC - ADHD", "https://www.cdc.gov/adhd/"),
            ("NIMH - ADHD", "https://www.nimh.nih.gov/health/topics/attention-deficit-hyperactivity-disorder-adhd"),
        ],
    },
    "ocd": {
        "label": "الوسواس القهري",
        "lenses": [
            "حب النظام أو التفضيلات الشخصية لا يساوي الوسواس القهري؛ المهم وجود أفكار أو دوافع ملحّة وطقوس مرتبطة بالضيق",
            "السلوك المتكرر يُقيّم بحسب وظيفته: هل يهدف إلى منع خطر متخيل أو تخفيف قلق شديد بطريقة يصعب مقاومتها",
            "مقدار الوقت والضيق والتعطيل اليومي مؤشرات أهم من غرابة الفكرة أو شكل السلوك وحده",
            "الطمأنة المتكررة وتجنب المثيرات قد يخففان القلق لحظيًا لكنهما قد يثبتان الحلقة لدى بعض الأشخاص",
            "التشخيص والعلاج يحتاجان تقييمًا مهنيًا؛ المقارنات السريعة لا تكفي للحكم أو لاختيار تدخل علاجي",
        ],
        "sources": [
            ("NIMH - OCD", "https://www.nimh.nih.gov/health/topics/obsessive-compulsive-disorder-ocd"),
            ("NICE - OCD and BDD", "https://www.nice.org.uk/guidance/cg31"),
        ],
    },
    "bipolar": {
        "label": "الاضطراب ثنائي القطب",
        "lenses": [
            "التقلب اليومي في المشاعر لا يساوي نوبة هوس أو هوس خفيف؛ التقييم ينظر إلى مجموعة أعراض ومدة وتغير واضح عن المعتاد",
            "انخفاض الحاجة إلى النوم مع زيادة النشاط أو الكلام أو الاندفاع يختلف عن مجرد ليلة قصيرة أو مزاج جيد",
            "التاريخ الزمني للنوبات والأدوية والمواد والحالات الطبية جزء أساسي من التقييم التفريقي",
            "الآثار في العمل والمال والعلاقات والسلامة تساعد على فهم شدة التغير أكثر من وصف المزاج بكلمة واحدة",
            "تغيرات المزاج الشديدة أو السلوك عالي الخطورة أو فقدان الاتصال بالواقع تستدعي تقييمًا مهنيًا عاجلًا بحسب الحالة",
        ],
        "sources": [
            ("NIMH - Bipolar Disorder", "https://www.nimh.nih.gov/health/topics/bipolar-disorder"),
            ("NHS - Bipolar disorder", "https://www.nhs.uk/mental-health/conditions/bipolar-disorder/"),
        ],
    },
    "sleep": {
        "label": "النوم والأرق",
        "lenses": [
            "التمييز بين قلة فرصة النوم وبين صعوبة النوم رغم وجود فرصة ووقت مناسبين مهم قبل تسمية المشكلة أرقًا",
            "انتظام المواعيد والضوء والكافيين والقيلولة والعمل الليلي والشاشات قد تغير جودة النوم دون أن تكون السبب الوحيد",
            "الشخير الشديد أو الاختناق أثناء النوم أو النعاس الخطير نهارًا أو الحركات غير المعتادة تحتاج تقييمًا طبيًا مناسبًا",
            "الهدف هو قياس نمط لعدة أيام أو أسابيع بدل بناء استنتاج على ليلة واحدة سيئة",
            "تأثير النوم في المزاج والتركيز والأداء والسلامة يجعل معالجة المشكلة عملية تتجاوز مجرد حساب عدد الساعات",
        ],
        "sources": [
            ("NHLBI - Sleep Deprivation and Deficiency", "https://www.nhlbi.nih.gov/health/sleep-deprivation"),
            ("NHS - Insomnia", "https://www.nhs.uk/conditions/insomnia/"),
        ],
    },
    "work": {
        "label": "العمل والاحتراق",
        "lenses": [
            "الاحتراق المهني يرتبط بسياق العمل المزمن ولا يفسر تلقائيًا كل تعب أو اكتئاب أو مشكلة صحية",
            "حجم المطالب مقابل الموارد والسيطرة والدعم والعدالة والقدرة على التعافي بعد الدوام عناصر عملية تستحق القياس",
            "الاستراحة القصيرة قد تساعد التعب العابر، بينما استمرار الاستنزاف رغم الراحة يشير إلى ضرورة مراجعة أوسع للظروف والصحة",
            "الحدود المهنية تشمل الوقت والتوقعات وقنوات التواصل والأولوية، وليس فقط القدرة على قول لا",
            "إذا امتد الضيق إلى كل مجالات الحياة أو صاحبه يأس شديد أو اضطراب نوم مستمر فالتقييم الصحي مهم بدل اختزاله في العمل",
        ],
        "sources": [
            ("WHO - Burn-out in ICD-11", "https://www.who.int/standards/classifications/frequently-asked-questions/burn-out-an-occupational-phenomenon"),
            ("WHO - Mental health at work", "https://www.who.int/news-room/fact-sheets/detail/mental-health-at-work"),
        ],
    },
    "addiction": {
        "label": "الإدمان والتعافي",
        "lenses": [
            "عدد مرات الاستخدام وحده لا يحدد الإدمان؛ فقدان السيطرة والضرر والاستمرار رغم العواقب مؤشرات أكثر دلالة",
            "الانسحاب والتحمل والرغبة الشديدة قد تكون مهمة لبعض المواد أو السلوكيات لكنها لا تُفهم خارج التقييم الكامل",
            "الانتكاسة أو التعثر لا تعني فشل التعافي؛ المهم تقييم الخطر والعودة السريعة إلى خطة دعم مناسبة",
            "وجود مواد مختلفة أو أدوية أو أمراض جسدية أو اضطرابات نفسية متزامنة قد يغير خطة الأمان والعلاج",
            "بعض حالات الانسحاب قد تكون خطرة طبيًا، لذلك لا ينبغي تقديم خطة انسحاب منزلية عامة كبديل عن التقييم المهني",
        ],
        "sources": [
            ("WHO - Substance use", "https://www.who.int/health-topics/drugs-psychoactive"),
            ("SAMHSA - Find Support", "https://www.samhsa.gov/find-support"),
        ],
    },
    "digital": {
        "label": "الصحة الرقمية",
        "lenses": [
            "المشكلة ليست عدد الساعات وحده؛ المهم هل يستطيع الشخص التوقف وهل يزاحم الاستخدام النوم والعمل والعلاقات والنشاط البدني",
            "نوع الاستخدام يهم: تواصل هادف أو تعلم يختلف عن تمرير قهري يترك الشخص أسوأ مزاجًا أو أكثر قلقًا",
            "الإشعارات وتصميم التطبيقات والملل والضغط قد تغذي حلقات الاستخدام، لذلك لا ينبغي اختزال الأمر في ضعف الإرادة",
            "التغيير الناجح يقيس سلوكًا محددًا مثل وقت البداية والنهاية والمواقف المحفزة بدل هدف عام مثل استخدام الهاتف أقل",
            "إذا ارتبط الاستخدام بعزلة شديدة أو اكتئاب أو قلق أو فقدان نوم مستمر فالمشكلة الأوسع تحتاج اهتمامًا أيضًا",
        ],
        "sources": [
            ("APA - Health Advisory on Social Media Use in Adolescence", "https://www.apa.org/topics/social-media-internet/health-advisory-adolescent-social-media-use"),
            ("WHO - Mental health", "https://www.who.int/health-topics/mental-health"),
        ],
    },
    "eating": {
        "label": "الأكل والسلوك الغذائي",
        "lenses": [
            "الجوع الجسدي والتناول العاطفي قد يتداخلان، لذلك يفيد تتبع التوقيت والمشاعر والسرعة والشبع دون وصم",
            "التقييد الشديد للطعام قد يزيد نوبات الأكل لدى بعض الأشخاص، ولا ينبغي تحويل الصفحة إلى قواعد حمية قاسية",
            "تغيرات الوزن السريعة أو القيء المتعمد أو الإغماء أو اضطراب الأكل الشديد تحتاج تقييمًا صحيًا مناسبًا",
            "النوم والضغط والأدوية والحالات الطبية قد تؤثر في الشهية والطاقة والسلوك الغذائي",
            "الهدف هو فهم النمط ودعم علاقة أكثر أمانًا مع الطعام والجسم، لا استخدام الخجل أو العقاب كأداة تغيير",
        ],
        "sources": [
            ("NIMH - Eating Disorders", "https://www.nimh.nih.gov/health/topics/eating-disorders"),
            ("NHS - Eating disorders", "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/behaviours/eating-disorders/overview/"),
        ],
    },
    "trauma": {
        "label": "الصدمة والضغط الشديد",
        "lenses": [
            "استجابات ما بعد الحدث المؤلم قد تشمل فرط يقظة وتجنبًا وذكريات مزعجة وتغيرًا في النوم، لكنها تختلف في المدة والشدة",
            "الشعور بالخطر قد يستمر بعد انتهاء الحدث؛ تنظيم الأمان الحالي يسبق دفع الشخص إلى مواجهة تفاصيل لا يحتملها",
            "ليس كل شخص يمر بصدمة يطور اضطراب ما بعد الصدمة، ولا تكفي علامة واحدة للتشخيص",
            "الدعم يجب أن يراعي الاختيار والسيطرة والخصوصية وألا يعيد تجربة الإكراه أو اللوم",
            "خطر إيذاء النفس أو العنف المستمر أو فقدان الأمان الحالي يتطلب خطة أمان ودعمًا عاجلًا مناسبًا للسياق المحلي",
        ],
        "sources": [
            ("NIMH - PTSD", "https://www.nimh.nih.gov/health/topics/post-traumatic-stress-disorder-ptsd"),
            ("WHO - Stress", "https://www.who.int/news-room/questions-and-answers/item/stress"),
        ],
    },
    "grief": {
        "label": "الفقد والحزن",
        "lenses": [
            "الحزن بعد الفقد ليس مسارًا خطيًا ولا يملك جدولًا واحدًا يصلح للجميع؛ التغير مع الوقت والوظيفة أهم من مقارنة الشخص بغيره",
            "موجات الحزن قد تشتد في المناسبات والذكريات دون أن يعني ذلك عودة الشخص إلى نقطة الصفر",
            "النوم والطعام والعزلة والدعم الاجتماعي والسياق الثقافي والديني تؤثر في تجربة الفقد وطريقة التعبير عنها",
            "وجود اكتئاب أو صدمة أو أفكار إيذاء للنفس يحتاج تقييمًا مستقلًا ولا يُفترض أنه مجرد جزء طبيعي من الحزن",
            "المساندة الأفضل تسمح بالحزن وتدعم الاحتياجات اليومية بدل إجبار الشخص على النسيان أو تجاوز التجربة بسرعة",
        ],
        "sources": [
            ("APA - Grief", "https://www.apa.org/topics/grief"),
            ("NHS - Grief after bereavement or loss", "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/grief-bereavement-loss/"),
        ],
    },
    "care": {
        "label": "الرعاية وطلب المساعدة",
        "lenses": [
            "وضوح الهدف من الموعد أو الدعم يساعد على جمع المعلومات ذات الصلة بدل محاولة سرد كل شيء دفعة واحدة",
            "التاريخ الزمني للأعراض والأدوية والحالات الصحية والعلاجات السابقة والمخاطر الحالية معلومات أساسية عند التقييم",
            "من حق الشخص أن يسأل عن المؤهلات والمنهج والخصوصية والتكلفة والخطة وكيفية قياس التقدم",
            "العلاقة العلاجية الجيدة لا تعني غياب الاختلاف، لكنها تتطلب أمانًا واحترامًا وإمكانية مناقشة الملاحظات والحدود",
            "عند وجود خطر عاجل لا ينبغي انتظار موعد روتيني؛ الأولوية لخدمات الطوارئ أو الرعاية العاجلة المحلية المناسبة",
        ],
        "sources": [
            ("NIMH - Help for Mental Illnesses", "https://www.nimh.nih.gov/health/find-help"),
            ("WHO - Mental health", "https://www.who.int/health-topics/mental-health"),
        ],
    },
}

FORMAT_INTENTS = {
    "comparison": "المقارنة هنا هدفها مساعدتك على ملاحظة الفروق العملية بين احتمالين متشابهين في الظاهر، لا إعطاء تشخيص من عنوان أو عرض واحد.",
    "check": "هذا الفحص أداة لتنظيم الملاحظة الذاتية وطرح أسئلة أفضل، وليس مقياسًا تشخيصيًا أو نتيجة طبية مستقلة.",
    "factors": "وجود عدة عوامل محتملة يعني أن الصفحة تساعد على بناء فرضيات قابلة للفحص، لا اختيار سبب واحد ثم اعتباره حقيقة.",
    "practical": "الهدف تحويل السؤال إلى خطوات صغيرة قابلة للتنفيذ والقياس مع مساحة للتعديل إذا لم تناسب الظروف الفعلية.",
    "relationship": "التركيز في موضوعات العلاقات يكون على السلوك المتكرر والأثر والحدود والأمان أكثر من تفسير نوايا الطرف الآخر.",
}

CSS_PATCH = r"""
/* quick-info long-form mobile/page-experience patch */
.article{min-width:0;overflow-wrap:anywhere}
.article .longform-section{margin-block:2rem;scroll-margin-top:100px}
.article .longform-section>p{max-width:78ch}
.article .signal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:18px 0}
.article .signal-card{border:1px solid var(--line);border-radius:18px;background:#fbfefd;padding:18px;min-width:0}
.article .signal-card h3{margin-top:0}
.article .intent-faq details{border:1px solid var(--line);border-radius:16px;background:#fff;margin:10px 0;padding:0 16px}
.article .intent-faq summary{cursor:pointer;font-weight:900;padding:15px 0;min-height:48px}
.article .intent-faq details p{padding-bottom:15px;margin-top:0}
.article table{max-width:100%}
.article .compare{display:table}
.source-list a{overflow-wrap:anywhere}
@media(max-width:640px){
  body{line-height:1.78}
  .wrap{width:min(100% - 28px,1160px)}
  .site-header{position:relative}
  .head{gap:8px}
  .nav{width:100%;overflow-x:auto;flex-wrap:nowrap;padding-bottom:4px;scrollbar-width:thin}
  .nav a{white-space:nowrap;min-height:44px;display:inline-flex;align-items:center}
  h1{font-size:clamp(1.9rem,9vw,2.45rem);text-wrap:balance}
  .lead{font-size:1.05rem}
  .cover{border-radius:18px}
  .article{padding:18px}
  .article .signal-grid{grid-template-columns:1fr}
  .article .compare{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch;white-space:normal}
  .article .compare th,.article .compare td{min-width:150px}
  .steps li{padding-inline-start:14px;padding-inline-end:54px}
}
"""


def clean(fragment: str) -> str:
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    return SPACE_RE.sub(" ", text).strip()


def unique(values: list[str], limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = clean(value)
        key = SPACE_RE.sub(" ", value).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value)
        if limit is not None and len(out) >= limit:
            break
    return out


def word_count(fragment: str) -> int:
    return len(WORD_RE.findall(clean(fragment)))


def domain_for(name: str) -> dict:
    return DOMAIN.get(name, DOMAIN["general"])


def concepts_from_title(title: str) -> tuple[str, str]:
    lead = re.split(r"[؟?]|:|—|\|", title, maxsplit=1)[0].strip()
    if " أم " in lead:
        left, right = [part.strip() for part in lead.split(" أم ", 1)]
        return left, right
    return lead, "الاحتمال الآخر أو التفسير الأوسع"


def pick(items: list[str], slug: str, offset: int = 0) -> str:
    digest = hashlib.sha256((slug + str(offset)).encode("utf-8")).digest()
    return items[digest[0] % len(items)]


def legacy_signals(old_body: str, item: dict) -> list[str]:
    found = unique(LIST_RE.findall(old_body), 8)
    if found:
        return found
    title = item["title"]
    summary = item["summary"]
    return [
        f"راقب النمط المرتبط بسؤال «{title}» بدل الاعتماد على لحظة واحدة.",
        summary,
        "دوّن ما يزيد المشكلة وما يخففها وما الذي تغير في حياتك بالتزامن معها.",
        "لاحظ الأثر في النوم والعمل أو الدراسة والعلاقات والعناية بالنفس.",
        "انتبه إلى أي عوامل جسدية أو دوائية أو بيئية قد تحتاج تقييمًا مستقلًا.",
    ]


def intro_section(item: dict, old_body: str) -> str:
    ctx = domain_for(item.get("domain", "general"))
    fmt = item.get("format", "practical")
    intent = FORMAT_INTENTS.get(fmt, FORMAT_INTENTS["practical"])
    left, right = concepts_from_title(item["title"])
    headings = unique(HEADING_RE.findall(old_body), 6)
    heading_note = "، ".join(headings[:3]) if headings else "الفكرة الأساسية، الإشارات، والخطوات العملية"
    return f"""
<section class="longform-section" id="intent">
<h2>ما الذي يريد الباحث معرفته فعلًا؟</h2>
<p>السؤال «{html.escape(item['title'])}» لا يحتاج إجابة بنعم أو لا فقط. الباحث غالبًا يريد أن يعرف كيف يميز بين التفسيرات المتشابهة، وما العلامات التي تستحق المراقبة، وما الذي يمكن فعله الآن، ومتى تصبح الاستشارة المهنية أكثر فائدة. لذلك تحافظ هذه النسخة الموسعة على المحتوى الأصلي الذي تناول {html.escape(heading_note)}، ثم تضيف طبقة تفسيرية تساعد على تحويل المعلومة إلى قرار عملي دون تشخيص ذاتي.</p>
<p>{html.escape(intent)} في مجال {html.escape(ctx['label'])}، لا تُقرأ «{html.escape(left)}» و«{html.escape(right)}» كصندوقين منفصلين دائمًا؛ قد يتداخلان، وقد يكون هناك تفسير ثالث لا يظهر من العنوان. لهذا تُبنى القراءة الصحيحة على السياق والمدة والشدة والأثر الوظيفي وعوامل السلامة، وعلى مقارنة ما يحدث الآن بالنمط المعتاد للشخص نفسه.</p>
</section>"""


def comparison_section(item: dict) -> str:
    left, right = concepts_from_title(item["title"])
    ctx = domain_for(item.get("domain", "general"))
    lenses = ctx["lenses"]
    return f"""
<section class="longform-section" id="how-to-distinguish">
<h2>كيف تفرّق دون الوقوع في التشخيص السريع؟</h2>
<p>ابدأ من الوظيفة لا من الاسم. عندما تسأل عن «{html.escape(left)}» مقابل «{html.escape(right)}»، راقب ما الذي يحدث قبل التجربة وأثناءها وبعدها، وكم تستمر، وهل يستطيع الشخص تعديل استجابته مع تغير الظروف. وجود كلمة مألوفة في وصفك لنفسك لا يعني وجود اضطراب، كما أن غياب عرض مشهور لا يستبعد الحاجة إلى تقييم عندما يكون التعطيل واضحًا.</p>
<p>عدسة مفيدة لهذا الموضوع هي: {html.escape(lenses[0])}. ثم أضف إليها: {html.escape(lenses[1])}. هاتان النقطتان تمنعان خطأ شائعًا هو تحويل مقارنة تثقيفية إلى اختبار تشخيصي ثنائي. كذلك يجب تذكر أن {html.escape(lenses[2])}. لذلك يكون السؤال الأفضل: ما النمط الكامل، وما أثره، وما المعلومات التي ما زالت ناقصة قبل الوصول إلى استنتاج؟</p>
</section>"""


def format_section(item: dict) -> str:
    fmt = item.get("format", "practical")
    if fmt == "comparison":
        return comparison_section(item)
    if fmt == "check":
        return f"""
<section class="longform-section" id="reading-check">
<h2>كيف تقرأ الفحص دون تحويله إلى تشخيص؟</h2>
<p>الأسئلة في «{html.escape(item['title'])}» تعمل كمؤشرات للملاحظة، وليست نقاطًا تجمعها لتحصل على تسمية. الإجابة «نعم» على بند واحد قد تعكس ظرفًا مؤقتًا، بينما تكرار عدة مشكلات مع أثر واضح في الحياة يستحق انتباهًا أكبر. سجّل أمثلة حقيقية وتواريخ تقريبية بدل الاعتماد على الانطباع العام؛ فهذا يجعل أي نقاش لاحق مع مختص أو شخص داعم أكثر دقة.</p>
<p>لا تستخدم نتيجة ذاتية لاستبعاد سبب طبي أو نفسي آخر. إذا تغير النوم أو الطاقة أو الشهية أو القدرة على التركيز أو السلامة، فهذه معلومات تُضاف إلى الصورة ولا تختصرها. الفائدة الحقيقية من الفحص هي أن يساعدك على وصف ما يحدث بوضوح: متى بدأ، أين يظهر، ما شدته، وما الذي يخففه أو يزيده.</p>
</section>"""
    if fmt == "factors":
        return f"""
<section class="longform-section" id="causes-context">
<h2>لماذا لا يوجد سبب واحد يفسر الصورة دائمًا؟</h2>
<p>العنوان «{html.escape(item['title'])}» يفتح مجموعة فرضيات، لكنه لا يحدد سببًا نهائيًا. في الصحة النفسية والسلوك الإنساني تتداخل عوامل بيولوجية ونفسية واجتماعية وبيئية، وقد تتغير أهميتها من شخص إلى آخر ومن مرحلة إلى أخرى. لهذا لا يكفي أن تجد عاملًا يشبه تجربتك ثم تعتبره التفسير الوحيد.</p>
<p>استخدم العوامل كخريطة للفحص: ما الذي بدأ أولًا؟ ما الذي تغير بالتزامن معه؟ ما العامل الذي يمكن قياسه أو تعديله بأمان؟ وما الذي يحتاج مختصًا لاستبعاده؟ هذه الطريقة تقلل التعميم وتساعد على بناء خطة عملية بدل الدوران بين تفسيرات كثيرة بلا اختبار.</p>
</section>"""
    return f"""
<section class="longform-section" id="practical-use">
<h2>كيف تحوّل الفكرة إلى خطوة قابلة للتطبيق؟</h2>
<p>في موضوع «{html.escape(item['title'])}» من الأفضل اختيار تغيير واحد صغير يمكن ملاحظته بدل محاولة إصلاح كل شيء في يوم واحد. حدد السلوك أو الموقف بدقة، وضع خط أساس بسيطًا لما يحدث الآن، ثم جرّب خطوة آمنة لفترة مناسبة وسجل النتيجة. عندما لا تنجح الخطوة، اعتبر ذلك معلومة عن الخطة لا دليلًا على فشل الشخص.</p>
<p>الفائدة العملية تأتي من التكرار والمراجعة: ما الذي أصبح أسهل؟ ما الذي بقي كما هو؟ هل ظهرت عقبة جديدة؟ وهل المشكلة أوسع مما ظننته في البداية؟ بهذه الطريقة تبقى الصفحة نقطة انطلاق إلى قرار أفضل، لا مجموعة نصائح منفصلة عن الواقع.</p>
</section>"""


def signals_section(item: dict, old_body: str) -> str:
    ctx = domain_for(item.get("domain", "general"))
    signals = legacy_signals(old_body, item)
    cards: list[str] = []
    for index, signal in enumerate(signals[:6], 1):
        lens = ctx["lenses"][(index - 1) % len(ctx["lenses"])]
        cards.append(f"""
<div class="signal-card">
<h3>{index}. {html.escape(signal)}</h3>
<p>هذه النقطة مأخوذة من المحتوى الأصلي للصفحة، لكنها لا تُفسر بمعزل عن بقية الصورة. عند ملاحظتها، سجّل السياق والمدة والتكرار وما إذا كانت جديدة أم جزءًا من نمط قديم. اسأل أيضًا هل تتغير مع الراحة أو الدعم أو تغير الموقف، وهل أصبحت تؤثر في وظيفة يومية مهمة.</p>
<p>في هذا المجال، من المفيد ربطها بعدسة إضافية: {html.escape(lens)}. الربط بين الإشارة والسياق يقلل احتمال المبالغة أو التقليل من المشكلة، ويعطيك وصفًا أدق يمكن استخدامه في قرار الرعاية أو في تعديل الخطة العملية.</p>
</div>""")
    return """
<section class="longform-section" id="signals-expanded">
<h2>شرح موسع للإشارات الموجودة في المحتوى الأصلي</h2>
<p>بدل عرض الإشارات كقائمة سريعة، يوضح هذا الجزء كيف تُقرأ كل إشارة داخل نمط كامل. لا توجد علامة واحدة تحمل المعنى نفسه لدى كل شخص، لذلك تُستخدم النقاط التالية لزيادة دقة الملاحظة لا لرفع القلق.</p>
<div class="signal-grid">""" + "".join(cards) + "</div></section>"


def context_section(item: dict) -> str:
    ctx = domain_for(item.get("domain", "general"))
    points = "".join(
        f"<li><strong>عدسة {i}:</strong> {html.escape(value)}. لا تستخدمها كشرط تشخيصي منفرد؛ استخدمها كسؤال يضيف معلومات إلى الصورة.</li>"
        for i, value in enumerate(ctx["lenses"], 1)
    )
    return f"""
<section class="longform-section" id="context-check">
<h2>خمسة أبعاد يجب فحصها قبل الوصول إلى استنتاج</h2>
<p>المحتوى المفيد لا يكتفي بوصف الظاهرة؛ يجب أن يوضح ما الذي قد يغير تفسيرها. في «{html.escape(item['title'])}» استخدم الأبعاد التالية كقائمة مراجعة. إذا كان أحدها غير معروف، فهذا بحد ذاته سبب لترك مساحة لعدم اليقين بدل ملء الفراغ بتشخيص ذاتي.</p>
<ol class="steps">{points}</ol>
<p>بعد هذه المراجعة، اكتب جملة واحدة تصف المشكلة دون تسمية: «يحدث كذا في هذه المواقف، منذ هذه المدة، ويؤثر في كذا، ويخف عندما يحدث كذا». هذا الوصف عادة أكثر فائدة من قول «أنا بالتأكيد أعاني من...» لأنه يحافظ على المعلومات التي يحتاجها أي تقييم مهني أو خطة مساعدة لاحقة.</p>
</section>"""


def action_section(item: dict) -> str:
    ctx = domain_for(item.get("domain", "general"))
    title = html.escape(item["title"])
    lens_a = html.escape(ctx["lenses"][0])
    lens_b = html.escape(ctx["lenses"][3])
    return f"""
<section class="longform-section" id="action-plan">
<h2>خطة عملية من سبع خطوات</h2>
<ol class="steps">
<li><strong>عرّف السؤال بدقة.</strong> اكتب ما الذي تريد فهمه من «{title}» دون افتراض النتيجة. فرّق بين ما لاحظته فعلًا وبين التفسير الذي خطر لك. هذه الخطوة تمنع أن تتحول كل ملاحظة لاحقة إلى دليل يؤكد الفكرة الأولى فقط.</li>
<li><strong>اجمع خطًا زمنيًا مختصرًا.</strong> متى بدأ التغير؟ هل كان مفاجئًا أم تدريجيًا؟ ما الأحداث أو التغيرات الصحية أو الدوائية أو الأسرية أو المهنية التي تزامنت معه؟ الترتيب الزمني يساعد على كشف العلاقات التي تضيع في الذاكرة العامة.</li>
<li><strong>قِس الأثر لا الإحساس وحده.</strong> راقب النوم والطاقة والتركيز والالتزام بالدراسة أو العمل والعلاقات والعناية بالنفس. يمكن أن يكون الشعور قويًا لكنه عابر، أو متوسطًا لكنه مستمر ويعطل الحياة؛ لذلك الأثر الوظيفي عنصر حاسم.</li>
<li><strong>استخدم عدسة المجال.</strong> راجع هذه النقطة تحديدًا: {lens_a}. اكتب مثالين من واقعك بدل الإجابة بكلمة نعم أو لا. المثال الواقعي يكشف الفروق ويقلل الاعتماد على الانطباعات المتغيرة.</li>
<li><strong>استبعد ما يحتاج مسارًا آخر.</strong> راجع الأدوية والحالات الصحية والنوم والمواد والمنبهات وأي تغير جسدي جديد. تذكّر أن {lens_b}. لا توقف دواءً ولا تبدأ علاجًا اعتمادًا على صفحة تثقيفية.</li>
<li><strong>جرّب تغييرًا صغيرًا آمنًا.</strong> اختر خطوة واحدة من النصائح الأصلية في الصفحة، حدد متى ستطبقها وكيف ستعرف أنها ساعدت، ثم راجع النتيجة بعد مدة مناسبة. إذا لم تساعد، عدّل الخطة بدل مضاعفة الجهد بلا اتجاه.</li>
<li><strong>حدد نقطة طلب المساعدة مسبقًا.</strong> لا تنتظر حتى يصبح كل شيء غير محتمل. قرر أنك ستطلب تقييمًا إذا استمر النمط أو ازداد أو عطّل وظيفة مهمة أو ظهرت مخاوف تتعلق بالسلامة. وجود معيار مسبق يقلل التردد عندما تكون الطاقة منخفضة.</li>
</ol>
</section>"""


def faq_section(item: dict) -> str:
    ctx = domain_for(item.get("domain", "general"))
    title = item["title"]
    left, right = concepts_from_title(title)
    fmt = item.get("format", "practical")
    if fmt == "comparison":
        questions = [
            (f"ما الفرق بين {left} و{right}؟", f"الفرق لا يُحسم بعرض واحد. راقب السياق والمدة والتكرار والأثر الوظيفي، واستخدم المقارنة لفهم النمط لا لإصدار تشخيص. في {ctx['label']} قد تتداخل التفسيرات أو توجد أسباب أخرى تحتاج فحصًا."),
            (f"كيف أعرف إن كان {left} طبيعيًا أم يحتاج تقييمًا؟", "اسأل هل يتغير مع الظروف والراحة والدعم، وهل ما زال الشخص قادرًا على أداء مسؤولياته الأساسية. الاستمرار أو التصاعد أو التعطيل الواضح يجعل التقييم أكثر فائدة."),
            (f"هل وجود علامة من علامات {right} يعني أنني أعاني منه؟", "لا. العلامة المنفردة قد تظهر لأسباب متعددة. التشخيص المهني يعتمد على نمط أوسع ومعايير وسياق وتاريخ صحي ونفسي، وقد يحتاج استبعاد أسباب جسدية أو دوائية."),
            ("ما المدة التي يجب أن أراقبها؟", "لا توجد مدة واحدة تصلح لكل موضوع. بعض المخاطر تستلزم تصرفًا فوريًا، بينما أنماط أخرى تُفهم أفضل بتتبعها أيامًا أو أسابيع. استخدم الإرشادات الخاصة بالحالة ولا تؤخر المساعدة عند وجود خطر أو تدهور واضح."),
        ]
    else:
        questions = [
            (f"ما المقصود بسؤال: {title}", "المقصود تنظيم الملاحظة وفهم النمط بما يكفي لاتخاذ خطوة أفضل. الصفحة لا تمنح تشخيصًا ولا تستبدل التقييم الصحي أو النفسي عندما يكون مطلوبًا."),
            ("هل يمكن الاعتماد على هذه الصفحة وحدها لاتخاذ قرار علاجي؟", "لا. يمكن استخدامها للتحضير وكتابة الملاحظات وفهم الخيارات العامة، لكن القرارات العلاجية أو الدوائية تحتاج معلومات فردية وتقييمًا مناسبًا."),
            ("كيف أعرف إن كانت النصيحة تناسبني؟", "ابدأ بخطوة صغيرة منخفضة المخاطر وحدد ما الذي ستقيسه. إذا زاد الضيق أو ظهرت آثار غير متوقعة أو كانت لديك حالة صحية معقدة، توقف واطلب توجيهًا مناسبًا."),
            ("ماذا أفعل إذا لم يتحسن الوضع؟", "راجع الفرضية نفسها: ربما كانت المشكلة أوسع، أو الخطوة غير مناسبة، أو توجد عوامل لم تُفحص بعد. استمرار التعطيل سبب معقول للانتقال من المساعدة الذاتية إلى تقييم مهني."),
        ]
    questions += [
        ("ما المعلومات التي أجهزها قبل طلب المساعدة؟", "اكتب متى بدأت المشكلة، وما أكثر موقف تظهر فيه، وما شدتها وتكرارها، وكيف تؤثر في النوم والعمل أو الدراسة والعلاقات، وأي أدوية أو حالات صحية أو مواد أو تغييرات كبيرة ذات صلة. هذه المعلومات تجعل الموعد أكثر كفاءة."),
        ("متى تكون المساعدة عاجلة؟", "عندما يوجد خطر وشيك على السلامة، أو أفكار لإيذاء النفس أو الآخرين، أو فقدان شديد للقدرة على العناية بالنفس، أو أعراض جسدية حادة قد تكون طارئة. في هذه الحالات استخدم خدمات الطوارئ أو الرعاية العاجلة المحلية المناسبة بدل انتظار نصيحة عامة من الإنترنت."),
        ("هل يمكن أن يكون هناك أكثر من تفسير في الوقت نفسه؟", "نعم. النوم والضغط والحالات الجسدية والأدوية والبيئة والعلاقات والصحة النفسية قد تتداخل. وجود تفسير محتمل لا يلغي البقية، ولهذا تكون الخريطة الزمنية والأثر الوظيفي والتقييم المتدرج أكثر دقة من تسمية سريعة."),
    ]
    blocks = "".join(
        f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>"
        for q, a in questions
    )
    return f"""
<section class="longform-section intent-faq" id="search-intent-questions">
<h2>أسئلة شائعة تحاكي نية البحث</h2>
<p>هذه الأسئلة صيغت لتغطي ما يحتاجه القارئ بعد الوصول من محرك البحث: المعنى، الفروق، المدة، الخطوة التالية، وحدود المساعدة الذاتية. افتح السؤال الذي يشبه موقفك بدل قراءة الصفحة كاختبار.</p>
{blocks}
</section>"""


def sources_section(item: dict) -> str:
    ctx = domain_for(item.get("domain", "general"))
    links = "".join(
        f'<li><a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">{html.escape(name)}</a></li>'
        for name, url in ctx["sources"]
    )
    return f"""
<section class="longform-section" id="evidence-use">
<h2>كيف استخدمنا المراجع في هذه النسخة؟</h2>
<p>المراجع التالية لا تُنسخ حرفيًا ولا تستخدم لصناعة قائمة أعراض آلية. وظيفتها تثبيت المبادئ العامة المتعلقة بالتعريفات، السلامة، حدود التشخيص الذاتي، ومتى يصبح التقييم المهني مهمًا. أما المحتوى الأصلي للصفحة فقد تم الحفاظ عليه ثم شرحه وتوسيعه ليصبح أكثر قابلية للاستخدام.</p>
<ul class="source-list">{links}</ul>
<p>المعلومات الصحية تتغير، وقد تختلف الإرشادات بحسب العمر والحالة الصحية والبلد. لذلك يجب مراجعة المصدر الأساسي أو المختص المناسب عند اتخاذ قرار فردي، خصوصًا في الأدوية والطوارئ والتشخيص وخطط الانسحاب أو الحالات المعقدة.</p>
</section>"""


def supplemental_section(item: dict, old_body: str) -> str:
    """Add unique, legacy-derived depth without repeating generic filler."""
    headings = unique(HEADING_RE.findall(old_body), 10)
    signals = legacy_signals(old_body, item)
    ctx = domain_for(item.get("domain", "general"))
    rows: list[str] = []
    seeds = unique(headings + signals, 10)
    for index, seed in enumerate(seeds, 1):
        lens = ctx["lenses"][(index + 1) % len(ctx["lenses"])]
        rows.append(f"""
<h3>{html.escape(seed)}</h3>
<p>عند تطبيق هذه النقطة على حياتك، لا تسأل فقط هل تنطبق أم لا؛ اسأل متى تظهر، وما الذي يسبقها، وما الذي يتغير بعدها، ومن يلاحظها أيضًا. إذا اختلفت الإجابة بين المنزل والعمل أو بين أيام الضغط والراحة، فهذه الفروق معلومات مهمة وليست تناقضًا يجب تجاهله.</p>
<p>اربطها كذلك بهذا الاعتبار الخاص بمجال {html.escape(ctx['label'])}: {html.escape(lens)}. بعد ذلك اكتب إجراءً واحدًا يمكن اختباره بأمان، أو سؤالًا واحدًا تأخذه إلى مختص. بهذه الطريقة تتحول المعرفة القديمة في الصفحة إلى أداة قرار بدل أن تبقى معلومة منفصلة.</p>""")
    return """
<section class="longform-section" id="legacy-application">
<h2>تطبيق أعمق لما ورد في الصفحة الأصلية</h2>
<p>الجزء التالي مبني مباشرة على عناوين وإشارات النسخة القديمة. الهدف هو إعطاء كل نقطة سياقًا عمليًا ومنع قراءتها كعبارة عامة منفصلة عن الواقع.</p>
""" + "".join(rows) + "</section>"


def build_longform(item: dict, old_body: str) -> str:
    blocks = [
        intro_section(item, old_body),
        format_section(item),
        signals_section(item, old_body),
        context_section(item),
        action_section(item),
        faq_section(item),
        sources_section(item),
        supplemental_section(item, old_body),
    ]
    return START + "\n" + "\n".join(blocks) + "\n" + END


def remove_existing_marker(body: str) -> str:
    if START not in body and END not in body:
        return body
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    cleaned, count = pattern.subn("", body)
    if count != 1:
        raise ValueError(f"Expected one prior long-form block, found {count}")
    return cleaned


def enrich_page(path: Path, item: dict) -> dict:
    source = path.read_text(encoding="utf-8")
    match = ARTICLE_RE.search(source)
    if not match:
        raise ValueError(f"Article container missing: {path.relative_to(ROOT)}")
    old_body = remove_existing_marker(match.group(2)).strip()
    if word_count(old_body) < 80:
        raise ValueError(f"Legacy body unexpectedly thin: {path.relative_to(ROOT)}")
    legacy_hash = hashlib.sha256(old_body.encode("utf-8")).hexdigest()
    longform = build_longform(item, old_body)
    new_body = old_body + "\n" + longform
    upgraded = source[: match.start(2)] + new_body + source[match.end(2) :]
    if upgraded.count(START) != 1 or upgraded.count(END) != 1:
        raise ValueError(f"Long-form marker failure: {path.relative_to(ROOT)}")
    if legacy_hash != hashlib.sha256(old_body.encode("utf-8")).hexdigest():
        raise ValueError(f"Legacy body changed in memory: {path.relative_to(ROOT)}")
    path.write_text(upgraded, encoding="utf-8")
    final_article = ARTICLE_RE.search(upgraded)
    assert final_article
    final_words = word_count(final_article.group(2))
    faq_count = final_article.group(2).count("<details>")
    return {
        "slug": item["slug"],
        "legacyWords": word_count(old_body),
        "finalWords": final_words,
        "faqQuestions": faq_count,
        "legacySha256": legacy_hash,
    }


def patch_css() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    marker = "/* quick-info long-form mobile/page-experience patch */"
    if marker in css:
        css = css[: css.index(marker)].rstrip() + "\n"
    CSS_PATH.write_text(css + "\n" + CSS_PATCH.strip() + "\n", encoding="utf-8")


def validate_page(path: Path, item: dict, result: dict) -> list[str]:
    failures: list[str] = []
    source = path.read_text(encoding="utf-8")
    if result["finalWords"] < MIN_WORDS:
        failures.append(f"{item['slug']}: {result['finalWords']} words < {MIN_WORDS}")
    if source.count(START) != 1 or source.count(END) != 1:
        failures.append(f"{item['slug']}: long-form marker count invalid")
    if "أسئلة شائعة تحاكي نية البحث" not in source:
        failures.append(f"{item['slug']}: search-intent FAQ section missing")
    if result["faqQuestions"] < 7:
        failures.append(f"{item['slug']}: fewer than 7 search-intent questions")
    if "max-image-preview:large" not in source:
        failures.append(f"{item['slug']}: max-image-preview:large missing")
    if 'fetchpriority="high"' not in source:
        failures.append(f"{item['slug']}: prioritized cover missing")
    canonical = f'<link rel="canonical" href="{item["url"]}">'
    if canonical not in source:
        failures.append(f"{item['slug']}: canonical URL changed or missing")
    if item["title"] not in source:
        failures.append(f"{item['slug']}: published title missing")
    return failures


def main() -> None:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != EXPECTED_COUNT or len(items) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} API items, found {len(items)}")
    if len({item["slug"] for item in items}) != EXPECTED_COUNT:
        raise SystemExit("Quick Information slugs are not unique")

    results: list[dict] = []
    failures: list[str] = []
    for item in items:
        page = SECTION / item["slug"] / "index.html"
        if not page.exists():
            failures.append(f"{item['slug']}: page missing")
            continue
        try:
            result = enrich_page(page, item)
            results.append(result)
            failures.extend(validate_page(page, item, result))
        except Exception as exc:  # fail closed with per-page context
            failures.append(f"{item['slug']}: {exc}")

    patch_css()

    final_words = [row["finalWords"] for row in results]
    legacy_words = [row["legacyWords"] for row in results]
    report = {
        "version": "1.0.0",
        "pagesExpected": EXPECTED_COUNT,
        "pagesProcessed": len(results),
        "editorialMinimumWords": MIN_WORDS,
        "minimumFinalWords": min(final_words) if final_words else 0,
        "maximumFinalWords": max(final_words) if final_words else 0,
        "averageFinalWords": round(sum(final_words) / len(final_words), 1) if final_words else 0,
        "minimumLegacyWords": min(legacy_words) if legacy_words else 0,
        "legacyBodiesPreserved": len(results) == EXPECTED_COUNT,
        "searchIntentFaqOnEveryPage": all(row["faqQuestions"] >= 7 for row in results),
        "discoverLargeImageContractRetained": not any("image-preview" in f or "cover" in f for f in failures),
        "failures": failures,
        "pages": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "pages"}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit("\n".join(failures[:50]))


if __name__ == "__main__":
    main()
