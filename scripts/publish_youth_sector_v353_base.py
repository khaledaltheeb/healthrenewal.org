#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 353
BASE = "https://healthrenewal.org"
BASE_PATH = ""
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "content" / "v353" / "youth-sector-ar.json"
REPORT_NAME = "youth-sector-v353.json"
ROBOTS_MARKER = "# youth-sector-v353"
BANNED = ("معاقين", "علاج مضمون", "تشخيصك هو", "نتائج مضمونة")


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)


def visible_words(source: str) -> int:
    parser = VisibleText()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def meta_description(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    suffix = " مع خطوات عملية وحدود سلامة ومصادر رسمية مراجعَة."
    if len(value) < 120:
        value += suffix
    if len(value) > 180:
        value = value[:177].rsplit(" ", 1)[0] + "…"
    if len(value) < 120:
        value += " دليل عربي موثوق."
    return value


def json_ld(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{raw}</script>'


STYLE = """
<style data-youth-sector-v353="1">
:root{--ys-ink:#17343a;--ys-muted:#536a70;--ys-brand:#075f5b;--ys-deep:#143b5d;--ys-sky:#e9f6ff;--ys-mint:#e8f7f2;--ys-sand:#fff6df;--ys-rose:#fff0f3;--ys-line:#c8dfe1;--ys-white:#fff;--ys-shadow:0 14px 38px rgba(20,59,93,.08)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f8fcfc;color:var(--ys-ink);font-family:Tahoma,"Segoe UI",Arial,sans-serif;line-height:1.9}
a{color:#075f5b;text-underline-offset:.2em}.ys-skip{position:absolute;inset-inline-start:1rem;top:-7rem;background:#fff;color:#000;padding:.75rem 1rem;z-index:50}.ys-skip:focus{top:1rem}
.ys-wrap{width:min(1160px,calc(100% - 2rem));margin-inline:auto}.ys-site-header{background:#fff;border-bottom:1px solid var(--ys-line)}.ys-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:76px;padding-block:.7rem}.ys-brand{display:flex;align-items:center;gap:.7rem;text-decoration:none;font-weight:900;color:var(--ys-deep)}.ys-brand img{width:46px;height:46px}.ys-nav{display:flex;gap:.25rem;flex-wrap:wrap}.ys-nav a{padding:.45rem .6rem;text-decoration:none;font-weight:800;border-radius:9px}.ys-nav a:hover{background:var(--ys-mint)}
.ys-hero{padding:clamp(2.7rem,7vw,5.8rem) 0;background:linear-gradient(135deg,#143b5d 0%,#075f5b 68%,#16847d 100%);color:#fff}.ys-hero h1{font-size:clamp(2rem,5vw,4.2rem);line-height:1.16;margin:.25rem 0 1rem;max-width:18ch}.ys-hero .ys-lead{font-size:clamp(1.05rem,2vw,1.28rem);max-width:78ch}.ys-eyebrow{font-weight:900;letter-spacing:.02em;color:#7eebe2}.ys-hero a{color:#fff}
.ys-actions,.ys-pills{display:flex;flex-wrap:wrap;gap:.65rem;margin-top:1.35rem}.ys-button{display:inline-flex;align-items:center;min-height:44px;padding:.55rem .9rem;border-radius:12px;background:#fff;color:var(--ys-deep)!important;text-decoration:none;font-weight:900}.ys-button.alt{background:transparent;border:2px solid rgba(255,255,255,.75);color:#fff!important}
.ys-section{padding:clamp(2.2rem,5vw,4.5rem) 0;border-bottom:1px solid var(--ys-line)}.ys-section:nth-of-type(even){background:#fff}.ys-section h2{font-size:clamp(1.45rem,3vw,2.35rem);line-height:1.35;margin-top:0}.ys-section h3{line-height:1.45}.ys-intro{font-size:1.08rem;color:var(--ys-muted);max-width:82ch}
.ys-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:1rem}.ys-card{background:#fff;border:1px solid var(--ys-line);border-radius:18px;padding:1.25rem;box-shadow:var(--ys-shadow)}.ys-card h3{margin:.2rem 0 .5rem}.ys-card p{color:var(--ys-muted)}.ys-card a{font-weight:900}.ys-tag{display:inline-block;border-radius:999px;background:var(--ys-mint);color:var(--ys-brand);font-size:.86rem;font-weight:900;padding:.2rem .55rem}
.ys-note{border-inline-start:5px solid #16847d;background:var(--ys-mint);border-radius:14px;padding:1rem 1.15rem;margin:1.1rem 0}.ys-warning{border-inline-start-color:#a55b00;background:var(--ys-sand)}.ys-danger{border-inline-start-color:#a42d48;background:var(--ys-rose)}
.ys-pills{margin:1.2rem 0 0}.ys-pills a{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.38);padding:.38rem .7rem;border-radius:999px;text-decoration:none;font-weight:800}
.ys-table-wrap{overflow-x:auto}.ys-table{width:100%;border-collapse:collapse;min-width:680px;background:#fff}.ys-table th,.ys-table td{text-align:start;vertical-align:top;border:1px solid var(--ys-line);padding:.85rem}.ys-table th{background:var(--ys-deep);color:#fff}
.ys-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:1.4rem;align-items:start}.ys-aside{position:sticky;top:1rem}.ys-aside a{display:block;padding:.3rem 0;font-weight:800}.ys-check li{margin:.45rem 0}.ys-source{border-top:4px solid #68bfb5}.ys-source small{color:var(--ys-muted)}.ys-faq details{background:#fff;border:1px solid var(--ys-line);border-radius:12px;padding:.85rem 1rem;margin:.55rem 0}.ys-faq summary{cursor:pointer;font-weight:900}
.ys-footer{background:#102c35;color:#eaf7f6;padding:2rem 0}.ys-footer a{color:#fff}.ys-footer-links{display:flex;flex-wrap:wrap;gap:.8rem}.ys-small{font-size:.92rem;color:var(--ys-muted)}
@media(max-width:850px){.ys-head{align-items:flex-start;flex-direction:column}.ys-layout{grid-template-columns:1fr}.ys-aside{position:static;order:-1}}
@media(max-width:620px){.ys-nav{display:none}.ys-hero h1{font-size:2.15rem}.ys-section{padding:1.8rem 0}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
@media(prefers-contrast:more){.ys-card{box-shadow:none;border-width:2px}}
@media print{.ys-site-header,.ys-footer,.ys-actions,.ys-pills,.ys-aside{display:none!important}.ys-card{box-shadow:none}.ys-section{break-inside:avoid}}
</style>
""".strip()


def shell_header() -> str:
    return f"""<a class="ys-skip" href="#main">تجاوز إلى المحتوى</a>
<header class="ys-site-header"><div class="ys-wrap ys-head">
<a class="ys-brand" href="{BASE_PATH}/"><img src="{BASE_PATH}/assets/brand/logo-mark.svg" alt="" width="46" height="46"><span>منصة الصحة النفسية وذوي الاحتياجات الخاصة</span></a>
<nav class="ys-nav" aria-label="التنقل الرئيسي"><a href="{BASE_PATH}/start-here/">ابدأ</a><a href="{BASE_PATH}/sectors/">القطاعات</a><a href="{BASE_PATH}/encyclopedia/">الموسوعة</a><a href="{BASE_PATH}/care-guides/">الأدلة</a><a href="{BASE_PATH}/trust/">المنهجية</a></nav>
</div></header>"""


def shell_footer(reviewed_at: str) -> str:
    return f"""<footer class="ys-footer"><div class="ys-wrap"><p><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong> — معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</p>
<p>المحتوى للتثقيف والدعم العام، ولا يستبدل التقييم أو العلاج الفردي. آخر مراجعة مصدرية لقطاع الشباب: {esc(reviewed_at)}.</p>
<nav class="ys-footer-links" aria-label="روابط التذييل"><a href="{BASE_PATH}/sectors/youth/">قطاع الشباب</a><a href="{BASE_PATH}/sectors/">كل القطاعات</a><a href="{BASE_PATH}/editorial-methodology/">المنهجية التحريرية</a><a href="{BASE_PATH}/copyright/">حقوق النشر</a></nav></div></footer>"""


def document(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    schemas: list[dict[str, Any]],
    reviewed_at: str,
) -> str:
    schema_html = "".join(json_ld(schema) for schema in schemas)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta_description(description))}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="author" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" hreflang="ar" href="{esc(canonical)}">
