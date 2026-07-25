from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "content" / "v193" / "lab-depth-contract-ar.json"
HEAD_START = "<!-- lab-depth-v193:head:start -->"
HEAD_END = "<!-- lab-depth-v193:head:end -->"
BODY_START = "<!-- lab-depth-v193:body:start -->"
BODY_END = "<!-- lab-depth-v193:body:end -->"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_contract() -> dict:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if data.get("status") != "internally-reviewed":
        raise SystemExit("Lab depth contract must remain internally-reviewed")
    if data.get("risk_level") != "moderate":
        raise SystemExit("Lab depth contract risk level changed unexpectedly")
    return data


def extract_definition(page: str) -> dict:
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Missing lab-definition JSON")
    return json.loads(match.group(1).replace("<\\/", "</"))


def unique_focus(definition: dict) -> list[str]:
    questions = definition.get("questions") or []
    focus: list[str] = []
    for question in questions:
        value = str(question).split(":", 1)[0].strip()
        if value and value not in focus:
            focus.append(value)
        if len(focus) == 6:
            break
    return focus


def source_map(contract: dict) -> dict[str, dict]:
    return {item["id"]: item for item in contract["sources"]}


def select_sources(definition: dict, kind: str, contract: dict) -> list[dict]:
    sources = source_map(contract)
    if kind == "cognitive":
        return [sources["nia-cognitive-health"]]
    score_type = definition.get("score_type")
    mapping = {
        "phq9": ["phq9-validation-2001", "uspstf-depression-screening-2023"],
        "gad7": ["gad7-validation-2006"],
        "who5": ["who5-2024"],
        "audit_guided": ["who-audit-manual"],
    }
    return [sources[item] for item in mapping.get(score_type, [])]


def rich_description(definition: dict, kind: str) -> str:
    title = definition.get("title", "الأداة")
    category = definition.get("category") or definition.get("mode") or "المتابعة"
    if kind == "cognitive":
        return f"{title}: مهمة تدريبية عربية في {category} مع شرح طريقة الاستخدام وحدود النتيجة والعوامل المؤثرة. ليست اختبار ذكاء أو تشخيصًا سريريًا."
    period = definition.get("period", "الفترة المحددة")
    return f"{title}: شرح عربي لطريقة الاستخدام خلال {period} وقراءة النتيجة وحدودها ومتى يلزم الدعم. الأداة لا تقدم تشخيصًا فرديًا."


