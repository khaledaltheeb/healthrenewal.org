from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v186" / "inclusive-disability-language-ar.json"
BASE_URL = "https://healthrenewal.org"
SITEMAP_NAME = "sitemap-inclusive-disability-language.xml"


def load_content() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    required = {"slug", "title", "description", "principles", "replace_examples", "context_checklist", "contexts", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing content fields: {sorted(missing)}")
    return data


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def cards(items: list[dict]) -> str:
    return "".join(
        f'<article class="card"><h2>{esc(item["title"])}</h2><p>{esc(item["body"])}</p></article>'
        for item in items
    )


def render(data: dict) -> str:
    canonical = f'{BASE_URL}/special-needs/{data["slug"]}/'
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data["title"],
        "description": data["description"],
        "inLanguage": "ar",
        "dateModified": data["reviewed_at"],
        "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "مصطلحات علم النفس"},
        "citation": [source["url"] for source in data["sources"]],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات", "item": f"{BASE_URL}/special-needs/"},
            {"@type": "ListItem", "position": 3, "name": data["title"], "item": canonical},
        ],
    }
    replacements = "".join(
        f'<tr><td>{esc(item["avoid"])}</td><td>{esc(item["prefer"])}</td></tr>'
        for item in data["replace_examples"]
    )
    checklist = "".join(f'<li><label><input type="checkbox"> {esc(item)}</label></li>' for item in data["context_checklist"])
    links = "".join(f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>' for item in data["internal_links"])
    sources = "".join(f'<li><a rel="noopener" href="{esc(item["url"])}">{esc(item["name"])}</a> — {esc(item["publisher"])}</li>' for item in data["sources"])
    schemas = json.dumps([article_schema, breadcrumb], ensure_ascii=False)
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data["title"])} | مصطلحات علم النفس</title><meta name="description" content="{esc(data["description"])}"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{esc(data["title"])}"><meta property="og:description" content="{esc(data["description"])}"><meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(data["title"])}"><meta name="twitter:description" content="{esc(data["description"])}">
<script type="application/ld+json">{schemas}</script>
<style>body{{font-family:system-ui;line-height:1.9;margin:auto;max-width:980px;padding:24px;color:#17222b}}main{{display:block}}.lead,.notice{{background:#f3f7f6;border-inline-start:5px solid #16766f;padding:16px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}}.card{{border:1px solid #d8e2df;border-radius:14px;padding:16px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #cfd8d5;padding:12px;text-align:start;vertical-align:top}}a{{color:#075e59}}@media print{{nav,.no-print{{display:none}}body{{max-width:none;padding:0}}}}</style></head>
<body><nav aria-label="مسار الصفحة"><a href="/">الرئيسية</a> ← <a href="/special-needs/">ذوو الاحتياجات</a></nav><main>
<h1>{esc(data["title"])}</h1><p class="lead">{esc(data["description"])}</p><p class="notice"><strong>حدود الاستخدام:</strong> {esc(data["professional_limits"])}</p>
<section><h2>ستة مبادئ قبل الكتابة أو الحديث</h2><div class="grid">{cards(data["principles"])}</div></section>
<section><h2>صياغات تحتاج مراجعة</h2><div style="overflow-x:auto"><table><thead><tr><th>تجنب الصياغة العامة</th><th>صياغة أدق بحسب السياق والتفضيل</th></tr></thead><tbody>{replacements}</tbody></table></div></section>
<section><h2>قائمة تحقق قبل النشر</h2><ol>{checklist}</ol></section>
<section><h2>التطبيق بحسب السياق</h2><div class="grid">{cards(data["contexts"])}</div></section>
<section><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>
<section><h2>المصادر وحدود المراجعة</h2><p>الحالة التحريرية: مراجعة داخلية، وتاريخ المراجعة {esc(data["reviewed_at"])}. لا توجد دعوى مراجعة اختصاصية خارجية.</p><ul>{sources}</ul></section>
</main></body></html>'''


def add_contextual_link(path: Path, href: str, label: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if href in text:
        return
    link = f'<p class="inclusive-language-link"><a href="{href}">{esc(label)}</a></p>'
    marker = "</main>"
    text = text.replace(marker, link + marker, 1) if marker in text else text + link
    path.write_text(text, encoding="utf-8")


def publish(site: Path) -> Path:
    data = load_content()
    output = site / "special-needs" / data["slug"] / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data), encoding="utf-8")
    href = f'/special-needs/{data["slug"]}/'
    canonical = f"{BASE_URL}{href}"
    sitemap = site / SITEMAP_NAME
    sitemap.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{canonical}</loc></url></urlset>\n',
        encoding="utf-8",
    )
    for relative, label in [
        ("special-needs/index.html", "دليل اللغة الدامجة عند الحديث عن الإعاقة"),
        ("audiences/family/index.html", "لغة محترمة ودقيقة داخل الأسرة"),
        ("audiences/teacher/index.html", "لغة دامجة للمعلم والمرشد"),
    ]:
        add_contextual_link(site / relative, href, label)
    report = site / "api" / "inclusive-disability-language-v186.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "status": "built-not-published",
                "version": 186,
                "path": href,
                "sitemap": f"/{SITEMAP_NAME}",
                "review": data["status"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    output = publish(args.site)
    print(json.dumps({"status": "built-not-published", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
