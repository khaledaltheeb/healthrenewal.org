#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_sitemap_index_v304_core as core
from ai_machine_readable_v1 import AI_USER_AGENTS, enhance_site, sync_robots as sync_ai_robots

BASE_URL = core.BASE_URL
EXCLUDED_PARTS = core.EXCLUDED_PARTS
EXCLUDED_FILES = core.EXCLUDED_FILES
PRIMARY_FILENAME = core.PRIMARY_FILENAME
FAMILY_PREFIX = core.FAMILY_PREFIX
INDEX_FILENAME = core.INDEX_FILENAME
REPORT_FILENAME = core.REPORT_FILENAME
FAMILIES = core.FAMILIES
MetadataParser = core.MetadataParser
metadata = core.metadata
is_verification_artifact = core.is_verification_artifact
normalized_url = core.normalized_url
family_for = core.family_for
is_indexable = core.is_indexable
write_urlset = core.write_urlset


def sync_robots(root: Path, base_url: str = BASE_URL) -> list[str]:
    return sync_ai_robots(root, base_url, PRIMARY_FILENAME, INDEX_FILENAME)


def generate(root: Path, base_url: str = BASE_URL) -> dict[str, object]:
    root = root.resolve()
    base_url = base_url.rstrip("/") + "/"
    report = core.generate(root, base_url)
    machine = enhance_site(root, base_url)
    report["robots_policy"] = "explicit-ai-and-public-crawling"
    report["explicit_ai_user_agents"] = list(AI_USER_AGENTS)
    report["preserved_custom_domain_sitemaps"] = machine["preserved_custom_domain_sitemaps"]
    report["machine_readable"] = {
        key: value
        for key, value in machine.items()
        if key not in {"explicit_ai_user_agents", "preserved_custom_domain_sitemaps"}
    }
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_FILENAME).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    print(json.dumps(generate(args.root, args.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
