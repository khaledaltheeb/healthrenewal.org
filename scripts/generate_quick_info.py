#!/usr/bin/env python3
"""Generate the Arabic Quick Information section and 150 static pages.

The generator is intentionally deterministic and idempotent. It produces:
- /quick-info/ index and 150 article directories
- 1280x720 JPEG social/Discover cards
- section RSS feed and JSON API
- dedicated sitemap and root-sitemap entries
- homepage navigation/feature links
- a machine-readable validation report

The content is educational, non-diagnostic and sourced from authoritative health
organizations. Strong titles are allowed; misleading clickbait is rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import textwrap
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from quick_info_topics import TOPICS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "quick-info"
ASSET_DIR = ROOT / "assets" / "quick-info"
CARD_DIR = ASSET_DIR / "cards"
REPORT = ROOT / "reports" / "quick-info-discover-150.json"
BASE = "https://healthrenewal.org"
TODAY = "2026-08-04"
BRAND = "روافد"
SECTION = "معلومات سريعة"


def P(summary: str, factors: str, markers: str, actions: str, urgent: str = "") -> dict:
    return {
        "summary": summary,
        "factors": factors.split("|"),
        "markers": markers.split("|"),
        "actions": actions.split("|"),
        "urgent": urgent or "إذا ظهرت خطورة مباشرة، أو أفكار لإيذاء النفس أو الآخرين، أو عجز واضح عن أداء المسؤوليات الأساسية، فاطلب مساعدة عاجلة من خدمات الطوارئ المحلية أو جهة صحية مؤهلة.",
    }


PROFILES = {
    "depression": P(
        "الاكتئاب ليس مجرد يوم سيئ؛ هو نمط مستمر من انخفاض المزاج أو فقدان الاهتمام يؤثر في النوم والطاقة والتفكير والقدرة على العمل أو الدراسة.",
        "ضغوط أو خسائر متراكمة|عوامل بيولوجية ونفسية متداخلة|العزلة ونقص الدعم|مشكلات النوم والألم المزمن|تاريخ شخصي أو عائلي لمشكلات المزاج",
        "انخفاض المزاج معظم اليوم|فقدان المتعة أو الاهتمام|تغير النوم أو الشهية|تعب وصعوبة تركيز|يأس أو شعور بعدم القيمة",
        "دوّن مدة الأعراض وأثرها|حافظ على أساسيات النوم والطعام والحركة|تحدث مع شخص موثوق|احجز تقييمًا مهنيًا عند الاستمرار أو التعطل|لا توقف علاجًا موصوفًا دون الطبيب",
        "الأفكار الانتحارية أو إيذاء النفس أو فقدان القدرة على العناية بالنفس تتطلب مساعدة عاجلة الآن.",
    ),
    "sadness": P(
        "الحزن استجابة إنسانية طبيعية للخسارة أو الإحباط، وغالبًا يتغير مع الوقت والسياق ولا يلغي كل القدرة على الشعور بالمتعة.",
        "خسارة أو خيبة أمل|تغيير مفاجئ|نزاع أو رفض|إجهاد وقلة نوم|ذكرى أو مناسبة مؤثرة",
        "ارتباط الشعور بحدث واضح|وجود فترات تخف فيها الشدة|بقاء بعض الاهتمام بالحياة|القدرة على الاستجابة للدعم|تحسن تدريجي مع الوقت",
        "اسمح بالمشاعر دون جلد الذات|حافظ على روتين بسيط|اطلب صحبة آمنة|راقب المدة والتعطل|اطلب تقييمًا إذا اتسع الأثر أو طال",
    ),
    "anxiety": P(
        "القلق الطبيعي ينبهنا للخطر، لكن القلق الذي يستمر أو يتضخم أو يدفع إلى التجنب ويعطل الحياة يستحق تقييمًا مهنيًا.",
        "عدم اليقين والضغط|قلة النوم والكافيين|تجارب سابقة مخيفة|تجنب متكرر يثبت الخوف|أعباء مالية أو أسرية أو مهنية",
        "تفكير متكرر يصعب إيقافه|توتر عضلي وخفقان|تجنب أماكن أو مهام|صعوبة نوم أو تركيز|بحث متكرر عن الطمأنة",
        "خفف الكافيين تدريجيًا|نظم وقت القلق بدل تركه طوال اليوم|استخدم تنفسًا بطيئًا لا قسريًا|واجه التجنب بخطوات صغيرة وآمنة|اطلب تقييمًا عند التعطل أو الاستمرار",
    ),
    "stress": P(
        "الضغط استجابة لمطالب تتجاوز الموارد المتاحة مؤقتًا. يصبح مشكلة عندما يطول، ولا توجد فترات تعافٍ، ويبدأ بالتأثير في الجسم والعلاقات والقرارات.",
        "تراكم المهام دون أولويات|نزاعات مستمرة|غياب النوم والتعافي|ضغط مالي أو وظيفي|أخبار ومثيرات متواصلة",
        "شد عضلي أو صداع|سرعة انفعال|تشتت ونسيان|تغير الشهية أو النوم|شعور دائم بالعجلة",
        "اخفض عدد المهام المتزامنة|حدد ما يمكن تأجيله أو تفويضه|أنشئ فترات تعافٍ قصيرة|حافظ على الحركة والنوم|اطلب دعمًا عندما تتجاوز المطالب قدرتك",
    ),
    "burnout": P(
        "الاحتراق يرتبط عادة بضغط مزمن غير مُدار، خصوصًا في العمل أو الرعاية، ويظهر كإنهاك وتبلد أو ابتعاد وشعور بانخفاض الفاعلية.",
        "عبء مستمر دون سيطرة|توقعات غير واضحة أو متعارضة|قلة التقدير أو الدعم|غياب الحدود والتعافي|تعارض العمل مع القيم",
        "إنهاك لا يتحسن بعطلة قصيرة|نفور أو تبلد تجاه العمل|انخفاض الإحساس بالإنجاز|أخطاء وتشتت متزايد|أعراض جسدية متكررة",
        "حدد مصادر العبء لا الأعراض فقط|تفاوض على الأولويات والموارد|أعد الحدود وساعات الانقطاع|استخدم الإجازة للتعافي لا للحاق بالعمل|اطلب دعمًا مهنيًا إذا امتد الأثر لكل الحياة",
    ),
    "fatigue": P(
        "التعب قد يكون جسديًا أو نفسيًا أو كليهما، ولا يجوز افتراض أنه كسل قبل مراجعة النوم والصحة والضغط والأدوية ونمط الحياة.",
        "نوم غير كافٍ أو غير منتظم|ضغط نفسي طويل|فقر دم أو اضطراب صحي|أدوية أو مواد مؤثرة|قلة الحركة أو غذاء غير متوازن",
        "صعوبة بدء المهام|ثقل جسدي أو ذهني|بطء التفكير|تراجع القدرة على التحمل|عدم التحسن رغم الراحة المعتادة",
        "راجع النوم والروتين أسبوعين|سجل توقيت التعب وما يسبقه|تحرك تدريجيًا ضمن القدرة|راجع طبيبًا عند الاستمرار أو الأعراض الجسدية|تجنب لوم الذات قبل فهم السبب",
    ),
    "sleep": P(
        "النوم الجيد لا يقاس بالساعات وحدها؛ الانتظام والجودة والتوقيت والشعور باليقظة نهارًا عناصر أساسية أيضًا.",
        "مواعيد متقلبة|ضوء وشاشات ليلية|كافيين أو نيكوتين متأخر|قلق وألم أو اضطراب صحي|بيئة نوم مزعجة",
        "صعوبة الاستغراق|استيقاظ متكرر|استيقاظ مبكر غير مرغوب|نعاس أو تهيج نهاري|اعتماد متزايد على المنبهات",
        "ثبت وقت الاستيقاظ|خفف الضوء والشاشات قبل النوم|اجعل السرير للنوم لا للعمل|قلل الكافيين بعد الظهر|اطلب تقييمًا إذا استمر الأرق أو صاحبته مشكلات تنفس",
    ),
    "attention": P(
        "التركيز يتأثر بالنوم والقلق والضغط والبيئة والمهام. وجود التشتت وحده لا يثبت اضطراب فرط الحركة وتشتت الانتباه.",
        "قلة النوم|مقاطعات الهاتف|القلق والاجترار|مهام غامضة أو كبيرة|ألم أو أدوية أو مشكلات صحية",
        "فقدان مسار المهمة|نسيان التعليمات|التنقل المستمر بين الأعمال|أخطاء سهو|الحاجة إلى وقت أطول للإنجاز",
        "اعمل في مهمة واحدة|قسّم الخطوة التالية بوضوح|أبعد المشتتات المرئية|استخدم مؤقتًا وفواصل|اطلب تقييمًا إذا كان النمط قديمًا ومتعدد البيئات ومعطلًا",
    ),
    "adhd": P(
        "اضطراب فرط الحركة وتشتت الانتباه حالة نمائية تحتاج تاريخًا ممتدًا وأعراضًا في أكثر من بيئة وتأثيرًا وظيفيًا؛ لا يُشخّص من قائمة قصيرة.",
        "عوامل نمائية ووراثية|متطلبات تتجاوز مهارات التنظيم|بيئات كثيرة المشتتات|قلة النوم التي تزيد الأعراض|مشكلات مصاحبة مثل القلق",
        "تشتت مستمر منذ الطفولة|صعوبة تنظيم الوقت والمهام|اندفاع أو حركة داخلية|نسيان متكرر رغم المحاولة|ظهور الأثر في أكثر من سياق",
        "اجمع أمثلة من أكثر من بيئة|راجع النوم والسمع والبصر والصحة|استخدم بنية وروتينًا بصريًا|اطلب تقييمًا شاملًا لا اختبارًا إلكترونيًا فقط|نسق الدعم في المنزل أو المدرسة أو العمل",
    ),
    "social": P(
        "الخجل سمة أو شعور مؤقت، أما القلق الاجتماعي فيتضمن خوفًا ملحوظًا من التقييم قد يؤدي إلى تجنب ومعاناة وتعطل.",
        "تجارب إحراج أو تنمر|نقد متكرر|توقعات كمالية|تجنب يثبت الخوف|استعداد شخصي مع ضغط بيئي",
        "خوف شديد قبل المواقف|مراقبة الذات أثناء الحديث|تجنب لقاءات أو عروض|اجترار ما حدث بعده|تأثير في الدراسة أو العمل أو العلاقات",
        "حضّر خطوة اجتماعية صغيرة|وجّه الانتباه للخارج|تجنب استخدام الكحول كحل|تدرج في المواجهة الآمنة|اطلب علاجًا نفسيًا مبنيًا على الدليل عند التعطل",
    ),
    "relationship": P(
        "العلاقة الصحية لا تخلو من الخلاف، لكنها تحافظ على الأمان والاحترام والاختيار والقدرة على الاعتراض دون خوف أو عقاب.",
        "تواصل غامض|حدود غير متفق عليها|تفاوت القوة أو الاعتماد|خبرات تعلق سابقة|ضغوط خارجية غير مُدارة",
        "الخوف من قول الرأي|تكرار الإهانة أو التهديد|مراقبة وعزل وسيطرة|اعتذارات دون تغير سلوكي|تحمل طرف واحد لكل الإصلاح",
        "قيّم النمط المتكرر لا الوعود|اكتب حدودًا قابلة للتطبيق|حافظ على شبكة دعم مستقلة|خطط للأمان عند وجود تهديد أو عنف|اطلب استشارة متخصصة عند الاستنزاف أو الخوف",
        "عند وجود عنف أو تهديد أو ابتزاز أو مراقبة خطرة، قدم الأمان على المواجهة المباشرة واطلب دعمًا محليًا متخصصًا.",
    ),
    "attachment": P(
        "التعلق المؤلم يظهر عندما تصبح الطمأنينة والقيمة والقدرة على الاستمرار مرتبطة بشخص واحد، مع مراقبة أو تنازلات أو خوف شديد من الفقد.",
        "خوف قديم من الهجر|علاقة متقطعة التعزيز|عزلة وضعف مصادر الدعم|انخفاض تقدير الذات|غياب الحدود الواضحة",
        "تفكير قهري بالشخص|مراقبة مستمرة|قبول أذى لتجنب الفقد|إهمال النوم والعمل والأصدقاء|هلع عند المسافة الطبيعية",
        "أوقف دوائر المراقبة تدريجيًا|أعد بناء الروتين والعلاقات الأخرى|اكتب الحقائق لا التخيلات|ضع حدود اتصال واضحة|اطلب دعمًا نفسيًا إذا تعطل يومك",
    ),
    "breakup": P(
        "ألم الانفصال قد يشبه الانسحاب لأن الروتين والهوية والتوقعات تتغير دفعة واحدة. التعافي ليس نسيانًا سريعًا بل استعادة القدرة على العيش والاختيار.",
        "فقد الروتين والهوية المشتركة|غياب الإغلاق أو الإجابات|تعزيز متقطع قبل الانفصال|عزلة بعد العلاقة|مثالية الذاكرة وانتقاء اللحظات الجميلة",
        "مراقبة الحسابات|إعادة المحادثات ذهنيًا|تجاهل أسباب الانفصال|تعطل النوم أو العمل|عودة متكررة رغم الأذى",
        "حدد فترة انقطاع أو تواصل ضروري فقط|احذف محفزات المراقبة لا الذكريات كلها|استعد روتين النوم والطعام|اطلب دعمًا لا تجسسًا|راجع مختصًا إذا استمر التعطل أو الخطر",
    ),
    "boundaries": P(
        "الحدود توضح ما تقبله وما ستفعله لحماية نفسك؛ ليست وسيلة للتحكم في الآخر ولا عقابًا صامتًا.",
        "الخوف من الرفض|تربية تربط الطاعة بالمحبة|عدم وضوح الاحتياجات|اعتماد مالي أو عاطفي|تجارب سابقة مع العقاب عند الرفض",
        "الموافقة مع الاستياء|شرح مفرط لكل رفض|الشعور بالذنب بعد حماية الوقت|السماح بتكرار الإهانة|تحمل نتائج قرارات الآخرين",
        "استخدم جملة قصيرة وواضحة|حدد الإجراء الذي ستتخذه أنت|ابدأ بحد صغير قابل للتطبيق|توقع مقاومة دون التراجع التلقائي|اطلب دعمًا عند وجود خوف أو اعتماد خطِر",
    ),
    "loneliness": P(
        "الوحدة شعور بنقص الاتصال المُرضي، وقد تحدث وسط الناس. العزلة المختارة قد تكون مريحة، لكن الانسحاب المؤلم يضيق الحياة بمرور الوقت.",
        "علاقات سطحية أو غير آمنة|انتقال أو فقد|قلق اجتماعي|عمل أو دراسة عن بُعد|استخدام رقمي يزاحم الاتصال الحقيقي",
        "شعور بعدم الفهم|غياب شخص يمكن التواصل معه|تجنب رغم الرغبة بالقرب|تعب بعد تواصل غير أصيل|زيادة الاجترار ليلًا",
        "ابدأ باتصال واحد منتظم|اختر نشاطًا متكررًا لا لقاءً وحيدًا|قلل المقارنة الرقمية|تحدث بصدق تدريجيًا|اطلب دعمًا إذا ارتبطت الوحدة باليأس",
    ),
    "digital": P(
        "المشكلة الرقمية لا تحددها الساعات وحدها، بل فقدان السيطرة واستمرار الاستخدام رغم الضرر في النوم أو الدراسة أو العلاقات أو السلامة.",
        "تصميم التطبيقات القائم على المكافأة|الملل والقلق|إشعارات مستمرة|غياب بدائل سهلة|استخدام الهاتف لتنظيم المشاعر",
        "فتح تلقائي دون هدف|تأخير النوم|فشل محاولات التقليل|توتر عند الابتعاد|إهمال مهام أو علاقات",
        "أوقف الإشعارات غير الضرورية|أبعد الهاتف عن السرير|حدد نوافذ استخدام|اجعل البديل جاهزًا|اطلب دعمًا إذا فشلت المحاولات وتضررت الحياة",
    ),
    "addiction": P(
        "الإدمان يتضمن صعوبة مستمرة في التحكم واستخدامًا أو سلوكًا يستمر رغم الضرر. الأخلاق أو قوة الإرادة وحدهما لا تفسران الحالة ولا تعالجانها.",
        "تعرض متكرر مع قابلية فردية|ضغط أو صدمة أو ألم|بيئة تسهل الوصول|اضطرابات نفسية مصاحبة|ضعف الدعم والعلاج",
        "فقدان السيطرة|زيادة الوقت أو الكمية|استمرار رغم الضرر|أعراض انسحاب أو اشتهاء|تعطل الأسرة أو العمل أو الصحة",
        "قيّم السلامة وخطر الجرعة أو الانسحاب|اطلب تقييمًا متخصصًا|ضع خطة تمنع القيادة والعنف والوصول للأطفال|ادعم العلاج دون تغطية الضرر|جهز خطة انتكاس واضحة",
        "فقد الوعي أو بطء التنفس أو تشنجات أو ارتباك شديد أو انسحاب خطِر تتطلب طوارئ فورية.",
    ),
    "panic": P(
        "نوبة الهلع اندفاع مفاجئ من خوف شديد وأعراض جسدية يبلغ ذروته خلال دقائق، وقد يبدو كخطر طبي؛ التقييم مهم خصوصًا في أول مرة أو مع أعراض غير معتادة.",
        "ضغط متراكم|حساسية لإشارات الجسم|كافيين أو منبهات|تجنب يضخم الخوف|أسباب صحية يجب استبعادها",
        "خفقان وضيق نفس|دوخة أو تنميل|شعور بفقد السيطرة|خوف من الموت|ذروة سريعة ثم هبوط تدريجي",
        "اجلس في مكان آمن|أبطئ الزفير دون فرط تنفس|ذكّر نفسك أن الموجة ستنخفض|لا تقد السيارة أثناء الأعراض|اطلب تقييمًا طبيًا عند أول نوبة أو ألم صدر غير معتاد",
    ),
    "ocd": P(
        "الأفكار الدخيلة شائعة، لكن الوسواس القهري يتضمن أفكارًا أو دوافع متكررة وطقوسًا أو سلوكيات ذهنية لتخفيف القلق، مع استهلاك وقت أو تعطيل.",
        "قابلية فردية|تفسير الفكرة كخطر أو حقيقة|طلب طمأنة متكرر|طقوس تجنب وفحص|ضغط يزيد الأعراض",
        "فحص أو تنظيف متكرر|طلب طمأنة لا يكفي|طقوس عقلية أو عد|خوف مبالغ من المسؤولية|استهلاك وقت وتعطل",
        "لا تجادل كل فكرة|قلل الطمأنة القهرية تدريجيًا|سجل الطقوس والوقت|اطلب علاج التعرض ومنع الاستجابة لدى مختص|لا توقف دواءً موصوفًا دون الطبيب",
    ),
    "bipolar": P(
        "الاضطراب ثنائي القطب لا يعني تغير المزاج خلال اليوم؛ يتضمن نوبات مميزة من تغير المزاج والطاقة والنشاط والنوم والسلوك تستمر وتؤثر بوضوح.",
        "عوامل وراثية وبيولوجية|اضطراب النوم|ضغط أو مواد|توقف علاج موصوف|تغيرات كبيرة في الروتين",
        "قلة حاجة للنوم مع طاقة مرتفعة|كلام أو أفكار متسارعة|اندفاع ومخاطر غير معتادة|فترات اكتئاب واضحة|تغير ملحوظ يراه الآخرون",
        "سجل النوم والطاقة والسلوك|تجنب التشخيص من منشور|راجع طبيبًا نفسيًا للتقييم|حافظ على انتظام النوم|اطلب مساعدة عاجلة عند السلوك الخطِر أو الذهان",
    ),
    "procrastination": P(
        "التسويف تأجيل رغم توقع الضرر، وغالبًا تحركه صعوبة المهمة أو الخوف أو الكمالية أو ضعف التنظيم، لا غياب الأخلاق.",
        "مهمة غامضة أو ضخمة|خوف من الفشل أو النجاح|كمالية|طاقة منخفضة أو تشتت|مكافأة فورية من الهاتف أو نشاط أسهل",
        "انتظار المزاج المناسب|التخطيط بدل البدء|العمل تحت ضغط اللحظة الأخيرة|جلد الذات ثم تكرار التأجيل|تجنب مهمة محددة مرارًا",
        "حدد خطوة في خمس دقائق|اخفض معيار البداية|استخدم موعد بدء لا موعد انتهاء فقط|أبعد المكافآت الفورية|راجع القلق أو ADHD أو الاكتئاب عند التعطل المزمن",
    ),
    "eating": P(
        "الأكل العاطفي استخدام الطعام لتعديل شعور مثل القلق أو الملل أو الحزن، وقد يحدث دون جوع جسدي واضح. لا يعني وحده وجود اضطراب أكل.",
        "حرمان شديد أو حمية قاسية|ضغط أو ملل|قلة نوم|ارتباط الطعام بالمكافأة|صعوبة تسمية المشاعر",
        "رغبة مفاجئة بطعام محدد|الأكل بسرعة أو دون انتباه|الاستمرار بعد الشبع|شعور بالذنب|تكرر الأكل بعد موقف انفعالي",
        "انتظم في الوجبات|سمّ الشعور قبل الأكل|جهز بدائل تهدئة غير غذائية|تجنب العقاب والحرمان التالي|اطلب مختصًا عند النوبات أو التعويض أو الخطر الصحي",
    ),
    "anger": P(
        "الغضب إشارة وليس تشخيصًا. قد يخفي خوفًا أو ألمًا أو إنهاكًا أو حدودًا منتهكة، لكن لا يبرر الإهانة أو العنف.",
        "قلة نوم|ضغط وألم|شعور بالعجز|توقعات غير واقعية|قلق أو اكتئاب يظهران كتهيج",
        "ارتفاع الصوت بسرعة|شد جسدي|ندم متكرر|تكسير أو تهديد|تأثير في الأسرة أو العمل",
        "ابتعد مؤقتًا قبل التصعيد|سمّ المحفز والحاجة|اخفض الكافيين وعالج النوم|تعلم تواصلًا حازمًا|اطلب مساعدة عاجلة عند خطر العنف",
    ),
    "child": P(
        "سلوك الطفل رسالة عن مهارة أو حاجة أو ضغط، وليس حكمًا على شخصيته. التقييم يعتمد على العمر والمدة والبيئة والأثر.",
        "تغير الروتين|نوم أو جوع|ضغط أسري أو مدرسي|صعوبة تواصل|احتياج حسي أو نمائي",
        "تغير مفاجئ ومستمر|تعطل المدرسة أو اللعب|أعراض جسدية متكررة|تجنب أو خوف شديد|فقد مهارات أو تراجع واضح",
        "راقب ما يحدث قبل السلوك وبعده|ثبت الروتين والتوقعات|استخدم لغة بسيطة|نسق مع المدرسة والطبيب|اطلب تقييمًا نمائيًا أو نفسيًا عند الاستمرار",
    ),
    "teen": P(
        "المراهق يحتاج إنصاتًا يحفظ كرامته وسلامته. التغيرات الطبيعية لا تفسر كل انسحاب أو يأس أو تراجع حاد.",
        "ضغط دراسي واجتماعي|تنمر أو رفض|اضطراب نوم|نزاعات أسرية|قلق أو اكتئاب أو استخدام مواد",
        "انسحاب مستمر|تراجع دراسي حاد|تغير نوم أو أكل|حديث عن اليأس أو الموت|إهمال النظافة أو الأنشطة",
        "ابدأ بالملاحظة لا الاتهام|اسأل مباشرة عن الأمان|استمع قبل تقديم الحلول|احفظ الخصوصية مع حدود السلامة|اطلب تقييمًا سريعًا عند أفكار إيذاء النفس",
        "أي حديث عن الانتحار أو إيذاء النفس يُؤخذ بجدية ويتطلب إشرافًا ومساعدة عاجلة، ولا يُترك المراهق وحده عند الخطر.",
    ),
    "sensory": P(
        "الإنهاك أو الانهيار الحسي استجابة لتراكم مثيرات تتجاوز قدرة التنظيم، وليس تلاعبًا متعمدًا. يحتاج تقليل المثيرات وأمانًا قبل التعليم أو النقاش.",
        "ضوضاء أو إضاءة|ملابس أو لمس|ازدحام وتغير مفاجئ|جوع وتعب|صعوبة تواصل الاحتياج",
        "تغطية الأذنين أو الهروب|فقد القدرة على الكلام أو الاستجابة|تصاعد بعد بيئة مزدحمة|حركات تنظيمية متكررة|تحسن في مكان هادئ",
        "قلل الكلام والمثيرات|وفر مكانًا آمنًا|لا تعاقب أثناء الانهيار|سجل المحفزات والإنذارات المبكرة|اطلب تقييم علاج وظيفي أو نمائي عند التكرار",
    ),
    "caregiver": P(
        "إنهاك مقدم الرعاية قد يتطور ببطء بسبب المسؤولية المستمرة وقلة النوم والعزلة. طلب الدعم جزء من الرعاية وليس تخليًا عنها.",
        "رعاية دون بديل|سهر ومراقبة مستمرة|أعباء مالية|شعور بالذنب عند الراحة|غياب الدعم والخدمات",
        "نفاد الصبر|مشكلات نوم وصحة|عزلة|فقد الاهتمام|شعور بالعجز أو التبلد",
        "حدد مهام يمكن مشاركتها|اطلب فترات راحة منتظمة|حافظ على فحوصك وصحتك|ضع خطة طوارئ وبديل رعاية|اطلب دعمًا نفسيًا أو اجتماعيًا مبكرًا",
    ),
}

ALIASES = [
    (r"اكتئاب|مكتئب|مزاجك منخفض", "depression"),
    (r"حزن|فقد", "sadness"),
    (r"احتراق", "burnout"),
    (r"إرهاق|متعب|تعب|استنزف|استنزاف", "fatigue"),
    (r"قلق|تفكير|اجترار|رأي الناس|مواجهة|رفض", "anxiety"),
    (r"ضغط|التوتر", "stress"),
    (r"أرق|نوم|قيلولة|كابوس|الثالثة صباح", "sleep"),
    (r"ADHD|تشتت|تركيز|نسيان|ذاكرة", "adhd"),
    (r"هلع|خوف طبيعي", "panic"),
    (r"وسواس", "ocd"),
    (r"ثنائي القطب|تقلب مزاج", "bipolar"),
    (r"تسويف|كسل", "procrastination"),
    (r"أكل|شهية|جوع", "eating"),
    (r"هاتف|رقمي|ألعاب|أخبار", "digital"),
    (r"إدمان|ينتكس|انتكاس", "addiction"),
    (r"طفل|كلام", "child"),
    (r"مراهق", "teen"),
    (r"حسي|انهيار", "sensory"),
    (r"مقدم الرعاية", "caregiver"),
    (r"غضب|عصبية", "anger"),
    (r"خجل|اجتماعي|الناس", "social"),
    (r"تعلق|اشتياق|تشتاق|الحنين|شخص قديم|غير متاح", "attachment"),
    (r"انفصال|الخيانة|إغلاق", "breakup"),
    (r"حدود|تقول لا|الرفض|مسؤوليات الآخرين|إرضاء", "boundaries"),
    (r"وحدة|عزلة|انطواء", "loneliness"),
    (r"علاقة|شريك|الحب|حب|غيرة|مراقبة|اعتذار|تجاهل|صمت|التملك|النقد|التلاعب|مسافة", "relationship"),
]

SOURCES = {
    "depression": [("منظمة الصحة العالمية: الاكتئاب", "https://www.who.int/ar/news-room/fact-sheets/detail/depression"), ("NIMH: Depression", "https://www.nimh.nih.gov/health/topics/depression")],
    "anxiety": [("NIMH: Anxiety Disorders", "https://www.nimh.nih.gov/health/topics/anxiety-disorders"), ("منظمة الصحة العالمية: الاضطرابات النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-disorders")],
    "sleep": [("CDC: About Sleep", "https://www.cdc.gov/sleep/about/index.html"), ("NHLBI: Sleep Deprivation and Deficiency", "https://www.nhlbi.nih.gov/health/sleep-deprivation")],
    "adhd": [("NIMH: ADHD", "https://www.nimh.nih.gov/health/topics/attention-deficit-hyperactivity-disorder-adhd"), ("CDC: ADHD", "https://www.cdc.gov/adhd/about/index.html")],
    "addiction": [("WHO: Substance use", "https://www.who.int/health-topics/drugs-psychoactive"), ("SAMHSA: Find Support", "https://www.samhsa.gov/find-support")],
    "child": [("UNICEF: Mental health and well-being", "https://www.unicef.org/parenting/mental-health"), ("NIMH: Children and Mental Health", "https://www.nimh.nih.gov/health/publications/children-and-mental-health")],
    "relationship": [("WHO: Violence against women", "https://www.who.int/news-room/fact-sheets/detail/violence-against-women"), ("APA: Relationships", "https://www.apa.org/topics/relationships")],
    "general": [("NIMH: Health Topics", "https://www.nimh.nih.gov/health/topics"), ("منظمة الصحة العالمية: الاضطرابات النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-disorders")],
}

PALETTES = {
    "مقارنات": ((8, 95, 91), (109, 211, 202), "↔"),
    "فحوص توعوية": ((75, 41, 112), (192, 164, 232), "؟"),
    "أسباب وعلامات": ((126, 56, 88), (238, 174, 196), "5"),
    "العلاقات والتعافي": ((120, 52, 92), (245, 191, 207), "♡"),
    "النوم والعادات": ((25, 52, 96), (132, 164, 220), "☾"),
    "الأسرة والنمو": ((116, 84, 20), (231, 203, 129), "+"),
}


def profile_key(text: str) -> str:
    for pattern, key in ALIASES:
        if re.search(pattern, text):
            return key
    return "stress"


def profile(text: str) -> dict:
    return PROFILES[profile_key(text)]


def split_comparison(title: str) -> tuple[str, str]:
    clean = re.sub(r"[؟?].*$", "", title)
    if " أم " in clean:
        left, right = clean.split(" أم ", 1)
        return left.strip(), right.strip()
    return "التجربة العابرة", "النمط المستمر"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def li(items: list[str]) -> str:
    return "".join(f"<li>{esc(x)}</li>" for x in items)


def sources_for(title: str) -> list[tuple[str, str]]:
    key = profile_key(title)
    if key in ("depression", "bipolar", "ocd", "panic"):
        return SOURCES.get("depression", []) + SOURCES["general"][:1]
    if key in ("anxiety", "stress", "burnout", "social"):
        return SOURCES["anxiety"] + SOURCES["general"][:1]
    if key == "sleep":
        return SOURCES["sleep"] + SOURCES["general"][:1]
    if key == "adhd":
        return SOURCES["adhd"] + SOURCES["general"][:1]
    if key in ("addiction", "digital"):
        return SOURCES["addiction"] + SOURCES["general"][:1]
    if key in ("child", "teen", "sensory", "caregiver"):
        return SOURCES["child"] + SOURCES["general"][:1]
    if key in ("relationship", "attachment", "breakup", "boundaries"):
        return SOURCES["relationship"] + SOURCES["general"][:1]
    return SOURCES["general"]


def quick_answer(title: str, kind: str) -> str:
    p = profile(title)
    if kind == "comparison":
        a, b = split_comparison(title)
        return f"الفرق بين {a} و{b} لا يُحسم بكلمة واحدة. راقب المدة والشدة والسياق والأثر على النوم والعمل والعلاقات. {p['summary']}"
    if kind == "check":
        return f"هذا فحص توعوي يساعدك على ملاحظة النمط، وليس اختبار تشخيص. {p['summary']}"
    if kind == "five":
        return f"هذه عوامل محتملة وليست حكمًا نهائيًا أو قائمة تشخيص. {p['summary']}"
    return p["summary"]


def comparison_block(title: str) -> str:
    left, right = split_comparison(title)
    lp, rp = profile(left), profile(right)
    rows = [
        ("الفكرة الأساسية", lp["summary"], rp["summary"]),
        ("المدة", "غالبًا يتغير مع السبب والراحة والدعم.", "قد يستمر أو يتكرر ويحتاج تقييمًا إذا عطّل الحياة."),
        ("الأثر", "يمكن أن يبقى الأداء ممكنًا مع بعض الصعوبة.", "قد يظهر تعطّل واضح في النوم أو الدراسة أو العمل أو العلاقات."),
        ("الخطوة التالية", lp["actions"][0], rp["actions"][3]),
    ]
    table = "".join(f"<tr><th>{esc(r[0])}</th><td>{esc(r[1])}</td><td>{esc(r[2])}</td></tr>" for r in rows)
    return f"""
    <section class="article-section"><h2>كيف تفرق بينهما؟</h2>
      <div class="table-wrap"><table><thead><tr><th>المعيار</th><th>{esc(left)}</th><th>{esc(right)}</th></tr></thead><tbody>{table}</tbody></table></div>
      <p class="micro-note">المقارنة للتثقيف فقط؛ قد تجتمع الحالتان أو تتداخلان، ولا يكفي هذا الجدول للتشخيص.</p>
    </section>
    <section class="article-section two"><article><h2>علامات مرتبطة بـ{esc(left)}</h2><ul>{li(lp['markers'])}</ul></article><article><h2>علامات مرتبطة بـ{esc(right)}</h2><ul>{li(rp['markers'])}</ul></article></section>
    """


def check_block(title: str) -> str:
    p = profile(title)
    questions = [
        f"هل تكرر معك: {x.rstrip('؟')}؟" for x in p["markers"]
    ] + [
        "هل استمر النمط بدل أن يكون يومًا عابرًا؟",
        "هل أثّر في نومك أو دراستك أو عملك؟",
        "هل دفعك إلى التجنب أو العزلة؟",
        "هل لاحظه شخص قريب منك؟",
        "هل حاولت التعامل معه ولم يتحسن؟",
    ]
    return f"""
    <section class="article-section"><h2>أسئلة المراجعة الذاتية</h2><ol class="checklist">{li(questions[:10])}</ol>
      <div class="notice"><strong>كيف تقرأ الإجابات؟</strong><p>لا تجمع النقاط لتشخيص نفسك. وجود إجابة «نعم» يعني أن هذه المنطقة تستحق المراقبة، بينما تكرار عدة مؤشرات مع استمرارها أو تعطيلها للحياة يجعل التقييم المهني خطوة معقولة.</p></div>
    </section>
    """


def five_block(title: str) -> str:
    p = profile(title)
    cards = "".join(
        f"<article class='point-card'><span>{i}</span><h3>{esc(factor)}</h3><p>{esc(p['summary'])}</p></article>"
        for i, factor in enumerate(p["factors"], 1)
    )
    return f"<section class='article-section'><h2>العوامل الخمسة</h2><div class='point-grid'>{cards}</div><p class='micro-note'>وجود عامل واحد لا يثبت سببًا أو تشخيصًا؛ الهدف هو فتح أسئلة أدق قبل اتخاذ قرار.</p></section>"


def standard_block(title: str) -> str:
    p = profile(title)
    cards = "".join(
        f"<article class='point-card'><span>{i}</span><h3>{esc(item)}</h3><p>راقب تكرار هذا النمط وسياقه وأثره، ولا تحكم من موقف واحد.</p></article>"
        for i, item in enumerate(p["markers"], 1)
    )
    return f"<section class='article-section'><h2>ما الذي يستحق الانتباه؟</h2><div class='point-grid'>{cards}</div></section>"


def article_body(title: str, kind: str) -> str:
    p = profile(title)
    special = comparison_block(title) if kind == "comparison" else check_block(title) if kind == "check" else five_block(title) if kind == "five" else standard_block(title)
    actions = "".join(f"<li><strong>خطوة {i}:</strong> {esc(x)}</li>" for i, x in enumerate(p["actions"], 1))
    src = "".join(f"<li><a href='{esc(url)}' rel='noopener noreferrer'>{esc(name)}</a></li>" for name, url in sources_for(title))
    faqs = [
        ("هل تكفي هذه الصفحة للتشخيص؟", "لا. التشخيص يعتمد على تاريخ كامل، ومدة الأعراض، والأثر الوظيفي، واستبعاد أسباب صحية أو دوائية أو بيئية."),
        ("متى يكون طلب المساعدة مناسبًا؟", "عندما يستمر النمط، أو يتصاعد، أو يؤثر في النوم أو الدراسة أو العمل أو العلاقات، أو عندما تفشل محاولات التعامل الذاتية."),
        ("هل التحسن ممكن؟", "في أغلب المشكلات النفسية والسلوكية توجد تدخلات فعالة، لكن الخطة المناسبة تختلف بحسب الشخص والسياق ودرجة الخطورة."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)
    return f"""
      <section class="answer-box"><p class="eyebrow">الخلاصة خلال 30 ثانية</p><p>{esc(quick_answer(title, kind))}</p></section>
      {special}
      <section class="article-section"><h2>ما الذي يمكنك فعله اليوم؟</h2><ol class="steps">{actions}</ol></section>
      <section class="article-section warning"><h2>متى لا تنتظر؟</h2><p>{esc(p['urgent'])}</p></section>
      <section class="article-section"><h2>خطأ شائع</h2><p>لا تستخدم عنوانًا أو قائمة قصيرة لوضع تشخيص على نفسك أو على شخص آخر. ركز على السلوك المتكرر والأثر والاحتياج إلى الأمان أو الدعم.</p></section>
      <section class="article-section"><h2>أسئلة شائعة</h2><div class="faq">{faq_html}</div></section>
      <section class="article-section sources"><h2>مصادر موثوقة للقراءة</h2><ul>{src}</ul><p>تُراجع الصفحات دوريًا وفق <a href="/editorial-methodology/">المنهجية التحريرية</a> و<a href="/trust/">منهجية الثقة والمصادر</a>.</p></section>
    """


def schema(title: str, slug: str, image_url: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{BASE}/quick-info/{slug}/#article",
                "headline": title,
                "description": quick_answer(title, next(row[2] for row in TOPICS if row[0] == slug))[:300],
                "image": {"@type": "ImageObject", "url": image_url, "width": 1280, "height": 720},
                "datePublished": TODAY,
                "dateModified": TODAY,
                "inLanguage": "ar",
                "isAccessibleForFree": True,
                "author": {"@type": "Organization", "name": "فريق روافد للتحرير الصحي", "url": f"{BASE}/editorial-methodology/"},
                "publisher": {"@type": "Organization", "name": BRAND, "url": f"{BASE}/", "logo": {"@type": "ImageObject", "url": f"{BASE}/assets/brand/logo-mark.svg"}},
                "mainEntityOfPage": f"{BASE}/quick-info/{slug}/",
                "about": {"@type": "Thing", "name": "الصحة النفسية والتثقيف الصحي"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": SECTION, "item": f"{BASE}/quick-info/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": f"{BASE}/quick-info/{slug}/"},
                ],
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def page_html(idx: int, slug: str, title: str, kind: str, category: str, related: list[tuple]) -> str:
    canonical = f"{BASE}/quick-info/{slug}/"
    image_url = f"{BASE}/assets/quick-info/cards/{slug}.jpg"
    description = quick_answer(title, kind)[:290]
    related_html = "".join(f"<a class='related-card' href='/quick-info/{r[0]}/'><small>{esc(r[3])}</small><strong>{esc(r[1])}</strong></a>" for r in related)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)} | {SECTION} | {BRAND}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{BRAND}">
<meta property="og:url" content="{canonical}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{image_url}"><meta property="og:image:width" content="1280"><meta property="og:image:height" content="720"><meta property="og:image:alt" content="صورة توضيحية لمقال {esc(title)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{image_url}">
<meta property="article:published_time" content="{TODAY}T01:00:00+03:00"><meta property="article:modified_time" content="{TODAY}T01:00:00+03:00"><meta property="article:section" content="{esc(category)}">
<link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/quick-info/quick-info.css?v=1.0.0">
<script type="application/ld+json">{schema(title, slug, image_url)}</script>
</head>
<body>
<a class="skip" href="#content">تجاوز إلى المحتوى</a>
<header class="site-header"><div class="wrap header-inner"><a class="brand" href="/"><img src="/assets/brand/logo-mark.svg" alt=""><span>{BRAND}<small>{SECTION}</small></span></a><nav><a href="/quick-info/">كل المعلومات</a><a href="/encyclopedia/">الموسوعة</a><a href="/daily-tools/">الأدوات</a><a href="/trust/">الثقة والمصادر</a></nav></div></header>
<main id="content">
  <article>
    <header class="article-hero"><div class="wrap hero-grid"><div><nav class="breadcrumbs" aria-label="مسار الصفحة"><a href="/">الرئيسية</a><span>/</span><a href="/quick-info/">{SECTION}</a><span>/</span><span>{esc(category)}</span></nav><p class="category">{esc(category)} · الصفحة {idx} من 150</p><h1>{esc(title)}</h1><p class="lead">{esc(description)}</p><div class="meta"><span>إعداد: فريق روافد للتحرير الصحي</span><span>نشر: 4 أغسطس 2026</span><span>قراءة: 4 دقائق</span></div></div><img src="/assets/quick-info/cards/{slug}.jpg" width="1280" height="720" alt="صورة توضيحية لمقال {esc(title)}" fetchpriority="high"></div></header>
    <div class="wrap article-layout"><div class="article-content">
      <aside class="disclaimer"><strong>تنبيه مهم:</strong> هذه مادة تثقيفية وليست تشخيصًا أو بديلًا عن التقييم والعلاج الفردي.</aside>
      {article_body(title, kind)}
    </div><aside class="side"><div class="side-card"><strong>قاعدة سريعة</strong><p>المدة + الشدة + التعطل + الأمان أهم من تسمية الشعور بسرعة.</p></div><div class="side-card"><strong>شارك بمسؤولية</strong><p>لا تستخدم الصفحة لتشخيص شخص آخر أو الضغط عليه.</p></div></aside></div>
  </article>
  <section class="related wrap"><h2>اقرأ أيضًا</h2><div class="related-grid">{related_html}</div></section>
</main>
<footer><div class="wrap"><strong>{BRAND}</strong><p>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</p><p><a href="/editorial-methodology/">المنهجية التحريرية</a> · <a href="/privacy/">الخصوصية</a> · <a href="/contact/">تواصل معنا</a></p></div></footer>
</body></html>"""


