#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
INVENTORY = SITE / "api" / "all-labs-v22.json"
PROFILES = ROOT / "content" / "v217" / "lab-guidance-profiles-ar.json"
START = "<!-- lab-guidance-v217:start -->"
END = "<!-- lab-guidance-v217:end -->"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
WHO = "https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response"
NIMH = "https://www.nimh.nih.gov/health/topics"
PUBMED = "https://pubmed.ncbi.nlm.nih.gov/about/"
COCHRANE = "https://www.cochrane.org/evidence"
STYLE = '<style id="lab-guidance-v217-style">.lab-guidance-v217{max-width:980px;margin:28px auto;padding:clamp(22px,4vw,42px);border:1px solid #cfe4df;border-radius:28px;background:#fff;box-shadow:0 16px 44px rgba(20,91,87,.08);line-height:1.9}.lab-guidance-v217 h2,.lab-guidance-v217 h3{color:#164f4c}.lab-guidance-v217 li{margin:.45rem 0}.lab-guide-lead{font-size:1.08rem}.lab-guide-sources{background:#f2faf8;border-radius:18px;padding:18px 38px}</style>'


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def visible_words(markup: str) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", re.sub(r"<[^>]+>", " ", markup)))


def find_profile(profiles: dict[str, object], group: str, category: str, title: str, mode: str = "") -> tuple[str, str]:
    items = profiles[group]
    haystack = f"{category} {title} {mode}"
    for key, item in items.items():
        if key in haystack or any(part and part in haystack for part in key.split()):
            return str(item["focus"]), str(item["context"])
    if group == "assessment":
        return (
            "تكرار الخبرة وأثرها في الوظيفة اليومية والمشاركة وطلب الدعم",
            "الزمن والمكان والمجيب والنوم والصحة والروتين والموارد المتاحة",
        )
    return (
        "اتباع القاعدة والمحافظة على الدقة وتعديل الاستجابة مع تغير عبء المهمة",
        "فهم التعليمات والتدريب والجهاز والتعب والمقاطعات وطريقة الإدخال",
    )


