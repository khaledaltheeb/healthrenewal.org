from __future__ import annotations

import html
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA_FILES = [
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
    ROOT / "content/v18/care-guides-family-anxiety-panic-support-ar.json",
    ROOT / "content/v18/care-guides-family-ocd-support-ar.json",
    ROOT / "content/v18/care-guides-bipolar-family-early-warning-plan-ar.json",
    ROOT / "content/v18/care-guides-trauma-ptsd-family-support-ar.json",
    ROOT / "content/v18/care-guides-eating-disorder-family-support-ar.json",
    ROOT / "content/v18/care-guides-self-harm-family-safety-support-ar.json",
    ROOT / "content/v18/care-guides-suicide-risk-family-safety-plan-ar.json",
    ROOT / "content/v18/care-guides-substance-use-family-recovery-plan-ar.json",
    ROOT / "content/v18/care-guides-perinatal-mental-health-family-plan-ar.json",
    ROOT / "content/v18/care-guides-borderline-emotional-instability-family-plan-ar.json",
    ROOT / "content/v18/care-guides-dementia-behaviour-family-plan-ar.json",
    ROOT / "content/v18/care-guides-chronic-insomnia-family-sleep-plan-ar.json",
]
EXPECTED_SOURCE_GUIDES = 20
CONTENT_RELEASE_VERSION = 244
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
TODAY = date.today().isoformat()
BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}

SECTION_LABELS = {
    "understanding": "فهم الحالة دون وصم",
    "what_the_person_may_feel": "ما الذي قد يشعر به الشخص من الداخل؟",
    "strengths_and_differences": "نقاط القوة والفروق الفردية",
    "communication_plan": "خطة التواصل",
    "sensory_plan": "خطة التنظيم الحسي",
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
    "when_to_seek_help": "متى نطلب مساعدة مهنية؟",
    "caregiver_plan": "خطة مقدم الرعاية",
    "observe": "ما الذي نراقبه؟",
    "conversation_steps": "خطوات الحوار",
    "plan": "خطة عملية مستدامة",
    "warning_signs": "إشارات الاستنزاف أو الخطر",
}

STYLE = """
:root{--ink:#173f45;--muted:#4b6f73;--pink:#ffe5ef;--turq:#dffaf7;--mint:#e9fff4;--lilac:#eee9ff;--line:#c9e9e5;--danger:#fff0f3}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#fff9fc,var(--turq),var(--lilac));color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}a{color:#086e69}a:focus-visible{outline:3px solid #168f88;outline-offset:4px}.care-v21{width:min(1060px,92%);margin:auto;padding:28px 0 60px}.care-v21__hero,.care-v21__section,.care-v21__sources{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:26px;padding:clamp(20px,4vw,38px);box-shadow:0 18px 48px rgba(45,117,116,.1);margin:18px 0}.care-v21__hero{background:linear-gradient(135deg,var(--pink),var(--turq),var(--lilac))}.care-v21__hero h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.3;margin:.25em 0}.care-v21__hero p{max-width:78ch;color:var(--muted);font-size:1.1rem}.care-v21__nav{display:flex;gap:10px;flex-wrap:wrap}.care-v21__nav a,.care-v21__button{display:inline-block;text-decoration:none;padding:10px 16px;border-radius:14px;background:#fff;border:1px solid var(--line);font-weight:900}.care-v21__audience{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.care-v21__audience span{padding:6px 11px;border-radius:999px;background:var(--mint);font-weight:800}.care-v21__section h2,.care-v21__sources h2{margin-top:0;color:#7d3658}.care-v21__section li{margin:.55rem 0}.care-v21__section--danger{background:var(--danger);border-color:#e9a2b7}.care-v21__emergency{border-right:6px solid #c7476e;background:#fff0f3;border-radius:20px;padding:20px;margin:18px 0;color:#651f36;font-weight:800}.care-v21__sources li{margin:.7rem 0}.care-v21__small{color:var(--muted)}
@media(max-width:650px){.care-v21{width:min(94%,1060px)}.care-v21__nav{display:grid;grid-template-columns:1fr}.care-v21__nav a{text-align:center}}
@media print{.care-v21__nav{display:none!important}body{background:#fff}.care-v21__hero,.care-v21__section,.care-v21__sources{box-shadow:none;break-inside:avoid}}
""".strip()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def list_section(title: str, items: list[str], danger: bool = False) -> str:
    css_class = "care-v21__section care-v21__section--danger" if danger else "care-v21__section"
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f'<section class="{css_class}"><h2>{esc(title)}</h2><ul>{rows}</ul></section>'