def css_text() -> str:
    return """:root{--ink:#123f43;--muted:#557074;--brand:#075f5b;--accent:#87345d;--line:#c8e1de;--mist:#edf9f7;--surface:#fff;--warn:#fff4e8;--shadow:0 18px 48px rgba(16,72,73,.12)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:var(--ink);background:#f8fcfb;line-height:1.85}a{color:#056a64;text-underline-offset:4px}a:focus-visible{outline:3px solid #0b8d84;outline-offset:3px}.wrap{width:min(1180px,92%);margin-inline:auto}.skip{position:absolute;inset-inline-start:-9999px;top:8px;background:#fff;padding:10px;z-index:99}.skip:focus{inset-inline-start:8px}.site-header{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.header-inner{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:10px 0}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-weight:900}.brand img{width:48px;height:48px}.brand span{display:grid;line-height:1.35}.brand small{color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{font-weight:800;text-decoration:none;padding:7px 9px;border-radius:10px}.article-hero{background:linear-gradient(145deg,#fff,var(--mist));border-bottom:1px solid var(--line);padding:45px 0}.hero-grid{display:grid;grid-template-columns:1.08fr .92fr;gap:34px;align-items:center}.hero-grid img{width:100%;height:auto;border-radius:24px;box-shadow:var(--shadow);aspect-ratio:16/9;object-fit:cover}.breadcrumbs{font-size:.9rem;color:var(--muted);gap:6px}.breadcrumbs a{padding:0}.category,.eyebrow{color:var(--accent);font-weight:900}.article-hero h1{font-size:clamp(2rem,5vw,4rem);line-height:1.18;margin:.25em 0}.lead{font-size:1.17rem;color:var(--muted)}.meta{display:flex;gap:10px;flex-wrap:wrap}.meta span{background:#fff;border:1px solid var(--line);padding:5px 10px;border-radius:99px;font-size:.87rem}.article-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:30px;padding:38px 0}.article-content{min-width:0}.disclaimer,.notice,.warning,.answer-box{padding:18px 20px;border-radius:18px;margin:0 0 22px;background:#fff;border:1px solid var(--line)}.disclaimer{border-inline-start:5px solid var(--accent)}.answer-box{background:linear-gradient(135deg,#edf9f7,#fff);font-size:1.1rem}.warning{background:var(--warn);border-color:#e9c8a7}.article-section{background:#fff;border:1px solid var(--line);border-radius:22px;padding:24px;margin:0 0 22px;box-shadow:0 9px 26px rgba(16,72,73,.06)}.article-section h2{font-size:clamp(1.45rem,3vw,2rem);line-height:1.3;margin-top:0}.article-section.two{display:grid;grid-template-columns:1fr 1fr;gap:22px}.article-section li{margin:.45rem 0}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:680px}th,td{padding:13px;border:1px solid var(--line);vertical-align:top}th{background:var(--mist)}.point-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.point-card{border:1px solid var(--line);border-radius:16px;padding:17px;background:#fbfefd}.point-card span{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;background:var(--brand);color:#fff;font-weight:900}.point-card h3{margin:.65rem 0 .25rem}.point-card p{color:var(--muted);margin:0}.checklist{counter-reset:item;list-style:none;padding:0}.checklist li{padding:13px 44px 13px 13px;position:relative;border-bottom:1px solid var(--line)}.checklist li:before{content:'✓';position:absolute;right:9px;top:13px;color:var(--brand);font-weight:900}.steps li{margin:.7rem 0}.micro-note{font-size:.92rem;color:var(--muted)}details{border-bottom:1px solid var(--line);padding:12px 0}summary{font-weight:900;cursor:pointer}.side{position:relative}.side-card{position:sticky;top:92px;background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px;margin-bottom:14px}.side-card+ .side-card{position:static}.related{padding:10px 0 50px}.related-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.related-card{display:grid;gap:8px;background:#fff;border:1px solid var(--line);border-radius:17px;padding:18px;text-decoration:none;color:var(--ink)}.related-card small{color:var(--accent);font-weight:800}footer{background:#123f43;color:#fff;padding:34px 0}footer a{color:#c9fff8}.index-hero{padding:62px 0 34px;background:linear-gradient(145deg,#fff,var(--mist),#f5efff)}.index-hero h1{font-size:clamp(2.5rem,7vw,5.5rem);line-height:1;margin:.2em 0}.filter-bar{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}.filter-bar input{flex:1;min-width:240px;padding:14px;border:1px solid var(--line);border-radius:14px;font:inherit}.filter-bar button{border:1px solid var(--line);background:#fff;border-radius:99px;padding:10px 14px;font-weight:800;cursor:pointer}.filter-bar button.active{background:var(--brand);color:#fff}.article-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:17px;padding:24px 0 60px}.article-card{background:#fff;border:1px solid var(--line);border-radius:20px;overflow:hidden;box-shadow:0 10px 28px rgba(16,72,73,.07)}.article-card img{width:100%;aspect-ratio:16/9;object-fit:cover}.article-card div{padding:16px}.article-card a{text-decoration:none;color:var(--ink)}.article-card h2{font-size:1.17rem;line-height:1.5;margin:.25rem 0}.article-card p{color:var(--muted);font-size:.92rem}.stats{display:flex;gap:12px;flex-wrap:wrap}.stats b{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px 14px}.empty{display:none;padding:30px;text-align:center}@media(max-width:900px){.hero-grid,.article-layout{grid-template-columns:1fr}.side{display:grid;grid-template-columns:1fr 1fr}.side-card{position:static}.article-grid,.related-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.header-inner{align-items:flex-start;flex-direction:column}.article-section.two,.point-grid,.article-grid,.related-grid,.side{grid-template-columns:1fr}.article-hero{padding-top:28px}.article-layout{padding-top:24px}.article-section{padding:19px}.meta span{font-size:.78rem}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}"""


