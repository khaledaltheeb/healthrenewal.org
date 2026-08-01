#!/usr/bin/env python3
"""Publish a long-form Arabic special-education family-tools hub and 15 printable guides."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median
from family_tools_v1_common import ROOT_ROUTE, esc, visible_words
from family_tools_v1_render import hub, page

DEFAULT_CONTENT = Path("content/family-guide-special-education-tools-v1")

ROOT_COPY_REPLACEMENTS = {
    "دليل الأسرة للأشخاص ذوي الاحتياجات الخاصة | 64 دليلًا للرعاية والدعم":
        "دليل الأسرة للأشخاص ذوي الاحتياجات الخاصة | 64 دليل حالة و15 أداة للرعاية والدعم",
    "دليل الأسرة للرعاية والدعم — 64 حالة":
        "دليل الأسرة للرعاية والدعم — 64 دليل حالة و15 أداة",
    "مرجع عربي منهجي للأسرة يضم 64 دليلًا عمليًا للحالات النمائية والعصبية والحركية والحسية والوراثية":
        "مرجع عربي منهجي للأسرة يضم 64 دليل حالة و15 أداة عملية تغطي الاحتياجات النمائية والعصبية والحركية والحسية والوراثية",
    "مرجع عربي منهجي للأسرة يضم 64 دليل حالة و15 أداة عملية للحالات النمائية والعصبية والحركية والحسية والوراثية":
        "مرجع عربي منهجي للأسرة يضم 64 دليل حالة و15 أداة عملية تغطي الاحتياجات النمائية والعصبية والحركية والحسية والوراثية",
    "مسار عملي من فهم الحالة إلى التقييم والخطة والمتابعة والاستقلال عبر 64 دليلًا أسريًا.":
        "مسار عملي من فهم الحالة إلى التقييم والخطة والمتابعة والاستقلال عبر 64 دليل حالة و15 أداة أسرية.",
    "يضم الإصدار الحالي 64 دليلًا مترابطًا مع مسارات التقييم والخدمات.":
        "يضم الإصدار الحالي مجموعة مترابطة من 64 دليل حالة و15 أداة، مع مسارات للتقييم والخدمات.",
    "يضم الإصدار الحالي 64 دليل حالة و15 أداة مترابطة مع مسارات التقييم والخدمات.":
        "يضم الإصدار الحالي مجموعة مترابطة من 64 دليل حالة و15 أداة، مع مسارات للتقييم والخدمات.",
    "64 دليلًا منشورًا وقابلًا للتوسع":
        "مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة",
    "64 دليل حالة و15 أداة منشورًا وقابلًا للتوسع":
        "مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة",
    "64 دليل حالة و15 أداة منشورة وقابلة للتوسع":
        "مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة",
    "64 دليل حالة و15 أداة منشورة وقابلًا للتوسع":
        "مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة",
    "15 أداة عمليًا": "15 أداة عملية",
    "15 أداة أسريًا": "15 أداة أسرية",
    "15 أداة مترابطًا": "15 أداة مترابطة",
    "15 أداة منشورًا": "15 أداة منشورة",
}

BAD_ROOT_COPY = (
    "15 أداة عمليًا",
    "15 أداة أسريًا",
    "15 أداة مترابطًا",
    "15 أداة منشورًا",
    "منشورة وقابلًا للتوسع",
    "64 دليل حالة و15 أداة منشورة وقابلة للتوسع",
)

def load_payload(content: Path) -> dict:
    if content.is_dir():
        payload = json.loads((content / "manifest.json").read_text(encoding="utf-8"))
        tools = []
        for path in sorted(content.glob("tools-*.json")):
            tools.extend(json.loads(path.read_text(encoding="utf-8")))
        payload["tools"] = tools
        return payload
    return json.loads(content.read_text(encoding="utf-8"))

def replace_root_tools(root_html: Path, tools: list[dict]) -> None:
    source = root_html.read_text(encoding="utf-8")
    featured = tools[:6]
    cards = "".join(f'<article class="tool-card"><h3>{esc(t["title"])}</h3><p>{esc(t["summary"])}</p><a class="button" href="tools/{esc(t["slug"])}/">فتح الأداة</a></article>' for t in featured)
    block = f'''<section class="section" id="tools"><div class="wrap"><p class="kicker">15 أداة موسعة وقابلة للطباعة</p><h2>مركز أدوات التربية الخاصة ودعم الأسرة</h2><p>حوّل الملاحظات إلى خط أساس وأهداف وتكييفات وخطط دعم وقرارات متابعة. كل صفحة تشرح المنهج والخطوات والمخاطر ثم تقدم نموذجًا عمليًا.</p><div class="grid">{cards}</div><div class="toolbar"><a class="button" href="tools/">عرض الأدوات الخمس عشرة</a></div></div></section>'''
    pattern = re.compile(r'<section\s+class="section"\s+id="tools">.*?</section>', re.I | re.S)
    if not pattern.search(source):
        raise SystemExit("family-guide root tools section not found")
    updated = pattern.sub(block, source, count=1)
    for old, new in ROOT_COPY_REPLACEMENTS.items():
        updated = updated.replace(old, new)
    bad = [phrase for phrase in BAD_ROOT_COPY if phrase in updated]
    if bad:
        raise SystemExit({"invalid_arabic_parent_copy": bad})
    required = (
        "دليل الأسرة للرعاية والدعم — 64 دليل حالة و15 أداة",
        "مجموعة مترابطة من 64 دليل حالة و15 أداة",
        "مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة",
    )
    missing = [phrase for phrase in required if phrase not in updated]
    if missing:
        raise SystemExit({"missing_polished_parent_copy": missing})
    root_html.write_text(updated, encoding="utf-8")


def publish(site: Path, content: Path) -> dict:
    site = site.resolve(); content = content.resolve()
    payload = load_payload(content)
    tools = payload.get("tools", []); sources = payload.get("sources", {})
    if len(tools) != 15:
        raise SystemExit({"expected_tools": 15, "actual": len(tools)})
    slugs = [t["slug"] for t in tools]
    if len(set(slugs)) != len(slugs):
        raise SystemExit("duplicate tool slugs")
    missing_sources = sorted({s for t in tools for s in t["sources"] if s not in sources})
    if missing_sources:
        raise SystemExit({"missing_sources": missing_sources})
    target = site / "family-guide" / "tools"; target.mkdir(parents=True, exist_ok=True)
    word_counts = {}
    for tool in tools:
        output = page(tool, sources, tools)
        words = visible_words(output)
        if words < 1200:
            raise SystemExit({"thin_tool": tool["slug"], "visible_words": words})
        destination = target / tool["slug"] / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
        word_counts[tool["slug"]] = words
    hub_html = hub(payload)
    if visible_words(hub_html) < 500:
        raise SystemExit({"thin_hub": visible_words(hub_html)})
    (target / "index.html").write_text(hub_html, encoding="utf-8")
    root_html = site / "family-guide" / "index.html"
    if not root_html.is_file():
        raise SystemExit(f"missing family guide root: {root_html}")
    replace_root_tools(root_html, tools)
    hub_source = (target / "index.html").read_text(encoding="utf-8")
    root_source = root_html.read_text(encoding="utf-8")
    missing_cards = [slug for slug in slugs if f'href="{slug}/"' not in hub_source]
    if missing_cards or 'href="tools/"' not in root_source:
        raise SystemExit({"missing_cards": missing_cards, "parent_link": 'href="tools/"' in root_source})
    report = {
      "schemaVersion":1,"version":payload["version"],"status":"passed","reviewStatus":payload["reviewStatus"],
      "reviewedAt":payload["reviewedAt"],"nextReviewDue":payload["nextReviewDue"],"tool_count":len(tools),
      "generated_pages":len(tools)+1,"minimum_page_words":min(word_counts.values()),"median_page_words":int(median(word_counts.values())),
      "maximum_page_words":max(word_counts.values()),"hub_words":visible_words(hub_html),"categories":dict(sorted(Counter(t["category"] for t in tools).items())),
      "source_count":len(sources),"slugs":slugs,"word_counts":word_counts,"parent_card_linked":True,"all_tool_cards_static":True,
      "content_source":str(content.relative_to(Path.cwd())) if content.is_relative_to(Path.cwd()) else str(content)
    }
    api = site / "api"; api.mkdir(parents=True, exist_ok=True)
    (api / "family-guide-special-education-tools-v1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default=".", type=Path)
    parser.add_argument("--content", default=DEFAULT_CONTENT, type=Path)
    args = parser.parse_args()
    publish(args.site, args.content)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
