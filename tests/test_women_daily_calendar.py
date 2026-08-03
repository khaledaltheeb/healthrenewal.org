from __future__ import annotations

import json
import re
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
    api_report = json.loads(
        (ROOT / "api" / "women-daily-calendar-v1.json").read_text(encoding="utf-8")
    )
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    women_index = (ROOT / "sectors" / "women" / "index.html").read_text(
        encoding="utf-8"
    )
    publisher = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
        encoding="utf-8"
    )

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
    assert "id=\"noonTime\"" in html
    assert "كيف تشعرين الآن؟" in html
    assert "الحيض" in html
    assert "الفاصل بين بدايات الحيض" in html
    for forbidden_term in ("الدورة الشهرية", "الدورة"):
        assert forbidden_term not in html
        assert forbidden_term not in js
    assert "طول الحيض" not in html
    assert "طول الحيض" not in js

    assert "صباح إيجابي" in js
    assert "morningBank" in js
    assert "noonBoostBank" in js
    assert "كيف تشعرين الآن؟" in js
    assert "UID:noon-${isoDate(date)}" in js
    assert "noonTime" in js
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
    assert len(manifest["yearCoverage"]["dailyRequiredElements"]) == 8
    assert manifest["calendarIntegration"]["middayReminder"] is True
    assert manifest["calendarIntegration"]["defaultNoonTime"] == "12:30"
    assert manifest["monthlyPrograms"] == 12
    assert manifest["cycleTracking"]["localStorageDefault"] is True
    assert manifest["cycleTracking"]["fertilityPrediction"] is False
    assert manifest["cycleTracking"]["contraceptionUse"] is False
    assert manifest["calendarIntegration"]["icsExport"] is True
    assert manifest["calendarIntegration"]["rangesInDays"] == [30, 90, 365]

    assert api_report["status"] == "passed"
    assert api_report["dailyElements"] == 8
    assert api_report["middayCheckIn"] is True
    assert api_report["feminineNoonBoost"] is True
    assert api_report["positiveMorningMessage"] is True
    assert api_report["pinkProfessionalDesign"] is True
    assert api_report["localFirst"] is True

    route = 'href="sectors/women/daily-calendar/"'
    assert route in homepage
    assert len(re.findall(r"<h3\b", homepage)) >= 16
    assert "/sectors/women/daily-calendar/" in women_index
    assert 'restore_static_route(\n            "sectors/women/daily-calendar"' in publisher
    assert 'restore_static_file(relative_path)' in publisher
    assert 'register_sitemap("sitemap-women-calendar.xml")' in publisher
    assert route in publisher


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
