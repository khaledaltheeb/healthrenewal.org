#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import random
import re
from pathlib import Path
from xml.sax.saxutils import escape as xesc

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://healthrenewal.org"
PUBLISHED = "2026-08-04"
SECTION = "quick-info"
AUTHOR = "فريق التحرير الصحي في المنصة"

TOPIC_DATA = """sadness-vs-depression|حزن أم اكتئاب؟ الفارق الذي يغيّر طريقة طلب المساعدة|comparison|depression|حزن|اكتئاب
fatigue-vs-laziness|إرهاق أم كسل؟ 7 علامات تكشف ما يحدث فعلًا|comparison|general|إرهاق|كسل
love-vs-painful-attachment|حب أم تعلق مؤلم؟ عندما يتحول القرب إلى استنزاف|comparison|relationships|حب|تعلق مؤلم
shyness-vs-social-anxiety|خجل أم قلق اجتماعي؟ متى يصبح تجنب الناس مشكلة؟|comparison|anxiety|خجل|قلق اجتماعي
panic-vs-heart-emergency|نوبة هلع أم مشكلة قلبية؟ الأعراض قد تتشابه ولا يجوز التخمين|comparison|anxiety|نوبة هلع|مشكلة قلبية
normal-forgetting-vs-evaluation|نسيان طبيعي أم علامة تستحق التقييم؟ راقب النمط لا الموقف الواحد|comparison|general|نسيان طبيعي|حاجة إلى تقييم
mood-swings-vs-bipolar|تقلب مزاج أم اضطراب ثنائي القطب؟ الفرق أكبر من يوم جيد ويوم سيئ|comparison|bipolar|تقلب مزاج|اضطراب ثنائي القطب
order-vs-ocd|حب الترتيب أم وسواس قهري؟ عندما يصبح القلق هو المحرّك|comparison|ocd|حب الترتيب|وسواس قهري
calm-vs-withdrawal|هدوء أم انسحاب نفسي؟ الصمت لا يعني دائمًا الراحة|comparison|general|هدوء|انسحاب نفسي
confidence-vs-narcissism|ثقة بالنفس أم نرجسية؟ الاختبار الحقيقي يظهر عند النقد والحدود|comparison|relationships|ثقة بالنفس|سمات نرجسية
jealousy-vs-control|غيرة أم سيطرة؟ خمس حدود لا ينبغي تجاوزها في العلاقة|comparison|relationships|غيرة|سيطرة
criticism-vs-emotional-abuse|نقد أم إساءة نفسية؟ عندما يصبح الكلام أداة لإضعافك|comparison|relationships|نقد|إساءة نفسية
care-vs-monitoring|اهتمام أم مراقبة؟ الهاتف والموقع وكلمات المرور ليست دليل حب|comparison|relationships|اهتمام|مراقبة
rest-vs-avoidance|راحة أم تجنب؟ كيف تعرف إن كانت الاستراحة تساعدك أم تعطل حياتك؟|comparison|general|راحة|تجنب
protection-vs-control|حماية أم تحكم؟ النية الطيبة لا تبرر سلب القرار|comparison|relationships|حماية|تحكم
tired-vs-burnout|تعب عابر أم احتراق نفسي؟ ثلاثة فروق تظهر بعد الراحة|comparison|work|تعب عابر|احتراق نفسي
deep-thinking-vs-rumination|تفكير عميق أم اجترار؟ السؤال الذي لا يقود إلى قرار يستهلكك|comparison|anxiety|تفكير عميق|اجترار
introversion-vs-harmful-isolation|انطواء أم عزلة مؤذية؟ الفرق هو الاختيار والأثر|comparison|general|انطواء|عزلة مؤذية
language-delay-vs-developmental-difference|تأخر لغوي أم اختلاف نمائي؟ لماذا لا تكفي المقارنة بأطفال آخرين؟|comparison|child|تأخر لغوي|اختلاف نمائي أوسع
activity-vs-adhd|حركة طبيعية أم اضطراب فرط الحركة؟ راقب أكثر من مكان وأكثر من موقف|comparison|adhd|حركة طبيعية|اضطراب فرط الحركة وتشتت الانتباه
habit-vs-addiction|عادة أم إدمان؟ فقدان السيطرة أهم من عدد المرات|comparison|addiction|عادة|إدمان
heavy-phone-use-vs-addiction|استخدام مرتفع للهاتف أم سلوك إدماني؟ راقب السيطرة والضرر|comparison|digital|استخدام مرتفع|سلوك إدماني
hunger-vs-emotional-eating|جوع أم أكل عاطفي؟ إشارات من التوقيت والسرعة والشبع|comparison|eating|جوع جسدي|أكل عاطفي
stress-vs-anxiety-disorder|توتر أم اضطراب قلق؟ متى يستمر الخوف بعد انتهاء السبب؟|comparison|anxiety|توتر|اضطراب قلق
fear-vs-phobia|خوف أم رهاب؟ عندما يصبح التجنب أكبر من الخطر نفسه|comparison|anxiety|خوف|رهاب
caution-vs-hypervigilance|حذر أم فرط يقظة؟ الجسم الذي يتصرف كأن الخطر لم ينتهِ|comparison|trauma|حذر|فرط يقظة
empathy-vs-people-pleasing|تعاطف أم إرضاء للناس؟ المساعدة التي تلغي نفسك ليست توازنًا|comparison|relationships|تعاطف|إرضاء للناس
space-vs-silent-treatment|مساحة شخصية أم عقاب صامت؟ الفرق في الوضوح والعودة للحوار|comparison|relationships|مساحة شخصية|عقاب صامت
honesty-vs-cruelty|صراحة أم قسوة؟ الحقيقة لا تحتاج إلى إذلال|comparison|relationships|صراحة|قسوة
apology-vs-manipulation|اعتذار أم تلاعب؟ خمس علامات تكشف الاعتذار الزائف|comparison|relationships|اعتذار|تلاعب
missing-vs-attachment|اشتياق أم تعلق؟ غياب الشخص لا يعني أن العودة آمنة|comparison|relationships|اشتياق|تعلق
breakup-grief-vs-depression|حزن الانفصال أم اكتئاب؟ راقب الزمن والوظيفة وفقدان المتعة|comparison|depression|حزن انفصال|اكتئاب
support-vs-rescuing|دعم أم إنقاذ؟ المساعدة التي تحمل مسؤولية الآخر قد تستنزفكما|comparison|relationships|دعم|إنقاذ
love-vs-dependency|حب أم اعتماد عاطفي؟ هل تستطيع أن تبقى أنت داخل العلاقة؟|comparison|relationships|حب|اعتماد عاطفي
boundaries-vs-walls|حدود أم جدار عاطفي؟ الحماية الصحية لا تمنع كل قرب|comparison|relationships|حدود|جدار عاطفي
forgiveness-vs-accepting-abuse|تسامح أم قبول للإساءة؟ يمكنك أن تتعافى دون العودة|comparison|relationships|تسامح|قبول إساءة
optimism-vs-denial|تفاؤل أم إنكار؟ الأمل الحقيقي يرى المشكلة ويعمل عليها|comparison|general|تفاؤل|إنكار
self-confidence-vs-arrogance|ثقة بالنفس أم غرور؟ الفرق يظهر في التعلم واحترام الآخرين|comparison|relationships|ثقة بالنفس|غرور
assertiveness-vs-aggression|حزم أم عدوانية؟ يمكنك حماية حقك دون تهديد|comparison|relationships|حزم|عدوانية
work-pressure-vs-burnout|ضغط عمل أم احتراق؟ متى لا تعود عطلة نهاية الأسبوع كافية؟|comparison|work|ضغط عمل|احتراق نفسي
sleepiness-vs-depression|نعاس أم اكتئاب؟ الطاقة المنخفضة لها أكثر من تفسير|comparison|depression|نعاس|اكتئاب
sleep-loss-vs-insomnia|قلة نوم أم أرق؟ الفرصة المتاحة للنوم تصنع الفرق|comparison|sleep|قلة نوم|أرق
distraction-vs-adhd|تشتت عابر أم اضطراب فرط الحركة؟ لا تشخّص نفسك من فيديو قصير|comparison|adhd|تشتت عابر|اضطراب فرط الحركة وتشتت الانتباه
perfectionism-vs-ocd|كمالية أم وسواس قهري؟ التشابه في التكرار لا يعني تشخيصًا واحدًا|comparison|ocd|كمالية|وسواس قهري
humility-vs-low-self-worth|تواضع أم تدنّي تقدير الذات؟ التقليل من نفسك ليس فضيلة|comparison|general|تواضع|تدنّي تقدير الذات
responsibility-vs-self-blame|مسؤولية أم لوم ذاتي؟ تحمل دورك لا يعني حمل كل الخطأ|comparison|general|مسؤولية|لوم ذاتي
independence-vs-avoidant-closeness|استقلال أم تجنب للقرب؟ القوة لا تعني رفض الاحتياج|comparison|relationships|استقلال|تجنب القرب
child-protection-vs-parental-anxiety|حماية الطفل أم قلق مفرط؟ الأمان لا يعني منع كل تجربة|comparison|child|حماية|قلق مفرط
tantrum-vs-sensory-meltdown|نوبة غضب أم انهيار حسي؟ الاستجابة الخاطئة قد تزيد الموقف|comparison|child|نوبة غضب|انهيار حسي
defiance-vs-regulation-difficulty|عناد أم صعوبة تنظيم؟ اسأل عمّا يعجز الطفل عن فعله الآن|comparison|child|عناد|صعوبة تنظيم
bad-behavior-vs-unmet-need|سلوك سيئ أم حاجة غير مُلباة؟ افهم الوظيفة قبل العقوبة|comparison|child|سلوك مزعج|حاجة غير ملباة
sensitivity-vs-sensory-overload|حساسية عاطفية أم فرط استجابة حسية؟ الصوت والضوء واللمس قد تكون عوامل حقيقية|comparison|child|حساسية عاطفية|فرط استجابة حسية
forgetfulness-vs-stress|نسيان أم ضغط نفسي؟ العقل المرهق لا يحتفظ بكل شيء|comparison|general|نسيان|ضغط نفسي
simple-mental-health-check|اختبار الصحة النفسية البسيط: 10 أسئلة تستحق التوقف|check|general||
do-you-have-insomnia|هل تعاني من الأرق؟ 8 إشارات تتجاوز ليلة سيئة|check|sleep||
are-you-in-toxic-relationship|هل أنت في علاقة سامة؟ 12 علامة لا ينبغي تطبيعها|check|relationships||
burnout-self-check|هل تعيش احتراقًا نفسيًا؟ اختبر أثر العمل بعد انتهاء الدوام|check|work||
anxiety-controls-day|هل القلق يسيطر على يومك؟ 9 أسئلة تكشف مساحة التجنب|check|anxiety||
loneliness-vs-isolation-check|هل تحولت وحدتك إلى عزلة؟ راقب الاختيار والأثر|check|general||
overthinking-check|هل تفرط في التفكير؟ سبع علامات أن التحليل تحول إلى اجترار|check|anxiety||
boundaries-check|هل تحتاج إلى حدود أوضح؟ 10 مواقف تجيبك|check|relationships||
people-pleasing-check|هل ترضي الجميع على حسابك؟ اختبار قصير بلا أحكام|check|relationships||
phone-drain-check|هل علاقتك بهاتفك تستنزفك؟ افحص النوم والتركيز والمزاج|check|digital||
sleep-affects-mood|هل نومك يضر مزاجك؟ 9 إشارات تربط الليل بالنهار|check|sleep||
emotional-eating-check|هل تأكل بسبب المشاعر؟ أسئلة تفرق بين الجوع والتهدئة|check|eating||
loss-of-pleasure-check|هل فقدت المتعة؟ علامة مهمة لا تعني الكسل|check|depression||
missing-person-or-idea|هل تشتاق لشخص أم لفكرة العلاقة؟ خمسة أسئلة صريحة|check|relationships||
fear-of-rejection-check|هل تخاف من الرفض أكثر مما ينبغي؟ راقب ما تتنازل عنه|check|relationships||
stuck-after-breakup|هل أنت عالق في علاقة انتهت؟ 8 علامات أن الحداد توقف عن الحركة|check|relationships||
guilt-manipulation-check|هل تتعرض للتلاعب بالذنب؟ هذه العبارات ليست مسؤولية صحية|check|relationships||
overworking-check|هل تعمل أكثر مما تستطيع؟ جسدك قد يدفع الفاتورة|check|work||
rest-or-help-check|هل تحتاج إلى استراحة أم مساعدة متخصصة؟ راقب ما لا يتحسن|check|general||
child-sleep-evaluation|هل يحتاج نوم طفلك إلى تقييم؟ مؤشرات تتجاوز مقاومة موعد النوم|check|child||
anger-hides-stress|هل غضبك يخفي ضغطًا؟ اختبر ما يحدث قبل الانفجار|check|general||
inner-critic-check|هل يقودك النقد الداخلي؟ 10 عبارات تكشف صوته|check|general||
social-avoidance-check|هل تتجنب الناس بسبب القلق؟ راقب ما تخسره مقابل الراحة المؤقتة|check|anxiety||
stress-body-check|هل الضغوط بدأت تؤثر على جسدك؟ علامات تستحق الانتباه|check|stress||
psychological-reasons-waking-tired|خمس أسباب نفسية قد تجعلك تستيقظ متعبًا رغم النوم|factors|sleep||
psychological-reasons-low-motivation|خمس أسباب نفسية وراء فقدان الدافعية لا علاقة لها بالكسل|factors|general||
why-think-about-ex|خمس أسباب تجعلك تفكر في شخص قديم حتى بعد انتهاء العلاقة|factors|relationships||
why-stay-harmful-relationship|خمس أسباب تجعل الشخص يبقى في علاقة مؤذية|factors|relationships||
fear-of-commitment-reasons|خمس أسباب وراء الخوف من الارتباط حتى مع وجود مشاعر|factors|relationships||
difficulty-saying-no|خمس أسباب تجعل قول «لا» صعبًا إلى هذا الحد|factors|relationships||
sensitive-to-criticism|خمس أسباب وراء الحساسية الشديدة للنقد|factors|general||
procrastination-reasons|خمس أسباب نفسية وراء التسويف قبل أن تسميه كسلًا|factors|general||
emotional-eating-reasons|خمس أسباب وراء الأكل العاطفي وكيف تكسر الحلقة بلطف|factors|eating||
quick-anger-reasons|خمس أسباب وراء الغضب السريع قد لا تكون واضحة|factors|stress||
excessive-attachment-reasons|خمس أسباب وراء التعلق الزائد بشخص واحد|factors|relationships||
emptiness-reasons|خمس أسباب وراء الشعور بالفراغ حتى عندما تبدو حياتك ممتلئة|factors|general||
comparison-with-others|خمس أسباب تجعلك تقارن نفسك بالآخرين بلا توقف|factors|digital||
fear-of-failure-reasons|خمس أسباب وراء الخوف من الفشل قبل أن تبدأ|factors|general||
guilt-after-rest|خمس أسباب تجعلك تشعر بالذنب عندما ترتاح|factors|work||
external-factors-mental-health|خمس عوامل خارجية تؤثر في صحتك النفسية أكثر مما تتوقع|factors|general||
work-burnout-factors|خمس عوامل في العمل ترفع خطر الاحتراق النفسي|factors|work||
night-habits-harm-sleep|خمس عادات ليلية تفسد النوم حتى لو دخلت السرير مبكرًا|factors|sleep||
body-signs-under-stress|خمس إشارات يرسلها الجسد عندما يتراكم الضغط|factors|stress||
anxiety-changes-decisions|خمس طرق يغيّر بها القلق قراراتك من دون أن تلاحظ|factors|anxiety||
breakup-harder-factors|خمس عوامل تجعل الانفصال أصعب من المتوقع|factors|relationships||
child-school-refusal-reasons|خمس أسباب قد تجعل الطفل يرفض المدرسة|factors|child||
attention-distraction-factors|خمس عوامل تزيد تشتت الانتباه حتى دون وجود اضطراب|factors|adhd||
sudden-withdrawal-reasons|خمس أسباب تجعل شخصًا ينسحب فجأة من الناس|factors|general||
tips-after-breakup|خمس نصائح بعد الانفصال تمنعك من تحويل الألم إلى أذى جديد|relationship|relationships||
stop-checking-ex-social|كيف تتوقف عن تفقد حساب شخص بعد الانفصال؟ خطة من سبع خطوات|relationship|digital||
why-miss-someone-who-hurt-you|لماذا تشتاق لمن أذاك؟ الذاكرة لا تعرض القصة كاملة|relationship|relationships||
when-getting-back-is-bad|متى يكون الرجوع بعد الانفصال فكرة سيئة؟ راقب السلوك لا الوعود|relationship|relationships||
boundaries-new-relationship|سبعة حدود تحميك في بداية العلاقة دون قتل العفوية|relationship|relationships||
real-apology-signs|كيف تعرف أن الاعتذار حقيقي؟ خمس علامات أهم من كلمة آسف|relationship|relationships||
why-they-disappear-and-return|لماذا يختفي شخص ثم يعود؟ لا تجعل الغموض يقرر قيمتك|relationship|relationships||
silent-treatment-abuse|العقاب الصامت: متى يتحول الانسحاب إلى إساءة نفسية؟|relationship|relationships||
jealousy-becomes-control|الغيرة في العلاقة: متى تتحول إلى سيطرة خطرة؟|relationship|relationships||
trust-after-betrayal|الحب بعد الخيانة: هل يمكن بناء الثقة من جديد؟|relationship|relationships||
end-relationship-safely|كيف تنهي علاقة باحترام وأمان؟ لا تستخدم الطريقة نفسها في كل علاقة|relationship|relationships||
partner-refuses-boundaries|ماذا تفعل عندما يرفض الطرف الآخر حدودك؟|relationship|relationships||
friendship-after-breakup|هل الصداقة بعد الانفصال ممكنة؟ خمسة شروط قبل المحاولة|relationship|relationships||
attracted-to-unavailable|لماذا ننجذب إلى شخص غير متاح عاطفيًا؟|relationship|relationships||
safe-relationship-signs|ثماني علامات لعلاقة آمنة نفسيًا لا تعتمد على المثالية|relationship|relationships||
relationship-drains-you|ست علامات أن العلاقة تستنزفك أكثر مما تدعمك|relationship|relationships||
critical-partner|كيف تتعامل مع شريك كثير النقد دون أن تفقد نفسك؟|relationship|relationships||
conflict-vs-abuse|كيف تفرق بين الخلاف الطبيعي والإساءة؟|relationship|relationships||
fear-loneliness-after-breakup|لماذا تخاف من الوحدة بعد الانفصال؟|relationship|relationships||
recover-self-after-long-relationship|كيف تستعيد نفسك بعد علاقة طويلة؟|relationship|relationships||
temporary-distance-relationship|متى يكون البعد المؤقت مفيدًا للعلاقة ومتى يصبح هروبًا؟|relationship|relationships||
stop-self-blame-after-betrayal|كيف تتوقف عن لوم نفسك بعد الخيانة؟|relationship|relationships||
anxious-attachment-relationship|هل التعلق القلق يفسد العلاقة؟ النمط قابل للفهم والتغيير|relationship|relationships||
express-needs-without-blame|كيف تتحدث عن احتياجاتك دون اتهام أو انفجار؟|relationship|relationships||
calm-mind-before-sleep|سبع خطوات لتهدئة العقل قبل النوم دون إجبار نفسك على النوم|practical|sleep||
five-minute-overthinking-reset|خمس دقائق لإيقاف دوامة التفكير والعودة إلى اللحظة|practical|anxiety||
small-mental-health-habits|عشر عادات صغيرة تحمي الصحة النفسية دون تغيير حياتك بالكامل|practical|general||
what-to-do-panic-attack|ماذا تفعل أثناء نوبة هلع؟ خطوات آمنة حتى تمر الموجة|practical|anxiety||
return-to-routine-after-hard-time|كيف تعود إلى روتينك بعد فترة صعبة دون خطة مثالية؟|practical|general||
say-no-without-guilt|طريقة بسيطة لقول «لا» دون شرح طويل أو شعور ساحق بالذنب|practical|relationships||
boundaries-with-family|كيف تضع حدودًا مع الأسرة عندما يعتبرونها رفضًا؟|practical|relationships||
support-depressed-person|كيف تدعم شخصًا مكتئبًا دون أن تتحول إلى معالج؟|practical|depression||
what-to-say-bereaved|ماذا تقول لشخص فقد عزيزًا؟ عبارات تساعد وأخرى تؤذي|practical|grief||
help-anxious-child|كيف تساعد طفلًا قلقًا دون تعزيز التجنب؟|practical|child||
low-motivation-day|كيف تتعامل مع يوم بلا دافعية؟ ابدأ بما يحافظ على اليوم|practical|general||
exam-stress|كيف تقلل التوتر قبل الامتحان دون وعود سحرية؟|practical|stress||
work-stress-plan|كيف تتعامل مع ضغط العمل قبل أن يتحول إلى احتراق؟|practical|work||
restore-sleep-after-bad-week|كيف تستعيد نومك بعد أسبوع مضطرب؟|practical|sleep||
personal-mental-safety-plan|كيف تكتب خطة أمان نفسي شخصية قبل الأزمة؟|practical|safety||
time-to-seek-help|كيف تعرف أن الوقت حان لطلب مساعدة نفسية؟|practical|general||
choose-therapist|كيف تختار معالجًا نفسيًا مناسبًا؟ سبعة أسئلة قبل البدء|practical|care||
prepare-first-therapy-session|كيف تستعد لأول جلسة علاج نفسي دون حفظ خطاب؟|practical|care||
explain-mental-health-to-family|كيف تشرح صحتك النفسية لأسرتك عندما لا يفهمونها؟|practical|relationships||
protect-child-from-bullying|كيف تحمي طفلك من التنمر دون تحميله المسؤولية؟|practical|child||
sensory-overload-plan|كيف تتعامل مع فرط التحفيز الحسي قبل الانهيار؟|practical|child||
support-addiction-recovery|كيف تدعم شخصًا في التعافي من الإدمان دون تمكين السلوك؟|practical|addiction||
suspected-relapse|كيف تتصرف عند الاشتباه بانتكاسة؟ الهدوء لا يعني تجاهل الخطر|practical|addiction||
reduce-phone-use|كيف تقلل استخدام الهاتف دون أن تعزل نفسك؟|practical|digital||
build-calmer-day|كيف تبني يومًا أكثر هدوءًا عندما لا تستطيع تغيير كل الظروف؟|practical|general||"""

