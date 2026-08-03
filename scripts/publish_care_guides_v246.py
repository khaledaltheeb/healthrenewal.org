from __future__ import annotations

import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from care_guides_catalog_v246 import EXPECTED_GUIDES as EXPECTED_INSTITUTIONAL_GUIDES
from care_guides_catalog_v246 import institutional_guides

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
RELEASE_DATE = "2026-07-26"
CONTENT_RELEASE_VERSION = 246
EXPECTED_LEGACY_SOURCE_GUIDES = 14
EXPECTED_SOURCE_GUIDES = 101
MINIMUM_PUBLISHED_GUIDES = 100
BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}
DATA_FILES = (
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
    ROOT / "content/v18/care-guides-family-anxiety-panic-support-ar.json",
    ROOT / "content/v18/care-guides-family-ocd-support-ar.json",
    ROOT / "content/v18/care-guides-bipolar-family-early-warning-plan-ar.json",
    ROOT / "content/v18/care-guides-trauma-ptsd-family-support-ar.json",
    ROOT / "content/v18/care-guides-eating-disorder-family-support-ar.json",
    ROOT / "content/v18/care-guides-self-harm-family-safety-support-ar.json",
)
TRUSTED_SOURCE_HOSTS = {
    "www.who.int", "www.nice.org.uk", "cks.nice.org.uk", "www.nhs.uk", "www.cdc.gov",
    "www.nimh.nih.gov", "www.nia.nih.gov", "www.nidcd.nih.gov", "www.nhlbi.nih.gov",
    "www.unicef.org", "www.ptsd.va.gov", "store.samhsa.gov",
}
SECTION_LABELS = {
    "understanding": "فهم الحالة دون وصم",
    "what_the_person_may_feel": "ما الذي قد يشعر به الشخص من الداخل؟",
    "strengths_and_differences": "نقاط القوة والفروق الفردية",
    "communication_plan": "خطة التواصل",
    "sensory_plan": "خطة التنظيم الحسي",
    "observe": "ما الذي نراقبه؟",
    "conversation_steps": "خطوات الحوار",
    "do": "ما الذي يمكنك فعله؟",
    "avoid": "ما الذي ينبغي تجنبه؟",
    "home_plan": "خطة الدعم في المنزل",
    "school_plan": "خطة الدعم في المدرسة",
    "homework_protocol": "بروتوكول الواجبات وبدء المهام",
    "transition_protocol": "بروتوكول الانتقالات والتغيير",
    "meltdown_protocol": "بروتوكول الانهيار والتصعيد",
    "wandering_protocol": "بروتوكول الخروج أو الضياع",
    "emotion_protocol": "بروتوكول الانفعال والتصعيد",
    "sleep_plan": "خطة النوم",
    "food_plan": "خطة الطعام والتغذية",
    "medication_awareness": "التوعية الدوائية وحدود دور الأسرة",
    "plan": "الخطة العملية المتكاملة",
    "when_to_seek_help": "متى نطلب مساعدة مهنية أو عاجلة؟",
    "warning_signs": "إشارات الاستنزاف أو الخطر",
    "caregiver_plan": "خطة مقدم الرعاية",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def word_count(value: object) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", json.dumps(value, ensure_ascii=False), flags=re.UNICODE))


def actionable_count(guide: dict) -> int:
    excluded = {"audience", "search_intent", "sources"}
    return sum(len(value) for key, value in guide.items() if isinstance(value, list) and key not in excluded)


def source_schema(guide: dict) -> list[str]:
    return [source["url"] for source in guide.get("sources", [])]


def structured_data(guide: dict, canonical: str) -> str:
    steps: list[dict] = []
    position = 1
    for key in ("do", "communication_plan", "conversation_steps", "plan", "home_plan", "school_plan", "caregiver_plan"):
        for item in guide.get(key, []):
            steps.append({"@type": "HowToStep", "position": position, "name": item, "text": item})
            position += 1
    graph = [
        {
            "@type": "WebPage",
            "@id": canonical + "#webpage",
            "url": canonical,
            "name": guide["title"],
            "description": guide["summary"],
            "inLanguage": "ar",
            "dateModified": guide.get("reviewed_at", RELEASE_DATE),
            "isAccessibleForFree": True,
        },
        {
            "@type": "Article",
            "@id": canonical + "#article",
            "headline": guide["title"],
            "description": guide["summary"],
            "inLanguage": "ar",
            "datePublished": guide.get("reviewed_at", RELEASE_DATE),
            "dateModified": guide.get("reviewed_at", RELEASE_DATE),
            "mainEntityOfPage": canonical,
            "about": guide.get("category_label", "أدلة التعامل والرعاية"),
            "keywords": guide.get("search_intent", []),
            "author": {"@type": "Organization", "name": "منصة روافد"},
            "publisher": {"@type": "Organization", "name": "منصة روافد"},
            "citation": source_schema(guide),
        },
        {
            "@type": "HowTo",
            "@id": canonical + "#howto",
            "name": guide["title"],
            "description": guide["summary"],
            "inLanguage": "ar",
            "url": canonical,
            "step": steps,
        },
        {
            "@type": "BreadcrumbList",
            "@id": canonical + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "أدلة التعامل والرعاية", "item": BASE + "care-guides/"},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def head(guide: dict, canonical: str) -> str:
    title = guide["title"]
    description = guide["summary"]
    keywords = ", ".join(dict.fromkeys([title, *guide.get("search_intent", []), "أدلة الرعاية النفسية", "دعم الأسرة", "مصطلحات علم النفس"]))[:700]
    schema = structured_data(guide, canonical)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | منصة روافد</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keywords)}"><meta name="author" content="منصة روافد"><meta name="publisher" content="منصة روافد"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="bingbot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="theme-color" content="#075f5b"><meta name="color-scheme" content="light"><link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة روافد"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta property="article:section" content="{esc(guide.get('category_label', 'أدلة التعامل والرعاية'))}"><meta property="article:modified_time" content="{esc(guide.get('reviewed_at', RELEASE_DATE))}"><script type="application/ld+json">{schema}</script><style>:root{{--ink:#173f45;--muted:#4b6f73;--pink:#ffe5ef;--turq:#dffaf7;--mint:#e9fff4;--lilac:#eee9ff;--line:#c9e9e5;--danger:#fff0f3}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(145deg,#fff9fc,var(--turq),var(--lilac));color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}a{{color:#086e69}}a:focus-visible{{outline:3px solid #168f88;outline-offset:4px}}.care-v21{{width:min(1060px,92%);margin:auto;padding:28px 0 60px}}.care-v21__hero,.care-v21__section,.care-v21__sources{{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:26px;padding:clamp(20px,4vw,38px);box-shadow:0 18px 48px rgba(45,117,116,.1);margin:18px 0}}.care-v21__hero{{background:linear-gradient(135deg,var(--pink),var(--turq),var(--lilac))}}.care-v21__hero h1{{font-size:clamp(2rem,5vw,3.6rem);line-height:1.3;margin:.25em 0}}.care-v21__hero p{{max-width:82ch;color:var(--muted);font-size:1.08rem}}.care-v21__nav{{display:flex;gap:10px;flex-wrap:wrap}}.care-v21__nav a,.care-v21__button{{display:inline-block;text-decoration:none;padding:10px 16px;border-radius:14px;background:#fff;border:1px solid var(--line);font-weight:900}}.care-v21__audience{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}.care-v21__audience span{{padding:6px 11px;border-radius:999px;background:var(--mint);font-weight:800}}.care-v21__section h2,.care-v21__sources h2{{margin-top:0;color:#7d3658}}.care-v21__section li{{margin:.58rem 0}}.care-v21__section--danger{{background:var(--danger);border-color:#e9a2b7}}.care-v21__emergency{{border-right:6px solid #c7476e;background:#fff0f3;border-radius:20px;padding:20px;margin:18px 0;color:#651f36;font-weight:800}}.care-v21__sources li{{margin:.7rem 0}}.care-v21__small{{color:var(--muted)}}@media(max-width:650px){{.care-v21{{width:min(94%,1060px)}}.care-v21__nav{{display:grid;grid-template-columns:1fr}}.care-v21__nav a{{text-align:center}}}}@media print{{.care-v21__nav{{display:none!important}}body{{background:#fff}}.care-v21__hero,.care-v21__section,.care-v21__sources{{box-shadow:none;break-inside:avoid}}}}</style></head>'''


