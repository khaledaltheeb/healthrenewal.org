#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import urljoin

VERSION = 333
SITE_BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
MARKER = 'data-pterminology-experience="v333"'
VERIFY_FILE = "google644f1f7a8b7aaa2b.html"
ASSET_CSS = "assets/platform/platform-experience-v333.css"
ASSET_JS = "assets/platform/platform-experience-v333.js"
SEARCH_API = "api/platform-search-v333.json"
REPORT_API = "api/platform-experience-v333.json"
OPENAPI = "api/openapi-v333.json"

SECTION_NAMES = {
    "encyclopedia": "الموسوعة",
    "terms": "المصطلحات",
    "special-needs": "ذوو الاحتياجات الخاصة",
    "care-guides": "أدلة التعامل",
    "assessment-lab": "مختبر المقاييس",
    "cognitive-lab": "مختبر القدرات المعرفية",
    "daily-tools": "الأدوات اليومية",
    "tools": "الأدوات",
    "library": "المكتبة",
    "academic-library": "المكتبة الأكاديمية",
    "magazine": "المجلة والأبحاث",
    "research": "الأبحاث",
    "comparisons": "المقارنات",
    "child": "الطفل",
    "family": "الأسرة",
    "home": "الصحة النفسية المنزلية",
    "women": "الصحة النفسية للمرأة",
    "learning-paths": "مسارات التعلم",
    "topic-hubs": "المراكز الموضوعية",
    "guided-assessment": "الاستكشاف الموجّه",
    "provider-assessment-demo": "منصة مقدم الخدمة",
    "developers": "المطورون",
    "trust": "الثقة والمنهجية",
}

UTILITY_PREFIXES = {
    "404",
    "search",
    "my-library",
    "api",
    "developers",
    "sitemap",
}

ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
SPACE_RE = re.compile(r"\s+")
MANAGED_HEAD_RE = re.compile(
    r"\s*<!-- pterminology-experience-v333:start -->.*?<!-- pterminology-experience-v333:end -->\s*",
    re.I | re.S,
)
MANAGED_DEVELOPER_RE = re.compile(
    r"\s*<!-- platform-api-v333:start -->.*?<!-- platform-api-v333:end -->\s*",
    re.I | re.S,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = ARABIC_DIACRITICS.sub("", value).replace("ـ", "")
    table = str.maketrans(
        {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ٱ": "ا",
            "ى": "ي",
            "ؤ": "و",
            "ئ": "ي",
            "ة": "ه",
        }
    )
    value = value.translate(table)
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value)
    return SPACE_RE.sub(" ", value).strip()


def compact(value: str, limit: int = 320) -> str:
    value = SPACE_RE.sub(" ", html.unescape(value or "")).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"



@dataclass(slots=True)
class PageFacts:
    title: str = ""
    description: str = ""
    canonical: str = ""
    language: str = "ar"
    h1: str = ""
    noindex: bool = False
    body_text: str = ""
    keywords: list[str] = field(default_factory=list)


class FactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.facts = PageFacts()
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._skip_depth = 0
        self._visible: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "html" and values.get("lang"):
            self.facts.language = values["lang"].split("-")[0].lower()
        if tag in {"script", "style", "template", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title" or (tag == "h1" and not self.facts.h1):
            self._capture = tag
            self._buffer = []
        if tag == "meta":
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            content = values.get("content", "")
            if name == "description" or prop == "og:description":
                if not self.facts.description:
                    self.facts.description = compact(content)
            if name == "robots" and "noindex" in content.lower():
                self.facts.noindex = True
            if name == "keywords" and content:
                self.facts.keywords.extend(compact(part, 80) for part in content.split(",") if part.strip())
        if tag == "link":
            rels = values.get("rel", "").lower().split()
            if "canonical" in rels and values.get("href"):
                self.facts.canonical = values["href"].strip()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture == tag:
            value = compact(" ".join(self._buffer), 300)
            if tag == "title":
                self.facts.title = value
            elif tag == "h1":
                self.facts.h1 = value
            self._capture = None
            self._buffer = []
        if tag in {"script", "style", "template", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)
        if not self._skip_depth and data.strip():
            self._visible.append(data)

    def close(self) -> None:
        super().close()
        self.facts.body_text = compact(" ".join(self._visible), 2400)


def parse_facts(document: str) -> PageFacts:
    parser = FactParser()
    parser.feed(document)
    parser.close()
    return parser.facts


def relative_route(page: Path, site: Path) -> str:
    rel = page.relative_to(site).as_posix()
    if rel == "index.html":
        return ""
    if rel.endswith("/index.html"):
        return rel[: -len("index.html")]
    return rel


def route_url(route: str) -> str:
    return urljoin(SITE_BASE, route)


def page_section(route: str) -> str:
    first = PurePosixPath(route).parts[0] if route else ""
    return SECTION_NAMES.get(first, "المنصة")


def is_eligible(page: Path, site: Path, facts: PageFacts) -> bool:
    if page.name == VERIFY_FILE or facts.noindex:
        return False
    route = relative_route(page, site)
    if route.startswith("api/"):
        return False
    if page.name.lower() in {"404.html", "offline.html"}:
        return False
    if not (facts.title or facts.h1):
        return False
    return True


def indexable_for_search(route: str) -> bool:
    first = PurePosixPath(route).parts[0] if route else ""
    return first not in UTILITY_PREFIXES


def build_search_item(page: Path, site: Path, facts: PageFacts) -> dict[str, object]:
    route = relative_route(page, site)
    title = facts.h1 or facts.title or route
    description = facts.description or compact(facts.body_text, 260)
    section = page_section(route)
    canonical = facts.canonical if facts.canonical.startswith("http") else route_url(route)
    keyword_text = " ".join(facts.keywords)
    search_text = normalize_arabic(" ".join((title, facts.title, description, section, keyword_text, route.replace("-", " "))))
    tokens = [token for token in dict.fromkeys(search_text.split()) if len(token) > 1][:80]
    return {
        "title": title,
        "description": description,
        "url": canonical,
        "path": route,
        "section": section,
        "language": facts.language,
        "tokens": tokens,
    }


def html_page(title: str, description: str, main: str, extra_head: str = "") -> str:
    if not extra_head:
        extra_head = managed_head()
    canonical = route_url("search/" if title.startswith("البحث") else "my-library/")
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
{extra_head}
</head>
<body>
<a class="skip-link" href="#main">تجاوز إلى المحتوى الرئيسي</a>
<main id="main" class="pte-utility-page">
{main}
</main>
</body>
</html>
'''


def search_page() -> str:
    main = '''
<header class="pte-utility-hero">
<p class="pte-eyebrow">بحث شامل في المنصة</p>
<h1>ابحث بمرونة في جميع الصفحات</h1>
<p>يتسامح البحث مع اختلاف الهمزات والتشكيل وبعض الأخطاء الإملائية، ويجمع النتائج من الموسوعة والمكتبة والأدلة والمقارنات والأدوات.</p>
</header>
<section aria-labelledby="search-title" class="pte-panel">
<h2 id="search-title">أدخل كلمة أو سؤالًا</h2>
<label for="pte-main-search">مصطلح البحث</label>
<input id="pte-main-search" type="search" autocomplete="off" placeholder="مثال: فرط الحركه، القلق عند الطفل، دعم التواصل">
<div class="pte-search-meta" id="pte-search-meta" aria-live="polite"></div>
<div id="pte-search-results" class="pte-search-results"></div>
</section>
<noscript><p class="pte-notice">يحتاج البحث التفاعلي إلى JavaScript. يمكن استخدام خريطة الموقع أو المراكز الموضوعية للتصفح.</p></noscript>
'''
    return html_page(
        "البحث الذكي الشامل | منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "بحث عربي وإنجليزي متسامح مع الأخطاء الإملائية في جميع أقسام المنصة.",
        main,
    )


def library_page() -> str:
    main = '''
<header class="pte-utility-hero">
<p class="pte-eyebrow">بياناتك تبقى في متصفحك</p>
<h1>مكتبتي وسجل الأدوات المحلي</h1>
<p>احفظ الصفحات والنتائج التي تختارها يدويًا. لا تُرسل هذه البيانات إلى خادم، ويمكن تصديرها أو حذفها في أي وقت.</p>
</header>
<section class="pte-panel" aria-labelledby="saved-title">
<div class="pte-section-heading"><h2 id="saved-title">الصفحات المحفوظة</h2><button type="button" data-pte-export>تصدير نسخة JSON</button></div>
<div id="pte-library-items"></div>
</section>
<section class="pte-panel" aria-labelledby="history-title">
<div class="pte-section-heading"><h2 id="history-title">النتائج المحفوظة اختياريًا</h2><button type="button" class="pte-danger" data-pte-clear-results>حذف سجل النتائج</button></div>
<p class="pte-notice">يُحفظ ملخص النتيجة فقط بعد ضغط زر الحفظ؛ لا تُحفظ إجابات النماذج أو بيانات الهوية.</p>
<div id="pte-result-history"></div>
</section>
<section class="pte-panel" aria-labelledby="privacy-title">
<h2 id="privacy-title">التحكم والخصوصية</h2>
<button type="button" class="pte-danger" data-pte-clear-all>حذف جميع البيانات المحلية</button>
<p id="pte-storage-status" aria-live="polite"></p>
</section>
'''
    return html_page(
        "مكتبتي المحلية | منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "حفظ الصفحات ونتائج الأدوات اختياريًا داخل المتصفح مع إمكان التصدير والحذف.",
        main,
    )


def developer_section(item_count: int) -> str:
    return f'''
<!-- platform-api-v333:start -->
<section id="platform-api-v333" class="pte-api-docs">
<p class="pte-eyebrow">واجهة بيانات عامة للقراءة فقط</p>
<h2>فهرس البحث وواجهات التكامل v333</h2>
<p>توفر المنصة ملفات JSON ثابتة لا تحتاج إلى مفتاح API. تحتوي النسخة الحالية على <strong>{item_count}</strong> صفحة قابلة للبحث، ولا تعرض بيانات مستخدمين أو نتائج أدوات محلية.</p>
<div class="pte-api-grid">
<article><h3>فهرس البحث</h3><code>{BASE_PATH}{SEARCH_API}</code><p>العنوان والوصف والقسم والرابط وكلمات مطبّعة للبحث.</p></article>
<article><h3>وصف OpenAPI</h3><code>{BASE_PATH}{OPENAPI}</code><p>عقد OpenAPI 3.1 للواجهات العامة الثابتة.</p></article>
<article><h3>حالة التنفيذ</h3><code>{BASE_PATH}{REPORT_API}</code><p>تغطية الصفحات والأصول واختبارات الوظائف.</p></article>
<article><h3>بيانات المنصة</h3><code>{BASE_PATH}platform.json</code><p>إصدارات الواجهات وروابط الأقسام وسياسة الاستخدام.</p></article>
</div>
<h3>مثال JavaScript</h3>
<pre><code>const response = await fetch('{BASE_PATH}{SEARCH_API}');
const index = await response.json();
console.log(index.count, index.items[0]);</code></pre>
<p>يجب احترام حقوق المصادر الأصلية وعدم إعادة نشر المحتوى الكامل أو المواد المقيدة. الروابط والبيانات الوصفية متاحة للتكامل المسؤول مع الإحالة إلى المنصة.</p>
</section>
<!-- platform-api-v333:end -->
'''


CSS = r'''
:root{--pte-accent:#0b6b66;--pte-accent-2:#9a6b22;--pte-bg:#f7f5ef;--pte-card:#fff;--pte-text:#18201f;--pte-muted:#53615e;--pte-border:#d5ddd9;--pte-danger:#9d2530}
.pte-utility-page{max-width:1120px;margin:0 auto;padding:clamp(1rem,3vw,3rem);color:var(--pte-text)}
.pte-utility-hero{padding:clamp(1.3rem,4vw,3.5rem);border-radius:1.5rem;background:linear-gradient(135deg,#e8f3f0,#fff8e8);margin-block:1rem 1.5rem}
.pte-utility-hero h1{font-size:clamp(2rem,5vw,4rem);line-height:1.15;margin:.3rem 0 1rem}.pte-eyebrow{font-weight:800;color:var(--pte-accent);letter-spacing:.04em}
.pte-panel,.pte-api-docs{background:var(--pte-card);border:1px solid var(--pte-border);border-radius:1.2rem;padding:clamp(1rem,3vw,2rem);margin-block:1rem;box-shadow:0 14px 38px rgba(18,43,39,.07)}
.pte-panel input[type=search]{width:100%;font:inherit;padding:1rem 1.1rem;border:2px solid var(--pte-border);border-radius:.9rem;background:#fff;color:var(--pte-text)}
.pte-panel input[type=search]:focus{outline:3px solid rgba(11,107,102,.22);border-color:var(--pte-accent)}
.pte-search-meta{min-height:1.7rem;margin:.75rem 0;color:var(--pte-muted)}.pte-search-results{display:grid;gap:.8rem}
.pte-result-card{display:block;border:1px solid var(--pte-border);border-radius:1rem;padding:1rem;text-decoration:none;color:inherit;background:#fff}.pte-result-card:hover,.pte-result-card:focus-visible{border-color:var(--pte-accent);box-shadow:0 8px 24px rgba(11,107,102,.12)}
.pte-result-card h3{margin:0 0 .35rem;color:var(--pte-accent)}.pte-result-card p{margin:.25rem 0;color:var(--pte-muted)}.pte-result-card small{font-weight:700;color:var(--pte-accent-2)}
.pte-tools{position:fixed;z-index:2147482000;inset-inline-end:clamp(.5rem,2vw,1rem);bottom:clamp(.5rem,2vw,1rem);display:flex;gap:.4rem;flex-wrap:wrap;max-width:min(96vw,34rem);justify-content:flex-end}
.pte-tools button,.pte-tools a,.pte-panel button,.pte-api-docs button{font:inherit;font-weight:700;border:1px solid var(--pte-border);border-radius:999px;padding:.65rem .9rem;background:#fff;color:var(--pte-text);text-decoration:none;box-shadow:0 5px 20px rgba(0,0,0,.1);cursor:pointer}.pte-tools button:hover,.pte-tools a:hover{border-color:var(--pte-accent)}
.pte-search-dialog{border:0;border-radius:1.2rem;padding:0;width:min(94vw,760px);max-height:86vh;color:var(--pte-text);box-shadow:0 30px 90px rgba(0,0,0,.35)}.pte-search-dialog::backdrop{background:rgba(8,23,21,.72)}
.pte-dialog-inner{padding:1rem}.pte-dialog-head{display:flex;justify-content:space-between;gap:1rem;align-items:center}.pte-dialog-head button{font:inherit;border:0;background:transparent;font-size:1.5rem;cursor:pointer}.pte-dialog-inner input{width:100%;font:inherit;padding:.9rem;border:2px solid var(--pte-border);border-radius:.8rem}.pte-dialog-results{overflow:auto;max-height:58vh;margin-top:.8rem;display:grid;gap:.6rem}
.pte-recommendations{border:1px solid var(--pte-border);border-inline-start:5px solid var(--pte-accent);border-radius:1rem;padding:1rem;margin-block:1rem;background:#f8fcfb}.pte-recommendations h2,.pte-recommendations h3{margin-top:0}.pte-recommendations ul{display:grid;gap:.55rem}.pte-recommendations-actions{display:flex;gap:.5rem;flex-wrap:wrap}.pte-recommendations button{font:inherit;font-weight:700;border:1px solid var(--pte-accent);border-radius:.7rem;padding:.55rem .8rem;background:#fff;cursor:pointer}
.pte-library-card{border-bottom:1px solid var(--pte-border);padding:1rem 0}.pte-library-card:last-child{border-bottom:0}.pte-library-card h3{margin:.15rem 0}.pte-library-card-actions{display:flex;gap:.5rem;flex-wrap:wrap}.pte-library-card button{box-shadow:none}.pte-danger{color:var(--pte-danger)!important;border-color:#e4b9be!important}.pte-section-heading{display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap}.pte-notice{padding:.8rem 1rem;border-radius:.8rem;background:#f4f0e7;color:var(--pte-muted)}
.pte-api-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem}.pte-api-grid article{border:1px solid var(--pte-border);border-radius:1rem;padding:1rem}.pte-api-docs pre{overflow:auto;padding:1rem;border-radius:.8rem;background:#12211e;color:#eef8f5;direction:ltr;text-align:left}.pte-api-docs code{overflow-wrap:anywhere}
.pte-toast{position:fixed;z-index:2147483000;inset-inline-start:50%;bottom:5rem;transform:translateX(-50%);background:#102a26;color:#fff;padding:.75rem 1rem;border-radius:.8rem;box-shadow:0 10px 30px rgba(0,0,0,.25)}
@media(max-width:640px){.pte-tools{inset-inline: .45rem;justify-content:center}.pte-tools button,.pte-tools a{padding:.55rem .7rem;font-size:.9rem}.pte-search-dialog{width:96vw}.pte-utility-page{padding:.8rem}}
@media print{.pte-tools,.pte-search-dialog,.pte-toast{display:none!important}}
'''.strip() + "\n"


JS = r'''
(()=>{"use strict";
const V=333,BASE="/pterminology-site/",INDEX=BASE+"api/platform-search-v333.json";
const KEYS={library:"pterminology.library.v333",results:"pterminology.results.v333"};
const state={index:null,indexPromise:null,lastResultText:""};
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>Array.from(r.querySelectorAll(s));
function normalize(v){return String(v||"").normalize("NFKC").toLowerCase().replace(/[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06edـ]/g,"").replace(/[أإآٱ]/g,"ا").replace(/ى/g,"ي").replace(/ؤ/g,"و").replace(/ئ/g,"ي").replace(/ة/g,"ه").replace(/[^\w\u0600-\u06ff]+/g," ").replace(/\s+/g," ").trim()}
const synonyms={"توحد":["طيف التوحد","autism","asd"],"فرط الحركه":["تشتت الانتباه","adhd","فرط النشاط"],"اكتئاب":["depression","مزاج منخفض"],"قلق":["anxiety","توتر"],"داون":["متلازمه داون","down syndrome"],"نطق":["كلام","لغه","تواصل"],"اعاقه":["احتياجات خاصه","ذوو الاحتياجات الخاصه"],"مقياس":["اختبار","تقييم","assessment"]};
function expandQuery(q){let n=normalize(q),parts=[n];Object.entries(synonyms).forEach(([k,vals])=>{if(n.includes(k)||vals.some(v=>n.includes(normalize(v))))parts.push(k,...vals)});return normalize(parts.join(" "))}
function trigrams(s){s=`  ${s}  `;const out=new Set;for(let i=0;i<s.length-2;i++)out.add(s.slice(i,i+3));return out}
function jaccard(a,b){if(!a.size||!b.size)return 0;let n=0;a.forEach(x=>{if(b.has(x))n++});return n/(a.size+b.size-n)}
function distance(a,b,cap=4){if(Math.abs(a.length-b.length)>cap)return cap+1;let p=Array.from({length:b.length+1},(_,i)=>i),c=[];for(let i=1;i<=a.length;i++){c=[i];let row=i;for(let j=1;j<=b.length;j++){let v=Math.min(c[j-1]+1,p[j]+1,p[j-1]+(a[i-1]===b[j-1]?0:1));c[j]=v;row=Math.min(row,v)}if(row>cap)return cap+1;p=c}return p[b.length]}
async function loadIndex(){if(state.index)return state.index;if(!state.indexPromise)state.indexPromise=fetch(INDEX,{cache:"force-cache"}).then(r=>{if(!r.ok)throw new Error(`index ${r.status}`);return r.json()}).then(d=>state.index=d.items||[]);return state.indexPromise}
function scoreItem(q,item){const phrase=expandQuery(q),tokens=phrase.split(" ").filter(Boolean),hay=normalize([item.title,item.description,item.section,(item.tokens||[]).join(" ")].join(" "));if(!phrase||!hay)return 0;let score=0;if(hay.includes(phrase))score+=120;if(normalize(item.title).includes(phrase))score+=90;tokens.forEach(t=>{if(hay.includes(t))score+=18;if(normalize(item.title).split(" ").some(x=>x.startsWith(t)))score+=16});score+=Math.round(jaccard(trigrams(phrase),trigrams(hay.slice(0,600)))*65);const titleWords=normalize(item.title).split(" ");tokens.forEach(t=>{if(t.length>3&&titleWords.some(w=>distance(t,w,2)<=2))score+=12});return score}
async function search(q,limit=20){const index=await loadIndex();const phrase=normalize(q);if(phrase.length<2)return[];return index.map(item=>({item,score:scoreItem(q,item)})).filter(x=>x.score>7).sort((a,b)=>b.score-a.score||a.item.title.localeCompare(b.item.title,"ar")).slice(0,limit).map(x=>x.item)}
function esc(v){return String(v||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function resultHTML(item){return `<a class="pte-result-card" href="${esc(item.url)}"><small>${esc(item.section)}</small><h3>${esc(item.title)}</h3><p>${esc(item.description||"")}</p></a>`}
function toast(message){const old=$(".pte-toast");if(old)old.remove();const el=document.createElement("div");el.className="pte-toast";el.setAttribute("role","status");el.textContent=message;document.body.append(el);setTimeout(()=>el.remove(),2600)}
function safeRead(key){try{const v=JSON.parse(localStorage.getItem(key)||"[]");return Array.isArray(v)?v:[]}catch{return[]}}
function safeWrite(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}}
function currentRecord(){return{title:document.querySelector("h1")?.textContent.trim()||document.title,url:location.href.split("#")[0],section:document.querySelector('meta[name="section"]')?.content||location.pathname.split("/").filter(Boolean)[1]||"المنصة",savedAt:new Date().toISOString()}}
function saveCurrent(){const record=currentRecord(),items=safeRead(KEYS.library).filter(x=>x.url!==record.url);items.unshift(record);if(safeWrite(KEYS.library,items.slice(0,300)))toast("تم الحفظ في مكتبتك على هذا المتصفح");else toast("تعذر التخزين المحلي في هذا المتصفح")}
function removeItem(key,url){safeWrite(key,safeRead(key).filter(x=>x.url!==url));renderLibrary()}
function exportData(){const data={version:V,exportedAt:new Date().toISOString(),pages:safeRead(KEYS.library),results:safeRead(KEYS.results)};const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`pterminology-library-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500)}
function renderLibrary(){const pages=$("#pte-library-items"),results=$("#pte-result-history"),status=$("#pte-storage-status");if(!pages&&!results)return;const p=safeRead(KEYS.library),r=safeRead(KEYS.results);if(pages)pages.innerHTML=p.length?p.map(x=>`<article class="pte-library-card"><small>${esc(x.section||"")}</small><h3><a href="${esc(x.url)}">${esc(x.title)}</a></h3><p>${new Date(x.savedAt).toLocaleString("ar-JO")}</p><div class="pte-library-card-actions"><button type="button" data-remove-page="${esc(x.url)}">إزالة</button></div></article>`).join(""):'<p class="pte-notice">لم تحفظ صفحات بعد. استخدم زر «حفظ الصفحة» أثناء التصفح.</p>';if(results)results.innerHTML=r.length?r.map(x=>`<article class="pte-library-card"><h3><a href="${esc(x.url)}">${esc(x.title)}</a></h3><p>${esc(x.summary)}</p><small>${new Date(x.savedAt).toLocaleString("ar-JO")}</small></article>`).join(""):'<p class="pte-notice">لا توجد نتائج محفوظة. الحفظ اختياري ويحدث فقط بعد ضغط الزر بجانب النتيجة.</p>';if(status)status.textContent=`${p.length} صفحة محفوظة و${r.length} نتيجة محفوظة محليًا.`;$$('[data-remove-page]').forEach(b=>b.onclick=()=>removeItem(KEYS.library,b.dataset.removePage))}
function utilityBar(){if($(".pte-tools")||location.pathname.endsWith("/my-library/"))return;const bar=document.createElement("nav");bar.className="pte-tools";bar.setAttribute("aria-label","أدوات الصفحة");bar.innerHTML='<button type="button" data-open-search aria-keyshortcuts="Control+K Meta+K">بحث</button><button type="button" data-save-current>حفظ الصفحة</button><a href="'+BASE+'my-library/">مكتبتي</a>';document.body.append(bar);$('[data-save-current]',bar).onclick=saveCurrent;$('[data-open-search]',bar).onclick=openDialog}
function dialog(){let d=$("#pte-search-dialog");if(d)return d;d=document.createElement("dialog");d.id="pte-search-dialog";d.className="pte-search-dialog";d.innerHTML='<div class="pte-dialog-inner"><div class="pte-dialog-head"><h2>بحث سريع في المنصة</h2><button type="button" aria-label="إغلاق">×</button></div><input type="search" placeholder="اكتب مصطلحًا أو سؤالًا" aria-label="البحث"><div class="pte-dialog-results" aria-live="polite"></div><p><a href="'+BASE+'search/">فتح صفحة البحث الكاملة</a></p></div>';document.body.append(d);$("button",d).onclick=()=>d.close();const input=$("input",d),out=$(".pte-dialog-results",d);let timer;input.oninput=()=>{clearTimeout(timer);timer=setTimeout(async()=>{const q=input.value.trim();out.innerHTML=q.length<2?'<p>اكتب حرفين على الأقل.</p>':'<p>جارٍ البحث…</p>';if(q.length>=2){const items=await search(q,10);out.innerHTML=items.length?items.map(resultHTML).join(""):'<p>لا توجد نتيجة مباشرة. جرّب كلمة أقصر أو مرادفًا.</p>'}},120)};return d}
function openDialog(){const d=dialog();d.showModal();setTimeout(()=>$("input",d)?.focus(),30)}
function bindSearchPage(){const input=$("#pte-main-search"),out=$("#pte-search-results"),meta=$("#pte-search-meta");if(!input||!out)return;let timer;const run=async()=>{const q=input.value.trim();if(q.length<2){out.innerHTML="";meta.textContent="اكتب حرفين على الأقل.";return}meta.textContent="جارٍ البحث…";const items=await search(q,50);meta.textContent=`${items.length} نتيجة مرتبة حسب الصلة`;out.innerHTML=items.length?items.map(resultHTML).join(""):'<p class="pte-notice">لم نجد نتيجة مباشرة. جرّب حذف كلمة أو استخدام مرادف.</p>';history.replaceState(null,"",q?`?q=${encodeURIComponent(q)}`:location.pathname)};input.oninput=()=>{clearTimeout(timer);timer=setTimeout(run,140)};const initial=new URLSearchParams(location.search).get("q");if(initial){input.value=initial;run()}else loadIndex().then(items=>{meta.textContent=`الفهرس يشمل ${items.length.toLocaleString("ar-JO")} صفحة.`})}
function assessmentPage(){return /\/(assessment-lab|cognitive-lab|guided-assessment|provider-assessment-demo|daily-tools|tools)\//.test(location.pathname)}
function resultCandidates(){return $$('[data-result],[data-score],.result,.results,#result,#results,[role="status"],[aria-live]').filter(el=>{const text=(el.innerText||"").trim();return text.length>=20&&text.length<=3000&&el.offsetParent!==null&&!el.closest(".pte-recommendations")})}
async function recommendations(query){const items=await search(query,30),self=location.href.split("#")[0];return items.filter(x=>x.url!==self&&!/\/(assessment-lab|cognitive-lab|guided-assessment|provider-assessment-demo)\//.test(x.url)).slice(0,6)}
async function attachRecommendations(target,detail={}){if(!target||target.dataset.pteEnhanced==="1")return;const summary=String(detail.summary||target.innerText||"").replace(/\s+/g," ").trim().slice(0,500);if(summary.length<20||summary===state.lastResultText)return;state.lastResultText=summary;target.dataset.pteEnhanced="1";const box=document.createElement("section");box.className="pte-recommendations";box.dataset.pteRecommendations="v333";box.innerHTML='<h2>خطوتك التالية</h2><p>هذه الروابط للتعلّم والتنظيم فقط؛ النتيجة المنفردة لا تثبت تشخيصًا ولا تحدد علاجًا.</p><div class="pte-recommendation-links"><p>جارٍ إعداد قراءات مرتبطة…</p></div><div class="pte-recommendations-actions"><button type="button" data-save-result>حفظ ملخص النتيجة محليًا</button><a href="'+BASE+'my-library/">فتح مكتبتي</a></div>';target.insertAdjacentElement("afterend",box);const q=[document.title,document.querySelector("h1")?.textContent,detail.topic].filter(Boolean).join(" ");const items=await recommendations(q);$(".pte-recommendation-links",box).innerHTML=items.length?'<ul>'+items.map(x=>`<li><a href="${esc(x.url)}">${esc(x.title)}</a> <small>(${esc(x.section)})</small></li>`).join("")+'</ul>':'<p>استخدم البحث الشامل للوصول إلى قراءة مرتبطة.</p>';$('[data-save-result]',box).onclick=()=>{const record={title:document.querySelector("h1")?.textContent.trim()||document.title,url:location.href.split("#")[0],summary,savedAt:new Date().toISOString()};const values=safeRead(KEYS.results);values.unshift(record);if(safeWrite(KEYS.results,values.slice(0,100)))toast("حُفظ ملخص النتيجة محليًا دون إجابات النموذج");else toast("تعذر التخزين المحلي")}}
function watchAssessment(){if(!assessmentPage())return;const scan=()=>resultCandidates().forEach(el=>attachRecommendations(el));new MutationObserver(()=>setTimeout(scan,80)).observe(document.body,{subtree:true,childList:true,characterData:true});document.addEventListener("pterminology:assessment-result",e=>{const target=e.detail?.target instanceof Element?e.detail.target:resultCandidates()[0];attachRecommendations(target,e.detail||{})});setTimeout(scan,350)}
function bindLibrary(){renderLibrary();$('[data-pte-export]')?.addEventListener("click",exportData);$('[data-pte-clear-results]')?.addEventListener("click",()=>{if(confirm("حذف سجل النتائج المحلي؟")){safeWrite(KEYS.results,[]);renderLibrary()}});$('[data-pte-clear-all]')?.addEventListener("click",()=>{if(confirm("حذف جميع الصفحات والنتائج المحفوظة في هذا المتصفح؟")){safeWrite(KEYS.library,[]);safeWrite(KEYS.results,[]);renderLibrary()}})}
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();openDialog()}});
function init(){utilityBar();bindSearchPage();bindLibrary();watchAssessment()}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();
'''.strip() + "\n"


def managed_head() -> str:
    return f'''\n<!-- pterminology-experience-v333:start -->
<link rel="stylesheet" href="{BASE_PATH}{ASSET_CSS}" {MARKER}>
<script defer src="{BASE_PATH}{ASSET_JS}" {MARKER}></script>
<!-- pterminology-experience-v333:end -->\n'''


def inject_assets(document: str) -> tuple[str, bool]:
    if document.count(MARKER) == 2 and "<!-- pterminology-experience-v333:start -->" in document and "<!-- pterminology-experience-v333:end -->" in document:
        return document, False
    cleaned = MANAGED_HEAD_RE.sub("\n", document)
    payload = managed_head()
    updated, count = re.subn(r"</head\s*>", payload + "</head>", cleaned, count=1, flags=re.I)
    if count != 1:
        return document, False
    return updated, updated != document


def inject_developer_docs(document: str, count: int) -> tuple[str, bool]:
    payload = developer_section(count)
    if payload.strip() in document:
        return document, False
    cleaned = MANAGED_DEVELOPER_RE.sub("\n", document)
    updated, matches = re.subn(r"</main\s*>", payload + "</main>", cleaned, count=1, flags=re.I)
    if matches != 1:
        updated, matches = re.subn(r"</body\s*>", payload + "</body>", cleaned, count=1, flags=re.I)
    if matches != 1:
        return document, False
    return updated, updated != document


def ensure_page(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if original == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_platform_json(site: Path, item_count: int) -> None:
    path = site / "platform.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.update(
        {
            "schema_version": VERSION,
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "base_url": SITE_BASE,
            "generated_at": utc_now(),
            "public_read_only": True,
            "privacy": "لا تتضمن الواجهات العامة بيانات المستخدم أو التخزين المحلي.",
            "endpoints": {
                "search_index": route_url(SEARCH_API),
                "openapi": route_url(OPENAPI),
                "implementation_report": route_url(REPORT_API),
            },
            "searchable_pages": item_count,
        }
    )
    write_json(path, payload)


def openapi_payload(item_count: int) -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Pterminology Public Static APIs",
            "version": "333.0.0",
            "description": "واجهات JSON ثابتة للقراءة فقط، دون بيانات مستخدمين أو نتائج محلية.",
        },
        "servers": [{"url": SITE_BASE.rstrip("/")}],
        "paths": {
            f"/{SEARCH_API}": {
                "get": {
                    "summary": "فهرس البحث الكامل",
                    "responses": {
                        "200": {
                            "description": f"فهرس يضم {item_count} صفحة",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            f"/{REPORT_API}": {
                "get": {
                    "summary": "تقرير تطبيق وظائف المنصة",
                    "responses": {"200": {"description": "تقرير التغطية والاختبارات"}},
                }
            },
        },
    }


def run(site: Path, strict: bool = False, min_pages: int = 0) -> dict[str, object]:
    if not site.is_dir():
        raise FileNotFoundError(f"Missing site directory: {site}")

    assets_changed = 0
    assets_changed += int(ensure_page(site / ASSET_CSS, CSS))
    assets_changed += int(ensure_page(site / ASSET_JS, JS))
    utility_changed = 0
    utility_changed += int(ensure_page(site / "search/index.html", search_page()))
    utility_changed += int(ensure_page(site / "my-library/index.html", library_page()))

    pages: list[tuple[Path, PageFacts]] = []
    errors: list[str] = []
    for page in sorted(site.rglob("*.html")):
        try:
            document = page.read_text(encoding="utf-8")
            facts = parse_facts(document)
            if is_eligible(page, site, facts):
                pages.append((page, facts))
        except Exception as exc:  # pragma: no cover - production evidence path
            errors.append(f"{page.relative_to(site).as_posix()}: {type(exc).__name__}: {exc}")

    items = [
        build_search_item(page, site, facts)
        for page, facts in pages
        if indexable_for_search(relative_route(page, site))
    ]
    items.sort(key=lambda item: (str(item["section"]), str(item["title"]), str(item["url"])))
    search_payload = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "count": len(items),
        "normalization": "arabic-diacritics-hamza-letter-folding-plus-trigram-and-edit-distance-ranking",
        "privacy": "public-page metadata only; no local library or assessment results",
        "items": items,
    }
    write_json(site / SEARCH_API, search_payload)
    write_json(site / OPENAPI, openapi_payload(len(items)))
    merge_platform_json(site, len(items))

    developers = site / "developers/index.html"
    developer_changed = 0
    if developers.exists():
        document = developers.read_text(encoding="utf-8")
        updated, changed = inject_developer_docs(document, len(items))
        if changed:
            developers.write_text(updated, encoding="utf-8")
            developer_changed = 1
    else:
        content = html_page(
            "واجهة المطورين والتكامل | منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "توثيق واجهات JSON العامة للبحث والتكامل المسؤول.",
            f"<h1>واجهة المطورين والتكامل</h1>{developer_section(len(items))}",
        )
        developer_changed = int(ensure_page(developers, content))

    pages_updated = 0
    pages_covered = 0
    for page in sorted(site.rglob("*.html")):
        if page.name == VERIFY_FILE or page.name.lower() in {"404.html", "offline.html"}:
            continue
        document = page.read_text(encoding="utf-8")
        facts = parse_facts(document)
        if not is_eligible(page, site, facts):
            continue
        updated, changed = inject_assets(document)
        if changed:
            page.write_text(updated, encoding="utf-8")
            pages_updated += 1
        if MARKER in updated:
            pages_covered += 1
        else:
            errors.append(f"asset_marker_missing:{page.relative_to(site).as_posix()}")

    report = {
        "schema_version": VERSION,
        "status": "passed",
        "generated_at": utc_now(),
        "eligible_pages": len(pages),
        "searchable_pages": len(items),
        "experience_covered_pages": pages_covered,
        "coverage_ratio": round(pages_covered / len(pages), 6) if pages else 0.0,
        "pages_updated": pages_updated,
        "assets_changed": assets_changed,
        "utility_pages_changed": utility_changed,
        "developer_page_changed": developer_changed,
        "features": {
            "full_site_search": True,
            "arabic_typo_tolerance": True,
            "keyboard_search": True,
            "local_library": True,
            "optional_local_result_history": True,
            "post_tool_recommendations": True,
            "developer_openapi": True,
            "no_server_side_user_data": True,
        },
        "storage_keys": ["pterminology.library.v333", "pterminology.results.v333"],
        "errors": errors,
    }
    if errors or report["coverage_ratio"] != 1.0 or len(items) < min_pages:
        report["status"] = "failed"
    write_json(site / REPORT_API, report)
    if strict and report["status"] != "passed":
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the site-wide search, local library, and user-journey layer.")
    parser.add_argument("site", nargs="?", default="_site")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--min-pages", type=int, default=0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run(Path(args.site), strict=args.strict, min_pages=args.min_pages)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