FORMAT_LABELS = {
    "comparison": "مقارنة سريعة",
    "check": "فحص ذاتي تثقيفي",
    "factors": "خمس نقاط مفسرة",
    "relationship": "دليل علاقات عملي",
    "practical": "خطوات قابلة للتطبيق",
}

SOURCES = {
    "general": [
        ("منظمة الصحة العالمية: الصحة النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-health-strengthening-our-response"),
        ("المعهد الوطني للصحة النفسية: العناية بالصحة النفسية", "https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health"),
    ],
    "depression": [
        ("منظمة الصحة العالمية: الاكتئاب", "https://www.who.int/ar/news-room/fact-sheets/detail/depression"),
        ("المعهد الوطني للصحة النفسية: الاكتئاب", "https://www.nimh.nih.gov/health/topics/depression"),
    ],
    "anxiety": [
        ("المعهد الوطني للصحة النفسية: اضطرابات القلق", "https://www.nimh.nih.gov/health/topics/anxiety-disorders"),
        ("منظمة الصحة العالمية: التعامل مع الضغط النفسي", "https://www.who.int/publications/i/item/9789240003927"),
    ],
    "sleep": [
        ("مراكز مكافحة الأمراض والوقاية منها: النوم والصحة", "https://www.cdc.gov/sleep/about/index.html"),
        ("الخدمة الصحية الوطنية البريطانية: الأرق", "https://www.nhs.uk/conditions/insomnia/"),
    ],
    "relationships": [
        ("الجمعية الأمريكية لعلم النفس: العلاقات", "https://www.apa.org/topics/relationships"),
        ("منظمة الصحة العالمية: الصحة النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-health-strengthening-our-response"),
    ],
    "work": [
        ("منظمة الصحة العالمية: الاحتراق المهني", "https://www.who.int/news/item/28-05-2019-burn-out-an-occupational-phenomenon-international-classification-of-diseases"),
        ("الجمعية الأمريكية لعلم النفس: الضغط النفسي", "https://www.apa.org/topics/stress"),
    ],
    "child": [
        ("مراكز مكافحة الأمراض والوقاية منها: اضطراب فرط الحركة", "https://www.cdc.gov/adhd/about/index.html"),
        ("منظمة الصحة العالمية: اضطرابات طيف التوحد", "https://www.who.int/ar/news-room/fact-sheets/detail/autism-spectrum-disorders"),
    ],
    "adhd": [
        ("مراكز مكافحة الأمراض والوقاية منها: اضطراب فرط الحركة", "https://www.cdc.gov/adhd/about/index.html"),
        ("مراكز مكافحة الأمراض والوقاية منها: النوم", "https://www.cdc.gov/sleep/about/index.html"),
    ],
    "ocd": [
        ("المعهد الوطني للصحة النفسية: الوسواس القهري", "https://www.nimh.nih.gov/health/topics/obsessive-compulsive-disorder-ocd"),
        ("منظمة الصحة العالمية: الاضطرابات النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-disorders"),
    ],
    "bipolar": [
        ("المعهد الوطني للصحة النفسية: الاضطراب ثنائي القطب", "https://www.nimh.nih.gov/health/topics/bipolar-disorder"),
        ("منظمة الصحة العالمية: الاضطرابات النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-disorders"),
    ],
    "trauma": [
        ("المعهد الوطني للصحة النفسية: اضطراب ما بعد الصدمة", "https://www.nimh.nih.gov/health/topics/post-traumatic-stress-disorder-ptsd"),
        ("منظمة الصحة العالمية: التعامل مع الضغط النفسي", "https://www.who.int/publications/i/item/9789240003927"),
    ],
    "digital": [
        ("الجمعية الأمريكية لعلم النفس: وسائل التواصل واليافعون", "https://www.apa.org/topics/social-media-internet/health-advisory-adolescent-social-media-use"),
        ("مراكز مكافحة الأمراض والوقاية منها: النوم", "https://www.cdc.gov/sleep/about/index.html"),
    ],
    "eating": [
        ("المعهد الوطني للصحة النفسية: اضطرابات الأكل", "https://www.nimh.nih.gov/health/topics/eating-disorders"),
        ("منظمة الصحة العالمية: الرعاية الذاتية", "https://www.who.int/news-room/fact-sheets/detail/self-care-health-interventions"),
    ],
    "stress": [
        ("الجمعية الأمريكية لعلم النفس: الضغط النفسي", "https://www.apa.org/topics/stress"),
        ("منظمة الصحة العالمية: التعامل مع الضغط النفسي", "https://www.who.int/publications/i/item/9789240003927"),
    ],
    "addiction": [
        ("SAMHSA: التعرف إلى العلاج والتعافي", "https://www.samhsa.gov/find-support/learn-about-treatment"),
        ("منظمة الصحة العالمية: الكحول", "https://www.who.int/news-room/fact-sheets/detail/alcohol"),
    ],
    "grief": [
        ("الخدمة الصحية الوطنية البريطانية: الحزن والفقد", "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/grief-bereavement-loss/"),
        ("منظمة الصحة العالمية: الصحة النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-health-strengthening-our-response"),
    ],
    "care": [
        ("المعهد الوطني للصحة النفسية: العناية بالصحة النفسية", "https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health"),
        ("منظمة الصحة العالمية: الرعاية الذاتية", "https://www.who.int/news-room/fact-sheets/detail/self-care-health-interventions"),
    ],
    "safety": [
        ("المعهد الوطني للصحة النفسية: العناية بالصحة النفسية", "https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health"),
        ("منظمة الصحة العالمية: الصحة النفسية", "https://www.who.int/ar/news-room/fact-sheets/detail/mental-health-strengthening-our-response"),
    ],
}

