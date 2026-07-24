#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from publish_daily_tools_v24 import DESIGN_CONTRACT, STYLE

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
TARGET = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"

SLEEP_EXTENSION = r"""
header,section{box-shadow:var(--shadow-mint)}
.notice{border-right:7px solid #c74776;background:var(--rose);border-color:var(--rose-line);box-shadow:var(--shadow-rose)}
.privacy{border-right:7px solid #078179;background:var(--mint);border-color:var(--mint-line);box-shadow:var(--shadow-mint)}
.actions,.legend{display:flex;gap:10px;flex-wrap:wrap}
button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:9px 15px;border:2px solid var(--mint-line);border-radius:15px;background:linear-gradient(145deg,#fff,var(--mint));color:var(--ink);font:inherit;font-weight:900;box-shadow:0 6px 0 #d6eee9,0 11px 22px rgba(102,190,171,.13);cursor:pointer}
button:nth-of-type(2n){background:linear-gradient(145deg,#fff,var(--rose));border-color:var(--rose-line);box-shadow:0 6px 0 #f5dce6,0 11px 22px rgba(205,129,160,.12)}
input[aria-invalid="true"],textarea[aria-invalid="true"]{border:3px solid #9b1c31;background:#fff7f8}
.field-error{display:block;color:#811329;font-weight:800;margin-top:4px}
.summary{font-weight:800}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{border:1px solid #b9d8d4;padding:8px;text-align:right}
th{background:var(--lilac);color:#4a315f}
.chart-wrap{overflow:auto;border:2px solid var(--lilac-line);border-radius:18px;padding:12px;background:linear-gradient(145deg,#fff,var(--lilac));box-shadow:var(--shadow-lilac)}
.chart-wrap svg{display:block;width:100%;min-width:620px;height:auto}
.chart-wrap text{font:12px Tahoma,Arial,sans-serif;fill:var(--ink)}
.axis{stroke:var(--ink);stroke-width:1.5}.grid-line{stroke:#d6e7e4;stroke-width:1}
.series{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.series-hours{stroke:#006f68}.series-quality{stroke:#6a42b8;stroke-dasharray:9 5}.series-energy{stroke:#a13c62;stroke-dasharray:2 5}
.legend span{display:inline-flex;align-items:center;gap:7px;padding:4px 10px;border-radius:999px;background:#fff;border:1px solid var(--mint-line)}
.legend i{display:inline-block;width:34px;border-top:3px solid}.legend .hours i{border-color:#006f68}.legend .quality i{border-color:#6a42b8;border-top-style:dashed}.legend .energy i{border-color:#a13c62;border-top-style:dotted}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:640px){nav,.actions{display:grid}table{font-size:.9rem}}
@media print{nav,.actions,form button,.privacy{display:none!important}body{background:#fff}header,section{box-shadow:none;border:1px solid #777}.chart-wrap{overflow:visible}.chart-wrap svg{min-width:0}}
"""


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"Missing generated sleep-log page: {TARGET}")
    text = TARGET.read_text(encoding="utf-8")

    html_tag = '<html lang="ar" dir="rtl">'
    designed_tag = f'<html lang="ar" dir="rtl" data-design="marshmallow-v{DESIGN_CONTRACT}">'
    if designed_tag not in text:
        if html_tag not in text:
            raise SystemExit("Sleep-log HTML language tag is missing")
        text = text.replace(html_tag, designed_tag, 1)

    style_pattern = re.compile(r"<style>.*?</style>", re.S)
    replacement = f"<style>{STYLE}\n{SLEEP_EXTENSION}</style>"
    text, count = style_pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Expected one sleep-log style block, found {count}")

    text = text.replace(
        '<a href="/pterminology-site/daily-tools/">الأدوات اليومية</a>',
        '<a href="/pterminology-site/daily-tools/">الأدوات التفاعلية</a>',
        1,
    )
    header_marker = '<header><p>أداة تنظيمية غير تشخيصية للبالغين ومقدمي الرعاية</p>'
    if header_marker in text:
        text = text.replace(
            header_marker,
            '<header><span class="tool-kicker">أداة تفاعلية تنظيمية غير تشخيصية</span><p>للبالغين ومقدمي الرعاية</p>',
            1,
        )

    if '<meta name="color-scheme" content="light">' not in text:
        text = text.replace(
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#e5faf5"><meta name="color-scheme" content="light">',
            1,
        )

    normalized = text.replace(" ", "").lower()
    if "rgba(0,0,0" in normalized or "text-shadow" in normalized:
        raise SystemExit("Dark text-box shadow regression detected in sleep-log page")
    for marker in ("--mint:#e5faf5", "--rose:#fff0f5", "--lilac:#f2edff", "--peach:#fff0e8", "--butter:#fff8d8"):
        if marker not in text:
            raise SystemExit(f"Missing marshmallow palette marker: {marker}")

    TARGET.write_text(text, encoding="utf-8")
    print({"status": "passed", "design_contract": DESIGN_CONTRACT, "page": TARGET.relative_to(SITE).as_posix()})


if __name__ == "__main__":
    main()