def generate_card(slug: str, title: str, category: str) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required to generate 1280x720 Discover images") from exc
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    start, end, symbol = PALETTES[category]
    w, h = 1280, 720
    im = Image.new("RGB", (w, h), start)
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        row = tuple(int(start[i] * (1 - t) + end[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    draw = ImageDraw.Draw(im, "RGBA")
    seed = int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)
    for i in range(9):
        r = 60 + ((seed >> (i % 16)) & 127)
        x = ((seed * (i + 3) * 37) % 1500) - 100
        y = ((seed * (i + 5) * 19) % 900) - 80
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255,255,255,18 + i * 3), outline=(255,255,255,30))
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    def font(size: int):
        for path in font_paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()
    draw.rounded_rectangle((70, 70, 1210, 650), radius=44, fill=(8,35,43,118), outline=(255,255,255,52), width=2)
    draw.text((1110, 155), symbol, font=font(170), fill=(255,255,255,215), anchor="ra")
    draw.text((1140, 100), SECTION, font=font(38), fill=(255,255,255,225), anchor="ra", direction="rtl")
    wrapped = textwrap.wrap(title, width=28)[:2]
    y = 390
    for line in wrapped:
        try:
            draw.text((1140, y), line, font=font(52), fill="white", anchor="ra", direction="rtl", language="ar")
        except Exception:
            draw.text((1140, y), line, font=font(52), fill="white", anchor="ra")
        y += 78
    draw.text((1140, 590), BRAND + " · معرفة موثوقة بلا تشخيص ذاتي", font=font(27), fill=(240,255,252,230), anchor="ra", direction="rtl")
    im.save(CARD_DIR / f"{slug}.jpg", "JPEG", quality=91, optimize=True, progressive=True)


