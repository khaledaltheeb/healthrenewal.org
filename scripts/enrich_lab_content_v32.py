from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "enrich_lab_content_v193.py"
MARK_START = "<!-- lab-depth-v32:body:start -->"
MARK_END = "<!-- lab-depth-v32:body:end -->"
HEAD_START = "<!-- lab-depth-v32:head:start -->"
HEAD_END = "<!-- lab-depth-v32:head:end -->"
EXPECTED_ASSESSMENTS = 40
EXPECTED_COGNITIVE = 53
MIN_VISIBLE_WORDS = 850

spec = importlib.util.spec_from_file_location("lab_depth_v193", LEGACY)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {LEGACY}")
v193 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v193)


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

    def words(self) -> int:
        return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(self.parts)))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def extract_definition(source: str) -> dict:
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', source, re.S)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(1).replace("<\\/", "</"))


def write_definition(source: str, definition: dict) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return re.sub(
        r'(<script type="application/json" id="lab-definition">).*?(</script>)',
        lambda m: m.group(1) + payload + m.group(2),
        source,
        count=1,
        flags=re.S,
    )


def replace_marked(source: str, start: str, end: str, fragment: str) -> str:
    pattern = re.escape(start) + r".*?" + re.escape(end)
    if re.search(pattern, source, re.S):
        return re.sub(pattern, fragment, source, count=1, flags=re.S)
    return source


def insert_before_footer(source: str, fragment: str) -> str:
    if "<footer" in source:
        return source.replace("<footer", fragment + "<footer", 1)
    if "</main>" in source:
        return source.replace("</main>", fragment + "</main>", 1)
    return source.replace("</body>", fragment + "</body>", 1)


def normalize_definition(definition: dict) -> tuple[dict, list[str]]:
    definition = json.loads(json.dumps(definition, ensure_ascii=False))
    repairs: list[str] = []
    if definition.get("score_type") == "who5":
        options = list(definition.get("options") or [])
        if options and options[0] == "في أي وقت":
            options[0] = "لم أشعر بذلك في أي وقت"
            definition["options"] = options
            repairs.append("who5_arabic_zero_option")
    if definition.get("score_type") == "audit_guided":
        definition["instrument_type"] = "عرض إرشادي غير محسوب بالترميز الرسمي"
        definition["scoring_policy"] = "completion_only"
        repairs.append("audit_completion_only")
    if definition.get("score_type") == "monitor":
        definition["instrument_type"] = "أداة متابعة ذاتية أصلية غير معيارية"
        definition["scoring_policy"] = "descriptive_tracking_only"
    return definition, repairs


METHODS = json.loads((ROOT / "content" / "v32" / "lab-methods-ar.json").read_text(encoding="utf-8"))
OFFICIAL = METHODS["official"]
CATEGORY_METHOD = METHODS["category_method"]
TASK_METHODS = METHODS["task_methods"]


def source_links(score_type: str) -> str:
    links = {
        "phq9": [("دراسة صلاحية PHQ-9", "https://pubmed.ncbi.nlm.nih.gov/11556941/"), ("توصية USPSTF للفحص والمتابعة", "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-depression-suicide-risk-adults")],
        "gad7": [("دراسة تطوير GAD-7", "https://pubmed.ncbi.nlm.nih.gov/16717171/")],
        "who5": [("WHO-5 — منظمة الصحة العالمية 2024", "https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01")],
        "audit_guided": [("دليل AUDIT — منظمة الصحة العالمية", "https://www.who.int/publications/i/item/WHO-MSD-MSB-01.6a")],
    }
    return "".join(f'<li><a href="{esc(url)}" rel="noopener">{esc(label)}</a></li>' for label, url in links.get(score_type, []))


