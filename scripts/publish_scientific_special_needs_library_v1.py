#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

BASE_URL = "https://healthrenewal.org"
PUBLISHED = "2026-08-11"
REVIEW_DUE = "2027-02-11"

SOURCES = {
    "nice_cp": {
        "title": "NICE NG62: Cerebral palsy in under 25s: assessment and management",
        "url": "https://www.nice.org.uk/guidance/ng62",
        "note": "إرشاد سريري لتشخيص وتقييم وإدارة الشلل الدماغي لدى الأطفال والشباب، مع توصيات للتواصل والمشكلات المصاحبة والمتابعة متعددة التخصصات.",
    },
    "nice_recs": {
        "title": "NICE NG62 Recommendations",
        "url": "https://www.nice.org.uk/guidance/ng62/chapter/Recommendations",
        "note": "التوصيات التفصيلية، ومنها التقييم الدوري للتواصل والإحالة المتخصصة والتدخل المبكر عند الحاجة.",
    },
    "aacpdm_hip": {
        "title": "AACPDM Care Pathway: Hip Surveillance in Cerebral Palsy",
        "url": "https://www.aacpdm.org/publications/care-pathways/hip-surveillance-in-cerebral-palsy",
        "note": "مسار رعاية يشرح المراقبة المنظمة للورك، والفحص السريري والتصوير، وتعديل وتيرة المتابعة بحسب مستوى الخطورة.",
    },
    "aacpdm_dystonia": {
        "title": "AACPDM Care Pathway: Dystonia in Cerebral Palsy",
        "url": "https://www.aacpdm.org/publications/care-pathways/dystonia-in-cerebral-palsy",
        "note": "مسار رعاية للتمييز والتقييم الوظيفي للديستونيا لدى المصابين بالشلل الدماغي وربط التدخل بالأهداف والعبء الوظيفي.",
    },
    "who_rehab": {
        "title": "WHO: Rehabilitation",
        "url": "https://www.who.int/news-room/fact-sheets/detail/rehabilitation",
        "note": "منظمة الصحة العالمية تعرف التأهيل بوصفه تدخلات لتحسين الأداء وتقليل الإعاقة في تفاعل الشخص مع بيئته، وتعزز المشاركة والاستقلال.",
    },
    "who_at": {
        "title": "WHO: Assistive technology",
        "url": "https://www.who.int/health-topics/assistive-technology",
        "note": "مرجع عالمي حول التقنيات المساعدة ودورها في الوظيفة والاستقلال والمشاركة في التعليم والعمل والحياة المجتمعية.",
    },
}

