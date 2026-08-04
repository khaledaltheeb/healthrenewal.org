from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"Expected one {label}, found {text.count(old)}")
    return text.replace(old, new, 1)


def main() -> None:
    core = ROOT / "scripts" / "apply_homepage_v20_core.py"
    publisher_path = ROOT / "scripts" / "apply_homepage_v20.py"
    publisher = core.read_text(encoding="utf-8")
    gate = '    run_publisher("enforce_health_publication_gate_v192.py")'
    calendar = '    run_publisher("publish_calendars_v221.py")'
    if calendar not in publisher:
        publisher = replace_once(publisher, gate, calendar + "\n" + gate, "health gate marker")
    publisher_path.write_text(publisher, encoding="utf-8")
    core.unlink()

    women_test = ROOT / "tests" / "test_women_daily_calendar.py"
    text = women_test.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    publisher = read(ROOT / "scripts" / "apply_homepage_v20.py")\n',
        '    publisher = read(ROOT / "scripts" / "apply_homepage_v20.py")\n    calendar_publisher = read(ROOT / "scripts" / "publish_calendars_v221.py")\n',
        "women publisher setup",
    )
    old = '''    assert "apply_homepage_v20_core.py" in publisher
    assert 'copy_tree("sectors/calendars")' in publisher
    assert 'copy_tree("sectors/women/daily-calendar")' in publisher
    assert 'register_sitemap("sitemap-calendars.xml")' in publisher
    assert 'register_sitemap("sitemap-women-calendar.xml")' in publisher
    assert 'href="sectors/women/daily-calendar/"' in publisher
    assert "منصة روافد" in publisher
'''
    new = '''    assert 'run_publisher("publish_calendars_v221.py")' in publisher
    assert publisher.index('run_publisher("publish_calendars_v221.py")') < publisher.index('run_publisher("enforce_health_publication_gate_v192.py")')
    assert 'copy_tree("sectors/calendars")' in calendar_publisher
    assert 'copy_tree("sectors/women/daily-calendar")' in calendar_publisher
    assert 'register_sitemap("sitemap-calendars.xml")' in calendar_publisher
    assert 'register_sitemap("sitemap-women-calendar.xml")' in calendar_publisher
    assert 'href="sectors/women/daily-calendar/"' in calendar_publisher
    assert "منصة روافد" in calendar_publisher
'''
    text = replace_once(text, old, new, "women publisher assertions")
    women_test.write_text(text, encoding="utf-8")

    student_test = ROOT / "tests" / "test_student_daily_calendar.py"
    text = student_test.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    publisher = read(ROOT / "scripts" / "apply_homepage_v20.py")\n',
        '    publisher = read(ROOT / "scripts" / "apply_homepage_v20.py")\n    calendar_publisher = read(ROOT / "scripts" / "publish_calendars_v221.py")\n',
        "student publisher setup",
    )
    text = replace_once(
        text,
        '    assert \'copy_tree("sectors/calendars")\' in publisher\n    assert \'register_sitemap("sitemap-calendars.xml")\' in publisher\n    assert \'href="sectors/calendars/"\' in publisher\n',
        '    assert \'run_publisher("publish_calendars_v221.py")\' in publisher\n    assert \'copy_tree("sectors/calendars")\' in calendar_publisher\n    assert \'register_sitemap("sitemap-calendars.xml")\' in calendar_publisher\n    assert \'href="sectors/calendars/"\' in calendar_publisher\n',
        "student publisher assertions",
    )
    student_test.write_text(text, encoding="utf-8")

    clean_workflow = '''name: Women daily calendar quality

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
    workflow = ROOT / ".github" / "workflows" / "women-daily-calendar.yml"
    workflow.write_text(clean_workflow, encoding="utf-8")

    for temporary in (
        ROOT / ".github" / "workflows" / "one-time-integrate-calendar-publisher.yml",
        ROOT / "scripts" / "integrate_calendar_publisher_once.py",
    ):
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
