#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import publish_special_needs_guides_v209 as shared
import publish_special_needs_guides_v209_compat as compat

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "v336" / "special-needs-guides" / "developmental-disabilities-sleep-support-plan.json"
BASE = "https://healthrenewal.org"
VERSION = 336
START = "<!-- special-needs-guides-v336:start -->"
END = "<!-- special-needs-guides-v336:end -->"
ALLOWED_HOSTS = {"www.nice.org.uk", "www.who.int", "publications.aap.org"}
PROHIBITED = re.compile(r"معاقين", re.IGNORECASE)


def words(value: Any) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", json.dumps(value, ensure_ascii=False)))


def load_data() -> dict[str, Any]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: dict[str, Any]) -> None:
    required = {
        "slug", "title", "description", "category", "audiences", "review_status",
        "external_review", "reviewed_at", "professional_limits", "when_to_seek_help",
        "intro", "sections", "checklist", "common_mistakes", "template", "sources",
    }
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing sleep-guide fields: {sorted(missing)}")
    if data["slug"] != "developmental-disabilities-sleep-support-plan":
        raise SystemExit("Unexpected sleep-guide slug")
    if data["review_status"] != "internally-reviewed":
        raise SystemExit("Sleep guide must retain an honest internal-review state")
    if data["external_review"] != "recommended-not-completed":
        raise SystemExit("Sleep guide must not overstate external clinical review")
    if not 90 <= len(data["description"]) <= 180:
        raise SystemExit("Sleep-guide meta description length is invalid")
    if words(data) < 900:
        raise SystemExit(f"Sleep guide is too thin: {words(data)} words")
    if len(data["intro"]) < 3:
        raise SystemExit("Sleep-guide introduction is incomplete")
    if len(data["sections"]) < 6 or any(len(section.get("paragraphs", [])) < 3 for section in data["sections"]):
        raise SystemExit("Sleep-guide sections are incomplete")
    if len(data["checklist"]) < 10 or len(data["common_mistakes"]) < 6 or len(data["template"]) < 10:
        raise SystemExit("Sleep-guide practical tools are incomplete")
    if len(data["sources"]) < 4:
        raise SystemExit("Sleep guide requires at least four primary or official sources")
    ids = [source.get("id") for source in data["sources"]]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise SystemExit("Sleep-guide source identifiers must be present and unique")
    for source in data["sources"]:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or parsed.netloc not in ALLOWED_HOSTS:
            raise SystemExit(f"Unapproved source host: {source['url']}")
        if source.get("id") == "aap-autism-insomnia-pathway" and source.get("doi") != "10.1542/peds.2012-0900I":
            raise SystemExit("AAP practice-pathway DOI contract failed")
    serialized = json.dumps(data, ensure_ascii=False)
    if PROHIBITED.search(serialized):
        raise SystemExit("Prohibited person-label language remains in sleep guide")
    if "دواء أو جرعة" not in data["professional_limits"] or "لا يوصي هذا الدليل" not in serialized:
        raise SystemExit("Medication boundary is not explicit enough")
    if not all(term in serialized for term in ("الشخير", "توقف التنفس", "أسبوعين", "خصوصية")):
        raise SystemExit("Sleep safety and monitoring contract is incomplete")


def render(data: dict[str, Any]) -> str:
    guide = dict(data)
    guide["source_ids"] = [source["id"] for source in data["sources"]]
    citations = [
        {
            "organization": source["organization"],
            "title": source["title"],
            "url": source["url"],
            "year": source["year"],
            "use": source["use"],
        }
        for source in data["sources"]
    ]
    old_base = shared.BASE
    shared.BASE = BASE
    try:
        return shared.render_guide(guide, citations)
    finally:
        shared.BASE = old_base


def link_hub(site: Path, data: dict[str, Any]) -> None:
    old_start, old_end = shared.START, shared.END
    shared.START, shared.END = START, END
    try:
        shared.link_hub(site, [data])
    finally:
        shared.START, shared.END = old_start, old_end


def publish(site: Path) -> dict[str, Any]:
    data = load_data()
    target = site / "special-needs" / data["slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")

    url = f"{BASE}/special-needs/{data['slug']}/"
    compat.MAIN_SITEMAP_MODE = "urlset"
    compat.compatible_upsert(site / "sitemap-special-needs.xml", [url], data["reviewed_at"])
    compat.compatible_upsert(site / "sitemap.xml", [url], data["reviewed_at"])
    link_hub(site, data)

    report = {
        "version": VERSION,
        "status": "passed",
        "slug": data["slug"],
        "generated_page": target.relative_to(site).as_posix(),
        "canonical_url": url,
        "word_count": words(data),
        "section_count": len(data["sections"]),
        "source_count": len(data["sources"]),
        "review_status": data["review_status"],
        "external_clinical_review_completed": False,
        "medication_boundary_visible": True,
        "sleep_apnoea_escalation_visible": True,
        "two_week_sleep_log_visible": True,
        "hub_linked": True,
        "sitemap_registered": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-sleep-support-v336.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
