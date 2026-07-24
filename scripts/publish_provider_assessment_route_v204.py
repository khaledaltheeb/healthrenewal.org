from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
TARGET = SITE / "provider-assessment-demo" / "index.html"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"

PAGE = f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>منصة التقييم والاستكشاف | مصطلحات علم النفس</title>
<meta name="description" content="بوابة منظمة للوصول إلى المقاييس الاسترشادية واختبارات القدرات المعرفية والأدلة المهنية، مع توضيح حدود الاستخدام وعدم اعتبار النتائج تشخيصًا أو درجة ذكاء معيارية.">
<link rel="canonical" href="{BASE}provider-assessment-demo/">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:title" content="منصة التقييم والاستكشاف | مصطلحات علم النفس">
<meta property="og:description" content="ابدأ من المقاييس أو القدرات المعرفية أو الأدلة المهنية ضمن مسارات واضحة وغير تشخيصية.">
<meta property="og:url" content="{BASE}provider-assessment-demo/">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="منصة التقييم والاستكشاف | مصطلحات علم النفس">
<meta name="twitter:description" content="مسارات منظمة للمقاييس والقدرات والأدلة المهنية مع حدود استخدام واضحة.">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"CollectionPage","name":"منصة التقييم والاستكشاف","inLanguage":"ar","url":"{BASE}provider-assessment-demo/","isPartOf":{{"@type":"WebSite","name":"مصطلحات علم النفس","url":"{BASE}"}}}}</script>
<style>body{{margin:0;background:#f5fffd;color:#173f45;font-family:Tahoma,Arial,sans-serif;line-height:1.9}}main{{width:min(920px,92%);margin:auto;padding:3rem 0}}h1{{font-size:clamp(2rem,6vw,3.8rem);line-height:1.25}}.lead{{font-size:1.15rem;color:#42696c}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:2rem 0}}article{{background:#fff;border:1px solid #b9e5df;border-radius:20px;padding:1.3rem}}a{{color:#075f5b;font-weight:800}}.note{{border-inline-start:6px solid #087e8b;background:#e9fbf8;padding:1rem;border-radius:14px}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}</style>
</head>
<body><main>
<nav aria-label="مسار الصفحة"><a href="../">الرئيسية</a> ← منصة التقييم والاستكشاف</nav>
<h1>منصة التقييم والاستكشاف</h1>
<p class="lead">اختر المسار الأقرب إلى هدفك: مقاييس استرشادية، اختبارات قدرات وألعاب معرفية، أو أدلة تساعد مقدم الخدمة والأسرة على اختيار الخطوة التالية بصورة منظمة.</p>
<div class="grid">
<article><h2>المقاييس الاسترشادية</h2><p>استكشف أدوات منظمة مع تعليمات وحدود تفسير واضحة، دون تحويل النتيجة إلى تشخيص ذاتي.</p><a href="../assessment-lab/">فتح مختبر المقاييس</a></article>
<article><h2>القدرات المعرفية</h2><p>مهام اختيار من متعدد للانتباه والذاكرة والاستدلال والمرونة، متدرجة عبر مستويات متعددة.</p><a href="../cognitive-lab/">فتح مختبر القدرات</a></article>
<article><h2>اختيار المختص</h2><p>راجع دليل اختيار الطبيب أو المعالج أو مقدم الخدمة المناسب، والأسئلة المهمة قبل بدء المتابعة.</p><a href="../care-guides/choosing-mental-health-professional/">فتح الدليل</a></article>
</div>
<p class="note" role="note"><strong>حدود الاستخدام:</strong> هذه المسارات للتثقيف والاستكشاف والتدريب، ولا تستبدل التقييم السريري أو النفسي أو التربوي المقنن، ولا تنتج درجة ذكاء معيارية.</p>
<p><a href="../start-here/">ابدأ من هنا</a> · <a href="../trust/">مركز الثقة والمنهجية</a> · <a href="../">العودة إلى الرئيسية</a></p>
</main></body></html>'''


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site directory: {SITE}")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(PAGE, encoding="utf-8")
    report = {
        "version": 204,
        "route": "provider-assessment-demo/",
        "published": True,
        "canonical": f"{BASE}provider-assessment-demo/",
        "internal_destinations": 3,
        "non_diagnostic_notice": True,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "provider-assessment-route-v204.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
