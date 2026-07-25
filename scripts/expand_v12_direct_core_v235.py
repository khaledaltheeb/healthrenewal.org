from __future__ import annotations

import html
import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = os.environ.get("SITE_BASE", "https://khaledaltheeb.github.io/pterminology-site/")
BASE_PATH = "/" + BASE.split("/", 3)[-1].strip("/") + "/"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SRC = Path("content/v12-direct")
VERIFY = "google644f1f7a8b7aaa2b.html"

PHQ = [
    "قلة الاهتمام أو المتعة في فعل الأشياء", "الشعور بالحزن أو الاكتئاب أو اليأس",
    "صعوبة النوم أو الاستمرار فيه أو النوم أكثر من المعتاد", "الشعور بالتعب أو قلة الطاقة",
    "ضعف الشهية أو الإفراط في الأكل", "الشعور بالسوء تجاه نفسك أو أنك خذلت نفسك أو أسرتك",
    "صعوبة التركيز في القراءة أو مشاهدة التلفاز", "بطء ملحوظ أو حركة وتململ أكثر من المعتاد",
    "أفكار بأن الموت أفضل أو أفكار في إيذاء النفس",
]
GAD = [
    "الشعور بالعصبية أو القلق أو التوتر", "عدم القدرة على إيقاف القلق أو التحكم فيه",
    "القلق المفرط بشأن أمور مختلفة", "صعوبة الاسترخاء", "التململ وصعوبة البقاء ساكنًا",
    "سهولة الانزعاج أو التهيج", "الخوف من حدوث شيء سيئ",
]
WHO5 = [
    "شعرت بالبهجة وبمزاج جيد", "شعرت بالهدوء والاسترخاء", "شعرت بالنشاط والحيوية",
    "استيقظت وأنا أشعر بالانتعاش والراحة", "كانت حياتي اليومية مليئة بأشياء تهمني",
]
AUDIT = [
    "كم مرة تتناول مشروبًا كحوليًا؟", "كم عدد المشروبات في يوم اعتيادي؟",
    "كم مرة تتناول ستة مشروبات أو أكثر في مناسبة واحدة؟", "كم مرة لم تستطع التوقف بعد البدء؟",
    "كم مرة أخفقت في أداء ما كان متوقعًا منك بسبب الشرب؟", "كم مرة احتجت إلى الشرب صباحًا؟",
    "كم مرة شعرت بالذنب أو الندم بعد الشرب؟", "كم مرة لم تتذكر ما حدث في الليلة السابقة؟",
    "هل تعرضت أنت أو شخص آخر لإصابة بسبب شربك؟", "هل أبدى قريب أو مختص قلقه بشأن شربك؟",
]

SCALES = [
    dict(slug="phq-9-plus", title="PHQ-9 — فحص أعراض الاكتئاب", category="مقياس موثق", summary="تقدير أولي لشدة أعراض الاكتئاب خلال الأسبوعين الماضيين.", period="الأسبوعان الماضيان", score_type="phq9", questions=PHQ, options=["أبدًا", "عدة أيام", "أكثر من نصف الأيام", "تقريبًا كل يوم"], source="Patient Health Questionnaire-9", source_url="https://www.nih.gov/node/19946"),
    dict(slug="gad-7-plus", title="GAD-7 — فحص أعراض القلق", category="مقياس موثق", summary="تقدير أولي لشدة أعراض القلق خلال الأسبوعين الماضيين.", period="الأسبوعان الماضيان", score_type="gad7", questions=GAD, options=["أبدًا", "عدة أيام", "أكثر من نصف الأيام", "تقريبًا كل يوم"], source="Generalized Anxiety Disorder-7", source_url="https://www.nih.gov/node/19876"),
    dict(slug="who-5-plus", title="WHO-5 — مؤشر العافية النفسية", category="مقياس موثق", summary="خمسة بنود لقياس العافية النفسية الإيجابية خلال الأسبوعين الماضيين.", period="الأسبوعان الماضيان", score_type="who5", questions=WHO5, options=["في أي وقت", "قليلًا", "أقل من نصف الوقت", "أكثر من نصف الوقت", "معظم الوقت", "طوال الوقت"], source="World Health Organization WHO-5", source_url="https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01"),
    dict(slug="audit-10-guided", title="AUDIT-10 — أسئلة استرشادية حول استخدام الكحول", category="فحص استرشادي موثق المصدر", summary="عرض تثقيفي لبنود AUDIT يساعد على ملاحظة النمط، ولا يحل محل التطبيق المهني أو احتساب الدرجة الرسمية.", period="السنة الماضية", score_type="audit_guided", questions=AUDIT, options=["أبدًا", "نادرًا", "أحيانًا", "غالبًا", "بصورة شديدة"], source="WHO Alcohol Use Disorders Identification Test", source_url="https://www.who.int/publications/i/item/WHO-MSD-MSB-01.6a"),
]