def assessment_fragment(definition: dict) -> str:
    score_type = str(definition.get("score_type") or "monitor")
    questions = definition.get("questions") or []
    options = definition.get("options") or []
    title = definition.get("title") or "الأداة"
    period = definition.get("period") or "الفترة المحددة"
    if score_type in OFFICIAL:
        profile = OFFICIAL[score_type]
        links = source_links(score_type)
        return f'''{MARK_START}<section class="lab-depth-v32" aria-labelledby="lab-depth-v32-title">
<style>.lab-depth-v32{{display:grid;gap:1rem;margin-block:2rem}}.lab-depth-v32__card{{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}}.lab-depth-v32 table{{width:100%;border-collapse:collapse}}.lab-depth-v32 th,.lab-depth-v32 td{{border:1px solid #cbdedb;padding:.65rem;text-align:start;vertical-align:top}}.lab-depth-v32 .method-warning{{border-inline-start:6px solid #9b2c2c;background:#fff7f7}}.lab-engine button,.lab-engine .choice-button,.lab-engine label{{min-height:44px}}@media print{{.lab-depth-v32__card{{break-inside:avoid}}}}</style>
<h2 id="lab-depth-v32-title">المنهج العلمي والتطبيقي لـ{esc(title)}</h2>
<section class="lab-depth-v32__card"><h3>بنية الأداة وما الذي تحسبه</h3><p>{esc(profile['architecture'])}</p><table><tbody><tr><th>عدد البنود</th><td>{len(questions)}</td></tr><tr><th>فترة الإجابة</th><td>{esc(period)}</td></tr><tr><th>بدائل كل بند في النسخة الحالية</th><td>{esc('، '.join(map(str, options)))}</td></tr><tr><th>سياسة النتيجة</th><td>{'حساب موثق مع حدود تفسيرية حذرة' if score_type != 'audit_guided' else 'إكمال وصفي فقط؛ لا درجة AUDIT رسمية'}</td></tr></tbody></table></section>
<section class="lab-depth-v32__card"><h3>الحساب والتفسير الصحيح</h3><p>{esc(profile['scoring'])}</p><p>يجب فحص اكتمال جميع البنود قبل النتيجة، وإظهار الدرجة الخام واتجاهها وفترة القياس. لا يجوز تحويل النسبة المئوية تلقائيًا إلى تشخيص أو خطة علاج، ولا مقارنة النتيجة بمعايير سكانية لم تُستخدم في هذه النسخة العربية الرقمية.</p></section>
<section class="lab-depth-v32__card"><h3>ما الذي لا تثبته النتيجة؟</h3><p>{esc(profile['limits'])}</p><p>التفسير المهني يجمع التاريخ، بداية الأعراض ومسارها، التعطل اليومي، الحالة الجسدية، الأدوية والمواد، النوم، الضغوط، والفحص السريري. اختلاف صياغة الترجمة أو طريقة العرض قد يغير قابلية المقارنة بالدراسة الأصلية.</p></section>
<section class="lab-depth-v32__card method-warning"><h3>السلامة والتصعيد</h3><p>{esc(profile['safety'])}</p><p>عند خطر فوري لا تنتظر اكتمال المقياس ولا تستخدم النتيجة كبديل عن الاتصال بشخص موثوق أو مختص أو خدمات الطوارئ المحلية.</p></section>
<section class="lab-depth-v32__card"><h3>بروتوكول متابعة قابل للمقارنة</h3><ol><li>استخدم الفترة الزمنية الأصلية نفسها في كل تطبيق.</li><li>سجل التاريخ والحدث الضاغط والنوم والمرض أو تغير الدواء دون معلومات تعريفية زائدة.</li><li>قارن الاتجاه عبر أكثر من نقطة زمنية، لا تغيرًا منفردًا صغيرًا.</li><li>اربط الرقم بأمثلة وظيفية: العمل أو الدراسة، العلاقات، العناية بالنفس، والنوم.</li><li>ناقش التغير الكبير أو الخطر أو التعطل المستمر مع مختص.</li></ol></section>
<section class="lab-depth-v32__card"><h3>المراجع التي تسند طريقة القراءة</h3><p>{esc(profile['source'])}</p><ul>{links}</ul></section></section>{MARK_END}'''

    domains: list[str] = []
    for question in questions:
        text = question if isinstance(question, str) else str(question.get("text", ""))
        domain = text.split(":", 1)[0].strip()
        if domain and domain not in domains:
            domains.append(domain)
    max_per_item = max(0, len(options) - 1)
    maximum = len(questions) * max_per_item
    rows = "".join(
        f"<tr><th>{esc(domain)}</th><td>راجع الصعوبة أو الأثر، مقدار الدعم المطلوب، واتجاه التغير في هذا المحور، ثم اربطه بمثال واقعي قابل للملاحظة.</td></tr>"
        for domain in domains
    )
    return f'''{MARK_START}<section class="lab-depth-v32" aria-labelledby="lab-depth-v32-title">
<style>.lab-depth-v32{{display:grid;gap:1rem;margin-block:2rem}}.lab-depth-v32__card{{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}}.lab-depth-v32 table{{width:100%;border-collapse:collapse}}.lab-depth-v32 th,.lab-depth-v32 td{{border:1px solid #cbdedb;padding:.65rem;text-align:start;vertical-align:top}}.lab-engine button,.lab-engine .choice-button,.lab-engine label{{min-height:44px}}@media print{{.lab-depth-v32__card{{break-inside:avoid}}}}</style>
<h2 id="lab-depth-v32-title">منهج استخدام {esc(title)} كمتابعة ذاتية</h2>
<section class="lab-depth-v32__card"><h3>نوع الأداة وحدودها</h3><p>هذه أداة متابعة أصلية غير معيارية، وليست مقياسًا سريريًا منشورًا أو اختبارًا ذا نقاط قطع. تتكون من {len(questions)} بندًا تغطي {len(domains)} محاور خلال {esc(period)}. كل بند يُسجل من 0 إلى {max_per_item} وفق بدائل الصفحة، ويكون المجال الحسابي الخام 0–{maximum}.</p><p>تحويل الخام إلى نسبة يسهل مقارنة سجلات الشخص نفسه فقط. لا توجد فئات «خفيف» أو «متوسط» أو «شديد» صالحة لهذه الأداة، ولا يجوز مقارنة النسبة بأشخاص آخرين أو استخدامها لقبول خدمة أو رفضها.</p></section>
<section class="lab-depth-v32__card"><h3>مصفوفة المحاور وما الذي تبحث عنه</h3><table><tbody>{rows}</tbody></table></section>
<section class="lab-depth-v32__card"><h3>كيف تحلل السجل بدل مطاردة رقم؟</h3><ol><li>استخرج المحور الأعلى تكرارًا وحدد السلوك أو الموقف الذي يوضحه.</li><li>افصل بين الشدة، التكرار، والمدة؛ فالرقم نفسه قد يخفي أنماطًا مختلفة.</li><li>ابحث عن سوابق قابلة للتعديل: نوم، ألم، حمل حسي، غموض مهمة، صراع، نقص دعم، أو تغير روتين.</li><li>سجل الموارد التي خففت الصعوبة، لا المشكلات فقط.</li><li>اختر تعديلًا واحدًا قابلًا للقياس للأسبوع التالي ثم راجع أثره.</li></ol></section>
<section class="lab-depth-v32__card"><h3>منع التفسير الخاطئ</h3><p>لا يعني الارتفاع وجود اضطراب بعينه، ولا يعني الانخفاض غياب الحاجة. بعض المحاور قد تكون أهم للسلامة أو الوظيفة حتى لو كان مجموعها قليلًا. الألم والمرض والدواء والحرمان من النوم والبيئة غير الملائمة يجب فحصها قبل إرجاع التغير إلى سبب نفسي.</p><p>التسجيل المتكرر بصورة قهرية قد يزيد القلق؛ استخدم موعدًا ثابتًا مناسبًا وغرضًا واضحًا، وتوقف عن القياس عندما لا يضيف قرارًا أو فهمًا.</p></section>
<section class="lab-depth-v32__card"><h3>متى يصبح الدعم البشري أولوية؟</h3><p>انتقل من المتابعة الذاتية إلى تقييم مناسب عندما يستمر التدهور، يتعطل النوم أو العمل أو الدراسة أو العناية بالنفس، تظهر إساءة أو استغلال أو خطر، أو تصبح الأسرة غير قادرة على تلبية الاحتياجات بأمان. أحضر أمثلة وتواريخ وتغيرات بيئية بدل الاكتفاء بصورة النتيجة.</p></section></section>{MARK_END}'''