def guide_page(guide: dict) -> str:
    canonical = BASE + "care-guides/" + guide["slug"] + "/"
    sections: list[str] = []
    for key, label in SECTION_LABELS.items():
        values = guide.get(key)
        if not values:
            continue
        rows = "".join(f"<li>{esc(item)}</li>" for item in values)
        danger = " care-v21__section--danger" if key in {"when_to_seek_help", "warning_signs"} else ""
        sections.append(f'<section class="care-v21__section{danger}"><h2>{esc(label)}</h2><ul>{rows}</ul></section>')
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["publisher"])} — {esc(source["title"])} ({esc(source["year"])})</a></li>'
        for source in guide["sources"]
    )
    audience = "".join(f"<span>{esc(item)}</span>" for item in guide.get("audience", []))
    review_note = "مراجعة تحريرية ومصدرية داخلية؛ لا توجد مراجعة اختصاصية بشرية موثقة ما لم يُذكر خلاف ذلك."
    body = f'''<body><main class="care-v21"><header class="care-v21__hero"><nav class="care-v21__nav" aria-label="التنقل"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}care-guides/">كل الأدلة</a><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BASE_PATH}assessment-lab/">منصة التقييم</a><a href="{BASE_PATH}tips/">النصائح</a></nav><p>{esc(guide.get('category_label', 'دليل عملي غير تشخيصي'))}</p><h1>{esc(guide['title'])}</h1><p>{esc(guide['summary'])}</p><div class="care-v21__audience" aria-label="الفئات المستفيدة">{audience}</div><p class="care-v21__small">آخر مراجعة للمحتوى والمصادر: {esc(guide.get('reviewed_at', RELEASE_DATE))}. {review_note}</p></header>{''.join(sections)}<aside class="care-v21__emergency" role="note"><strong>عند الخطر أو التدهور الحاد:</strong> {esc(guide.get('emergency_note', 'استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة.'))}</aside><section class="care-v21__sources"><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul><p class="care-v21__small">المحتوى للتثقيف والدعم العام، ولا يستبدل التقييم أو العلاج الفردي أو خدمات الطوارئ.</p></section></main></body></html>'''
    return head(guide, canonical) + body


