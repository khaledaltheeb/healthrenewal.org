from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.encyclopedia_seo_contract_v1 import (
        EXPECTED_DETAIL_PAGES, FAQ_MARKER, SEARCH_INTENT_MARKER,
        faq_items, meta_description, search_intent_for, seo_title,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/rebuild_encyclopedia_v13.py
    from encyclopedia_seo_contract_v1 import (
        EXPECTED_DETAIL_PAGES, FAQ_MARKER, SEARCH_INTENT_MARKER,
        faq_items, meta_description, search_intent_for, seo_title,
    )

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/") + "/"
TODAY = date.today().isoformat()
VERIFY = "google644f1f7a8b7aaa2b.html"
ORG = "مصطلحات علم النفس"

FACETS = [
    {"key":"definition","ar":"التعريف والمفهوم","en":"definition and concept","focus":"المعنى الدقيق وحدود المصطلح","section":"الفهم الأساسي","questions":["ما التعريف العملي؟","ما الذي لا يعنيه المصطلح؟","كيف يختلف عن الخبرة العابرة؟"],"actions":["ابدأ بتحديد المعنى قبل تفسير السلوك.","دوّن أمثلة واقعية بدل الاكتفاء بوصف عام.","اربط المصطلح بالسياق والمدة والأثر الوظيفي."]},
    {"key":"signs","ar":"الأعراض والعلامات","en":"symptoms and signs","focus":"العلامات المحتملة وطريقة ملاحظتها دون تشخيص ذاتي","section":"العلامات والمظاهر","questions":["ما المظاهر الانفعالية؟","ما المظاهر السلوكية أو الجسدية؟","هل تظهر في أكثر من بيئة؟"],"actions":["راقب النمط عبر الوقت لا في يوم واحد.","افصل بين الملاحظة والتفسير.","سجّل الشدة والتكرار والموقف المصاحب."]},
    {"key":"factors","ar":"الأسباب والعوامل","en":"causes and contributing factors","focus":"العوامل الحيوية والنفسية والاجتماعية التي قد تتداخل","section":"العوامل والتفسيرات","questions":["ما العوامل السابقة؟","ما المحفزات الحالية؟","ما عوامل الحماية؟"],"actions":["تجنب البحث عن سبب واحد لكل حالة.","راجع النوم والصحة والأدوية والضغط البيئي.","فرّق بين عامل الخطر والسبب المؤكد."]},
    {"key":"assessment","ar":"التقييم النفسي","en":"psychological assessment","focus":"كيفية جمع المعلومات بصورة مهنية ومنظمة","section":"التقييم وجمع المعلومات","questions":["ما مصادر المعلومات المطلوبة؟","كيف يُقاس الأثر الوظيفي؟","ما الذي يجب استبعاده؟"],"actions":["حضّر خطًا زمنيًا واضحًا.","اجمع ملاحظات من أكثر من مصدر عند الحاجة.","استخدم المقاييس للفحص لا كبديل عن المقابلة المهنية."]},
    {"key":"differential","ar":"التشخيص التفريقي","en":"differential diagnosis","focus":"الفروق مع الظواهر أو الحالات المتشابهة","section":"الفروق والتشابهات","questions":["ما الحالات التي قد تبدو مشابهة؟","ما العلامة الأكثر تمييزًا؟","هل توجد أسباب جسدية أو دوائية؟"],"actions":["لا تعتمد على عرض واحد.","قارن البداية والمدة والسياق.","اطلب تقييمًا عند وجود تداخل أو غموض."]},
    {"key":"psychotherapy","ar":"العلاج النفسي","en":"psychotherapy","focus":"أهداف العلاج النفسي ومراحله وتوقعاته الواقعية","section":"العلاج النفسي","questions":["ما الهدف العلاجي؟","ما الأساليب الممكنة؟","كيف تُقاس الاستفادة؟"],"actions":["اختر مختصًا مؤهلًا وخطة واضحة.","ناقش الأهداف والمدة والمؤشرات العملية للتقدم.","راجع الخطة إذا لم يتحسن الأداء أو ظهرت مخاطر."]},
    {"key":"cbt","ar":"العلاج المعرفي السلوكي","en":"cognitive behavioral therapy","focus":"العلاقة بين الأفكار والانفعالات والسلوك والتجارب العملية","section":"المنظور المعرفي السلوكي","questions":["ما الفكرة التلقائية؟","ما السلوك الذي يحافظ على المشكلة؟","ما التجربة السلوكية المناسبة؟"],"actions":["حدد موقفًا واحدًا قابلًا للتحليل.","اختبر الفكرة بدل مجادلتها نظريًا.","استخدم واجبات صغيرة قابلة للقياس."]},
    {"key":"self_help","ar":"الدعم الذاتي","en":"self-help","focus":"خطوات آمنة ومحدودة يمكن تطبيقها دون ادعاء العلاج الكامل","section":"الدعم الذاتي المنظم","questions":["ما الخطوة الأصغر الممكنة؟","ما العادة التي تدعم الاستقرار؟","متى لا يكفي الدعم الذاتي؟"],"actions":["ابدأ بخطوة صغيرة متكررة.","راقب أثرها أسبوعيًا.","توقف واطلب مساعدة عند التدهور أو الخطر."]},
    {"key":"coping","ar":"استراتيجيات التعامل","en":"coping strategies","focus":"التعامل مع المواقف الصعبة بطريقة تقلل الضرر وتحافظ على الوظيفة","section":"استراتيجيات التعامل","questions":["هل الاستراتيجية تحل المشكلة أم تؤجلها؟","هل تقلل الضرر على المدى الطويل؟","ما البديل الأكثر مرونة؟"],"actions":["فرّق بين التكيف والتجنب.","استخدم أكثر من أداة بدل الاعتماد على أسلوب واحد.","قيّم النتيجة بعد الموقف لا أثناءه فقط."]},
    {"key":"prevention","ar":"الوقاية","en":"prevention","focus":"تقليل عوامل الخطر وتعزيز الحماية قبل تفاقم الصعوبة","section":"الوقاية والحماية","questions":["ما الإنذارات المبكرة؟","ما الروتين الواقي؟","ما شبكة الدعم المتاحة؟"],"actions":["ضع خطة للإنذارات المبكرة.","حافظ على النوم والحركة والعلاقات الداعمة.","راجع الخطة بعد الأزمات أو الانتكاسات."]},
    {"key":"early","ar":"التدخل المبكر","en":"early intervention","focus":"التصرف المبكر عند ظهور تغيرات متكررة أو معطلة","section":"التدخل المبكر","questions":["متى بدأ التغير؟","هل يتوسع أثره؟","ما الخدمة المناسبة للعمر والسياق؟"],"actions":["وثق التغيرات دون انتظار اكتمال الصورة.","ابدأ بمقدم رعاية مؤهل.","نسق بين الأسرة والمدرسة أو العمل عند الحاجة."]},
    {"key":"children","ar":"لدى الأطفال","en":"in children","focus":"ظهور المفهوم في النمو واللعب والتعلم والعلاقات الأسرية","section":"عند الأطفال","questions":["هل يتناسب السلوك مع العمر؟","هل يظهر في البيت والمدرسة؟","هل توجد صعوبات نمو أو تواصل مصاحبة؟"],"actions":["استخدم لغة بسيطة وغير وصمية.","اجمع ملاحظات الأسرة والمدرسة.","اطلب تقييمًا نمائيًا عند التأخر أو فقد المهارات."]},
    {"key":"adolescents","ar":"لدى المراهقين","en":"in adolescents","focus":"تأثير النمو والهوية والأقران والدراسة في الصورة النفسية","section":"عند المراهقين","questions":["ما التغير عن خط الأساس؟","هل توجد عزلة أو تراجع دراسي؟","هل يوجد خطر أو إيذاء ذاتي؟"],"actions":["وازن بين الخصوصية والمتابعة.","استمع قبل تقديم الحلول.","تعامل سريعًا مع مخاطر السلامة."]},
    {"key":"adults","ar":"لدى البالغين","en":"in adults","focus":"الأثر على العمل والعلاقات والرعاية الذاتية والمسؤوليات","section":"عند البالغين","questions":["كيف تأثر الأداء؟","هل توجد ضغوط مهنية أو أسرية؟","ما الموارد المتاحة؟"],"actions":["حدد مجال التعطل الأكبر.","خفف الحمل غير الضروري مؤقتًا.","اطلب دعمًا مهنيًا عند الاستمرار أو التفاقم."]},
    {"key":"older","ar":"لدى كبار السن","en":"in older adults","focus":"التغيرات النفسية في سياق الصحة الجسدية والفقد والتقاعد والدواء","section":"عند كبار السن","questions":["هل التغير جديد أم قديم؟","هل توجد أسباب طبية أو دوائية؟","هل حدث فقد أو عزلة؟"],"actions":["ابدأ بفحص طبي عند التغير المفاجئ.","حافظ على الروتين والاتصال الاجتماعي.","راعِ السمع والبصر والذاكرة عند التقييم."]},
    {"key":"family","ar":"في الأسرة","en":"in families","focus":"تأثير المفهوم في الأدوار والتواصل والرعاية داخل الأسرة","section":"داخل الأسرة","questions":["كيف توزعت الأدوار؟","ما الذي يزيد التوتر؟","كيف يمكن تقديم دعم دون سيطرة؟"],"actions":["اتفقوا على لغة مشتركة وواضحة.","وزعوا مهام الرعاية واقعيًا.","ضعوا خطة للأزمات والحدود."]},
    {"key":"relationships","ar":"في العلاقات","en":"in relationships","focus":"التواصل والحدود والاحتياجات المتبادلة وتأثير النمط النفسي","section":"في العلاقات","questions":["هل يوجد أمان واحترام؟","هل تتكرر دائرة معينة؟","ما الحدود المطلوبة؟"],"actions":["استخدم وصفًا للسلوك لا اتهامًا للشخص.","حدد طلبًا واضحًا وقابلًا للتنفيذ.","لا تبرر العنف أو الإكراه بأي تشخيص."]},
    {"key":"work","ar":"في مكان العمل","en":"in the workplace","focus":"الأداء والضغط والعلاقات المهنية والتعديلات الممكنة","section":"في العمل","questions":["ما المهام الأكثر تأثرًا؟","هل المشكلة في الحمل أم البيئة أم المهارة؟","ما التعديل الواقعي؟"],"actions":["قسم المهام وحدد الأولويات.","وثق أثر الضغط وساعات العمل.","ناقش تعديلات معقولة دون كشف معلومات غير ضرورية."]},
    {"key":"school","ar":"في المدرسة والجامعة","en":"in school and university","focus":"التعلم والحضور والاختبارات والعلاقات مع الزملاء والمعلمين","section":"في التعليم","questions":["هل التأثير أكاديمي أم اجتماعي أم حسي؟","ما المواد أو الأوقات الأصعب؟","ما التسهيلات الممكنة؟"],"actions":["حدد صعوبة قابلة للقياس.","نسق خطة بين الطالب والأسرة والمؤسسة.","راجع فعالية التسهيلات دوريًا."]},
    {"key":"quality","ar":"وجودة الحياة","en":"and quality of life","focus":"الأثر الكلي على المعنى والاستقلال والعلاقات والصحة اليومية","section":"جودة الحياة","questions":["ما المجالات المتأثرة؟","ما الذي بقي جيدًا؟","ما التغيير الذي سيصنع فرقًا ملموسًا؟"],"actions":["قِس التقدم بوظائف الحياة لا بالأعراض فقط.","حافظ على النشاطات ذات المعنى.","ضع أهدافًا واقعية قابلة للمراجعة."]},
]

EXTRA_DOMAINS = [
    ("اضطراب ثنائي القطب","Bipolar Disorder","اضطرابات المزاج"),
    ("الفصام","Schizophrenia","الاضطرابات الذهانية"),
    ("اضطرابات الأكل","Eating Disorders","الصحة والسلوك"),
    ("اضطراب الشخصية الحدية","Borderline Personality Disorder","الشخصية"),
    ("الذهان","Psychosis","الاضطرابات الذهانية"),
    ("الانتحار وإيذاء النفس","Suicide and Self-Harm","السلامة النفسية"),
    ("الإعاقة الذهنية","Intellectual Disability","النمو العصبي"),
    ("اضطرابات التواصل","Communication Disorders","النمو العصبي"),
    ("متلازمة توريت","Tourette Syndrome","النمو العصبي"),
    ("الشلل الدماغي والدعم النفسي","Cerebral Palsy and Psychological Support","النمو العصبي"),
    ("متلازمة داون والدعم النفسي","Down Syndrome and Psychological Support","النمو العصبي"),
    ("ضعف السمع والصحة النفسية","Hearing Loss and Mental Health","الاحتياجات الخاصة"),
    ("ضعف البصر والصحة النفسية","Vision Loss and Mental Health","الاحتياجات الخاصة"),
    ("الصحة النفسية لمقدمي الرعاية","Caregiver Mental Health","الأسرة"),
    ("اكتئاب ما بعد الولادة","Postpartum Depression","الصحة النفسية للمرأة"),
    ("القلق بعد الولادة","Postpartum Anxiety","الصحة النفسية للمرأة"),
    ("العلاج باللعب","Play Therapy","العلاج والإرشاد"),
    ("العلاج الوظيفي والدعم النفسي","Occupational Therapy and Psychological Support","العلاج والإرشاد"),
    ("علاج النطق واللغة والدعم النفسي","Speech-Language Therapy and Psychological Support","العلاج والإرشاد"),
    ("التدخلات القائمة على الأسرة","Family-Based Interventions","العلاج والإرشاد"),
]

OVERRIDES = {
    "القلق": {"definition":"القلق استجابة انفعالية ومعرفية تتضمن توقع الخطر والتوتر والاستعداد للتعامل معه. يصبح مشكلة سريرية عندما يكون مفرطًا أو صعب السيطرة ويستمر أو يعطل الدراسة أو العمل أو العلاقات.","observations":["توقع الأسوأ وصعوبة تهدئة التفكير","توتر جسدي واضطراب نوم أو تجنب","بحث متكرر عن الطمأنة"],"distinctions":["القلق الطبيعي يتناسب غالبًا مع الموقف ويخف بعده، بينما الاضطراب أشد وأطول وأكثر تعطيلًا.","الأعراض الجسدية قد تشبه مشكلات طبية؛ التقييم لا يبدأ بافتراض نفسي تلقائي."],"related":["اضطراب الهلع","الرهاب الاجتماعي","التفكير الكارثي","الاجترار الفكري"]},
    "الاكتئاب": {"definition":"الاكتئاب ليس حزنًا عابرًا فقط؛ قد يشمل مزاجًا منخفضًا أو فقدان المتعة مع تغيرات في النوم والطاقة والتركيز والشهية والشعور بالقيمة، ويُنظر إلى المدة والشدة والأثر الوظيفي عند التقييم.","observations":["فقد الاهتمام أو المتعة","انخفاض الطاقة وبطء الأداء","انسحاب أو شعور باليأس والذنب"],"distinctions":["الحزن استجابة إنسانية قد تتبدل وتبقى معها لحظات تواصل ومتعة، بينما الاكتئاب قد يكون أوسع وأثبت وأكثر تعطيلًا.","يجب الانتباه للأسباب الطبية والدوائية واضطرابات النوم والاضطراب ثنائي القطب."],"related":["الحزن","الفقد","تقدير الذات","اضطراب ثنائي القطب"]},
    "الوسواس القهري": {"definition":"الوسواس القهري يتضمن أفكارًا أو صورًا أو اندفاعات متطفلة متكررة، وسلوكيات أو أفعالًا ذهنية قهرية يُراد بها خفض القلق أو منع حدث مخيف، لكنها تستهلك الوقت وتحافظ على الدائرة.","observations":["شك متكرر وصعوبة تحمل عدم اليقين","غسل أو فحص أو ترتيب أو طقوس ذهنية","تجنب محفزات أو طلب طمأنة"],"distinctions":["الوساوس ليست رغبات حقيقية لمجرد أنها مزعجة، وغالبًا تتعارض مع قيم الشخص.","العادات والتفضيلات لا تُعد قهرية ما لم تكن مدفوعة بضغط واضح أو تسبب تعطيلًا."],"related":["القلق","التشوهات المعرفية","ضبط النفس","العلاج المعرفي السلوكي"]},
    "اضطراب الهلع": {"definition":"اضطراب الهلع يرتبط بنوبات خوف شديد مفاجئة مع أعراض جسدية ومعرفية، يتبعها قلق مستمر من تكرار النوبات أو تغيرات سلوكية مثل التجنب.","observations":["خفقان أو ضيق نفس أو دوخة","إحساس بفقد السيطرة أو الخطر","تجنب أماكن أو مجهودات خوفًا من النوبة"],"distinctions":["نوبة الهلع قد تحدث في حالات مختلفة، أما اضطراب الهلع فيتضمن قلقًا أو تغيرًا سلوكيًا مستمرًا بشأن النوبات.","الأعراض الحادة تستلزم تقييمًا طبيًا عندما تكون جديدة أو غير معتادة."],"related":["القلق","الخوف","الرهاب الاجتماعي","اضطرابات القلق"]},
    "الصدمة النفسية": {"definition":"الصدمة النفسية تشير إلى أثر تجربة أو سلسلة تجارب تهدد الأمان أو تتجاوز قدرة الشخص الحالية على الاستيعاب والتكيف. الاستجابات تختلف ولا تعني كل تجربة مؤلمة اضطراب ما بعد الصدمة.","observations":["استثارة أو خدر أو تجنب","ذكريات مقتحمة أو اضطراب نوم","تغير الإحساس بالأمان والثقة"],"distinctions":["الضغط الشديد لا يساوي تلقائيًا اضطراب ما بعد الصدمة.","الاستجابة المبكرة قد تكون مؤقتة؛ الأثر المستمر والمعطل يحتاج تقييمًا."],"related":["اضطراب ما بعد الصدمة","المرونة النفسية","الفقد","التعافي"]},
    "اضطراب ما بعد الصدمة": {"definition":"اضطراب ما بعد الصدمة قد يظهر بعد التعرض لحدث شديد التهديد، ويتضمن أنماطًا مثل إعادة المعايشة والتجنب والشعور المستمر بالتهديد وتغيرات معرفية أو انفعالية تؤثر في الحياة.","observations":["كوابيس أو ذكريات مقتحمة","تجنب التذكير بالحدث","استثارة مفرطة أو خدر وانفصال"],"distinctions":["التذكر المؤلم وحده لا يكفي للتشخيص.","التقييم يراعي نوع التعرض والمدة والأثر واحتمال وجود اكتئاب أو قلق أو إصابات جسدية."],"related":["الصدمة النفسية","القلق","النوم","المرونة النفسية"]},
    "فرط الحركة وتشتت الانتباه": {"definition":"اضطراب فرط الحركة وتشتت الانتباه نمط نمائي مستمر من صعوبات الانتباه و/أو فرط النشاط والاندفاع يؤثر سلبًا في الأداء، ويحتاج إلى معلومات من أكثر من بيئة واستبعاد تفسيرات أخرى.","observations":["صعوبة تنظيم المهام والوقت","نسيان وتشتت متكرر","اندفاع أو حركة لا تتناسب مع الموقف"],"distinctions":["لا يوجد اختبار واحد يشخص الاضطراب، وقد تشبهه مشكلات النوم والقلق والاكتئاب وصعوبات التعلم.","الحركة الطبيعية أو الملل في موقف واحد لا يكفيان."],"related":["الانتباه","الذاكرة العاملة","صعوبات التعلم","الدافعية الدراسية"]},
    "التوحد": {"definition":"التوحد مجموعة متنوعة من الحالات النمائية المرتبطة باختلافات في التواصل والتفاعل الاجتماعي وأنماط سلوكية أو اهتمامات متكررة أو مقيدة وحاجات حسية متفاوتة. القدرات واحتياجات الدعم تختلف كثيرًا بين الأشخاص.","observations":["اختلافات في التواصل الاجتماعي المتبادل","حاجة للروتين أو اهتمامات مركزة","استجابات حسية غير معتادة"],"distinctions":["لا يُشخّص التوحد من سمة واحدة أو اختبار إلكتروني واحد.","المعلومات الأساسية تأتي من تاريخ النمو ووصف الأسرة والملاحظة المهنية، مع فحص الحالات المصاحبة."],"related":["الحساسية الحسية","اضطرابات التواصل","الإعاقة الذهنية","الأبوة والأمومة"]},
    "الأرق": {"definition":"الأرق صعوبة مستمرة في بدء النوم أو استمراره أو الاستيقاظ المبكر، رغم وجود فرصة مناسبة للنوم، مع أثر نهاري مثل التعب أو ضعف التركيز أو المزاج.","observations":["وقت طويل للدخول في النوم","استيقاظات متكررة","قلق متزايد حول النوم وأثر نهاري"],"distinctions":["قلة النوم بسبب جدول مزدحم ليست أرقًا بالمعنى نفسه.","يجب مراجعة الألم والأدوية واضطرابات التنفس والمزاج والعادات."],"related":["النوم","القلق","الضغط النفسي","التركيز"]},
    "الحزن": {"definition":"الحزن استجابة إنسانية للفقد أو الخيبة أو التغير، وقد يتضمن موجات من الألم والاشتياق واضطراب النوم والتركيز. مساره فردي ولا يختزل في جدول زمني واحد.","observations":["اشتياق وموجات انفعال","تغير الروتين والنوم","حاجة للمعنى والدعم"],"distinctions":["الحزن لا يُعد مرضًا تلقائيًا، لكنه قد يتداخل مع اكتئاب أو صدمة أو حزن مطوّل.","الخطورة تُقيّم عبر السلامة والوظيفة والاستمرار لا عبر شدة البكاء وحدها."],"related":["الفقد","الاكتئاب","المرونة النفسية","التعاطف"]},
    "العلاج المعرفي السلوكي": {"definition":"العلاج المعرفي السلوكي مجموعة تدخلات منظمة تدرس العلاقة بين الأفكار والانفعالات والسلوك، وتستخدم مهارات وتجارب عملية وتدرجًا في مواجهة الصعوبات وفق المشكلة والأهداف.","observations":["تحديد أنماط التفكير والسلوك","واجبات وتجارب بين الجلسات","قياس التقدم بأهداف واضحة"],"distinctions":["ليس مجرد تفكير إيجابي أو إنكار للمشاعر.","تختلف التقنيات باختلاف الحالة والعمر والسياق، ويحتاج التطبيق السريري إلى مختص مؤهل."],"related":["التشوهات المعرفية","التفكير الكارثي","العلاج النفسي","الوسواس القهري"]},
}

SOURCE_LIBRARY = {
    "general": [("منظمة الصحة العالمية: الاضطرابات النفسية","https://www.who.int/news-room/fact-sheets/detail/mental-disorders"),("المعهد الوطني للصحة النفسية: الموضوعات الصحية","https://www.nimh.nih.gov/health/topics")],
    "anxiety": [("منظمة الصحة العالمية: اضطرابات القلق","https://www.who.int/news-room/fact-sheets/detail/anxiety-disorders"),("NIMH: Anxiety Disorders","https://www.nimh.nih.gov/health/topics/anxiety-disorders")],
    "autism": [("منظمة الصحة العالمية: التوحد","https://www.who.int/news-room/fact-sheets/detail/autism-spectrum-disorders"),("CDC: About Autism Spectrum Disorder","https://www.cdc.gov/autism/about/index.html"),("CDC: Clinical Testing and Diagnosis for Autism","https://www.cdc.gov/autism/hcp/diagnosis/index.html")],
    "adhd": [("CDC: Diagnosing ADHD","https://www.cdc.gov/adhd/diagnosis/index.html"),("CDC: Clinical Care of ADHD in Children","https://www.cdc.gov/adhd/hcp/treatment-recommendations/index.html")],
    "child": [("CDC: Child Development Resources","https://www.cdc.gov/child-development/resources/index.html"),("WHO: Adolescent Mental Health","https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health")],
    "therapy": [("NIMH: Psychotherapies","https://www.nimh.nih.gov/health/topics/psychotherapies"),("APA: What practicing psychologists do","https://www.apa.org/topics/psychotherapy/about-psychologists")],
}

V13_CSS = r'''
/* v13 encyclopedia quality system */
.ency-v13{width:min(1160px,calc(100% - 24px));margin:auto;padding:18px 0 60px;color:#17383d}
.ency-v13__hero{padding:clamp(26px,5vw,60px);border-radius:34px;background:linear-gradient(125deg,#ffdbea,#c9f5ee,#efe4ff);box-shadow:0 18px 52px rgba(57,125,128,.14);margin-bottom:24px}
.ency-v13__hero h1{font-size:clamp(2rem,5vw,4rem);margin:.2em 0;line-height:1.25}.ency-v13__hero p{max-width:900px;color:#3d6268;font-size:1.1rem}
.ency-v13__article{background:rgba(255,255,255,.96);border:1px solid #cde9e5;border-radius:28px;box-shadow:0 16px 44px rgba(57,125,128,.1);padding:clamp(20px,4vw,48px)}
.ency-v13__article h2{margin-top:2rem;color:#174b52;font-size:clamp(1.35rem,3vw,2rem)}.ency-v13__article h3{color:#7d3562}
.ency-v13__article p,.ency-v13__article li{font-size:1.04rem;line-height:2}.ency-v13__article ul{padding-right:1.3rem}
.ency-v13__meta{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 24px}.ency-v13__tag{padding:7px 12px;border-radius:999px;background:#fff1f7;border:1px solid #f2c4d8;color:#743154;font-weight:700}
.ency-v13__callout{padding:18px 20px;border-radius:20px;background:linear-gradient(135deg,#fff5c9,#d8f7f1);border:1px solid #cbe7df;margin:20px 0}.ency-v13__warning{background:linear-gradient(135deg,#ffe7ee,#fff4ce)}
.ency-v13__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:16px}.ency-v13__card{padding:20px;border-radius:22px;background:linear-gradient(145deg,#fff,#fff1f7);border:1px solid #cde9e5;box-shadow:0 10px 30px rgba(57,125,128,.08)}
.ency-v13__card:nth-child(3n+2){background:linear-gradient(145deg,#fff,#e8fbf7)}.ency-v13__card:nth-child(3n){background:linear-gradient(145deg,#fff,#f2ecff)}
.ency-v13__sources{padding:18px;border-radius:20px;background:#f3fbfa;border:1px solid #cde9e5}.ency-v13__sources a{overflow-wrap:anywhere}
.ency-v13__search{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin:20px 0}.ency-v13__search input,.ency-v13__search select{width:100%;padding:14px;border:1px solid #bcded9;border-radius:14px;background:#fff;color:#17383d}
.ency-v13__crumbs{font-size:.92rem;margin:8px 0 18px;color:#58747a}.ency-v13__crumbs a{color:#146e77}
.ency-v13__intent{margin:28px 0;padding:clamp(18px,3vw,28px);border:1px solid #b9ded8;border-radius:24px;background:linear-gradient(145deg,#f4fffd,#fff3f8)}
.ency-v13__intent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(230px,100%),1fr));gap:14px}.ency-v13__intent-card{padding:16px;border-radius:18px;background:#fff;border:1px solid #d6e9e6}.ency-v13__intent-card h3{margin-top:0}.ency-v13__intent-query{font-weight:800;color:#174b52}.ency-v13__faq article{padding:14px 0;border-bottom:1px solid #dcebea}.ency-v13__faq article:last-child{border-bottom:0}
@media(max-width:760px){.ency-v13{width:calc(100% - 14px)}.ency-v13__hero,.ency-v13__article{border-radius:22px;padding:20px}.ency-v13__search{grid-template-columns:1fr}.ency-v13__article p,.ency-v13__article li{font-size:1rem}}
'''


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_legacy() -> Any:
    path = Path("scripts/scale_site_v8.py")
    spec = importlib.util.spec_from_file_location("scale_site_v8", path)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to import legacy encyclopedia source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def choose_sources(domain: str, facet_key: str, category: str) -> list[tuple[str, str]]:
    keys = ["general"]
    if any(x in domain for x in ("قلق", "هلع", "رهاب")):
        keys.append("anxiety")
    if "توحد" in domain:
        keys.append("autism")
    if "فرط الحركة" in domain or "تشتت الانتباه" in domain:
        keys.append("adhd")
    if facet_key in {"children", "adolescents", "school", "early"} or any(x in category for x in ("النمو", "الطفولة", "التربوي", "الأسرة")):
        keys.append("child")
    if facet_key in {"psychotherapy", "cbt"} or any(x in category for x in ("العلاج", "الإرشاد")):
        keys.append("therapy")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key in keys:
        for title, url in SOURCE_LIBRARY[key]:
            if url not in seen:
                results.append((title, url)); seen.add(url)
    return results[:4]


def category_profile(domain: str, category: str) -> dict[str, Any]:
    if "العلاج" in category or "الإرشاد" in category:
        definition = f"{domain} مفهوم أو تدخل مهني ضمن مجال العلاج والإرشاد النفسي. يُفهم من خلال أهدافه والفئة المناسبة له وطريقة تطبيقه وحدود الدليل العلمي، وليس من خلال الاسم وحده."
        obs = ["وضوح الهدف العلاجي والتعاقد المهني", "ملاءمة الأسلوب للحالة والعمر والسياق", "متابعة التقدم والآثار غير المرغوبة"]
        distinctions = ["الأسلوب العلاجي ليس نصيحة عامة أو وصفة واحدة للجميع.", "الكفاءة المهنية والعلاقة العلاجية والخطة القابلة للمراجعة عناصر أساسية."]
    elif "البحث" in category or "القياس" in category:
        definition = f"{domain} مفهوم منهجي في القياس والبحث النفسي. قيمته تعتمد على التعريف الإجرائي وجودة الأداة والعينة وطريقة التفسير، ولا يجوز تحويل النتيجة الإحصائية وحدها إلى حكم فردي."
        obs = ["وضوح ما الذي تقيسه الأداة", "جودة الصدق والثبات والمعايير", "حدود التعميم والخطأ المحتمل"]
        distinctions = ["الدرجة ليست حقيقة مطلقة عن الشخص.", "الصدق والثبات مفهومان مختلفان، وكلاهما ضروري للتفسير المسؤول."]
    elif "فروع" in category:
        definition = f"{domain} مجال علمي يدرس جانبًا محددًا من السلوك أو العمليات النفسية باستخدام مناهج بحث وتطبيقات تختلف حسب السؤال والسياق."
        obs = ["موضوعات البحث الأساسية", "المناهج المستخدمة", "التطبيقات والحدود المهنية"]
        distinctions = ["الفرع العلمي أوسع من تقنية علاجية واحدة.", "النتائج البحثية العامة لا تُحوّل مباشرة إلى تشخيص فردي."]
    elif any(x in category for x in ("النمو", "التربوي", "الطفولة", "الأسرة", "الاحتياجات")):
        definition = f"{domain} موضوع يرتبط بالنمو والتعلم والأسرة والبيئة المحيطة. فهمه يتطلب مقارنة السلوك بالعمر النمائي وملاحظة الأداء في أكثر من سياق والاستماع إلى الطفل والأسرة والمهنيين."
        obs = ["المهارات النمائية والتواصل", "الأداء في البيت والمدرسة", "احتياجات الدعم ونقاط القوة"]
        distinctions = ["الاختلاف الفردي لا يعني اضطرابًا تلقائيًا.", "التقييم الجيد يجمع التاريخ النمائي والملاحظة ولا يعتمد على اختبار واحد."]
    elif any(x in category for x in ("العلاقات", "الاجتماعي", "الأسرة")):
        definition = f"{domain} مفهوم يصف نمطًا أو خبرة في العلاقات والسياق الاجتماعي. لا يُستخدم كملصق ثابت للشخص، بل لفهم السلوك والحدود والأمان والتأثير المتبادل."
        obs = ["طريقة التواصل وحل الخلاف", "الأمان والاحترام والحدود", "تكرار النمط وآثاره"]
        distinctions = ["وصف السلوك أدق من تشخيص الآخرين عن بعد.", "لا يبرر أي مفهوم نفسي العنف أو الإكراه أو الإهانة."]
    elif any(x in category for x in ("المعرفي", "الذاكرة", "التعلم")):
        definition = f"{domain} عملية أو نمط معرفي يؤثر في استقبال المعلومات أو تنظيمها أو تذكرها أو استخدامها. يتأثر بالنوم والانفعال والصحة والسياق، لذلك لا يُفسر بمعزل عن بقية الوظائف."
        obs = ["الدقة والسرعة والجهد", "تأثير الضغط والنوم", "الفرق بين القدرة والأداء في موقف محدد"]
        distinctions = ["ضعف الأداء مرة واحدة لا يثبت ضعف القدرة.", "الاختبارات المعرفية تحتاج معايير مناسبة للعمر واللغة والتعليم."]
    elif any(x in category for x in ("الشخصية", "الذات")):
        definition = f"{domain} مفهوم يتعلق بسمات أو أنماط في تصور الذات والتفاعل مع المواقف. السمات تقع على متصل، ولا تتحول إلى اضطراب إلا وفق نمط واسع ومستمر ومؤثر مع تقييم مهني."
        obs = ["ثبات النمط عبر المواقف", "المرونة عند التغير", "الأثر على العلاقات والقرارات"]
        distinctions = ["السمة ليست تشخيصًا.", "السلوك المتأثر بضغط مؤقت لا يعرّف شخصية كاملة."]
    elif any(x in category for x in ("اضطرابات", "الصدمة", "الإدمان", "السلامة")):
        definition = f"{domain} حالة أو مجموعة أعراض نفسية تُفهم عبر النمط والمدة والشدة والأثر في الوظائف المهمة. التشخيص يتطلب تقييمًا مهنيًا واستبعاد أسباب أو حالات أخرى."
        obs = ["الأعراض الانفعالية والمعرفية", "التغير السلوكي والجسدي", "الأثر على النوم والعمل والعلاقات"]
        distinctions = ["وجود بعض العلامات لا يساوي تشخيصًا.", "السياق الطبي والدوائي والتنموي جزء من التقييم."]
    else:
        definition = f"{domain} مفهوم في علم النفس والصحة النفسية يصف خبرة أو عملية أو نمطًا سلوكيًا. يُفهم بدقة عبر التعريف والسياق والمدة والأثر، مع تجنب الاختزال والتشخيص الذاتي."
        obs = ["الموقف الذي يظهر فيه", "تكراره وشدته", "أثره في القرارات والعلاقات والحياة اليومية"]
        distinctions = ["المفهوم العلمي أدق من الاستخدام الشعبي للكلمة.", "الاختلاف الطبيعي لا يصبح مشكلة إلا عند الضيق أو التعطيل أو الخطر."]
    return {"definition": definition, "observations": obs, "distinctions": distinctions, "related": []}


def profile_for(domain: str, category: str) -> dict[str, Any]:
    base = category_profile(domain, category)
    if domain in OVERRIDES:
        merged = dict(base)
        merged.update(OVERRIDES[domain])
        return merged
    return base


def all_domains() -> list[tuple[str, str, str]]:
    legacy = load_legacy()
    result: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in list(legacy.DOMAINS) + EXTRA_DOMAINS:
        ar = item[0]
        if ar in seen:
            continue
        result.append(tuple(item)); seen.add(ar)
        if len(result) == 100:
            break
    if len(result) != 100:
        raise SystemExit(f"Expected 100 unique domains, found {len(result)}")
    return result


def entries() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    idx = 1
    for domain_index, (ar, en, category) in enumerate(all_domains(), 1):
        for facet_index, facet in enumerate(FACETS, 1):
            items.append({"id": idx,"slug": f"concept-{idx:04d}","ar": f"{ar}: {facet['ar']}","en": f"{en}: {facet['en']}","domain_ar": ar,"domain_en": en,"category": category,"facet": facet,"domain_index": domain_index,"facet_index": facet_index})
            idx += 1
    return items


def head(title: str, description: str, path: str, schema: dict[str, Any], keywords: list[str]) -> str:
    canonical = BASE + path.lstrip("/")
    image = BASE + "assets/brand/social-card.svg"
    keyword_text = ", ".join(dict.fromkeys(str(value).strip() for value in keywords if str(value).strip()))
    return f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keyword_text)}"><meta name="author" content="{ORG}"><meta name="application-name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta name="subject" content="علم النفس والصحة النفسية والتربية الدامجة"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="bingbot" content="index,follow,max-image-preview:large,max-snippet:-1"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="theme-color" content="#fff0f6"><link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE}manifest.webmanifest"><link rel="stylesheet" href="{BASE}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE}assets/css/marshmallow-v12.css"><link rel="stylesheet" href="{BASE}assets/css/encyclopedia-v13.css"><meta property="og:locale" content="ar_AR"><meta property="og:type" content="article"><meta property="og:site_name" content="{ORG}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{esc(image)}"><meta property="og:image:alt" content="بطاقة منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="article:modified_time" content="{TODAY}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{esc(image)}"><meta name="twitter:image:alt" content="بطاقة منصة الصحة النفسية وذوي الاحتياجات الخاصة"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>'''


def source_links(sources: list[tuple[str, str]]) -> str:
    return "".join(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{esc(title)}</a></li>' for title, url in sources)


def related_for(item: dict[str, Any], by_domain: dict[str, list[dict[str, Any]]], by_facet: dict[str, list[dict[str, Any]]], domain_map: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    same_domain = by_domain[item["domain_ar"]]
    pos = item["facet_index"] - 1
    result.extend(same_domain[(pos + offset) % len(same_domain)] for offset in (1, 2, 5, 9))
    for related_name in profile_for(item["domain_ar"], item["category"]).get("related", []):
        candidates = domain_map.get(related_name, [])
        if candidates:
            result.append(candidates[min(pos, len(candidates)-1)])
    result.extend(by_facet[item["facet"]["key"]][i] for i in range(min(3, len(by_facet[item["facet"]["key"]]))))
    unique: list[dict[str, Any]] = []
    seen: set[str] = {item["slug"]}
    for candidate in result:
        if candidate["slug"] not in seen:
            unique.append(candidate); seen.add(candidate["slug"])
        if len(unique) == 8:
            break
    return unique


def concept_html(item: dict[str, Any], related: list[dict[str, Any]]) -> tuple[str, str]:
    domain = item["domain_ar"]
    facet = item["facet"]
    profile = profile_for(domain, item["category"])
    sources = choose_sources(domain, facet["key"], item["category"])
    intent = search_intent_for(item)
    title = seo_title(item)
    description = meta_description(item)
    canonical = BASE + f"encyclopedia/{item['slug']}/"
    keywords = [
        domain,
        item["domain_en"],
        facet["ar"],
        facet["en"],
        item["category"],
        intent["primary_query"],
        *intent["secondary_queries"][:3],
        "علم النفس",
        "الصحة النفسية",
    ]
    faq = faq_items(item, profile, intent)
    breadcrumb_id = canonical + "#breadcrumb"
    faq_id = canonical + "#faq"
    article_id = canonical + "#article"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": BASE + "#organization",
                "name": ORG,
                "url": BASE,
                "logo": {"@type": "ImageObject", "url": BASE + "assets/brand/logo-mark.svg"},
            },
            {
                "@type": "WebSite",
                "@id": BASE + "#website",
                "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                "url": BASE,
                "inLanguage": "ar",
                "publisher": {"@id": BASE + "#organization"},
            },
            {
                "@type": "DefinedTerm",
                "@id": canonical + "#term",
                "name": item["ar"],
                "alternateName": item["en"],
                "description": description,
                "inDefinedTermSet": BASE + "encyclopedia/",
                "url": canonical,
            },
            {
                "@type": "Article",
                "@id": article_id,
                "headline": title,
                "name": item["ar"],
                "description": description,
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": TODAY,
                "author": {"@id": BASE + "#organization"},
                "publisher": {"@id": BASE + "#organization"},
                "mainEntityOfPage": {"@id": canonical + "#webpage"},
                "about": {"@id": canonical + "#term"},
                "keywords": keywords,
                "citation": [url for _, url in sources],
            },
            {
                "@type": "WebPage",
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": "ar",
                "dateModified": TODAY,
                "isPartOf": {"@id": BASE + "#website"},
                "about": {"@id": canonical + "#term"},
                "mainEntity": [{"@id": article_id}, {"@id": faq_id}],
                "breadcrumb": {"@id": breadcrumb_id},
                "publisher": {"@id": BASE + "#organization"},
                "audience": {"@type": "Audience", "audienceType": intent["audience"]},
                "keywords": keywords,
                "citation": [url for _, url in sources],
            },
            {
                "@type": "BreadcrumbList",
                "@id": breadcrumb_id,
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "الموسوعة", "item": BASE + "encyclopedia/"},
                    {"@type": "ListItem", "position": 3, "name": domain, "item": BASE + f"hubs/topic-{item['domain_index']:03d}/"},
                    {"@type": "ListItem", "position": 4, "name": facet["ar"], "item": canonical},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": faq_id,
                "mainEntity": [
                    {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
                    for question, answer in faq
                ],
            },
        ],
    }
    observations = profile["observations"] + [f"في زاوية {facet['ar']}، اسأل تحديدًا: {question}" for question in facet["questions"]]
    obs_html = "".join(f"<li>{esc(x)}</li>" for x in observations)
    distinctions = profile["distinctions"] + [f"عند تناول {facet['ar']} في {domain}، يجب التمييز بين المعلومات التثقيفية وبين قرار التقييم أو العلاج الفردي."]
    distinction_html = "".join(f"<li>{esc(x)}</li>" for x in distinctions)
    actions = [f"{action} طبّق ذلك في سياق {domain} مع مراعاة العمر والبيئة والهدف." for action in facet["actions"]] + [f"حدّد أثر {domain} على مجال واحد قابل للقياس مثل النوم أو الدراسة أو العمل أو العلاقات.", f"راجع التغير في {domain} خلال فترة زمنية واضحة بدل الحكم من موقف منفرد.", "عند وجود خطر على السلامة أو تدهور سريع أو تعطيل شديد، تكون الأولوية للتواصل مع خدمة طوارئ محلية أو مختص مؤهل."]
    actions_html = "".join(f"<li>{esc(x)}</li>" for x in actions)
    related_html = "".join(f'<li><a href="{BASE}encyclopedia/{x["slug"]}/">{esc(x["ar"])}</a><span lang="en" dir="ltr"> — {esc(x["en"])}</span></li>' for x in related)
    intent_queries_html = "".join(f"<li>{esc(query)}</li>" for query in intent["all_queries"])
    faq_html = "".join(f'<article><h3>{esc(question)}</h3><p>{esc(answer)}</p></article>' for question, answer in faq)
    body = f'''<!doctype html><html lang="ar" dir="rtl"><head>{head(title, description, f"encyclopedia/{item['slug']}/", schema, keywords)}</head><body><main class="ency-v13" data-v13-page="concept" data-encyclopedia-seo="v1"><nav class="ency-v13__crumbs" aria-label="مسار التنقل"><a href="{BASE}">الرئيسية</a> ← <a href="{BASE}encyclopedia/">الموسوعة</a> ← <a href="{BASE}hubs/topic-{item['domain_index']:03d}/">{esc(domain)}</a> ← {esc(facet['ar'])}</nav><header class="ency-v13__hero"><div class="ency-v13__meta"><span class="ency-v13__tag">{esc(item['category'])}</span><span class="ency-v13__tag">مراجعة: {TODAY}</span><span class="ency-v13__tag">المدخل {item['id']} من 2000</span><span class="ency-v13__tag">نية البحث: {esc(intent['type_ar'])}</span></div><h1>{esc(item['ar'])}</h1><p lang="en" dir="ltr">{esc(item['en'])}</p><p>{esc(profile['definition'])} وتركز هذه الصفحة على <strong>{esc(facet['focus'])}</strong>.</p></header><article class="ency-v13__article" data-v13-article="1"><section><h2>تعريف دقيق وسياق الاستخدام</h2><p>{esc(profile['definition'])}</p><p>عند الحديث عن <strong>{esc(item['ar'])}</strong> لا يكفي ذكر الاسم أو علامة واحدة. الفهم المسؤول يجمع بين ما يحدث، ومتى بدأ، وكم يتكرر، ومدى شدته، وما إذا كان يغيّر أداء الشخص أو أمانه أو قدرته على الدراسة والعمل والتواصل. زاوية <strong>{esc(facet['ar'])}</strong> تضيف سؤالًا محددًا: {esc(facet['focus'])}.</p></section><section class="ency-v13__intent" id="search-intent" {SEARCH_INTENT_MARKER}><h2>نوايا البحث التي تجيب عنها الصفحة</h2><p>صُممت صفحة {esc(item['ar'])} لتلبية نية بحث <strong>{esc(intent['type_ar'])}</strong> في مرحلة <strong>{esc(intent['stage'])}</strong>. هدفها في موضوع {esc(domain)} وزاوية {esc(facet['ar'])} هو {esc(intent['goal'])} دون تحويل المعلومات العامة إلى تشخيص أو خطة فردية.</p><div class="ency-v13__intent-grid"><div class="ency-v13__intent-card"><h3>السؤال الرئيسي</h3><p class="ency-v13__intent-query">{esc(intent['primary_query'])}</p></div><div class="ency-v13__intent-card"><h3>نطاق الإجابة</h3><p>{esc(intent['answer_scope'])}</p></div><div class="ency-v13__intent-card"><h3>لمن تفيد؟</h3><p>{esc('، '.join(intent['audience']))}</p></div></div><h3>عبارات بحث مرتبطة</h3><ul>{intent_queries_html}</ul></section><section><h2>{esc(facet['section'])}: ما الذي ينبغي ملاحظته؟</h2><p>تختلف صورة {esc(domain)} بين الأشخاص، وقد تتأثر بالعمر والصحة والنوم والضغط والبيئة والخبرة السابقة. لذلك تُستخدم النقاط التالية كمنظم للملاحظة والحوار، لا كقائمة تشخيص ذاتي:</p><ul>{obs_html}</ul></section><section><h2>الفروق التي تمنع الخلط</h2><p>تزداد دقة المعرفة عندما نعرف حدود المصطلح وما الذي قد يشبهه. في موضوع {esc(domain)}، تساعد الفروق الآتية على تجنب التعميم والوصم:</p><ul>{distinction_html}</ul></section><section><h2>كيف يُجمع فهم متكامل؟</h2><p>في تقييم {esc(item['ar'])} يبدأ الفهم بخط زمني: ما الوضع المعتاد؟ ما التغير الجديد؟ ما المواقف التي تزيد أو تخفف الصعوبة؟ ثم تُراجع الوظائف المهمة مثل النوم والتعلم والعمل والعلاقات والرعاية الذاتية. وتختلف أهمية هذه المعلومات في زاوية {esc(facet['ar'])} بحسب العمر والسياق؛ ففي الأطفال أو المراهقين تكون معلومات الأسرة والمدرسة والتاريخ النمائي مهمة، بينما يحتاج التغير المفاجئ أو الجسدي إلى مراجعة طبية مناسبة.</p><div class="ency-v13__callout"><strong>قاعدة عملية:</strong> لا توجد نتيجة إلكترونية أو صفحة واحدة تستطيع تشخيص {esc(domain)}. المقاييس قد تدعم الفحص والمتابعة، لكن التشخيص أو الخطة العلاجية قرار مهني يعتمد على معلومات متعددة.</div></section><section><h2>خطوات عملية مرتبطة بـ{esc(facet['ar'])}</h2><ol>{actions_html}</ol></section><section><h2>دور الأسرة أو شبكة الدعم</h2><p>في سياق {esc(domain)} وخصوصًا عند مناقشة {esc(facet['ar'])}، يجمع الدعم المفيد بين الاستماع والاحترام والحدود. يمكن للأسرة أن تساعد في تنظيم المواعيد، توثيق التغير، تخفيف العوائق اليومية، ودعم الالتزام بالخطة دون تحويل الشخص إلى “حالة” أو مراقبته بصورة مهينة. عند الأطفال وذوي الاحتياجات الخاصة، يُفضّل بناء خطة مشتركة توضح نقاط القوة والاحتياجات وطريقة التواصل وما الذي يهدئ وما الذي يفاقم الضغط.</p><p>مهما كان تفسير {esc(domain)} أو زاوية {esc(facet['ar'])}، لا ينبغي تفسير العنف أو الإكراه أو الإهمال على أنه مجرد عرض نفسي. في وجود خطر مباشر تكون السلامة وطلب المساعدة المحلية العاجلة أولوية.</p></section><section><h2>متى تكون المساعدة المهنية مهمة؟</h2><ul><li>عندما يستمر الأثر أو يتفاقم بدل التحسن.</li><li>عند تعطّل النوم أو الدراسة أو العمل أو العلاقات أو الرعاية الذاتية.</li><li>عند ظهور سلوك خطِر أو أفكار إيذاء النفس أو الآخرين أو فقد الاتصال بالواقع.</li><li>عندما تكون الصورة معقدة أو تتداخل مع حالة طبية أو دوائية أو نمائية.</li></ul></section><section class="ency-v13__faq" id="faq" {FAQ_MARKER}><h2>أسئلة شائعة مرتبطة بنية البحث</h2>{faq_html}</section><section><h2>أسئلة تساعدك قبل الموعد</h2><details><summary>ما أهم المعلومات التي أدوّنها؟</summary><p>قبل موعد يتعلق بـ{esc(item['ar'])} دوّن وقت البداية، التكرار، الشدة، المحفزات، ما الذي يخففها، أثرها اليومي، الأدوية والحالة الصحية، والتغيرات التي لاحظها أشخاص موثوقون.</p></details><details><summary>كيف أعرف أن الخطة مفيدة؟</summary><p>في متابعة {esc(domain)} من زاوية {esc(facet['ar'])} حدد مؤشرات عملية مثل تحسن النوم أو الحضور أو القدرة على إكمال مهمة أو انخفاض التجنب، وراجعها دوريًا مع المختص بدل الاعتماد على الشعور العام وحده.</p></details><details><summary>هل يمكن الاكتفاء بالمعلومات العامة؟</summary><p>المعلومات العامة حول {esc(item['ar'])} تساعد في الفهم والاستعداد، لكنها لا تكفي عندما توجد معاناة مستمرة أو تعطيل أو خطر أو حاجة إلى تشخيص وعلاج فردي.</p></details></section><section><h2>موضوعات مرتبطة</h2><ul>{related_html}</ul></section><section class="ency-v13__sources"><h2>مصادر رسمية للمراجعة</h2><p>تم ربط مدخل {esc(item['ar'])} بمصادر مؤسسية عامة تساعد على التحقق والتوسع. قد تتغير التوصيات بمرور الوقت، لذلك تُراجع المصادر الأصلية عند اتخاذ قرار صحي متعلق بـ{esc(domain)}.</p><ul>{source_links(sources)}</ul></section><aside class="ency-v13__callout ency-v13__warning"><strong>حدود المحتوى:</strong> هذا شرح تثقيفي منظم، وليس تشخيصًا أو وصفة علاجية أو بديلًا عن الطبيب أو الأخصائي النفسي المرخّص.</aside></article></main><script src="{BASE}assets/js/app-v10.js" defer></script><script src="{BASE}assets/js/lab-v12.js" defer></script></body></html>'''
    return body, description


def hub_page(title: str, description: str, path: str, links: list[dict[str, Any]], intro: str) -> str:
    canonical = BASE + path
    schema = {"@context":"https://schema.org","@type":"CollectionPage","name":title,"description":description,"url":canonical,"numberOfItems":len(links),"inLanguage":"ar"}
    cards = "".join(f'<article class="ency-v13__card"><span class="ency-v13__tag">{esc(x["category"])}</span><h2><a href="{BASE}encyclopedia/{x["slug"]}/">{esc(x["ar"])}</a></h2><p lang="en" dir="ltr">{esc(x["en"])}</p></article>' for x in links)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>{head(title+' | '+ORG,description,path,schema,[title,"علم النفس","الموسوعة النفسية"])}</head><body><main class="ency-v13" data-v13-page="hub"><nav class="ency-v13__crumbs"><a href="{BASE}">الرئيسية</a> ← <a href="{BASE}hubs/">المراكز الموضوعية</a> ← {esc(title)}</nav><header class="ency-v13__hero"><h1>{esc(title)}</h1><p>{esc(intro)}</p><p><strong>{len(links)}</strong> صفحة مترابطة، مع انتقال مباشر إلى التعريف والتقييم والدعم والتطبيقات.</p></header><section class="ency-v13__grid">{cards}</section></main><script src="{BASE}assets/js/app-v10.js" defer></script><script src="{BASE}assets/js/lab-v12.js" defer></script></body></html>'''