TOPICS = [
    {
        "slug": "cerebral-palsy-evidence-overview",
        "title": "الشلل الدماغي: مدخل علمي قائم على الدليل",
        "description": "مدخل عربي منظم لفهم الشلل الدماغي كحالة نمائية عصبية تؤثر أساسًا في الحركة والوضعية، مع التركيز على الوظيفة والمشاركة والمشكلات المصاحبة.",
        "lead": "الشلل الدماغي ليس تشخيصًا وظيفيًا واحدًا ولا يتنبأ وحده بما يستطيع الشخص فعله. الممارسة الحديثة تجمع بين وصف نمط الحركة، قياس الوظيفة، فهم البيئة، ورصد المشكلات المصاحبة التي قد تؤثر في التعلم والنوم والألم والتواصل والتغذية والمشاركة.",
        "questions": ["ما أثر الحالة في النشاط اليومي والمشاركة، لا في الفحص الحركي فقط؟", "ما القدرات الحالية التي يمكن البناء عليها وما الحواجز البيئية القابلة للتعديل؟", "ما المشكلات المصاحبة التي تستدعي تقييماً متخصصاً أو متابعة دورية؟"],
        "practice": ["استخدام أهداف وظيفية قابلة للقياس مرتبطة بما يهم الشخص والأسرة.", "فصل وصف شدة الاضطراب الحركي عن الحكم على الذكاء أو القدرة على التعلم.", "مراجعة الخطة عند تغير الألم أو النوم أو البلع أو التواصل أو الحركة بدل افتراض أن التغير جزء ثابت من الحالة."],
        "safety": "أي فقد مفاجئ للمهارات، تغير عصبي حاد، صعوبة تنفس أو بلع، ألم شديد جديد أو إصابة يحتاج إلى تقييم صحي عاجل بحسب السياق المحلي.",
        "sources": ["nice_cp", "nice_recs", "who_rehab"],
    },
    {
        "slug": "cerebral-palsy-early-recognition",
        "title": "التعرف المبكر والتقييم في الشلل الدماغي",
        "description": "مبادئ علمية للتعرف المبكر على أنماط النمو الحركي غير المعتادة وإحالة الطفل للتقييم المتخصص دون تأخير الدعم الوظيفي.",
        "lead": "التعرف المبكر لا يعني وضع حكم نهائي من ملاحظة واحدة؛ بل تجميع التاريخ النمائي وعوامل الخطورة والفحص المتكرر ومقاييس موثوقة عند توفرها. الهدف هو تقليل التأخير في التقييم والدعم مع الحفاظ على دقة التشخيص.",
        "questions": ["هل توجد أنماط حركية غير معتادة أو تأخر مستمر في اكتساب المهارات مقارنة بالمسار النمائي المتوقع؟", "هل توجد عوامل قبل الولادة أو حولها أو بعدها تزيد الحاجة إلى متابعة نمائية دقيقة؟", "هل يحتاج الطفل إلى فريق نمائي أو عصبي أو تأهيلي متعدد التخصصات؟"],
        "practice": ["توثيق ما يستطيع الطفل فعله تلقائياً في أكثر من بيئة وعدم الاعتماد على جلسة واحدة.", "إحالة المخاوف المستمرة إلى خدمات نمائية متخصصة بدل الانتظار السلبي.", "بدء الدعم الملائم للوظيفة والتواصل والمشاركة عندما تكون الحاجة واضحة، بالتوازي مع استكمال التقييم."],
        "safety": "الانحدار النمائي أو فقد مهارات مكتسبة ليس نمطاً نموذجياً للشلل الدماغي ويحتاج إلى تقييم طبي لتفسير السبب.",
        "sources": ["nice_cp", "nice_recs"],
    },
    {
        "slug": "cerebral-palsy-communication-aac",
        "title": "التواصل والوسائل المعززة والبديلة AAC في الشلل الدماغي",
        "description": "دليل علمي يضع التواصل الوظيفي في المركز، ويوضح متى يجب تقييم الكلام واللغة ووسائل التواصل المعززة والبديلة ضمن فريق متعدد التخصصات.",
        "lead": "صعوبة وضوح الكلام لا تساوي غياب اللغة أو الفهم. ينبغي تقييم الوصول إلى التواصل بصورة مستقلة، وتوفير وسيلة فعالة للتعبير عن الاحتياجات والاختيارات والرفض والمشاركة الاجتماعية والتعليمية.",
        "questions": ["هل يستطيع الشخص إيصال الرسالة بسرعة كافية وبطريقة يفهمها الشركاء المختلفون؟", "هل توجد طريقة موثوقة للرفض، طلب المساعدة، وصف الألم، وطرح الأسئلة؟", "هل يحتاج الوصول إلى رموز أو لوحة أو جهاز أو طريقة اختيار بديلة بسبب القيود الحركية؟"],
        "practice": ["تقييم الكلام واللغة والتواصل بصورة دورية عند وجود مخاوف، وإشراك اختصاصي النطق واللغة ضمن الفريق.", "عدم اشتراط فشل الكلام قبل تجربة AAC؛ يمكن أن يكون داعماً للكلام أو بديلاً وظيفياً بحسب الحاجة.", "تدريب شركاء التواصل في المنزل والمدرسة والخدمات على إتاحة الوقت وتأكيد الرسالة وعدم التحدث نيابة عن الشخص دون ضرورة."],
        "safety": "لا تُسحب وسيلة التواصل كعقوبة أو لإدارة السلوك؛ الوصول إلى التواصل جزء من السلامة والقدرة على الإبلاغ عن الألم أو الخطر أو الإساءة.",
        "sources": ["nice_recs", "who_at"],
    },
    {
        "slug": "cerebral-palsy-hip-surveillance",
        "title": "مراقبة الورك في الشلل الدماغي: لماذا وكيف تُنظم المتابعة؟",
        "description": "شرح عربي لمسار مراقبة الورك لدى الأطفال والشباب المصابين بالشلل الدماغي، ولماذا يجمع بين الفحص السريري والتصوير وفق مستوى الخطورة.",
        "lead": "إزاحة الورك قد تتطور تدريجياً قبل أن تصبح واضحة وظيفياً. لذلك تعتمد الممارسة المنظمة على المراقبة الاستباقية بدلاً من انتظار الألم أو الخلع، مع تعديل تواتر المتابعة بحسب العمر ومستوى الوظيفة الحركية وعوامل الخطورة.",
        "questions": ["هل يوجد برنامج مراقبة محدد بجدول زمني موثق وليس متابعة عشوائية؟", "هل يشمل التقييم السؤال عن الألم ومدى حركة الورك والفحص الشعاعي عندما يوصي المسار بذلك؟", "هل يعرف الفريق متى تستدعي النتائج إحالة إلى جراحة عظام أطفال أو اختصاص مناسب؟"],
        "practice": ["ربط خطة المراقبة بالعمر ومستوى GMFCS ونمط المشي عند استخدام المسارات المعتمدة محلياً.", "تسجيل نتائج الفحص والتصوير بطريقة تسمح بمقارنة التغير عبر الزمن.", "مناقشة أي ألم أو تناقص في مدى الحركة أو صعوبة جديدة في الجلوس والعناية مع الفريق المعالج."],
        "safety": "المراقبة لا تعني أن الأسرة تقيس أو تفسر الصور بنفسها. قياس نسبة الهجرة وقرار الإحالة والتدخل مسؤولية الفريق السريري المؤهل.",
        "sources": ["aacpdm_hip", "nice_cp"],
    },
    {
        "slug": "cerebral-palsy-dystonia",
        "title": "الديستونيا في الشلل الدماغي: التعرف والتقييم الوظيفي",
        "description": "مدخل قائم على مسار AACPDM لفهم الديستونيا كتقلصات عضلية مستمرة أو متقطعة قد تسبب حركات أو وضعيات غير طبيعية وتتداخل مع النشاط والراحة.",
        "lead": "قد تختلط الديستونيا بالتشنج أو يظهر النمطان معاً. التمييز السريري مهم لأن العبء الوظيفي والمحفزات والاستجابة للتدخل قد تختلف. الهدف ليس وصف النغمة العضلية فقط، بل فهم أثرها في الألم والنوم والعناية الذاتية والتواصل والحركة.",
        "questions": ["هل تتغير الوضعيات أو الحركات مع المحاولة أو اللمس أو الانفعال أو الإرهاق؟", "هل تسبب الديستونيا ألماً أو تعيق النوم أو الجلوس أو الرعاية أو الوصول إلى وسيلة التواصل؟", "هل أهداف التدخل محددة وظيفياً ويمكن قياسها بعد أي تغيير علاجي؟"],
        "practice": ["توثيق المواقف المحفزة والأثر الوظيفي بدل الاكتفاء بوصف عام مثل تيبس أو شد.", "مراجعة الأهداف مع الشخص والأسرة قبل تغيير خطة العلاج.", "متابعة الفائدة والآثار غير المرغوبة باستخدام مؤشرات مرتبطة بالأهداف اليومية."],
        "safety": "التدخلات الدوائية أو الإجراءات المتخصصة للديستونيا تحتاج وصفاً ومتابعة طبية؛ هذه الصفحة لا تقدم جرعات أو اختيار دواء لشخص بعينه.",
        "sources": ["aacpdm_dystonia", "nice_cp"],
    },
    {
        "slug": "rehabilitation-functioning-participation",
        "title": "التأهيل المبني على الوظيفة والمشاركة",
        "description": "كيف ينتقل التأهيل من محاولة تغيير الجسم فقط إلى تحسين الأداء والاستقلال والمشاركة عبر الشخص والمهمة والبيئة.",
        "lead": "تعرف منظمة الصحة العالمية التأهيل بأنه مجموعة تدخلات تهدف إلى تحسين الأداء وتقليل الإعاقة لدى الأشخاص ذوي الحالات الصحية في تفاعلهم مع البيئة. لذلك قد يكون تعديل البيئة أو المهمة أو التقنية المساعدة جزءاً جوهرياً من النتيجة، وليس حلاً ثانوياً.",
        "questions": ["ما النشاط الحقيقي الذي يريد الشخص تحسينه في المنزل أو المدرسة أو المجتمع؟", "أي جزء من الصعوبة يعود إلى متطلبات المهمة أو البيئة ويمكن تغييره؟", "ما المؤشر الذي سيبين أن التدخل حسن المشاركة فعلاً؟"],
        "practice": ["صياغة أهداف مرتبطة بنشاط أو دور حياتي واضح مع خط أساس ومؤشر متابعة.", "اختبار التعديلات في السياق الحقيقي لا داخل العيادة فقط.", "إشراك الشخص والأسرة في الأولويات وموازنة عبء الخطة مع الفائدة المتوقعة."],
        "safety": "التحسن في أداء مهمة لا يبرر تعريض الشخص للألم أو الإرهاق المفرط أو سحب الدعم الذي يحتاجه للاستقلال الآمن.",
        "sources": ["who_rehab", "nice_cp"],
    },
    {
        "slug": "assistive-technology-selection",
        "title": "اختيار التقنية المساعدة: من الحاجة إلى التجربة والمتابعة",
        "description": "إطار علمي لاختيار التقنيات المساعدة انطلاقاً من الوظيفة والسياق والتدريب والصيانة، لا من مواصفات الجهاز وحدها.",
        "lead": "التقنية المساعدة تشمل منتجات وخدمات تدعم الحركة والرؤية والسمع والتواصل والإدراك والعناية الذاتية. نجاحها يعتمد على ملاءمتها للشخص والبيئة والتدريب والمتابعة، وليس على كونها أحدث أو أغلى تقنية.",
        "questions": ["ما الوظيفة المحددة التي يجب أن تحسنها التقنية؟", "هل يمكن تجربتها في البيئة الحقيقية ومع الشركاء الفعليين قبل القرار النهائي؟", "من سيتولى الإعداد والتدريب والصيانة والتعديل عند تغير الاحتياجات؟"],
        "practice": ["تحديد معيار نجاح قبل التجربة مثل سرعة إتمام المهمة أو الاستقلال أو تقليل جهد الشريك.", "مقارنة خيارات منخفضة وعالية التقنية عندما يحقق كلاهما الهدف.", "إعادة تقييم الملاءمة دورياً مع النمو أو تغير البيئة أو المهارات."],
        "safety": "الأجهزة التي تؤثر في الوضعية أو الحركة أو البلع أو السلامة الجسدية قد تحتاج تقييماً وضبطاً من مختص مؤهل؛ لا تكفي المطابقة العامة للمواصفات.",
        "sources": ["who_at", "who_rehab"],
    },
    {
        "slug": "inclusive-education-access",
        "title": "الوصول والمشاركة في التعليم الدامج",
        "description": "إطار وظيفي لرفع المشاركة التعليمية عبر إزالة حواجز البيئة والتعليم والتواصل واستخدام الدعم والتقنيات المساعدة.",
        "lead": "المشاركة التعليمية ليست مجرد وجود الطالب في الصف. الوصول يتطلب أن يستطيع فهم المهمة والتعبير والمشاركة والتنقل واستخدام المواد وإظهار التعلم بطرق مناسبة لقدراته واحتياجاته.",
        "questions": ["ما الحاجز المحدد في النشاط: طريقة العرض، الوقت، الحركة، التواصل، البيئة الحسية أم طريقة الاستجابة؟", "هل التكييف يتيح الوصول إلى هدف التعلم دون خفض التوقعات غير الضرورية؟", "هل يستطيع الطالب استخدام الدعم باستقلال وكرامة عبر المواد والمواقف المختلفة؟"],
        "practice": ["تعديل طريقة الوصول أو الاستجابة عندما يكون الحاجز غير مرتبط بهدف التعلم نفسه.", "دمج وسيلة التواصل والتقنية المساعدة في الروتين اليومي لا في جلسات منفصلة فقط.", "متابعة المشاركة والإنجاز والرفاه معاً، لأن الحضور وحده لا يثبت الدمج الفعلي."],
        "safety": "لا ينبغي أن يؤدي الدعم إلى عزل الطالب عن أقرانه أو التحدث نيابة عنه بصورة دائمة؛ يجب مراجعة أثر التكييف على الاستقلال والمشاركة.",
        "sources": ["who_at", "who_rehab", "nice_recs"],
    },
    {
        "slug": "feeding-swallowing-communication-safety",
        "title": "الأكل والبلع والتواصل: فصل المشاركة عن خطر البلع",
        "description": "مبادئ علمية لتمييز صعوبات المشاركة في الوجبات عن علامات اضطراب البلع التي تحتاج تقييماً صحياً متخصصاً.",
        "lead": "قد تتأثر الوجبات بالوضعية أو الحركة أو التواصل أو الحساسية أو الألم أو مهارات المضغ والبلع. الخطة الآمنة لا تفترض أن الرفض سلوك، ولا تغير قوام الطعام أو السوائل بناءً على التخمين، بل تحدد متى يلزم تقييم متخصص.",
        "questions": ["هل توجد سعال أو اختناق متكرر أو تغيرات تنفسية أو صعوبة واضحة أثناء الأكل والشرب؟", "هل يستطيع الشخص التعبير عن الألم والرفض والاختيار أثناء الوجبة؟", "هل الجلوس والأدوات والوقت والبيئة تدعم المشاركة دون إجبار؟"],
        "practice": ["توثيق علامات الخطر والسياق الذي تظهر فيه وإبلاغ الفريق المختص.", "فصل هدف الاستقلال في الوجبة عن القرارات الطبية المتعلقة بسلامة البلع.", "احترام الإشارات والرفض وإتاحة وسيلة تواصل فعالة خلال الوجبة."],
        "safety": "الاختناق أو صعوبة التنفس حالة طارئة. الاشتباه باضطراب البلع يحتاج تقييماً متخصصاً؛ لا تُغيّر القوامات أو السوائل أو طرق التغذية كبديل عن التقييم السريري.",
        "sources": ["nice_cp", "nice_recs", "who_rehab"],
    },
    {
        "slug": "pain-communication-disability",
        "title": "الألم لدى الأشخاص ذوي صعوبات التواصل: لا تفسره كسلوك فقط",
        "description": "إطار عملي قائم على الوظيفة للتعامل مع تغير السلوك أو المشاركة باعتباره أحياناً إشارة إلى ألم أو مشكلة صحية تحتاج تقييماً.",
        "lead": "عندما يكون التعبير اللفظي محدوداً قد يظهر الألم كتغير في النوم أو الحركة أو الوجه أو التفاعل أو تحمل النشاط. التقييم الجيد يجمع معرفة الشخص بخط أساسه مع فحص الأسباب الصحية ولا يحول كل تغير إلى مشكلة سلوكية.",
        "questions": ["ما التغير الجديد مقارنة بخط الأساس المعتاد للشخص؟", "هل توجد علامات جسدية أو وضعية أو سياقية ترافق التغير؟", "هل يملك الشخص طريقة موثوقة للإشارة إلى مكان الألم وشدته أو طلب التوقف؟"],
        "practice": ["استخدام ملاحظات متعددة من أشخاص يعرفون خط الأساس مع تجنب الاعتماد على انطباع واحد.", "البحث عن أسباب صحية محتملة عند التغير المفاجئ في السلوك أو المشاركة.", "تعزيز مفردات ورموز التواصل المرتبطة بالألم والراحة والتوقف والمساعدة."],
        "safety": "الألم الشديد الجديد أو المتزايد، الإصابة، تغير الوعي أو العلامات العصبية أو التنفسية تستدعي تقييماً طبياً عاجلاً بحسب السياق.",
        "sources": ["nice_cp", "who_rehab", "who_at"],
    },
    {
        "slug": "family-centered-rehabilitation",
        "title": "التأهيل المتمركز حول الشخص والأسرة",
        "description": "مبادئ لصناعة أهداف مشتركة قابلة للقياس وتحويل توصيات الفريق إلى خطة يومية قابلة للتنفيذ دون تحميل الأسرة برنامجاً غير واقعي.",
        "lead": "الرعاية المتمركزة حول الشخص والأسرة لا تعني نقل عبء العلاج إلى الأسرة؛ بل بناء القرار على أولويات الشخص، مشاركة المعلومات بوضوح، وتنسيق أهداف قليلة عالية القيمة يمكن دمجها في الحياة اليومية.",
        "questions": ["ما الأولويات التي يختارها الشخص والأسرة الآن؟", "ما مقدار الوقت والجهد المطلوب وما البدائل الأقل عبئاً؟", "هل يعرف كل عضو في الفريق دوره ومتى ستراجع الخطة؟"],
        "practice": ["اختيار عدد محدود من الأهداف ذات أثر يومي واضح بدلاً من قائمة طويلة متنافسة.", "تحويل التوصيات إلى فرص ممارسة طبيعية داخل الروتين عندما يكون ذلك مناسباً.", "مراجعة الخطة عند ضعف الفائدة أو ارتفاع العبء أو تغير الأولويات."],
        "safety": "لا ينبغي أن تُستخدم مشاركة الأسرة لتبرير غياب الخدمات المهنية الضرورية أو مطالبتها بإجراءات تحتاج تدريباً أو إشرافاً سريرياً متخصصاً.",
        "sources": ["who_rehab", "nice_cp"],
    },
    {
        "slug": "evidence-informed-goal-setting",
        "title": "صياغة أهداف تأهيلية قابلة للقياس ومدعومة بالدليل",
        "description": "طريقة عملية لتحويل الشكوى العامة إلى هدف وظيفي محدد مع خط أساس، تدخل قابل للاختبار، ومؤشر قرار للمراجعة أو التغيير.",
        "lead": "الأهداف الجيدة تربط الدليل بأولويات الشخص. لا يكفي هدف عام مثل تحسين الحركة أو التركيز؛ يجب تحديد النشاط والسياق ومستوى المساعدة ومؤشر التحسن والفترة التي ستراجع عندها الخطة.",
        "questions": ["ما السلوك أو النشاط الذي يمكن ملاحظته وقياسه؟", "ما خط الأساس الحالي وفي أي سياق تم قياسه؟", "ما مقدار التحسن الذي سيعد ذا معنى للشخص والأسرة وليس ذا دلالة رقمية فقط؟"],
        "practice": ["تحديد خط أساس قبل بدء التغيير كلما أمكن.", "اختيار مؤشر واحد أو اثنين يرتبطان مباشرة بالهدف لتقليل عبء القياس.", "وضع نقطة مراجعة مسبقة: نستمر، نعدل، أو نتوقف إذا لم تظهر فائدة كافية أو ظهر ضرر."],
        "safety": "لا ينبغي أن يدفع الهدف القابل للقياس إلى تجاهل الراحة أو الموافقة أو الألم؛ مؤشرات الضرر والعبء جزء من قرار الاستمرار.",
        "sources": ["who_rehab", "nice_recs"],
    },
]