GUIDES = {
    "general": {
        "label": "الصحة النفسية اليومية", "colors": ("#075f5b", "#dff5f1"),
        "signals": ["استمرار التغير بدل ظهوره في موقف واحد", "تأثر النوم أو الطاقة أو التركيز", "تعطل الدراسة أو العمل أو العناية بالنفس", "الانسحاب من الناس والأنشطة المهمة", "ارتفاع الضيق أو ظهور خطر على السلامة"],
        "actions": ["دوّن ما يحدث ووقت ظهوره وما سبقه", "ابدأ بخطوة صغيرة تحمي النوم والطعام والحركة", "تجنب وصف المشكلة بكسل أو ضعف قبل فهمها", "اطلب مساعدة عملية من شخص موثوق", "اطلب تقييمًا مهنيًا عند الاستمرار أو التعطيل"],
        "factors": ["ضغط يفوق فرص التعافي", "نوم غير كاف أو غير منتظم", "توقعات قاسية أو كمالية", "عزلة أو نقص دعم عملي", "سبب صحي أو دوائي يحتاج استبعادًا"],
    },
    "depression": {
        "label": "المزاج والاكتئاب", "colors": ("#374785", "#e7eafa"),
        "signals": ["مزاج منخفض أو تهيج معظم اليوم", "فقدان المتعة أو الاهتمام", "تغير الطاقة أو النوم أو الشهية", "صعوبة التركيز واليأس أو الذنب", "أفكار الموت أو إيذاء النفس تستلزم مساعدة عاجلة"],
        "actions": ["راقب المدة والأثر", "حافظ على أساسيات اليوم بأهداف صغيرة", "لا تعزل نفسك تمامًا", "راجع طبيبًا عند وجود أعراض جسدية أو دوائية", "اطلب دعمًا متخصصًا عند الاستمرار أو الخطر"],
        "factors": ["ضغط أو فقد أو تغير حياتي", "نقص النوم والتعافي", "عزلة وتراجع الأنشطة المجزية", "أمراض جسدية أو أدوية أو مواد", "عوامل بيولوجية ونفسية واجتماعية متداخلة"],
    },
    "anxiety": {
        "label": "القلق والخوف", "colors": ("#7a2e55", "#fae7f0"),
        "signals": ["توقع خطر متكرر يصعب إيقافه", "توتر جسدي أو خفقان أو اضطراب معدة", "تجنب أماكن أو أشخاص أو مهام", "طلب طمأنة متكرر", "تأثر النوم والتركيز والقرارات"],
        "actions": ["سم القلق ولا تعامل كل فكرة كحقيقة", "خفف التجنب تدريجيًا عندما يكون الموقف آمنًا", "استخدم تثبيت الحواس وتنفسًا طبيعيًا بطيئًا", "قلل الكافيين ونظم النوم", "اطلب تقييمًا عند تعطيل الحياة"],
        "factors": ["عدم اليقين والمبالغة في تقدير الخطر", "التجنب الذي يريح مؤقتًا", "قلة النوم والمنبهات", "ضغط أو تجربة مخيفة", "عوامل بيولوجية واجتماعية"],
    },
    "sleep": {
        "label": "النوم والأرق", "colors": ("#182848", "#dce7ff"),
        "signals": ["صعوبة بدء النوم أو استمراره", "وجود فرصة كافية للنوم مع بقاء الصعوبة", "نعاس أو تهيج أو ضعف تركيز نهارًا", "قلق متزايد حول النوم", "شخير شديد أو توقف تنفس يحتاج تقييمًا"],
        "actions": ["ثبت وقت الاستيقاظ", "استخدم ضوء الصباح وخفف الضوء ليلًا", "اجعل السرير للنوم لا للعمل", "خفف الكافيين المتأخر والقيلولة الطويلة", "اطلب تقييمًا عند الاستمرار أو صعوبة التنفس"],
        "factors": ["روتين متقلب", "قلق واجترار قبل النوم", "منبهات أو شاشات متأخرة", "بيئة نوم مزعجة", "سبب صحي أو دوائي أو اضطراب نوم"],
    },
    "relationships": {
        "label": "العلاقات والحدود", "colors": ("#87345d", "#ffe6ef"),
        "signals": ["الخوف من التعبير أو الرفض أو العقاب", "انتهاك الخصوصية والحدود", "العزل أو التحكم بالمال والحركة", "غياب المساءلة والإصلاح", "فقدان الهوية أو الأمان داخل العلاقة"],
        "actions": ["صف السلوك المحدد وأثره", "ضع حدًا واضحًا وعاقبة قابلة للتنفيذ", "احتفظ بشبكة دعم مستقلة", "راقب التغيير السلوكي لا الوعود", "عند التهديد أو العنف قدم السلامة"],
        "factors": ["خوف من الرفض أو الوحدة", "حدود غير واضحة أو غير محترمة", "تعزيز متقطع بين القرب والأذى", "عزلة أو اعتماد مالي واجتماعي", "تجارب سابقة تشكل التوقعات"],
    },
    "work": {
        "label": "ضغط العمل والاحتراق", "colors": ("#6b4f2a", "#f7ead8"),
        "signals": ["استنزاف لا يتحسن بعد الراحة القصيرة", "تبلد أو سخرية تجاه العمل", "انخفاض الإحساس بالفاعلية", "امتداد العمل إلى النوم والعلاقات", "شعور بانعدام السيطرة أو العدالة"],
        "actions": ["حدد المطالب التي يمكن تقليلها أو ترتيبها", "اتفق على أولويات واقعية", "احم فترات التعافي وحدود نهاية الدوام", "وثق عبء العمل وناقشه", "اطلب دعمًا صحيًا عند استمرار الأعراض"],
        "factors": ["عبء عمل مزمن", "ضعف السيطرة", "غموض الدور", "انعدام العدالة أو التقدير", "نقص الدعم والتعافي"],
    },
    "child": {
        "label": "الطفل والنمو", "colors": ("#0b7285", "#def5f8"),
        "signals": ["ظهور النمط في أكثر من بيئة", "تأثيره في التعلم أو التواصل أو النوم", "تغير مفاجئ أو فقد مهارة", "مثيرات حسية أو انتقالات صعبة", "حاجة إلى تقييم متعدد المصادر"],
        "actions": ["صف السلوك وما يسبقه ويتبعه", "عدل البيئة والمطلب قبل افتراض سوء النية", "علم مهارة بديلة بخطوات صغيرة", "نسق بين الأسرة والمدرسة", "اطلب تقييمًا عند الاستمرار أو فقد المهارات"],
        "factors": ["مرحلة النمو والمهارات المتاحة", "النوم والجوع والألم", "صعوبة حسية أو تواصلية", "قلق أو تنمر أو ضغط مدرسي", "مطلب غير مناسب للقدرة الحالية"],
    },
    "adhd": {
        "label": "الانتباه والتنظيم", "colors": ("#c06c24", "#fff0dc"),
        "signals": ["صعوبة مستمرة في الانتباه أو التنظيم", "ظهور الأثر في أكثر من بيئة", "تاريخ يمتد إلى الطفولة", "تأثر الدراسة أو العمل أو العلاقات", "ضرورة استبعاد النوم والقلق وأسباب أخرى"],
        "actions": ["قلل المشتتات واجعل الخطوة التالية مرئية", "قسم المهمة واستخدم تذكيرات خارجية", "نظم النوم والحركة", "اجمع ملاحظات من أكثر من سياق", "اطلب تقييمًا متخصصًا"],
        "factors": ["قلة النوم", "ضغط أو قلق أو مزاج منخفض", "مشتتات رقمية وبيئية", "مهام غامضة أو طويلة", "اختلافات عصبية تحتاج تقييمًا"],
    },
    "ocd": {
        "label": "الوسواس القهري", "colors": ("#5f3dc4", "#eee8ff"),
        "signals": ["أفكار أو صور ملحة ومتكررة", "أفعال أو طقوس لتخفيف القلق", "استهلاك وقت أو ضيق شديد", "صعوبة مقاومة الطقس", "تأثر الدراسة أو العمل أو العلاقات"],
        "actions": ["لا تقدم طمأنة بلا نهاية", "سجل الوسواس والطقس والأثر", "تجنب السخرية أو الإجبار العنيف", "اطلب مختصًا يعرف علاج الوسواس", "اطلب مساعدة عاجلة عند الخطر"],
        "factors": ["عدم يقين مرتفع", "طقوس تخفف الضيق مؤقتًا", "تجنب يوسع الحلقة", "ضغط يزيد الأعراض", "عوامل بيولوجية ونفسية"],
    },
    "bipolar": {
        "label": "المزاج ثنائي القطب", "colors": ("#3b5b92", "#e5edff"),
        "signals": ["فترات واضحة من ارتفاع أو تهيج المزاج والطاقة", "انخفاض الحاجة إلى النوم", "تسارع الكلام أو اندفاع غير معتاد", "فترات اكتئاب أو فقد متعة", "تغير يراه الآخرون ويؤثر في الأمان"],
        "actions": ["لا تستخدم المصطلح لوصف التقلب اليومي", "سجل النوم والطاقة والسلوك والمدة", "راجع الأدوية والمواد مع طبيب", "اطلب تقييمًا متخصصًا", "اطلب مساعدة عاجلة عند اندفاع خطير أو ذهان"],
        "factors": ["نمط مزاج وطاقة غير معتاد", "اضطراب النوم", "أدوية أو مواد", "ضغط قد يسبق النوبات", "استعداد بيولوجي"],
    },
    "trauma": {
        "label": "الصدمة وفرط اليقظة", "colors": ("#4c6a58", "#e2f1e8"),
        "signals": ["إحساس مستمر بأن الخطر قريب", "تجنب تذكيرات أو أماكن", "كوابيس أو ذكريات اقتحامية", "سهولة الفزع وصعوبة النوم", "تأثر العلاقات والعمل"],
        "actions": ["ابدأ بالأمان والاستقرار", "استخدم تثبيت الحواس والروتين", "قلل المحفزات دون عزلة كاملة", "اطلب مختصًا مدربًا على الصدمة", "عند خطر حالي اطلب حماية محلية"],
        "factors": ["تجربة تهديد أو فقد", "استمرار الخطر", "نقص الدعم", "تجارب سابقة متراكمة", "نوم مضطرب وضغط"],
    },
    "digital": {
        "label": "الهاتف والحياة الرقمية", "colors": ("#244a7c", "#dfebfb"),
        "signals": ["فقدان السيطرة على وقت الاستخدام", "تأثر النوم أو الدراسة أو العمل", "مزاج أسوأ بعد الاستخدام", "تفقد قهري", "تراجع الاتصال الواقعي أو الحركة"],
        "actions": ["حدد وظيفة الاستخدام", "أزل الإشعارات غير الضرورية", "ضع الهاتف خارج السرير", "استبدل الاستخدام بنشاط يؤدي الوظيفة نفسها", "اطلب دعمًا عند الضرر المستمر"],
        "factors": ["تنبيهات ومكافآت متغيرة", "ملل أو وحدة أو قلق", "حدود غير واضحة بين العمل والراحة", "استخدام ليلي", "مقارنة اجتماعية"],
    },
    "eating": {
        "label": "الأكل والمشاعر", "colors": ("#9c5c2e", "#fff0df"),
        "signals": ["رغبة مفاجئة مرتبطة بشعور", "أكل سريع أو دون انتباه", "صعوبة التوقف رغم الشبع", "ذنب أو سرية أو تعويض", "تأثر الصحة أو الحياة"],
        "actions": ["انتبه للجوع والوقت والشعور دون وصم", "نظم الوجبات وتجنب الحرمان", "ابن بدائل تهدئة", "ابتعد عن الحميات العقابية", "اطلب تقييمًا عند فقدان السيطرة أو التعويض"],
        "factors": ["ضغط أو حزن أو ملل", "حرمان غذائي", "عادات مرتبطة بالشاشة", "نقص بدائل التنظيم", "اضطراب أكل يحتاج تقييمًا"],
    },
    "stress": {
        "label": "الضغط والجسد", "colors": ("#8a3b12", "#fde9dc"),
        "signals": ["تغير النوم أو الشهية أو الطاقة", "شد عضلي أو صداع أو اضطراب هضم", "تهيج أو صعوبة تركيز", "مطالب أكبر من الموارد", "أعراض جديدة أو شديدة تحتاج تقييمًا طبيًا"],
        "actions": ["حدد مصدر الضغط", "قسم المشكلة إلى خطوة واحدة", "استخدم حركة خفيفة وفترات توقف", "اطلب دعمًا في المسؤوليات", "راجع مختصًا عند الاستمرار أو الأعراض المقلقة"],
        "factors": ["مطالب كثيرة أو غامضة", "قلة النوم", "نقص السيطرة أو الدعم", "صراع أو عدم أمان", "حالة صحية أو دواء"],
    },
    "addiction": {
        "label": "الإدمان والتعافي", "colors": ("#5a4633", "#efe5d9"),
        "signals": ["صعوبة التحكم أو التوقف", "الاستمرار رغم الضرر", "تضييق الحياة حول الاستخدام", "تحمل أو انسحاب في بعض الحالات", "خطر جرعة زائدة أو قيادة يحتاج طوارئ"],
        "actions": ["قدم السلامة وتجنب المواجهة أثناء التسمم", "شجع علاجًا قائمًا على الدليل", "ضع حدودًا دون إهانة", "احتفظ بخطة طوارئ ودعم للأسرة", "عند بطء التنفس أو فقد الوعي اطلب الطوارئ"],
        "factors": ["تخفيف سريع للضيق", "توفر المادة أو السلوك", "ضغط أو صدمة", "عزلة ونقص بدائل الدعم", "عوامل بيولوجية واجتماعية"],
    },
    "grief": {
        "label": "الفقد والحزن", "colors": ("#536271", "#e8edf1"),
        "signals": ["موجات حزن واشتياق", "اختلاف كبير بين الأشخاص", "تأثر النوم والتركيز", "حاجة إلى دعم عملي", "خطر على النفس أو عجز مستمر"],
        "actions": ["اعترف بالخسارة", "اعرض مساعدة محددة", "احترم الصمت والاختلاف", "حافظ على اتصال دون فرض الحديث", "شجع الدعم عند الضيق الشديد"],
        "factors": ["طبيعة العلاقة والخسارة", "مفاجأة الحدث", "الدعم المتاح", "خسائر متزامنة", "تاريخ صحي ونفسي"],
    },
    "care": {
        "label": "طلب الرعاية النفسية", "colors": ("#116466", "#dff3f0"),
        "signals": ["ضيق يستمر أو يزداد", "تعطل الوظيفة أو العلاقات", "عدم كفاية الدعم المعتاد", "أعراض جسدية أو دوائية", "خطر على النفس أو الآخرين"],
        "actions": ["حدد هدفًا أوليًا للرعاية", "تحقق من الترخيص والخبرة", "اسأل عن المنهج والتكلفة والخصوصية", "دون الأعراض والأدوية", "غير مقدم الخدمة إذا غاب الأمان"],
        "factors": ["استمرار الأعراض", "تعطل الحياة", "تفاقم الخطر", "حاجة إلى تشخيص تفريقي", "رغبة في دعم منظم"],
    },
    "safety": {
        "label": "الأمان النفسي", "colors": ("#8b1e3f", "#ffe3eb"),
        "signals": ["أفكار أو خطط لإيذاء النفس أو الآخرين", "فقدان السيطرة أو الاتصال بالواقع", "عنف أو تهديد أو قيادة تحت التأثير", "عجز عن حماية شخص يعتمد عليك", "تدهور سريع أو أعراض جسدية طارئة"],
        "actions": ["اتصل بالطوارئ المحلية عند الخطر الوشيك", "لا تترك الشخص وحده إذا كان ذلك آمنًا", "أبعد الوسائل الخطرة عند الإمكان", "استعن بشخص موثوق وخدمة صحية", "اكتب خطة أمان مسبقة"],
        "factors": ["تاريخ أزمات", "عزلة أو فقد حديث", "استخدام مواد أو اندفاع", "وصول إلى وسائل خطرة", "غياب خطة دعم"],
    },
}