<link rel="alternate" hreflang="x-default" href="{esc(canonical)}">
<link rel="manifest" href="{BASE_PATH}/manifest.webmanifest">
<meta property="og:locale" content="ar_AR">
<meta property="og:type" content="article">
<meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(meta_description(description))}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="article:modified_time" content="{esc(reviewed_at)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(meta_description(description))}">
{STYLE}
<!-- pt-platform-shell:v1 -->
<link rel="stylesheet" href="{BASE_PATH}/assets/platform/platform-core.css?v=1.1.0">
{schema_html}
</head>
<body class="pt-platform" data-youth-publication="v353">
{shell_header()}
{body}
{shell_footer(reviewed_at)}
</body>
</html>
"""


def list_items(values: list[str]) -> str:
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def source_by_id(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {str(item["id"]): item for item in data["sources"]}


def source_cards(source_ids: list[str], sources: dict[str, dict[str, str]]) -> str:
    return "".join(
        f"""<article class="ys-card ys-source"><span class="ys-tag">{esc(sources[source_id]["type"])}</span>
<h3>{esc(sources[source_id]["name"])}</h3><p>{esc(sources[source_id]["scope"])}</p>
<p><small>{esc(sources[source_id]["organization"])}</small></p>
<a href="{esc(sources[source_id]["url"])}" rel="noopener noreferrer">فتح المصدر الرسمي</a></article>"""
        for source_id in source_ids
    )


def guide_card(guide: dict[str, Any]) -> str:
    return f"""<article class="ys-card"><span class="ys-tag">دليل تطبيقي</span><h3>{esc(guide["title"])}</h3>
<p>{esc(guide["summary"])}</p><a href="{BASE_PATH}/sectors/youth/{esc(guide["slug"])}/">قراءة الدليل الكامل</a></article>"""


def hub_body(data: dict[str, Any]) -> str:
    guide_map = {item["slug"]: item for item in data["guides"]}
    collection_cards = "".join(
        f"""<article class="ys-card"><span class="ys-tag">مسار من 4 أدلة</span><h3>{esc(item["title"])}</h3>
<p>{esc(item["summary"])}</p><ul>{list_items([guide_map[slug]["title"] for slug in item["guide_slugs"]])}</ul>
<a href="{BASE_PATH}/sectors/youth/{esc(item["slug"])}/">فتح المسار</a></article>"""
        for item in data["collections"]
    )
    guide_cards = "".join(guide_card(item) for item in data["guides"])
    source_cards_html = source_cards(
        [item["id"] for item in data["sources"]], source_by_id(data)
    )
    return f"""<main id="main" data-youth-hub-v353="1">