def load_legacy_guides() -> tuple[dict, list[dict]]:
    primary = json.loads(DATA_FILES[0].read_text(encoding="utf-8"))
    guides: list[dict] = []
    for path in DATA_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        guides.extend(payload.get("guides", []))
    if len(guides) != EXPECTED_LEGACY_SOURCE_GUIDES:
        raise SystemExit(f"Expected {EXPECTED_LEGACY_SOURCE_GUIDES} legacy guides, found {len(guides)}")
    return primary, guides


def validate_guide(guide: dict, institutional: bool) -> None:
    required = ("slug", "title", "summary", "sources", "emergency_note", "review_status")
    missing = [key for key in required if not guide.get(key)]
    if missing:
        raise SystemExit(f"Guide {guide.get('slug', '<unknown>')} missing fields: {missing}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", guide["slug"]):
        raise SystemExit(f"Invalid care-guide slug: {guide['slug']}")
    if len(guide["summary"]) < 150:
        raise SystemExit(f"Guide {guide['slug']} summary is too short")
    minimum_sources = 3 if institutional else 2
    if len(guide["sources"]) < minimum_sources:
        raise SystemExit(f"Guide {guide['slug']} needs at least {minimum_sources} sources")
    for source in guide["sources"]:
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit(f"Guide {guide['slug']} contains a non-HTTPS source")
        if institutional and parsed.netloc not in TRUSTED_SOURCE_HOSTS:
            raise SystemExit(f"Guide {guide['slug']} contains an unapproved source host: {parsed.netloc}")
    if institutional:
        if guide.get("editorial_review") != "structural-and-source-review":
            raise SystemExit(f"Guide {guide['slug']} lacks honest review provenance")
        if word_count(guide) < 900 or actionable_count(guide) < 60:
            raise SystemExit(f"Guide {guide['slug']} fails depth contract")
        if len(guide.get("when_to_seek_help", [])) < 8 or len(guide.get("caregiver_plan", [])) < 6:
            raise SystemExit(f"Guide {guide['slug']} fails safety/caregiver contract")
    joined = json.dumps(guide, ensure_ascii=False)
    for prohibited in ("معاقين", "يغني عن الطبيب", "بديل عن العلاج", "نتيجة نهائية", "مضمون 100%"):
        if prohibited in joined:
            raise SystemExit(f"Guide {guide['slug']} contains prohibited wording: {prohibited}")


def extension_urls() -> list[str]:
    path = SITE / "sitemap-care-guides.xml"
    if not path.is_file():
        return []
    found: list[str] = []
    for node in ET.parse(path).getroot().findall("{*}url/{*}loc"):
        url = (node.text or "").strip()
        if not url.startswith(BASE + "care-guides/") or url == BASE + "care-guides/":
            continue
        relative = url.removeprefix(BASE).strip("/")
        if (SITE / relative / "index.html").is_file():
            found.append(url)
    return sorted(set(found))


def write_sitemaps(guides: list[dict]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    core = [BASE + "care-guides/"] + [BASE + "care-guides/" + guide["slug"] + "/" for guide in guides]
    urls = list(dict.fromkeys(core + extension_urls()))
    root = ET.Element("urlset", xmlns=namespace)
    for url in urls:
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = RELEASE_DATE
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = "0.92" if url == BASE + "care-guides/" else "0.82"
    ET.ElementTree(root).write(SITE / "sitemap-care-guides.xml", encoding="utf-8", xml_declaration=True)
    sitemap_index = SITE / "sitemap.xml"
    if sitemap_index.is_file():
        tree = ET.parse(sitemap_index)
        index_root = tree.getroot()
        target = BASE + "sitemap-care-guides.xml"
        existing = {node.text for node in index_root.findall("{*}sitemap/{*}loc") if node.text}
        if target not in existing:
            sitemap = ET.SubElement(index_root, "sitemap")
            ET.SubElement(sitemap, "loc").text = target
        tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)
    return len(urls)


