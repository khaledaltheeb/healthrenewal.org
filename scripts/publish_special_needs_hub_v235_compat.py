#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_special_needs_hub_v235 as hub


def publish(site: Path) -> dict[str, Any]:
    original_render = hub.render

    def render_with_emergency_marker(course: dict[str, Any], manifest: dict[str, Any]) -> str:
        source = original_render(course, manifest)
        old = "استخدم رقم الطوارئ والخدمات الصحية أو الحماية المختصة في بلدك"
        new = "استخدم رقم الطوارئ المحلية والخدمات الصحية أو الحماية المختصة في بلدك"
        if old not in source:
            raise SystemExit("Special-needs emergency guidance marker is missing")
        return source.replace(old, new, 1)

    hub.render = render_with_emergency_marker
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
