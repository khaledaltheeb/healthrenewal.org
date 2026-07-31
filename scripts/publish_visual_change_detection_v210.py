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
SLUG = "visual-change-detection"
TITLE = "تحديد التغير في الذاكرة البصرية"
CATEGORY = "الذاكرة البصرية العاملة"
SUMMARY = "مهمة تدريبية غير تشخيصية لمقارنة عرضين بصريين وتحديد موضع التغير، بخيارات متعددة وخمسة مستويات متدرجة للأطفال والبالغين."
BASE = "https://healthrenewal.org/"
CANONICAL = BASE + "cognitive-lab/" + SLUG + "/"
TODAY = date.today().isoformat()


def definition() -> dict:
    return {
        "slug": SLUG,
        "title": TITLE,
        "category": CATEGORY,
        "summary": SUMMARY,
        "mode": "visual_change_detection",
        "stages": 5,
        "trials_per_stage": 10,
        "instructions": "احفظ العرض البصري الأول، ثم بعد اختفائه قارن العرض الثاني وحدد الخانة التي تغير لونها أو شكلها.",
        "answer_mode": "multiple-choice",
        "question_pool_version": 210,
        "difficulty_levels": ["تمهيدي", "أساسي", "متوسط", "متقدم", "تحدٍ مرتفع"],
        "session_randomization": True,
        "repeat_guard": True,
        "audience": ["الأطفال بإشراف بالغ", "المراهقون", "البالغون"],
        "clinical_status": "training-only-not-diagnostic",
        "evidence_note": "تدرب المهمة على الاحتفاظ المؤقت بخصائص بصرية ومقارنتها بعد فاصل قصير. لا تعادل مقياسًا معياريًا لسعة الذاكرة البصرية، ولا تمثل تشخيصًا أو درجة ذكاء.",
        "version": 210,
    }