MONITORS = [
    ("mood-daily", "متابعة المزاج اليومية", "المتابعة اليومية", ["المزاج", "الطاقة", "الاهتمام", "القدرة على أداء المهام"]),
    ("sleep-quality", "متابعة جودة النوم", "النوم", ["انتظام النوم", "بدء النوم", "الاستيقاظ", "النشاط النهاري"]),
    ("stress-load", "مؤشر الحمل النفسي", "الضغط النفسي", ["المتطلبات", "الشعور بالسيطرة", "التوتر الجسدي", "الاستعادة"]),
    ("caregiver-strain", "متابعة إجهاد مقدم الرعاية", "الأسرة", ["الإنهاك", "الوقت", "الدعم العملي", "الراحة"]),
    ("parenting-stress", "متابعة ضغط التربية", "الأسرة", ["الصبر", "القواعد", "الدعم", "وقت الاستعادة"]),
    ("family-communication", "مؤشر التواصل الأسري", "الأسرة", ["الاستماع", "الاحترام", "إصلاح الخلاف", "وضوح الطلب"]),
    ("relationship-safety", "مؤشر الأمان في العلاقة", "العلاقات", ["الاحترام", "الحدود", "حرية التعبير", "الأمان"]),
    ("breakup-recovery", "متابعة التعافي بعد الانفصال", "التعافي", ["الاجترار", "الاندفاع للتواصل", "الروتين", "استعادة الذات"]),
    ("grief-adjustment", "متابعة التكيف مع الفقد", "التعافي", ["شدة الحزن", "الوظيفة اليومية", "الدعم", "حمل الذكرى"]),
    ("trauma-recovery", "متابعة التعافي بعد تجربة صادمة", "التعافي", ["الأمان", "الاستثارة", "التجنب", "العودة للحياة"]),
    ("emotional-regulation", "متابعة تنظيم الانفعالات", "المهارات", ["التصاعد", "التهدئة", "تسمية الشعور", "اختيار السلوك"]),
    ("self-compassion", "مؤشر التعاطف مع الذات", "التعافي", ["لغة الذات", "تقبل النقص", "الرعاية", "المرونة"]),
    ("loneliness", "متابعة الوحدة والاتصال", "العلاقات", ["الانتماء", "شخص آمن", "جودة التواصل", "المبادرة"]),
    ("social-support", "خريطة الدعم الاجتماعي", "العلاقات", ["دعم عاطفي", "دعم عملي", "معلومات", "طلب المساعدة"]),
    ("burnout-risk", "متابعة خطر الاحتراق", "العمل والدراسة", ["الإنهاك", "التبلد", "الفاعلية", "الحدود"]),
    ("daily-function", "متابعة الأداء اليومي", "المتابعة اليومية", ["العناية الذاتية", "العمل أو الدراسة", "العلاقات", "المنزل"]),
    ("sensory-overload", "متابعة الحمل الحسي", "الاحتياجات الخاصة", ["الصوت", "الضوء", "الازدحام", "الاستراحة الحسية"]),
    ("executive-function", "متابعة الوظائف التنفيذية", "القدرات اليومية", ["بدء المهمة", "التنظيم", "تذكر الخطوات", "الانتقال"]),
    ("attention-daily", "متابعة الانتباه اليومية", "القدرات اليومية", ["الاستمرار", "المشتتات", "استعادة التركيز", "إنهاء المهمة"]),
    ("school-wellbeing", "مؤشر العافية المدرسية", "الأطفال والمراهقون", ["الأمان", "الانتماء", "الضغط الدراسي", "طلب المساعدة"]),
    ("postpartum-support", "متابعة دعم ما بعد الولادة", "المرأة", ["المزاج", "النوم", "الدعم", "العناية بالنفس"]),
    ("recovery-safety", "خطة أمان التعافي", "السلامة", ["المحفزات", "الإشارات المبكرة", "الأشخاص الداعمون", "خطوات السلامة"]),
    ("autism-family-load", "متابعة احتياجات أسرة طفل متوحد", "الاحتياجات الخاصة", ["الحمل الحسي", "التواصل", "الروتين", "راحة الأسرة"]),
    ("adhd-family-support", "متابعة دعم طفل لديه تشتت وفرط حركة", "الاحتياجات الخاصة", ["البيئة", "التعليمات", "الانتقال", "التعزيز"]),
    ("learning-difficulty-support", "متابعة صعوبات التعلم", "الاحتياجات الخاصة", ["وضوح المهمة", "التكييف", "الثقة", "التعاون المدرسي"]),
    ("speech-language-support", "متابعة دعم التواصل واللغة", "الاحتياجات الخاصة", ["فرص التواصل", "تقليل الضغط", "البدائل", "التعاون العلاجي"]),
    ("intellectual-disability-support", "متابعة دعم الإعاقة الذهنية", "الاحتياجات الخاصة", ["الاستقلال", "المهارات التكيفية", "الأمان", "المشاركة"]),
    ("down-syndrome-family", "متابعة دعم أسرة طفل بمتلازمة داون", "الاحتياجات الخاصة", ["الصحة", "التعلم", "الاستقلال", "الانتماء"]),
    ("cerebral-palsy-family", "متابعة دعم الشلل الدماغي", "الاحتياجات الخاصة", ["الراحة", "الحركة", "التواصل", "المشاركة"]),
    ("hearing-support-family", "متابعة دعم ضعف السمع", "الاحتياجات الخاصة", ["الوصول للتواصل", "البيئة السمعية", "اللغة", "المشاركة"]),
    ("visual-support-family", "متابعة دعم ضعف البصر", "الاحتياجات الخاصة", ["التنقل", "الوصول للمعلومات", "الاستقلال", "الأمان"]),
    ("chronic-illness-family", "متابعة الأسرة مع المرض المزمن", "الأسرة", ["العلاج", "الروتين", "الأدوار", "احتياجات الأسرة"]),
    ("emotionally-detached", "متابعة الانفصال العاطفي", "العلاقات", ["الخدر", "التجنب", "تسمية المشاعر", "القرب الآمن"]),
    ("panic-pattern", "متابعة نمط نوبات الهلع", "القلق", ["المحفزات", "الأعراض الجسدية", "التجنب", "استعادة النشاط"]),
    ("worry-cycle", "متابعة دائرة القلق", "القلق", ["مدة القلق", "طلب الطمأنة", "التجنب", "العودة للحاضر"]),
    ("compulsive-pattern", "متابعة السلوك القهري", "الوسواس", ["المحفز", "الاندفاع", "الطقس", "الأثر اليومي"]),
]

