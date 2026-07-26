from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
errors: list[str] = []

report = json.loads((SITE / "api/core-sections-v15.json").read_text(encoding="utf-8"))
tips_report_path = SITE / "api/practical-tips-v237.json"
tips_report = (
    json.loads(tips_report_path.read_text(encoding="utf-8"))
    if tips_report_path.is_file()
    else None
)

if tips_report is not None:
    required_tips_report = {
        "version": 237,
        "status": "passed",
        "guide_count": 100,
        "preserved_existing_guides": 20,
        "new_guides": 80,
        "pillar_count": 10,
        "remaining_below_minimum": 0,
        "missing_or_failed": 0,
        "duplicate_slugs": 0,
        "duplicate_titles": 0,
        "sitemap_urls": 111,
        "core_sections_compatibility": "passed",
        "compatibility_pages": 100,
        "unique_titles": 100,
        "unique_descriptions": 100,
    }
    for key, expected in required_tips_report.items():
        if tips_report.get(key) != expected:
            errors.append(
                f"practical tips v237 report {key}={tips_report.get(key)!r}, expected={expected!r}"
            )
    if int(tips_report.get("category_count", 0)) < 25:
        errors.append("practical tips v237 category count")
    if int(tips_report.get("minimum_after_words", 0)) < 700:
        errors.append("practical tips v237 minimum words")
    expected_tips_pages = 100
    expected_tip_titles = 100
    expected_tip_descriptions = 100
    expected_tip_sitemap_urls = 111
    accepted_step_classes = ('class="tip237-step"', 'class="tips-v15__step"')
    tips_contract_version = 237
else:
    expected_tips_pages = 20
    expected_tip_titles = 20
    expected_tip_descriptions = 20
    expected_tip_sitemap_urls = 21
    accepted_step_classes = ('class="tips-v15__step"',)
    tips_contract_version = 15

if report.get("tips_guides") not in {20, expected_tips_pages}:
    errors.append("tips guide count")
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

pages = sorted((SITE / "tips").glob("*/index.html"))
lengths: list[int] = []
descriptions: set[str] = set()
titles: set[str] = set()
required = [
    "متى يفيد هذا الدليل؟",
    "خطة التنفيذ خطوة بخطوة",
    "جملة جاهزة للاستخدام",
    "ما الذي يجب تجنبه؟",
    "كيف تعرف أن الخطة تتحسن؟",
    "متى تحتاج إلى مساعدة؟",
    "مصادر موثوقة للتوسع",
]
if len(pages) != expected_tips_pages:
    errors.append(f"tips pages={len(pages)}")

for page in pages:
    text = page.read_text(encoding="utf-8")
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    lengths.append(len(plain))
    for marker in required:
        if marker not in text:
            errors.append(f"{page}: missing {marker}")
    step_count = max(text.count(marker) for marker in accepted_step_classes)
    if step_count < 6:
        errors.append(f"{page}: fewer than six steps")
    if '"@type": "HowTo"' not in text and '"@type":"HowTo"' not in text:
        errors.append(f"{page}: HowTo schema missing")
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    description = re.search(
        r'<meta name="description" content="(.*?)">', text, re.S
    )
    if not title or not description:
        errors.append(f"{page}: metadata missing")
    else:
        titles.add(title.group(1))
        descriptions.add(description.group(1))

if lengths and min(lengths) < 1800:
    errors.append(f"min tips chars={min(lengths)}")
if (
    len(titles) != expected_tip_titles
    or len(descriptions) != expected_tip_descriptions
):
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
urls = [
    node.text
    for node in tree.getroot().findall("s:url/s:loc", namespace)
    if node.text
]
if len(urls) != expected_tip_sitemap_urls:
    errors.append(f"tips sitemap={len(urls)}")

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
    else (
        21
        if "pterminology-v21-global-quality" in service_worker
        else (
            20
            if "pterminology-v20-global-quality" in service_worker
            else 15
        )
    )
)
result = {
    "version": version,
    "tips_contract_version": tips_contract_version,
    "checks": checks,
    "tips_pages": len(pages),
    "expected_tips_pages": expected_tips_pages,
    "tips_sitemap_urls": len(urls),
    "expected_tips_sitemap_urls": expected_tip_sitemap_urls,
    "unique_tip_titles": len(titles),
    "unique_tip_descriptions": len(descriptions),
    "minimum_tip_characters": min(lengths) if lengths else 0,
    "errors": errors,
}
(SITE / "api/core-sections-audit-v15.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit("\n".join(errors[:50]))