def assessment_block(tool: dict[str, object], profiles: dict[str, object]) -> str:
    title = esc(tool.get("title") or tool.get("slug") or "الأداة")
    category_raw = str(tool.get("category") or "المتابعة")
    category = esc(category_raw)
    questions = int(tool.get("questions") or 0)
    score_type = str(tool.get("score_type") or "monitor")
    focus, context = find_profile(profiles, "assessment", category_raw, str(tool.get("title") or ""))
    score_note = (
        "لهذه الأداة طريقة تصحيح أو مرجع معلن، لكن النطاق الرقمي يبقى جزءًا من صورة أوسع. اقرأ تعليمات النسخة المستخدمة وفترة الإجابة، ولا تحول نقطة القطع إلى تشخيص آلي أو قرار علاجي منفرد."
        if score_type != "monitor" else
        "هذه متابعة محلية غير معيارية؛ الرقم يصف اتجاه الشخص داخل شروطه فقط. لا توجد نقطة قطع تشخيصية، ولا يصح مقارنة أشخاص مختلفين أو اتخاذ قرار علاجي أو تربوي مرتفع الأثر من الرقم وحده."
    )
    return f'''{START}<section class="lab-guidance-v217" aria-labelledby="lab-guide-v217-title">
<h2 id="lab-guide-v217-title">دليل استخدام {title}</h2>
<p class="lab-guide-lead">تضم الأداة {questions} بنودًا ضمن مجال «{category}». الغرض هو تنظيم الملاحظة وتحويل الانطباع العام إلى معلومات يمكن مراجعتها مع السياق، لا إصدار تشخيص أو حكم على الشخصية أو الأسرة. اقرأ كل بند وفق الفترة المحددة، واختر الإجابة الأقرب إلى الوضع المعتاد، ثم دوّن الظروف الاستثنائية التي قد تفسر النتيجة.</p>
<h3>ما الذي تساعد الأداة على ملاحظته؟</h3>
<p>يركز هذا المسار على {esc(focus)}. القيمة الحقيقية ليست في الرقم المجرد، بل في معرفة المواقف التي يظهر فيها النمط، وما الذي يسبقه، وكيف يؤثر في التعلم أو العمل أو العلاقات أو الرعاية الذاتية، وما التغيير الذي خفف أثره.</p>
<p>اقرأ الإجابات ضمن {esc(context)}. اختلاف النتيجة بين سياقين أو بين مجيبين ليس خطأً تلقائيًا؛ قد يكشف اختلاف المتطلبات أو الدعم أو وضوح التعليمات أو شعور الشخص بالأمان. احتفظ بالأمثلة الواقعية ولا تلغِ صوت الشخص أو وسيلة تواصله.</p>
<p>عند إعادة التطبيق، ابحث عن تغير وظيفي قابل للملاحظة: مشاركة أوسع، استقلال أكبر، وقت أقل مستهلك في الصعوبة، تعافٍ أسرع، أو قدرة أفضل على طلب المساندة. لا تعتبر اختفاء السلوك وحده تقدمًا إذا ترافق مع انسحاب أو إجهاد أو فقدان للاختيار.</p>
<h3>قبل البدء: ثبّت شروط الإجابة</h3>
<ul><li>حدد من يجيب، والفترة الزمنية، والأماكن أو المواقف التي تستند إليها الإجابة.</li><li>اختر وقتًا يسمح بالتركيز، وتجنب الإجابة أثناء خلاف حاد أو أزمة إلا عندما تكون الأداة مخصصة لذلك.</li><li>سجل التغيرات المهمة في النوم والصحة والأدوية الموصوفة والروتين والدعم؛ فقد تغير النمط.</li><li>لا تطلب من شخص آخر كشف إجاباته الخاصة، ولا تستخدم النتيجة للعقاب أو الحرمان أو إثبات موقف مسبق.</li></ul>
<h3>قراءة النتيجة بطريقة مهنية</h3>
<p>{score_note}</p>
<p>راجع البنود الأعلى أثرًا إلى جانب الدرجة الكلية: ما الخبرة أو السلوك؟ كم يتكرر؟ أين يظهر؟ ما أثره؟ وما الدعم الذي غيّره؟ هذه الأسئلة تحول النتيجة إلى فرضية صغيرة قابلة للاختبار. لا تفسر فرقًا محدودًا بين تطبيقين قبل مراجعة اختلاف المجيب والوقت والبيئة وطريقة الإجابة.</p>
<p>لا تستخدم النتيجة لتأكيد سبب واحد. قد تتداخل الصحة الجسدية والألم والنوم والأدوية واللغة والسمع والبصر والضغط والبيئة. عندما تكون الحاجة لاتخاذ قرار مهني أو تربوي أو علاجي، يجب جمع التاريخ والمقابلة والملاحظة ومصادر معلومات متعددة وأدوات مناسبة للغرض.</p>
<h3>خطة متابعة من أربع خطوات</h3>
<ol><li><strong>حدد أولوية واحدة:</strong> اختر بندًا مرتبطًا بالأمان أو الوظيفة أو جودة الحياة بدل محاولة تغيير كل شيء دفعة واحدة.</li><li><strong>اختر تغييرًا واضحًا:</strong> تعديل روتين أو تيسير أو مهارة أو طلب دعم يمكن ملاحظته خلال فترة محددة.</li><li><strong>سجل مؤشرًا واقعيًا:</strong> التكرار أو المدة أو الاستقلال أو المشاركة، مع مثال موجز من الحياة اليومية.</li><li><strong>راجع القرار:</strong> استمر عند ظهور نفع واضح، وعدل الخطة أو اطلب تقييمًا أوسع عندما يبقى الأثر أو يتفاقم.</li></ol>
<h3>متى نطلب مساعدة متخصصة؟</h3>
<p>اطلب تقييمًا متخصصًا عندما يستمر الضيق أو يتسع أثره، أو تتراجع الدراسة أو العمل أو العلاقات أو الرعاية الذاتية، أو توجد أعراض جسدية أو دوائية محتملة، أو تحتاج الأسرة أو المدرسة إلى قرار يتجاوز التثقيف العام. عند وجود خطر مباشر أو أفكار إيذاء النفس أو الآخرين أو فقدان الأمان أو ارتباك شديد، استخدم خدمات الطوارئ المحلية ولا تنتظر نتيجة الأداة.</p>
<h3>حدود الاستخدام ومصادر التحقق</h3>
<p>المحتوى للتثقيف والمتابعة المنظمة، ولا يستبدل التشخيص أو العلاج أو التقييم النفسي والتربوي المقنن. ابدأ بالمصادر المؤسسية، ثم ارجع إلى الدراسات الأصلية والمراجعات المنهجية، وافحص تاريخ النشر والسكان وطريقة الدراسة والصدق والثبات وتعارض المصالح قبل نقل نتيجة إلى سياق مختلف.</p>
<ul class="lab-guide-sources"><li><a href="{WHO}">منظمة الصحة العالمية: الصحة النفسية والاستجابة</a></li><li><a href="{NIMH}">المعهد الوطني للصحة النفسية: الموضوعات الصحية</a></li><li><a href="{PUBMED}">PubMed: البحث في الأدبيات الطبية والسلوكية</a></li><li><a href="{COCHRANE}">Cochrane: الأدلة والمراجعات المنهجية</a></li></ul>
</section>{END}'''