def related_for(index: int, category: str) -> list[tuple]:
    same = [row for row in TOPICS if row[3] == category and row != TOPICS[index]]
    ordered = same[index % len(same):] + same[:index % len(same)] if same else []
    return ordered[:3]


def index_html() -> str:
    categories = sorted({x[3] for x in TOPICS})
    buttons = "".join(f"<button type='button' data-filter='{esc(c)}'>{esc(c)}</button>" for c in categories)
    cards = []
    for i, (slug, title, kind, category) in enumerate(TOPICS, 1):
        cards.append(f"<article class='article-card' data-category='{esc(category)}' data-text='{esc(title)}'><a href='/quick-info/{slug}/'><img src='/assets/quick-info/cards/{slug}.jpg' width='1280' height='720' loading='lazy' alt=''><div><small>{esc(category)} · {i}</small><h2>{esc(title)}</h2><p>{esc(quick_answer(title, kind)[:150])}</p></div></a></article>")
    schema_data = {"@context":"https://schema.org","@type":"CollectionPage","name":SECTION,"url":f"{BASE}/quick-info/","inLanguage":"ar","description":"150 صفحة عربية سريعة وموثوقة في الصحة النفسية والعلاقات والنوم والأسرة.","hasPart":[{"@type":"Article","name":t,"url":f"{BASE}/quick-info/{s}/"} for s,t,_,_ in TOPICS]}
    return f"""<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><title>{SECTION} | 150 إجابة ومقارنة نفسية موثوقة | {BRAND}</title><meta name='description' content='150 صفحة عربية سريعة: مقارنات نفسية، فحوص توعوية، علاقات، نوم، ضغط، أسرة وADHD، بعناوين مباشرة ومحتوى غير تشخيصي موثق.'><meta name='robots' content='index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1'><link rel='canonical' href='{BASE}/quick-info/'><link rel='alternate' type='application/rss+xml' title='{SECTION}' href='{BASE}/quick-info/feed.xml'><meta property='og:type' content='website'><meta property='og:title' content='{SECTION}: 150 موضوعًا يهمك'><meta property='og:description' content='مقارنات وأسئلة وعلامات وخطوات عملية في الصحة النفسية والعلاقات والنوم.'><meta property='og:image' content='{BASE}/assets/quick-info/cards/sadness-or-depression.jpg'><meta property='og:image:width' content='1280'><meta property='og:image:height' content='720'><meta name='twitter:card' content='summary_large_image'><link rel='stylesheet' href='/assets/quick-info/quick-info.css?v=1.0.0'><link rel='icon' href='/assets/brand/logo-mark.svg' type='image/svg+xml'><script type='application/ld+json'>{json.dumps(schema_data, ensure_ascii=False, separators=(',',':'))}</script></head><body><a class='skip' href='#content'>تجاوز إلى المحتوى</a><header class='site-header'><div class='wrap header-inner'><a class='brand' href='/'><img src='/assets/brand/logo-mark.svg' alt=''><span>{BRAND}<small>{SECTION}</small></span></a><nav><a href='/'>الرئيسية</a><a href='/encyclopedia/'>الموسوعة</a><a href='/daily-tools/'>الأدوات</a><a href='/trust/'>الثقة والمصادر</a></nav></div></header><main id='content'><section class='index-hero'><div class='wrap'><p class='category'>قسم تحريري جديد</p><h1>{SECTION}</h1><p class='lead'>150 صفحة تجيب بوضوح عن الأسئلة التي يفكر فيها الناس: حزن أم اكتئاب؟ إرهاق أم كسل؟ هل العلاقة آمنة؟ ولماذا لا يتوقف العقل قبل النوم؟</p><div class='stats'><b>150 صفحة</b><b>6 مسارات</b><b>صور 1280×720</b><b>محتوى غير تشخيصي</b></div><div class='filter-bar'><input id='search' type='search' placeholder='ابحث: اكتئاب، أرق، علاقة، ADHD...' aria-label='البحث في المعلومات السريعة'><button class='active' type='button' data-filter='الكل'>الكل</button>{buttons}</div></div></section><section class='wrap'><div id='grid' class='article-grid'>{''.join(cards)}</div><p id='empty' class='empty'>لا توجد نتيجة مطابقة. جرّب كلمة أقصر.</p></section></main><footer><div class='wrap'><strong>{BRAND}</strong><p>المحتوى للتثقيف العام ولا يستبدل التقييم أو العلاج الفردي.</p></div></footer><script>const q=document.getElementById('search'),buttons=[...document.querySelectorAll('[data-filter]')],cards=[...document.querySelectorAll('.article-card')],empty=document.getElementById('empty');let active='الكل';function run(){{const term=q.value.trim().toLowerCase();let shown=0;cards.forEach(c=>{{const ok=(active==='الكل'||c.dataset.category===active)&&(!term||c.dataset.text.toLowerCase().includes(term));c.hidden=!ok;if(ok)shown++;}});empty.style.display=shown?'none':'block';}}q.addEventListener('input',run);buttons.forEach(b=>b.addEventListener('click',()=>{{active=b.dataset.filter;buttons.forEach(x=>x.classList.toggle('active',x===b));run();}}));</script></body></html>"""


