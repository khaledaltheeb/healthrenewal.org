#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise SystemExit(f"Expected repair anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def main() -> int:
    travel = ROOT / "guides" / "accessible-travel-planning" / "index.html"
    books = ROOT / "resources" / "open-books-discovery" / "index.html"
    anxiety = ROOT / "content" / "sectors-v10" / "clinical-anxiety.json"

    changed = False
    changed |= replace_once(
        travel,
        '<meta name="description" content="دليل عربي عملي للتحقق من الإقامة والنقل والتواصل والأدوية والطوارئ قبل السفر.">',
        '<meta name="description" content="دليل عربي عملي للتخطيط للسفر الميسّر والتحقق من الإقامة والنقل والتواصل والأدوية والأجهزة والطوارئ وخطط البدائل قبل الحجز والدفع.">\n<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">',
    )
    changed |= replace_once(
        travel,
        '<section aria-labelledby="sources-heading"><h2 id="sources-heading">المصادر المرجعية</h2>',
        '<section aria-labelledby="related-heading"><h2 id="related-heading">مسارات مرتبطة داخل المنصة</h2><ul><li><a href="/special-needs/">بوابة ذوي الاحتياجات الخاصة</a></li><li><a href="/daily-tools/medical-visit-preparation/">التحضير للزيارة الطبية</a></li><li><a href="/safety/">خطة السلامة وطلب المساعدة</a></li><li><a href="/services/">دليل الخدمات والمسارات</a></li><li><a href="/care-guides/">أدلة التعامل العملية</a></li></ul></section>\n<section aria-labelledby="sources-heading"><h2 id="sources-heading">المصادر المرجعية</h2>',
    )
    changed |= replace_once(
        books,
        '  <meta name="description" content="دليل عربي عملي لاكتشاف الكتب المفتوحة عبر بيانات Thoth، والتحقق من الناشر والرخصة والإصدار قبل القراءة أو التنزيل أو إعادة الاستخدام.">',
        '  <meta name="description" content="دليل عربي عملي لاكتشاف الكتب المفتوحة عبر بيانات Thoth، والتحقق من الناشر والرخصة والإصدار قبل القراءة أو التنزيل أو إعادة الاستخدام.">\n  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">',
    )
    changed |= replace_once(
        anxiety,
        '"title":"اضطرابات القلق والوسواس: دليل عربي للفهم والتقييم والمساعدة الآمنة"',
        '"title":"اضطرابات القلق والوسواس: الفهم والتقييم والمساعدة"',
    )
    changed |= replace_once(
        anxiety,
        '"meta":{"title":"اضطرابات القلق والوسواس: الأعراض والفروق وطرق المساعدة الآمنة"',
        '"meta":{"title":"اضطرابات القلق والوسواس: الأعراض والتقييم والمساعدة"',
    )

    subprocess.run(
        ["python", "scripts/materialize_sectors_v10_compat_v4.py", "."],
        cwd=ROOT,
        check=True,
    )

    print("strict SEO target repair applied" if changed else "strict SEO targets already compliant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())