CSS = """
:root{--ink:#163f43;--muted:#567176;--brand:#075f5b;--accent:#87345d;--surface:#fff;--mist:#eef9f7;--line:#cce2df;--shadow:0 18px 55px rgba(16,72,73,.12);--radius:24px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(145deg,#fff 0,#f1fbfa 55%,#f7f2fa 100%);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.85}
a{color:#066d67;text-underline-offset:4px}a:hover{color:#7d2f57}a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #0b8d84;outline-offset:3px}
.wrap{width:min(1160px,92%);margin-inline:auto}.skip{position:absolute;inset-inline-start:-9999px;top:8px;background:#fff;padding:10px 15px;border:2px solid var(--brand);border-radius:12px;z-index:100}.skip:focus{inset-inline-start:8px}
.site-header{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.head{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:10px 0}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:900;color:var(--ink)}.brand img{width:48px;height:48px}.nav{display:flex;flex-wrap:wrap;gap:6px}.nav a{padding:8px 10px;border-radius:10px;text-decoration:none;font-weight:800}.nav a:hover{background:var(--mist)}
.hero{padding:52px 0 28px}.crumbs{font-size:.94rem;color:var(--muted)}.eyebrow{color:var(--accent);font-weight:900;margin:0}h1{font-size:clamp(2rem,6vw,4.3rem);line-height:1.15;margin:.2em 0}.lead{font-size:clamp(1.06rem,2vw,1.28rem);color:var(--muted);max-width:900px}.meta{display:flex;flex-wrap:wrap;gap:9px;margin:18px 0}.pill{display:inline-flex;padding:6px 11px;border:1px solid var(--line);border-radius:999px;background:#fff;font-weight:800;font-size:.92rem}
.cover{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:28px;border:1px solid var(--line);box-shadow:var(--shadow);background:#dfeeea}.notice{padding:18px 20px;border-radius:18px;background:#fff4f7;border-inline-start:5px solid var(--accent);margin:20px 0}.notice strong{display:block;margin-bottom:4px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:26px;align-items:start}.article,.side-card,.card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}.article{padding:clamp(20px,4vw,38px)}.article h2{font-size:clamp(1.45rem,3vw,2.15rem);line-height:1.35;margin-top:1.6em}.article h3{font-size:1.2rem;margin-top:1.25em}.article li{margin:.6rem 0}.article p{max-width:78ch}.side{position:sticky;top:90px;display:grid;gap:14px}.side-card{padding:18px}.side-card h2{font-size:1.15rem;margin:.1em 0 .5em}.compare{width:100%;border-collapse:collapse;margin:18px 0}.compare th,.compare td{padding:13px;border:1px solid var(--line);vertical-align:top}.compare th{background:#e5f5f2;text-align:start}.compare tr:nth-child(even) td{background:#fafdfd}
.steps{counter-reset:step;display:grid;gap:12px;padding:0;list-style:none}.steps li{counter-increment:step;padding:15px 54px 15px 15px;position:relative;border:1px solid var(--line);border-radius:15px;background:#fbfefd}.steps li::before{content:counter(step);position:absolute;right:13px;top:13px;width:30px;height:30px;display:grid;place-items:center;border-radius:10px;background:var(--brand);color:#fff;font-weight:900}
.related{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0 44px}.related a{display:block;text-decoration:none;color:var(--ink);padding:16px;border:1px solid var(--line);border-radius:16px;background:#fff;font-weight:800}.controls{display:grid;grid-template-columns:1fr 260px;gap:12px;margin:20px 0}.controls input,.controls select{width:100%;min-height:50px;border:1px solid var(--line);border-radius:14px;padding:10px 14px;background:#fff;font:inherit}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0 50px}.card{overflow:hidden;display:flex;flex-direction:column}.card img{width:100%;aspect-ratio:16/9;object-fit:cover}.card-body{padding:17px;display:flex;flex-direction:column;flex:1}.card h2{font-size:1.18rem;line-height:1.45;margin:.25rem 0}.card p{color:var(--muted)}.card a{margin-top:auto;font-weight:900}.count{font-weight:900;color:var(--accent)}
footer{border-top:1px solid var(--line);padding:30px 0 50px;color:var(--muted);background:rgba(255,255,255,.7)}.footer-links{display:flex;flex-wrap:wrap;gap:12px}
@media(max-width:920px){.layout{grid-template-columns:1fr}.side{position:static;grid-template-columns:repeat(2,1fr)}.cards,.related{grid-template-columns:repeat(2,1fr)}}@media(max-width:640px){.head{align-items:flex-start;flex-direction:column}.controls{grid-template-columns:1fr}.cards,.related,.side{grid-template-columns:1fr}h1{font-size:2.25rem}.article{padding:20px}}
"""