<section class="ys-hero"><div class="ys-wrap"><p class="ys-eyebrow">قطاع عربي موثّق لليافعين والشباب ومن يدعمهم</p>
<h1>{esc(data["title"])}</h1><p class="ys-lead">{esc(data["subtitle"])}. تبدأ الصفحات بوصف التغير والأثر والسياق، ثم تنظم ما ينبغي ملاحظته وما يمكن فعله وما يحتاج تقييمًا أو استجابة عاجلة.</p>
<div class="ys-note ys-danger"><strong>عند الخطر المباشر:</strong> إذا وُجدت نية أو خطة لإيذاء النفس أو الآخرين، أو تسمم أو إصابة، أو فقد للاتصال بالواقع، أو عنف يجعل المكان غير آمن، لا تنتظر اكتمال التصفح. ابقَ مع الشاب إن كان ذلك آمنًا، واطلب خدمات الطوارئ المحلية أو توجّه إلى أقرب قسم طوارئ.</div>
<div class="ys-actions"><a class="ys-button" href="#pathways">اختر المسار</a><a class="ys-button alt" href="#decision">خريطة القرار</a><a class="ys-button alt" href="#sources">المصادر والمنهجية</a></div>
<nav class="ys-pills" aria-label="روابط سريعة"><a href="#principles">المبادئ</a><a href="#observe">الملاحظة</a><a href="#roles">الأدوار</a><a href="#care">الوصول للرعاية</a><a href="#guides">الأدلة</a><a href="#faq">الأسئلة</a></nav>
</div></section>
<section class="ys-section" id="principles"><div class="ys-wrap"><h2>مبادئ تمنع التشخيص الذاتي والوصم</h2>
<div class="ys-grid"><article class="ys-card"><h3>التغير عن خط الأساس</h3><p>اسأل كيف كان الشاب قبل أسابيع أو أشهر، وما الذي تغير في النوم والطاقة والتواصل والدراسة والعناية بالنفس. المقارنة مع طريقته المعتادة أدق من مقارنته بزميل أو أخ.</p></article>
<article class="ys-card"><h3>الوظيفة قبل الملصق</h3><p>قد يحافظ الشاب على الدرجات وهو يدفع كلفة عالية من النوم أو القلق، وقد ينخفض أداؤه بسبب تنمر أو تعلم أو مرض جسدي لا اضطراب نفسي واحد. وصف الوظيفة يفتح أكثر من احتمال.</p></article>
<article class="ys-card"><h3>التحري ليس تشخيصًا</h3><p>الاستبيان يساعد على فتح الحوار أو متابعة الشدة، لكنه لا يحدد السبب ولا يستبعد الحالات الأخرى ولا يختار العلاج بمفرده. النتيجة المرتفعة تستدعي فهمًا أوسع لا حكمًا آليًا.</p></article>
<article class="ys-card"><h3>الصوت والخصوصية</h3><p>يشارك الشاب في الهدف والخطة ومن يحضر المقابلة وما المعلومات التي تتبادلها الجهات، مع شرح واضح لحدود السرية عندما يوجد خطر أو واجب حماية وفق النظام المحلي.</p></article></div>
<p class="ys-intro">تعرف منظمة الصحة العالمية المراهقة عادة بالمرحلة من 10 إلى 19 سنة، لكن هذا القطاع يشمل كذلك بدايات الرشد عندما يستمر الانتقال التعليمي والاجتماعي والخدمي. الحدود العمرية تنظيمية ولا تلغي اختلاف النضج أو الحقوق أو الأهلية بين الأنظمة.</p></div></section>
<section class="ys-section" id="observe"><div class="ys-wrap"><h2>ملاحظة منظمة لمدة أسبوعين دون مراقبة قهرية</h2>
<p class="ys-intro">يكفي سجل قصير مرة واحدة يوميًا. الهدف تحويل عبارة «ليس على طبيعته» إلى معلومات نافعة للقرار، لا جمع كل حركة أو تفتيش الهاتف أو تحويل البيت إلى عيادة.</p>
<div class="ys-table-wrap"><table class="ys-table"><thead><tr><th>المجال</th><th>ما الذي يسجل؟</th><th>كيف يفيد؟</th></tr></thead><tbody>
<tr><td>البداية والنمط</td><td>تاريخ تقريبي، أيام أفضل وأسوأ، أحداث أو أمراض أو أدوية سبقت التغير.</td><td>يفصل الاستجابة العابرة عن نمط مستمر ويقلل الاعتماد على الذاكرة.</td></tr>
<tr><td>النوم والجسد</td><td>فرصة النوم والاستيقاظات والطاقة والألم والشهية والكافيين والمواد.</td><td>يكشف عوامل جسدية وسلوكية قد تفسر جزءًا من الصورة أو تزيدها.</td></tr>
<tr><td>الوظيفة</td><td>الحضور والتعلم والعناية بالنفس والعلاقات والأنشطة والمسؤوليات.</td><td>يساعد على تحديد الشدة والهدف القابل للقياس.</td></tr>
<tr><td>السياق والأمان</td><td>تنمر أو عنف أو فقد أو ضغط مالي أو نزاع أو محتوى رقمي وخطر الإيذاء.</td><td>يمنع لوم الشاب ويحدد ما يجب تغييره في البيئة فورًا.</td></tr>
</tbody></table></div>
<div class="ys-note"><strong>لغة عملية:</strong> اكتب «تغيب ثلاثة أيام ولم ينم قبل الثانية صباحًا» بدل «كسول»، و«توقف عن لقاء أصدقائه وفقد اهتمامه بالرياضة» بدل «مكتئب» قبل اكتمال التقييم.</div></div></section>
<section class="ys-section" id="decision"><div class="ys-wrap"><h2>أربعة مستويات للحاجة إلى المساعدة</h2><div class="ys-grid">
<article class="ys-card"><h3>دعم ومراجعة</h3><p>ضيق خفيف مرتبط بحدث، والوظيفة الأساسية محفوظة ولا يوجد خطر. اختر تعديلًا واحدًا في النوم أو العبء أو التواصل وحدد مراجعة خلال أيام.</p></article>
<article class="ys-card"><h3>موعد قريب</h3><p>استمرار أو تكرار أو تراجع واضح في الحضور أو الأكل أو النوم أو العلاقات. احجز رعاية أولية أو خدمة نفسية مناسبة للعمر مع ملخص للملاحظات.</p></article>
<article class="ys-card"><h3>تقييم سريع</h3><p>تدهور متسارع، إيذاء نفس دون خطر وشيك ظاهر، قلة شديدة في الحاجة للنوم مع نشاط غير معتاد، فقد وزن أو إغماء، مواد أو عجز عن الرعاية الأساسية.</p></article>
<article class="ys-card"><h3>طوارئ الآن</h3><p>نية أو خطة أو وسائل إيذاء، تسمم أو إصابة، ارتباك شديد أو ذهان، عنف حالي أو عجز عن إبقاء الشاب آمنًا. استخدم الطوارئ المحلية ولا تتركه وحده.</p></article>
</div><p class="ys-intro">المستويات أدوات تنظيمية وليست درجات تشخيص. قد يتغير المستوى خلال ساعات، ويجب أن يتغلب الحكم المباشر والبيانات الجديدة على أي قائمة سابقة.</p></div></section>
<section class="ys-section" id="pathways"><div class="ys-wrap"><h2>أربعة مسارات، في كل مسار أربع صفحات مترابطة</h2><p class="ys-intro">اختر المسار الذي يصف الحاجة الأكثر إلحاحًا، ثم انتقل بين الصفحات عند تداخل العوامل. لا يلزم قراءة القطاع كاملًا قبل اتخاذ خطوة أمان أو حجز موعد.</p><div class="ys-grid">{collection_cards}</div></div></section>
<section class="ys-section" id="roles"><div class="ys-wrap"><h2>تقسيم الأدوار بدل تحميل الشاب مسؤولية الحل</h2><div class="ys-grid">
<article class="ys-card"><h3>الشاب</h3><p>يصف ما يحدث بلغته، ويختار أهدافًا ذات معنى، ويشارك في خطة الأمان والخصوصية. لا يطلب منه إثبات المعاناة أو إدارة شبكة خدمات معقدة وحده.</p></article>
<article class="ys-card"><h3>الأسرة ومقدم الرعاية</h3><p>توفر الاستماع والنقل والمواعيد والنوم والوجبات وتقليل الوسائل الخطرة، وتفرق بين حدود السلامة والرغبة في السيطرة. الدعم العملي أهم من المحاضرة.</p></article>
<article class="ys-card"><h3>المدرسة والجامعة</h3><p>تعالج التنمر والأمان والعبء والتكييفات والحضور، وتعين نقطة اتصال وتحفظ الخصوصية. لا تحول كل مشكلة إلى غياب أو عقوبة أو طلب تقرير جديد.</p></article>
<article class="ys-card"><h3>الخدمة المهنية</h3><p>تشرح التقييم والبدائل والسرية والمخاطر وخطة المتابعة بلغة ملائمة للعمر، وتنسق الانتقال بين الجهات ولا تعتبر الإحالة نهاية المسؤولية.</p></article>
</div></div></section>
<section class="ys-section" id="care"><div class="ys-wrap"><h2>الاستعداد للرعاية واتخاذ قرار مشترك</h2>
<div class="ys-grid"><article class="ys-card"><h3>قبل الموعد</h3><p>خط زمني في نصف صفحة، قائمة الأدوية والمكملات والحالات الجسدية، هدفان وظيفيان، وأهم سؤالين. أحضر تقارير ذات صلة فقط ولا تغرق المقابلة بملفات غير منظمة.</p></article>
<article class="ys-card"><h3>داخل الموعد</h3><p>اطلب شرح الاحتمالات وما يدعمها وما يعارضها، وما الفحوص اللازمة، وما الخيارات وفوائدها ومخاطرها. ينبغي أن يحصل الشاب على مساحة للكلام وفق العمر والأمان.</p></article>
<article class="ys-card"><h3>بعد الموعد</h3><p>اكتب الخطة والمسؤول والموعد التالي وكيف سيقاس التحسن والآثار الجانبية ومن يتلقى الاتصال عند التدهور. إذا تعذر العلاج المختار، اطلب بديلًا أو خطة انتظار آمنة.</p></article>
<article class="ys-card"><h3>عند الانتقال</h3><p>ابدأ قبل الحد العمري، وحدد الخدمة المستقبلة ومعاييرها والمنسق والوصفات وفجوات الانتظار. لا تغلق الرعاية الحالية قبل وضوح الاستقبال والمتابعة.</p></article></div>
<div class="ys-note ys-warning"><strong>حد دوائي ثابت:</strong> لا تبدأ دواء نفسيًا أو توقفه أو تغير جرعته اعتمادًا على هذه الصفحات. ناقش القرار مع مقدم رعاية مؤهل يعرف العمر والتاريخ الصحي والأدوية الأخرى والخطر والمتابعة المتاحة.</div></div></section>
<section class="ys-section" id="guides"><div class="ys-wrap"><h2>ستة عشر دليلًا غنيًا قابلًا للاستخدام</h2><p class="ys-intro">كل دليل يضم حدود الدليل، مؤشرات للملاحظة، خريطة تقييم، خطوات قابلة للقياس، ما ينبغي تجنبه، أسئلة للموعد، ومسارًا واضحًا للحالات العاجلة.</p><div class="ys-grid">{guide_cards}</div></div></section>
<section class="ys-section ys-faq" id="faq"><div class="ys-wrap"><h2>أسئلة شائعة</h2>
<details><summary>هل اختلاف المزاج طبيعي في المراهقة؟</summary><p>قد تحدث تقلبات، لكن الاستمرار والتصاعد والتغير عن خط الأساس وتعطل النوم أو الدراسة أو الأكل أو العلاقات أو ظهور خطر أسباب كافية لطلب تقييم، حتى لو بدت بعض التغيرات شائعة.</p></details>
<details><summary>هل يمكن للأسرة قراءة رسائل الشاب لحمايته؟</summary><p>الخصوصية مهمة للنمو وطلب المساعدة. أي تدخل ينبغي أن يكون متناسبًا مع خطر محدد ومعلنًا قدر الإمكان، مع طريق آمن للحصول على دعم. التفتيش الشامل السري قد يقطع الثقة ولا يعالج السبب.</p></details>
<details><summary>هل اختبار الإنترنت يثبت القلق أو الاكتئاب أو التوحد؟</summary><p>لا. قد يساعد الاستبيان على تنظيم الملاحظات أو بدء الحوار، لكنه لا يجمع التاريخ النمائي والصحي والسياق ولا يستبعد الأسباب الأخرى ولا يختار العلاج.</p></details>
<details><summary>متى نطلب مساعدة عاجلة؟</summary><p>عند نية أو خطة أو وسائل لإيذاء النفس أو الآخرين، تسمم أو إصابة، ارتباك شديد أو فقد اتصال بالواقع، خطر عنف، إغماء أو جفاف أو عجز متزايد عن الرعاية الأساسية.</p></details>
<details><summary>كيف تتعاون المدرسة دون انتهاك الخصوصية؟</summary><p>تشارك الحد الأدنى اللازم للسلامة والتكييف، وتحدد من يصل إلى المعلومة ولماذا ومدة حفظها، وتشرك الشاب والأسرة قدر الإمكان، ولا تعمم التشخيص أو التفاصيل على المعلمين والزملاء.</p></details>
<details><summary>ماذا لو رفض الشاب الموعد؟</summary><p>ابدأ بما يهمه هو: النوم أو المدرسة أو الألم أو النزاع، واعرض خيارات في المكان والمختص والحضور. لا تستخدم الإكراه إلا ضمن متطلبات أمان وقانون واضحة عندما يكون الخطر كبيرًا.</p></details>
</div></section>
<section class="ys-section" id="sources"><div class="ys-wrap"><h2>سجل المصادر الرسمية</h2><p class="ys-intro">اختيرت مصادر منظمة الصحة العالمية واليونيسف واليونسكو وNICE وCDC ووزارة الصحة الأمريكية وفق صلتها المباشرة. الاستشهاد لا يعني اعتماد هذه الجهات للصفحات العربية، ولا يعني أن النص ترجمة حرفية. روجعت الروابط والنطاق في {esc(data["reviewed_at"])}.</p><div class="ys-grid">{source_cards_html}</div></div></section>
<section class="ys-section" id="methodology"><div class="ys-wrap"><h2>كيف بُني القطاع وما حدوده؟</h2>
<p>حُولت الإرشادات وصحائف الوقائع إلى أسئلة قرار ومؤشرات وظيفة وخطوات دعم عامة. فصلنا بين التعزيز والوقاية والتحري والتقييم والتشخيص والعلاج، وذكرنا مواضع عدم اليقين، ولم ننقل جرعات أو مقاييس محمية أو أرقام طوارئ غير محلية. كل صفحة تربط ادعاءاتها بالمصادر الأقرب لموضوعها.</p>
<p>هذه مراجعة تحريرية ومنهجية داخلية وليست مراجعة سريرية خارجية مستقلة. قد تختلف الخدمات والأعمار القانونية وحقوق السرية وواجبات الإبلاغ بين البلدان؛ لذلك تستخدم الصفحات عبارة «وفق النظام المحلي» عندما لا يصح تعميم إجراء واحد.</p>
<p class="ys-small">الإصدار {VERSION} — {esc(data["scope"])}</p></div></section>
</main>"""


def collection_body(
    collection: dict[str, Any],
    guides: list[dict[str, Any]],
    sources: dict[str, dict[str, str]],
    reviewed_at: str,
) -> str:
    relevant_ids: list[str] = []
    for guide in guides:
        for source_id in guide["sources"]:
            if source_id not in relevant_ids:
                relevant_ids.append(source_id)
    cards = "".join(guide_card(guide) for guide in guides)
    return f"""<main id="main" data-youth-collection-v353="{esc(collection["slug"])}">
