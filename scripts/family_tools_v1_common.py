#!/usr/bin/env python3
from __future__ import annotations
import html
import re
from pathlib import Path

ORIGIN = "https://healthrenewal.org"
DEFAULT_CONTENT = Path("content/family-guide-special-education-tools-v1.json")
ROOT_ROUTE = "/family-guide/tools/"

STYLE = r"""
<style>
:root{--ink:#14231e;--muted:#52645d;--brand:#0b6651;--brand2:#164e63;--soft:#eef7f3;--cream:#fffaf0;--line:#cedbd5;--card:#fff;--warn:#8a5208}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8f7;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.95}a{color:#075c49}a:hover{text-decoration-thickness:2px}.skip{position:absolute;inset-inline-start:-9999px}.skip:focus{inset-inline-start:1rem;top:1rem;background:#fff;padding:.7rem;z-index:10}.wrap{width:min(1160px,calc(100% - 2rem));margin:auto}.site-header{background:#fff;border-bottom:1px solid var(--line)}.head{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 0}.brand{font-weight:800;text-decoration:none}.nav{display:flex;gap:1rem;flex-wrap:wrap}.breadcrumbs{padding:1rem 0;color:var(--muted)}.hero{background:linear-gradient(135deg,var(--soft),var(--cream));border-bottom:1px solid var(--line);padding:clamp(2rem,6vw,5rem) 0}.kicker{font-weight:800;color:var(--brand);margin:0}.hero h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.35;margin:.4rem 0 1rem}.lead{font-size:1.16rem;max-width:82ch}.notice{background:#fff;border:1px solid #e4c98c;border-inline-start:6px solid var(--warn);border-radius:14px;padding:1rem 1.2rem}.section{padding:2.5rem 0}.section.alt{background:#eef3f1}.section h2{font-size:clamp(1.5rem,3vw,2.15rem);line-height:1.45}.section h3{line-height:1.55}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:1rem}.card,.tool-card,details,.source-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.2rem;box-shadow:0 7px 22px rgba(15,40,30,.05)}.tool-card{display:flex;flex-direction:column}.tool-card p{flex:1;color:var(--muted)}.button,button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;border:0;border-radius:10px;padding:.68rem 1rem;background:var(--brand);color:#fff;text-decoration:none;font:inherit;font-weight:800;cursor:pointer}.button.secondary,button.secondary{background:#fff;color:var(--brand);border:1px solid var(--brand)}.toolbar{display:flex;gap:.7rem;flex-wrap:wrap;margin:1rem 0}.steps{counter-reset:step;display:grid;gap:1rem}.step{position:relative;padding:1.1rem 4.2rem 1.1rem 1.2rem;background:#fff;border:1px solid var(--line);border-radius:16px}.step:before{counter-increment:step;content:counter(step);position:absolute;inset-inline-start:1rem;top:1rem;width:2.3rem;height:2.3rem;border-radius:50%;background:var(--brand);color:#fff;display:grid;place-items:center;font-weight:800}.checklist li,.rules li,.avoid li{margin:.55rem 0}.example{background:#fef8e9;border:1px solid #e7c879;border-radius:16px;padding:1.2rem}.tool-form label{display:block;font-weight:800;margin-top:1rem}.tool-form input,.tool-form textarea,.tool-form select{width:100%;padding:.75rem;border:1px solid #9fb2aa;border-radius:9px;font:inherit;background:#fff;color:#111}.tool-form textarea{min-height:100px}.tool-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}.meta{color:var(--muted)}.toc{columns:2;column-gap:2rem}.toc li{break-inside:avoid;margin:.35rem 0}.sources{display:grid;gap:.7rem}.source-card a{font-weight:800}.footer{background:#10251e;color:#fff;padding:2rem 0}.footer a{color:#d5fff0}.tag{display:inline-block;background:#dcece6;border-radius:999px;padding:.2rem .65rem;margin:.15rem}.quality-table{width:100%;border-collapse:collapse;background:#fff}.quality-table th,.quality-table td{border:1px solid var(--line);padding:.7rem;text-align:right;vertical-align:top}.quality-table th{background:#e8f3ef}.related{display:flex;gap:.6rem;flex-wrap:wrap}.related a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:.45rem .75rem;text-decoration:none}.print-only{display:none}
@media(max-width:760px){.head{align-items:flex-start;flex-direction:column}.toc{columns:1}.step{padding-inline-start:3.9rem}}
@media print{.site-header,.breadcrumbs,.toolbar,.footer,.nav,.skip{display:none!important}.print-only{display:block}.hero,.section,.section.alt{background:#fff;padding:.7rem 0}.card,.tool-card,.step,.example,.source-card{box-shadow:none;break-inside:avoid}.tool-form input,.tool-form textarea{border:1px solid #777}.wrap{width:100%}a{color:#000;text-decoration:none}}
</style>
"""