def cognitive_fragment(definition: dict) -> str:
    slug = str(definition.get("slug") or "")
    title = definition.get("title") or "المهمة"
    category = str(definition.get("category") or definition.get("mode") or "القدرات المعرفية")
    stages = int(definition.get("stages", 5) or 5)
    trials = int(definition.get("trials_per_stage", 6) or 6)
    task = TASK_METHODS.get(slug, f"تطبيق قاعدة محددة في {category} عبر محاولات متدرجة، مع ضرورة التحقق من أن لكل محاولة جوابًا واحدًا قابلًا للحل.")
    category_method = CATEGORY_METHOD.get(category, f"تصف المهمة أداءً محدودًا داخل نشاط رقمي في {category} ولا تمثل تقييمًا معياريًا.")
    return f'''{MARK_START}<section class="lab-depth-v32" aria-labelledby="lab-depth-v32-title">
<style>.lab-depth-v32{{display:grid;gap:1rem;margin-block:2rem}}.lab-depth-v32__card{{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}}.lab-depth-v32 table{{width:100%;border-collapse:collapse}}.lab-depth-v32 th,.lab-depth-v32 td{{border:1px solid #cbdedb;padding:.65rem;text-align:start;vertical-align:top}}.lab-engine button,.lab-engine .choice-button,.lab-engine label{{min-height:44px}}@media print{{.lab-depth-v32__card{{break-inside:avoid}}}}</style>
<h2 id="lab-depth-v32-title">المنهج التجريبي لمهمة {esc(title)}</h2>
<section class="lab-depth-v32__card"><h3>العملية المستهدفة داخل هذه المهمة</h3><p>{esc(category_method)}</p><p><strong>البنية الخاصة هنا:</strong> {esc(task)}</p><p>تتكون الجلسة من {stages} مراحل × {trials} محاولات، أي {stages * trials} محاولة عند الإكمال. زيادة المرحلة ينبغي أن تغير حملًا محددًا مثل طول السلسلة أو عدد المشتتات أو تبدل القاعدة، لا أن تكرر السؤال نفسه بصياغة شكلية.</p></section>
<section class="lab-depth-v32__card"><h3>عقد صلاحية كل محاولة</h3><ol><li>المثير والتعليمات ظاهران وقابلان للفهم قبل الإجابة.</li><li>يوجد جواب صحيح واحد فقط داخل البدائل.</li><li>لا توجد بدائل مكررة بعد التطبيع، ولا قيم فارغة أو NaN أو undefined.</li><li>المشتتات معقولة لكنها خاطئة بسبب قاعدة واضحة، لا بسبب غموض لغوي.</li><li>التغذية الراجعة تشرح القاعدة أو الجواب ولا تكتفي بعبارة «خطأ».</li></ol></section>
<section class="lab-depth-v32__card"><h3>كيف تُحسب مؤشرات الجلسة؟</h3><table><tbody><tr><th>الدقة</th><td>عدد الإجابات الصحيحة ÷ عدد المحاولات المكتملة × 100.</td></tr><tr><th>الزمن الوسيط</th><td>وسيط الأزمنة الصحيحة تقنيًا بعد استبعاد القيم غير الرقمية أو السالبة؛ الوسيط أقل تأثرًا بمحاولة بطيئة جدًا من المتوسط.</td></tr><tr><th>المؤشر المركب</th><td>في النسخة الحالية: 70% من الدقة و30% من مكوّن سرعة مُطبع مقابل 1200 مللي ثانية. هذه صيغة منتج داخلية غير مقننة، وليست درجة ذكاء أو معيارًا عصبيًا نفسيًا.</td></tr><tr><th>المرحلة</th><td>تعكس موضع الصعوبة داخل هذه الجلسة فقط، ولا تعادل مستوى عمريًا أو تعليميًا.</td></tr></tbody></table></section>
<section class="lab-depth-v32__card"><h3>تحليل الأخطاء بصورة مفيدة</h3><p>لا تجمع كل الأخطاء في معنى واحد. صنّفها إلى: سوء فهم قاعدة، استجابة اندفاعية، إغفال، خلط ترتيب، فقد عنصر، استمرار على قاعدة سابقة، أو تخمين. راجع هل ظهرت الأخطاء في البداية قبل فهم المهمة، أم لاحقًا مع التعب، أم عند ارتفاع الحمل فقط.</p><p>اقرأ السرعة مع الدقة. سرعة أعلى مع أخطاء أكثر قد تعكس مبادلة سرعة–دقة، بينما التباطؤ مع تحسن الدقة قد يكون استراتيجية مقصودة لا تراجعًا.</p></section>
<section class="lab-depth-v32__card"><h3>بروتوكول مقارنة جلستين</h3><ol><li>استخدم الجهاز وطريقة الإدخال وحجم الشاشة نفسها قدر الإمكان.</li><li>ثبت مستوى الصوت والإضاءة والمشتتات ووقت اليوم.</li><li>سجل النوم والتعب والألم والأدوية والقلق والخبرة السابقة بالمهمة.</li><li>لا تكرر الجلسة فورًا بحثًا عن نتيجة أفضل؛ أثر الممارسة قد يرفع الأداء داخل المهمة.</li><li>قارن الدقة والأخطاء والزمن معًا، ولا تستنتج انتقال التحسن إلى الدراسة أو العمل دون دليل مستقل.</li></ol></section>
<section class="lab-depth-v32__card"><h3>الحدود السريرية والأخلاقية</h3><p>المهمة لا تشخص ضعفًا معرفيًا، ولا تقيس الذكاء العام، ولا تثبت اضطرابًا عصبيًا أو نفسيًا. لا تستخدم النتيجة لاتخاذ قرار تعليمي أو وظيفي أو أهلي أو قانوني. التغير الجديد والمستمر في الذاكرة أو اللغة أو الانتباه أو الأداء اليومي يحتاج تاريخًا صحيًا وفحصًا للسمع والبصر والنوم والمزاج والأدوية وتقييمًا مهنيًا مناسبًا.</p></section></section>{MARK_END}'''


