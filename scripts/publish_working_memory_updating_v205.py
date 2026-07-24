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
SLUG = "working-memory-updating"
TITLE = "تحديث الذاكرة العاملة المتسلسل"
CATEGORY = "الذاكرة العاملة"
SUMMARY = "مهمة تدريبية غير تشخيصية تتطلب الاحتفاظ بقيم قصيرة وتحديثها بعد تعليمات متتابعة، بخيارات متعددة وخمسة مستويات متدرجة."
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
CANONICAL = BASE + "cognitive-lab/" + SLUG + "/"
TODAY = date.today().isoformat()


def definition() -> dict:
    return {
        "slug": SLUG,
        "title": TITLE,
        "category": CATEGORY,
        "summary": SUMMARY,
        "mode": "working_memory_updating",
        "stages": 5,
        "trials_per_stage": 10,
        "instructions": "احتفظ بالقيم الابتدائية، وطبّق كل تحديث بالترتيب، ثم اختر الحالة النهائية الصحيحة.",
        "answer_mode": "multiple-choice",
        "question_pool_version": 205,
        "difficulty_levels": ["تمهيدي", "أساسي", "متوسط", "متقدم", "تحدٍ مرتفع"],
        "session_randomization": True,
        "repeat_guard": True,
        "audience": ["الأطفال بإشراف بالغ", "المراهقون", "البالغون"],
        "clinical_status": "training-only-not-diagnostic",
        "evidence_note": "تحسن الأداء المتوقع يخص المهمة ومهامًا قريبة منها؛ لا تمثل النتيجة درجة ذكاء ولا تثبت انتقالًا إلى الذكاء العام.",
        "version": 205,
    }


def find_template() -> tuple[Path, dict]:
    candidates = sorted(ROOT.glob("*/index.html"))
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', text, re.S)
        if not match:
            continue
        data = json.loads(match.group(1))
        if data.get("mode") in {"digit_span", "sequence_memory", "n_back", "one_back", "two_back"}:
            return path, data
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', text, re.S)
        if match:
            return path, json.loads(match.group(1))
    raise SystemExit("No cognitive page template found")


def publish_page() -> tuple[str, dict]:
    target = ROOT / SLUG / "index.html"
    data = definition()
    if target.exists():
        text = target.read_text(encoding="utf-8")
        source_slug = SLUG
        source = data
    else:
        template, source = find_template()
        source_slug = str(source.get("slug") or template.parent.name)
        text = template.read_text(encoding="utf-8")
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
    text = text[:match.start(1)] + payload + text[match.end(1):]
    description = html.escape(SUMMARY, quote=True)
    text = re.sub(r'<title>.*?</title>', f'<title>{TITLE} | مصطلحات علم النفس</title>', text, count=1, flags=re.S)
    text = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{description}">', text, count=1)
    text = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{TITLE}">', text, count=1)
    text = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{description}">', text, count=1)
    text = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{CANONICAL}">', text, count=1)
    text = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{CANONICAL}">', text, count=1)
    if '<meta name="twitter:description"' in text:
        text = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{description}">', text, count=1)
    else:
        text = text.replace("</head>", f'<meta name="twitter:description" content="{description}"></head>', 1)
    if 'data-working-memory-v205' not in text:
        note = '<section class="cognitive-bank-v202" data-working-memory-v205 role="note"><h2>ما الذي تتدرب عليه؟</h2><p>تتبع حالة قصيرة تتغير خطوة بعد خطوة. تبدأ المستويات الأولى بخانتين وتحديثات قليلة، ثم تزداد الخانات وعدد العمليات تدريجيًا. هذه مهمة تدريبية وليست اختبار IQ أو تشخيصًا.</p></section>'
        text = text.replace('<div data-v12-lab="cognitive"', note + '<div data-v12-lab="cognitive"', 1)
    schema = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": TITLE,
        "description": SUMMARY,
        "url": CANONICAL,
        "inLanguage": "ar",
        "educationalUse": "practice",
        "learningResourceType": "interactive cognitive training task",
        "dateModified": TODAY,
        "isAccessibleForFree": True,
    }
    schema_text = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    marker = '<script type="application/ld+json" data-working-memory-v205>'
    if marker not in text:
        text = text.replace("</head>", marker + schema_text + "</script></head>", 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return source_slug, source


def patch_runtime() -> None:
    text = JS.read_text(encoding="utf-8")
    branch = r""" if(mode==='working_memory_updating'){const slots=2+Math.floor(stage/2),initial=Array.from({length:slots},()=>ri(1,9)),state=[...initial],steps=[],updates=2+stage*2;for(let i=0;i<updates;i++){const slot=ri(0,slots-1),maxDown=Math.max(1,Math.min(3,state[slot])),delta=rnd()>.45?ri(1,3):-ri(1,maxDown);state[slot]+=delta;steps.push(`${delta>0?'أضف':'اطرح'} ${Math.abs(delta)} ${delta>0?'إلى':'من'} الخانة ${slot+1}`)}const answer=state.join(' - '),options=[answer];for(let j=0;j<4;j++){const wrong=[...state],slot=(j+stage)%slots,change=j%2?1:-1;wrong[slot]=Math.max(0,wrong[slot]+change);options.push(wrong.join(' - '))}return v202Finish(d,stage,rnd,{prompt:`ابدأ بالقيم: ${initial.join(' - ')}. طبّق بالترتيب: ${steps.join('، ')}. ما الحالة النهائية؟`,answer,options,explanation:`بعد تطبيق التحديثات بالتسلسل تصبح القيم ${answer}.`})}
 """
    marker = " const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"
    if "mode==='working_memory_updating'" not in text:
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
    text = text[:match.end()] + card + text[match.end():]
    path.write_text(text, encoding="utf-8")


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
            raise SystemExit("Working-memory sitemap entry must exist exactly once")
        return path.name
    raise SystemExit("No cognitive sitemap containing the template route was found")


def synchronize_reports() -> None:
    complete = SITE / "api/cognitive-complete-v24.json"
    if complete.exists():
        data = json.loads(complete.read_text(encoding="utf-8"))
        data["completed"] = 49
        data["remaining"] = 0
        data["working_memory_updating_v205"] = True
        slugs = list(data.get("slugs", []))
        if SLUG not in slugs:
            slugs.append(SLUG)
        data["slugs"] = slugs
        complete.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify() -> dict:
    pages = sorted(ROOT.glob("*/index.html"))
    if len(pages) != 49:
        raise SystemExit(f"Expected 49 cognitive pages after v205, found {len(pages)}")
    target = ROOT / SLUG / "index.html"
    text = target.read_text(encoding="utf-8")
    required = [TITLE, CANONICAL, '"mode":"working_memory_updating"', '"trials_per_stage":10', 'data-working-memory-v205', 'application/ld+json']
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Working-memory page missing markers: {missing}")
    return {"version": 205, "cognitive_pages": 49, "total_lab_tools": 89, "slug": SLUG, "multiple_choice": True, "levels": 5, "trials": 50, "diagnostic": False}


def main() -> None:
    source_slug, source = publish_page()
    patch_runtime()
    patch_index(source_slug, source)
    sitemap = patch_sitemap(source_slug)
    synchronize_reports()
    report = {**verify(), "sitemap": sitemap, "status": "built-not-published"}
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "working-memory-updating-v205.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