COMMON_SECTIONS = {
"rights": """تستند الأداة إلى منظور حقوقي ووظيفي. حق الشخص في التعليم والمشاركة والتواصل والتكييف المعقول لا يعتمد على قدرته على التصرف بالطريقة التي يفضلها الآخرون. لذلك تبدأ الخطة بسؤالين: ما النتيجة التي يريدها الشخص أو يحتاجها في حياته اليومية؟ وما الحاجز الموجود في المهمة أو البيئة أو طريقة التواصل؟ يساعد إطار التصنيف الدولي للوظائف والعجز والصحة ICF على فصل وظائف الجسم عن النشاط والمشاركة والعوامل البيئية، ويمنع اختزال القرار في اسم التشخيص. كما يدعم التصميم الشامل للتعلم تقديم أكثر من طريقة للفهم والمشاركة والتعبير، مع إبقاء الدعم الفردي متاحًا عندما لا يكفي التصميم العام.""",
"before": """قبل استخدام النموذج، اجمع الحد الأدنى الكافي من المعلومات بدل انتظار ملف مثالي. تحدث مع الشخص بالطريقة التي يفهمها ويستخدمها، وراجع أمثلة من بيئتين على الأقل متى كان ذلك ممكنًا. دوّن عوامل الصحة والألم والنوم والسمع والبصر والحركة والدواء عندما قد تؤثر في الأداء، ولا تفسر تغيرًا مفاجئًا بوصفه مشكلة تعليمية أو سلوكية فقط. اتفق على معنى الكلمات والمقاييس بين الأسرة والمدرسة، وحدد من يملك حق الوصول إلى المعلومات. لا تضع أسماء كاملة أو بيانات حساسة في نسخة مشتركة أو على جهاز عام.""",
"quality": [
"هل يصف النموذج أداءً أو حاجزًا يمكن ملاحظته بدل حكم على الشخصية؟",
"هل شارك الشخص نفسه أو مُنح وسيلة مناسبة للتعبير عن الاختيار والرفض؟",
"هل ربط كل قرار بخط أساس أو مثال أو مصدر بيانات واضح؟",
"هل جُرّبت تعديلات البيئة وطريقة التعليم والتواصل قبل زيادة المطالب؟",
"هل يمكن لشخص آخر تطبيق الخطوة بالطريقة نفسها دون تخمين؟",
"هل يتضمن القرار مؤشر فائدة ومؤشر ضرر وموعد مراجعة؟",
"هل تحمي الخطة الكرامة والخصوصية وتستخدم أقل إجراء تقييدًا؟",
"هل توضح حدود الأداة والحالات التي تحتاج تقييمًا أو تدخلًا عاجلًا؟"
],
"avoid": [
"نسخ هدف أو تكييف من طالب آخر لأن التشخيص متشابه.",
"اعتبار الهدوء أو الامتثال نتيجة أهم من التواصل والأمان والمشاركة.",
"تغيير عدة متغيرات في وقت واحد ثم الادعاء بمعرفة ما نجح.",
"استخدام عقوبة أو حرمان أو سحب وسيلة تواصل بوصفه تدخلًا تعليميًا.",
"إهمال الألم أو التعب أو الجوع أو صعوبة السمع والبصر عند تفسير الأداء.",
"جمع بيانات كثيرة لا يستخدمها أحد في قرار واضح.",
"اعتبار عدم التقدم فشلًا للشخص قبل مراجعة جودة التنفيذ وملاءمة الهدف.",
"تبادل معلومات تعريفية حساسة خارج القنوات المصرح بها."
],
"roles": """توزع المسؤوليات بحسب الخبرة والسياق. يوضح الشخص ما يهمه وما يرفضه بالوسيلة المناسبة له. تقدم الأسرة المعرفة بالتاريخ والروتين والنجاحات خارج المدرسة. يربط المعلم الأهداف بالمنهج والمشاركة الصفية ويجمع بيانات قابلة للاستخدام. يسهم اختصاصيو التربية الخاصة والتواصل والعلاج الوظيفي والطبي وغيرهم عندما تكون خبرتهم مرتبطة بالسؤال، دون أن يعمل كل تخصص بمعزل عن الآخر. مسؤول التنسيق يغلق الحلقة: يلخص القرار، يحدد المواعيد، ويتأكد أن ما اتفق عليه وصل إلى البيئة اليومية.""",
"decision": """لا يكفي أن تبدو الخطة منطقية؛ يجب أن تحدد ما الذي سيجعل الفريق يستمر أو يعدل أو يتوقف. يستمر الدعم عندما تتحسن النتيجة المهمة للشخص دون ضرر أو عبء غير متناسب. يُعدّل عندما يكون التنفيذ غير ثابت، أو لا يتحسن المؤشر، أو يظهر أن الحاجز مختلف عما افترضه الفريق. يُوقف ويُطلب تقييم مختص عندما يزيد الألم أو الضيق أو الخطر، أو يحدث فقد مهارة مفاجئ، أو تظهر آثار جانبية أو انتهاك لحق الشخص. القرار الجيد يوثق عدم اليقين بدل إخفائه."""
}

