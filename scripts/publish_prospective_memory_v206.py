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
SLUG = "prospective-memory-cues"
TITLE = "ذاكرة النوايا والإشارات المستقبلية"
CATEGORY = "الذاكرة التنفيذية"
SUMMARY = "مهمة تدريبية غير تشخيصية تربط نية مؤجلة بإشارة مناسبة بعد نشاط فاصل، بخيارات متعددة وخمسة مستويات متدرجة للأطفال والبالغين."
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
CANONICAL = BASE + "cognitive-lab/" + SLUG + "/"
TODAY = date.today().isoformat()


def definition() -> dict:
    return {
        "slug": SLUG,
        "title": TITLE,
        "category": CATEGORY,
        "summary": SUMMARY,
        "mode": "prospective_memory_cues",
        "stages": 5,
        "trials_per_stage": 10,
        "instructions": "احفظ النية التي تظهر أولًا، ثم أكمل النشاط الفاصل واختر الفعل الصحيح عندما تظهر الإشارة.",
        "answer_mode": "multiple-choice",
        "question_pool_version": 206,
        "difficulty_levels": ["تمهيدي", "أساسي", "متوسط", "متقدم", "تحدٍ مرتفع"],
        "session_randomization": True,
        "repeat_guard": True,
        "audience": ["الأطفال بإشراف بالغ", "المراهقون", "البالغون"],
        "clinical_status": "training-only-not-diagnostic",
        "evidence_note": "تدرب المهمة على تذكر نية بعد نشاط فاصل ثم تنفيذها عند إشارة مستقبلية. لا تعادل بطارية ذاكرة مستقبلية معيارية، ولا تمثل تشخيصًا أو درجة ذكاء.",
        "version": 206,
    }


def template() -> tuple[Path, dict]:
    preferred = ROOT / "working-memory-updating" / "index.html"
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
    for old, new in ((str(source.get("title", "")), TITLE), (str(source.get("summary", "")), SUMMARY), (str(source.get("category", "")), CATEGORY)):
        if old:
            text = text.replace(old, new)
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', text, re.S)
    if not match:
        raise SystemExit("Template definition missing")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    text = text[:match.start(1)] + payload + text[match.end(1):]
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
    if '<meta name="twitter:description"' in text:
        text = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{description}">', text, count=1)
    else:
        text = text.replace("</head>", f'<meta name="twitter:description" content="{description}"></head>', 1)
    text = re.sub(r'<section class="cognitive-bank-v202"[^>]*>.*?</section>', '', text, count=1, flags=re.S)
    note = '<section class="cognitive-bank-v202" data-prospective-memory-v206 role="note"><h2>ما الذي تتدرب عليه؟</h2><p>تكوين نية قصيرة، والاحتفاظ بها أثناء نشاط فاصل، ثم استدعاؤها عند ظهور الإشارة المناسبة. المستويات الأولى مباشرة للأطفال، ثم يزداد طول النشاط الفاصل وتتنوع الإشارات تدريجيًا. هذه مهمة تدريبية وليست اختبار IQ أو تشخيصًا أو مقياسًا معياريًا للذاكرة المستقبلية.</p></section>'
    text = text.replace('<div data-v12-lab="cognitive"', note + '<div data-v12-lab="cognitive"', 1)
    schema = {"@context":"https://schema.org","@type":"LearningResource","name":TITLE,"description":SUMMARY,"url":CANONICAL,"inLanguage":"ar","educationalUse":"practice","learningResourceType":"interactive prospective-memory training task","dateModified":TODAY,"isAccessibleForFree":True}
    text = re.sub(r'<script type="application/ld\+json" data-working-memory-v205>.*?</script>', '', text, flags=re.S)
    text = text.replace("</head>", '<script type="application/ld+json" data-prospective-memory-v206>' + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/") + "</script></head>", 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return source_slug, source


def patch_runtime() -> None:
    text = JS.read_text(encoding="utf-8")
    branch = r''' if(mode==='prospective_memory_cues'){const cues=[['دائرة','●'],['نجمة','★'],['مثلث','▲'],['مربع','■'],['الرقم 7','7'],['الرقم 3','3'],['كلمة مدرسة','مدرسة'],['كلمة ماء','ماء'],['كلمة موعد','موعد'],['اللون الأخضر','أخضر'],['اللون الأزرق','أزرق'],['رمز المفتاح','🔑']],actions=['اختر الكتاب','اختر المفتاح','اختر التقويم','اختر الحقيبة','اختر القلم','اختر الدفتر','اختر الساعة','اختر الكوب','اختر البطاقة','اختر الخريطة','اختر المصباح','اختر المظلة'],cue=pick(cues),answer=pick(actions),distractors=shuffle(actions.filter(x=>x!==answer),rnd).slice(0,3),fillerCount=2+stage*2,fillers=Array.from({length:fillerCount},()=>{const a=ri(2,20+stage*4),b=ri(1,9+stage);return `${a} + ${b} = ${a+b}`}),study=`احفظ النية: عندما تظهر ${cue[0]} (${cue[1]})، ${answer}.`,prompt=`نشاط فاصل: ${fillers.join('؛ ')}. ظهرت الآن الإشارة ${cue[0]} (${cue[1]}). ماذا يجب أن تفعل؟`;return v202Finish(d,stage,rnd,{prompt,study,studyMs:Math.max(1800,4200-stage*450),answer,options:[answer,...distractors],explanation:`الإشارة ${cue[0]} مرتبطة بالنية: ${answer}.`})}
'''
    marker = " const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"
    if "mode==='prospective_memory_cues'" not in text:
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
    for old, new in ((str(source.get("title", "")), TITLE), (str(source.get("summary", "")), SUMMARY), (str(source.get("category", "")), CATEGORY)):
        if old:
            card = card.replace(old, new)
    path.write_text(text[:match.end()] + card + text[match.end():], encoding="utf-8")


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
            raise SystemExit("Prospective-memory sitemap entry must exist exactly once")
        return path.name
    raise SystemExit("No cognitive sitemap containing template route found")


def synchronize_reports() -> None:
    complete = SITE / "api/cognitive-complete-v24.json"
    if complete.exists():
        data = json.loads(complete.read_text(encoding="utf-8"))
        data["completed"] = 50
        data["remaining"] = 0
        data["prospective_memory_v206"] = True
        slugs = list(data.get("slugs", []))
        if SLUG not in slugs:
            slugs.append(SLUG)
        data["slugs"] = slugs
        complete.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify() -> dict:
    pages = sorted(ROOT.glob("*/index.html"))
    if len(pages) != 50:
        raise SystemExit(f"Expected 50 cognitive pages after v206, found {len(pages)}")
    text = (ROOT / SLUG / "index.html").read_text(encoding="utf-8")
    required = [TITLE, CANONICAL, '"mode":"prospective_memory_cues"', '"trials_per_stage":10', 'data-prospective-memory-v206', 'application/ld+json', 'ليست اختبار IQ']
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Prospective-memory page missing markers: {missing}")
    return {"version":206,"cognitive_pages":50,"total_lab_tools":90,"slug":SLUG,"multiple_choice":True,"levels":5,"trials":50,"diagnostic":False,"standardized_measure":False,"cue_action_combinations":144,"delayed_intention_display":True}


def main() -> None:
    source_slug, source = publish_page()
    patch_runtime()
    patch_index(source_slug, source)
    sitemap = patch_sitemap(source_slug)
    synchronize_reports()
    report = {**verify(), "sitemap": sitemap, "status": "built-not-published"}
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "prospective-memory-v206.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