def feed_xml() -> str:
    items = []
    for slug, title, kind, _ in TOPICS[:50]:
        items.append(f"<item><title>{xml_escape(title)}</title><link>{BASE}/quick-info/{slug}/</link><guid>{BASE}/quick-info/{slug}/</guid><pubDate>Tue, 04 Aug 2026 01:00:00 +0300</pubDate><description>{xml_escape(quick_answer(title, kind))}</description></item>")
    return f"<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel><title>{SECTION} | {BRAND}</title><link>{BASE}/quick-info/</link><description>محتوى عربي سريع وموثوق في الصحة النفسية والعلاقات والنوم والأسرة.</description><language>ar</language>{''.join(items)}</channel></rss>"


def sitemap_xml() -> str:
    urls = [(f"{BASE}/quick-info/", "1.0")] + [(f"{BASE}/quick-info/{s}/", "0.8") for s,_,_,_ in TOPICS]
    body = "".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod><changefreq>monthly</changefreq><priority>{p}</priority></url>" for u,p in urls)
    return f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{body}</urlset>"


def api_json() -> str:
    payload = {"name": SECTION, "url": f"{BASE}/quick-info/", "language": "ar", "generated_at": TODAY, "count": len(TOPICS), "editorial_status": "internally-reviewed", "external_specialist_review_claimed": False, "items": [{"id": i, "slug": s, "title": t, "type": k, "category": c, "url": f"{BASE}/quick-info/{s}/", "image": f"{BASE}/assets/quick-info/cards/{s}.jpg"} for i,(s,t,k,c) in enumerate(TOPICS,1)]}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def patch_homepage() -> None:
    path = ROOT / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if 'href="/quick-info/"' not in text and "</nav>" in text:
        text = text.replace("</nav>", '<a href="/quick-info/">معلومات سريعة</a></nav>', 1)
    marker = "<!-- quick-info-discover-section -->"
    if marker not in text and "</main>" in text:
        block = f"""{marker}<section class="section"><div class="wrap"><div class="section-head"><div><p class="eyebrow">جديد</p><h2>معلومات سريعة</h2><p class="section-intro">150 مقارنة وفحصًا توعويًا ودليلًا قصيرًا في الصحة النفسية والعلاقات والنوم والأسرة، بصياغة مباشرة لا تشخّص القارئ.</p></div><a class="section-link" href="/quick-info/">استكشف القسم ←</a></div><div class="journeys"><a class="journey" href="/quick-info/sadness-or-depression/"><b>01</b><h3 class="item-title">حزن أم اكتئاب؟</h3><p>فروق عملية دون تشخيص ذاتي.</p></a><a class="journey" href="/quick-info/fatigue-or-laziness/"><b>02</b><h3 class="item-title">إرهاق أم كسل؟</h3><p>راجع الأسباب قبل لوم نفسك.</p></a><a class="journey" href="/quick-info/are-you-in-toxic-relationship/"><b>03</b><h3 class="item-title">هل العلاقة آمنة؟</h3><p>افحص السلوك والنمط المتكرر.</p></a><a class="journey" href="/quick-info/simple-mental-health-check/"><b>04</b><h3 class="item-title">فحص الصحة النفسية</h3><p>10 أسئلة توعوية بلا نتيجة تشخيصية.</p></a></div></div></section>"""
        text = text.replace("</main>", block + "</main>", 1)
    path.write_text(text, encoding="utf-8")


