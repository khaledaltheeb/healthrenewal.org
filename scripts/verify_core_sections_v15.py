from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
errors: list[str] = []
report = json.loads((SITE / "api/core-sections-v15.json").read_text(encoding="utf-8"))
if report.get("tips_guides") != 20:
    errors.append("tips guide source baseline")
if report.get("assessment_pages") != 40:
    errors.append("assessment page count")
if report.get("cognitive_pages") != 48:
    errors.append("cognitive page count")

runtime = (SITE / "assets/js/lab-v12.js").read_text(encoding="utf-8")
checks = {
    "v15_marker": "__PTERMINOLOGY_LAB_V15__" in runtime,
    "old_color_bug_absent": "answer=Math.floor(rnd()*4)" not in runtime,
    "color_value_answer": "answer=target.value" in runtime,
    "result_hook": "showAssessmentResult" in runtime and "cognitiveResult" in runtime,
    "partial_scoring": "maxAnswered" in runtime,
    "missing_answer_guard": "أجب عن ${missing.length}" in runtime,
    "node_export": "globalThis.__PTERMINOLOGY_LAB_V15__" in runtime,
    "no_mutation_observer": "MutationObserver" not in runtime,
}
for key, value in checks.items():
    if not value:
        errors.append(key)

tips_root = SITE / "tips"
v234_report_path = SITE / "api/tips-verification-v234.json"
v234 = None
if v234_report_path.is_file():
    v234 = json.loads(v234_report_path.read_text(encoding="utf-8"))

lengths: list[int] = []
tips_version = 15
if v234 is not None:
    tips_version = 234
    pages = sorted(page for page in tips_root.rglob("index.html") if page.parent != tips_root)
    if v234.get("status") != "passed":
        errors.append("tips v234 verification status")
    expected_v234 = {
        "pages": 49,
        "guides": 36,
        "categories": 9,
        "sitemap_urls": 49,
        "unique_titles": 49,
        "unique_descriptions": 49,
        "unique_canonicals": 49,
    }
    for key, expected in expected_v234.items():
        if v234.get(key) != expected:
            errors.append(f"tips v234 {key}={v234.get(key)!r}")
    if len(pages) != 48:
        errors.append(f"tips v234 child pages={len(pages)}")
    for page in pages:
        text = page.read_text(encoding="utf-8")
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        lengths.append(len(plain))
        if text.count("<h1") != 1:
            errors.append(f"{page}: expected one h1")
        if "application/ld+json" not in text:
            errors.append(f"{page}: JSON-LD missing")
        if "tips-v234.css" not in text:
            errors.append(f"{page}: v234 stylesheet missing")
    if int(v234.get("minimum_arabic_words", 0)) < 100:
        errors.append("tips v234 Arabic depth")
    if int(v234.get("minimum_internal_links", 0)) < 3:
        errors.append("tips v234 internal links")
else:
    pages = sorted(tips_root.glob("*/index.html"))
    required = [
        "متى يفيد هذا الدليل؟",
        "خطة التنفيذ خطوة بخطوة",
        "جملة جاهزة للاستخدام",
        "ما الذي يجب تجنبه؟",
        "كيف تعرف أن الخطة تتحسن؟",
        "متى تحتاج إلى مساعدة؟",
        "مصادر موثوقة للتوسع",
    ]
    if len(pages) != 20:
        errors.append(f"tips pages={len(pages)}")
    descriptions: set[str] = set()
    titles: set[str] = set()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        lengths.append(len(plain))
        for marker in required:
            if marker not in text:
                errors.append(f"{page}: missing {marker}")
        if text.count('class="tips-v15__step"') < 6:
            errors.append(f"{page}: fewer than six steps")
        if '"@type": "HowTo"' not in text and '"@type":"HowTo"' not in text:
            errors.append(f"{page}: HowTo schema missing")
        title = re.search(r"<title>(.*?)</title>", text, re.S)
        description = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        if not title or not description:
            errors.append(f"{page}: metadata missing")
        else:
            titles.add(title.group(1))
            descriptions.add(description.group(1))
    if lengths and min(lengths) < 1800:
        errors.append(f"min tips chars={min(lengths)}")
    if len(titles) != 20 or len(descriptions) != 20:
        errors.append("tips title/description duplicates")

for root, count in [("assessment-lab", 40), ("cognitive-lab", 48)]:
    files = sorted((SITE / root).glob("*/index.html"))
    if len(files) != count:
        errors.append(f"{root} count={len(files)}")
    for page in files:
        text = page.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/json" id="lab-definition">(.*?)</script>',
            text,
            re.S,
        )
        if not match:
            errors.append(f"{page}: definition missing")
            continue
        try:
            data = json.loads(match.group(1))
        except Exception as exc:
            errors.append(f"{page}: invalid definition {exc}")
            continue
        if not data.get("slug") or not data.get("title"):
            errors.append(f"{page}: incomplete definition")
        if "lab-v12.js?v=15" not in text:
            errors.append(f"{page}: v15 runtime not linked")
        if "core-v15.css" not in text:
            errors.append(f"{page}: v15 css not linked")

namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
tree = ET.parse(SITE / "sitemap-tips.xml")
urls = [node.text for node in tree.getroot().findall("s:url/s:loc", namespace) if node.text]
expected_sitemap_urls = 49 if tips_version == 234 else 21
if len(urls) != expected_sitemap_urls:
    errors.append(f"tips sitemap={len(urls)} expected={expected_sitemap_urls}")
if len(urls) != len(set(urls)):
    errors.append("tips sitemap duplicates")

service_worker = (SITE / "sw.js").read_text(encoding="utf-8")
supported = (
    "pterminology-v15-core-sections",
    "pterminology-v20-global-quality",
    "pterminology-v21-global-quality",
    "pterminology-v23-resilient-core",
)
if not any(name in service_worker for name in supported):
    errors.append("supported cache missing")
if "pterminology-v23-resilient-core" in service_worker:
    if "Promise.allSettled" not in service_worker:
        errors.append("resilient core cache missing")
    if "cached===0" not in service_worker:
        errors.append("empty core cache guard missing")
    if "cache.addAll" in service_worker:
        errors.append("atomic cache.addAll regression")
version = (
    23
    if "pterminology-v23-resilient-core" in service_worker
    else 21
    if "pterminology-v21-global-quality" in service_worker
    else 20
    if "pterminology-v20-global-quality" in service_worker
    else 15
)
result = {
    "version": version,
    "tips_version": tips_version,
    "checks": checks,
    "tips_pages": len(pages),
    "tips_sitemap_urls": len(urls),
    "minimum_tip_characters": min(lengths) if lengths else 0,
    "tips_v234_verification": v234 if v234 is not None else None,
    "errors": errors,
}
(SITE / "api/core-sections-audit-v15.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit("\n".join(errors[:80]))
