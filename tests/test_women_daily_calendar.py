from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "sectors" / "women" / "daily-calendar"


def read(path: Path) -> str:
    assert path.is_file(), path
    return path.read_text(encoding="utf-8")


def test_women_daily_calendar_static_contract() -> None:
    required = (
        "index.html",
        "calendar.css",
        "calendar.js",
        "calendar-core.js",
        "calendar-enhancements.js",
        "calendar-enhancements.css",
        "manifest.webmanifest",
        "service-worker.js",
        "icon.svg",
        "editorial-manifest.json",
    )
    for filename in required:
        assert (APP / filename).is_file(), filename

    html = read(APP / "index.html")
    core = read(APP / "calendar-core.js")
    loader = read(APP / "calendar.js")
    enhancements = read(APP / "calendar-enhancements.js")
    enhancement_css = read(APP / "calendar-enhancements.css")
    service_worker = read(APP / "service-worker.js")
    webmanifest = json.loads(read(APP / "manifest.webmanifest"))
    editorial = json.loads(read(APP / "editorial-manifest.json"))
    api = json.loads(read(ROOT / "api" / "women-daily-calendar-v1.json"))
    publisher = read(ROOT / "scripts" / "apply_homepage_v20.py")

    for token in (
        "تقويم صحة المرأة اليومي",
        "كيف تشعرين الآن؟",
        "الحيض",
        "الفاصل بين بدايات الحيض",
        "ليس وسيلة لمنع الحمل",
        "تُحفظ محليًا",
    ):
        assert token in html or token in core, token

    for forbidden in ("الدورة الشهرية", "تتبع اختياري للدورة", "طول الحيض"):
        assert forbidden not in html
        assert forbidden not in core
        assert forbidden not in enhancements

    assert "calendar-enhancements.js?v=2.0.0" in loader
    assert "calendar-core.js?v=2.0.0" in loader
    assert "ما الذي يحتاجه جسدك قبل النوم؟" in enhancements
    assert "eveningBoostBank" in enhancements
    assert "weeklyInsightBody" in enhancements
    assert "UID:evening-${dateKey(date)}" in enhancements
    assert "preserveWellbeingFields" in enhancements
    assert "30 تذكيرًا مسائيًا" in enhancements
    assert "weekly-insight-grid" in enhancement_css
    assert 'CACHE_NAME = "rawafid-women-calendar-v4"' in service_worker
    assert "calendar-core.js?v=2.0.0" in service_worker
    assert "calendar-enhancements.js?v=2.0.0" in service_worker

    assert webmanifest["name"].endswith("منصة روافد")
    assert len(editorial["yearCoverage"]["dailyRequiredElements"]) == 10
    assert editorial["dailyCheckpoints"] == ["morning", "midday", "evening"]
    assert editorial["weeklyInsight"]["days"] == 7
    assert editorial["weeklyInsight"]["diagnostic"] is False
    assert editorial["menstruationTracking"]["approvedArabicTerm"] == "الحيض"
    assert editorial["privacy"]["remoteSubmission"] is False

    assert api["status"] == "passed"
    assert api["brand"] == "منصة روافد"
    assert api["dailyElements"] == 10
    assert api["dailyCheckpoints"] == 3
    assert api["eveningCheckIn"] is True
    assert api["weeklySevenDayInsight"] is True
    assert api["weeklyInsightDiagnostic"] is False
    assert api["pwaCacheVersion"] == 4

    assert "apply_homepage_v20_core.py" in publisher
    assert 'copy_tree("sectors/calendars")' in publisher
    assert 'copy_tree("sectors/women/daily-calendar")' in publisher
    assert 'register_sitemap("sitemap-calendars.xml")' in publisher
    assert 'register_sitemap("sitemap-women-calendar.xml")' in publisher
    assert 'href="sectors/women/daily-calendar/"' in publisher
    assert "منصة روافد" in publisher


def test_women_daily_calendar_has_no_remote_health_data_submission() -> None:
    core = read(APP / "calendar-core.js")
    enhancements = read(APP / "calendar-enhancements.js")
    loader = read(APP / "calendar.js")
    html = read(APP / "index.html")

    assert "<form" in html
    assert "action=" not in html
    for script in (core, enhancements, loader):
        assert "XMLHttpRequest" not in script
        assert "navigator.sendBeacon" not in script
        assert "FormData" not in script
        assert "sessionStorage" not in script
    assert "fetch(" not in core
    assert "fetch(" not in enhancements
    assert "localStorage" in core
    assert "localStorage" in enhancements