def patch_root_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if f"{BASE}/quick-info/" in text:
        return
    entries = [f"  <url><loc>{BASE}/quick-info/</loc><lastmod>{TODAY}</lastmod></url>"] + [f"  <url><loc>{BASE}/quick-info/{s}/</loc><lastmod>{TODAY}</lastmod></url>" for s,_,_,_ in TOPICS]
    text = text.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
    path.write_text(text, encoding="utf-8")


def patch_robots() -> None:
    path = ROOT / "robots.txt"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    line = f"Sitemap: {BASE}/sitemap-quick-info.xml"
    if line not in text:
        text = text.rstrip() + "\n" + line + "\n"
        path.write_text(text, encoding="utf-8")


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "api" / "v1").mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "quick-info.css").write_text(css_text(), encoding="utf-8")
    for i, (slug, title, kind, category) in enumerate(TOPICS, 1):
        target = OUT / slug
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(page_html(i, slug, title, kind, category, related_for(i - 1, category)), encoding="utf-8")
        generate_card(slug, title, category)
    (OUT / "index.html").write_text(index_html(), encoding="utf-8")
    (OUT / "feed.xml").write_text(feed_xml(), encoding="utf-8")
    (ROOT / "sitemap-quick-info.xml").write_text(sitemap_xml(), encoding="utf-8")
    (ROOT / "api" / "v1" / "quick-info.json").write_text(api_json(), encoding="utf-8")
    patch_homepage(); patch_root_sitemap(); patch_robots()
    validate(write_report=True)


