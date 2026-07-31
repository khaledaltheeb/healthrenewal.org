#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v192" / "platform-institutional-foundation-ar.json"
SOURCE = ROOT / "magazine"
BASE = "https://healthrenewal.org"
LEGACY_BASE = "https://khaledaltheeb.github.io/pterminology-site"
URL = BASE + "/magazine/"
CONTRACT = 315
MIN_ARTICLES = 70
TARGET_ARTICLES = 100
FEED_LIMIT = 20
EDITORIAL_UPDATED = "2026-07-27"
ROBOTS_META = '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
ROBOTS_PATTERN = re.compile(r'<meta\s+[^>]*name=["\']robots["\'][^>]*>', re.I)
CANONICAL_PATTERN = re.compile(
    r'<link\b(?=[^>]*\brel=["\']canonical["\'])(?=[^>]*\bhref=["\'][^"\']+["\'])[^>]*>',
    re.I,
)
ARTICLE_DATE_PATTERN = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', re.I)
SOURCE_LINK_PATTERN = re.compile(
    r'href="https://(?:doi\.org/|pubmed\.ncbi\.nlm\.nih\.gov/|etheses\.whiterose\.ac\.uk/|research-repository\.uwa\.edu\.au/)',
    re.I,
)
SOURCE_HEADING_PATTERN = re.compile(
    r'<h2>(?:المصدر الأصلي|السجل الأصلي|السجل الجامعي|السجل الجامعي الأصلي)</h2>', re.I
)
LIMITATION_HEADING_PATTERN = re.compile(r'<h2>[^<]*(?:حدود|قيود|الحذر)[^<]*</h2>', re.I)
KNOWN_MARKERS = {
    "peer-led-adolescent-mental-health-2025.html": ("7,060", "لم يجد التحليل التلوي آثارًا دالة", "ست دراسات من أصل سبع"),
    "adhd-school-social-skills-meta-analysis-2026.html": ("10.1177/10870547251364578", "40905635", "0.09"),
    "intensive-community-care-adolescents-2026.html": ("10.1016/j.jaac.2026.01.006", "41580120", "16,546"),
    "neurodivergent-university-mental-health-interventions-2026.html": ("10.1038/s44184-026-00196-4", "41741588", "37 دراسة"),
    "thesis-autism-heterogeneity-research-2025.html": ("38156", "51 ورقة", "حتى 1 مارس 2028"),
    "thesis-autistic-camouflaging-mental-health-2025.html": ("10.26182/pez7-d531", "دراسة مقطعية", "دراسة طولية"),
    "thesis-sensory-processing-adhd-autism-2026.html": ("38725", "3 دراسات تجريبية", "حتى 6 مايو 2027"),
    "autism-social-functioning-meta-analysis-2026.html": ("10.1038/s41562-026-02457-w", "2,622 دراسة", "−0.744"),
    "autism-ssri-children-meta-analysis-2026.html": ("10.1177/11795565261442820", "606 مشاركين", "GRADE"),
    "adhd-screen-time-meta-analysis-2026.html": ("10.1080/24694193.2026.2640837", "235,283", "يقين منخفض"),
    "adhd-technology-interventions-meta-analysis-2026.html": ("10.1080/01942638.2026.2689070", "0.24", "I² = 68.3%"),
    "adhd-physical-fitness-meta-analysis-2026.html": ("10.1016/j.arcped.2026.105583", "1,814", "−0.46"),
    "autism-sleep-disorders-prevalence-meta-analysis-2026.html": ("10.1186/s12888-026-08191-x", "60.0%", "I² = 98.8%"),
    "adhd-baduanjin-response-inhibition-rct-2026.html": ("10.1016/j.ridd.2026.105277", "41936141", "90 طفلًا"),
    "autism-structured-interactive-play-screening-cohort-2026.html": ("10.1186/s12888-026-08274-9", "42464217", "0.915"),
    "adolescent-depression-one-step-back-rct-2026.html": ("10.1016/j.eclinm.2026.103971", "42232686", "d=0.61"),
    "latinx-adolescent-suicidal-behavior-cbt-rct-2026.html": ("10.1080/15374416.2026.2687880", "42413031", "RR=0.50"),
    "adhd-personalized-neurofeedback-sham-rct-2026.html": ("10.1111/jcpp.70188", "42324882", "80.7%"),
    "autism-lets-play-caregiver-mediated-rct-2026.html": ("10.1007/s10803-026-07396-z", "42405995", "لم تظهر فروق دالة"),
    "autism-parent-reflective-functioning-rct-2026.html": ("10.1002/aur.70301", "42394366", "249 والدًا ووالدة"),
    "cerebral-palsy-participate-cp-leisure-rct-2026.html": ("10.1542/peds.2025-075162", "42425531", "2.75"),
    "down-syndrome-dual-task-exergaming-cognition-rct-2026.html": ("10.1016/j.psychsport.2026.103190", "42309334", "η²=0.31"),
    "adhd-dexamphetamine-methylphenidate-randomized-2026.html": ("10.1111/jpc.70487", "42415397", "−1.44"),
}