def schema_for(guide: dict, canonical: str) -> str:
    steps: list[dict] = []
    for key in ("do", "communication_plan", "conversation_steps", "plan", "caregiver_plan", "home_plan", "school_plan"):
        for item in guide.get(key, []):
            steps.append({"@type": "HowToStep", "position": len(steps) + 1, "name": item, "text": item})
    graph = [
        {
            "@type": "Article",
            "headline": guide["title"],
            "description": guide["summary"],
            "inLanguage": "ar",
            "dateModified": guide.get("reviewed_at", TODAY),
            "mainEntityOfPage": canonical,
            "author": {"@type": "Organization", "name": "مصطلحات علم النفس"},
            "publisher": {"@type": "Organization", "name": "مصطلحات علم النفس"},
            "citation": [source["url"] for source in guide["sources"]],
        },
        {"@type": "HowTo", "name": guide["title"], "description": guide["summary"], "inLanguage": "ar", "url": canonical, "step": steps},
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "أدلة التعامل", "item": BASE + "care-guides/"},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def head(title: str, description: str, canonical: str, schema: str) -> str:
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<title>{esc(title)} | مصطلحات علم النفس</title>'
        f'<meta name="description" content="{esc(description)}">'
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
        '<meta name="theme-color" content="#71d8cf"><meta name="color-scheme" content="light">'
        f'<link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}">'
        f'<link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest">'
        f'<link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css">'
        '<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="مصطلحات علم النفس">'
        f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}">'
        f'<meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script><style>{STYLE}</style></head>'
    )


def guide_page(guide: dict) -> str:
    canonical = BASE + "care-guides/" + guide["slug"] + "/"
    sections = [
        list_section(label, guide[key], danger=key in {"when_to_seek_help", "warning_signs"})
        for key, label in SECTION_LABELS.items()
        if guide.get(key)
    ]
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["publisher"])} — {esc(source["title"])} ({esc(source["year"])})</a></li>'
        for source in guide["sources"]
    )
    audience = "".join(f"<span>{esc(item)}</span>" for item in guide.get("audience", []))
    review_line = ""
    if guide.get("reviewed_at"):
        review_line = f'<p class="care-v21__small">آخر مراجعة للمحتوى والمصادر: {esc(guide["reviewed_at"])}. لا توجد مراجعة اختصاصية موثقة لهذا الدليل حتى الآن.</p>'
    emergency = ""
    if guide.get("emergency_note"):
        emergency = f'<aside class="care-v21__emergency" role="note"><strong>عند الخطر أو التدهور الحاد:</strong> {esc(guide["emergency_note"])}</aside>'
    body = (
        f'<body><main class="care-v21"><header class="care-v21__hero"><nav class="care-v21__nav" aria-label="التنقل">'
        f'<a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}care-guides/">كل أدلة التعامل</a>'
        f'<a href="{BASE_PATH}tips/">النصائح</a><a href="{BASE_PATH}assessment-lab/">المقاييس</a></nav>'
        f'<p>دليل عملي غير تشخيصي</p><h1>{esc(guide["title"])}</h1><p>{esc(guide["summary"])}</p>'
        f'<div class="care-v21__audience" aria-label="الفئات المستفيدة">{audience}</div>{review_line}</header>'
        + "".join(sections)
        + emergency
        + f'<section class="care-v21__sources"><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul>'
          '<p class="care-v21__small">هذا الدليل للتثقيف والدعم العام، ولا يستبدل التقييم أو العلاج الفردي. عند وجود خطر مباشر استخدم خدمات الطوارئ المحلية.</p></section></main></body></html>'
    )
    return head(guide["title"], guide["summary"], canonical, schema_for(guide, canonical)) + body


