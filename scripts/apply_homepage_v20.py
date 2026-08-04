from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
CORE = ROOT / "scripts" / "apply_homepage_v20_core.py"
BASE_URL = "https://healthrenewal.org/"


def run_core() -> None:
    subprocess.run([sys.executable, str(CORE), str(SITE)], check=True)


def copy_tree(route: str) -> int:
    source = ROOT / route
    target = SITE / route
    if not source.is_dir():
        raise SystemExit(f"Missing calendar route: {route}")
    shutil.copytree(source, target, dirs_exist_ok=True)
    return sum(1 for path in target.rglob("*") if path.is_file())


def copy_file(relative_path: str) -> None:
    source = ROOT / relative_path
    target = SITE / relative_path
    if not source.is_file():
        raise SystemExit(f"Missing calendar publication file: {relative_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def brand_calendar_tree(route: str) -> None:
    root = SITE / route
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".js", ".json", ".webmanifest"}:
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace("Health Renewal", "منصة روافد")
        text = text.replace("منصة الصحة النفسية وذوي الاحتياجات الخاصة", "منصة روافد")
        path.write_text(text, encoding="utf-8")


def register_sitemap(name: str) -> None:
    sitemap = SITE / name
    index = SITE / "sitemap.xml"
    if not sitemap.is_file() or not index.is_file():
        raise SystemExit(f"Missing sitemap publication input: {name}")
    target = BASE_URL + name
    tree = ET.parse(index)
    root = tree.getroot()
    kind = root.tag.rsplit("}", 1)[-1]
    prefix = root.tag.split("}", 1)[0] + "}" if root.tag.startswith("{") else ""
    if kind == "sitemapindex":
        existing = {(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")}
        if target not in existing:
            item = ET.SubElement(root, prefix + "sitemap")
            ET.SubElement(item, prefix + "loc").text = target
    elif kind == "urlset":
        existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
        child = ET.parse(sitemap).getroot()
        for node in child.findall("{*}url/{*}loc"):
            url = (node.text or "").strip()
            if not url or url in existing:
                continue
            item = ET.SubElement(root, prefix + "url")
            ET.SubElement(item, prefix + "loc").text = url
            existing.add(url)
    else:
        raise SystemExit(f"Unsupported sitemap root: {kind}")
    tree.write(index, encoding="utf-8", xml_declaration=True)


def inject_homepage_cards() -> None:
    path = SITE / "index.html"
    text = path.read_text(encoding="utf-8")
    if 'href="sectors/women/daily-calendar/"' not in text:
        anchor = 'href="sectors/women/">فتح قسم المرأة</a></article>'
        cards = (
            '<article class="card" data-women-daily-calendar-v2><span class="tag">3 محطات يومية</span>'
            '<h3 class="item-title">تقويم صحة المرأة اليومي</h3>'
            '<p>صباح إيجابي، وقفة ظهر، إغلاق مسائي، تتبع اختياري للحيض، وملخص محلي لسبعة أيام.</p>'
            '<a href="sectors/women/daily-calendar/">فتح تقويم المرأة</a></article>'
            '<article class="card" data-calendars-sector-v1><span class="tag">تخطيط وتذكيرات</span>'
            '<h3 class="item-title">قطاع التقويمات التفاعلية</h3>'
            '<p>تقويمات للمرأة والطلاب مع خطط يومية وتذكيرات هاتف وخصوصية محلية.</p>'
            '<a href="sectors/calendars/">فتح قطاع التقويمات</a></article>'
        )
        if anchor not in text:
            raise SystemExit("Women homepage card anchor was not found")
        text = text.replace(anchor, anchor + cards, 1)
    path.write_text(text, encoding="utf-8")

    report_path = SITE / "api" / "homepage-v20.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["version"] = max(221, int(report.get("version", 0)))
        report["target_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        report["h3"] = len(re.findall(r"<h3\b", text))
        report["calendars_sector_published"] = True
        report["women_daily_calendar_published"] = True
        report["calendar_sitemaps_registered"] = True
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def inject_women_sector_card() -> None:
    source = ROOT / "sectors" / "women" / "index.html"
    target = SITE / "sectors" / "women" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    text = target.read_text(encoding="utf-8")
    if "/sectors/women/daily-calendar/" not in text:
        marker = "<section><h2>الأدلة المنشورة</h2>"
        block = (
            '<section aria-labelledby="women-calendar-title"><h2 id="women-calendar-title">تقويم المرأة اليومي</h2>'
            '<div class="grid"><article class="card"><span class="tag">محلي وآمن</span>'
            '<h2>من الصباح إلى المساء</h2><p>رسالة صباحية، وقفة ظهر، إغلاق مسائي، ملخص سبعة أيام، '
            'وتتبع اختياري للحيض مع تذكيرات الهاتف.</p>'
            '<a href="/sectors/women/daily-calendar/">فتح التقويم اليومي ←</a></article></div></section>'
        )
        if marker not in text:
            raise SystemExit("Women sector guides marker was not found")
        text = text.replace(marker, block + marker, 1)
    text = text.replace("Health Renewal", "منصة روافد")
    target.write_text(text, encoding="utf-8")


def publish_calendars() -> None:
    routes = {
        "calendars": copy_tree("sectors/calendars"),
        "women_daily_calendar": copy_tree("sectors/women/daily-calendar"),
    }
    for relative_path in (
        "api/student-daily-calendar-v1.json",
        "api/women-daily-calendar-v1.json",
        "sitemap-calendars.xml",
        "sitemap-women-calendar.xml",
    ):
        copy_file(relative_path)
    brand_calendar_tree("sectors/calendars")
    brand_calendar_tree("sectors/women/daily-calendar")
    inject_women_sector_card()
    inject_homepage_cards()
    register_sitemap("sitemap-calendars.xml")
    register_sitemap("sitemap-women-calendar.xml")
    report = SITE / "api" / "calendar-publication-v221.json"
    report.write_text(json.dumps({
        "version": 221,
        "status": "passed",
        "brand": "منصة روافد",
        "routes": routes,
        "womenDailyCheckpoints": 3,
        "womenWeeklyInsight": True,
        "menstruationTerminology": "الحيض",
        "sitemaps": ["sitemap-calendars.xml", "sitemap-women-calendar.xml"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    run_core()
    publish_calendars()


if __name__ == "__main__":
    main()