GAMES = [
    ("simple-reaction", "سرعة الاستجابة البسيطة", "السرعة"), ("choice-reaction", "سرعة الاختيار", "السرعة"),
    ("visual-reaction", "الاستجابة البصرية", "السرعة"), ("auditory-symbol", "ربط الرمز بالتعليمات", "السرعة"),
    ("go-no-go", "اذهب أو توقف", "الكبح"), ("stroop-basic", "ستروب الأساسي", "الكبح"),
    ("stroop-advanced", "ستروب المتقدم", "الكبح"), ("response-inhibition", "كبح الاستجابة", "الكبح"),
    ("digit-span-forward", "مدى الأرقام الأمامي", "الذاكرة العاملة"), ("digit-span-backward", "مدى الأرقام العكسي", "الذاكرة العاملة"),
    ("letter-span", "مدى الحروف", "الذاكرة العاملة"), ("spatial-span", "المدى المكاني", "الذاكرة العاملة"),
    ("one-back", "مهمة 1-Back", "الذاكرة العاملة"), ("two-back", "مهمة 2-Back", "الذاكرة العاملة"),
    ("three-back", "مهمة 3-Back", "الذاكرة العاملة"), ("memory-update", "تحديث الذاكرة", "الذاكرة العاملة"),
    ("visual-grid", "ذاكرة الشبكة", "الذاكرة"), ("sequence-memory", "ذاكرة التسلسل", "الذاكرة"),
    ("paired-associates", "الروابط المزدوجة", "الذاكرة"), ("symbol-memory", "ذاكرة الرموز", "الذاكرة"),
    ("visual-search", "البحث البصري", "الانتباه"), ("symbol-search", "بحث الرموز", "الانتباه"),
    ("sustained-attention", "الانتباه المستمر", "الانتباه"), ("divided-attention", "الانتباه المقسم", "الانتباه"),
    ("selective-attention", "الانتباه الانتقائي", "الانتباه"), ("attention-switch", "تحويل الانتباه", "الانتباه"),
    ("number-series", "سلاسل الأرقام", "الاستدلال"), ("matrix-patterns", "المصفوفات الأصلية", "الاستدلال"),
    ("odd-one-out", "العنصر المختلف", "الاستدلال"), ("verbal-analogy", "التناظر اللفظي", "الاستدلال"),
    ("logical-rules", "القواعد المنطقية", "الاستدلال"), ("conditional-reasoning", "الاستدلال الشرطي", "الاستدلال"),
    ("mental-arithmetic", "الحساب الذهني", "المرونة"), ("estimation", "التقدير السريع", "المرونة"),
    ("mental-rotation", "الدوران الذهني", "القدرات المكانية"), ("spatial-relations", "العلاقات المكانية", "القدرات المكانية"),
    ("trail-switching", "المسار المتناوب", "المرونة"), ("task-switching", "تبديل القاعدة", "المرونة"),
    ("planning-steps", "تخطيط الخطوات", "الوظائف التنفيذية"), ("rule-discovery", "اكتشاف القاعدة", "الوظائف التنفيذية"),
    ("priority-planning", "ترتيب الأولويات", "الوظائف التنفيذية"), ("problem-solving", "حل المشكلة", "الوظائف التنفيذية"),
    ("emotion-recognition", "تمييز الانفعالات", "المعالجة الاجتماعية"), ("perspective-taking", "أخذ المنظور", "المعالجة الاجتماعية"),
    ("social-scenarios", "المواقف الاجتماعية", "المعالجة الاجتماعية"), ("context-clues", "قرائن السياق", "اللغة"),
    ("word-categories", "تصنيف الكلمات", "اللغة"), ("semantic-fluency", "الطلاقة الدلالية", "اللغة"),
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def url(path: str) -> str:
    return BASE.rstrip("/") + "/" + path.lstrip("/")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def inject(text: str, close: str, addition: str) -> str:
    if addition in text:
        return text
    return text.replace(close, addition + close, 1) if close in text else text + addition


def monitor(row: tuple[str, str, str, list[str]]) -> dict:
    slug, title, category, domains = row
    questions = [f"{domain}: كان هذا الجانب صعبًا أو أثر في يومي" for domain in domains]
    questions += [f"{domain}: احتجت إلى دعم إضافي في هذا الجانب" for domain in domains]
    questions += [f"{domain}: أريد متابعة تغير هذا الجانب" for domain in domains]
    return dict(slug=slug, title=title, category=category, summary=f"أداة متابعة ذاتية لأربعة محاور مرتبطة بـ{title}. لا تقدم تشخيصًا.", period="الأسبوع الماضي", score_type="monitor", instrument_type="أداة متابعة ذاتية غير تشخيصية", questions=questions, options=["لا ينطبق", "قليلًا", "أحيانًا", "غالبًا", "بدرجة شديدة"])


def page_head(title: str, description: str, canonical: str, data: dict) -> str:
    schema = {"@context": "https://schema.org", "@type": "Quiz", "name": title, "description": description, "url": canonical, "inLanguage": "ar", "isAccessibleForFree": True}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | مصطلحات علم النفس</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><meta name="theme-color" content="#ffd9e8"><meta name="color-scheme" content="light"><link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="مصطلحات علم النفس"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta name="twitter:card" content="summary"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script><script type="application/json" id="lab-definition">{payload}</script></head>'''


def nav() -> str:
    return f'''<header class="lab-v12__hero"><a href="{BASE_PATH}"><img src="{BASE_PATH}assets/logo.svg" alt="مصطلحات علم النفس" style="width:min(280px,80%);height:auto"></a><nav class="game-actions" aria-label="التنقل"><a class="button" href="{BASE_PATH}assessment-lab/">المقاييس والمتابعة</a><a class="button" href="{BASE_PATH}cognitive-lab/">الألعاب والقدرات</a><a class="button" href="{BASE_PATH}sectors/family/">دعم الأسرة</a></nav></header>'''


def footer() -> str:
    return f'''<footer class="marshmallow-surface" style="padding:28px;margin-top:44px;border-radius:28px"><p><strong>مصطلحات علم النفس</strong> — أدوات تثقيفية وتدريبية لا تستبدل التقييم المهني.</p><p><a href="{BASE_PATH}sitemap.xml">خريطة الموقع</a></p></footer><script src="{BASE_PATH}assets/js/app-v10.js" defer></script><script src="{BASE_PATH}assets/js/lab-v12.js" defer></script>'''


def tool_html(item: dict) -> str:
    canonical = url(f"assessment-lab/{item['slug']}/")
    source = ""
    if item.get("source"):
        source = f'''<aside class="lab-v12__card"><h2>المصدر والمنهج</h2><p>{esc(item['source'])}</p><p><a href="{esc(item['source_url'])}" rel="noopener">فتح المصدر الرسمي</a></p></aside>'''
    return page_head(item["title"], item["summary"], canonical, item) + f'''<body><main class="lab-v12">{nav()}<section class="lab-shell"><span class="lab-v12__badge">{esc(item['category'])}</span><h1>{esc(item['title'])}</h1><p>{esc(item['summary'])}</p><p><strong>الفترة:</strong> {esc(item.get('period', ''))}</p><div data-v12-lab="assessment" aria-live="polite"></div>{source}</section>{footer()}</main></body></html>'''


def game_html(item: dict) -> str:
    canonical = url(f"cognitive-lab/{item['slug']}/")
    data = {**item, "stages": 5, "trials_per_stage": 6, "instrument_type": "مهمة تدريبية أصلية غير تشخيصية"}
    return page_head(item["title"], item["summary"], canonical, data) + f'''<body><main class="lab-v12">{nav()}<section class="lab-shell"><span class="lab-v12__badge">{esc(item['category'])}</span><h1>{esc(item['title'])}</h1><p>{esc(item['summary'])}</p><div class="question"><strong>مهم:</strong> النتيجة تدريبية وليست درجة ذكاء سريرية أو تشخيصًا.</div><div data-v12-lab="cognitive" aria-live="polite"></div></section>{footer()}</main></body></html>'''


def index_html(folder: str, title: str, items: list[dict]) -> str:
    description = f"{len(items)} أداة متعددة المراحل مع حفظ التقدم وإظهار النتيجة في أي وقت."
    cards = "".join(f'''<a class="lab-v12__card" href="{BASE_PATH}{folder}/{esc(item['slug'])}/"><span class="lab-v12__badge">{esc(item['category'])}</span><h2>{esc(item['title'])}</h2><p>{esc(item['summary'])}</p><strong>فتح الأداة ←</strong></a>''' for item in items)
    return page_head(title, description, url(folder + "/"), {"count": len(items)}) + f'''<body><main class="lab-v12">{nav()}<section class="lab-v12__hero" style="margin-top:24px"><span class="lab-v12__badge">{len(items)} أداة</span><h1>{esc(title)}</h1><p>{esc(description)}</p></section><section class="lab-v12__grid">{cards}</section>{footer()}</main></body></html>'''


def make_sitemap(filename: str, links: list[str]) -> None:
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for link in links:
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = link
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = "0.75"
    ET.ElementTree(root).write(SITE / filename, encoding="utf-8", xml_declaration=True)


def main() -> None:
    (SITE / "assets/css").mkdir(parents=True, exist_ok=True)
    (SITE / "assets/js").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "marshmallow-v12.css", SITE / "assets/css/marshmallow-v12.css")
    shutil.copy2(SRC / "lab-v12.js", SITE / "assets/js/lab-v12.js")

    assessments = SCALES + [monitor(row) for row in MONITORS]
    games = [dict(slug=slug, title=title, category=category, summary=f"خمس مراحل تدريبية متدرجة في {title}، مع حفظ النتائج وإظهارها في أي وقت.", mode=category, stages=5) for slug, title, category in GAMES]

    for item in assessments:
        write(SITE / "assessment-lab" / item["slug"] / "index.html", tool_html(item))
    for item in games:
        write(SITE / "cognitive-lab" / item["slug"] / "index.html", game_html(item))
    write(SITE / "assessment-lab/index.html", index_html("assessment-lab", "مركز المقاييس والمتابعة النفسية", assessments))
    write(SITE / "cognitive-lab/index.html", index_html("cognitive-lab", "مختبر القدرات والألعاب المعرفية", games))

    css_link = f'<link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css">'
    js_link = f'<script src="{BASE_PATH}assets/js/lab-v12.js" defer></script>'
    patched = 0
    for page in SITE.rglob("*.html"):
        if page.name == VERIFY:
            continue
        text = page.read_text(encoding="utf-8", errors="strict")
        before = text
        text = inject(text, "</head>", css_link)
        text = inject(text, "</body>", js_link)
        if 'name="viewport"' not in text:
            text = inject(text, "</head>", '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">')
        if text != before:
            page.write_text(text, encoding="utf-8")
            patched += 1

    assessment_links = [url("assessment-lab/")] + [url(f"assessment-lab/{x['slug']}/") for x in assessments]
    game_links = [url("cognitive-lab/")] + [url(f"cognitive-lab/{x['slug']}/") for x in games]
    make_sitemap("sitemap-assessment-lab.xml", assessment_links)
    make_sitemap("sitemap-cognitive-lab.xml", game_links)

    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        tree = ET.parse(sitemap)
        root = tree.getroot()
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        current = [node.text for node in root.findall(".//s:loc", namespace)]
        for filename in ("sitemap-assessment-lab.xml", "sitemap-cognitive-lab.xml"):
            link = url(filename)
            if link not in current:
                node = ET.SubElement(root, "sitemap")
                ET.SubElement(node, "loc").text = link
        tree.write(sitemap, encoding="utf-8", xml_declaration=True)

    manifest = {"name": "مصطلحات علم النفس", "short_name": "مصطلحات", "lang": "ar", "dir": "rtl", "start_url": BASE_PATH, "scope": BASE_PATH, "display": "standalone", "background_color": "#fff8fc", "theme_color": "#ffd9e8", "description": "موسوعة ومختبر عربي للصحة النفسية والقدرات.", "shortcuts": [{"name": "المقاييس", "url": BASE_PATH + "assessment-lab/"}, {"name": "القدرات", "url": BASE_PATH + "cognitive-lab/"}]}
    write(SITE / "manifest.webmanifest", json.dumps(manifest, ensure_ascii=False, indent=2))
    service_worker = f"const CACHE='pterminology-v12-direct';const CORE=['{BASE_PATH}','{BASE_PATH}assessment-lab/','{BASE_PATH}cognitive-lab/','{BASE_PATH}assets/css/marshmallow-v12.css','{BASE_PATH}assets/js/lab-v12.js'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE))));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x))))));self.addEventListener('fetch',e=>{{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(x=>{{const y=x.clone();caches.open(CACHE).then(c=>c.put(e.request,y));return x;}}).catch(()=>caches.match('{BASE_PATH}'))));}});"
    write(SITE / "sw.js", service_worker)

    report = {"version": "v12-direct", "assessment_tools": len(assessments), "validated_scales": len(SCALES), "self_monitoring_tools": len(MONITORS), "cognitive_games": len(games), "assessment_stages": len(assessments) * 4, "cognitive_stages": len(games) * 5, "new_indexable_urls": len(assessments) + len(games) + 2, "patched_html": patched}
    write(SITE / "api/build-report-v12.json", json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
