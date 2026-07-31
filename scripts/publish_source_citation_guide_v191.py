from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v191" / "source-citation-guide-ar.json"
BASE_URL = "https://healthrenewal.org/"
SITEMAP_NAME = "sitemap-source-citation-guide.xml"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_content() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    required = {
        "slug", "title", "description", "summary", "professional_limits",
        "sections", "checklist", "examples", "internal_links", "sources",
        "reviewed_at", "status", "risk_level",
    }
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing content fields: {sorted(missing)}")
    return data


def render(data: dict) -> str:
    canonical = f'{BASE_URL}/guides/{data["slug"]}/'
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data["title"],
        "description": data["description"],
        "inLanguage": "ar",
        "dateModified": data["reviewed_at"],
        "mainEntityOfPage": canonical,
        "author": {"@type": "Organization", "name": "مصطلحات علم النفس"},
        "publisher": {"@type": "Organization", "name": "مصطلحات علم النفس"},
        "citation": [source["url"] for source in data["sources"]],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "الأدلة", "item": f"{BASE_URL}/guides/"},
            {"@type": "ListItem", "position": 3, "name": data["title"], "item": canonical},
        ],
    }
    sections = "".join(
        f'<section><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )
    checklist = "".join(
        f'<li><label><input type="checkbox"> {esc(item)}</label></li>'
        for item in data["checklist"]
    )
    examples = "".join(
        f'<tr><td>{esc(item["avoid"])}</td><td>{esc(item["prefer"])}</td></tr>'
        for item in data["examples"]
    )
    links = "".join(
        f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>'
        for item in data["internal_links"]
    )
    sources = "".join(
        f'<li><a rel="noopener" href="{esc(item["url"])}">{esc(item["title"])}</a>'
        f' — {esc(item["publisher"])} ({esc(item["year"])})'
        f'<ul>{"".join(f"<li>{esc(claim)}</li>" for claim in item["claims_supported"])}</ul></li>'
        for item in data["sources"]
    )
    schemas = json.dumps([article, breadcrumb], ensure_ascii=False)
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data["title"])} | مصطلحات علم النفس</title>
<meta name="description" content="{esc(data["description"])}"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{esc(data["title"])}"><meta property="og:description" content="{esc(data["description"])}"><meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(data["title"])}"><meta name="twitter:description" content="{esc(data["description"])}">
<script type="application/ld+json">{schemas}</script>
<style>body{{font-family:system-ui;line-height:1.9;margin:0;background:#fbfaf6;color:#19343a}}main{{max-width:980px;margin:auto;padding:28px 18px}}section,.lead,.notice,.checklist,.examples{{background:#fff;border:1px solid #d6e2de;border-radius:16px;padding:18px;margin:16px 0}}.notice{{border-inline-start:6px solid #9a6d12}}a{{color:#075d64;font-weight:700}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ccd8d5;padding:12px;text-align:start;vertical-align:top}}:focus-visible{{outline:3px solid #9a6d12;outline-offset:3px}}@media print{{nav,.no-print{{display:none}}body{{background:#fff}}main{{max-width:none;padding:0}}section,.lead,.notice,.checklist,.examples{{break-inside:avoid;border-color:#888}}}}</style></head>
<body><a class="no-print" href="#content">تجاوز إلى المحتوى</a><main id="content"><nav aria-label="مسار الصفحة"><a href="/">الرئيسية</a> ← <a href="/guides/">الأدلة</a></nav>
<header><h1>{esc(data["title"])}</h1><p class="lead">{esc(data["summary"])}</p><p class="notice"><strong>حدود الاستخدام:</strong> {esc(data["professional_limits"])}</p></header>
{sections}
<section class="checklist"><h2>قائمة تحقق قبل النشر</h2><ol>{checklist}</ol></section>
<section class="examples"><h2>أمثلة تحريرية قبل وبعد</h2><table><thead><tr><th>صياغة تحتاج مراجعة</th><th>بديل أدق</th></tr></thead><tbody>{examples}</tbody></table></section>
<section><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>
<section><h2>المصادر وما تدعمه</h2><p>الحالة التحريرية: مراجعة داخلية. لا توجد دعوى مراجعة اختصاصية خارجية. آخر مراجعة: {esc(data["reviewed_at"])}.</p><ul>{sources}</ul></section>
</main></body></html>'''


def add_contextual_link(path: Path, href: str, label: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if href in text:
        return
    link = f'<p class="source-citation-guide-link"><a href="{href}">{esc(label)}</a></p>'
    text = text.replace("</main>", link + "</main>", 1) if "</main>" in text else text + link
    path.write_text(text, encoding="utf-8")


def publish(site: Path) -> Path:
    data = load_content()
    output = site / "guides" / data["slug"] / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data), encoding="utf-8")
    href = f'/guides/{data["slug"]}/'
    add_contextual_link(site / "encyclopedia" / "index.html", href, "منهج الاستشهاد بالمصادر وتحديث الصفحات")
    add_contextual_link(site / "blog" / "index.html", href, "دليل الاستشهاد والتحديث للمحررين")
    add_contextual_link(site / "trust" / "index.html", href, "دليل الاستشهاد بالمصادر")
    canonical = BASE_URL + href
    sitemap = site / SITEMAP_NAME
    sitemap.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{canonical}</loc><lastmod>{data["reviewed_at"]}</lastmod></url></urlset>\n',
        encoding="utf-8",
    )
    report = site / "api" / "source-citation-guide-v191.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({
        "status": "built-not-published",
        "version": 191,
        "path": href,
        "sitemap": f"/{SITEMAP_NAME}",
        "review": data["status"],
        "risk_level": data["risk_level"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    output = publish(args.site)
    print(json.dumps({"status": "built-not-published", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
