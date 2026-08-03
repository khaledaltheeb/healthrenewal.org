from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALENDARS = ROOT / "sectors" / "calendars"
STUDENT = CALENDARS / "students"


def read(path: Path) -> str:
    assert path.exists(), f"Missing required file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_calendars_sector_contract() -> None:
    landing = read(CALENDARS / "index.html")
    women_gateway = read(CALENDARS / "women" / "index.html")
    sitemap = read(ROOT / "sitemap-calendars.xml")
    sitemap_index = read(ROOT / "sitemap-index.xml")

    assert "التقويمات التفاعلية" in landing
    assert "تقويم المرأة" in landing
    assert "تقويم الطلاب" in landing
    assert "تقويم الرياضيين" in landing
    assert 'href="students/"' in landing
    assert "/sectors/women/daily-calendar/" in women_gateway
    assert "https://healthrenewal.org/sectors/calendars/" in sitemap
    assert "https://healthrenewal.org/sectors/calendars/students/" in sitemap
    assert "sitemap-calendars.xml" in sitemap_index


def test_student_daily_calendar_contract() -> None:
    html = read(STUDENT / "index.html")
    css = read(STUDENT / "student-calendar.css")
    js = read(STUDENT / "student-calendar.js")
    manifest = json.loads(read(STUDENT / "manifest.webmanifest"))
    editorial = json.loads(read(STUDENT / "editorial-manifest.json"))
    api = json.loads(read(ROOT / "api" / "student-daily-calendar-v1.json"))
    workflow = read(ROOT / ".github" / "workflows" / "student-daily-calendar.yml")

    required_html = [
        "تقويم الطلاب التفاعلي",
        "مولّد خطة الدراسة",
        "قائمة الدراسة والتسليمات",
        "مؤقت جلسة الدراسة",
        "كيف يسير تركيزك الآن؟",
        "المراجعة المتباعدة",
        "العدّ التنازلي وخطة الرجوع",
        "الخطة الأسبوعية",
        'id="morningTime"',
        'id="noonTime"',
        'id="eveningTime"',
        'data-ics-days="365"',
    ]
    for token in required_html:
        assert token in html, token

    required_js = [
        "hr-student-daily-calendar-v1",
        "monthThemes",
        "morningBank",
        "noonBoostBank",
        "buildSmartPlan",
        "reviewDates",
        "[1,3,7,14,30]",
        "generateWeekPlan",
        "buildICS",
        "BEGIN:VALARM",
        "morning-${isoDate(date)}",
        "noon-${isoDate(date)}",
        "evening-${isoDate(date)}",
        "utcDayNumber",
        "d.setDate(d.getDate() + Number(days || 0))",
        "Math.max(5, total - wrap - recall)",
        "localStorage",
        "exportData",
        "importData",
        "Notification",
        "serviceWorker",
    ]
    for token in required_js:
        assert token in js, token

    forbidden_remote_submission = ["XMLHttpRequest", "sendBeacon", "FormData", "fetch("]
    for token in forbidden_remote_submission:
        assert token not in js, f"Unexpected remote submission primitive: {token}"

    assert "toISOString().slice(0,10)" not in js
    assert "dashboard-grid" in css
    assert "week-grid" in css
    assert "@media print" in css
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "./"
    assert len(editorial["dailyRequiredElements"]) == 7
    assert editorial["planningModules"]["spacedReviewIntervalsDays"] == [1, 3, 7, 14, 30]
    assert editorial["calendarIntegration"]["dailyEvents"] == ["morning", "midday", "evening"]
    assert editorial["privacy"]["localFirst"] is True
    assert editorial["privacy"]["remoteSubmission"] is False
    assert api["status"] == "passed"
    assert api["sector"] == "calendars"
    assert api["sectorDirectoryLinked"] is True
    assert api["localCalendarDateSafe"] is True
    assert api["standardYearDays"] == 365
    assert api["dailyCalendarEvents"] == 3
    assert api["spacedIntervalsDays"] == [1, 3, 7, 14, 30]
    assert api["weeklyLoadBalancing"] is True
    assert api["localFirst"] is True
    assert "node --check sectors/calendars/students/student-calendar.js" in workflow