CSS = ":root{--bg:#f4f8f7;--ink:#12231f;--muted:#52645e;--card:#fff;--line:#d6e3df;--accent:#087a67;--soft:#e6f5f1;--warn:#8b4a0c}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}a{color:#056552}header,main,footer{max-width:1120px;margin:auto;padding:1.15rem}.hero{background:linear-gradient(135deg,var(--soft),#fff);border:1px solid var(--line);border-radius:22px;padding:clamp(1.4rem,4vw,3rem);margin:1rem 0 2rem}h1{font-size:clamp(2rem,5vw,3.25rem);line-height:1.3}h2{margin-top:2.2rem}.card,.notice{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.25rem;margin:1rem 0}.notice{border-inline-start:6px solid var(--warn)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}.meta{color:var(--muted)}li{margin:.55rem 0}nav a{margin-inline-end:1rem}.source-list li{overflow-wrap:anywhere}.badge{display:inline-block;background:#dcefe9;border-radius:999px;padding:.2rem .65rem;margin:.2rem}footer{color:var(--muted);font-size:.93rem}"


def render_sources(keys: list[str]) -> str:
    items = []
    for key in keys:
        src = SOURCES[key]
        items.append(f'<li><a href="{escape(src["url"])}" rel="noopener noreferrer">{escape(src["title"])}</a><br><span>{escape(src["note"])}</span></li>')
    return "\n".join(items)


