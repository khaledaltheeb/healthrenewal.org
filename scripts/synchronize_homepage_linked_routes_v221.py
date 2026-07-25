#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 221
REQUIRED_HOME_LINKS = ('href="daily-tools/"', 'href="learning-paths/"')
REQUIRED_ROUTES = (
    Path("daily-tools/index.html"),
    Path("learning-paths/index.html"),
)
SLEEP_PAGE = Path("daily-tools/sleep-wind-down-plan/index.html")
SLEEP_ASSET = Path("assets/sleep-log-v49.js")
SLEEP_MARKERS = (
    'data-sleep-log',
    'data-design="marshmallow-v219"',
    'data-seo="institutional-v219"',
    'data-export-json',
    'data-export-csv',
    'data-delete-sleep',
    'لا تُرسل البيانات إلى خادم',
)


def run(script: str, site: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(site)],
        check=True,
    )


def daily_report_valid(site: Path) -> bool:
    path = site / "api" / "daily-tools-v24.json"
    if not path.is_file():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        report.get("version") == 24
        and report.get("design_contract") == 219
        and report.get("tools") == 8
        and report.get("paths") == 4
        and report.get("pages") == 14
        and report.get("local_only") is True
        and report.get("marshmallow_palette") is True
        and report.get("dark_text_box_shadow") is False
        and report.get("homepage_linked") is True
    )


def sleep_contract_valid(site: Path) -> bool:
    page = site / SLEEP_PAGE
    asset = site / SLEEP_ASSET
    if not page.is_file() or not asset.is_file():
        return False
    text = page.read_text(encoding="utf-8")
    if not all(marker in text for marker in SLEEP_MARKERS):
        return False
    if text.count('<meta name="description"') != 1 or text.count('<link rel="canonical"') != 1:
        return False
    runtime = asset.read_text(encoding="utf-8")
    if "localStorage" not in runtime or "fetch(" in runtime:
        return False
    return True


def publish_linked_routes(site: Path) -> None:
    # Verify the generic tool shell before the specialized sleep publisher
    # replaces one page with the tested external sleep-log-v49.js runtime.
    run("publish_daily_tools_v24.py", site)
    run("verify_daily_tools_v24.py", site)
    run("publish_sleep_log_v49.py", site)
    run("patch_sleep_svg_export_v65.py", site)
    run("apply_daily_tools_marshmallow_v219.py", site)


def synchronize(site: Path) -> dict[str, object]:
    homepage = site / "index.html"
    if not homepage.is_file():
        return {
            "contract": CONTRACT,
            "status": "skipped-no-homepage",
            "homepage_present": False,
            "links_present": False,
            "published": False,
        }

    source = homepage.read_text(encoding="utf-8")
    links_present = all(marker in source for marker in REQUIRED_HOME_LINKS)
    if not links_present:
        return {
            "contract": CONTRACT,
            "status": "skipped-links-not-declared",
            "homepage_present": True,
            "links_present": False,
            "published": False,
        }

    missing_before = [path.as_posix() for path in REQUIRED_ROUTES if not (site / path).is_file()]
    report_valid_before = daily_report_valid(site)
    sitemap_missing = not (site / "sitemap-tools-paths.xml").is_file()
    sleep_valid_before = sleep_contract_valid(site)
    published = bool(missing_before or not report_valid_before or sitemap_missing or not sleep_valid_before)

    if published:
        publish_linked_routes(site)

    missing_after = [path.as_posix() for path in REQUIRED_ROUTES if not (site / path).is_file()]
    if missing_after:
        raise SystemExit(f"Homepage-linked routes remain missing after synchronization: {missing_after}")
    if not daily_report_valid(site):
        raise SystemExit("Daily-tools publication report is missing or invalid after synchronization")
    if not sleep_contract_valid(site):
        raise SystemExit("Interactive local sleep-log contract remains incomplete after synchronization")

    homepage_after = homepage.read_text(encoding="utf-8")
    if not all(marker in homepage_after for marker in REQUIRED_HOME_LINKS):
        raise SystemExit("Daily-tools publisher removed homepage discovery links")

    daily_pages = len(list((site / "daily-tools").rglob("index.html")))
    learning_pages = len(list((site / "learning-paths").rglob("index.html")))
    if daily_pages != 9 or learning_pages != 5:
        raise SystemExit(
            f"Homepage-linked route counts are incomplete: daily={daily_pages}, learning={learning_pages}"
        )

    report = {
        "contract": CONTRACT,
        "status": "passed",
        "homepage_present": True,
        "links_present": True,
        "published": published,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "daily_tools_pages": daily_pages,
        "learning_path_pages": learning_pages,
        "daily_tools_report": "passed",
        "sitemap_present": (site / "sitemap-tools-paths.xml").is_file(),
        "publication_report_present": (site / "api" / "daily-tools-v24.json").is_file(),
        "sleep_log_page": SLEEP_PAGE.as_posix(),
        "sleep_log_asset": SLEEP_ASSET.as_posix(),
        "sleep_log_contract": "passed",
        "sleep_log_local_only": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-linked-routes-v221.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(synchronize(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