def article_date(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = ARTICLE_DATE_PATTERN.search(text)
    if match:
        return match.group(1)
    year_match = re.search(r"-(20\d{2})\.html$", path.name)
    if not year_match:
        raise SystemExit(f"Magazine article lacks a year suffix: {path.name}")
    return f"{year_match.group(1)}-01-01"


def article_files() -> list[Path]:
    pages = sorted(
        (path for path in SOURCE.glob("*-20*.html") if path.name != "index.html"),
        key=lambda path: (article_date(path), path.name),
        reverse=True,
    )
    if len(pages) < MIN_ARTICLES:
        raise SystemExit(f"Magazine requires at least {MIN_ARTICLES} research pages, found {len(pages)}")
    return pages


def load_methodology() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("status") != "internally-reviewed" or data.get("risk_level") != "low":
        raise SystemExit("Magazine methodology must remain internally reviewed and low risk")
    return data


def ensure_robots_meta(text: str, filename: str) -> tuple[str, bool]:
    matches = ROBOTS_PATTERN.findall(text)
    if len(matches) > 1:
        raise SystemExit(f"Magazine page contains duplicate robots metadata: {filename}")
    if matches:
        return text, False
    updated, count = re.subn(r"</head\s*>", ROBOTS_META + "</head>", text, count=1, flags=re.I)
    if count != 1:
        raise SystemExit(f"Magazine page lacks a closing head element: {filename}")
    return updated, True


def normalize_article_canonical(text: str, filename: str) -> tuple[str, bool]:
    matches = CANONICAL_PATTERN.findall(text)
    if len(matches) != 1:
        raise SystemExit(
            f"Magazine article must contain exactly one canonical link: {filename} ({len(matches)})"
        )
    expected = f'<link rel="canonical" href="{URL}{filename}">'
    if matches[0] == expected:
        return text, False
    return CANONICAL_PATTERN.sub(expected, text, count=1), True


def plain_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def first_match(text: str, pattern: str, fallback: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    return plain_text(match.group(1)) if match else fallback


def article_record(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {
        "filename": path.name,
        "date": article_date(path),
        "title": first_match(text, r"<h1[^>]*>(.*?)</h1>", path.stem.replace("-", " ")),
        "tag": first_match(text, r'<p\s+class=["\']eyebrow["\'][^>]*>(.*?)</p>', "قراءة علمية حديثة"),
        "description": first_match(
            text,
            r'<p\s+class=["\']lead["\'][^>]*>(.*?)</p>',
            first_match(
                text,
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                "قراءة عربية نقدية للدراسة الأصلية.",
            ),
        ),
    }


def render_index(pages: list[Path]) -> str:
    records = [article_record(path) for path in pages]
    thesis_count = sum(item["filename"].startswith("thesis-") for item in records)
    peer_count = len(records) - thesis_count
    remaining = max(0, TARGET_ARTICLES - len(records))
    scholarly = [
        {"@type": "ScholarlyArticle", "url": URL + item["filename"], "datePublished": item["date"]}
        for item in records
    ]
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "المجلة والأبحاث",
        "url": URL,
        "inLanguage": "ar",
        "dateModified": EDITORIAL_UPDATED,
        "description": "ملخصات عربية تحليلية للأبحاث المحكمة والرسائل الجامعية الحديثة في الصحة النفسية وعلم النفس.",
        "numberOfItems": len(records),
        "hasPart": scholarly,
    }
    cards = "\n".join(
        '<article class="card"><span class="tag">{tag}</span><h2><a href="{filename}">{title}</a></h2>'
        '<p>{description}</p><a class="source" href="{filename}">قراءة التحليل العربي</a></article>'.format(
            tag=html.escape(item["tag"]),
            filename=html.escape(item["filename"], quote=True),
            title=html.escape(item["title"]),
            description=html.escape(item["description"]),
        )
        for item in records
    )
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>المجلة والأبحاث | أحدث الدراسات والرسائل العلمية بالعربية</title>
<meta name="description" content="{len(records)} قراءة عربية منهجية للأبحاث المحكمة والرسائل الجامعية في الصحة النفسية وعلم النفس والأشخاص ذوي الاحتياجات الخاصة، مع المصادر الأصلية والمنهج والنتائج وحدود الدليل.">
{ROBOTS_META}
<link rel="canonical" href="{URL}">
<link rel="alternate" type="application/rss+xml" title="خلاصة المجلة والأبحاث" href="{URL}feed.xml">
<link rel="stylesheet" href="research.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>
</head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<header><div class="wrap header-inner"><a class="brand" href="../">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav aria-label="التنقل الرئيسي"><a href="../">الرئيسية</a><a href="../encyclopedia/">الموسوعة</a><a href="../special-needs/">ذوو الاحتياجات الخاصة</a><a href="./" aria-current="page">المجلة والأبحاث</a></nav></div></header>
<main id="main">
<section class="hero"><div class="wrap"><p class="eyebrow">مرصد عربي للأدلة العلمية</p><h1>المجلة والأبحاث</h1><p class="lead">ملخصات عربية نقدية للأوراق المحكمة والرسائل الجامعية الحديثة، تشمل تصميم الدراسة والعينة والنتائج والقيود والدلالة العملية والمصدر الأصلي.</p><div class="notice"><strong>حالة القسم:</strong> {len(records)} قراءة علمية مستقلة: {peer_count} ورقة أو مراجعة محكمة و{thesis_count} رسائل جامعية. الهدف المرحلي 100 قراءة؛ المتبقي {remaining}. تتم الإضافة على دفعات بعد فحص المصدر الأصلي.</div><div class="filters" aria-label="التصنيفات"><span class="chip">أبحاث 2026</span><span class="chip">دراسات أصلية</span><span class="chip">تحليلات تلوية وشبكية</span><span class="chip">تجارب عشوائية</span><span class="chip">دراسات أتراب</span><span class="chip">نتائج محايدة وسلبية</span><span class="chip">رسائل جامعية</span><span class="chip">الصحة النفسية</span><span class="chip">النمو والتأهيل</span></div><p><a class="source" href="feed.xml">الاشتراك في خلاصة RSS</a></p></div></section>
<section class="wrap grid" aria-label="أحدث القراءات البحثية">
{cards}
</section>
</main>
<footer><div class="wrap"><strong>منهج التحرير:</strong> لا تُنقل الخلاصات الصحفية بوصفها دليلًا؛ كل صفحة تربط بالمصدر الأصلي وتعرض المنهج والنتائج والحدود، وتشمل النتائج المحايدة أو غير الدالة عندما تكون مهمة.</div></footer>
</body>
</html>
'''


def rss_date(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return format_datetime(parsed, usegmt=True)


def render_feed(pages: list[Path]) -> str:
    records = [article_record(path) for path in pages[:FEED_LIMIT]]
    items = "\n".join(
        """    <item>\n      <title>{title}</title>\n      <link>{url}</link>\n      <guid isPermaLink=\"true\">{url}</guid>\n      <pubDate>{pub_date}</pubDate>\n      <description>{description}</description>\n    </item>""".format(
            title=html.escape(item["title"]),
            url=html.escape(URL + item["filename"], quote=True),
            pub_date=rss_date(item["date"]),
            description=html.escape(item["description"]),
        )
        for item in records
    )
    latest = rss_date(records[0]["date"] if records else EDITORIAL_UPDATED)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>المجلة والأبحاث | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
    <link>{URL}</link>
    <description>قراءات عربية نقدية للدراسات الأصلية والمراجعات المنهجية والرسائل الجامعية في الصحة النفسية وذوي الاحتياجات الخاصة.</description>
    <language>ar</language>
    <atom:link href="{URL}feed.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{latest}</lastBuildDate>
    <ttl>60</ttl>
{items}
  </channel>
</rss>
'''


def validate_source_tree(pages: list[Path]) -> dict[str, str]:
    for name in ("index.html", "research.css"):
        if not (SOURCE / name).is_file():
            raise SystemExit(f"Missing magazine source file: {name}")
    template = (SOURCE / "index.html").read_text(encoding="utf-8")
    for marker in ('<html lang="ar" dir="rtl">', '<h1>المجلة والأبحاث</h1>', 'research.css'):
        if marker not in template:
            raise SystemExit(f"Magazine source template contract failed: {marker}")
    rendered = render_index(pages)
    expected_count = len(pages)
    if rendered.count('class="card"') != expected_count:
        raise SystemExit("Generated magazine index card count failed")
    if f'"numberOfItems":{expected_count}' not in rendered:
        raise SystemExit("Generated magazine JSON-LD count failed")
    feed = render_feed(pages)
    if feed.count("<item>") != min(FEED_LIMIT, expected_count):
        raise SystemExit("Generated magazine RSS count failed")
    ET.fromstring(feed)
    hashes: dict[str, str] = {}
    for path in pages:
        filename = path.name
        text = path.read_text(encoding="utf-8")
        normalized, _ = normalize_article_canonical(text, filename)
        required = (
            '<html lang="ar" dir="rtl">',
            '<meta name="description"',
            f'<link rel="canonical" href="{URL}{filename}">',
            '<link rel="stylesheet" href="research.css">',
            '<h1>',
        )
        absent = [marker for marker in required if marker not in normalized]
        absent.extend(marker for marker in KNOWN_MARKERS.get(filename, ()) if marker not in text)
        if absent:
            raise SystemExit(f"Research article contract failed for {filename}: {absent}")
        if not SOURCE_HEADING_PATTERN.search(text):
            raise SystemExit(f"Research article lacks an approved original-source heading: {filename}")
        if not LIMITATION_HEADING_PATTERN.search(text):
            raise SystemExit(f"Research article lacks a limitations or caution section: {filename}")
        if len(re.findall(r"<h1\b", text, flags=re.I)) != 1:
            raise SystemExit(f"Research article must contain exactly one H1: {filename}")
        if not SOURCE_LINK_PATTERN.search(text):
            raise SystemExit(f"Research article lacks an approved original-source link: {filename}")
        if any(term in text for term in ("يشخّص", "علاج مضمون", "نتائج مؤكدة للجميع")):
            raise SystemExit(f"Unsupported clinical claim in {filename}")
        if rendered.count(f'href="{filename}"') < 2:
            raise SystemExit(f"Generated magazine index must expose article twice: {filename}")
        if URL + filename not in rendered:
            raise SystemExit(f"Generated magazine JSON-LD does not include article: {filename}")
        normalized, _ = ensure_robots_meta(normalized, filename)
        hashes[filename] = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return hashes


def publish_files(site: Path, pages: list[Path]) -> dict[str, object]:
    target = site / "magazine"
    target.mkdir(parents=True, exist_ok=True)
    (target / "index.html").write_text(render_index(pages), encoding="utf-8")
    (target / "feed.xml").write_text(render_feed(pages), encoding="utf-8")
    shutil.copy2(SOURCE / "research.css", target / "research.css")
    robots_added: list[str] = []
    canonicals_normalized: list[str] = []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        text, canonical_changed = normalize_article_canonical(text, path.name)
        text, robots_changed = ensure_robots_meta(text, path.name)
        (target / path.name).write_text(text, encoding="utf-8")
        if canonical_changed:
            canonicals_normalized.append(path.name)
        if robots_changed:
            robots_added.append(path.name)
    return {
        "index_robots_added": False,
        "article_robots_added": robots_added,
        "robots_normalized_pages": len(robots_added),
        "article_canonicals_normalized": canonicals_normalized,
        "canonical_normalized_pages": len(canonicals_normalized),
        "canonical_base": BASE,
        "legacy_canonical_base": LEGACY_BASE,
        "rss_items": min(FEED_LIMIT, len(pages)),
    }


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, reviewed_at: str, pages: list[Path]) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urls = [URL, *(URL + path.name for path in pages)]
    child = site / "sitemap-magazine.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    for target_url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = target_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = reviewed_at
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "weekly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)
    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    main = tree.getroot()
    mode = local_name(main.tag)
    changed = False
    if mode == "urlset":
        existing = {(node.text or "").strip() for node in main.findall("{*}url/{*}loc")}
        for target_url in urls:
            if target_url not in existing:
                item = ET.SubElement(main, qualify(main, "url"))
                ET.SubElement(item, qualify(main, "loc")).text = target_url
                existing.add(target_url)
                changed = True
    elif mode == "sitemapindex":
        child_url = BASE + "/sitemap-magazine.xml"
        existing = {(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            item = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(item, qualify(main, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": mode, "main_changed": changed, "child_urls": len(urls)}


def publish(site: Path) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    data = load_methodology()
    pages = article_files()
    hashes = validate_source_tree(pages)
    robots = publish_files(site, pages)
    sitemap = write_sitemaps(site, data["reviewed_at"], pages)
    report = {
        "version": CONTRACT,
        "page": "magazine/index.html",
        "url": URL,
        "methodology_published": True,
        "research_summaries_published": len(pages),
        "target_research_summaries": TARGET_ARTICLES,
        "remaining_to_target": max(0, TARGET_ARTICLES - len(pages)),
        "continuous_publication_policy": True,
        "editorial_updated_at": EDITORIAL_UPDATED,
        "articles": [path.name for path in pages],
        "article_dates": {path.name: article_date(path) for path in pages},
        "source_sha256": hashes,
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "unwired_research_pages": 0,
        "source_heading_contract": "article-or-official-repository",
        "limitations_contract": "limitations-or-cautions-required",
        "robots_contract": "exactly-one-index-follow-meta-per-published-page",
        "canonical_contract": "single-healthrenewal-custom-domain-canonical-per-published-page",
        "index_contract": "generated-from-discovered-articles-sorted-by-datePublished",
        "rss_contract": "latest-twenty-sorted-by-datePublished",
        "robots": robots,
        "sitemap": sitemap,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "magazine-v201.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish(Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve())