<section class="ys-hero"><div class="ys-wrap"><p class="ys-eyebrow"><a href="{BASE_PATH}/sectors/youth/">قطاع الشباب واليافعين</a> / مسار موضوعي</p>
<h1>{esc(collection["title"])}</h1><p class="ys-lead">{esc(collection["summary"])}</p>
<div class="ys-note ys-danger"><strong>السلامة لا تنتظر المسار:</strong> عند إصابة أو تسمم أو نية أو خطة إيذاء أو فقد للاتصال بالواقع أو عنف حالي، استخدم الطوارئ المحلية أو أقرب قسم طوارئ وابقَ مع الشاب إن كان ذلك آمنًا.</div>
<div class="ys-actions"><a class="ys-button" href="#guides">الأدلة الأربعة</a><a class="ys-button alt" href="#method">طريقة الاستخدام</a><a class="ys-button alt" href="#sources">مصادر المسار</a></div></div></section>
<section class="ys-section" id="method"><div class="ys-wrap"><h2>طريقة استخدام هذا المسار</h2>
<div class="ys-grid"><article class="ys-card"><h3>ابدأ بالوظيفة</h3><p>صف ما تغير في النوم أو الدراسة أو الأكل أو التواصل أو الأمان بدل بدء الحوار باسم اضطراب. هذا يفتح احتمالات نفسية وجسدية وتعليمية وبيئية بدل حصرها مبكرًا.</p></article>
<article class="ys-card"><h3>اجمع أكثر من منظور</h3><p>استمع إلى الشاب والأسرة والمدرسة أو الجامعة بحسب الحاجة. اختلاف الروايات معلومة عن السياق، وليس دليلًا تلقائيًا على أن طرفًا غير صادق.</p></article>
<article class="ys-card"><h3>اختر خطوة واحدة</h3><p>حدد إجراءً له مسؤول ووقت ومعيار مراجعة: موعد، تعديل نوم، نقطة اتصال مدرسية، تقليل وسيلة خطر أو دعم عملي. كثرة النصائح بلا ترتيب تزيد الاستنزاف.</p></article>
<article class="ys-card"><h3>راجع ولا تجمّد الخطة</h3><p>حدد موعدًا خلال أيام أو أسبوعين وفق الشدة. تحسن العرض لا يلغي مراجعة السبب، وتدهور الخطر يتقدم على الموعد الروتيني.</p></article></div>
<p class="ys-intro">المسارات تنظيمية لا تشخيصية. قد يحتاج المستخدم دليلًا من مسار آخر، مثل الجمع بين النوم والقلق أو التنمر والحضور المدرسي أو الأكل ووسائل التواصل.</p></div></section>
<section class="ys-section" id="guides"><div class="ys-wrap"><h2>الأدلة الأربعة في هذا المسار</h2><div class="ys-grid">{cards}</div></div></section>
<section class="ys-section" id="shared-observation"><div class="ys-wrap"><h2>ورقة ملاحظة مشتركة قبل الموعد</h2>
<div class="ys-table-wrap"><table class="ys-table"><thead><tr><th>السؤال</th><th>مثال لمعلومة نافعة</th><th>ما الذي لا نستنتجه؟</th></tr></thead><tbody>
<tr><td>متى بدأ التغير؟</td><td>بعد انتقال مدرسي بثلاثة أسابيع، ويتحسن جزئيًا في العطلة.</td><td>لا يثبت أن المدرسة هي السبب الوحيد.</td></tr>
<tr><td>ما الذي تعطل؟</td><td>تأخر الحضور أربع مرات وتوقف عن النشاط الأسبوعي.</td><td>لا يثبت كسلًا أو تشخيصًا.</td></tr>
<tr><td>ما العوامل المصاحبة؟</td><td>نوم خمس ساعات، كافيين مساءً، نزاع مع زميل.</td><td>لا يحدد أي عامل السببية بمفرده.</td></tr>
<tr><td>ما الخطر والحماية؟</td><td>لا خطة إيذاء، ويستطيع التواصل مع خالته ومعلم محدد.</td><td>لا يجعل الخطر ثابتًا؛ يعاد السؤال عند التغير.</td></tr>
</tbody></table></div>
<div class="ys-note ys-warning"><strong>الخصوصية:</strong> احفظ السجل في مكان آمن، ولا ترسله إلى مجموعات أو تطبيقات عامة. شارك الحد الأدنى اللازم مع الجهة التي ستساعد.</div></div></section>
<section class="ys-section" id="roles"><div class="ys-wrap"><h2>اتفاق عمل قصير بين الشاب والبالغ</h2>
<ol class="ys-check"><li>ما الهدف الذي يهم الشاب نفسه خلال الأسبوعين القادمين؟</li><li>ما المساعدة العملية التي يستطيع البالغ تقديمها دون سيطرة أو لوم؟</li><li>ما علامة التدهور التي تنقل الخطة من المتابعة إلى موعد سريع أو طوارئ؟</li><li>من نقطة الاتصال، ومتى تتم المراجعة، وما المعلومة التي ستقاس؟</li></ol>
<p>ينبغي أن تكون الاتفاقات قليلة وقابلة للتراجع والمراجعة. لا تستخدم الخطة لسحب الخصوصية أو العلاج أو التعليم كعقوبة، ولا تجعل الإفصاح الصادق سببًا تلقائيًا للعقاب.</p></div></section>
<section class="ys-section" id="sources"><div class="ys-wrap"><h2>مصادر هذا المسار</h2><p class="ys-intro">هذه الروابط مؤسسية مباشرة. روجعت في {esc(reviewed_at)}، والاستشهاد بها لا يعني أن الصفحة ترجمة حرفية أو اعتمادًا من الجهة.</p><div class="ys-grid">{source_cards(relevant_ids, sources)}</div></div></section>
<section class="ys-section"><div class="ys-wrap"><h2>الحدود والمنهجية</h2><p>يقدم المسار تثقيفًا عامًا ويساعد على الاستعداد للتقييم. لا يحدد تشخيصًا أو أهلية قانونية أو دواء، ولا يحل محل تقييم الإصابات أو التسمم أو الخطر. عند اختلاف الإرشاد العام مع خطة فريق يعرف الحالة، ناقش التعارض مع الفريق بدل تغيير العلاج ذاتيًا.</p>
<p><a href="{BASE_PATH}/sectors/youth/">العودة إلى مركز الشباب</a> · <a href="{BASE_PATH}/editorial-methodology/">قراءة المنهجية التحريرية</a> · <a href="{BASE_PATH}/evaluate-mental-health-information/">تعلم تقييم المعلومة النفسية</a></p></div></section>
</main>"""


def guide_body(
    guide: dict[str, Any],
    collection: dict[str, Any],
    sources: dict[str, dict[str, str]],
    reviewed_at: str,
) -> str:
    slug = guide["slug"]
    canonical = f"{BASE}/sectors/youth/{slug}/"
    return f"""<main id="main" data-youth-guide-v353="{esc(slug)}">