def parse_topics():
    items = []
    for line in TOPIC_DATA.strip().splitlines():
        slug, title, fmt, domain, left, right = line.split("|")
        items.append({"slug": slug, "title": title, "format": fmt, "domain": domain, "left": left, "right": right})
    return items

TOPICS = parse_topics()

def e(v):
    return html.escape(str(v), quote=True)

def guide(topic):
    return GUIDES.get(topic["domain"], GUIDES["general"])

def summary(topic):
    label = guide(topic)["label"]
    if topic["format"] == "comparison":
        return f"مقارنة تثقيفية بين {topic['left']} و{topic['right']} تركز على السياق والاستمرار والأثر في الحياة، دون تشخيص ذاتي."
    if topic["format"] == "check":
        return f"فحص ذاتي تثقيفي يساعدك على ملاحظة ما يرتبط بـ{label} وتنظيم الأسئلة التي قد تناقشها مع مختص."
    if topic["format"] == "factors":
        return f"شرح خمسة عوامل محتملة مرتبطة بـ{label}، مع خطوات عملية وحدود واضحة لما يمكن استنتاجه من الأعراض."
    if topic["format"] == "relationship":
        return "دليل عملي لفهم النمط وحماية الحدود والأمان واتخاذ خطوة قابلة للتنفيذ دون لوم أو وعود مبالغ فيها."
    return f"خطة عملية مرتبطة بـ{label} تبدأ بخطوات صغيرة وتوضح متى لا تكفي النصائح العامة."