def validate(write_report: bool = False) -> dict:
    errors = []
    if len(TOPICS) != 150:
        errors.append(f"topic count is {len(TOPICS)}")
    banned = ("لن تصدق", "صادم", "كارثة", "علاج نهائي", "يشفي")
    for i, (slug, title, _, _) in enumerate(TOPICS, 1):
        page = OUT / slug / "index.html"
        image = CARD_DIR / f"{slug}.jpg"
        if not page.exists(): errors.append(f"missing page {i}: {slug}"); continue
        text = page.read_text(encoding="utf-8")
        required = [title, "max-image-preview:large", "application/ld+json", "og:image:width", "تنبيه مهم", "مصادر موثوقة", f"{BASE}/quick-info/{slug}/"]
        for token in required:
            if token not in text: errors.append(f"{slug}: missing {token}")
        if any(word in title for word in banned): errors.append(f"{slug}: banned clickbait title")
        if len(re.sub(r"<[^>]+>", " ", text).split()) < 320: errors.append(f"{slug}: thin content")
        if not image.exists() or image.stat().st_size < 25000: errors.append(f"{slug}: image missing or too small")
    report = {"generated_at": TODAY, "section": SECTION, "pages": len(TOPICS), "categories": {c: sum(1 for x in TOPICS if x[3] == c) for c in sorted({x[3] for x in TOPICS})}, "discover": {"large_image_width": 1280, "large_image_height": 720, "max_image_preview_large": True, "unique_images": len(list(CARD_DIR.glob('*.jpg'))) if CARD_DIR.exists() else 0}, "quality": {"non_diagnostic_notice": True, "official_sources": True, "unique_titles": len({x[1] for x in TOPICS}), "unique_slugs": len({x[0] for x in TOPICS}), "errors": errors}}
    if write_report:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        raise SystemExit("\n".join(errors[:30]))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(write_report=True), ensure_ascii=False, indent=2))
    else:
        generate()
        print(json.dumps(validate(write_report=True), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