def render_page(topic: dict[str, object]) -> str:
    slug, title, description = str(topic["slug"]), str(topic["title"]), str(topic["description"])
    canonical = f"{BASE_URL}/special-needs/science/{slug}/"
    questions = "".join(f"<li>{escape(str(item))}</li>" for item in topic["questions"])
    practice = "".join(f"<li>{escape(str(item))}</li>" for item in topic["practice"])
    schema = json.dumps({"@context":"https://schema.org","@type":"MedicalWebPage","inLanguage":"ar","headline":title,"description":description,"url":canonical,"datePublished":PUBLISHED,"dateModified":PUBLISHED,"author":{"@type":"Organization","name":"منصة روافد"},"publisher":{"@type":"Organization","name":"منصة روافد"},"isAccessibleForFree":True}, ensure_ascii=False)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | منصة روافد</title><meta name="description" content="{escape(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{escape(title)} | منصة روافد"><meta property="og:description" content="{escape(description)}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="منصة روافد"><meta property="og:image" content="{BASE_URL}/assets/brand/rawafid-social-card.jpg"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script><style>{CSS}</style><link rel="stylesheet" href="/assets/brand/rawafid-brand.css"><link rel="stylesheet" href="/assets/platform/platform-core.css?v=1.1.0"><script defer src="/assets/brand/rawafid-brand.js"></script><script defer src="/assets/platform/platform-core.js?v=1.1.0"></script></head><body class="pt-platform" data-pt-normalized="1.1.0" data-topic="{escape(slug)}"><header><nav aria-label="التنقل الأساسي"><a href="/">الرئيسية</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/special-needs/science/">المكتبة العلمية</a><a href="/trust/">الثقة والمنهج</a></nav></header><main id="content"><section class="hero"><span class="badge">محتوى علمي موثق</span><h1>{escape(title)}</h1><p>{escape(description)}</p><p class="meta">نشر: {PUBLISHED} · مراجعة مخططة: {REVIEW_DUE} · المصادر المرجعية موضحة أدناه</p></section><section class="notice"><h2>حدود الاستخدام</h2><p>هذا المحتوى للتثقيف ودعم الحوار مع الفريق المختص، ولا يشخص حالة فردية ولا يصف دواءً أو جرعةً أو جهازاً أو إجراءً لشخص بعينه. القرارات السريرية تحتاج تقييماً مباشراً ومراعاة العمر والتاريخ الصحي والسياق المحلي.</p></section><section><h2>الفكرة العلمية الأساسية</h2><p>{escape(str(topic["lead"]))}</p><p>المنهج المستخدم هنا يربط بين الدليل المنشور والنتيجة الوظيفية. لا تُعامل التوصيات العامة كقواعد ثابتة لكل شخص؛ بل تُحوّل إلى أسئلة تقييم، ثم أهداف قابلة للقياس، ثم مراجعة للفائدة والعبء والسلامة.</p></section><section><h2>أسئلة تقييم توجه القرار</h2><div class="card"><ul>{questions}</ul></div></section><section><h2>تطبيق عملي مبني على الدليل</h2><div class="card"><ol>{practice}</ol></div><p>عند اختبار أي دعم، يفضل تسجيل خط أساس بسيط قبل التغيير ثم مقارنة النتيجة في أكثر من مناسبة. إذا كان الأداء يتحسن فقط في جلسة منظمة ولا ينتقل إلى الحياة اليومية، فهذه إشارة إلى ضرورة تعديل السياق أو التدريب أو طريقة القياس.</p></section><section><h2>السلامة ومؤشرات التصعيد</h2><div class="notice"><p>{escape(str(topic["safety"]))}</p></div></section><section><h2>كيف نقرأ قوة الدليل؟</h2><p>تختلف قوة التوصيات بحسب نوع السؤال وجودة الدراسات وقابلية تطبيقها. الإرشادات ومسارات الرعاية تجمع الأدلة المتاحة وخبرة الاختصاصيين، لكنها لا تلغي الحكم السريري ولا تفضيلات الشخص. عند وجود تعارض بين هدف وظيفي وسلامة صحية، تُعالج السلامة أولاً ثم يعاد تصميم الهدف بطريقة تحافظ على أكبر قدر ممكن من الاستقلال والمشاركة.</p></section><section><h2>المراجع الأساسية</h2><ul class="source-list">{render_sources(list(topic["sources"]))}</ul><p class="meta">تمت مراجعة روابط المصادر المرجعية عند إعداد هذه النسخة في {PUBLISHED}. يُفضّل الرجوع إلى المصدر الأصلي للتحقق من أي تحديثات لاحقة.</p></section><section><h2>موضوعات مرتبطة</h2><p><a href="/special-needs/science/">العودة إلى المكتبة العلمية</a> · <a href="/special-needs/practical/">الأدلة العملية</a> · <a href="/source-registry/">سجل المصادر</a></p></section></main><footer>© 2026 Khaled Altheeb — منصة روافد. محتوى تثقيفي عام.</footer></body></html>'''


def render_index() -> str:
    cards = "".join(f'<article class="card"><h2><a href="/special-needs/science/{escape(str(t["slug"]))}/">{escape(str(t["title"]))}</a></h2><p>{escape(str(t["description"]))}</p></article>' for t in TOPICS)
    schema = json.dumps({"@context":"https://schema.org","@type":"CollectionPage","inLanguage":"ar","name":"المكتبة العلمية لذوي الاحتياجات الخاصة","url":f"{BASE_URL}/special-needs/science/","dateModified":PUBLISHED,"numberOfItems":len(TOPICS)}, ensure_ascii=False)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>المكتبة العلمية لذوي الاحتياجات الخاصة | منصة روافد</title><meta name="description" content="مكتبة عربية موثقة تربط الأدلة الإرشادية بالتأهيل والشلل الدماغي والتواصل والتقنيات المساعدة والمشاركة التعليمية."><meta name="robots" content="index,follow"><link rel="canonical" href="{BASE_URL}/special-needs/science/"><script type="application/ld+json">{schema}</script><style>{CSS}</style><link rel="stylesheet" href="/assets/brand/rawafid-brand.css"><link rel="stylesheet" href="/assets/platform/platform-core.css?v=1.1.0"></head><body class="pt-platform"><header><nav aria-label="التنقل الأساسي"><a href="/">الرئيسية</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/source-registry/">سجل المصادر</a><a href="/trust/">الثقة والمنهج</a></nav></header><main><section class="hero"><span class="badge">Evidence-informed</span><h1>المكتبة العلمية لذوي الاحتياجات الخاصة</h1><p>حزمة معرفية عربية تربط الإرشادات ومسارات الرعاية الدولية بالوظيفة والمشاركة والسلامة. تضم {len(TOPICS)} موضوعاً علمياً مستقلاً، وكل صفحة تعرض حدود الاستخدام ومراجعها الأصلية.</p><p class="meta">الإصدار الأول · {PUBLISHED}</p></section><section class="grid">{cards}</section><section class="notice"><h2>منهجية التحرير</h2><p>الأولوية للمصادر الأولية المؤسسية مثل WHO وNICE وAACPDM. لا تستبدل المكتبة التقييم السريري، ولا تقدم وصفات علاجية فردية. عند تحديث المصدر المرجعي يجب مراجعة الصفحة المرتبطة قبل اعتماد النسخة التالية.</p></section></main><footer>© 2026 Khaled Altheeb — منصة روافد.</footer></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="_site")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Site root does not exist: {root}")
    base = root / "special-needs" / "science"
    base.mkdir(parents=True, exist_ok=True)
    (base / "index.html").write_text(render_index(), encoding="utf-8")
    routes = ["/special-needs/science/"]
    for topic in TOPICS:
        destination = base / str(topic["slug"])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(render_page(topic), encoding="utf-8")
        routes.append(f'/special-needs/science/{topic["slug"]}/')
    report = {"schemaVersion":1,"status":"passed","published":PUBLISHED,"reviewDue":REVIEW_DUE,"topicPages":len(TOPICS),"totalRoutes":len(routes),"routes":routes,"sourceAuthorities":sorted({SOURCES[key]["title"] for topic in TOPICS for key in topic["sources"]})}
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "scientific-special-needs-library-v1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
