#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import publish_williams_prader_willi_v324 as previous

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v325" / "smith-magenis-pitt-hopkins-guides-ar.json"
VERSION = 325
EXPECTED = ("smith-magenis-syndrome", "pitt-hopkins-syndrome")


def read_payload() -> dict:
    try:
        data = json.loads(CONTENT.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid v325 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("v325 content must be an object")
    return data


def is_https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(data: dict) -> list[dict]:
    render_base = previous.base
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("v325 identity contract failed")
    if data.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("v325 review state must remain honest")
    for key in ("reviewed_at", "next_review_due"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get(key, ""))):
            raise SystemExit(f"v325 {key} is invalid")
    guides = data.get("guides")
    if not isinstance(guides, list) or len(guides) != 2:
        raise SystemExit("v325 requires exactly two condition guides")
    if tuple(guide.get("slug") for guide in guides) != EXPECTED:
        raise SystemExit("v325 condition routes are incomplete or out of order")
    serialized = json.dumps(data, ensure_ascii=False)
    if render_base.BANNED.search(serialized) or render_base.UNSUPPORTED.search(serialized):
        raise SystemExit("v325 contains banned terminology or unsupported promises")

    for guide in guides:
        required = ("title", "short_title", "english_name", "meta_description", "lead", "warning")
        if any(not str(guide.get(key, "")).strip() for key in required):
            raise SystemExit(f"Incomplete v325 guide identity: {guide.get('slug')}")
        if len(guide.get("key_facts", [])) < 5:
            raise SystemExit(f"Insufficient v325 key facts: {guide['slug']}")
        sections = guide.get("sections")
        sources = guide.get("sources")
        if not isinstance(sections, list) or len(sections) != 7:
            raise SystemExit(f"Each v325 condition needs seven sections: {guide['slug']}")
        if not isinstance(sources, list) or len(sources) < 7:
            raise SystemExit(f"Each v325 condition needs at least seven sources: {guide['slug']}")
        if len(guide.get("action_steps", [])) < 8 or len(guide.get("urgent", [])) < 6:
            raise SystemExit(f"v325 action or urgent depth failed: {guide['slug']}")
        if len(guide.get("myths", [])) < 5 or len(guide.get("faqs", [])) < 5:
            raise SystemExit(f"v325 myth or FAQ depth failed: {guide['slug']}")

        source_index: dict[str, dict] = {}
        urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate v325 source id in {guide['slug']}: {sid}")
            if not is_https(url) or url in urls:
                raise SystemExit(f"Invalid or duplicate v325 source URL in {guide['slug']}: {url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid v325 source level: {guide['slug']}/{sid}")
            if any(not str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete v325 source: {guide['slug']}/{sid}")
            source_index[sid] = source
            urls.add(url)

        section_ids: set[str] = set()
        used: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            source_ids = section.get("source_ids", [])
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Invalid v325 section id: {guide['slug']}/{section_id}")
            if not str(section.get("title", "")).strip() or not str(section.get("summary", "")).strip():
                raise SystemExit(f"Incomplete v325 section: {guide['slug']}/{section_id}")
            if len(section.get("points", [])) < 6 or not source_ids:
                raise SystemExit(f"v325 section depth failed: {guide['slug']}/{section_id}")
            if any(source_id not in source_index for source_id in source_ids):
                raise SystemExit(f"Unknown v325 source reference: {guide['slug']}/{section_id}")
            section_ids.add(section_id)
            used.update(source_ids)
        if set(source_index) - used:
            raise SystemExit(f"Unused v325 sources in {guide['slug']}: {sorted(set(source_index) - used)}")
    return guides


def combined_payload(extension: dict) -> tuple[dict, list[dict], list[dict]]:
    previous_extension = previous.read_payload()
    previous_combined, previous_base, previous_added = previous.combined_payload(previous_extension)
    previous_guides = deepcopy(previous_base + previous_added)
    new_guides = validate_payload(extension)
    slugs = [guide["slug"] for guide in previous_guides + new_guides]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("v325 duplicates an existing condition route")

    combined = deepcopy(previous_combined)
    combined["version"] = VERSION
    combined["review_status"] = extension["review_status"]
    combined["reviewed_at"] = extension["reviewed_at"]
    combined["next_review_due"] = extension["next_review_due"]
    combined["cluster"].update(extension.get("cluster_updates", {}))
    combined["guides"] = deepcopy(previous_guides + new_guides)
    return combined, previous_guides, new_guides


def render_expanded_cluster(data: dict, guides: list[dict]) -> str:
    page = previous.render_expanded_cluster(data, guides)
    page, count = re.subn(
        r'<section class="wrap panel"><h2>منهج التوسع التالي</h2>.*?</section>',
        '<section class="wrap panel"><h2>منهج التوسع التالي</h2><p>يضم المركز الآن سبعة أدلة مستقلة: ريت، والكروموسوم X الهش، وأنجلمان، وويليامز، وبرادر–ويلي، وسميث–ماجينيس، وبيت–هوبكنز. تستمر الإضافة بعد فحص عدم التكرار، وربط المحاور بالمصادر الأصلية، واختبار العمق والفهرسة وحالة المراجعة.</p></section>',
        page,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit("v325 could not replace the five-condition cluster roadmap")
    return page


def publish(site: Path) -> dict:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    extension = read_payload()
    combined, previous_guides, new_guides = combined_payload(extension)
    render_base = previous.base

    missing_previous = [
        guide["slug"]
        for guide in previous_guides
        if not (site / "special-needs" / guide["slug"] / "index.html").is_file()
    ]
    if missing_previous:
        raise SystemExit(f"v325 requires v323 and v324 production layers first: {missing_previous}")

    generated: list[str] = []
    word_counts: dict[str, int] = {}
    all_guides = previous_guides + new_guides
    for guide in new_guides:
        page = render_base.render_condition(guide, combined, all_guides)
        words = render_base.text_words(page)
        if words < 1550:
            raise SystemExit(f"v325 condition page is too shallow: {guide['slug']}={words}")
        if page.lower().count("<h1") != 1 or page.count('class="section-card"') != 7:
            raise SystemExit(f"v325 rendered structure failed: {guide['slug']}")
        if "MedicalWebPage" not in page or "FAQPage" not in page or render_base.BANNED.search(page):
            raise SystemExit(f"v325 rendered metadata or language failed: {guide['slug']}")
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

    render_base.patch_hub(site, combined, all_guides)
    render_base.update_sitemap(site, combined, all_guides)

    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": extension["review_status"],
        "external_clinical_review_completed": False,
        "cluster_slug": combined["cluster"]["slug"],
        "previous_condition_count": len(previous_guides),
        "added_condition_count": len(new_guides),
        "total_condition_count": len(all_guides),
        "added_condition_slugs": [guide["slug"] for guide in new_guides],
        "all_condition_slugs": [guide["slug"] for guide in all_guides],
        "generated_pages": generated,
        "source_count": sum(len(guide["sources"]) for guide in new_guides),
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
    (api / "smith-magenis-pitt-hopkins-guides-v325.json").write_text(
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
