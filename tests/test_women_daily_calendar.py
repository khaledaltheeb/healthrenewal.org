from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "sectors" / "women" / "daily-calendar"


def test_women_daily_calendar_static_contract() -> None:
    required_files = (
        "index.html",
        "calendar.css",
        "calendar.js",
        "manifest.webmanifest",
        "service-worker.js",
        "icon.svg",
        "editorial-manifest.json",
    )
    for filename in required_files:
        assert (APP / filename).is_file(), filename

    html = (APP / "index.html").read_text(encoding="utf-8")
    css = (APP / "calendar.css").read_text(encoding="utf-8")
    js = (APP / "calendar.js").read_text(encoding="utf-8")
    manifest = json.loads((APP / "editorial-manifest.json").read_text(encoding="utf-8"))

    assert '<html lang="ar" dir="rtl">' in html
    assert "تقويم صحة المرأة اليومي" in html
    assert "معلومة" in html
    assert "نصيحة" in html
    assert "فكرة" in html
    assert "اقتراح" in html
    assert "10 دقائق" in html
    assert "ليس وسيلة لمنع الحمل" in html
    assert "تُحفظ محليًا" in html
    assert "تقويم الهاتف" in html

    assert "صباح إيجابي" in js
    assert "morningBank" in js
    assert "factBank" in js
    assert "tipBank" in js
    assert "ideaBank" in js
    assert "suggestionBank" in js
    assert "tenMinuteBank" in js
    assert "localStorage" in js
    assert "BEGIN:VCALENDAR" in js
    assert "BEGIN:VALARM" in js
    assert "Notification.requestPermission" in js
    assert "includeCycleInExport" in js
    assert "fertile" not in js.lower()
    assert "ovulation" not in js.lower()

    for pink_token in ("#702857", "#fffafc", "#f8edf3", "#5b2148"):
        assert pink_token in css or pink_token in html

    assert manifest["yearCoverage"]["standardYearDays"] == 365
    assert manifest["yearCoverage"]["leapDaySupported"] is True
    assert len(manifest["yearCoverage"]["dailyRequiredElements"]) == 6
    assert manifest["monthlyPrograms"] == 12
    assert manifest["cycleTracking"]["localStorageDefault"] is True
    assert manifest["cycleTracking"]["fertilityPrediction"] is False
    assert manifest["cycleTracking"]["contraceptionUse"] is False
    assert manifest["calendarIntegration"]["icsExport"] is True
    assert manifest["calendarIntegration"]["rangesInDays"] == [30, 90, 365]


def test_women_daily_calendar_has_no_remote_health_data_submission() -> None:
    html = (APP / "index.html").read_text(encoding="utf-8")
    js = (APP / "calendar.js").read_text(encoding="utf-8")

    assert "<form" in html
    assert "action=" not in html
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
    assert "navigator.sendBeacon" not in js
    assert "FormData" not in js
    assert "sessionStorage" not in js
