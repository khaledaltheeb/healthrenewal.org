from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize_calendar_pages() -> None:
    from normalize_platform_shell import normalize_file

    for relative in (
        "sectors/calendars/index.html",
        "sectors/calendars/women/index.html",
    ):
        path = ROOT / relative
        for _ in range(4):
            result = normalize_file(path, ROOT, check_only=False)
            if result.status == "current":
                break
            if result.status not in {"updated", "current"}:
                raise SystemExit(f"Could not normalize {relative}: {result.status} {result.detail}")
        check = normalize_file(path, ROOT, check_only=True)
        if check.status != "current":
            raise SystemExit(f"Calendar page still needs normalization: {relative}: {check.status}")


def make_public_report_non_operational() -> None:
    path = ROOT / "scripts" / "publish_calendars_v221.py"
    text = path.read_text(encoding="utf-8")
    old = '''        "brand": "منصة روافد",
        "routes": routes,
        "womenDailyCheckpoints": 3,
        "womenWeeklyInsight": True,
        "menstruationTerminology": "الحيض",
        "sitemaps": ["sitemap-calendars.xml", "sitemap-women-calendar.xml"],
'''
    new = '''        "brand": "منصة روافد",
        "calendarsSectorPublished": True,
        "womenDailyCalendarPublished": True,
        "publishedCalendarFileCount": sum(routes.values()),
        "womenDailyCheckpoints": 3,
        "womenWeeklyInsight": True,
        "menstruationTerminology": "الحيض",
'''
    if old not in text:
        raise SystemExit("Calendar public report block was not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def restore_workflow() -> None:
    clean = '''name: Women daily calendar quality

on:
  pull_request:
    paths:
      - "sectors/women/daily-calendar/**"
      - "sectors/women/index.html"
      - "sectors/calendars/**"
      - "api/women-daily-calendar-v1.json"
      - "scripts/apply_homepage_v20.py"
      - "scripts/publish_calendars_v221.py"
      - "tests/test_women_daily_calendar.py"
      - "sitemap-women-calendar.xml"
      - "sitemap-calendars.xml"
      - ".github/workflows/women-daily-calendar.yml"
  push:
    branches:
      - main
      - agent/women-calendar-publish-v3
    paths:
      - "sectors/women/daily-calendar/**"
      - "sectors/women/index.html"
      - "sectors/calendars/**"
      - "api/women-daily-calendar-v1.json"
      - "scripts/apply_homepage_v20.py"
      - "scripts/publish_calendars_v221.py"
      - "tests/test_women_daily_calendar.py"
      - "sitemap-women-calendar.xml"
      - "sitemap-calendars.xml"
      - ".github/workflows/women-daily-calendar.yml"

permissions:
  contents: read

jobs:
  static-contract:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: Check JavaScript and Python syntax
        run: |
          node --check sectors/women/daily-calendar/calendar.js
          node --check sectors/women/daily-calendar/calendar-core.js
          node --check sectors/women/daily-calendar/calendar-enhancements.js
          node --check sectors/women/daily-calendar/service-worker.js
          python -m py_compile scripts/apply_homepage_v20.py scripts/publish_calendars_v221.py tests/test_women_daily_calendar.py
      - name: Validate JSON manifests
        run: |
          python - <<'PY'
          import json
          from pathlib import Path
          for path in [
              Path("sectors/women/daily-calendar/manifest.webmanifest"),
              Path("sectors/women/daily-calendar/editorial-manifest.json"),
              Path("api/women-daily-calendar-v1.json"),
          ]:
              json.loads(path.read_text(encoding="utf-8"))
              print(f"PASS {path}")
          PY
      - name: Run calendar contract without external dependencies
        run: |
          python - <<'PY'
          import runpy
          namespace = runpy.run_path("tests/test_women_daily_calendar.py")
          tests = [value for name, value in sorted(namespace.items()) if name.startswith("test_") and callable(value)]
          if len(tests) != 2:
              raise SystemExit(f"Expected 2 tests, found {len(tests)}")
          for test in tests:
              test()
              print(f"PASS {test.__name__}")
          PY
'''
    (ROOT / ".github" / "workflows" / "women-daily-calendar.yml").write_text(clean, encoding="utf-8")
    temporary = ROOT / "scripts" / "finalize_calendar_release_once.py"
    if temporary.exists():
        temporary.unlink()


def main() -> None:
    normalize_calendar_pages()
    make_public_report_non_operational()
    restore_workflow()


if __name__ == "__main__":
    main()