def url(topic):
    return f"{SITE}/{SECTION}/{topic['slug']}/"

def img_url(topic):
    return f"{SITE}/assets/quick-info/cards/{topic['slug']}.png"

def related(topic):
    same = [x for x in TOPICS if x["slug"] != topic["slug"] and x["domain"] == topic["domain"]]
    other = [x for x in TOPICS if x["slug"] != topic["slug"] and x["domain"] != topic["domain"]]
    rng = random.Random(int(hashlib.sha256(topic["slug"].encode()).hexdigest()[:12], 16))
    rng.shuffle(same); rng.shuffle(other)
    return (same + other)[:6]

def header():
    return """<a class="skip" href="#content">تجاوز إلى المحتوى</a><header class="site-header"><div class="wrap head"><a class="brand" href="/"><img src="/assets/brand/logo-mark.svg" alt="" width="48" height="48"><span>منصة الصحة النفسية</span></a><nav class="nav" aria-label="التنقل الرئيسي"><a href="/">الرئيسية</a><a href="/quick-info/">معلومات سريعة</a><a href="/encyclopedia/">الموسوعة</a><a href="/family-guide/">دليل الأسرة</a><a href="/trust/">منهجية الثقة</a></nav></div></header>"""

def footer():
    return """<footer><div class="wrap"><strong>محتوى تثقيفي لا يستبدل التقييم أو العلاج الفردي.</strong><p>عند خطر وشيك أو صعوبة تنفس أو ألم صدر جديد وشديد أو أفكار إيذاء النفس، تواصل مع خدمات الطوارئ المحلية فورًا.</p><div class="footer-links"><a href="/trust/">منهجية الثقة</a><a href="/contact/">تواصل معنا</a><a href="/copyright/">حقوق الاستخدام</a></div></div></footer>"""

