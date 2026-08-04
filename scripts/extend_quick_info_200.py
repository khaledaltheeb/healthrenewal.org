#!/usr/bin/env python3
"""Extend the Quick Information section from 150 to 200 pages.

This module reuses the established page, image, schema, API and sitemap renderer
from ``build_quick_info.py``. It adds 50 curated topics with topic-specific
summaries and guidance, then regenerates the complete section deterministically.
"""

from __future__ import annotations

import json
import re

import build_quick_info as base

EXPECTED_BASE = 150
EXPECTED_TOTAL = 200
NEW_TOPIC_DATA = """emotional-numbness-vs-calm|خدر عاطفي أم هدوء؟ غياب الألم لا يعني دائمًا وجود السلام|comparison|general|خدر عاطفي|هدوء
self-care-vs-avoidance|عناية بالنفس أم هروب؟ الاستراحة التي لا تعيدك إلى حياتك تحتاج مراجعة|comparison|general|عناية بالنفس|تجنب
guilt-vs-shame|ذنب أم عار؟ الفرق بين مراجعة السلوك ورفض الذات كلها|comparison|general|شعور بالذنب|شعور بالعار
privacy-vs-secrecy|خصوصية أم سرية مؤذية؟ ما الذي يحق لكل طرف الاحتفاظ به؟|comparison|relationships|خصوصية|سرية مؤذية
closeness-vs-enmeshment|قرب أم ذوبان في العلاقة؟ الحب لا يلغي الهوية والقرار|comparison|relationships|قرب صحي|تشابك عاطفي
boredom-vs-low-mood|ملل أم مزاج منخفض؟ راقب المتعة والطاقة والاستمرار|comparison|depression|ملل|مزاج منخفض
patience-vs-emotional-suppression|صبر أم كبت؟ تحمل اللحظة لا يعني إنكار المشاعر|comparison|general|صبر|كبت عاطفي
high-standards-vs-perfectionism|معايير عالية أم كمالية؟ عندما يصبح الخطأ تهديدًا لقيمتك|comparison|general|معايير عالية|كمالية مؤذية
restlessness-vs-hyperactivity|تململ أم فرط حركة؟ السياق والعمر وتعدد البيئات تصنع الفرق|comparison|adhd|تململ|فرط حركة
health-awareness-vs-health-anxiety|اهتمام بالصحة أم قلق مرضي؟ كثرة الفحص قد تزيد الخوف|comparison|anxiety|وعي صحي|قلق صحي
discipline-vs-punishment|انضباط أم عقاب؟ الهدف تعليم المهارة لا إخضاع الطفل|comparison|child|انضباط|عقاب
sensory-preference-vs-avoidance|تفضيل حسي أم تجنب حسي؟ متى يضيق الصوت والضوء حياة الطفل؟|comparison|child|تفضيل حسي|تجنب حسي
compassion-fatigue-vs-indifference|إرهاق تعاطف أم لامبالاة؟ مقدم الرعاية قد يحتاج رعاية أيضًا|comparison|care|إرهاق تعاطف|لامبالاة
ambition-vs-overwork|طموح أم إفراط في العمل؟ النجاح الذي يستهلك الصحة ليس مستدامًا|comparison|work|طموح|إفراط في العمل
post-trauma-caution-vs-ptsd|حذر بعد صدمة أم اضطراب ما بعد الصدمة؟ لا يكفي وجود ذكرى مؤلمة|comparison|trauma|حذر بعد صدمة|اضطراب ما بعد الصدمة
emotionally-unavailable-check|هل أنت غير متاح عاطفيًا؟ 10 أسئلة عن القرب والتعبير والانسحاب|check|relationships||
self-criticism-check|هل نقدك لنفسك أصبح مؤذيًا؟ فحص يفرق بين المراجعة وجلد الذات|check|general||
survival-mode-check|هل تعيش في وضع النجاة؟ راقب الجسم والقرارات والشعور بالأمان|check|trauma||
social-media-mood-check|هل تضر وسائل التواصل بمزاجك؟ اختبر ما يحدث قبل الاستخدام وبعده|check|digital||
work-follows-home-check|هل يلاحقك العمل إلى المنزل؟ فحص لحدود التعافي ونهاية الدوام|check|work||
nightmare-sleep-fear-check|هل تخاف النوم بسبب الكوابيس؟ إشارات تحتاج تنظيمًا أو تقييمًا|check|sleep||
over-responsibility-check|هل تحمل مسؤولية الجميع؟ فحص للسيطرة والذنب والإنهاك|check|general||
child-hidden-school-distress-check|هل يخفي طفلك ضيقه في المدرسة؟ راقب ما يظهر بعد العودة للمنزل|check|child||
authentic-self-relationship-check|هل تستطيع أن تكون نفسك داخل العلاقة؟ 10 أسئلة عن الأمان والقبول|check|relationships||
grief-support-check|هل تحتاج دعمًا إضافيًا بعد الفقد؟ فحص للوظيفة والعزلة والأمان|check|grief||
five-reasons-indecision|خمس أسباب نفسية قد تجعلك عالقًا بين القرارات|factors|general||
five-factors-night-loneliness|خمس عوامل تجعل الوحدة أشد في الليل|factors|general||
five-reasons-compliments-uncomfortable|خمس أسباب قد تجعلك تنزعج من المديح|factors|general||
five-factors-emotional-exhaustion|خمس عوامل تصنع الإنهاك العاطفي بصمت|factors|care||
five-reasons-school-refusal|خمس أسباب محتملة لرفض الطفل الذهاب إلى المدرسة|factors|child||
five-reasons-repeated-arguments|خمس أسباب تجعل الخلاف نفسه يتكرر في العلاقة|factors|relationships||
five-factors-breakup-recovery|خمس عوامل تبطئ التعافي بعد الانفصال|factors|relationships||
five-reasons-morning-anxiety|خمس أسباب محتملة للقلق عند الاستيقاظ|factors|anxiety||
five-factors-adhd-symptoms|خمس عوامل خارجية قد تزيد صعوبات الانتباه والتنظيم|factors|adhd||
five-reasons-freeze-under-pressure|خمس أسباب تجعلك تتجمد تحت الضغط بدل التصرف|factors|trauma||
repair-after-argument|كيف تصلح العلاقة بعد خلاف مؤلم؟ ابدأ بالمسؤولية لا بتبرير النية|relationship|relationships||
digital-boundaries-relationship|كيف تضع حدودًا رقمية في العلاقة حول الهاتف والموقع وكلمات المرور؟|relationship|relationships||
co-parenting-after-separation|كيف تنظم الأبوة المشتركة بعد الانفصال دون وضع الطفل في المنتصف؟|practical|child||
emotionally-unavailable-parent|كيف تتعامل مع والد غير متاح عاطفيًا دون إنكار احتياجاتك؟|relationship|relationships||
ask-reassurance-without-dependency|كيف تطلب الطمأنة دون أن تتحول إلى اعتماد مستمر؟|practical|relationships||
respond-passive-aggression|كيف ترد على العدوان السلبي دون دخول لعبة التلميحات؟|relationship|relationships||
end-friendship-respectfully|كيف تنهي صداقة لم تعد آمنة أو متوازنة باحترام؟|relationship|relationships||
financial-abuse-signs|كيف تتعرف إلى الإساءة المالية داخل العلاقة وتحمي خياراتك؟|relationship|relationships||
protect-child-adult-conflict|كيف تحمي الطفل من صراعات الكبار دون مطالبته باختيار طرف؟|practical|child||
workplace-boundaries-manager|كيف تضع حدودًا مهنية مع مديرك دون تصعيد غير محسوب؟|practical|work||
grounding-after-nightmare|كيف تستعيد الإحساس بالأمان بعد كابوس أو استيقاظ مفزع؟|practical|sleep||
reduce-doomscrolling|كيف تقلل التصفح القهري للأخبار دون تجاهل الواقع؟|practical|digital||
return-social-life-after-isolation|كيف تعود إلى الحياة الاجتماعية بعد عزلة طويلة بخطوات قابلة للتحمل؟|practical|general||
guilt-after-saying-no|كيف تتعامل مع الشعور بالذنب بعد قول «لا»؟|practical|relationships||
prepare-psychiatry-appointment|كيف تستعد لموعد الطبيب النفسي وتعرض الأعراض بوضوح؟|practical|care||"""

