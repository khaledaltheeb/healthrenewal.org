#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
VERIFY = ROOT / "scripts" / "verify_homepage_v19.py"
BASE = "https://healthrenewal.org/"
RELEASE = 219
TOOL_COUNT = 100
PATH_COUNT = 10
CATEGORY_COUNT = 10


def add_once(text: str, marker: str, addition: str, identity: str) -> str:
    if identity in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise SystemExit(f"{identity}: expected one insertion marker, found {count}")
    return text.replace(marker, marker + addition, 1)


def patch_keywords(text: str) -> str:
    match = re.search(r'(<meta name="keywords" content=")([^"]*)(">)', text)
    if not match:
        raise SystemExit("Homepage keyword metadata is missing")
    values = [item.strip() for item in match.group(2).split(",") if item.strip()]
    for value in ("أدوات نفسية تفاعلية", "أدوات تنظيم التوتر", "أدوات متابعة النوم", "مسارات تعلم الصحة النفسية"):
        if value not in values:
            values.append(value)
    return text[: match.start(2)] + ",".join(values) + text[match.end(2) :]


def patch_jsonld(text: str) -> str:
    match = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', text, re.S)
    if not match:
        raise SystemExit("Homepage JSON-LD is missing")
    payload = json.loads(match.group(2))
    graph = payload.get("@graph")
    if not isinstance(graph, list):
        raise SystemExit("Homepage JSON-LD graph is invalid")
    collection = next((item for item in graph if isinstance(item, dict) and item.get("@type") == "CollectionPage" and str(item.get("@id", "")).endswith("#home")), None)
    if not collection:
        raise SystemExit("Homepage CollectionPage JSON-LD is missing")
    parts = collection.setdefault("hasPart", [])
    additions = (
        {"@type": "CollectionPage", "name": "الأدوات النفسية التفاعلية اليومية", "url": BASE + "daily-tools/"},
        {"@type": "CollectionPage", "name": "مسارات تعلم الصحة النفسية", "url": BASE + "learning-paths/"},
    )
    urls = {item.get("url") for item in parts if isinstance(item, dict)}
    for item in additions:
        if item["url"] not in urls:
            parts.append(item)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start(2)] + encoded + text[match.end(2) :]


def cards() -> tuple[str, str]:
    tools = (
        '<article class="card" data-daily-tools-v219><span class="tag">خصوصية محلية</span><h3>الأدوات النفسية التفاعلية</h3>'
        f'<p>{TOOL_COUNT} أداة عربية عملية موزعة على {CATEGORY_COUNT} مجالات للتنظيم النفسي والأسري والتربوي، تعمل محليًا دون تشخيص أو إرسال البيانات إلى خادم.</p>'
        '<a href="daily-tools/">فتح الأدوات التفاعلية</a></article>'
    )
    paths = (
        '<article class="card" data-learning-paths-v219><span class="tag">تعلم منظم</span><h3>مسارات التعلم القصيرة</h3>'
        f'<p>{PATH_COUNT} مسارات مترابطة تحول المعرفة إلى خطة أيام وأدوات عملية قابلة للمراجعة.</p>'
        '<a href="learning-paths/">فتح مسارات التعلم</a></article>'
    )
    return tools, paths


def upsert_card(text: str, identity: str, card: str, marker: str) -> str:
    pattern = re.compile(rf'<article class="card" {identity}>.*?</article>', re.S)
    matches = list(pattern.finditer(text))
    if len(matches) > 1:
        raise SystemExit(f"Duplicate homepage card before normalization: {identity}")
    if matches:
        match = matches[0]
        return text[: match.start()] + card + text[match.end() :]
    if text.count(marker) != 1:
        raise SystemExit(f"Homepage card marker changed for {identity}")
    return text.replace(marker, marker + card, 1)