def head_fragment(definition: dict, kind: str) -> str:
    title = str(definition.get("title") or "الأداة")
    score_type = str(definition.get("score_type") or "")
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "inLanguage": "ar",
        "dateModified": "2026-08-07",
        "about": definition.get("category") or definition.get("mode") or title,
        "educationalUse": "التثقيف والمتابعة" if kind == "assessment" else "التدريب المعرفي داخل الجلسة",
        "isBasedOn": [url for _, url in {
            "phq9": [("", "https://pubmed.ncbi.nlm.nih.gov/11556941/")],
            "gad7": [("", "https://pubmed.ncbi.nlm.nih.gov/16717171/")],
            "who5": [("", "https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01")],
            "audit_guided": [("", "https://www.who.int/publications/i/item/WHO-MSD-MSB-01.6a")],
        }.get(score_type, [])],
    }
    return HEAD_START + f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>' + HEAD_END


def enrich_page(path: Path, kind: str) -> dict:
    source = path.read_text(encoding="utf-8")
    definition = extract_definition(source)
    definition, repairs = normalize_definition(definition)
    source = write_definition(source, definition)
    head = head_fragment(definition, kind)
    if HEAD_START in source:
        source = replace_marked(source, HEAD_START, HEAD_END, head)
    else:
        source = source.replace("</head>", head + "</head>", 1)
    fragment = assessment_fragment(definition) if kind == "assessment" else cognitive_fragment(definition)
    if MARK_START in source:
        source = replace_marked(source, MARK_START, MARK_END, fragment)
    else:
        source = insert_before_footer(source, fragment)
    path.write_text(source, encoding="utf-8")
    parser = VisibleText()
    parser.feed(source)
    return {
        "path": path.as_posix(),
        "kind": kind,
        "slug": definition.get("slug"),
        "title": definition.get("title"),
        "score_type": definition.get("score_type"),
        "words": parser.words(),
        "repairs": repairs,
        "task_profile": kind == "assessment" or definition.get("slug") in TASK_METHODS,
    }