DETAILS = {
    "emotional-numbness-vs-calm": {"summary": "الهدوء يترك مساحة للشعور والاختيار، بينما قد يظهر الخدر العاطفي كابتعاد عن الفرح والحزن معًا بعد ضغط أو صدمة أو إنهاك.", "key": "هل تستطيع الشعور والتواصل ثم العودة إلى توازنك، أم تبدو التجربة كلها بعيدة ومسطحة؟", "specific": ["فقدان الاستجابة لأحداث كانت مهمة", "الشعور بأنك تراقب نفسك من بعيد", "ضعف الاتصال بالجسد والاحتياجات"]},
    "self-care-vs-avoidance": {"summary": "العناية بالنفس تعيد القدرة على أداء ما يهمك، أما التجنب فيمنح راحة قصيرة ثم يزيد الخوف والتراكم.", "key": "هل الاستراحة تعيدك إلى المهمة بقدرة أفضل، أم تجعل العودة أصعب كل مرة؟", "specific": ["تأجيل متكرر لمهمة محددة", "تزايد الذنب بعد الراحة", "ضيق الحياة بسبب ما تتجنبه"]},
    "guilt-vs-shame": {"summary": "الذنب يركز على سلوك قابل للإصلاح، بينما العار يحول الخطأ إلى حكم شامل بأن الذات سيئة أو غير جديرة.", "key": "هل تفكر: فعلت شيئًا خاطئًا ويمكن إصلاحه، أم أنا الخطأ ولا أستحق القبول؟", "specific": ["اعتذار وإصلاح يتبعهما هدوء نسبي", "إخفاء الذات والخوف من الانكشاف", "جلد ذات لا يتناسب مع الحدث"]},
    "privacy-vs-secrecy": {"summary": "الخصوصية مساحة شخصية متفق عليها، أما السرية المؤذية فتخفي معلومات تمس الأمان أو الاتفاقات الأساسية أو حق الطرف الآخر في القرار.", "key": "هل المساحة تحمي الاستقلال دون خداع، أم تمنع الطرف الآخر من معرفة ما يؤثر مباشرة في حياته؟", "specific": ["اتفاق واضح على حدود الهاتف والحسابات", "إخفاء ديون أو علاقات أو مخاطر مشتركة", "استخدام الخصوصية لإيقاف أي سؤال مشروع"]},
    "closeness-vs-enmeshment": {"summary": "القرب الصحي يسمح بالاتصال والاختلاف، بينما التشابك العاطفي يضعف الحدود ويجعل قرار فرد واحد مسؤولية الجميع.", "key": "هل تستطيع الحفاظ على رأيك ووقتك وعلاقاتك، أم يصبح الاختلاف تهديدًا للعلاقة؟", "specific": ["الشعور بالذنب عند الاستقلال", "توقع معرفة الاحتياجات دون كلام", "تدخل مفرط في القرارات الشخصية"]},
    "boredom-vs-low-mood": {"summary": "الملل غالبًا يتحسن بتغيير النشاط أو المعنى، بينما يمتد المزاج المنخفض إلى الطاقة والمتعة والنوم والنظرة للمستقبل.", "key": "هل يعود الاهتمام عندما يتغير الموقف، أم بقي فقدان المتعة في معظم الأنشطة؟", "specific": ["غياب المتعة حتى في الأشياء المحببة", "استمرار الانخفاض معظم الأيام", "تغير واضح في النوم أو الشهية أو الأمل"]},
    "patience-vs-emotional-suppression": {"summary": "الصبر ينظم رد الفعل مع الاعتراف بالمشاعر، أما الكبت فينكرها أو يمنع التعبير عنها حتى تتراكم أو تظهر جسديًا.", "key": "هل تؤجل التعبير إلى وقت مناسب ثم تناقشه، أم لا تسمح لنفسك أصلًا بالاعتراف بما تشعر؟", "specific": ["انفجارات بعد فترات صمت طويلة", "توتر جسدي دون تفسير واضح", "استخدام الصبر لتبرير استمرار الأذى"]},
    "high-standards-vs-perfectionism": {"summary": "المعايير العالية تقبل التعلم والخطأ، بينما تربط الكمالية القيمة الشخصية بنتيجة مثالية وتؤخر البدء أو الإنهاء.", "key": "هل تساعدك المعايير على التحسن، أم تمنعك من المحاولة خوفًا من نتيجة غير كاملة؟", "specific": ["تأجيل التسليم رغم كفاية العمل", "صعوبة تفويض المهام", "انهيار التقدير الذاتي بعد خطأ صغير"]},
    "restlessness-vs-hyperactivity": {"summary": "التململ قد يرتبط بموقف أو قلق أو نوم، بينما يحتاج تقييم فرط الحركة إلى نمط نمائي مستمر يظهر في أكثر من بيئة.", "key": "هل الحركة مرتبطة بظرف حديث، أم نمط قديم ومتعدد السياقات يؤثر في الوظيفة؟", "specific": ["ظهور الأثر منذ الطفولة", "صعوبة انتظار الدور وكبح الاندفاع", "وجود المشكلة في البيت والدراسة أو العمل"]},
    "health-awareness-vs-health-anxiety": {"summary": "الوعي الصحي يقود إلى فحص مناسب ثم قرار، أما القلق الصحي فيعيد الفحص والبحث والطمأنة دون راحة مستقرة.", "key": "هل المعلومة الطبية الموثوقة تساعدك على الإغلاق، أم تبدأ دورة جديدة من البحث والفحص؟", "specific": ["فحص الجسم مرات كثيرة", "بحث طويل عن أمراض نادرة", "طمأنة مؤقتة يعقبها خوف جديد"]},
    "discipline-vs-punishment": {"summary": "الانضباط يعلّم مهارة وحدًا متوقعًا، أما العقاب فيركز على الألم أو الخضوع وقد لا يعلّم البديل المطلوب.", "key": "هل يعرف الطفل ما المهارة التي سيتعلمها، أم يعرف فقط أنه سيعاقب عند الخطأ؟", "specific": ["تعليم السلوك البديل قبل توقعه", "تناسب النتيجة مع العمر والسلوك", "تجنب الإهانة والخوف كأدوات طاعة"]},
    "sensory-preference-vs-avoidance": {"summary": "التفضيل الحسي لا يعطل الحياة غالبًا، أما التجنب الحسي فقد يحد الملابس والطعام والمدرسة واللعب ويحتاج فهمًا وظيفيًا.", "key": "هل هو اختيار مريح بين بدائل، أم استجابة شديدة تضيق الأنشطة اليومية؟", "specific": ["ألم أو انهيار مع أصوات محددة", "رفض ملابس أو أطعمة بسبب الملمس", "تجنب أماكن ضرورية كليًا"]},
    "compassion-fatigue-vs-indifference": {"summary": "إرهاق التعاطف قد يخفف القدرة المؤقتة على الاستجابة بسبب التعرض المستمر لمعاناة الآخرين، ولا يعني غياب القيم أو الرحمة.", "key": "هل تراجعت استجابتك بعد حمل رعاية طويل مع شعور بالإنهاك، أم لا يوجد اهتمام أو مسؤولية أصلًا؟", "specific": ["تبلد بعد نوبات رعاية مكثفة", "أحلام أو استدعاء لمشاهد مؤلمة", "ذنب عند أخذ استراحة"]},
    "ambition-vs-overwork": {"summary": "الطموح يحدد أهدافًا مع موارد وتعافٍ، أما الإفراط في العمل فيستمر رغم الضرر ويجعل التوقف مصدر قلق أو ذنب.", "key": "هل العمل يخدم هدفًا يمكن مراجعته، أم أصبح الطريقة الوحيدة للشعور بالقيمة أو الأمان؟", "specific": ["إلغاء النوم والعلاقات باستمرار", "قلق واضح عند التوقف", "استمرار العمل رغم تدهور الصحة"]},
    "post-trauma-caution-vs-ptsd": {"summary": "الحذر بعد الصدمة قد يكون متوقعًا، لكن اضطراب ما بعد الصدمة يتضمن نمطًا مستمرًا من الاستعادة والتجنب وتغيرات المزاج واليقظة مع تعطل.", "key": "هل تتراجع الاستجابة تدريجيًا مع الأمان، أم يستمر النمط ويعيد تنظيم الحياة حول الخطر؟", "specific": ["ذكريات أو كوابيس اقتحامية", "تجنب واسع لما يذكّر بالحدث", "يقظة شديدة وتعطل مستمر"]},
    "emotionally-unavailable-check": {"summary": "فحص للتعرف إلى نمط تجنب القرب أو صعوبة تسمية المشاعر أو الانسحاب عند الاحتياج، دون تحويله إلى ملصق ثابت.", "questions": ["هل تنسحب كلما طلب منك شخص قريب الحديث عن المشاعر؟", "هل تشعر أن الاحتياج ضعف أو عبء؟", "هل تختار علاقات لا تتطلب قربًا حقيقيًا؟", "هل تستخدم الانشغال الدائم لتجنب الاتصال؟", "هل يصعب عليك طلب الدعم حتى عند الحاجة؟"]},
    "self-criticism-check": {"summary": "النقد المفيد يحدد سلوكًا وخطوة، أما جلد الذات فيستخدم لغة مطلقة ويقلل القدرة على التعلم.", "questions": ["هل تصف نفسك بكلمات مهينة عند الخطأ؟", "هل تتجاهل النجاحات وتضخم العيوب؟", "هل تطلب من نفسك ما لا تطلبه من الآخرين؟", "هل يمنعك الخوف من النقد من البدء؟", "هل يبقى العقاب الداخلي بعد إصلاح الخطأ؟"]},
    "survival-mode-check": {"summary": "وضع النجاة وصف لتجربة بقاء الجسم والذهن في التأهب، وليس تشخيصًا مستقلًا.", "questions": ["هل تشعر بالعجلة حتى دون خطر مباشر؟", "هل يصعب عليك الراحة دون ذنب أو خوف؟", "هل تركز على اجتياز اليوم دون قدرة على التخطيط؟", "هل تفزع بسهولة أو تراقب البيئة باستمرار؟", "هل تبدو احتياجاتك الأساسية مؤجلة دائمًا؟"]},
    "social-media-mood-check": {"summary": "راقب العلاقة بين الاستخدام والمزاج بدل الحكم من عدد الساعات وحده.", "questions": ["هل ينخفض مزاجك بعد المقارنة بالآخرين؟", "هل تستخدم التطبيق للهروب ثم تشعر بأسوأ؟", "هل يؤخر الاستخدام نومك؟", "هل تفشل حدود الوقت التي تضعها مرارًا؟", "هل تتعرض لمحتوى يزيد الخوف أو كراهية الذات؟"]},
    "work-follows-home-check": {"summary": "انتهاء الدوام لا يعني التعافي إذا بقي الذهن والجسد داخل مطالب العمل.", "questions": ["هل تفحص الرسائل خارج الدوام دون ضرورة؟", "هل تعيد مواقف العمل ذهنيًا لساعات؟", "هل يؤثر العمل في النوم أو الحضور مع الأسرة؟", "هل تشعر بالذنب عند عدم التوفر؟", "هل لم تعد العطلة القصيرة تعيد طاقتك؟"]},
    "nightmare-sleep-fear-check": {"summary": "الخوف من الكوابيس قد يدفع إلى تأخير النوم ويزيد الحرمان واليقظة، ويحتاج تقييمًا عند التكرار أو الارتباط بصدمة.", "questions": ["هل تؤخر النوم خوفًا من حلم متكرر؟", "هل تستيقظ مرتبكًا أو في حالة تأهب؟", "هل تتجنب مكان النوم أو الظلام؟", "هل تؤثر الكوابيس في النهار والتركيز؟", "هل ترتبط بحدث صادم أو دواء أو مادة؟"]},
    "over-responsibility-check": {"summary": "تحمل المسؤولية يصبح مؤذيًا عندما تعتبر نفسك مسؤولًا عن مشاعر وقرارات ونتائج لا تملك السيطرة عليها.", "questions": ["هل تتدخل لمنع كل نتيجة عن الآخرين؟", "هل تشعر بالذنب عند قول لا؟", "هل يصعب عليك التفويض؟", "هل تراقب مزاج الجميع قبل احتياجاتك؟", "هل تنهك ثم تلوم نفسك على التعب؟"]},
    "child-hidden-school-distress-check": {"summary": "بعض الأطفال يمسكون أنفسهم في المدرسة ثم يظهر الضيق في المنزل؛ جمع المعلومات من البيئتين مهم.", "questions": ["هل تحدث الانهيارات بعد العودة من المدرسة؟", "هل تظهر آلام بطن أو رأس صباحًا؟", "هل يتغير النوم قبل أيام الدراسة؟", "هل يرفض الحديث عن زملاء أو معلم؟", "هل يبدو أداؤه جيدًا مع استنزاف شديد بعده؟"]},
    "authentic-self-relationship-check": {"summary": "الأمان النفسي يظهر في القدرة على الاختلاف والتعبير والحدود دون خوف من السخرية أو العقاب.", "questions": ["هل تستطيع قول رأي مختلف؟", "هل تخفي أجزاء أساسية من شخصيتك لتجنب الرفض؟", "هل يحترم الطرف الآخر حدودك وخصوصيتك؟", "هل يمكن إصلاح الخلاف دون تهديد؟", "هل تحتفظ بعلاقاتك واهتماماتك المستقلة؟"]},
    "grief-support-check": {"summary": "الحزن لا يملك جدولًا واحدًا، لكن استمرار التعطل أو العزلة أو اليأس يستحق دعمًا إضافيًا.", "questions": ["هل تعجز عن أداء المسؤوليات الأساسية؟", "هل أصبحت معزولًا تمامًا؟", "هل تستخدم مواد أو سلوكًا خطيرًا لتسكين الألم؟", "هل يزداد اليأس بدل أن يتحرك في موجات؟", "هل توجد أفكار موت أو إيذاء للنفس؟"]},
    "five-reasons-indecision": {"summary": "التردد ليس ضعف شخصية دائمًا؛ قد يحميك مؤقتًا من خوف أو مسؤولية أو خسارة متخيلة.", "factors": ["الخوف من الندم", "كمالية تبحث عن قرار بلا مخاطرة", "تعارض القيم والاحتياجات", "نقص المعلومات أو كثرتها", "إرهاق القرار وقلة النوم"]},
    "five-factors-night-loneliness": {"summary": "قد تشتد الوحدة ليلًا عندما تقل المشتتات ويزداد الاجترار وتضعف فرص الاتصال الفوري.", "factors": ["غياب روتين مسائي داعم", "استخدام رقمي قائم على المقارنة", "ذكريات مرتبطة بوقت الليل", "اضطراب النوم والإرهاق", "نقص اتصال منتظم ذي معنى"]},
    "five-reasons-compliments-uncomfortable": {"summary": "الانزعاج من المديح قد يرتبط بصورة ذاتية سلبية أو خوف من التوقعات أو خبرات جعلت الثناء غير آمن.", "factors": ["عدم توافق المديح مع صورة الذات", "الخوف من توقع أداء أعلى", "الشك في نية المادح", "تربية تقلل التعبير الإيجابي", "الشعور بعدم الاستحقاق"]},
    "five-factors-emotional-exhaustion": {"summary": "الإنهاك العاطفي يتراكم عندما تتكرر المطالب الانفعالية دون حدود أو دعم أو وقت معالجة.", "factors": ["رعاية مستمرة دون بديل", "تعرض متكرر لأزمات الآخرين", "كبت المشاعر المهنية أو الأسرية", "حدود غير واضحة", "نوم وتعافٍ غير كافيين"]},
    "five-reasons-school-refusal": {"summary": "رفض المدرسة سلوك له وظيفة محتملة، ولا ينبغي اختزاله في العناد قبل فحص الأمان والتعلم والصحة.", "factors": ["قلق الانفصال أو التقييم", "تنمر أو شعور بعدم الأمان", "صعوبة تعلم أو انتباه", "حساسية حسية أو إرهاق اجتماعي", "ألم أو اضطراب نوم أو مشكلة صحية"]},
    "five-reasons-repeated-arguments": {"summary": "تكرار الخلاف قد يعني أن المشكلة الأساسية لم تُسمّ أو أن طريقة الإصلاح نفسها تعيد الجرح.", "factors": ["احتياج غير مصاغ بوضوح", "دفاع واتهام بدل وصف السلوك", "وعود دون تغيير قابل للقياس", "حدود غير متفق عليها", "توقيت سيئ مع إرهاق أو غضب"]},
    "five-factors-breakup-recovery": {"summary": "التعافي بعد الانفصال يتأثر بالنمط السابق وبالبيئة الحالية، وليس بقوة الإرادة وحدها.", "factors": ["تواصل متقطع يعيد الأمل", "مراقبة الحسابات والرسائل", "عزلة وفقد الروتين", "مثالية الذاكرة ونسيان الأذى", "غياب دعم أو معنى جديد"]},
    "five-reasons-morning-anxiety": {"summary": "القلق الصباحي قد يتأثر بالنوم والكافيين والتوقعات والضغط، ويحتاج تقييمًا عند الاستمرار أو الأعراض الجسدية.", "factors": ["نوم متقطع أو غير كاف", "استيقاظ مباشرة على الأخبار والرسائل", "توقع يوم مثقل أو غير واضح", "كافيين مبكر بجرعة عالية", "قلق أو اكتئاب أو سبب صحي"]},
    "five-factors-adhd-symptoms": {"summary": "حتى لدى المصاب بـADHD تتغير شدة الصعوبات حسب البيئة والنوم وبنية المهمة والدعم.", "factors": ["قلة النوم", "مقاطعات وإشعارات مستمرة", "مهمة غامضة أو طويلة", "ضغط وقلق مرتفعان", "غياب أدوات تنظيم خارجية"]},
    "five-reasons-freeze-under-pressure": {"summary": "التجمد استجابة عصبية محتملة للتهديد، وقد يظهر عندما يشعر الشخص أن القتال أو الهرب غير متاحين.", "factors": ["تهديد مفاجئ أو غامض", "خبرات سابقة مشابهة", "خوف شديد من الخطأ", "تضارب أوامر ومطالب", "إرهاق يقلل المرونة العصبية"]},
    "repair-after-argument": {"summary": "الإصلاح يبدأ بفهم الضرر وتحمل الجزء الشخصي وتغيير سلوك محدد، لا بإثبات أن النية كانت جيدة.", "specific": ["العودة للحوار بعد هدوء متفق عليه", "وصف ما حدث دون تعميم أو إهانة", "اتفاق على خطوة تمنع تكرار النمط"], "action": "ابدأ باعتراف محدد بالأثر قبل شرح دوافعك."},
    "digital-boundaries-relationship": {"summary": "الحدود الرقمية تحتاج اتفاقًا صريحًا حول الخصوصية والتوفر والموقع والصور، ولا تُستنتج من الغيرة أو الحب.", "specific": ["توقع الرد الفوري في كل وقت", "طلب كلمات المرور أو الموقع بالإكراه", "نشر صور أو رسائل دون موافقة"], "action": "اكتبوا اتفاقًا واضحًا لما هو اختياري وما هو ضروري للأمان."},
    "co-parenting-after-separation": {"summary": "الأبوة المشتركة الناجحة تقلل انتقال الصراع إلى الطفل وتفصل بين الخلاف الزوجي ومسؤوليات الرعاية.", "specific": ["رسائل عملية تركز على احتياجات الطفل", "جدول واضح وقابل للتوقع", "منع استخدام الطفل ناقلًا للمعلومات"], "action": "اجعل التواصل مختصرًا وموثقًا ومتمحورًا حول الطفل."},
    "emotionally-unavailable-parent": {"summary": "قد لا يستطيع الوالد تقديم القرب المطلوب، ويمكنك الاعتراف بالخسارة وبناء حدود ودعم دون انتظار تغير غير مضمون.", "specific": ["إنكار المشاعر أو السخرية منها", "تواصل يقتصر على الواجبات", "انسحاب عند الحديث عن الألم"], "action": "حدد ما يمكن طلبه واقعيًا وابنِ مصادر دعم أخرى."},
    "ask-reassurance-without-dependency": {"summary": "الطمأنة الصحية طلب واضح ومحدود، أما الاعتماد فيجعل الراحة متوقفة على تكرار تأكيدات لا تدوم.", "specific": ["إعادة السؤال نفسه بعد دقائق", "مراقبة نبرة الرد بدل مضمونه", "تصاعد القلق عند تأخر الاستجابة"], "action": "اطلب نوع الطمأنة مرة بوضوح ثم استخدم مهارة تنظيم ذاتي."},
    "respond-passive-aggression": {"summary": "العدوان السلبي يعبّر عن الغضب بالتلميح أو التأخير أو الإنكار؛ الرد المباشر الهادئ يمنع لعبة التخمين.", "specific": ["تعليقات ساخرة قابلة للإنكار", "موافقة لفظية يتبعها تعطيل", "صمت أو تأخير بقصد العقاب"], "action": "صف السلوك الملاحظ واطلب جوابًا مباشرًا دون اتهام النوايا."},
    "end-friendship-respectfully": {"summary": "إنهاء الصداقة قد يكون ضروريًا عندما يغيب الأمان أو التوازن، ويمكن فعله بوضوح يتناسب مع مستوى الخطر.", "specific": ["تكرار الإهانة أو الاستغلال", "غياب الإصلاح بعد مناقشات واضحة", "خوف مستمر من رد الفعل"], "action": "اختر رسالة قصيرة تحدد القرار والحدود دون محاكمة طويلة."},
    "financial-abuse-signs": {"summary": "الإساءة المالية تستخدم المال أو العمل أو الديون لتقليل حرية الطرف الآخر وقد ترافقها مراقبة وتهديد وعزل.", "specific": ["منع الوصول إلى الحسابات أو الوثائق", "ديون أو التزامات باسمك دون موافقة", "منع العمل أو الاستيلاء على الدخل"], "action": "احفظ نسخًا آمنة من الوثائق واطلب دعمًا قانونيًا أو اجتماعيًا محليًا."},
    "protect-child-adult-conflict": {"summary": "الطفل لا ينبغي أن يحمل أسرار الكبار أو رسائلهم أو مسؤولية تهدئة أحد الوالدين.", "specific": ["سؤال الطفل عن الطرف الآخر", "مشاركته تفاصيل لا تناسب عمره", "طلب اختيار طرف أو حفظ سر"], "action": "قدّم تفسيرًا بسيطًا يؤكد أن الصراع مسؤولية الكبار وأن الطفل محبوب."},
    "workplace-boundaries-manager": {"summary": "الحدود المهنية تنجح أكثر عندما تُربط بالأولويات والموارد والمواعيد بدل أن تُعرض كرفض شخصي.", "specific": ["مهام متعارضة بلا ترتيب", "اتصال دائم خارج الدوام", "توسع مستمر في الدور دون موارد"], "action": "اطلب تحديد الأولوية: ما الذي سيتأخر إذا أضيفت هذه المهمة؟"},
    "grounding-after-nightmare": {"summary": "بعد الكابوس يحتاج الدماغ إلى إشارات حسية وزمنية تؤكد أن الحدث انتهى وأنك في مكان آمن الآن.", "specific": ["تشوش بين الحلم والواقع للحظات", "خفقان وتعرق ويقظة", "خوف من العودة إلى النوم"], "action": "سمّ المكان والتاريخ، أشعل ضوءًا هادئًا، والمس سطحًا ثابتًا مع زفير بطيء."},
    "reduce-doomscrolling": {"summary": "التصفح القهري للأخبار يعطي شعورًا مؤقتًا بالسيطرة لكنه قد يزيد الخوف ويؤخر النوم دون تحسين الاستعداد.", "specific": ["تحديث الصفحات دون معلومة جديدة", "صعوبة التوقف رغم ارتفاع القلق", "بدء اليوم ونهايته بالأخبار"], "action": "حدد نافذتين قصيرتين من مصادر موثوقة وأوقف الإشعارات العاجلة غير الضرورية."},
    "return-social-life-after-isolation": {"summary": "العودة بعد العزلة تحتاج تدرجًا؛ الهدف اتصال قابل للاستمرار لا اختبار اجتماعي كبير يثبت أنك تعافيت.", "specific": ["توقع أداء اجتماعي مثالي", "اختيار لقاء طويل كخطوة أولى", "تفسير التعب بعد اللقاء كفشل"], "action": "ابدأ باتصال قصير مع شخص آمن وحدد وقت الانتهاء مسبقًا."},
    "guilt-after-saying-no": {"summary": "الشعور بالذنب بعد وضع حد لا يثبت أن الحد خاطئ؛ قد يكون أثرًا لتعلم قديم يربط القبول بالطاعة.", "specific": ["شرح طويل ومحاولات تبرير", "التراجع فور ظهور استياء", "تحمل ما يفوق القدرة لتجنب الرفض"], "action": "كرر الحد بجملة قصيرة واسمح للشعور بالذنب أن ينخفض دون إلغائه."},
    "prepare-psychiatry-appointment": {"summary": "التحضير الجيد يساعد الطبيب على فهم المدة والشدة والأثر والأدوية والمخاطر بدل الاعتماد على ذاكرة مضغوطة داخل الموعد.", "specific": ["خط زمني للأعراض والتغيرات", "قائمة الأدوية والمواد والمكملات", "أمثلة على أثر الأعراض في النوم والعمل والعلاقات"], "action": "اكتب أهم ثلاثة أسئلة وأي مخاوف سلامة قبل الموعد."},
}


