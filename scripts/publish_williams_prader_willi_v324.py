#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import publish_new_special_needs_conditions_v323 as base

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v324" / "williams-prader-willi-guides-ar.json"
VERSION = 324
EXPECTED = ("williams-syndrome", "prader-willi-syndrome")
SOURCE_URL_OVERRIDES = {
    "W2": "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.recommended_evaluations_follo/",
    "W4": "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.treatment_of_manifestations_i/",
    "W7": "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.surveillance_for_williams_syn/",
}


def read_payload() -> dict:
    try:
        data = json.loads(CONTENT.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid v324 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("v324 content must be an object")
    for guide in data.get("guides", []):
        for source in guide.get("sources", []):
            corrected = SOURCE_URL_OVERRIDES.get(str(source.get("id", "")))
            if corrected:
                source["url"] = corrected
    return data


def is_https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(data: dict) -> list[dict]:
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("v324 identity contract failed")
    if data.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("v324 review state must remain honest")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("reviewed_at", ""))):
        raise SystemExit("v324 reviewed_at is invalid")
    guides = data.get("guides")
    if not isinstance(guides, list) or len(guides) != 2:
        raise SystemExit("v324 requires exactly two condition guides")
    if tuple(guide.get("slug") for guide in guides) != EXPECTED:
        raise SystemExit("v324 condition routes are incomplete or out of order")
    serialized = json.dumps(data, ensure_ascii=False)
    if base.BANNED.search(serialized) or base.UNSUPPORTED.search(serialized):
        raise SystemExit("v324 contains banned terminology or unsupported promises")

    for guide in guides:
        required = ("title", "short_title", "english_name", "meta_description", "lead", "warning")
        if any(not str(guide.get(key, "")).strip() for key in required):
            raise SystemExit(f"Incomplete v324 guide identity: {guide.get('slug')}")
        if len(guide.get("key_facts", [])) < 5:
            raise SystemExit(f"Insufficient v324 key facts: {guide['slug']}")
        sections = guide.get("sections")
        sources = guide.get("sources")
        if not isinstance(sections, list) or len(sections) != 7:
            raise SystemExit(f"Each v324 condition needs seven sections: {guide['slug']}")
        if not isinstance(sources, list) or len(sources) < 6:
            raise SystemExit(f"Each v324 condition needs at least six sources: {guide['slug']}")
        if len(guide.get("action_steps", [])) < 8 or len(guide.get("urgent", [])) < 6:
            raise SystemExit(f"v324 action or urgent depth failed: {guide['slug']}")
        if len(guide.get("myths", [])) < 5 or len(guide.get("faqs", [])) < 5:
            raise SystemExit(f"v324 myth or FAQ depth failed: {guide['slug']}")

        source_index: dict[str, dict] = {}
        urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate v324 source id in {guide['slug']}: {sid}")
            if not is_https(url) or url in urls:
                raise SystemExit(f"Invalid or duplicate v324 source URL in {guide['slug']}: {url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid v324 source level: {guide['slug']}/{sid}")
            if any(not str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete v324 source: {guide['slug']}/{sid}")
            source_index[sid] = source
            urls.add(url)

        section_ids: set[str] = set()
        used: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            source_ids = section.get("source_ids", [])
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Invalid v324 section id: {guide['slug']}/{section_id}")
            if not str(section.get("title", "")).strip() or not str(section.get("summary", "")).strip():
                raise SystemExit(f"Incomplete v324 section: {guide['slug']}/{section_id}")
            if len(section.get("points", [])) < 5 or not source_ids:
                raise SystemExit(f"v324 section depth failed: {guide['slug']}/{section_id}")
            if any(source_id not in source_index for source_id in source_ids):
                raise SystemExit(f"Unknown v324 source reference: {guide['slug']}/{section_id}")
            section_ids.add(section_id)
            used.update(source_ids)
        if set(source_index) - used:
            raise SystemExit(f"Unused v324 sources in {guide['slug']}: {sorted(set(source_index) - used)}")
    return guides


def combined_payload(extension: dict) -> tuple[dict, list[dict], list[dict]]:
    base_data = base.read_payload()
    base_guides = base.validate_payload(base_data)
    new_guides = validate_payload(extension)
    all_slugs = [guide["slug"] for guide in base_guides + new_guides]
    if len(all_slugs) != len(set(all_slugs)):
        raise SystemExit("v324 duplicates an existing condition route")

    combined = deepcopy(base_data)
    combined["version"] = VERSION
    combined["review_status"] = extension["review_status"]
    combined["reviewed_at"] = extension["reviewed_at"]
    combined["next_review_due"] = extension["next_review_due"]
    combined["cluster"].update(extension.get("cluster_updates", {}))
    combined["guides"] = deepcopy(base_guides + new_guides)
    return combined, base_guides, new_guides


def render_expanded_cluster(data: dict, guides: list[dict]) -> str:
    page = base.render_cluster(data, guides)
    page = page.replace(
        '<p class="eyebrow">مركز جديد للحالات غير المغطاة سابقًا</p>',
        '<p class="eyebrow">مركز موسع للحالات النمائية والجينية</p>',
    )
    page = page.replace(
        '<h2>الأدلة المنشورة في الدفعة الأولى</h2>',
        '<h2>الأدلة المنشورة في المركز</h2>',
    )
    page, count = re.subn(
        r'<section class="wrap panel"><h2>ما الذي سيُضاف لاحقًا؟</h2>.*?</section>',
        '<section class="wrap panel"><h2>منهج التوسع التالي</h2><p>يضم المركز الآن خمسة أدلة مستقلة: ريت، والكروموسوم X الهش، وأنجلمان، وويليامز، وبرادر–ويلي. تستمر الإضافة على دفعات صغيرة بعد فحص عدم التكرار، وربط كل ادعاء بمصدر، واختبار العمق والاكتشاف والفهرسة وحالة المراجعة.</p></section>',
        page,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit("v324 could not replace the obsolete cluster roadmap")
    return page


def publish(site: Path) -> dict:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    extension = read_payload()
    combined, base_guides, new_guides = combined_payload(extension)

    missing_base = [
        guide["slug"]
        for guide in base_guides
        if not (site / "special-needs" / guide["slug"] / "index.html").is_file()
    ]
    if missing_base:
        raise SystemExit(f"v324 requires the v323 production layer first: {missing_base}")

    generated: list[str] = []
    word_counts: dict[str, int] = {}
    all_guides = base_guides + new_guides
    for guide in new_guides:
        page = base.render_condition(guide, combined, all_guides)
        words = base.text_words(page)
        if words < 1400:
            raise SystemExit(f"v324 condition page is too shallow: {guide['slug']}={words}")
        if page.lower().count("<h1") != 1 or page.count('class="section-card"') != 7:
            raise SystemExit(f"v324 rendered structure failed: {guide['slug']}")
        if "MedicalWebPage" not in page or "FAQPage" not in page or base.BANNED.search(page):
            raise SystemExit(f"v324 rendered metadata or language failed: {guide['slug']}")
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        generated.append(target.relative_to(site).as_posix())
        word_counts[guide["slug"]] = words

    cluster_page = render_expanded_cluster(combined, all_guides)
    cluster_target = site / "special-needs" / combined["cluster"]["slug"] / "index.html"
    cluster_target.parent.mkdir(parents=True, exist_ok=True)
    cluster_target.write_text(cluster_page, encoding="utf-8")
    generated.insert(0, cluster_target.relative_to(site).as_posix())

    base.patch_hub(site, combined, all_guides)
    base.update_sitemap(site, combined, all_guides)

    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": extension["review_status"],
        "external_clinical_review_completed": False,
        "cluster_slug": combined["cluster"]["slug"],
        "base_condition_count": len(base_guides),
        "added_condition_count": len(new_guides),
        "total_condition_count": len(all_guides),
        "added_condition_slugs": [guide["slug"] for guide in new_guides],
        "all_condition_slugs": [guide["slug"] for guide in all_guides],
        "generated_pages": generated,
        "source_count": sum(len(guide["sources"]) for guide in new_guides),
        "source_url_normalizations": len(SOURCE_URL_OVERRIDES),
        "section_count": sum(len(guide["sections"]) for guide in new_guides),
        "faq_count": sum(len(guide["faqs"]) for guide in new_guides),
        "minimum_condition_words": min(word_counts.values()),
        "word_counts": word_counts,
        "cluster_expanded": True,
        "hub_link_updated": True,
        "sitemap_registered": True,
        "reviewed_at": extension["reviewed_at"],
        "next_review_due": extension["next_review_due"],
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "williams-prader-willi-guides-v324.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