def index_page(data: dict) -> str:
    canonical = BASE + "care-guides/"
    cards = "".join(
        f'<article class="care-v21__section"><h2>{esc(guide["title"])}</h2><p>{esc(guide["summary"])}</p>'
        f'<p><a class="care-v21__button" href="{BASE_PATH}care-guides/{esc(guide["slug"])}/">فتح الدليل الكامل</a></p></article>'
        for guide in data["guides"]
    )
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": data["title"],
            "description": "أدلة عربية عملية موثقة تساعد الأسرة والأصدقاء ومقدمي الرعاية على التعامل الآمن والداعم.",
            "url": canonical,
            "inLanguage": "ar",
            "hasPart": [{"@type": "Article", "name": guide["title"], "url": canonical + guide["slug"] + "/"} for guide in data["guides"]],
        },
        ensure_ascii=False,
    )
    description = "أدلة عربية عملية موثقة لدعم الأسرة والأصدقاء ومقدمي الرعاية، مع حدود واضحة للمراجعة المهنية والسلامة."
    body = (
        f'<body><main class="care-v21"><header class="care-v21__hero"><nav class="care-v21__nav" aria-label="التنقل">'
        f'<a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a>'
        f'<a href="{BASE_PATH}tips/">النصائح</a><a href="{BASE_PATH}sectors/family/">الأسرة</a></nav>'
        f'<p>معرفة عملية للأسرة ومقدمي الرعاية</p><h1>{esc(data["title"])}</h1>'
        '<p>مسارات واضحة لما يمكن فعله، وما ينبغي تجنبه، ومتى يلزم طلب مساعدة مهنية، بلغة خالية من الوصم وبالاستناد إلى مصادر مؤسسية.</p>'
        f'</header>{cards}</main></body></html>'
    )
    return head(data["title"], description, canonical, schema) + body


def extension_urls() -> list[str]:
    sitemap_path = SITE / "sitemap-care-guides.xml"
    if not sitemap_path.is_file():
        return []
    root = ET.parse(sitemap_path).getroot()
    found: list[str] = []
    for node in root.findall("{*}url/{*}loc"):
        url = (node.text or "").strip()
        if not url.startswith(BASE + "care-guides/") or url == BASE + "care-guides/":
            continue
        relative = url.removeprefix(BASE).strip("/")
        if (SITE / relative / "index.html").is_file():
            found.append(url)
    return sorted(set(found))


