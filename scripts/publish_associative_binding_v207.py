from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
ROOT = SITE / "cognitive-lab"
JS = SITE / "assets/js/lab-v12.js"
SLUG = "associative-context-binding"
TITLE = "ذاكرة الربط بين العنصر والسياق"
CATEGORY = "الذاكرة الترابطية"
SUMMARY = "مهمة تدريبية غير تشخيصية لتذكر الروابط بين عناصر وسياقات أو مواقع، بخيارات متعددة وخمسة مستويات متدرجة للأطفال والبالغين."
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
CANONICAL = BASE + "cognitive-lab/" + SLUG + "/"
TODAY = date.today().isoformat()


def definition() -> dict:
    return {
        "slug": SLUG,
        "title": TITLE,
        "category": CATEGORY,
        "summary": SUMMARY,
        "mode": "associative_context_binding",
        "stages": 5,
        "trials_per_stage": 10,
        "instructions": "احفظ الروابط التي تظهر أولًا، ثم اختر السياق المرتبط بالعنصر أو العنصر المرتبط بالسياق بعد اختفاء القائمة.",
        "answer_mode": "multiple-choice",
        "question_pool_version": 207,
        "difficulty_levels": ["تمهيدي", "أساسي", "متوسط", "متقدم", "تحدٍ مرتفع"],
        "session_randomization": True,
        "repeat_guard": True,
        "audience": ["الأطفال بإشراف بالغ", "المراهقون", "البالغون"],
        "clinical_status": "training-only-not-diagnostic",
        "evidence_note": "تدرب المهمة على ربط عنصر بسياق محدد واسترجاع الاقتران الصحيح. لا تعادل مقياسًا معياريًا للذاكرة الترابطية، ولا تمثل تشخيصًا أو درجة ذكاء.",
        "version": 207,
    }


def template() -> tuple[Path, dict]:
    preferred = ROOT / "prospective-memory-cues" / "index.html"
    candidates = [preferred] + sorted(ROOT.glob("*/index.html"))
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', text, re.S)
        if match:
            return path, json.loads(match.group(1))
    raise SystemExit("No cognitive template found")