def parse_new_topics() -> list[dict]:
    topics = []
    for line in NEW_TOPIC_DATA.strip().splitlines():
        slug, title, fmt, domain, left, right = line.split("|")
        topics.append({"slug": slug, "title": title, "format": fmt, "domain": domain, "left": left, "right": right})
    return topics


ORIGINAL_SUMMARY = base.summary
ORIGINAL_BODY = base.body


def summary(topic: dict) -> str:
    detail = DETAILS.get(topic["slug"])
    return detail["summary"] if detail else ORIGINAL_SUMMARY(topic)


def _list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    cls = " class='steps'" if ordered else ""
    return f"<{tag}{cls}>" + "".join(f"<li>{base.e(item)}</li>" for item in items) + f"</{tag}>"


def body(topic: dict) -> str:
    detail = DETAILS.get(topic["slug"])
    if not detail:
        return ORIGINAL_BODY(topic)
    guide = base.guide(topic)
    fmt = topic["format"]
    if fmt == "comparison":
        specific = detail["specific"]
        rows = [
            ("المعنى", f"{base.e(topic['left'])}: يظهر مع بقاء قدر من الاختيار والمرونة.", f"{base.e(topic['right'])}: يحتاج النظر إلى النمط والأثر لا الاسم وحده."),
            ("ما يرجّح الفرق", base.e(specific[0]), base.e(specific[1])),
            ("الأثر الوظيفي", "قد يبقى الأداء ممكنًا مع تعديل بسيط.", base.e(specific[2])),
            ("السؤال الفاصل", base.e(detail["key"]), "لا يكفي عرض واحد أو موقف منفرد للتشخيص."),
            ("الخطوة", "دوّن المدة والسياق وما يساعد.", "اطلب تقييمًا عند الاستمرار أو التعطل أو الخطر."),
        ]
        trs = "".join(f"<tr><th>{a}</th><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
        return (
            f"<h2>الخلاصة الدقيقة</h2><p>{base.e(detail['summary'])}</p>"
            f"<div class='notice'><strong>السؤال الأهم</strong>{base.e(detail['key'])}</div>"
            f"<table class='compare'><thead><tr><th>المعيار</th><th>{base.e(topic['left'])}</th><th>{base.e(topic['right'])}</th></tr></thead><tbody>{trs}</tbody></table>"
            f"<h2>إشارات تستحق المراقبة</h2>{_list(specific + guide['signals'][:2])}"
            f"<h2>خطوات عملية</h2>{_list(guide['actions'], ordered=True)}"
        )
    if fmt == "check":
        questions = (list(detail["questions"]) + ["هل استمر النمط بدل أن يكون موقفًا عابرًا؟", "هل أثر في النوم أو العمل أو الدراسة أو العلاقات؟", "هل دفعك إلى التجنب أو العزلة؟", "هل لاحظه شخص موثوق؟", "هل توجد خطورة أو فقدان قدرة على العناية بالنفس؟"])[:10]
        return (
            f"<h2>قبل الإجابة</h2><p>{base.e(detail['summary'])}</p>"
            "<div class='notice'><strong>الفحص للتثقيف لا للتشخيص.</strong> لا تجمع الإجابات لتمنح نفسك تسمية؛ راقب المدة والشدة والأثر.</div>"
            f"<h2>الأسئلة العشرة</h2>{_list(questions, ordered=True)}"
            f"<h2>ما الخطوة التالية؟</h2>{_list(guide['actions'], ordered=True)}"
        )
    if fmt == "factors":
        sections = "".join(
            f"<section><h3>{i}. {base.e(value)}</h3><p>قد يساهم هذا العامل في النمط، لكنه لا يثبت السبب وحده. راقب توقيته وما يزيده وما يخففه.</p></section>"
            for i, value in enumerate(detail["factors"], 1)
        )
        return (
            f"<h2>الفكرة الأساسية</h2><p>{base.e(detail['summary'])}</p>"
            "<div class='notice'><strong>لا تختزل السبب في عامل واحد.</strong> الأسباب النفسية والجسدية والاجتماعية قد تتداخل.</div>"
            f"<h2>العوامل الخمسة</h2>{sections}"
            f"<h2>خطة مراجعة عملية</h2>{_list(guide['actions'], ordered=True)}"
        )
    specific = detail["specific"]
    actions = [detail["action"]] + guide["actions"][:4]
    safety = ""
    if topic["slug"] in {"financial-abuse-signs", "protect-child-adult-conflict"}:
        safety = "<div class='notice'><strong>الأمان أولًا.</strong> عند وجود تهديد أو عنف أو سيطرة قسرية استخدم دعمًا محليًا متخصصًا ولا تدخل مواجهة غير آمنة.</div>"
    return (
        f"<h2>الخلاصة</h2><p>{base.e(detail['summary'])}</p>"
        f"<h2>ما الذي تراقبه؟</h2>{_list(specific + guide['signals'][:2])}"
        f"<h2>خطة قابلة للتنفيذ</h2>{_list(actions, ordered=True)}"
        f"{safety}<h2>ما الذي لا يساعد؟</h2>{_list(['التعميم والاتهام بدل وصف السلوك', 'انتظار اللحظة المثالية أو اعتذار كامل', 'العزلة عن مصادر الدعم الموثوقة'])}"
    )


def patch_homepage_count() -> None:
    path = base.ROOT / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- QUICK_INFO_SECTION_START -->.*?<!-- QUICK_INFO_SECTION_END -->", re.DOTALL)
    match = pattern.search(text)
    if match:
        block = match.group(0).replace("150", "200")
        text = text[:match.start()] + block + text[match.end():]
    base.write(path, text)


def write_tests(new_slugs: set[str]) -> None:
    new_slug_literal = repr(sorted(new_slugs))
    content = """from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 200
NEW_SLUGS = __NEW_SLUGS__

def test_quick_info():
    api = json.loads((ROOT / "api/v1/quick-info.json").read_text(encoding="utf-8"))
    assert api["count"] == EXPECTED
    assert len(api["items"]) == EXPECTED
    assert len(list((ROOT / "quick-info").glob("*/index.html"))) == EXPECTED
    assert len({item["slug"] for item in api["items"]}) == EXPECTED
    assert len({item["title"] for item in api["items"]}) == EXPECTED
    assert set(NEW_SLUGS).issubset({item["slug"] for item in api["items"]})
    for item in api["items"]:
        page = ROOT / "quick-info" / item["slug"] / "index.html"
        source = page.read_text(encoding="utf-8")
        assert "max-image-preview:large" in source
        assert '"Article"' in source
        assert '"FAQPage"' in source
        assert "المصادر المحورية" in source
        assert item["url"] in source
        with Image.open(ROOT / "assets/quick-info/cards" / (item["slug"] + ".png")) as image:
            assert image.size == (1280, 720)
    sitemap = (ROOT / "sitemap-quick-info.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == EXPECTED + 1
    assert "sitemap-quick-info.xml" in (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
    hub = (ROOT / "quick-info/index.html").read_text(encoding="utf-8")
    assert "200 صفحة" in hub
    assert 'href="/quick-info/"' in (ROOT / "index.html").read_text(encoding="utf-8")
""".replace("__NEW_SLUGS__", new_slug_literal)
    base.write(base.ROOT / "tests/test_quick_info_section.py", content)


def main() -> None:
    existing = list(base.TOPICS)
    if len(existing) != EXPECTED_BASE:
        raise SystemExit(f"Expected {EXPECTED_BASE} base topics, found {len(existing)}")
    new_topics = parse_new_topics()
    existing_slugs = {topic["slug"] for topic in existing}
    existing_titles = {topic["title"] for topic in existing}
    collisions = [topic["slug"] for topic in new_topics if topic["slug"] in existing_slugs or topic["title"] in existing_titles]
    if collisions:
        raise SystemExit(f"Topic collisions: {collisions}")
    base.TOPICS = existing + new_topics
    base.summary = summary
    base.body = body
    if len(base.TOPICS) != EXPECTED_TOTAL:
        raise SystemExit(f"Expected {EXPECTED_TOTAL} topics, found {len(base.TOPICS)}")
    if len({topic["slug"] for topic in base.TOPICS}) != EXPECTED_TOTAL:
        raise SystemExit("Duplicate slugs")
    if len({topic["title"] for topic in base.TOPICS}) != EXPECTED_TOTAL:
        raise SystemExit("Duplicate titles")
    for topic in base.TOPICS:
        if not re.fullmatch(r"[a-z0-9-]+", topic["slug"]):
            raise SystemExit(f"Invalid slug: {topic['slug']}")
        if topic["format"] not in base.FORMAT_LABELS:
            raise SystemExit(f"Invalid format: {topic['format']}")
        if topic["domain"] not in base.GUIDES:
            raise SystemExit(f"Invalid domain: {topic['domain']}")
    base.write(base.ROOT / "assets/quick-info/quick-info.css", base.CSS)
    base.write(base.ROOT / "quick-info/index.html", base.hub().replace("150", "200"))
    base.make_image(base.ROOT / "assets/quick-info/quick-info-cover.png")
    for topic in base.TOPICS:
        base.write(base.ROOT / "quick-info" / topic["slug"] / "index.html", base.article(topic))
        base.make_image(base.ROOT / "assets/quick-info/cards" / (topic["slug"] + ".png"), topic)
    base.update_home()
    patch_homepage_count()
    base.sitemap()
    base.api()
    write_tests({topic["slug"] for topic in new_topics})
    report = {
        "generatedAt": base.PUBLISHED + "T09:08:00+03:00",
        "pages": EXPECTED_TOTAL,
        "images": EXPECTED_TOTAL + 1,
        "newPages": len(new_topics),
        "formats": {key: sum(1 for topic in base.TOPICS if topic["format"] == key) for key in base.FORMAT_LABELS},
        "discover": {"largeImages": True, "maxImagePreviewLarge": True, "articleSchema": True, "faqSchema": True, "canonicalUrls": True, "nonDiagnosticDisclosures": True},
        "errors": [],
    }
    base.write(base.ROOT / "reports/quick-info-build.json", json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