def schema(topic):
    src = SOURCES.get(topic["domain"], SOURCES["general"])
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": ["Article", "MedicalWebPage"],
                "@id": url(topic) + "#article",
                "headline": topic["title"], "description": summary(topic), "url": url(topic),
                "mainEntityOfPage": url(topic), "image": [img_url(topic)],
                "datePublished": PUBLISHED, "dateModified": PUBLISHED, "inLanguage": "ar",
                "author": {"@type": "Organization", "name": AUTHOR, "url": SITE + "/trust/"},
                "publisher": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة", "url": SITE + "/", "logo": {"@type": "ImageObject", "url": SITE + "/assets/brand/logo-mark.svg"}},
                "citation": [x[1] for x in src],
            },
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "معلومات سريعة", "item": SITE + "/quick-info/"},
                {"@type": "ListItem", "position": 3, "name": topic["title"], "item": url(topic)},
            ]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": "هل تكفي هذه الصفحة للتشخيص؟", "acceptedAnswer": {"@type": "Answer", "text": "لا. الصفحة للتثقيف وتنظيم الملاحظات فقط، والتشخيص يحتاج تقييمًا مهنيًا وسياقًا كاملًا."}},
                {"@type": "Question", "name": "ما أهم شيء أراقبه؟", "acceptedAnswer": {"@type": "Answer", "text": "راقب الاستمرار والشدة والأثر في النوم والعمل أو الدراسة والعلاقات والعناية بالنفس."}},
                {"@type": "Question", "name": "متى أطلب مساعدة؟", "acceptedAnswer": {"@type": "Answer", "text": "عند استمرار الضيق أو تعطيله للحياة أو وجود خطر على السلامة، اطلب تقييمًا أو طوارئ محلية بحسب الحالة."}},
            ]},
        ],
    }
    return json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def body(topic):
    g = guide(topic)
    signals = "".join(f"<li>{e(x)}</li>" for x in g["signals"])
    actions = "".join(f"<li>{e(x)}</li>" for x in g["actions"])
    if topic["format"] == "comparison":
        rows = [
            ("السياق", f"قد يظهر {e(topic['left'])} في سياق واضح أو كاستجابة مفهومة.", f"يستحق {e(topic['right'])} الانتباه عندما يتكرر أو يحمل ضررًا أو خطرًا."),
            ("المرونة", "يميل إلى التغير مع الراحة أو الدعم أو تغير الظروف.", "قد يكون أقل مرونة ويستمر رغم محاولات التكيف المعتادة."),
            ("الأثر", "وجوده وحده لا يعني تعطل الحياة.", "يصبح مهمًا عندما يؤثر في النوم أو العمل أو الدراسة أو العلاقات."),
            ("ما لا يكفي", "موقف واحد أو عنوان قصير لا يثبت شيئًا.", "عرض واحد لا يكفي للتشخيص أو استبعاد أسباب أخرى."),
            ("الخطوة", "راقب النمط ودوّن السياق والمدة.", "اطلب تقييمًا عند الاستمرار أو التعطيل أو الخطر."),
        ]
        trs = "".join(f"<tr><th>{a}</th><td>{b}</td><td>{c}</td></tr>" for a,b,c in rows)
        return f"<h2>الفرق المختصر</h2><p>{e(summary(topic))}</p><div class='notice'><strong>لا تحول المقارنة إلى تشخيص ثنائي.</strong> قد يجتمع أكثر من عامل، وقد تفسر حالة جسدية أو دواء أو ضغط مؤقت بعض الأعراض.</div><table class='compare'><thead><tr><th>المعيار</th><th>{e(topic['left'])}</th><th>{e(topic['right'])}</th></tr></thead><tbody>{trs}</tbody></table><h2>ما الذي تراقبه؟</h2><ul>{signals}</ul><h2>ماذا تفعل الآن؟</h2><ol class='steps'>{actions}</ol>"
    if topic["format"] == "check":
        qs = [
            "هل استمر التغير أكثر من موقف عابر؟", "هل أثر في النوم أو الطاقة أو التركيز؟",
            "هل دفعك إلى تجنب أشخاص أو مهام مهمة؟", "هل أصبحت تحتاج إلى طمأنة متكررة؟",
            "هل لاحظ شخص موثوق تغيرًا واضحًا؟", "هل أثر في الدراسة أو العمل أو العناية بالنفس؟",
            "هل لم تعد الراحة المعتادة كافية؟", "هل تستخدم سلوكًا ما للهروب بصورة متكررة؟",
            "هل تشعر بفقدان سيطرة أو يأس؟", "هل توجد أفكار إيذاء النفس أو خطر فوري؟",
        ]
        lis = "".join(f"<li>{e(x)}</li>" for x in qs)
        return f"<h2>قبل أن تبدأ</h2><p>{e(summary(topic))}</p><div class='notice'><strong>هذا فحص للتفكير وليس مقياسًا تشخيصيًا.</strong> لا تجمع النقاط لتمنح نفسك تشخيصًا.</div><h2>الأسئلة العشرة</h2><ol class='steps'>{lis}</ol><h2>كيف تقرأ إجاباتك؟</h2><p>إجابة واحدة لا تكفي. تصبح المتابعة أهم عندما تتكرر عدة مؤشرات أو تستمر أو تؤثر في الوظيفة اليومية.</p><h2>خطوات تالية</h2><ol class='steps'>{actions}</ol>"
    if topic["format"] == "factors":
        sections = "".join(f"<section><h3>{i}. {e(x)}</h3><p>قد يساهم هذا العامل، لكنه لا يعمل بالطريقة نفسها لدى الجميع ولا يثبت أنه السبب الوحيد. راقب توقيته وتكراره وأثره.</p></section>" for i,x in enumerate(g["factors"],1))
        return f"<h2>لماذا يستحق الموضوع نظرة أعمق؟</h2><p>{e(summary(topic))}</p><div class='notice'><strong>الأسباب النفسية لا تلغي الأسباب الجسدية والاجتماعية.</strong> عند تغير مفاجئ أو أعراض شديدة ابدأ بتقييم صحي مناسب.</div><h2>العوامل الخمسة</h2>{sections}<h2>الخطوة الأكثر فائدة</h2><ol class='steps'>{actions}</ol>"
    if topic["format"] == "relationship":
        avoid = ["لا تتخذ قرارًا تحت تهديد أو ضغط زمني", "لا تعتبر الاشتياق أو الذنب دليلًا على الأمان", "لا تعزل نفسك عن الأشخاص الموثوقين", "لا تدخل مواجهة منفردة عند وجود تهديد", "لا تنتظر اعتذارًا مثاليًا كي تحمي نفسك"]
        return f"<h2>الخلاصة</h2><p>{e(summary(topic))}</p><h2>علامات لا تتجاهلها</h2><ul>{signals}</ul><h2>خطة عملية</h2><ol class='steps'>{actions}</ol><h2>ما الذي يفاقم المشكلة؟</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in avoid)}</ul><div class='notice'><strong>السلامة قبل إصلاح العلاقة.</strong> عند وجود عنف أو تهديد أو مراقبة قسرية اطلب دعمًا محليًا وخطة أمان.</div>"
    return f"<h2>لماذا تفيد هذه الخطة؟</h2><p>{e(summary(topic))}</p><div class='notice'><strong>ابدأ صغيرًا وقس الأثر.</strong> الهدف هو زيادة القدرة على الخطوة التالية، لا حل كل شيء فورًا.</div><h2>الخطوات</h2><ol class='steps'>{actions}<li>حدد أصغر خطوة قابلة للتنفيذ اليوم</li><li>راجع النتيجة وعدل الخطة بدل جلد الذات</li></ol><h2>متى لا تكفي الخطة الذاتية؟</h2><p>عندما يستمر الضيق أو يتفاقم أو يعطل الحياة أو يظهر خطر على السلامة.</p>"

def article(topic):
    g = guide(topic)
    src = SOURCES.get(topic["domain"], SOURCES["general"])
    source_html = "".join(f'<li><a href="{e(u)}" rel="noopener noreferrer">{e(t)}</a></li>' for t,u in src)
    rel = "".join(f'<a href="/quick-info/{e(x["slug"])}/">{e(x["title"])}</a>' for x in related(topic))
    desc = (summary(topic) + " شرح عربي موثوق وخطوات عملية.")[:210]
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{e(topic["title"])} | معلومات سريعة</title><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><meta name="googlebot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><link rel="canonical" href="{url(topic)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:url" content="{url(topic)}"><meta property="og:title" content="{e(topic["title"])}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="{img_url(topic)}"><meta property="og:image:width" content="1280"><meta property="og:image:height" content="720"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{img_url(topic)}"><link rel="stylesheet" href="/assets/quick-info/quick-info.css?v=1.0.0"><script type="application/ld+json">{schema(topic)}</script></head><body>{header()}<main id="content"><section class="hero wrap"><div class="crumbs"><a href="/">الرئيسية</a> ← <a href="/quick-info/">معلومات سريعة</a> ← {e(g["label"])}</div><p class="eyebrow">{e(FORMAT_LABELS[topic["format"]])}</p><h1>{e(topic["title"])}</h1><p class="lead">{e(summary(topic))}</p><div class="meta"><span class="pill">{e(g["label"])}</span><span class="pill">نشر: 4 أغسطس 2026</span><a class="pill" href="/trust/">منهجية التحرير</a></div><img class="cover" src="/assets/quick-info/cards/{e(topic["slug"])}.png" width="1280" height="720" alt="رسم توضيحي مجرد مرتبط بموضوع الصفحة"></section><div class="wrap layout"><article class="article">{body(topic)}<h2>متى تطلب مساعدة عاجلة؟</h2><p>اطلب خدمات الطوارئ المحلية فورًا عند خطر وشيك أو أفكار لإيذاء النفس أو الآخرين أو فقدان وعي أو صعوبة تنفس أو ألم صدر جديد وشديد أو عنف مباشر.</p><h2>المصادر المحورية</h2><ol>{source_html}</ol><h2>أسئلة شائعة</h2><details><summary>هل تكفي الصفحة للتشخيص؟</summary><p>لا. هي للتثقيف وتنظيم الملاحظات فقط.</p></details><details><summary>ما أهم شيء أراقبه؟</summary><p>الاستمرار والشدة والأثر في الحياة اليومية.</p></details><details><summary>متى أطلب مساعدة؟</summary><p>عند الاستمرار أو التعطيل أو الخطر.</p></details></article><aside class="side"><section class="side-card"><h2>الخلاصة في 30 ثانية</h2><p>{e(summary(topic))}</p></section><section class="side-card"><h2>قاعدة مهمة</h2><p>لا تشخص نفسك أو غيرك من عنوان أو عرض واحد.</p></section><section class="side-card"><h2>إعداد الصفحة</h2><p>{AUTHOR}. دون ادعاء مراجعة سريرية فردية.</p></section></aside></div><section class="wrap"><h2>موضوعات مرتبطة</h2><div class="related">{rel}</div></section></main>{footer()}</body></html>"""

def hub():
    cards = []
    for i,t in enumerate(TOPICS):
        cards.append(f'<article class="card" data-format="{t["format"]}" data-title="{e(t["title"])}"><img src="/assets/quick-info/cards/{t["slug"]}.png" width="1280" height="720" loading="{"eager" if i<3 else "lazy"}" alt=""><div class="card-body"><span class="pill">{e(FORMAT_LABELS[t["format"]])}</span><h2>{e(t["title"])}</h2><p>{e(summary(t))}</p><a href="/quick-info/{t["slug"]}/">اقرأ الصفحة ←</a></div></article>')
    graph = {"@context":"https://schema.org","@type":"CollectionPage","name":"معلومات سريعة","url":SITE+"/quick-info/","inLanguage":"ar","hasPart":[{"@type":"Article","name":t["title"],"url":url(t)} for t in TOPICS]}
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>معلومات سريعة | 150 مقارنة واختبارًا ودليلًا نفسيًا</title><meta name="description" content="150 صفحة عربية موثوقة: حزن أم اكتئاب، إرهاق أم كسل، فحوص تثقيفية، علاقات، نوم، قلق وخطوات عملية."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><link rel="canonical" href="{SITE}/quick-info/"><meta property="og:type" content="website"><meta property="og:title" content="معلومات سريعة: 150 موضوعًا نفسيًا"><meta property="og:image" content="{SITE}/assets/quick-info/quick-info-cover.png"><meta property="og:image:width" content="1280"><meta property="og:image:height" content="720"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/assets/quick-info/quick-info.css?v=1.0.0"><script type="application/ld+json">{json.dumps(graph,ensure_ascii=False,separators=(",",":"))}</script></head><body>{header()}<main id="content"><section class="hero wrap"><p class="eyebrow">معرفة مختصرة، لا تشخيص سريع</p><h1>معلومات سريعة</h1><p class="lead">150 صفحة في أكثر الأسئلة النفسية والاجتماعية تداولًا: مقارنات واضحة، فحوص ذاتية للتثقيف، أسباب محتملة، وخطوات عملية. العناوين جذابة لكنها لا تخفي المعلومة ولا تبالغ.</p><div class="notice"><strong>لا توجد نتيجة آلية أو تشخيص.</strong> استخدم الصفحات لتنظيم ملاحظاتك ومعرفة متى يلزم التقييم المهني.</div><img class="cover" src="/assets/quick-info/quick-info-cover.png" width="1280" height="720" alt="رسم تجريدي للصحة النفسية"><div class="controls"><input id="q" type="search" placeholder="ابحث: أرق، اكتئاب، علاقة، طفل..."><select id="f"><option value="">كل الأنواع</option><option value="comparison">مقارنات</option><option value="check">فحوص تثقيفية</option><option value="factors">خمسة أسباب وعوامل</option><option value="relationship">العلاقات والانفصال</option><option value="practical">خطوات عملية</option></select></div><p class="count" id="count">150 صفحة</p></section><section class="wrap cards" id="cards">{"".join(cards)}</section></main>{footer()}<script>const q=document.getElementById("q"),f=document.getElementById("f"),cs=[...document.querySelectorAll(".card")],c=document.getElementById("count");function x(){{let n=0,s=q.value.trim().toLowerCase(),v=f.value;for(const a of cs){{const ok=(!s||a.dataset.title.toLowerCase().includes(s))&&(!v||a.dataset.format===v);a.hidden=!ok;if(ok)n++}}c.textContent=n+" صفحة"}}q.addEventListener("input",x);f.addEventListener("change",x);</script></body></html>"""

def make_image(path, topic=None):
    domain = topic["domain"] if topic else "general"
    fg,bg = GUIDES.get(domain, GUIDES["general"])["colors"]
    im = Image.new("RGB",(1280,720),bg); d=ImageDraw.Draw(im)
    seed = int(hashlib.sha256((topic["slug"] if topic else "cover").encode()).hexdigest()[:12],16)
    rng=random.Random(seed)
    for _ in range(20):
        x,y=rng.randint(-50,1330),rng.randint(-50,770); r=rng.randint(30,160)
        d.ellipse((x-r,y-r,x+r,y+r),outline=fg,width=rng.randint(3,9))
    d.rounded_rectangle((65,65,1215,655),60,outline=fg,width=6)
    if domain=="sleep":
        d.ellipse((470,170,820,520),fill=fg); d.ellipse((590,120,890,430),fill=bg)
    elif domain in {"relationships","grief"}:
        d.ellipse((470,230,640,400),fill=fg); d.ellipse((640,230,810,400),fill=fg); d.polygon([(470,315),(810,315),(640,560)],fill=fg)
    elif domain in {"child","adhd"}:
        d.ellipse((450,160,570,280),fill=fg); d.ellipse((710,160,830,280),fill=fg); d.rounded_rectangle((400,320,610,570),35,outline=fg,width=14); d.rounded_rectangle((670,320,880,570),35,outline=fg,width=14)
    elif domain=="work":
        d.rounded_rectangle((390,240,890,520),40,outline=fg,width=18); d.arc((550,150,730,330),180,360,fill=fg,width=18)
    elif domain=="digital":
        d.rounded_rectangle((500,120,780,600),45,outline=fg,width=18); d.ellipse((625,540,655,570),fill=fg)
    else:
        for dx,dy,r in [(-120,-80,100),(0,-120,110),(120,-80,100),(-150,50,95),(0,45,120),(150,50,95),(-80,145,90),(80,145,90)]:
            d.ellipse((640+dx-r,330+dy-r,640+dx+r,330+dy+r),outline=fg,width=14)
        d.line((640,105,640,570),fill=fg,width=8)
    path.parent.mkdir(parents=True,exist_ok=True); im.save(path,"PNG",optimize=True)

def write(path, text):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text.rstrip()+"\n",encoding="utf-8")

