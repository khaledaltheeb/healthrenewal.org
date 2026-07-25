#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_special_needs_hub_v235 as hub

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
PATHWAYS = (
    ("aac-daily-communication-access", "pathway-communication", "التواصل والوصول إلى المعلومات", "فتح دليل التواصل المعزز والبديل"),
    ("inclusive-classroom-adjustments-plan", "pathway-inclusive-learning", "التعلّم والتربية الدامجة", "فتح خطة التكييفات الصفية"),
    ("adaptive-skills-stepwise-teaching", "pathway-daily-skills", "المهارات اليومية والاستقلال", "فتح دليل تعليم المهارات اليومية"),
    ("sensory-regulation-daily-environment-plan", "pathway-sensory-regulation", "التنظيم الحسي والانتقالات", "فتح خطة التنظيم الحسي"),
    ("caregiver-wellbeing-sustainable-support-plan", "pathway-family-care", "الأسرة ومقدم الرعاية", "فتح خطة استدامة دعم مقدم الرعاية"),
    ("safeguarding-bullying-abuse-response-plan", "pathway-safeguarding", "الحماية والحقوق والمشاركة", "فتح دليل الحماية والاستجابة"),
    ("vision-access-orientation-learning", "pathway-sensory-mobility-access", "السمع والبصر والحركة", "فتح دليل الوصول البصري والحركة"),
    ("transition-adulthood-employment-independence", "pathway-adulthood", "الانتقال إلى الرشد والعمل", "فتح دليل الانتقال والاستقلال"),
)
LOCAL_SOURCE_MARKER = "data-special-needs-jordan-sources-v241"
ASHA_OLD = "https://www.asha.org/public/speech/disorders/aac/"
ASHA_CURRENT = "https://www.asha.org/Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication/"
JORDAN_SOURCES = (
    (
        "اليونسكو والأردن",
        "الإطار الوطني للإدماج والتنوع في التعليم ومسؤوليات بناء بيئة تعليمية دامجة",
        "https://www.unesco.org/en/articles/jordan-launches-national-framework-inclusion-and-diversity-education-unesco",
    ),
    (
        "وزارة التربية والتعليم واليونسكو",
        "الخطة الاستراتيجية للتعليم في الأردن 2026–2030: الوصول والجودة والإنصاف والإدماج والمرونة",
        "https://www.unesco.org/en/articles/jordans-education-strategic-plan-2026-2030?hub=422",
    ),
    (
        "اليونيسف في الأردن",
        "برامج التعليم والوصول الدامج للأطفال والأسر داخل السياق الأردني",
        "https://www.unicef.org/jordan/education",
    ),
)


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def sync_hub_sitemaps(site: Path) -> None:
    ET.register_namespace("", SITEMAP_NS)
    canonical = f"{hub.BASE}/special-needs/"
    child_url = f"{hub.BASE}/sitemap-special-needs.xml"

    for name in ("sitemap-special-needs.xml", "sitemap.xml"):
        path = site / name
        if not path.is_file():
            raise SystemExit(f"Missing sitemap while enhancing special-needs hub: {path}")
        tree = ET.parse(path)
        root = tree.getroot()
        mode = root.tag.rsplit("}", 1)[-1]

        if mode == "urlset":
            matches = [
                item
                for item in root.findall("{*}url")
                if (item.findtext("{*}loc") or "").strip() == canonical
            ]
            if len(matches) > 1:
                raise SystemExit(f"Duplicate special-needs hub URLs in {path}")
            item = matches[0] if matches else ET.SubElement(root, qualify(root, "url"))
            loc = item.find("{*}loc")
            if loc is None:
                loc = ET.SubElement(item, qualify(root, "loc"))
            loc.text = canonical
            values = {
                "lastmod": hub.UPDATED,
                "changefreq": "weekly",
                "priority": "0.95",
            }
            for key, value in values.items():
                node = item.find(f"{{*}}{key}")
                if node is None:
                    node = ET.SubElement(item, qualify(root, key))
                node.text = value
        elif mode == "sitemapindex" and name == "sitemap.xml":
            matches = [
                item
                for item in root.findall("{*}sitemap")
                if (item.findtext("{*}loc") or "").strip() == child_url
            ]
            if len(matches) > 1:
                raise SystemExit("Duplicate special-needs child sitemaps in the main sitemap index")
            item = matches[0] if matches else ET.SubElement(root, qualify(root, "sitemap"))
            loc = item.find("{*}loc")
            if loc is None:
                loc = ET.SubElement(item, qualify(root, "loc"))
            loc.text = child_url
            lastmod = item.find("{*}lastmod")
            if lastmod is None:
                lastmod = ET.SubElement(item, qualify(root, "lastmod"))
            lastmod.text = hub.UPDATED
        else:
            raise SystemExit(f"Unsupported sitemap mode for {path}: {mode}")

        tree.write(path, encoding="utf-8", xml_declaration=True)


def render_local_sources() -> str:
    items = "".join(
        f'<li {LOCAL_SOURCE_MARKER}><a href="{url}" rel="noopener noreferrer">{organization} — {topic}</a></li>'
        for organization, topic, url in JORDAN_SOURCES
    )
    return items


def publish(site: Path) -> dict[str, Any]:
    original_render = hub.render

    def render_with_compatibility(course: dict[str, Any], manifest: dict[str, Any]) -> str:
        source = original_render(course, manifest)

        old_emergency = "استخدم رقم الطوارئ والخدمات الصحية أو الحماية المختصة في بلدك"
        new_emergency = "استخدم رقم الطوارئ المحلية والخدمات الصحية أو الحماية المختصة في بلدك"
        if old_emergency not in source:
            raise SystemExit("Special-needs emergency guidance marker is missing")
        source = source.replace(old_emergency, new_emergency, 1)

        if ASHA_OLD not in source:
            raise SystemExit("Legacy ASHA AAC source URL is missing")
        source = source.replace(ASHA_OLD, ASHA_CURRENT, 1)

        source_list_end = "</ul></section>"
        if source.count(source_list_end) < 1:
            raise SystemExit("Special-needs source list insertion point is missing")
        local_sources = render_local_sources()
        source = source.replace(source_list_end, local_sources + source_list_end, 1)
        if source.count(LOCAL_SOURCE_MARKER) != len(JORDAN_SOURCES):
            raise SystemExit("Jordan source insertion contract failed")

        for slug, anchor, title, old_label in PATHWAYS:
            absolute = f"{hub.BASE}/special-needs/{slug}/"
            internal = f"{hub.BASE_PATH}special-needs/{slug}/"
            source = source.replace(absolute, f"{hub.BASE}/special-needs/#{anchor}")
            source = source.replace(internal, f"#{anchor}")
            source = source.replace(
                f'<article class="path-card"><h3>{title}</h3>',
                f'<article class="path-card" id="{anchor}"><h3>{title}</h3>',
                1,
            )
            source = source.replace(f">{old_label}</a>", ">استعراض موارد هذا المسار</a>", 1)
            if absolute in source or internal in source:
                raise SystemExit(f"Pathway guide route remains duplicated before library injection: {slug}")

        return source

    hub.render = render_with_compatibility
    try:
        report = hub.publish(site)
        sync_hub_sitemaps(site)
        report.pop("robots_child_sitemap_changed", None)
        report["robots_child_sitemap_registered"] = True
        report["sitemap_hub_registered"] = True
        report["source_count"] = 10
        report["jordan_source_count"] = len(JORDAN_SOURCES)
        report["asha_aac_source_updated"] = True
        report_path = site / "api" / "special-needs-hub-v235.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        hub.render = original_render


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
