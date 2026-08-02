#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org"
HUBS = {
    "care-guides": (
        "أدلة الرعاية والتعامل العملي",
        "أدلة عربية منهجية للأسر والمعلمين ومقدمي الخدمة تربط السؤال العملي بالتقييم والتنفيذ والقياس والسلامة.",
        "/care-guides/evidence-guided/",
        "فتح 12 دليل رعاية موسعًا",
    ),
    "comparisons": (
        "المقارنات المنهجية في الإعاقة والدعم",
        "مقارنات عملية تمنع الخلط بين التشخيص والوظيفة، والدمج والإدماج، والدعم والعقاب.",
        "/comparisons/disability-support/",
        "فتح 6 مقارنات تطبيقية",
    ),
    "daily-tools": (
        "أدوات عملية لدعم القرار والمتابعة",
        "قوالب تثقيفية لبناء ملف وظيفي ومراجعة خطة الدعم وتقييم جودة الخدمة وتنظيم الاجتماع متعدد التخصصات.",
        "/daily-tools/disability-support/",
        "فتح 4 أدوات عملية",
    ),
}


def render(sector: str, title: str, description: str, href: str, label: str) -> str:
    canonical = f"{BASE}/{sector}/"
    schema = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": description, "url": canonical, "inLanguage": "ar",
    }
    return f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>
<style>body{{margin:0;font-family:Tahoma,Arial,sans-serif;background:#f3faf8;color:#143f43;line-height:1.95}}.wrap{{width:min(1040px,92%);margin:auto}}header{{background:#123f43;padding:15px}}header a{{color:#fff;text-decoration:none;font-weight:900}}main{{padding:55px 0}}.card{{background:#fff;border:1px solid #c6e2de;border-radius:20px;padding:24px;box-shadow:0 12px 30px #123f4314}}a.button{{display:inline-block;background:#08776f;color:#fff;text-decoration:none;font-weight:900;padding:11px 17px;border-radius:12px}}</style>
</head><body><header><div class="wrap"><a href="/">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a></div></header><main><div class="wrap"><article class="card"><h1>{html.escape(title)}</h1><p>{html.escape(description)}</p><p>تجمع الصفحات الجديدة إطار الوظيفة والمشاركة والحقوق مع خطوات تنفيذ ومؤشرات مراجعة ومراجع أصلية. المحتوى للتثقيف والتنظيم ولا يستبدل التقييم الفردي أو القانون المحلي.</p><p><a class="button" href="{href}">{html.escape(label)}</a></p><p><a href="/special-needs/">مركز ذوي الاحتياجات الخاصة</a> · <a href="/learning-paths/">مسارات التعلم</a> · <a href="/trust/">منهجية المصادر</a></p></article></div></main></body></html>"""


def main() -> None:
    created = []
    for sector, values in HUBS.items():
        path = ROOT / sector / "index.html"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(sector, *values), encoding="utf-8")
        created.append(path.relative_to(ROOT).as_posix())
    print(json.dumps({"created": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()