def publish_page() -> tuple[str, dict]:
    target = ROOT / SLUG / "index.html"
    data = definition()
    source_path, source = template()
    source_slug = str(source.get("slug") or source_path.parent.name)
    text = source_path.read_text(encoding="utf-8")
    text = text.replace(f"/cognitive-lab/{source_slug}/", f"/cognitive-lab/{SLUG}/")
    text = text.replace(source_slug, SLUG)
    for old, new in (
        (str(source.get("title", "")), TITLE),
        (str(source.get("summary", "")), SUMMARY),
        (str(source.get("category", "")), CATEGORY),
    ):
        if old:
            text = text.replace(old, new)
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', text, re.S)
    if not match:
        raise SystemExit("Template definition missing")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    text = text[: match.start(1)] + payload + text[match.end(1) :]
    description = html.escape(SUMMARY, quote=True)
    text = re.sub(r'<title>.*?</title>', f'<title>{TITLE} | مصطلحات علم النفس</title>', text, count=1, flags=re.S)
    for pattern, replacement in (
        (r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{description}">'),
        (r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{TITLE}">'),
        (r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{description}">'),
        (r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{CANONICAL}">'),
        (r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{CANONICAL}">'),
    ):
        text = re.sub(pattern, replacement, text, count=1)
    if '<meta name="twitter:title"' in text:
        text = re.sub(r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{TITLE}">', text, count=1)
    else:
        text = text.replace("</head>", f'<meta name="twitter:title" content="{TITLE}"></head>', 1)
    if '<meta name="twitter:description"' in text:
        text = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{description}">', text, count=1)
    else:
        text = text.replace("</head>", f'<meta name="twitter:description" content="{description}"></head>', 1)
    text = re.sub(r'<section class="cognitive-bank-v202"[^>]*>.*?</section>', "", text, count=1, flags=re.S)
    note = (
        '<section class="cognitive-bank-v202" data-associative-binding-v207 role="note">'
        '<h2>ما الذي تتدرب عليه؟</h2>'
        '<p>تذكر العنصر وحده لا يكفي هنا؛ المطلوب حفظ الرابط بين العنصر وسياقه ثم استرجاع الاقتران الصحيح بعد اختفاء القائمة. تبدأ المهمة برابطين واضحين للأطفال ثم ترتفع تدريجيًا إلى ستة روابط واتجاهي سؤال مختلفين.</p>'
        '<p><strong>حدود الاستخدام:</strong> هذه مهمة تدريبية غير تشخيصية، وليست اختبار IQ أو مقياسًا معياريًا للذاكرة. الأداء قد يتأثر بالعمر والانتباه والخبرة وطريقة العرض والجهاز.</p>'
        '<h2>الأساس العلمي</h2>'
        '<p>تفرق أبحاث الذاكرة بين تذكر العنصر وتذكر ارتباطه بسياق مثل المكان أو اللون أو المصدر. يتطور هذا الربط خلال الطفولة، وقد يختلف عبر مراحل العمر، لذلك لا تُقارن النتيجة بمعايير سريرية غير متوفرة هنا.</p>'
        '<ul><li><a href="https://pubmed.ncbi.nlm.nih.gov/24660802/" rel="noopener noreferrer">بحث عن ربط العنصر بالسياق عبر مراحل العمر</a></li>'
        '<li><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC3784827/" rel="noopener noreferrer">مسارات تطور الذاكرة الترابطية من الطفولة إلى البلوغ</a></li>'
        '<li><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10219367/" rel="noopener noreferrer">ذاكرة العناصر وروابط العنصر باللون لدى الأطفال والبالغين</a></li></ul>'
        '</section>'
    )
    text = text.replace('<div data-v12-lab="cognitive"', note + '<div data-v12-lab="cognitive"', 1)
    schema = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": TITLE,
        "description": SUMMARY,
        "url": CANONICAL,
        "inLanguage": "ar",
        "educationalUse": "practice",
        "learningResourceType": "interactive associative item-context memory task",
        "dateModified": TODAY,
        "isAccessibleForFree": True,
        "audience": {"@type": "EducationalAudience", "educationalRole": "learner"},
    }
    text = re.sub(r'<script type="application/ld\+json" data-(?:working-memory-v205|prospective-memory-v206)>.*?</script>', "", text, flags=re.S)
    text = text.replace(
        "</head>",
        '<script type="application/ld+json" data-associative-binding-v207>'
        + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
        + "</script></head>",
        1,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return source_slug, source


def patch_runtime() -> None:
    text = JS.read_text(encoding="utf-8")
    branch = r''' if(mode==='associative_context_binding'){const items=[['مفتاح','🔑'],['كتاب','📘'],['قلم','✏️'],['ساعة','⌚'],['مظلة','☂️'],['كرة','⚽'],['مصباح','💡'],['كوب','🥤'],['جرس','🔔'],['خريطة','🗺️'],['حقيبة','🎒'],['مقص','✂️'],['نظارة','👓'],['هاتف','📱'],['تفاحة','🍎'],['زهرة','🌼']],contexts=[['الحديقة','🌳'],['المكتبة','📚'],['المطبخ','🍽️'],['الصف','🏫'],['الشاطئ','🏖️'],['المتجر','🏪'],['المحطة','🚉'],['العيادة','🏥'],['المسرح','🎭'],['المزرعة','🚜'],['الملعب','🏟️'],['المتحف','🏛️'],['المنزل','🏠'],['المختبر','🔬'],['المكتب','🗄️'],['المرسم','🎨']],pairCount=2+stage,chosenItems=shuffle(items,rnd).slice(0,pairCount),chosenContexts=shuffle(contexts,rnd).slice(0,pairCount),pairs=chosenItems.map((item,i)=>({item,context:chosenContexts[i]})),target=pick(pairs),reverse=rnd()>.5,answer=reverse?target.item[0]:target.context[0],sameKind=reverse?pairs.filter(x=>x!==target).map(x=>x.item[0]):pairs.filter(x=>x!==target).map(x=>x.context[0]),pool=reverse?items.map(x=>x[0]):contexts.map(x=>x[0]),distractors=shuffle(unique([...sameKind,...pool.filter(x=>x!==answer&&!sameKind.includes(x))]),rnd).slice(0,3),study=`<div data-binding-set-size="${pairCount}"><strong>احفظ الروابط:</strong> ${pairs.map(x=>`${x.item[0]} ${x.item[1]} ↔ ${x.context[0]} ${x.context[1]}`).join('؛ ')}</div>`,prompt=reverse?`أي عنصر كان مرتبطًا بسياق ${target.context[0]} ${target.context[1]}؟`:`في أي سياق ظهر ${target.item[0]} ${target.item[1]}؟`;return v202Finish(d,stage,rnd,{prompt,study,studyMs:Math.max(3000,5200-stage*550),answer,options:[answer,...distractors],bindingSetSize:pairCount,bindingDirection:reverse?'context-to-item':'item-to-context',explanation:`الرابط الصحيح هو ${target.item[0]} ↔ ${target.context[0]}.`})}
'''
    marker = " const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"
    if "mode==='associative_context_binding'" not in text:
        if marker not in text:
            raise SystemExit("Runtime fallback marker missing")
        text = text.replace(marker, branch + marker, 1)
    JS.write_text(text, encoding="utf-8")


def patch_index(source_slug: str, source: dict) -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    if f"/{SLUG}/" in text:
        return
    pattern = rf'(<a class="lab-v12__card" href="[^"]*{re.escape(source_slug)}/".*?</a>)'
    match = re.search(pattern, text, re.S)
    if not match:
        raise SystemExit("Cognitive index card template missing")
    card = match.group(1).replace(source_slug, SLUG)
    for old, new in (
        (str(source.get("title", "")), TITLE),
        (str(source.get("summary", "")), SUMMARY),
        (str(source.get("category", "")), CATEGORY),
    ):
        if old:
            card = card.replace(old, new)
    path.write_text(text[: match.end()] + card + text[match.end() :], encoding="utf-8")


def patch_sitemap(source_slug: str) -> str:
    source_url = BASE + "cognitive-lab/" + source_slug + "/"
    for path in sorted(SITE.glob("sitemap*.xml")):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
        if source_url not in urls:
            continue
        if CANONICAL not in urls:
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = CANONICAL
            ET.SubElement(node, "lastmod").text = TODAY
            ET.SubElement(node, "changefreq").text = "monthly"
            ET.SubElement(node, "priority").text = "0.80"
            tree.write(path, encoding="utf-8", xml_declaration=True)
        check = [(node.text or "").strip() for node in ET.parse(path).getroot().findall("{*}url/{*}loc")]
        if check.count(CANONICAL) != 1:
            raise SystemExit("Associative-binding sitemap entry must exist exactly once")
        return path.name
    raise SystemExit("No cognitive sitemap containing template route found")


def synchronize_reports() -> None:
    complete = SITE / "api/cognitive-complete-v24.json"
    if complete.exists():
        data = json.loads(complete.read_text(encoding="utf-8"))
        data["completed"] = 51
        data["remaining"] = 0
        data["associative_binding_v207"] = True
        slugs = list(data.get("slugs", []))
        if SLUG not in slugs:
            slugs.append(SLUG)
        data["slugs"] = slugs
        complete.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify() -> dict:
    pages = sorted(ROOT.glob("*/index.html"))
    if len(pages) != 51:
        raise SystemExit(f"Expected 51 cognitive pages after v207, found {len(pages)}")
    text = (ROOT / SLUG / "index.html").read_text(encoding="utf-8")
    required = [
        TITLE,
        CANONICAL,
        '"mode":"associative_context_binding"',
        '"trials_per_stage":10',
        'data-associative-binding-v207',
        'application/ld+json',
        'ليست اختبار IQ',
        'training-only-not-diagnostic',
        'pubmed.ncbi.nlm.nih.gov/24660802',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Associative-binding page missing markers: {missing}")
    return {
        "version": 207,
        "cognitive_pages": 51,
        "total_lab_tools": 91,
        "slug": SLUG,
        "multiple_choice": True,
        "levels": 5,
        "trials": 50,
        "diagnostic": False,
        "standardized_measure": False,
        "minimum_pairs": 2,
        "maximum_pairs": 6,
        "bidirectional_retrieval": True,
        "study_then_test": True,
        "item_context_pool": 256,
    }


def main() -> None:
    source_slug, source = publish_page()
    patch_runtime()
    patch_index(source_slug, source)
    sitemap = patch_sitemap(source_slug)
    synchronize_reports()
    report = {**verify(), "sitemap": sitemap, "status": "built-not-published"}
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "associative-binding-v207.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