def cognitive_block(tool: dict[str, object], profiles: dict[str, object]) -> str:
    title_raw = str(tool.get("title") or tool.get("slug") or "المهمة")
    category_raw = str(tool.get("category") or "القدرات المعرفية")
    title, category = esc(title_raw), esc(category_raw)
    stages = int(tool.get("stages") or 0)
    trials = int(tool.get("total_trials") or int(tool.get("trials_per_stage") or 0) * stages)
    focus, context = find_profile(profiles, "cognitive", category_raw, title_raw, str(tool.get("mode") or ""))
    return f'''{START}<section class="lab-guidance-v217" aria-labelledby="lab-guide-v217-title">
<h2 id="lab-guide-v217-title">كيف تستخدم مهمة {title}؟</h2>
<p class="lab-guide-lead">تنتمي المهمة إلى مجال «{category}»، وتتدرج عبر {stages} مراحل ونحو {trials} محاولة. هي تمرين تفاعلي يصف الأداء داخل هذه الجلسة وظروف الجهاز، وليست اختبار ذكاء أو أداة تشخيص أو نسخة رقمية من مقياس سريري مقنن.</p>
<h3>ما العملية التي تستدعيها المهمة؟</h3>
<p>تستدعي المهمة {esc(focus)}. الأداء لا يمثل قدرة منفصلة ثابتة؛ فهو حصيلة فهم القاعدة والانتباه والاستراتيجية والرؤية أو السمع والحركة والاستجابة للضغط، إضافة إلى خصائص الجهاز والواجهة.</p>
<p>فسر النتيجة ضمن {esc(context)}. انخفاض الدقة أو بطء الزمن قد ينتج من أكثر من عامل، لذلك لا تحول النتيجة إلى وصف للشخص مثل «ذكي» أو «ضعيف»، ولا تقارنها بأشخاص آخرين من دون عينة معيارية وشروط تطبيق موحدة.</p>
<h3>تهيئة جلسة قابلة للمقارنة</h3>
<ul><li>استخدم الجهاز وطريقة الإدخال نفسيهما قدر الإمكان، وتحقق من وضوح النص والألوان والصوت إن وجد.</li><li>اقرأ التعليمات وأكمل المثال قبل التسجيل؛ الخطأ الناتج عن سوء الفهم لا يقيس العملية المستهدفة.</li><li>اختر وقتًا بلا مقاطعات متكررة، وسجل التعب والنوم والألم والمنبهات والأدوية الموصوفة.</li><li>خذ استراحة عند الإجهاد البصري أو الصداع أو التوتر، ولا تكرر المهمة حتى يصبح التدريب على المواد هو العامل الأكبر.</li></ul>
<h3>ما الذي تعنيه الأرقام؟</h3>
<p>تعرض المهمة عادة الدقة والزمن ونمط الأخطاء. الدقة هي الاستجابات المطابقة للقاعدة، والزمن يشمل الفهم والحركة والجهاز، أما التباين بين المحاولات فيصف الثبات داخل الجلسة. لا يجمع أي رقم واحد هذه الجوانب أو يحدد سبب الخطأ.</p>
<p>عند مقارنة محاولتين، ابحث عن تغير متسق لا عن أفضل جولة منفردة. قد تتحسن السرعة بسبب معرفة الواجهة، وقد تتراجع الدقة بسبب الاستعجال. احتفظ بملاحظة عن الاستراتيجية والظروف؛ فهذه المعلومة ضرورية لفهم الفرق أكثر من الرقم الخام.</p>
<p>لا تستنتج وجود حالة صحية أو غيابها من المهمة. التقييم المهني يجمع التاريخ والمقابلة والملاحظة والاختبارات المقننة والصحة الجسدية والسياق. تختلف صلاحية الأدوات باختلاف اللغة والعمر والتعليم والهدف، ولا تنتقل معايير أداة إلى مهمة تفاعلية غير مقننة.</p>
<h3>أسئلة تفسير عملية</h3>
<ol><li>هل فُهمت القاعدة منذ البداية أم احتاجت إلى تدريب إضافي؟</li><li>في أي مرحلة تغير الأداء، وهل زاد العبء أو تبدلت القاعدة أو طالت السلسلة؟</li><li>هل كانت الأخطاء من نوع واحد، أم ظهرت مع التعب أو المقاطعة أو الاستعجال؟</li><li>هل يظهر نمط مشابه في مهمة يومية، أم ظهر داخل هذه الواجهة فقط؟</li></ol>
<h3>الاستخدام المسؤول وإمكانية الوصول</h3>
<p>يجب توفير تباين وحجم ووقت مناسبين وطريقة إدخال يمكن استخدامها بأمان. إذا كانت الرؤية أو السمع أو الحركة أو اللغة تؤثر في التفاعل، فقد تكون العامل الأساسي في النتيجة. لا تفسر أداءً منخفضًا قبل التأكد من أن المهمة كانت مفهومة وقابلة للوصول.</p>
<p>إذا كانت هناك شكوى معرفية جديدة أو متفاقمة، أو تغير مفاجئ بعد إصابة أو مرض، أو أثر واضح في الأمان والعمل والدراسة والاستقلال، اطلب تقييمًا مهنيًا مناسبًا. عند الارتباك الحاد أو أعراض عصبية مفاجئة أو خطر مباشر، استخدم الرعاية العاجلة المحلية.</p>
<h3>مصادر لفهم الأدلة والبحث</h3>
<p>للتوسع، استخدم قواعد البحث والمراجعات المنهجية، وميز بين دراسة تستخدم مهمة تجريبية وبين أداة مقننة لاتخاذ القرار. افحص العينة واللغة وطريقة القياس والصدق والثبات قبل نقل استنتاج إلى شخص أو بيئة مختلفة.</p>
<ul class="lab-guide-sources"><li><a href="{NIMH}">المعهد الوطني للصحة النفسية: معلومات وبحوث الصحة النفسية</a></li><li><a href="{PUBMED}">PubMed: فهرس الأدبيات الطبية والعلوم السلوكية</a></li><li><a href="{COCHRANE}">Cochrane: الأدلة والمراجعات المنهجية</a></li><li><a href="{WHO}">منظمة الصحة العالمية: الصحة النفسية وحدود المعلومات العامة</a></li></ul>
</section>{END}'''


