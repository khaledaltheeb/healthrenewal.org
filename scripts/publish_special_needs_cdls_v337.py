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
SOURCE = ROOT / "content" / "v337" / "special-needs-guides" / "cornelia-de-lange-syndrome.json"
BASE = "https://healthrenewal.org"
VERSION = 337
START = "<!-- special-needs-guides-v337:start -->"
END = "<!-- special-needs-guides-v337:end -->"
ALLOWED_HOSTS = {"www.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov", "www.orpha.net", "rarediseases.org"}
PROHIBITED = re.compile(r"معاقين", re.IGNORECASE)


def words(value: Any) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", json.dumps(value, ensure_ascii=False)))


def canonical_path(data: dict[str, Any]) -> str:
    return f"/special-needs/conditions/{data['slug']}/"


def canonical_url(data: dict[str, Any]) -> str:
    return BASE + canonical_path(data)


def load_data() -> dict[str, Any]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: dict[str, Any]) -> None:
    required = {
        "slug", "title", "description", "category", "audiences", "review_status",
        "external_review", "reviewed_at", "rights_classification", "professional_limits",
        "when_to_seek_help", "intro", "sections", "practical_tips", "avoid", "sources",
    }
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing CdLS guide fields: {sorted(missing)}")
    if data["slug"] != "cornelia-de-lange-syndrome":
        raise SystemExit("Unexpected CdLS slug")
    if data["review_status"] != "internally-reviewed":
        raise SystemExit("CdLS guide must retain internally-reviewed status")
    if data["external_review"] != "recommended-not-completed":
        raise SystemExit("CdLS guide must not overstate external review")
    if data["rights_classification"] != "link-cite-and-original-summary-only":
        raise SystemExit("CdLS rights classification changed")
    if not 90 <= len(data["description"]) <= 180:
        raise SystemExit("CdLS meta description length is invalid")
    if words(data) < 1400:
        raise SystemExit(f"CdLS guide is too thin: {words(data)} words")
    if len(data["intro"]) < 3 or len(data["sections"]) < 10:
        raise SystemExit("CdLS guide hierarchy is incomplete")
    if any(len(section.get("paragraphs", [])) < 3 for section in data["sections"]):
        raise SystemExit("Every CdLS section requires at least three paragraphs")
    if len(data["practical_tips"]) < 20 or len(data["avoid"]) < 8:
        raise SystemExit("CdLS practical guidance is incomplete")
    if len(data["sources"]) < 4:
        raise SystemExit("CdLS guide requires four governed sources")
    ids = [source.get("id") for source in data["sources"]]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise SystemExit("CdLS source IDs must be unique")
    for source in data["sources"]:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or parsed.netloc not in ALLOWED_HOSTS:
            raise SystemExit(f"Unapproved CdLS source host: {source['url']}")
        if not source.get("verified_at"):
            raise SystemExit("Every CdLS source needs a verification date")
    consensus = next(item for item in data["sources"] if item["id"] == "international-consensus-2018")
    if (
        consensus.get("doi") != "10.1038/s41576-018-0031-0"
        or consensus.get("pmid") != "29995837"
        or consensus.get("pmcid") != "PMC7136165"
    ):
        raise SystemExit("CdLS consensus identifiers are incomplete")
    serialized = json.dumps(data, ensure_ascii=False)
    if PROHIBITED.search(serialized):
        raise SystemExit("Prohibited terminology remains in CdLS guide")
    for marker in ("لا يشخّص", "دواء أو جرعة", "الفحص الجيني", "الانتقال إلى الرشد", "التواصل"):
        if marker not in serialized:
            raise SystemExit(f"CdLS safety or scope marker missing: {marker}")


def render(data: dict[str, Any]) -> str:
    guide = dict(data)
    guide["source_ids"] = [source["id"] for source in data["sources"]]
    guide["checklist"] = data["practical_tips"]
    guide["common_mistakes"] = data["avoid"]
    guide["template"] = [
        "أولوية الشخص والأسرة لهذا الشهر",
        "التغير الصحي أو الوظيفي المرصود",
        "وسيلة التواصل المستخدمة",
        "علامات الألم المعتادة والجديدة",
        "القياسات أو النتائج التي يجب إحضارها",
        "الأدوية وهدف كل دواء وآثاره المحتملة",
        "سؤال التشخيص أو المتابعة المطلوب حسمه",
        "الهدف الوظيفي للتدخل المقترح",
        "من المسؤول عن المتابعة والموعد التالي",
        "ما الذي سيعد تحسنًا أو سببًا لإيقاف الخطة",
    ]
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
        page = shared.render_guide(guide, citations)
    finally:
        shared.BASE = old_base
    old_url = f"{BASE}/special-needs/{data['slug']}/"
    page = page.replace(old_url, canonical_url(data))
    identifiers = (
        '<section class="card" aria-labelledby="cdls-identifiers">'
        '<h2 id="cdls-identifiers">معرفات المرجع الأساسي</h2>'
        '<p>DOI: 10.1038/s41576-018-0031-0 · PMID: 29995837 · PMCID: PMC7136165</p>'
        '</section>'
    )
    return page.replace('<section class="sources"', identifiers + '<section class="sources"', 1)


def link_hub(site: Path, data: dict[str, Any]) -> bool:
    hub = site / "special-needs" / "index.html"
    target_route = canonical_path(data)
    if hub.is_file() and target_route in hub.read_text(encoding="utf-8", errors="replace"):
        return True
    old_start, old_end = shared.START, shared.END
    old_base = shared.BASE
    shared.START, shared.END = START, END
    shared.BASE = BASE
    try:
        shared.link_hub(site, [data])
    finally:
        shared.START, shared.END = old_start, old_end
        shared.BASE = old_base
    if not hub.is_file():
        return False
    source = hub.read_text(encoding="utf-8", errors="replace")
    source = source.replace(
        f"/special-needs/{data['slug']}/",
        target_route,
    ).replace(
        f"{BASE}/special-needs/{data['slug']}/",
        canonical_url(data),
    )
    hub.write_text(source, encoding="utf-8")
    return target_route in source


def publish(site: Path) -> dict[str, Any]:
    data = load_data()
    target = site / "special-needs" / "conditions" / data["slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")

    url = canonical_url(data)
    compat.MAIN_SITEMAP_MODE = "urlset"
    compat.compatible_upsert(site / "sitemap-special-needs.xml", [url], data["reviewed_at"])
    compat.compatible_upsert(site / "sitemap.xml", [url], data["reviewed_at"])
    hub_linked = link_hub(site, data)

    competing = site / "special-needs" / data["slug"] / "index.html"
    if competing.is_file():
        raise SystemExit(f"Competing CdLS route must not be created: {competing}")

    report = {
        "version": VERSION,
        "status": "passed",
        "slug": data["slug"],
        "generated_page": target.relative_to(site).as_posix(),
        "canonical_url": url,
        "word_count": words(data),
        "section_count": len(data["sections"]),
        "practical_tip_count": len(data["practical_tips"]),
        "source_count": len(data["sources"]),
        "review_status": data["review_status"],
        "external_review_completed": False,
        "professional_limits_visible": True,
        "consensus_identifiers_visible": True,
        "hub_linked": hub_linked,
        "sitemap_registered": True,
        "single_canonical_route": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-cdls-v337.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