def temporary_index(primary: dict, guides: list[dict]) -> str:
    cards = "".join(f'<article class="care-v21__section"><h2>{esc(guide["title"])}</h2><p>{esc(guide["summary"])}</p><p><a class="care-v21__button" href="{BASE_PATH}care-guides/{esc(guide["slug"])}/">فتح الدليل الكامل</a></p></article>' for guide in guides)
    hub = {"title": primary.get("title", "أدلة التعامل والرعاية"), "summary": "مكتبة عربية مؤسسية من الأدلة العملية الموسعة."}
    return head(hub, BASE + "care-guides/") + f'<body><main class="care-v21"><header class="care-v21__hero"><h1>أدلة التعامل والرعاية النفسية والأسرية</h1><p>مكتبة عملية موسعة منظمة حسب الاحتياج والفئة، مع مصادر مؤسسية وحدود واضحة للسلامة.</p></header>{cards}</main></body></html>'


def main() -> dict:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site output: {SITE}")
    primary, legacy = load_legacy_guides()
    generated = institutional_guides()
    if len(generated) != EXPECTED_INSTITUTIONAL_GUIDES:
        raise SystemExit("Institutional guide catalog count mismatch")
    all_guides = [*legacy, *generated]
    if len(all_guides) != EXPECTED_SOURCE_GUIDES:
        raise SystemExit(f"Expected {EXPECTED_SOURCE_GUIDES} source guides, found {len(all_guides)}")
    slugs = [guide["slug"] for guide in all_guides]
    titles = [guide["title"] for guide in all_guides]
    if len(slugs) != len(set(slugs)) or len(titles) != len(set(titles)):
        raise SystemExit("Duplicate care-guide slugs or titles")
    generated_ids = {id(guide) for guide in generated}
    for guide in all_guides:
        validate_guide(guide, id(guide) in generated_ids)
    blocked = [guide for guide in all_guides if guide.get("review_status") in BLOCKED_REVIEW_STATUSES]
    published = [guide for guide in all_guides if guide not in blocked]
    if len(published) < MINIMUM_PUBLISHED_GUIDES:
        raise SystemExit(f"Published guide minimum failed: {len(published)} < {MINIMUM_PUBLISHED_GUIDES}")
    output = SITE / "care-guides"
    output.mkdir(parents=True, exist_ok=True)
    for guide in blocked:
        shutil.rmtree(output / guide["slug"], ignore_errors=True)
    for guide in published:
        path = output / guide["slug"] / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(guide_page(guide), encoding="utf-8")
    (output / "index.html").write_text(temporary_index(primary, published), encoding="utf-8")
    sitemap_urls = write_sitemaps(published)
    page_count = len(list(output.rglob("index.html")))
    if page_count != sitemap_urls:
        raise SystemExit(f"Care-guide page/sitemap mismatch: pages={page_count}, sitemap={sitemap_urls}")
    blocked_slugs = [guide["slug"] for guide in blocked]
    autism = next(guide for guide in all_guides if guide["slug"] == "autism-family-practical-guide")
    report = {
        "version": 246,
        "publication_gate_version": 246,
        "content_release_version": CONTENT_RELEASE_VERSION,
        "source_guides": len(all_guides),
        "legacy_source_guides": len(legacy),
        "institutional_source_guides": len(generated),
        "published_core_guides": len(published),
        "minimum_published_guides": MINIMUM_PUBLISHED_GUIDES,
        "minimum_published_guides_met": len(published) >= MINIMUM_PUBLISHED_GUIDES,
        "guides": max(0, sitemap_urls - 1),
        "pages": page_count,
        "sitemap_urls": sitemap_urls,
        "extension_guides_preserved": max(0, sitemap_urls - 1 - len(published)),
        "all_have_sources": all(bool(guide.get("sources")) for guide in all_guides),
        "all_have_unique_titles": len(titles) == len(set(titles)),
        "blocked_review_statuses": sorted(BLOCKED_REVIEW_STATUSES),
        "blocked_review_guides": len(blocked),
        "blocked_review_slugs": blocked_slugs,
        "needs_specialist_review_published": False,
        "autism_published": "autism-family-practical-guide" not in {guide["slug"] for guide in published},
        "autism_guide_sections": sum(1 for key in SECTION_LABELS if autism.get(key)),
        "autism_guide_source_count": len(autism["sources"]),
        "autism_review_status": autism.get("review_status"),
        "autism_human_specialist_review_claimed": False,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from enhance_care_guides_v246 import enhance
    enhancement = enhance(SITE)
    print(json.dumps({"publication": report, "enhancement": enhancement}, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