def ensure_inventory() -> None:
    if INVENTORY.is_file():
        return
    subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_all_labs_v22.py"), str(SITE)], cwd=ROOT, check=True)
    if not INVENTORY.is_file():
        raise SystemExit(f"Laboratory inventory was not created: {INVENTORY}")


def inject(page: Path, block: str) -> tuple[bool, int]:
    text = page.read_text(encoding="utf-8")
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise SystemExit(f"Broken v217 markers: {page}")
        return False, visible_words(text[text.index(START):text.index(END)])
    if BANNED.search(block):
        raise SystemExit(f"Banned person-label in generated guidance: {page}")
    insertion = text.lower().rfind("</main>")
    if insertion < 0:
        insertion = text.lower().rfind("</body>")
    if insertion < 0:
        raise SystemExit(f"Missing main/body closing marker: {page}")
    if 'id="lab-guidance-v217-style"' not in text:
        head = re.search(r"</head\s*>", text, re.I)
        if not head:
            raise SystemExit(f"Missing head close: {page}")
        text = text[:head.start()] + STYLE + text[head.start():]
        insertion = text.lower().rfind("</main>")
        if insertion < 0:
            insertion = text.lower().rfind("</body>")
    page.write_text(text[:insertion] + block + text[insertion:], encoding="utf-8")
    return True, visible_words(block)


def main() -> int:
    if not SITE.is_dir() or not PROFILES.is_file():
        raise SystemExit("Missing generated site or v217 profile source")
    ensure_inventory()
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    tools = inventory.get("tools") or []
    stats = {"version":217,"status":"passed","inventory_tools":len(tools),"pages_changed":0,"assessment_pages":0,"cognitive_pages":0,"minimum_added_words":10**9,"missing_pages":[]}
    for tool in tools:
        kind, rel = str(tool.get("kind") or ""), str(tool.get("path") or "")
        page = SITE / rel
        if kind not in {"assessment", "cognitive"} or not page.is_file():
            stats["missing_pages"].append(rel)
            continue
        block = assessment_block(tool, profiles) if kind == "assessment" else cognitive_block(tool, profiles)
        changed, words = inject(page, block)
        stats["pages_changed"] += int(changed)
        stats[f"{kind}_pages"] += 1
        stats["minimum_added_words"] = min(stats["minimum_added_words"], words)
    if stats["missing_pages"] or stats["assessment_pages"] != int(inventory.get("assessment_count") or 0) or stats["cognitive_pages"] != int(inventory.get("cognitive_count") or 0) or stats["minimum_added_words"] < 430:
        stats["status"] = "failed"
    output = SITE / "api" / "lab-guidance-v217.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if stats["status"] != "passed":
        raise SystemExit(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