def template() -> tuple[Path, dict]:
    preferred = ROOT / "temporal-order-memory" / "index.html"
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
        '<section class="cognitive-bank-v202" data-visual-change-v210 role="note">'
        '<h2>ما الذي تتدرب عليه؟</h2>'
        '<p>تعرض المهمة مجموعة قصيرة من الأشكال الملونة ثم تخفيها، وبعد فاصل قصير يظهر عرض ثانٍ تغيرت فيه خانة واحدة. يبدأ الحمل بثلاث خانات وأشكال شديدة التمايز للأطفال، ثم يرتفع تدريجيًا إلى سبع خانات وتغييرات في اللون أو الشكل.</p>'
        '<p><strong>حدود الاستخدام:</strong> هذه مهمة تدريبية غير تشخيصية، وليست اختبار IQ أو مقياسًا معياريًا لسعة الذاكرة البصرية. قد يتأثر الأداء بالعمر والانتباه والرؤية اللونية وسطوع الشاشة والجهاز والخبرة.</p>'
        '<h2>الأساس العلمي</h2>'
        '<p>تستخدم أبحاث الذاكرة البصرية العاملة مهام كشف التغير أو تحديد موضعه لمقارنة عرض بصري محفوظ بعرض لاحق. يزداد العبء عادة مع حجم المجموعة وتعقيد الخصائص، كما تتطور القدرة خلال الطفولة. لذلك تعرض الصفحة تدريبًا متدرجًا ولا تحول النتيجة إلى حكم سريري.</p>'
        '<ul><li><a href="https://pubmed.ncbi.nlm.nih.gov/22099167/" rel="noopener noreferrer">تطور سعة الذاكرة البصرية خلال الطفولة المبكرة</a></li>'
        '<li><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10197827/" rel="noopener noreferrer">موثوقية تحديد موضع التغير في الذاكرة البصرية</a></li>'
        '<li><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC5632133/" rel="noopener noreferrer">ثبات وموثوقية مهمة كشف التغير</a></li>'
        '<li><a href="https://pubmed.ncbi.nlm.nih.gov/31267436/" rel="noopener noreferrer">أثر حجم المجموعة وتعقيد الخصائص في الصعوبة</a></li></ul>'
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
        "learningResourceType": "interactive visual change localization task",
        "dateModified": TODAY,
        "isAccessibleForFree": True,
        "audience": {"@type": "EducationalAudience", "educationalRole": "learner"},
    }
    text = re.sub(
        r'<script type="application/ld\+json" data-(?:working-memory-v205|prospective-memory-v206|associative-binding-v207|temporal-order-v208)>.*?</script>',
        "",
        text,
        flags=re.S,
    )
    text = text.replace(
        "</head>",
        '<script type="application/ld+json" data-visual-change-v210>'
        + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
        + "</script></head>",
        1,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return source_slug, source


def patch_runtime() -> None:
    text = JS.read_text(encoding="utf-8")
    branch = r''' if(mode==='visual_change_detection'){const shapes=[['دائرة','●'],['مثلث','▲'],['مربع','■'],['معين','◆'],['نجمة','★'],['سداسي','⬟'],['صليب','✚'],['مثمن','⬢'],['قلب','♥'],['هلال','☾']],colors=[['أحمر','#b42318'],['أزرق','#175cd3'],['أخضر','#067647'],['برتقالي','#b54708'],['بنفسجي','#6941c6'],['تركواز','#087e8b']],setSize=3+stage,shapeOrder=shuffle(shapes,rnd),colorOrder=shuffle(colors,rnd),items=Array.from({length:setSize},(_,i)=>({shape:shapeOrder[i%shapeOrder.length],color:colorOrder[(i+Math.floor(rnd()*colors.length))%colors.length]})),changeIndex=Math.floor(rnd()*setSize),changeFeature=stage===0?'shape':stage===1?'color':(rnd()>.5?'shape':'color'),probe=items.map(x=>({shape:x.shape,color:x.color}));if(changeFeature==='shape'){const alternatives=shapes.filter(x=>x[0]!==probe[changeIndex].shape[0]);probe[changeIndex].shape=pick(alternatives)}else{const alternatives=colors.filter(x=>x[0]!==probe[changeIndex].color[0]);probe[changeIndex].color=pick(alternatives)}const positionNames=['الخانة الأولى','الخانة الثانية','الخانة الثالثة','الخانة الرابعة','الخانة الخامسة','الخانة السادسة','الخانة السابعة'],answer=positionNames[changeIndex],distractors=shuffle(positionNames.slice(0,setSize).filter(x=>x!==answer),rnd).slice(0,3),render=arr=>`<div class="visual-change-grid" data-visual-change-grid data-set-size="${setSize}" style="display:grid;grid-template-columns:repeat(${Math.min(setSize,4)},minmax(3rem,1fr));gap:.65rem;margin:1rem 0">${arr.map((x,i)=>`<span class="visual-change-item" data-position="${i+1}" aria-label="الخانة ${i+1}: ${x.shape[0]} ${x.color[0]}" style="display:grid;place-items:center;min-height:4.25rem;border:2px solid #b8cbc8;border-radius:14px;background:#fff;color:${x.color[1]};font-size:2.35rem;font-weight:900">${x.shape[1]}</span>`).join('')}</div>`,featurePrompt=stage<2?(changeFeature==='shape'?'الشكل':'اللون'):'اللون أو الشكل',study=`<div data-visual-change-study><strong>احفظ العرض الأول:</strong>${render(items)}</div>`,prompt=`<div data-visual-change-probe><strong>حدد الخانة التي تغير فيها ${featurePrompt} بعد اختفاء العرض الأول:</strong>${render(probe)}</div>`;return v202Finish(d,stage,rnd,{prompt,study,studyMs:Math.max(3000,5400-stage*550),answer,options:[answer,...distractors],visualChangeSetSize:setSize,visualChangeFeature:changeFeature,visualChangePosition:changeIndex+1,visualChangeStudySignature:items.map(x=>x.shape[0]+'-'+x.color[0]).join('|'),visualChangeProbeSignature:probe.map(x=>x.shape[0]+'-'+x.color[0]).join('|'),explanation:`التغير ظهر في ${answer} وكان في ${changeFeature==='shape'?'الشكل':'اللون'}.`})}
'''
    marker = " const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"
    if "mode==='visual_change_detection'" not in text:
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
            raise SystemExit("Visual-change sitemap entry must exist exactly once")
        return path.name
    raise SystemExit("No cognitive sitemap containing template route found")


def synchronize_reports() -> None:
    complete = SITE / "api/cognitive-complete-v24.json"
    if complete.exists():
        data = json.loads(complete.read_text(encoding="utf-8"))
        data["completed"] = 53
        data["remaining"] = 0
        data["visual_change_detection_v210"] = True
        slugs = list(data.get("slugs", []))
        if SLUG not in slugs:
            slugs.append(SLUG)
        data["slugs"] = slugs
        complete.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify() -> dict:
    pages = sorted(ROOT.glob("*/index.html"))
    if len(pages) != 53:
        raise SystemExit(f"Expected 53 cognitive pages after v210, found {len(pages)}")
    text = (ROOT / SLUG / "index.html").read_text(encoding="utf-8")
    required = [
        TITLE,
        CANONICAL,
        '"mode":"visual_change_detection"',
        '"trials_per_stage":10',
        'data-visual-change-v210',
        'application/ld+json',
        'ليست اختبار IQ',
        'training-only-not-diagnostic',
        'pubmed.ncbi.nlm.nih.gov/22099167',
        'pmc.ncbi.nlm.nih.gov/articles/PMC10197827',
        'pmc.ncbi.nlm.nih.gov/articles/PMC5632133',
        'pubmed.ncbi.nlm.nih.gov/31267436',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Visual-change page missing markers: {missing}")
    return {
        "version": 210,
        "cognitive_pages": 53,
        "total_lab_tools": 93,
        "slug": SLUG,
        "multiple_choice": True,
        "levels": 5,
        "trials": 50,
        "diagnostic": False,
        "standardized_measure": False,
        "minimum_set_size": 3,
        "maximum_set_size": 7,
        "change_features": ["shape", "color"],
        "study_then_test": True,
        "shape_pool": 10,
        "color_pool": 6,
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
    (api / "visual-change-v210.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
