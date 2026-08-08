from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS_PATH = ROOT / "content" / "v32" / "lab-methods-ar.json"
START = "<!-- lab-specificity-v32:start -->"
END = "<!-- lab-specificity-v32:end -->"
EXPECTED_MONITORS = 36
EXPECTED_COGNITIVE = 53
MIN_MONITOR_SPECIFIC_WORDS = 130
MIN_COGNITIVE_SPECIFIC_WORDS = 95

TASK_NOTES = {
    "simple-reaction": "اقرأ الزمن مع ثبات الدقة. الاستجابات السابقة لظهور المثير أو الضغطات المتكررة لا تمثل سرعة معالجة، والتباطؤ المفرد قد ينتج من لمس الشاشة أو فقد التركيز لا من تغير معرفي ثابت.",
    "choice-reaction": "فرّق بين بطء اكتشاف المثير وبطء اختيار الاستجابة. زيادة البدائل ترفع عبء القرار، لذلك لا تقارن زمن هذه المهمة بزمن الاستجابة البسيطة كما لو كانا القياس نفسه.",
    "visual-reaction": "راجع وضوح المثير وتباينه وموقعه على الشاشة قبل تفسير الزمن. صعوبة الرؤية أو الوهج أو تغيير حجم العرض قد ترفع زمن الاستجابة حتى لو لم تتغير القدرة المستهدفة.",
    "auditory-symbol": "تحقق من سماع التعليمات ومن تكافؤ البديل النصي قبل قراءة الأداء. الخطأ قد يكون في سماع الإشارة أو تذكر ارتباطها بالرمز أو اختيار الاستجابة، وهذه عمليات مختلفة.",
    "go-no-go": "افصل أخطاء العمولة، أي الاستجابة عندما يجب الامتناع، عن أخطاء الإغفال، أي عدم الاستجابة للمثير المطلوب. النمطان لا يحملان المعنى نفسه وقد يتأثران بالسرعة والتعب وفهم القاعدة.",
    "stroop-basic": "المعلومة المهمة هي كلفة التعارض بين معنى الكلمة ولون الحبر، لا عدد الإجابات الصحيحة وحده. القراءة الآلية للكلمات وألفة الألوان وسرعة الإدخال تؤثر في الأداء الرقمي.",
    "stroop-advanced": "راقب أخطاء الكبح وأخطاء تبديل القاعدة بصورة منفصلة. إذا استمر المشارك في تطبيق القاعدة السابقة بعد الإشارة الجديدة فهذا يختلف عن خطأ تسمية لون أو قراءة كلمة.",
    "response-inhibition": "حدد هل الخطأ حدث بسبب بدء الاستجابة قبل اكتمال الإشارة أم بسبب فشل الاحتفاظ بقاعدة التوقف. لا يُستنتج اضطراب اندفاع من جلسة رقمية قصيرة دون سياق وظيفي وتقييم أوسع.",
    "digit-span-forward": "الأداء يتأثر بطول السلسلة، سرعة العرض، وطريقة التجميع الذهني. خطأ موضع واحد يختلف عن فقد نهاية السلسلة، لذلك راقب نمط الخطأ لا الحد الأقصى للطول فقط.",
    "digit-span-backward": "هذه المهمة تضيف إعادة ترتيب إلى الاحتفاظ؛ لذلك الانخفاض مقارنة بالترتيب الأمامي لا يعزل سببًا واحدًا. راقب أخطاء القلب الجزئي وفقد العناصر وتجاوز طول السلسلة القابل للإدارة.",
    "letter-span": "ألفة الحروف وسهولة نطقها واستراتيجية الترديد عوامل مؤثرة. عند المقارنة بين جلستين ثبّت سرعة العرض وطريقة الإدخال حتى لا تنسب فرقًا تقنيًا إلى الذاكرة اللفظية.",
    "spatial-span": "راقب هل الأخطاء حذف لموقع، تبديل في الترتيب، أم لمس لموضع مجاور. حجم الشاشة والمسافة بين المواضع ودقة اللمس قد تغير النتيجة بصورة كبيرة.",
    "one-back": "المطلوب تحديث عنصر واحد باستمرار. الأخطاء المتتابعة بعد خطأ واحد قد تعكس فقد الحالة الحالية مؤقتًا، لذلك افحص تسلسل المحاولات بدل حساب نسبة نهائية فقط.",
    "two-back": "يرتفع التداخل لأن القرار يعتمد على عنصر أقدم من المثير السابق مباشرة. راقب خلط المثير الحالي بالسابق وميل التخمين عندما يزداد الحمل، ولا تقارن النتيجة مباشرة بمهام N-back ذات إعدادات أخرى.",
    "three-back": "ارتفاع الحمل يجعل الأداء حساسًا للتعب وفقد القاعدة والتخمين. إذا انهارت الدقة في مرحلة متأخرة فافحص عدد المحاولات وسرعة العرض وأثر الممارسة قبل تفسير ذلك كحد ثابت للذاكرة العاملة.",
    "memory-update": "الخطأ المهم هو الاحتفاظ بقيمة قديمة بعد وصول معلومة جديدة. فرّق بين فشل التحديث وفشل تذكر العنصر الأصلي، وسجل في أي نقطة من سلسلة التغييرات بدأ الانحراف.",
    "working-memory-updating": "راقب هل الفشل مرتبط بعدد العناصر التي يجب تحديثها، بتعارض القواعد، أم بفقد عنصر واحد يفسد ما بعده. الأداء هنا ليس مقياسًا عامًا للذكاء ولا يحدد سبب صعوبة يومية.",
    "visual-grid": "افصل بين خطأ ترميز الموقع أثناء العرض وخطأ الاستدعاء لاحقًا. كثافة الشبكة، التباين، وحجم الخلايا عوامل يجب تثبيتها عند المقارنة بين الجلسات.",
    "sequence-memory": "ميّز بين معرفة العناصر الصحيحة ووضعها بالترتيب الصحيح. أخطاء التبديل بين عنصرين تحمل معلومات مختلفة عن نسيان عنصر كامل أو إضافة عنصر لم يُعرض.",
    "paired-associates": "النجاح يتطلب تعلم العلاقة بين عنصرين لا التعرف على كل عنصر منفردًا. راقب أزواجًا تتكرر أخطاؤها واحتمال التشابه الدلالي أو البصري بينها قبل تعميم النتيجة.",
    "symbol-memory": "التشابه البصري بين الرموز قد يرفع التداخل. يجب التحقق من وضوح الرسم وحجم الشاشة وعدم وجود رمز غامض قبل تفسير الخلط باعتباره صعوبة ذاكرية.",
    "prospective-memory": "المهمة تجمع استمرار النشاط الجاري مع تذكر تنفيذ نية عند إشارة لاحقة. نسيان النية يختلف عن رؤية الإشارة متأخرًا أو إيقاف المهمة الجارية بصورة غير صحيحة.",
    "associative-binding": "راقب هل يتذكر المشارك العناصر لكنه يخلط الروابط بينها؛ هذا يختلف عن فقد العنصر نفسه. التشابه بين الأزواج وعدد الروابط يؤثران في صعوبة المهمة.",
    "temporal-order-memory": "المطلوب تمثيل ترتيب الظهور. أخطاء قلب عنصرين متجاورين تختلف عن عدم التعرف على عنصر، لذلك يجب الحفاظ على تسلسل المحاولات في تقرير الجلسة.",
    "visual-change-detection": "حدد نوع التغير: لون أو شكل أو موضع، لأن صعوبتها ليست متكافئة. زيادة عدد العناصر قد ترفع الحمل، كما أن الوميض أو اختلاف العرض قد يصنع إشارة بصرية غير مقصودة.",
    "visual-search": "اقرأ الزمن والدقة بحسب عدد المشتتات وتشابهها مع الهدف. البحث السهل بخاصية بارزة لا يقارن مباشرة بالبحث الذي يحتاج فحص عدة عناصر.",
    "symbol-search": "راقب التوازن بين السرعة والدقة، وتأكد أن الرموز متمايزة بصريًا. الضغط لزيادة السرعة قد يرفع الأخطاء دون أن يعني تدهور القدرة المستهدفة.",
    "sustained-attention": "قسّم الجلسة زمنيًا لملاحظة التراجع المتأخر بدل الاكتفاء بالمجموع. ازدياد الإغفالات مع الوقت قد يرتبط بالتعب أو الملل أو المشتتات ويحتاج تفسيرًا سياقيًا.",
    "divided-attention": "افحص أداء كل مسار من المسارين إضافة إلى النتيجة الكلية. قد يحافظ المشارك على هدف واحد على حساب الآخر، وهو نمط لا يظهر إذا جُمعت الإجابات في نسبة واحدة.",
    "selective-attention": "حدد البعد المطلوب والبعد المشتت، ثم راقب أي نوع من المشتتات يقود إلى الخطأ. التباين البصري وفهم التعليمات قد يغيران مقدار التداخل.",
    "attention-switch": "قارن محاولات تبديل القاعدة بمحاولات تكرار القاعدة نفسها. تكلفة التبديل تُفهم من الفرق بينهما لا من الزمن الخام وحده، وتتأثر بنسبة محاولات التبديل والتدريب.",
    "number-series": "لا تعتمد السؤال إلا إذا كانت هناك قاعدة واحدة معقولة تقود إلى جواب واحد. الخطأ قد يكون حسابيًا أو في استنتاج النمط؛ لذلك تشرح التغذية الراجعة القاعدة المستخدمة بدل وصف الإجابة بأنها خطأ فقط.",
    "matrix-patterns": "يجب أن تكون العلاقة بين الأشكال قابلة للوصف وأن تكون المشتتات ناتجة عن قواعد بديلة معقولة. البدائل العشوائية تجعل المهمة أسهل ولا تقدم قراءة مفيدة للاستدلال.",
    "odd-one-out": "تحقق أن الفئة التي تجمع العناصر واضحة وأن عنصرًا واحدًا فقط يخالفها. إذا أمكن بناء أكثر من تصنيف صحيح تصبح المحاولة غامضة ولا ينبغي احتسابها كدليل على الاستدلال.",
    "verbal-analogy": "حدّد العلاقة بين الزوج الأول قبل نقلها للزوج الثاني. المفردات والثقافة والخبرة التعليمية قد تكون مصدر الخطأ، لذلك لا تُفسر النتيجة كقدرة استدلال مستقلة عن اللغة.",
    "logical-rules": "راقب أخطاء قلب الشرط أو إضافة معلومات غير معطاة. جودة المهمة تعتمد على صياغة قاعدة لا تحتمل أكثر من قراءة، وعلى تمييز ما يلزم منطقيًا مما يبدو محتملًا فقط.",
    "conditional-reasoning": "فرّق بين إثبات التالي وقلب الشرط وبين الاستنتاج الصحيح من المعطيات. إذا كانت اللغة معقدة فقد تقيس القراءة بقدر ما تقيس الاستدلال الشرطي.",
    "mental-arithmetic": "حدد العمليات المطلوبة وطول الاحتفاظ بالنتائج الوسيطة. الخطأ قد يكون في حقيقة حسابية أو حمل الذاكرة العاملة أو الاستعجال، لذلك لا تختزل الأداء في سرعة الحساب.",
    "estimation": "عرّف نطاق الإجابة المقبول مسبقًا. الهدف تقدير معقول لا حساب دقيق، ويجب أن تعكس المشتتات درجات مختلفة من المعقولية بدل فروق اعتباطية.",
    "mental-rotation": "افصل الدوران الحقيقي عن الانعكاس المرآتي في البدائل. زاوية الدوران وتعقيد الشكل يؤثران في الزمن، لذلك ينبغي تسجيلهما عند تفسير الفروق بين المراحل.",
    "spatial-relations": "تحقق من وضوح المصطلحات الاتجاهية ومن ثبات منظور المشاهد. خطأ اليمين واليسار قد يكون لغويًا أو ناتجًا عن تبدل المنظور لا عن تمثيل مكاني واحد محدد.",
    "trail-switching": "المهمة تجمع البحث البصري والتسلسل والتبديل بين مجموعتين. راقب أخطاء التسلسل وأخطاء الانتقال بصورة منفصلة لأن الزمن الكلي وحده لا يحدد مصدر الصعوبة.",
    "task-switching": "قس تكلفة التحول بمقارنة محاولات التبديل بالتكرار. استمرار تطبيق القاعدة السابقة خطأ مختلف عن نسيان القاعدة الحالية، ويتأثر بوضوح إشارة التحويل.",
    "planning-steps": "يجب أن تكون القيود والهدف واضحين وأن يوجد مسار قابل للتحقق. راقب اختيار خطوة تعيق ما بعدها أو تجاهل قيد، بدل تقييم الخطة على عدد النقرات فقط.",
    "rule-discovery": "سجل الفرضيات التي تختبرها المحاولات والتغذية الراجعة المتاحة. تكرار الاختيار نفسه رغم دليل معاكس يختلف عن بناء فرضية جديدة خاطئة، وكلاهما يحتاج قراءة منفصلة.",
    "priority-planning": "الأولوية تعتمد على الموعد والأثر والاعتماد والموارد، لذلك لا تجعل كل سؤال قائمًا على معيار واحد. إذا تعددت الإجابات المعقولة يجب توضيح الافتراض الذي يجعل أحدها أفضل.",
    "problem-solving": "اعرض المشكلة والقيود والموارد بصورة صريحة. الإجابة الجيدة يجب أن تعالج العائق المحدد، لا أن تكون نصيحة أخلاقية عامة يمكن قبولها في أي موقف.",
    "emotion-recognition": "تعبيرات الانفعال تختلف ثقافيًا وفرديًا، ولا تكشف النية يقينًا. استخدم قرائن واضحة متعددة وتجنب تحويل خطأ في بطاقة مبسطة إلى حكم على التعاطف أو الشخصية.",
    "perspective-taking": "فرّق بين ما يعرفه الشخص وما يعرفه الآخر بناء على المعلومات المتاحة لكل منهما. المهمة لا تقيس التعاطف الأخلاقي ولا صلاحية العلاقات الاجتماعية بصورة عامة.",
    "social-scenarios": "صمّم الموقف بحيث تكون معايير الأمان والاحترام والحدود واضحة، مع الاعتراف بأن أكثر من استجابة قد تكون مناسبة ثقافيًا. لا تُعاقب اختلاف الأسلوب عندما يحقق الهدف بأمان.",
    "context-clues": "حدد القرينة التي تسمح باستنتاج المعنى وتأكد أن بقية البدائل لا تلائم السياق أيضًا. صعوبة القراءة أو المفردات قد تفسر الخطأ أكثر من الاستدلال السياقي.",
    "word-categories": "حدد مستوى الفئة المطلوبة؛ فالكلمة قد تنتمي إلى فئات متعددة. جودة السؤال تعتمد على وجود تصنيف واحد مقصود يمكن شرحه بعد الإجابة.",
    "semantic-fluency": "الأداء يتأثر بالمفردات والتعليم وسرعة الإدخال وألفة الفئة. عند التوليد الحر راقب التكرار والتجمعات الدلالية والتحول بينها، ولا تعامل العدد وحده كدرجة معيارية.",
}