def patch_index() -> None:
    text = patch_jsonld(patch_keywords(INDEX.read_text(encoding="utf-8")))
    nav_marker = '<a href="provider-assessment-demo/">منصة التقييم</a>'
    missing_nav = ""
    if 'href="daily-tools/"' not in text:
        missing_nav += '<a href="daily-tools/">أدوات تفاعلية</a>'
    if 'href="learning-paths/"' not in text:
        missing_nav += '<a href="learning-paths/">مسارات التعلم</a>'
    if missing_nav:
        if text.count(nav_marker) != 1:
            raise SystemExit("Homepage provider-assessment navigation marker changed")
        text = text.replace(nav_marker, missing_nav + nav_marker, 1)

    tools_card, paths_card = cards()
    card_marker = '<a href="cognitive-tests/">فتح المهام</a></article>'
    text = upsert_card(text, "data-daily-tools-v219", tools_card, card_marker)
    text = upsert_card(text, "data-learning-paths-v219", paths_card, card_marker)

    journey_marker = '<li><strong>لخطوات يومية:</strong> استخدم النصائح وأدلة التعامل.</li>'
    journey_addition = '<li data-daily-tools-journey-v219><strong>لأداة تفاعلية محلية:</strong> استخدم الأدوات اليومية أو مسار التعلم المناسب.</li>'
    text = add_once(text, journey_marker, journey_addition, "data-daily-tools-journey-v219")

    exact = {
        "data-daily-tools-v219": 1,
        "data-learning-paths-v219": 1,
        "data-daily-tools-journey-v219": 1,
    }
    minimum = {
        'href="daily-tools/"': 2,
        'href="learning-paths/"': 2,
        BASE + "daily-tools/": 1,
        BASE + "learning-paths/": 1,
    }
    errors = {marker: text.count(marker) for marker, count in exact.items() if text.count(marker) != count}
    errors.update({marker: text.count(marker) for marker, count in minimum.items() if text.count(marker) < count})
    if errors:
        raise SystemExit(f"Homepage interactive-tools discovery contract failed: {errors}")
    if f"{TOOL_COUNT} أداة عربية عملية" not in text or f"{PATH_COUNT} مسارات مترابطة" not in text:
        raise SystemExit("Homepage tool counts are stale")
    INDEX.write_text(text, encoding="utf-8")


def insert_after_once(text: str, marker: str, addition: str, identity: str) -> str:
    if identity in text:
        return text
    if text.count(marker) != 1:
        raise SystemExit(f"{identity}: verifier marker changed")
    return text.replace(marker, marker + addition, 1)


def patch_verifier() -> None:
    text = VERIFY.read_text(encoding="utf-8")
    link_marker = '    "provider-assessment-demo/",\n'
    link_additions = ""
    if '    "daily-tools/",\n' not in text:
        link_additions += '    "daily-tools/",\n'
    if '    "learning-paths/",\n' not in text:
        link_additions += '    "learning-paths/",\n'
    if link_additions:
        if text.count(link_marker) != 1:
            raise SystemExit("Homepage verifier link marker changed")
        text = text.replace(link_marker, link_additions + link_marker, 1)

    assertion_marker = '    assert "المكتبة الأكاديمية العربية" in source, "Academic library is not visibly described"\n'
    assertion_addition = (
        '    assert "الأدوات النفسية التفاعلية" in source, "Interactive tools are not visibly described"\n'
        '    assert "مسارات التعلم القصيرة" in source, "Learning paths are not visibly described"\n'
        '    assert source.count("data-daily-tools-v219") == 1, "Interactive tools card must be unique"\n'
        '    assert source.count("data-learning-paths-v219") == 1, "Learning paths card must be unique"\n'
    )
    text = insert_after_once(text, assertion_marker, assertion_addition, "Interactive tools are not visibly described")

    jsonld_marker = '    assert "https://healthrenewal.org/guided-assessment/" in part_urls\n'
    text = insert_after_once(
        text,
        jsonld_marker,
        '    assert "https://healthrenewal.org/daily-tools/" in part_urls\n',
        '"https://healthrenewal.org/daily-tools/" in part_urls',
    )
    text = insert_after_once(
        text,
        jsonld_marker,
        '    assert "https://healthrenewal.org/learning-paths/" in part_urls\n',
        '"https://healthrenewal.org/learning-paths/" in part_urls',
    )

    report_contract = re.search(r'"interactive_tools_discovery_contract"\s*:\s*(\d+)', text)
    if report_contract:
        if int(report_contract.group(1)) < RELEASE:
            text = text[: report_contract.start(1)] + str(RELEASE) + text[report_contract.end(1) :]
    else:
        report_marker = '                "guided_assessment_linked": True,\n'
        report_addition = (
            '                "daily_tools_linked": True,\n'
            '                "learning_paths_linked": True,\n'
            f'                "interactive_tools_discovery_contract": {RELEASE},\n'
        )
        text = insert_after_once(text, report_marker, report_addition, "interactive_tools_discovery_contract")

    required = (
        '    "daily-tools/",',
        '    "learning-paths/",',
        "Interactive tools are not visibly described",
        '"https://healthrenewal.org/daily-tools/" in part_urls',
        '"https://healthrenewal.org/learning-paths/" in part_urls',
        '"daily_tools_linked": True',
        '"learning_paths_linked": True',
        "interactive_tools_discovery_contract",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit(f"Homepage verifier contract remains incomplete: {missing}")
    VERIFY.write_text(text, encoding="utf-8")


def main() -> None:
    patch_index()
    patch_verifier()
    print(json.dumps({"status": "passed", "release": RELEASE, "homepage_source_linked": True, "daily_tools": TOOL_COUNT, "categories": CATEGORY_COUNT, "learning_paths": PATH_COUNT, "duplicate_free": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
