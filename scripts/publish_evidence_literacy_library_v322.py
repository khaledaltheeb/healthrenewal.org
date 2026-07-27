#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import publish_evidence_literacy_library_v322_core as core
from publish_evidence_literacy_library_v322_core import *  # noqa: F401,F403

ROOT = Path(__file__).resolve().parents[1]
TRUST_SOURCE = ROOT / "trust" / "index.html"


def publish(site: Path) -> dict:
    if not TRUST_SOURCE.is_file():
        raise SystemExit(f"Missing institutional trust source: {TRUST_SOURCE}")
    trust_target = site / "trust" / "index.html"
    trust_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRUST_SOURCE, trust_target)
    trust_source = trust_target.read_text(encoding="utf-8")
    trust_words = core.words(trust_source)
    if trust_words < 1100 or trust_source.count("<h1") != 1:
        raise SystemExit({"trust_page_depth_failed": {"words": trust_words}})
    if 'rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/trust/"' not in trust_source:
        raise SystemExit("Trust page canonical contract failed")
    if 'application/ld+json' not in trust_source or "لم تكتمل مراجعة خارجية مستقلة" not in trust_source:
        raise SystemExit("Trust page structure or review disclosure failed")

    report = core.publish(site)
    core.update_sitemap(site, ["/trust/"], report["reviewed_at"])
    report.update(
        {
            "trust_page_published": True,
            "trust_page_path": "trust/index.html",
            "trust_page_words": trust_words,
            "trust_page_review_status": "internally-reviewed-external-methodology-review-required",
            "trust_page_sitemap_registered": True,
        }
    )
    api_path = site / "api" / "evidence-literacy-library-v322.json"
    api_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