CATEGORY_CONFOUNDERS = {
    "السرعة": "زمن الجهاز، معدل تحديث الشاشة، نوع الإدخال، وضوح المثير، التوقع، والمشتتات المحيطة.",
    "الكبح": "فهم القاعدة، نسبة مثيرات التوقف، الاستعجال، التعب، أثر التدريب، وسرعة عرض المثير.",
    "الذاكرة العاملة": "طول السلسلة، سرعة العرض، استراتيجيات الترديد أو التجميع، اللغة، النوم، والتداخل بين العناصر.",
    "الذاكرة": "الانتباه أثناء الترميز، زمن الاحتفاظ، التشابه بين العناصر، الاستراتيجية، الرؤية أو السمع، وأثر التكرار.",
    "الانتباه": "المشتتات، طول الجلسة، كثافة المثيرات، التباين، التعب، النوم، الدواء، وطريقة إدخال الإجابة.",
    "الاستدلال": "وضوح القاعدة، المفردات والتعليم، وجود أكثر من حل معقول، الخبرة بنمط السؤال، والضغط الزمني.",
    "المرونة": "وضوح إشارة التحويل، نسبة محاولات التبديل، الحمل الحسابي أو اللغوي، التدريب، وسرعة الاستجابة المطلوبة.",
    "القدرات المكانية": "حجم الشاشة، التباين، زاوية العرض، سلامة البصر، دقة اللمس، الخبرة بالأشكال، وفهم المصطلحات الاتجاهية.",
    "الوظائف التنفيذية": "فهم القيود، الذاكرة العاملة، الخبرة بالموقف، الدافعية، الوقت المتاح، وإمكان وجود أكثر من خطة جيدة.",
    "المعالجة الاجتماعية": "الثقافة، اللغة، الخبرة الاجتماعية، وضوح السياق، تعدد الاستجابات المقبولة، وعدم اكتمال القرائن غير اللفظية.",
    "اللغة": "اللهجة، التعليم، القراءة، المفردات، ازدواج المعنى، طول الجملة، وسهولة الإدخال الكتابي أو اللمسي.",
}


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "template"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def words(value: str) -> int:
    parser = VisibleText()
    parser.feed(value)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts)))