def update_home():
    p=ROOT/"index.html"
    if not p.exists(): return
    t=p.read_text(encoding="utf-8")
    if 'href="/quick-info/"' not in t:
        t=t.replace('<nav class="nav">','<nav class="nav"><a href="/quick-info/">معلومات سريعة</a>',1)
    if "QUICK_INFO_SECTION_START" not in t:
        block="""<!-- QUICK_INFO_SECTION_START --><section class="section wrap" aria-labelledby="quick-info-home-title"><div class="section-head"><div><p class="eyebrow">جديد المنصة</p><h2 id="quick-info-home-title">معلومات سريعة</h2><p class="section-intro">150 مقارنة وفحصًا تثقيفيًا وخطة عملية في أكثر أسئلة الصحة النفسية والعلاقات والنوم انتشارًا.</p></div><a class="section-link" href="/quick-info/">استكشف 150 صفحة ←</a></div><div class="panel"><p><strong>حزن أم اكتئاب؟ إرهاق أم كسل؟ هل تعاني من الأرق؟ هل أنت في علاقة سامة؟</strong></p><p>صفحات مختصرة بمصادر مؤسسية وصور كبيرة وتنبيهات سلامة دون تشخيص ذاتي.</p><a class="button dark" href="/quick-info/">افتح القسم</a></div></section><!-- QUICK_INFO_SECTION_END -->"""
        t=t.replace("</main>",block+"</main>",1)
    write(p,t)

def sitemap():
    rows=[("معلومات سريعة",SITE+"/quick-info/",SITE+"/assets/quick-info/quick-info-cover.png")]
    rows += [(t["title"],url(t),img_url(t)) for t in TOPICS]
    parts=[]
    for title,u,img in rows:
        parts.append(f"<url><loc>{xesc(u)}</loc><lastmod>{PUBLISHED}</lastmod><changefreq>monthly</changefreq><image:image><image:loc>{xesc(img)}</image:loc><image:title>{xesc(title)}</image:title></image:image></url>")
    write(ROOT/"sitemap-quick-info.xml",'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'+"".join(parts)+"</urlset>")
    p=ROOT/"sitemap-index.xml"
    if p.exists():
        t=p.read_text(encoding="utf-8")
        if "sitemap-quick-info.xml" not in t:
            t=t.replace("</sitemapindex>",'<sitemap><loc>https://healthrenewal.org/sitemap-quick-info.xml</loc></sitemap></sitemapindex>')
            write(p,t)

def api():
    payload={"version":"1.0.0","generatedAt":PUBLISHED+"T09:00:00+03:00","count":len(TOPICS),"items":[{"slug":t["slug"],"title":t["title"],"format":t["format"],"domain":t["domain"],"summary":summary(t),"url":url(t),"image":img_url(t)} for t in TOPICS]}
    write(ROOT/"api/v1/quick-info.json",json.dumps(payload,ensure_ascii=False,indent=2))

def tests():
    text="""from pathlib import Path\nimport json\nfrom PIL import Image\nROOT=Path(__file__).resolve().parents[1]\ndef test_quick_info():\n api=json.loads((ROOT/"api/v1/quick-info.json").read_text(encoding="utf-8")); assert api["count"]==150; assert len(list((ROOT/"quick-info").glob("*/index.html")))==150; assert len({x["slug"] for x in api["items"]})==150\n for item in api["items"]:\n  p=ROOT/"quick-info"/item["slug"]/"index.html"; s=p.read_text(encoding="utf-8"); assert "max-image-preview:large" in s and '"Article"' in s and '"FAQPage"' in s and "المصادر المحورية" in s\n  with Image.open(ROOT/"assets/quick-info/cards"/(item["slug"]+".png")) as im: assert im.size==(1280,720)\n sm=(ROOT/"sitemap-quick-info.xml").read_text(encoding="utf-8"); assert sm.count("<url>")==151; assert "sitemap-quick-info.xml" in (ROOT/"sitemap-index.xml").read_text(encoding="utf-8")\n assert 'href="/quick-info/"' in (ROOT/"index.html").read_text(encoding="utf-8")\n"""; write(ROOT/"tests/test_quick_info_section.py",text)

def main():
    assert len(TOPICS)==150 and len({t["slug"] for t in TOPICS})==150 and len({t["title"] for t in TOPICS})==150
    for t in TOPICS:
        assert re.fullmatch(r"[a-z0-9-]+",t["slug"]) and t["format"] in FORMAT_LABELS and t["domain"] in GUIDES
    write(ROOT/"assets/quick-info/quick-info.css",CSS)
    write(ROOT/"quick-info/index.html",hub()); make_image(ROOT/"assets/quick-info/quick-info-cover.png")
    for t in TOPICS:
        write(ROOT/"quick-info"/t["slug"]/"index.html",article(t)); make_image(ROOT/"assets/quick-info/cards"/(t["slug"]+".png"),t)
    update_home(); sitemap(); api(); tests()
    report={"generatedAt":PUBLISHED+"T09:00:00+03:00","pages":150,"images":151,"formats":{k:sum(1 for t in TOPICS if t["format"]==k) for k in FORMAT_LABELS},"discover":{"largeImages":True,"maxImagePreviewLarge":True,"articleSchema":True,"faqSchema":True,"canonicalUrls":True,"nonDiagnosticDisclosures":True}}
    write(ROOT/"reports/quick-info-build.json",json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