def faq_schema(title: str, faq: list[list[str]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "name": f"أسئلة شائعة حول {title}",
        "mainEntity": [
            {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
            for question, answer in faq
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def head_fragment(definition: dict, kind: str, contract: dict) -> str:
    title = definition.get("title", "الأداة")
    faq = contract["faq"]["cognitive" if kind == "cognitive" else "assessment"]
    web_page = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": rich_description(definition, kind),
        "inLanguage": "ar",
        "dateModified": contract["reviewed_at"],
        "isPartOf": {"@type": "WebSite", "name": "المنصة الشاملة للصحة النفسية وذوي الاحتياجات الخاصة"},
        "about": definition.get("category") or definition.get("mode") or title,
    }
    return (
        HEAD_START
        + f'<meta name="twitter:title" content="{esc(title)}">'
        + f'<meta name="twitter:description" content="{esc(rich_description(definition, kind))}">'
        + f'<script type="application/ld+json">{json.dumps(web_page, ensure_ascii=False)}</script>'
        + f'<script type="application/ld+json">{faq_schema(title, faq)}</script>'
        + HEAD_END
    )


def list_html(items: list[str]) -> str:
    return "".join(f"<li>{esc(item)}</li>" for item in items)


def source_html(items: list[dict], definition: dict) -> str:
    if not items:
        return (
            '<section class="lab-depth-v193__card"><h2>مصدر الأداة وحدودها</h2>'
            '<p>هذه متابعة ذاتية أصلية غير معيارية. لم تُنسب إلى مقياس سريري، ولا تستخدم عينات معيارية أو حدود تشخيصية.</p>'
            '<p>الفائدة المقصودة هي تنظيم الملاحظة وصياغة أسئلة أفضل للحوار، لا منح صلاحية سريرية غير موجودة.</p></section>'
        )
    links = "".join(
        f'<li><a href="{esc(item["url"])}" rel="noopener">{esc(item["title"])}</a> — {esc(item["publisher"])}، {esc(item["year"])}</li>'
        for item in items
    )
    context = " ".join(item["claims_supported"][0] for item in items)
    return (
        '<section class="lab-depth-v193__card"><h2>المصدر والسياق العلمي</h2>'
        f'<p>{esc(context)} لا يعني ذلك أن التطبيق الرقمي الحالي بديل عن النسخة الأصلية المطبقة مهنيًا أو أنه صالح لكل فئة وسياق.</p>'
        f'<ul>{links}</ul></section>'
    )


def assessment_body(definition: dict, contract: dict, prefix: str) -> str:
    title = definition.get("title", "الأداة")
    period = definition.get("period", "الفترة المحددة")
    focus = unique_focus(definition)
    focus_text = "، ".join(focus) if focus else "البنود الظاهرة في الصفحة"
    is_monitor = definition.get("score_type") == "monitor"
    guidance = contract["monitor_guidance" if is_monitor else "assessment_guidance"]
    faq = contract["faq"]["assessment"]
    safety = ""
    if any("إيذاء النفس" in str(item) or "الموت أفضل" in str(item) for item in definition.get("questions", [])):
        safety = (
            '<aside class="lab-depth-v193__safety" role="note"><h2>تنبيه أمان مهم</h2>'
            '<p>الإجابة عن بند الأمان لا ينبغي أن تبقى رقمًا داخل الصفحة. إذا كانت لديك الآن أفكار بإيذاء نفسك أو لا تستطيع ضمان سلامتك، ابتعد عن الوسائل المؤذية، تواصل فورًا مع شخص موثوق، واستخدم خدمات الطوارئ المحلية أو اذهب إلى أقرب قسم طوارئ.</p></aside>'
        )
    privacy = guidance.get("privacy", "لا تدخل معلومات تعريفية لا تحتاجها، وتحقق من الحفظ والمسح عند استخدام جهاز مشترك.")
    faq_html = "".join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faq)
    return f'''{BODY_START}<section class="lab-depth-v193" aria-labelledby="lab-depth-v193-title"><style>.lab-depth-v193{{margin-top:2rem;display:grid;gap:1rem}}.lab-depth-v193__card,.lab-depth-v193__safety{{padding:1.25rem;border:1px solid #b9ddd8;border-radius:1.25rem;background:#fff;line-height:1.9}}.lab-depth-v193__safety{{border-inline-start:6px solid #9b2c2c;background:#fff7f7}}.lab-depth-v193 h2{{line-height:1.45}}.lab-depth-v193 details{{padding:.8rem 0;border-bottom:1px solid #d9e8e5}}.lab-depth-v193 a{{font-weight:700}}@media print{{.lab-depth-v193__card,.lab-depth-v193__safety{{break-inside:avoid}}}}</style>
<h2 id="lab-depth-v193-title">فهم {esc(title)} قبل الاعتماد على النتيجة</h2>
<section class="lab-depth-v193__card"><h2>ما الذي تعرضه الأداة؟</h2><p>{esc(guidance["purpose"])}</p><p>تركز هذه الصفحة على: <strong>{esc(focus_text)}</strong>. والفترة المطلوبة للإجابة هي <strong>{esc(period)}</strong>؛ تغيير الفترة أو خلط أيام متباعدة قد يغير معنى الإجابة.</p></section>
<section class="lab-depth-v193__card"><h2>طريقة استخدام أكثر دقة</h2><p>{esc(guidance["use"])}</p><ol><li>اقرأ الفترة والتعليمات قبل البدء.</li><li>أجب عن كل بند بحسب خبرتك لا بحسب توقع الآخرين.</li><li>سجل حدثًا أو تغيرًا مهمًا قد يفسر النتيجة.</li><li>احتفظ بالنتيجة للغرض الذي اخترته، ولا تحول المتابعة إلى فحص متكرر بحثًا عن الطمأنة.</li></ol></section>
<section class="lab-depth-v193__card"><h2>كيف تقرأ النتيجة؟</h2><p>{esc(guidance["interpretation"])}</p><p>اسأل بعد الانتهاء: هل ظهر تغير في الوظيفة اليومية؟ هل يتكرر النمط؟ ما العامل الذي سبق التغير؟ وما الدعم الصغير القابل للتنفيذ الآن؟ هذه الأسئلة أكثر فائدة من التعامل مع الرقم كحكم نهائي.</p></section>
<section class="lab-depth-v193__card"><h2>الحدود والعوامل المؤثرة</h2><p>{esc(guidance.get("limits", "الأداة لا تستخدم عينة معيارية ولا تمنح تشخيصًا."))}</p><p>قد تؤثر جودة النوم والمرض الجسدي والألم والأدوية واللغة والبيئة والضغط الحديث وطريقة فهم السؤال. لا يمكن للصفحة وحدها فصل هذه العوامل أو تحديد سبب الأعراض.</p></section>
<section class="lab-depth-v193__card"><h2>الخصوصية والحفظ</h2><p>{esc(privacy)}</p><p>استخدم وصفًا مختصرًا غير معرف للشخص، ولا ترسل صورة النتيجة تلقائيًا. مشاركة السجل قرار واعٍ ينبغي أن يخدم متابعة أو دعمًا محددًا.</p></section>
<section class="lab-depth-v193__card"><h2>متى تنتقل من المتابعة إلى طلب المساعدة؟</h2><p>{esc(guidance["help"])}</p><p>يمكنك إحضار النتيجة إلى موعد مهني مع أمثلة واقعية عن المدة والشدة والأثر وما جربته من دعم. المختص يحتاج القصة والسياق، وليس الرقم وحده.</p></section>{safety}
{source_html(select_sources(definition, "assessment", contract), definition)}
<section class="lab-depth-v193__card"><h2>أسئلة شائعة</h2>{faq_html}</section>
<nav class="lab-depth-v193__card" aria-label="روابط مرتبطة"><h2>تابع من هنا</h2><p><a href="{prefix}assessment-lab/">جميع المقاييس وأدوات المتابعة</a> · <a href="{prefix}cognitive-lab/">الألعاب المعرفية</a> · <a href="{prefix}privacy/">الخصوصية</a> · <a href="{prefix}about/">عن المنصة</a></p></nav></section>{BODY_END}'''


def cognitive_body(definition: dict, contract: dict, prefix: str) -> str:
    title = definition.get("title", "المهمة")
    category = definition.get("category") or definition.get("mode") or "القدرات المعرفية"
    category_text = contract["cognitive_categories"].get(category, f"تقدم المهمة تدريبًا محدودًا في {category} داخل سياق رقمي.")
    guidance = contract["cognitive_guidance"]
    faq = contract["faq"]["cognitive"]
    stages = definition.get("stages", 5)
    trials = definition.get("trials_per_stage", 6)
    faq_html = "".join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faq)
    return f'''{BODY_START}<section class="lab-depth-v193" aria-labelledby="lab-depth-v193-title"><style>.lab-depth-v193{{margin-top:2rem;display:grid;gap:1rem}}.lab-depth-v193__card{{padding:1.25rem;border:1px solid #b9ddd8;border-radius:1.25rem;background:#fff;line-height:1.9}}.lab-depth-v193 h2{{line-height:1.45}}.lab-depth-v193 details{{padding:.8rem 0;border-bottom:1px solid #d9e8e5}}.lab-depth-v193 a{{font-weight:700}}@media print{{.lab-depth-v193__card{{break-inside:avoid}}}}</style>
<h2 id="lab-depth-v193-title">ما الذي تعنيه نتيجة {esc(title)}؟</h2>
<section class="lab-depth-v193__card"><h2>القدرة المستهدفة داخل المهمة</h2><p>{esc(guidance["purpose"])}</p><p><strong>{esc(category_text)}</strong> اسم المهمة يصف النشاط المعروض، ولا يعني أنها تقيس جميع جوانب {esc(category)} أو تحاكي تقييمًا عصبيًا نفسيًا معياريًا.</p></section>
<section class="lab-depth-v193__card"><h2>كيف تعمل الجلسة؟</h2><p>تتكون النسخة الحالية من {esc(stages)} مراحل، وفي كل مرحلة نحو {esc(trials)} محاولات. تزداد المتطلبات تدريجيًا لتدريب فهم القاعدة والاستمرار والتكيف مع المهمة.</p><p>{esc(guidance["use"])}</p></section>
<section class="lab-depth-v193__card"><h2>قراءة السرعة والدقة والأخطاء</h2><p>{esc(guidance["interpretation"])}</p><p>اقرأ السرعة مع الدقة: الاستجابة الأسرع مع أخطاء أكثر ليست بالضرورة أفضل، والتباطؤ المقصود لفهم القاعدة قد يكون استراتيجية مناسبة. سجّل الجهاز والوقت والتعب إذا كنت تقارن جلسات متعددة.</p></section>
<section class="lab-depth-v193__card"><h2>التدريب لا يساوي تشخيصًا أو وعدًا علاجيًا</h2><p>{esc(guidance["training"])}</p><p>المصادر المؤسسية تحذر من مساواة الألعاب التجارية بالدراسات المضبوطة أو تعميم تحسن مهمة واحدة على كل التفكير والذاكرة. لذلك تعرض الصفحة نتيجة تدريبية فقط.</p></section>
<section class="lab-depth-v193__card"><h2>استخدام آمن ومفيد</h2><ul><li>ابدأ بعد فهم التعليمات وليس تحت ضغط السرعة.</li><li>استخدم شاشة وطريقة إدخال مريحتين.</li><li>خذ استراحة عند التعب أو الصداع أو الانزعاج الحسي.</li><li>قارن أداءك بنفسك وفي ظروف متقاربة، لا بأشخاص يستخدمون أجهزة مختلفة.</li><li>لا تستخدم النتيجة لاتخاذ قرار دراسي أو وظيفي أو طبي مصيري.</li></ul></section>
<section class="lab-depth-v193__card"><h2>متى تحتاج تقييمًا أوسع؟</h2><p>{esc(guidance["help"])}</p><p>التقييم المهني يجمع التاريخ الصحي والأدوية والنوم والمزاج واللغة والسمع والبصر والأداء اليومي، وقد يستخدم أدوات معيارية لا توفرها هذه اللعبة.</p></section>
{source_html(select_sources(definition, "cognitive", contract), definition)}
<section class="lab-depth-v193__card"><h2>أسئلة شائعة</h2>{faq_html}</section>
<nav class="lab-depth-v193__card" aria-label="روابط مرتبطة"><h2>تابع من هنا</h2><p><a href="{prefix}cognitive-lab/">جميع الألعاب المعرفية</a> · <a href="{prefix}assessment-lab/">المقاييس والمتابعة</a> · <a href="{prefix}privacy/">الخصوصية</a> · <a href="{prefix}about/">عن المنصة</a></p></nav></section>{BODY_END}'''


def base_prefix(page: str) -> str:
    match = re.search(r'href="([^"]*)manifest\.webmanifest"', page)
    return match.group(1) if match else "/pterminology-site/"


def replace_marked(page: str, start: str, end: str, fragment: str) -> str:
    pattern = re.escape(start) + r".*?" + re.escape(end)
    if re.search(pattern, page, re.S):
        return re.sub(pattern, fragment, page, flags=re.S)
    return page


def enrich_page(path: Path, kind: str, contract: dict) -> None:
    page = path.read_text(encoding="utf-8")
    definition = extract_definition(page)
    description = rich_description(definition, kind)
    page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(description)}">', page, count=1)
    head = head_fragment(definition, kind, contract)
    if HEAD_START in page:
        page = replace_marked(page, HEAD_START, HEAD_END, head)
    else:
        page = page.replace("</head>", head + "</head>", 1)
    prefix = base_prefix(page)
    body = assessment_body(definition, contract, prefix) if kind == "assessment" else cognitive_body(definition, contract, prefix)
    if BODY_START in page:
        page = replace_marked(page, BODY_START, BODY_END, body)
    elif "<footer" in page:
        page = page.replace("<footer", body + "<footer", 1)
    else:
        page = page.replace("</main>", body + "</main>", 1)
    path.write_text(page, encoding="utf-8")


def enrich(site: Path) -> dict:
    contract = load_contract()
    assessment = sorted((site / "assessment-lab").glob("*/index.html"))
    cognitive = sorted((site / "cognitive-lab").glob("*/index.html"))
    for path in assessment:
        enrich_page(path, "assessment", contract)
    for path in cognitive:
        enrich_page(path, "cognitive", contract)
    report = {
        "status": "built-not-published",
        "version": 193,
        "assessment_pages_enriched": len(assessment),
        "cognitive_pages_enriched": len(cognitive),
        "total_pages_enriched": len(assessment) + len(cognitive),
        "minimum_visible_words": contract["scope"]["minimum_visible_words"],
        "review": contract["status"],
        "risk_level": contract["risk_level"],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-depth-v193.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(enrich(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