def extract_definition(source: str) -> dict:
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', source, re.S)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(1).replace("<\\/", "</"))


def replace_or_insert(source: str, fragment: str) -> str:
    pattern = re.escape(START) + r".*?" + re.escape(END)
    if re.search(pattern, source, re.S):
        return re.sub(pattern, fragment, source, count=1, flags=re.S)
    anchor = "<!-- lab-depth-v32:body:start -->"
    if anchor in source:
        return source.replace(anchor, fragment + anchor, 1)
    if "<footer" in source:
        return source.replace("<footer", fragment + "<footer", 1)
    return source.replace("</main>", fragment + "</main>", 1)


def grouped_items(questions: list[object]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for raw in questions:
        text = raw if isinstance(raw, str) else str((raw or {}).get("text", ""))
        text = " ".join(text.split())
        if not text:
            continue
        domain = text.split(":", 1)[0].strip() if ":" in text else "محور المتابعة"
        groups[domain].append(text)
    return dict(groups)


def monitor_fragment(definition: dict) -> str:
    title = str(definition.get("title") or "أداة المتابعة")
    summary = str(definition.get("summary") or "")
    direction = str(definition.get("monitor_direction") or "")
    policy = str(definition.get("monitor_policy") or "burden_tracking")
    questions = list(definition.get("questions") or [])
    options = list(definition.get("options") or [])
    critical = [index for index in definition.get("critical_item_indices") or [] if isinstance(index, int) and 0 <= index < len(questions)]
    groups = grouped_items(questions)
    cards = []
    for domain, items in groups.items():
        item_html = "".join(f"<li>{esc(item)}</li>" for item in items)
        cards.append(
            f'<section class="lab-specificity-v32__card"><h3>{esc(domain)}</h3><p>اقرأ هذا المحور كسلسلة ملاحظات سلوكية ووظيفية قابلة للمقارنة داخل الشخص نفسه. لا يكفي ارتفاع بند واحد لتفسير السبب؛ راجع متى ظهر، ما الذي سبقه، مقدار الأثر، وما الدعم الذي غيّر النتيجة.</p><ul>{item_html}</ul></section>'
        )
    if policy == "safety_flags":
        policy_text = "هذه الصفحة لا تنتج «درجة أمان». كل بند يتضمن تهديدًا أو إكراهًا أو عنفًا أو تقييدًا للقرار يُقرأ مستقلًا عن بقية البنود وعن أي مجموع حسابي. الأولوية لتقييم الخطر الحالي وخطة الأمان والوصول إلى دعم بشري مناسب."
    elif policy == "readiness_gaps":
        policy_text = "النتيجة هنا خريطة فجوات في جاهزية الخطة. ارتفاعها يعني أن عناصر أكثر من خطة الدعم أو الأمان غير مكتملة أو صعبة الاستخدام؛ لا يعني شدة إدمان، ولا يتنبأ بالانتكاس، ولا يحدد علاجًا أو انسحابًا دوائيًا."
    else:
        policy_text = "المجموع إن عُرض هو وسيلة وصفية لمقارنة سجل الشخص بنفسه عبر ظروف متقاربة. لا توجد لهذه الأداة عتبات خفيف/متوسط/شديد، ولا عينة معيارية، ولا صلاحية لتشخيص حالة أو مقارنة شخص بآخر."
    critical_html = ""
    if critical:
        listed = "".join(f"<li>{esc(questions[index])}</li>" for index in critical)
        critical_html = f'<section class="lab-specificity-v32__card lab-specificity-v32__alert"><h3>بنود لا تنتظر المجموع</h3><p>هذه البنود محددة كإشارات تحتاج مراجعة مستقلة. وجودها لا يثبت تشخيصًا، لكنه يغيّر أولوية القرار لأن السلامة أو الوصول إلى الدعم أهم من النتيجة الكلية.</p><ul>{listed}</ul></section>'
    options_html = "".join(f"<li>{esc(option)}</li>" for option in options)
    return (
        START
        + '<section class="lab-specificity-v32" aria-labelledby="lab-specificity-v32-title">'
        + '<style>.lab-specificity-v32{display:grid;gap:1rem;margin-block:2rem}.lab-specificity-v32__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:1rem}.lab-specificity-v32__card{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}.lab-specificity-v32__alert{border-inline-start:6px solid #9b2c2c;background:#fff7f7}.lab-specificity-v32 li{margin-block:.35rem}</style>'
        + f'<h2 id="lab-specificity-v32-title">قراءة تفصيلية لمحاور {esc(title)}</h2>'
        + f'<section class="lab-specificity-v32__card"><h3>ما الذي تتبعه هذه النسخة تحديدًا؟</h3><p>{esc(summary)}</p><p>{esc(direction)}</p><p>{esc(policy_text)}</p></section>'
        + '<div class="lab-specificity-v32__grid">' + "".join(cards) + '</div>'
        + critical_html
        + f'<section class="lab-specificity-v32__card"><h3>كيف تستخدم بدائل الإجابة دون تضخيم المعنى؟</h3><ul>{options_html}</ul><p>اختر البديل الذي يصف الفترة المحددة، ثم اربط البنود الأعلى بمثال واقعي: موقف، وقت، أثر وظيفي، وما الذي خفف أو زاد الصعوبة. إذا تغيرت ظروف القياس بصورة كبيرة فسجّل ذلك قبل مقارنة الرقم بسجل سابق.</p></section>'
        + '</section>'
        + END
    )


def cognitive_fragment(definition: dict, methods: dict) -> str:
    slug = str(definition.get("slug") or "")
    title = str(definition.get("title") or slug or "المهمة المعرفية")
    category = str(definition.get("category") or definition.get("mode") or "القدرات المعرفية")
    task_method = str(methods["task_methods"].get(slug) or "")
    category_method = str(methods["category_method"].get(category) or "")
    note = TASK_NOTES.get(slug, "")
    confounders = CATEGORY_CONFOUNDERS.get(category, "الجهاز، فهم التعليمات، التعب، النوم، المشتتات، والخبرة السابقة بالمهمة.")
    stages = int(definition.get("stages", 5) or 5)
    trials = int(definition.get("trials_per_stage", 6) or 6)
    return (
        START
        + '<section class="lab-specificity-v32" aria-labelledby="lab-specificity-v32-title">'
        + '<style>.lab-specificity-v32{display:grid;gap:1rem;margin-block:2rem}.lab-specificity-v32__card{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}.lab-specificity-v32 table{width:100%;border-collapse:collapse}.lab-specificity-v32 th,.lab-specificity-v32 td{border:1px solid #cbdedb;padding:.7rem;text-align:start;vertical-align:top}</style>'
        + f'<h2 id="lab-specificity-v32-title">ما الذي يحدث فعليًا في مهمة {esc(title)}؟</h2>'
        + f'<section class="lab-specificity-v32__card"><h3>العملية المستهدفة</h3><p>{esc(category_method)}</p><p><strong>الآلية الخاصة بهذه المهمة:</strong> {esc(task_method)}</p></section>'
        + f'<section class="lab-specificity-v32__card"><h3>قراءة نمط الأداء</h3><p>{esc(note)}</p><p>لا تُحوّل الفرق بين محاولتين إلى صفة ثابتة. راجع موضع الخطأ داخل المرحلة، وهل سبقته زيادة حمل أو تبديل قاعدة أو سلسلة أخطاء، ثم اقرأ الدقة والزمن ونوع الخطأ معًا.</p></section>'
        + f'<section class="lab-specificity-v32__card"><h3>عوامل يجب ضبطها قبل المقارنة</h3><p>{esc(confounders)}</p><p>الجلسة الحالية تتكون من {stages} مراحل وبحد مستهدف {trials} محاولات لكل مرحلة عند الإكمال. أي تغيير في عدد المحاولات أو الجهاز أو طريقة الإدخال أو شروط العرض يحد من قابلية مقارنة الزمن والدقة بجلسة أخرى.</p></section>'
        + '<section class="lab-specificity-v32__card"><h3>ماذا لا تقول النتيجة؟</h3><p>هذه مهمة رقمية تدريبية/وصفية داخل المنصة وليست اختبارًا عصبيًا نفسيًا مقننًا. لا تعطي درجة ذكاء، ولا تحدد تشخيصًا، ولا تستخدم لاتخاذ قرار تعليمي أو وظيفي أو قانوني. التغير المستمر في الأداء اليومي يحتاج سياقًا صحيًا ووظيفيًا وتقييمًا مناسبًا، لا إعادة اللعبة بحثًا عن رقم أفضل.</p></section>'
        + '</section>'
        + END
    )


def render(site: Path) -> dict:
    methods = json.loads(METHODS_PATH.read_text(encoding="utf-8"))
    monitor_rows = []
    cognitive_rows = []
    blocks: list[str] = []

    for path in sorted((site / "assessment-lab").glob("*/index.html")):
        source = path.read_text(encoding="utf-8")
        definition = extract_definition(source)
        if definition.get("score_type") != "monitor":
            continue
        fragment = monitor_fragment(definition)
        updated = replace_or_insert(source, fragment)
        path.write_text(updated, encoding="utf-8")
        groups = grouped_items(list(definition.get("questions") or []))
        row = {
            "slug": definition.get("slug") or path.parent.name,
            "specific_words": words(fragment),
            "items": len(definition.get("questions") or []),
            "domains": len(groups),
            "critical_items": len(definition.get("critical_item_indices") or []),
            "all_items_visible": all(str(item) in fragment for item in definition.get("questions") or []),
        }
        monitor_rows.append(row)
        blocks.append(re.sub(r"\s+", " ", fragment))

    for path in sorted((site / "cognitive-lab").glob("*/index.html")):
        source = path.read_text(encoding="utf-8")
        definition = extract_definition(source)
        slug = str(definition.get("slug") or path.parent.name)
        fragment = cognitive_fragment(definition, methods)
        updated = replace_or_insert(source, fragment)
        path.write_text(updated, encoding="utf-8")
        row = {
            "slug": slug,
            "specific_words": words(fragment),
            "task_method_visible": str(methods["task_methods"].get(slug) or "") in fragment,
            "task_note_present": slug in TASK_NOTES and TASK_NOTES[slug] in fragment,
        }
        cognitive_rows.append(row)
        blocks.append(re.sub(r"\s+", " ", fragment))

    monitor_failures = [row for row in monitor_rows if row["specific_words"] < MIN_MONITOR_SPECIFIC_WORDS or row["items"] != 12 or row["domains"] < 4 or not row["all_items_visible"]]
    cognitive_failures = [row for row in cognitive_rows if row["specific_words"] < MIN_COGNITIVE_SPECIFIC_WORDS or not row["task_method_visible"] or not row["task_note_present"]]
    duplicate_blocks = len(blocks) - len(set(blocks))
    report = {
        "version": 32,
        "status": "passed" if not monitor_failures and not cognitive_failures and duplicate_blocks == 0 and len(monitor_rows) == EXPECTED_MONITORS and len(cognitive_rows) == EXPECTED_COGNITIVE else "failed",
        "monitor_pages": len(monitor_rows),
        "cognitive_pages": len(cognitive_rows),
        "minimum_monitor_specific_words": min((row["specific_words"] for row in monitor_rows), default=0),
        "minimum_cognitive_specific_words": min((row["specific_words"] for row in cognitive_rows), default=0),
        "monitor_failures": monitor_failures,
        "cognitive_failures": cognitive_failures,
        "duplicate_specific_blocks": duplicate_blocks,
        "monitors": monitor_rows,
        "cognitive": cognitive_rows,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-specificity-v32.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise SystemExit(json.dumps(report, ensure_ascii=False)[:12000])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(render(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
