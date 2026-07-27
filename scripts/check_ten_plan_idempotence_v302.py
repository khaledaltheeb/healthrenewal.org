#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_v254.py"
PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_ten_plans_v302.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(site: Path) -> None:
    (site / "special-needs").mkdir(parents=True)
    (site / "provider-assessment-demo").mkdir(parents=True)
    (site / "index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
        '<header><nav class="nav"><a href="special-needs/">المركز</a></nav></header>'
        '<main><h1>الرئيسية</h1></main></body></html>',
        encoding="utf-8",
    )
    (site / "special-needs/index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
        '<main><h1>مركز ذوي الاحتياجات الخاصة</h1></main></body></html>',
        encoding="utf-8",
    )
    (site / "provider-assessment-demo/index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
        '<main><h1>منصة مقدم الخدمة</h1></main></body></html>',
        encoding="utf-8",
    )
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap>'
        "</sitemapindex>",
        encoding="utf-8",
    )
    (site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        choices=("hub", "condition", "methodology", "api", "sitemap"),
    )
    args = parser.parse_args()
    site = Path(tempfile.mkdtemp(prefix="ten-plan-idempotence-"))
    try:
        prepare(site)
        base = load(BASE_PUBLISHER, "base_idempotence_probe")
        publisher = load(PUBLISHER, "ten_plan_idempotence_probe")
        base.publish(site)
        publisher.publish(site)
        targets = {
            "hub": site / "outside-the-box/index.html",
            "condition": site / "outside-the-box/speech-sound-disorder/index.html",
            "methodology": site / "outside-the-box/ten-plan-methodology/index.html",
            "api": site / "api/outside-the-box-ten-plans-v302.json",
            "sitemap": site / "sitemap-outside-the-box.xml",
        }
        path = targets[args.target]
        before = digest(path)
        publisher.publish(site)
        after = digest(path)
        print({"target": args.target, "before": before, "after": after, "stable": before == after})
        return 0 if before == after else 1
    finally:
        shutil.rmtree(site, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