def update_sitemaps(guides: list[dict]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    core_urls = [BASE + "care-guides/"] + [BASE + "care-guides/" + guide["slug"] + "/" for guide in guides]
    urls = list(dict.fromkeys(core_urls + extension_urls()))
    urlset = ET.Element("urlset", xmlns=namespace)
    for url in urls:
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = TODAY
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = "0.90" if url == BASE + "care-guides/" else "0.80"
    ET.ElementTree(urlset).write(SITE / "sitemap-care-guides.xml", encoding="utf-8", xml_declaration=True)
    index = SITE / "sitemap.xml"
    tree = ET.parse(index)
    root = tree.getroot()
    existing = {node.text for node in root.findall("{*}sitemap/{*}loc") if node.text}
    target = BASE + "sitemap-care-guides.xml"
    if target not in existing:
        sitemap = ET.SubElement(root, "sitemap")
        ET.SubElement(sitemap, "loc").text = target
    tree.write(index, encoding="utf-8", xml_declaration=True)
    return len(urls)


def validate_guide(guide: dict) -> None:
    if not guide.get("title") or not guide.get("slug") or not guide.get("summary"):
        raise SystemExit("Every care guide must have a title, slug and summary")
    if len(guide.get("sources", [])) < 2:
        raise SystemExit(f'Guide {guide.get("slug")} must have at least two sources')
    for source in guide["sources"]:
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit(f'Guide {guide.get("slug")} contains a non-HTTPS source')


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Missing site output: {SITE}")
    primary = json.loads(DATA_FILES[0].read_text(encoding="utf-8"))
    all_guides = list(primary.get("guides", []))
    for path in DATA_FILES[1:]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        all_guides.extend(payload.get("guides", []))
    if len(all_guides) != EXPECTED_SOURCE_GUIDES:
        raise SystemExit(f"Expected {EXPECTED_SOURCE_GUIDES} validated source guides, found {len(all_guides)}")
    slugs = [guide["slug"] for guide in all_guides]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate care-guide slugs")
    for guide in all_guides:
        validate_guide(guide)

    blocked_guides = [guide for guide in all_guides if guide.get("review_status") in BLOCKED_REVIEW_STATUSES]
    guides = [guide for guide in all_guides if guide not in blocked_guides]
    blocked_slugs = [guide["slug"] for guide in blocked_guides]
    primary["guides"] = guides

    output = SITE / "care-guides"
    output.mkdir(parents=True, exist_ok=True)
    for guide in blocked_guides:
        shutil.rmtree(output / guide["slug"], ignore_errors=True)
    (output / "index.html").write_text(index_page(primary), encoding="utf-8")
    for guide in guides:
        page = output / guide["slug"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(guide_page(guide), encoding="utf-8")

    sitemap_url_count = update_sitemaps(guides)
    published_guide_count = max(0, sitemap_url_count - 1)
    page_count = len(list(output.rglob("index.html")))
    if page_count != sitemap_url_count:
        raise SystemExit(f"Care-guide page/sitemap mismatch after source safety filtering: pages={page_count}, sitemap_urls={sitemap_url_count}")
    blocked_routes = [BASE + "care-guides/" + slug + "/" for slug in blocked_slugs]
    sitemap_text = (SITE / "sitemap-care-guides.xml").read_text(encoding="utf-8")
    remaining = [route for route, slug in zip(blocked_routes, blocked_slugs) if route in sitemap_text or (output / slug / "index.html").exists()]
    if remaining:
        raise SystemExit(f"Blocked specialist-review guides remain after publication filtering: {remaining}")

    autism = next(guide for guide in all_guides if guide["slug"] == "autism-family-practical-guide")
    report = {
        "version": 194,
        "publication_gate_version": 194,
        "content_release_version": CONTENT_RELEASE_VERSION,
        "source_guides": len(all_guides),
        "guides": published_guide_count,
        "core_guides": len(all_guides),
        "published_core_guides": len(guides),
        "pages": page_count,
        "sitemap_urls": sitemap_url_count,
        "extension_guides_preserved": max(0, published_guide_count - len(guides)),
        "all_have_sources": True,
        "all_have_unique_titles": len({guide["title"] for guide in all_guides}) == len(all_guides),
        "blocked_review_statuses": sorted(BLOCKED_REVIEW_STATUSES),
        "blocked_review_guides": len(blocked_guides),
        "blocked_review_slugs": blocked_slugs,
        "needs_specialist_review_published": False,
        "autism_published": "autism-family-practical-guide" not in blocked_slugs,
        "autism_guide_sections": sum(1 for key in SECTION_LABELS if autism.get(key)),
        "autism_guide_source_count": len(autism["sources"]),
        "autism_review_status": autism.get("review_status"),
        "autism_human_specialist_review_claimed": False,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
    from enhance_care_guides_v234 import enhance

    enhance(SITE)