def enrich(site: Path) -> dict:
    legacy = v193.enrich(site)
    assessment = sorted((site / "assessment-lab").glob("*/index.html"))
    cognitive = sorted((site / "cognitive-lab").glob("*/index.html"))
    if len(assessment) != EXPECTED_ASSESSMENTS or len(cognitive) != EXPECTED_COGNITIVE:
        raise SystemExit({"assessment": len(assessment), "cognitive": len(cognitive), "expected": [EXPECTED_ASSESSMENTS, EXPECTED_COGNITIVE]})
    rows = [enrich_page(path, "assessment") for path in assessment]
    rows += [enrich_page(path, "cognitive") for path in cognitive]
    low = [row for row in rows if row["words"] < MIN_VISIBLE_WORDS]
    missing_profiles = [row for row in rows if not row["task_profile"]]
    score_types = {str(row["score_type"] or "") for row in rows if row["kind"] == "assessment"}
    unexpected_scales = sorted(score_types - {"phq9", "gad7", "who5", "audit_guided", "monitor"})
    report = {
        "version": 32,
        "status": "passed" if not low and not missing_profiles and not unexpected_scales else "failed",
        "assessment_pages": len(assessment),
        "cognitive_pages": len(cognitive),
        "total_tools": len(rows),
        "minimum_required_words": MIN_VISIBLE_WORDS,
        "minimum_actual_words": min(row["words"] for row in rows),
        "median_words": sorted(row["words"] for row in rows)[len(rows) // 2],
        "pages_below_depth": low,
        "missing_task_profiles": missing_profiles,
        "unexpected_score_types": unexpected_scales,
        "official_scales": sorted(score_types & set(OFFICIAL)),
        "descriptive_monitoring_only": True,
        "audit_official_score_disabled": True,
        "who5_arabic_zero_option_repaired": any("who5_arabic_zero_option" in row["repairs"] for row in rows),
        "legacy_depth_report": legacy,
        "tools": rows,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-depth-v32.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise SystemExit(json.dumps(report, ensure_ascii=False)[:8000])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(enrich(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