<section class="ys-hero"><div class="ys-wrap"><p class="ys-eyebrow"><a href="{BASE_PATH}/sectors/youth/">قطاع الشباب</a> / <a href="{BASE_PATH}/sectors/youth/{esc(collection["slug"])}/">{esc(collection["title"])}</a></p>
<h1>{esc(guide["title"])}</h1><p class="ys-lead">{esc(guide["summary"])}</p>
<div class="ys-note ys-danger"><strong>قاعدة السلامة:</strong> إصابة أو تسمم أو نية أو خطة إيذاء أو ارتباك شديد أو فقد للاتصال بالواقع أو عنف حالي لا ينتظر تطبيق هذا الدليل. استخدم خدمات الطوارئ المحلية أو أقرب قسم طوارئ، ولا تترك الشاب وحده إذا كان ذلك آمنًا.</div>
<nav class="ys-pills" aria-label="فهرس الدليل"><a href="#understand">الفهم</a><a href="#evidence">حدود الدليل</a><a href="#signals">المؤشرات</a><a href="#assessment">التقييم</a><a href="#plan">الخطة</a><a href="#avoid">التجنب</a><a href="#appointment">الموعد</a><a href="#sources">المصادر</a></nav>
</div></section>
<div class="ys-wrap ys-section ys-layout"><article>
<section id="understand"><h2>فهم الموضوع دون اختزال الشاب</h2><p>{esc(guide["context"])}</p>
<p>ابدأ بأربعة محاور: ما التغير عن خط الأساس؟ كم استمر وتكرر؟ ما أثره في الوظيفة اليومية؟ وما السياق الجسدي والأسري والمدرسي والرقمي المحيط؟ وجود مؤشر واحد لا يثبت اضطرابًا، وغياب المظهر الخارجي لا ينفي المعاناة. قد ينجز الشاب واجباته بكلفة عالية أو يخفي الصعوبة خوفًا من اللوم.</p>
<p>استخدم لغة تصف السلوك والوقت والأثر. قول «ينام بعد الثانية ويغيب عن الحصة الأولى مرتين أسبوعيًا» أكثر فائدة من «مهمل». الوصف الدقيق يساعد على اختيار خطوة، ويحمي من ربط كل مشكلة بالشخصية أو التربية أو الهاتف أو التشخيص المفضل.</p></section>
<section class="ys-section" id="evidence"><h2>ما يقوله الدليل وما لا يقوله</h2><div class="ys-note"><p>{esc(guide["evidence_boundary"])}</p></div>
<p>المصادر المستخدمة إرشادات وصحائف وقائع مؤسسية؛ تقدم اتجاهًا عامًا ولا تعرف تفاصيل الشاب أو نظام الخدمات المحلي. قوة التوصية لا تعني أن كل تدخل متاح أو مناسب لكل شخص. كما أن الارتباط بين عامل ونتيجة لا يثبت أن العامل سبب منفرد، خصوصًا في النوم والهواتف والتنمر والمواد والصحة النفسية.</p></section>
<section class="ys-section" id="signals"><h2>مؤشرات تستحق الملاحظة</h2><ul class="ys-check">{list_items(guide["signals"])}</ul>
<p>تزداد أهمية المؤشر عندما يتكرر أو يتصاعد أو يظهر في أكثر من سياق أو يعطل وظيفة أو يترافق مع خطر. لا تنتظر اجتماع كل البنود. وفي المقابل، لا تحول بندًا واحدًا إلى تشخيص؛ اسأل عما سبقه وما يخففه وما يزيده وما إذا كانت هناك أسباب جسدية أو دوائية أو بيئية.</p></section>
<section class="ys-section" id="assessment"><h2>خريطة تقييم قبل الحكم</h2><ol class="ys-check">{list_items(guide["assessment"])}</ol>
<div class="ys-table-wrap"><table class="ys-table"><thead><tr><th>المجال</th><th>بيانات مختصرة</th><th>سؤال القرار</th></tr></thead><tbody>
<tr><td>الزمن</td><td>البداية والمدة والتكرار والأيام الأفضل والأسوأ.</td><td>هل هو تغير عابر أم نمط مستمر أو متصاعد؟</td></tr>
<tr><td>الوظيفة</td><td>النوم والأكل والعناية والحضور والتعلم والعلاقات.</td><td>ما الهدف الوظيفي الأول الذي نريد استعادته؟</td></tr>
<tr><td>السياق</td><td>صحة وأدوية ومواد وتنمر وعنف وفقد وبيئة رقمية.</td><td>ما العامل القابل للتعديل وما الذي يحتاج فحصًا؟</td></tr>
<tr><td>الأمان</td><td>إيذاء أو خطة أو وسائل أو إصابة وشخص ومكان آمنان.</td><td>هل تكفي المتابعة أم يلزم تقييم سريع أو طوارئ؟</td></tr>
</tbody></table></div>
<p>اجمع رواية الشاب أولًا ثم معلومات الأسرة أو المدرسة عند الحاجة وبأقل قدر لازم من المشاركة. اختلاف الروايات قد يعكس اختلاف السياق أو القدرة على الإخفاء، ولا يبرر اتهام طرف بالكذب قبل الاستيضاح.</p></section>
<section class="ys-section" id="observe"><h2>متابعة قصيرة لمدة أربعة عشر يومًا</h2>
<p>سجل مرة واحدة يوميًا شدة الضيق من صفر إلى عشرة، وفرصة النوم، والطاقة، وموقفًا مهمًا، ووظيفة واحدة مثل الحضور أو الوجبة أو التواصل، وأي علامة خطر. اجعل السجل أقل من دقيقتين حتى لا يتحول إلى عبء أو فحص قهري. أوقف السجل واطلب مساعدة إذا تصاعد الخطر؛ لا يلزم إكمال أربعة عشر يومًا.</p>
<p>في المراجعة، ابحث عن نمط لا عن يوم مثالي: هل يظهر التغير بعد موقف محدد؟ هل يساعد النوم أو شخص معين؟ هل التعطل محصور في المدرسة أم موجود في البيت والعلاقات أيضًا؟ هذه الأسئلة تولد فرضيات للتقييم ولا تثبت السببية.</p></section>
<section class="ys-section" id="plan"><h2>خطة عملية متدرجة</h2><ol class="ys-check">{list_items(guide["actions"])}</ol>
<p>حوّل كل خطوة إلى اتفاق: من المسؤول؟ متى تبدأ؟ ما المورد المطلوب؟ وما علامة النجاح أو الفشل؟ اختر خطوتين فقط في الأسبوع الأول: خطوة تخفف الخطر أو العبء اليوم، وخطوة تفتح طريقًا إلى دعم أو تقييم. لا تغير النوم والمدرسة والهاتف والدواء والعلاقات كلها في وقت واحد.</p>
<div class="ys-note ys-warning"><strong>مثال قياس:</strong> بدل «تحسن أكثر»، استخدم «حضر الحصتين الأوليين ثلاثة أيام»، أو «أبلغ بالغًا آمنًا عند تصاعد الرغبة»، أو «حصل على ثماني ساعات كفرصة للنوم أربع ليال». القياس يخدم القرار ولا يستخدم لمعاقبة الشاب.</div></section>
<section class="ys-section" id="roles"><h2>ماذا يفعل الشاب والأسرة والمدرسة والخدمة؟</h2>
<div class="ys-grid"><article class="ys-card"><h3>الشاب</h3><p>يختار هدفًا مهمًا ويصف ما يساعد وما يضر ويعرف طريق طلب المساعدة. لا يحمل مسؤولية تنسيق كل الجهات أو ضمان نجاح الخطة.</p></article>
<article class="ys-card"><h3>الأسرة</h3><p>تقدم نقلًا ووقتًا ونومًا ووجبات واتصالًا ومتابعة وتقلل الوسائل الخطرة عند الحاجة، مع احترام الصوت والخصوصية.</p></article>
<article class="ys-card"><h3>المدرسة</h3><p>تعالج الأمان والتنمر والعبء والتكييفات وتعين نقطة اتصال، ولا تستخدم التفاصيل الصحية في التأديب أو التداول العام.</p></article>
<article class="ys-card"><h3>الخدمة</h3><p>تشرح الاحتمالات والسرية والخطة والبدائل والمتابعة، وتنسق مع الجهات الأخرى بعد موافقة مناسبة وحدود حماية واضحة.</p></article></div></section>
<section class="ys-section" id="avoid"><h2>ما ينبغي تجنبه</h2><ul class="ys-check">{list_items(guide["avoid"])}</ul>
<p>تجنب كذلك المقارنات والتهديد والوعود العلاجية وإيقاف دواء أو بدء مكمل دون مقدم مؤهل. لا تنشر قصة الشاب أو صوره أو تشخيصه لطلب رأي عام. إذا أخبرك بخطر، اشكره على الإفصاح واشرح الخطوة التالية ومن سيشارك بدل مفاجأته بعقوبة أو فضيحة.</p></section>
<section class="ys-section" id="appointment"><h2>أسئلة للموعد المهني</h2><ul class="ys-check">{list_items(guide["questions"])}</ul>
<p>أضف أسئلة ثابتة: ما البدائل؟ ما فوائد ومخاطر كل خيار؟ كيف نقيس الوظيفة والآثار الجانبية؟ متى المراجعة؟ ومن نتصل به قبل الموعد إذا ساءت الحالة؟ اطلب لغة مفهومة للشاب ونسخة من الخطة، واسأل عن التكلفة والوصول والتكييفات والخصوصية.</p>
<div class="ys-note"><strong>قبل الخروج:</strong> ينبغي أن يكون واضحًا من سيفعل ماذا، وما الموعد التالي، وما علامة التصعيد، وأين تحفظ خطة الأمان أو الأدوية. الطمأنة العامة من دون متابعة ليست خطة.</div></section>
<section class="ys-section" id="urgent"><h2>متى تصبح الاستجابة عاجلة؟</h2>
<p>اطلب تقييمًا عاجلًا عند إيذاء نفس حديث، تدهور سريع، عجز متزايد عن الأكل أو الشرب أو العناية الأساسية، قلة شديدة في الحاجة للنوم مع نشاط واندفاع غير معتاد، أعراض ذهانية، تسمم، إغماء، جفاف، أو عنف. عند نية أو خطة أو وسائل وشيكة، اتصل بالطوارئ المحلية أو اذهب إلى أقرب قسم طوارئ ولا تترك الشاب وحده إذا كان ذلك آمنًا.</p>
<p>لا تعتمد على وعد شفهي بعدم الإيذاء ولا على درجة منخفضة سابقة. قلل الوصول إلى الوسائل الخطرة بطريقة آمنة ومتعاونة، وأحضر معلومات عن الأدوية والمواد والإصابة. حماية الحياة تتقدم على إكمال الصفحة أو انتظار موعد روتيني.</p></section>
<section class="ys-section" id="inclusion"><h2>الإتاحة والاختلاف والخصوصية</h2>
<p>قد يحتاج الشاب ذو الاحتياجات الخاصة أو الاختلاف العصبي إلى لغة مباشرة ووقت أطول ومواد مكتوبة وبيئة أقل إثارة حسية أو وسيلة تواصل بديلة أو مترجم لغة إشارة أو مرافقة يختارها. لا تفسر صعوبة التواصل كغياب للألم أو الرأي أو الأهلية، ولا تجعل التواصل البصري شرطًا للإصغاء.</p>
<p>شارك الحد الأدنى اللازم من المعلومات، وحدد من يصل إليها ولماذا ومدة حفظها. تختلف حقوق السرية وموافقة اليافع وواجبات الإبلاغ حسب البلد والعمر والمهنة؛ اسأل مقدم الخدمة عن السياسة بصراحة ولا تعد بسرية مطلقة قبل فهم الحدود.</p></section>
<section class="ys-section" id="sources"><h2>المصادر الرسمية لهذا الدليل</h2><p>روابط المصدر مباشرة وليست روابط تسويقية. روجعت في {esc(reviewed_at)}. الاستشهاد لا يعني اعتماد الجهة للصفحة العربية ولا أن النص ترجمة حرفية.</p><div class="ys-grid">{source_cards(guide["sources"], sources)}</div></section>
<section class="ys-section" id="methodology"><h2>المنهجية وحدود الصفحة</h2>
<p>صيغ الدليل من نطاق المصادر الرسمية ثم حُول إلى أسئلة قرار ووظيفة وسلامة. لم تنقل الصفحة جرعات أو مقاييس محمية، ولم تدّع سببية حيث كان الدليل ارتباطيًا، ولم تستبدل الخطة العامة بحكم فردي. المراجعة تحريرية ومنهجية داخلية وليست مراجعة سريرية خارجية مستقلة.</p>
<p><a href="{BASE_PATH}/sectors/youth/{esc(collection["slug"])}/">العودة إلى المسار</a> · <a href="{BASE_PATH}/sectors/youth/">كل أدلة الشباب</a> · <a href="{BASE_PATH}/evaluate-mental-health-information/">تقييم المعلومات النفسية</a></p></section>
</article>
<aside class="ys-card ys-aside" aria-label="ملخص الدليل"><span class="ys-tag">ملخص قرار</span><h2>ثلاثة أسئلة</h2><ol><li>ما الذي تغير وتعطل؟</li><li>ما مستوى الخطر الآن؟</li><li>من المسؤول عن الخطوة التالية ومتى تراجع؟</li></ol><p class="ys-small">لا تشخيص ذاتي، لا تغيير دوائي ذاتي، ولا انتظار عند الخطر.</p><a href="#urgent">حدود الاستجابة العاجلة</a><a href="#appointment">أسئلة الموعد</a><a href="#sources">مصادر الصفحة</a></aside>
</div></main>"""


def validate_source(data: dict[str, Any]) -> None:
    if data.get("version") != VERSION or data.get("key") != "youth":
        raise ValueError("youth_source_version_or_key_mismatch")
    sources = data.get("sources")
    collections = data.get("collections")
    guides = data.get("guides")
    if not isinstance(sources, list) or len(sources) < 14:
        raise ValueError("youth_source_requires_at_least_14_sources")
    if not isinstance(collections, list) or len(collections) != 4:
        raise ValueError("youth_source_requires_4_collections")
    if not isinstance(guides, list) or len(guides) != 16:
        raise ValueError("youth_source_requires_16_guides")
    source_ids = [item.get("id") for item in sources]
    guide_slugs = [item.get("slug") for item in guides]
    collection_slugs = [item.get("slug") for item in collections]
    for label, values in (
        ("source", source_ids),
        ("guide", guide_slugs),
        ("collection", collection_slugs),
    ):
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"youth_{label}_identifier_missing")
        if len(values) != len(set(values)):
            raise ValueError(f"youth_{label}_identifier_duplicate")
    source_set = set(source_ids)
    guide_set = set(guide_slugs)
    collected: list[str] = []
    required_guide_fields = {
        "slug", "title", "summary", "context", "evidence_boundary", "signals",
        "assessment", "actions", "avoid", "questions", "sources",
    }
    for guide in guides:
        if not required_guide_fields <= set(guide):
            raise ValueError(f"youth_guide_fields_missing:{guide.get('slug')}")
        for field in ("signals", "assessment", "actions", "avoid", "questions"):
            if not isinstance(guide[field], list) or len(guide[field]) < 4:
                raise ValueError(f"youth_guide_{field}_incomplete:{guide['slug']}")
        if len(guide["sources"]) < 3 or not set(guide["sources"]) <= source_set:
            raise ValueError(f"youth_guide_sources_invalid:{guide['slug']}")
    for collection in collections:
        slugs = collection.get("guide_slugs")
        if not isinstance(slugs, list) or len(slugs) != 4 or not set(slugs) <= guide_set:
            raise ValueError(f"youth_collection_guides_invalid:{collection.get('slug')}")
        collected.extend(slugs)
    if sorted(collected) != sorted(guide_slugs):
        raise ValueError("youth_collections_must_cover_each_guide_once")
    for source in sources:
        if not str(source.get("url", "")).startswith("https://"):
            raise ValueError(f"youth_source_requires_https:{source.get('id')}")


def update_robots(site: Path) -> bool:
    path = site / "robots.txt"
    if not path.is_file():
        return False
    source = path.read_text(encoding="utf-8")
    block = (
        f"{ROBOTS_MARKER}\n"
        "Allow: /sectors/youth/\n"
    )
    pattern = re.compile(
        rf"{re.escape(ROBOTS_MARKER)}\nAllow: /sectors/youth/\n?",
        flags=re.I,
    )
    updated = pattern.sub("", source).rstrip() + "\n\n" + block
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def publish(site: Path, source_path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"youth_site_missing:{site}")
    data = json.loads(source_path.read_text(encoding="utf-8"))
    validate_source(data)
    sources = source_by_id(data)
    guide_map = {item["slug"]: item for item in data["guides"]}
    collection_by_guide: dict[str, dict[str, Any]] = {}
    for collection in data["collections"]:
        for slug in collection["guide_slugs"]:
            collection_by_guide[slug] = collection

    hub_canonical = f"{BASE}/sectors/youth/"
    hub_schemas = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": data["title"],
            "description": data["subtitle"],
            "url": hub_canonical,
            "inLanguage": "ar",
            "dateModified": data["reviewed_at"],
            "isPartOf": {"@type": "WebSite", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة", "url": BASE + "/"},
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "القطاعات", "item": BASE + "/sectors/"},
                {"@type": "ListItem", "position": 3, "name": data["title"], "item": hub_canonical},
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "numberOfItems": len(data["guides"]),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": guide["title"],
                    "url": f"{BASE}/sectors/youth/{guide['slug']}/",
                }
                for index, guide in enumerate(data["guides"], 1)
            ],
        },
    ]
    hub = document(
        title=f"{data['title']} | مركز عربي موثّق",
        description=data["subtitle"],
        canonical=hub_canonical,
        body=hub_body(data),
        schemas=hub_schemas,
        reviewed_at=data["reviewed_at"],
    )
    hub_path = site / "sectors" / "youth" / "index.html"
    hub_path.parent.mkdir(parents=True, exist_ok=True)
    hub_path.write_text(hub, encoding="utf-8")
    published_pages = [hub_path]

    collection_words: dict[str, int] = {}
    for collection in data["collections"]:
        canonical = f"{BASE}/sectors/youth/{collection['slug']}/"
        guides = [guide_map[slug] for slug in collection["guide_slugs"]]
        schemas = [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": collection["title"],
                "description": collection["summary"],
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "قطاع الشباب", "item": hub_canonical},
                    {"@type": "ListItem", "position": 2, "name": collection["title"], "item": canonical},
                ],
            },
            {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "numberOfItems": 4,
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": guide["title"],
                        "url": f"{BASE}/sectors/youth/{guide['slug']}/",
                    }
                    for index, guide in enumerate(guides, 1)
                ],
            },
        ]
        page = document(
            title=f"{collection['title']} | قطاع الشباب",
            description=collection["summary"],
            canonical=canonical,
            body=collection_body(collection, guides, sources, data["reviewed_at"]),
            schemas=schemas,
            reviewed_at=data["reviewed_at"],
        )
        target = site / "sectors" / "youth" / collection["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        published_pages.append(target)
        collection_words[collection["slug"]] = visible_words(page)

    guide_words: dict[str, int] = {}
    for guide in data["guides"]:
        collection = collection_by_guide[guide["slug"]]
        canonical = f"{BASE}/sectors/youth/{guide['slug']}/"
        schemas = [
            {
                "@context": "https://schema.org",
                "@type": ["Article", "MedicalWebPage"],
                "headline": guide["title"],
                "description": guide["summary"],
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
                "author": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"},
                "citation": [sources[source_id]["url"] for source_id in guide["sources"]],
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "قطاع الشباب", "item": hub_canonical},
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": collection["title"],
                        "item": f"{BASE}/sectors/youth/{collection['slug']}/",
                    },
                    {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
                ],
            },
        ]
        page = document(
            title=f"{guide['title']} | دليل الشباب واليافعين",
            description=guide["summary"],
            canonical=canonical,
            body=guide_body(guide, collection, sources, data["reviewed_at"]),
            schemas=schemas,
            reviewed_at=data["reviewed_at"],
        )
        target = site / "sectors" / "youth" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        published_pages.append(target)
        guide_words[guide["slug"]] = visible_words(page)

    robots_updated = update_robots(site)
    pages = sorted(published_pages)
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in pages)
    structural_errors: list[str] = []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(site).as_posix()
        if text.count("<h1") != 1:
            structural_errors.append(f"{relative}:h1")
        if text.count('rel="canonical"') != 1:
            structural_errors.append(f"{relative}:canonical")
        if "application/ld+json" not in text or "noindex" in text.lower():
            structural_errors.append(f"{relative}:indexability")
        if "<header" not in text or "<footer" not in text:
            structural_errors.append(f"{relative}:shell")
    report = {
        "version": VERSION,
        "status": "passed",
        "reviewed_at": data["reviewed_at"],
        "pages_published": len(pages),
        "hub_pages": 1,
        "collection_pages": len(data["collections"]),
        "guide_pages": len(data["guides"]),
        "institutional_sources": len(data["sources"]),
        "hub_words": visible_words(hub),
        "minimum_collection_words": min(collection_words.values()),
        "minimum_guide_words": min(guide_words.values()),
        "maximum_guide_words": max(guide_words.values()),
        "guide_words": guide_words,
        "collection_words": collection_words,
        "robots_updated": robots_updated,
        "structural_errors": structural_errors,
        "banned_terms_present": [term for term in BANNED if term in all_text],
        "unique_canonicals": len(set(re.findall(r'<link rel="canonical" href="([^"]+)"', all_text))),
        "publication_model": "source-backed-static-html",
        "clinical_review_status": "internal-editorial-methodological-review; not external independent clinical review",
    }
    if report["pages_published"] != 21:
        raise ValueError({"youth_page_count_contract": report})
    if report["hub_words"] < 1800:
        raise ValueError({"youth_hub_depth_contract": report})
    if report["minimum_collection_words"] < 700:
        raise ValueError({"youth_collection_depth_contract": report})
    if report["minimum_guide_words"] < 900:
        raise ValueError({"youth_guide_depth_contract": report})
    if report["structural_errors"] or report["banned_terms_present"]:
        raise ValueError({"youth_structure_language_contract": report})
    if report["unique_canonicals"] != 21:
        raise ValueError({"youth_canonical_contract": report})
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the evidence-backed youth mental-health sector")
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    print(json.dumps(publish(args.site, args.source), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