def build() -> dict[str, Any]:
    if not SITE.exists():
        raise SystemExit("_site does not exist")
    items = entries()
    if len(items) != 2000 or len({x['ar'] for x in items}) != 2000:
        raise SystemExit("v13 entry count or title uniqueness failed")
    for folder in (SITE/"encyclopedia", SITE/"hubs"):
        if folder.exists(): shutil.rmtree(folder)
    write(SITE/"assets/css/encyclopedia-v13.css", V13_CSS)

    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_facet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_domain[item["domain_ar"]].append(item)
        by_facet[item["facet"]["key"]].append(item)
    domain_map = by_domain

    descriptions: list[str] = []
    seo_titles: list[str] = []
    primary_queries: list[str] = []
    concept_urls: list[str] = []
    article_hashes: set[str] = set()
    long_paragraphs: Counter[str] = Counter()
    seo_complete_pages = 0
    search_intent_sections = 0
    faq_schema_pages = 0
    min_chars = 10**9
    for item in items:
        related = related_for(item, by_domain, by_facet, domain_map)
        markup, description = concept_html(item, related)
        intent = search_intent_for(item)
        descriptions.append(description)
        seo_titles.append(seo_title(item))
        primary_queries.append(intent["primary_query"])
        required_fragments = (
            '<meta name="description"', '<meta name="robots"', '<meta name="googlebot"',
            '<link rel="canonical"', 'hreflang="ar"', 'hreflang="x-default"',
            'property="og:title"', 'property="og:image:alt"', 'name="twitter:image:alt"',
            'data-encyclopedia-seo="v1"', SEARCH_INTENT_MARKER, FAQ_MARKER,
            '"@type":"DefinedTerm"', '"@type":"Article"',
            '"@type":"WebPage"', '"@type":"BreadcrumbList"', '"@type":"FAQPage"',
        )
        missing = [fragment for fragment in required_fragments if fragment not in markup]
        if missing:
            raise SystemExit(f"Incomplete encyclopedia SEO for {item['slug']}: {missing}")
        if markup.count(SEARCH_INTENT_MARKER) != 1 or markup.count(FAQ_MARKER) != 1:
            raise SystemExit(f"Search-intent marker count failed: {item['slug']}")
        seo_complete_pages += 1
        search_intent_sections += 1
        faq_schema_pages += 1
        path = SITE/"encyclopedia"/item["slug"]/"index.html"
        write(path, markup)
        concept_urls.append(BASE+f"encyclopedia/{item['slug']}/")
        article_match = re.search(r'<article class="ency-v13__article"[^>]*>(.*?)</article>', markup, re.S)
        article = article_match.group(1) if article_match else ""
        plain = normalize(re.sub(r"<[^>]+>", " ", article))
        min_chars = min(min_chars, len(plain))
        digest = hashlib.sha256(plain.encode()).hexdigest()
        if digest in article_hashes:
            raise SystemExit(f"duplicate full article: {item['slug']}")
        article_hashes.add(digest)
        for p in re.findall(r"<p[^>]*>(.*?)</p>", article, re.S):
            text = normalize(re.sub(r"<[^>]+>", " ", p))
            if len(text) >= 180 and "حدود المحتوى" not in text:
                long_paragraphs[text] += 1

    hub_urls: list[str] = []
    hub_cards: list[str] = []
    for idx, (domain, group) in enumerate(by_domain.items(), 1):
        path = f"hubs/topic-{idx:03d}/"
        title = f"{domain}: الدليل الموضوعي الكامل"
        description = f"مركز موضوعي يجمع عشرين زاوية موثقة لفهم {domain} والتقييم والدعم والتطبيقات المختلفة."
        markup = hub_page(title, description, path, group, "مسار منظم يبدأ بالتعريف ثم ينتقل إلى العلامات والعوامل والتقييم والفروق والعلاج والدعم عبر مراحل العمر والأسرة والعمل والتعليم.")
        write(SITE/path/"index.html", markup); hub_urls.append(BASE+path)
        hub_cards.append(f'<article class="ency-v13__card"><h2><a href="{BASE}{path}">{esc(title)}</a></h2><p>{esc(description)}</p></article>')

    for idx, facet in enumerate(FACETS, 1):
        group = by_facet[facet["key"]]
        path = f"hubs/angle-{idx:03d}/"
        title = f"{facet['ar']}: مسار مقارن عبر علم النفس"
        description = f"مركز يقارن زاوية {facet['ar']} عبر مئة موضوع نفسي ونمائي وعلاجي."
        markup = hub_page(title, description, path, group, f"هذا المسار يسمح بمقارنة {facet['focus']} بين الاضطرابات والعمليات المعرفية والعلاقات والنمو والعلاج والقياس.")
        write(SITE/path/"index.html", markup); hub_urls.append(BASE+path)
        hub_cards.append(f'<article class="ency-v13__card"><h2><a href="{BASE}{path}">{esc(title)}</a></h2><p>{esc(description)}</p></article>')

    categories = sorted({x["category"] for x in items})
    cross_facets = [FACETS[i] for i in (0,1,3,5,7,10,15,19)]
    combos: list[tuple[str, dict[str, Any]]] = []
    for category in categories:
        for facet in cross_facets:
            combos.append((category, facet))
    for idx, (category, facet) in enumerate(combos[:80], 1):
        candidates = [x for x in items if x["category"] == category and x["facet"]["key"] == facet["key"]]
        path = f"hubs/path-{idx:03d}/"
        title = f"{category}: {facet['ar']}"
        description = f"مسار تطبيقي يجمع موضوعات {category} من زاوية {facet['ar']} مع روابط للتوسع."
        markup = hub_page(title, description, path, candidates, f"يعرض هذا المركز {facet['focus']} داخل {category} بصورة تسمح بالمقارنة دون خلط بين المصطلحات أو تحويلها إلى تشخيصات سريعة.")
        write(SITE/path/"index.html", markup); hub_urls.append(BASE+path)
        hub_cards.append(f'<article class="ency-v13__card"><h2><a href="{BASE}{path}">{esc(title)}</a></h2><p>{esc(description)}</p></article>')
    if len(hub_urls) != 200:
        raise SystemExit(f"Expected 200 hubs, got {len(hub_urls)}")

    api_items = []
    csv_items = []
    for x in items:
        intent = search_intent_for(x)
        record = {
            "id": x["id"], "slug": x["slug"], "ar": x["ar"], "en": x["en"],
            "domain": x["domain_ar"], "category": x["category"], "facet": x["facet"]["ar"],
            "url": BASE + f"encyclopedia/{x['slug']}/", "reviewed_at": TODAY,
            "seo_title": seo_title(x), "meta_description": meta_description(x),
            "search_intent": intent,
        }
        api_items.append(record)
        csv_items.append({
            "id": x["id"], "slug": x["slug"], "ar": x["ar"], "en": x["en"],
            "domain": x["domain_ar"], "category": x["category"], "facet": x["facet"]["ar"],
            "url": record["url"], "reviewed_at": TODAY, "seo_title": record["seo_title"],
            "meta_description": record["meta_description"],
            "search_intent_type": intent["type"], "primary_query": intent["primary_query"],
            "secondary_queries": " | ".join(intent["secondary_queries"]),
        })
    write(SITE/"api/encyclopedia-v13.json", json.dumps({"version":13,"count":EXPECTED_DETAIL_PAGES,"seo_contract":"encyclopedia-search-intent-v1","items":api_items}, ensure_ascii=False, separators=(",",":")))
    write(SITE/"api/encyclopedia-seo-search-intent-v1.json", json.dumps({
        "version": 1, "status": "passed", "pages": EXPECTED_DETAIL_PAGES,
        "unique_titles": len(set(seo_titles)), "unique_descriptions": len(set(descriptions)),
        "unique_primary_queries": len(set(primary_queries)), "search_intent_sections": search_intent_sections,
        "faq_schema_pages": faq_schema_pages, "seo_complete_pages": seo_complete_pages,
        "items": [{"slug": item["slug"], "url": item["url"], "seo_title": item["seo_title"], "meta_description": item["meta_description"], "search_intent": item["search_intent"]} for item in api_items],
    }, ensure_ascii=False, separators=(",",":")))
    (SITE/"downloads").mkdir(parents=True, exist_ok=True)
    with (SITE/"downloads/encyclopedia-2000-v13.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_items[0].keys())); writer.writeheader(); writer.writerows(csv_items)
    cards = "".join(f'<article class="ency-v13__card ency-item" data-domain="{esc(x["domain_ar"])}" data-category="{esc(x["category"])}" data-q="{esc(normalize(x["ar"]+" "+x["en"]+" "+x["category"]+" "+x["facet"]["ar"]))}"><span class="ency-v13__tag">{esc(x["category"])}</span><h2><a href="{BASE}encyclopedia/{x["slug"]}/">{esc(x["ar"])}</a></h2><p lang="en" dir="ltr">{esc(x["en"])}</p></article>' for x in items)
    domain_options = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in by_domain)
    category_options = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in sorted({x["category"] for x in items}))
    index_script = '''<script>(()=>{const q=document.querySelector('#ency-q'),d=document.querySelector('#ency-domain'),c=document.querySelector('#ency-category'),n=document.querySelector('#ency-count'),items=[...document.querySelectorAll('.ency-item')];function run(){const s=q.value.trim().toLowerCase(),dv=d.value,cv=c.value;let count=0;for(const item of items){const ok=(!s||item.dataset.q.includes(s))&&(!dv||item.dataset.domain===dv)&&(!cv||item.dataset.category===cv);item.hidden=!ok;if(ok)count++}n.textContent=count}q.addEventListener('input',run);d.addEventListener('change',run);c.addEventListener('change',run);run()})()</script>'''
    index_desc = "موسوعة عربية نفسية تضم 2000 صفحة أصلية موزعة على مئة موضوع وعشرين زاوية، مع بحث وفلاتر ومصادر رسمية وروابط داخلية."
    index_schema = {"@context":"https://schema.org","@type":"CollectionPage","name":"الموسوعة النفسية العربية","description":index_desc,"url":BASE+"encyclopedia/","numberOfItems":2000,"inLanguage":"ar"}
    index_html = f'''<!doctype html><html lang="ar" dir="rtl"><head>{head('الموسوعة النفسية العربية | '+ORG,index_desc,'encyclopedia/',index_schema,['الموسوعة النفسية','مصطلحات علم النفس','الصحة النفسية'])}</head><body><main class="ency-v13"><header class="ency-v13__hero"><h1>الموسوعة النفسية العربية</h1><p>مئة موضوع أساسي، وعشرون زاوية لكل موضوع: تعريف وعلامات وعوامل وتقييم وفروق وعلاج ودعم ومراحل عمرية وأسرة وعمل وتعليم وجودة حياة.</p><p><strong id="ency-count">2000</strong> صفحة قابلة للتصفح والفهرسة.</p><div class="ency-v13__search"><input id="ency-q" type="search" placeholder="ابحث بالعربية أو الإنجليزية"><select id="ency-domain"><option value="">كل الموضوعات</option>{domain_options}</select><select id="ency-category"><option value="">كل التصنيفات</option>{category_options}</select></div></header><section class="ency-v13__grid">{cards}</section></main>{index_script}<script src="{BASE}assets/js/app-v10.js" defer></script><script src="{BASE}assets/js/lab-v12.js" defer></script></body></html>'''
    write(SITE/"encyclopedia/index.html", index_html)
    hubs_desc = "مئتا مركز موضوعي ذكي للمقارنة والتصفح: مئة موضوع، وعشرون زاوية، وثمانون مسارًا تطبيقيًا."
    hubs_schema = {"@context":"https://schema.org","@type":"CollectionPage","name":"المراكز الموضوعية النفسية","description":hubs_desc,"url":BASE+"hubs/","numberOfItems":200,"inLanguage":"ar"}
    hubs_html = f'''<!doctype html><html lang="ar" dir="rtl"><head>{head('المراكز الموضوعية النفسية | '+ORG,hubs_desc,'hubs/',hubs_schema,['مراكز علم النفس','الموسوعة النفسية'])}</head><body><main class="ency-v13"><header class="ency-v13__hero"><h1>200 مركز موضوعي</h1><p>مراكز ذات أسماء ومعنى بدل المجموعات الرقمية العامة، وتربط التعريف بالتقييم والعلاج والأسرة والعمر والسياق.</p></header><section class="ency-v13__grid">{''.join(hub_cards)}</section></main><script src="{BASE}assets/js/app-v10.js" defer></script><script src="{BASE}assets/js/lab-v12.js" defer></script></body></html>'''
    write(SITE/"hubs/index.html", hubs_html)
    hub_urls.append(BASE+"hubs/")

    def urlset(urls: list[str]) -> str:
        root = ET.Element("urlset", {"xmlns":"http://www.sitemaps.org/schemas/sitemap/0.9"})
        for url in urls:
            node = ET.SubElement(root,"url"); ET.SubElement(node,"loc").text=url; ET.SubElement(node,"lastmod").text=TODAY
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
    write(SITE/"sitemap-terms-1.xml", urlset(concept_urls[:1000]))
    write(SITE/"sitemap-terms-2.xml", urlset(concept_urls[1000:]))
    write(SITE/"sitemap-hubs.xml", urlset(hub_urls))

    duplicates = {text:count for text,count in long_paragraphs.items() if count > 25}
    if duplicates:
        sample = next(iter(duplicates.items()))
        raise SystemExit(f"excessive repeated long paragraph: {sample}")
    if len(set(descriptions)) != EXPECTED_DETAIL_PAGES:
        raise SystemExit("duplicate meta descriptions")
    if len(set(seo_titles)) != EXPECTED_DETAIL_PAGES:
        raise SystemExit("duplicate SEO titles")
    if len(set(primary_queries)) != EXPECTED_DETAIL_PAGES:
        raise SystemExit("duplicate primary search-intent queries")
    if seo_complete_pages != EXPECTED_DETAIL_PAGES or search_intent_sections != EXPECTED_DETAIL_PAGES or faq_schema_pages != EXPECTED_DETAIL_PAGES:
        raise SystemExit("incomplete encyclopedia SEO/search-intent coverage")
    if min_chars < 1800:
        raise SystemExit(f"article too short: minimum normalized chars {min_chars}")
    report = {"version":13,"concept_pages":EXPECTED_DETAIL_PAGES,"domain_hubs":100,"facet_hubs":20,"application_hubs":80,"hub_pages":200,"unique_titles":len({x['ar'] for x in items}),"unique_seo_titles":len(set(seo_titles)),"unique_article_hashes":len(article_hashes),"unique_descriptions":len(set(descriptions)),"unique_primary_queries":len(set(primary_queries)),"seo_complete_pages":seo_complete_pages,"search_intent_sections":search_intent_sections,"faq_schema_pages":faq_schema_pages,"minimum_article_characters":min_chars,"repeated_long_paragraphs_over_25":len(duplicates),"old_boilerplate_removed":True,"generated":TODAY}
    write(SITE/"api/encyclopedia-audit-v13.json", json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