CATEGORY_GUIDANCE = {
"التخطيط الفردي":"تستخدم أدوات التخطيط عندما تحتاج الأسرة والفريق إلى توحيد الأولويات وترجمة الرؤية إلى خطوات ومسؤوليات. لا تستخدم لإلزام الشخص بهدف لم يشارك في اختياره.",
"السلوك والدعم الإيجابي":"تستخدم عند وجود سلوك يعطل الأمان أو المشاركة ويحتاج فهمًا وظيفيًا. لا تحل محل التقييم الطبي أو النفسي عند التغير المفاجئ أو الخطر الشديد.",
"التقييم والتنسيق":"تستخدم قبل الاجتماعات والتقييمات لتقليل فقد المعلومات وتحسين الأسئلة. لا تحول الأسرة إلى جهة تشخيص ولا تستبدل الاختبارات المهنية المعيارية.",
"الخطة التربوية الفردية":"تستخدم لبناء أو مراجعة خطة تربوية مترابطة. القوانين والإجراءات تختلف بين البلدان؛ المبادئ التعليمية والحقوقية لا تغني عن مراجعة النظام المحلي.",
"القياس التربوي":"تستخدم عندما يحتاج الفريق خط أساس أو متابعة أو هدفًا يمكن قياسه. القياس أداة قرار وليس قيمة للشخص أو ترتيبًا نهائيًا لقدراته.",
"الوصول إلى المنهج":"تستخدم عندما يمنع شكل المهمة أو البيئة الطالب من إظهار التعلم. يجب تمييز التكييف عن تعديل الهدف الأكاديمي بوضوح.",
"التواصل المعزز والبديل":"تستخدم لحماية الوصول إلى التواصل في كل البيئات. لا يشترط فشل الكلام ولا عمرًا أو درجة ذكاء محددة قبل التفكير في AAC.",
"الوصول الحسي":"تستخدم لفحص تفاعل البيئة مع التنظيم والمشاركة. لا تثبت تشخيصًا حسيًا ولا تبرر أساليب تقييدية أو مؤلمة.",
"التكنولوجيا المساندة":"تستخدم لمقارنة حلول في مهمة حقيقية. لا يكفي شراء جهاز؛ يلزم تدريب ودعم وصيانة وبديل احتياطي.",
"التعليم الدامج":"تستخدم لتحليل تصميم الصف وفرص المشاركة. ليست تقييم أداء للمعلم ولا مراقبة عقابية للطالب.",
"التنسيق والشراكة":"تستخدم لتثبيت القرارات المشتركة وإغلاق حلقة المتابعة. لا تستبدل النماذج أو الإجراءات الرسمية المطلوبة محليًا.",
"الانتقال والاستقلال":"تستخدم مبكرًا لتخطيط الحياة بعد المدرسة. يجب أن تقودها تفضيلات الشخص وحقه في اتخاذ القرار المدعوم."
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def visible_words(markup: str) -> int:
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", markup, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return len(re.findall(r"[\u0600-\u06FF\w]+", text, flags=re.UNICODE))
