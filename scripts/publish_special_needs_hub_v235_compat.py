#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_special_needs_hub_v235 as hub

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


def publish(site: Path) -> dict[str, Any]:
    original_render = hub.render

    def render_with_compatibility(course: dict[str, Any], manifest: dict[str, Any]) -> str:
        source = original_render(course, manifest)

        old_emergency = "استخدم رقم الطوارئ والخدمات الصحية أو الحماية المختصة في بلدك"
        new_emergency = "استخدم رقم الطوارئ المحلية والخدمات الصحية أو الحماية المختصة في بلدك"
        if old_emergency not in source:
            raise SystemExit("Special-needs emergency guidance marker is missing")
        source = source.replace(old_emergency, new_emergency, 1)

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
        return hub.publish(site)
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
