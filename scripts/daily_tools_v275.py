from __future__ import annotations

import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "v24" / "daily-tools-learning-paths-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
PATH = "/pterminology-site/"
CONTENT_CONTRACT = 275


def e(value: object) -> str:
    import html
    return html.escape(str(value), quote=True)


def load_catalog() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    templates_path = ROOT / data["template_file"]
    templates = json.loads(templates_path.read_text(encoding="utf-8"))["templates"]
    compact: list[dict[str, Any]] = []
    for relative in data["catalog_files"]:
        payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        compact.extend(payload["tools"])

    by_category: dict[str, list[str]] = defaultdict(list)
    for item in compact:
        by_category[item["category"]].append(item["slug"])

    tools: list[dict[str, Any]] = []
    for item in compact:
        tool = deepcopy(item)
        template = templates[tool["category"]]
        peers = by_category[tool["category"]]
        position = peers.index(tool["slug"])
        tool["when_to_use"] = deepcopy(template["when_to_use"])
        tool["steps"] = [
            f'حدّد هدف الأداة الآن: {tool["intent"].rstrip("。. ")}',
            f'سجّل {tool["save_fields"][0]} و{tool["save_fields"][1]} بوصف موجز وخالٍ من الحكم.',
            f'أكمل {tool["save_fields"][2]} و{tool["save_fields"][3]} مع ذكر السياق أو الوقت عند الحاجة.',
            f'راجع {tool["focus"]} وابحث عن أصغر تعديل آمن يمكن تجربته.',
            "حدّد موعدًا قصيرًا للمراجعة، واحتفظ فقط بالمعلومات الضرورية على جهازك.",
        ]
        tool["review_questions"] = [
            f'ما الجزء الأكثر وضوحًا في {tool["focus"]}؟',
            "ما العامل السياقي أو البيئي الذي ربما أثّر في النتيجة؟",
            "ما الخطوة الأصغر التي تحسن الأمان أو الوظيفة دون مبالغة؟",
        ]
        tool["interpretation"] = deepcopy(template["interpretation"])
        tool["next_steps"] = deepcopy(template["next_steps"])
        tool["avoid"] = deepcopy(template["avoid"])
        tool["safety"] = tool.get("safety") or template["safety"]
        tool["evidence_note"] = template["evidence_note"]
        tool["reviewed_at"] = data["reviewed_at"]
        tool["related_tools"] = [peers[(position - 1) % len(peers)], peers[(position + 1) % len(peers)]]
        tools.append(tool)
    tools.sort(key=lambda item: item["id"])
    data["tools"] = tools
    return data


def list_html(items: Iterable[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{e(item)}</li>" for item in items) + f"</{tag}>"


def source_list(data: dict[str, Any], source_ids: Iterable[str]) -> str:
    sources = {item["id"]: item for item in data["sources"]}
    return "<ul>" + "".join(
        f'<li><a rel="noopener noreferrer" href="{e(sources[source_id]["url"])}">'
        f'{e(sources[source_id]["publisher"])} — {e(sources[source_id]["title"])} ({e(sources[source_id]["year"])})</a><br>'
        f'<small>{e(sources[source_id]["scope"])} — تحقق: {e(sources[source_id]["checked_at"])}</small></li>'
        for source_id in source_ids
    ) + "</ul>"


def _replace_jsonld(text: str, transform) -> str:
    match = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', text, re.S)
    if not match:
        raise RuntimeError("JSON-LD marker is missing")
    payload = transform(json.loads(match.group(2)))
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return text[:match.start(2)] + encoded + text[match.end(2):]


def _index_cards(data: dict[str, Any]) -> str:
    categories = {item["id"]: item for item in data["categories"]}
    return "".join(
        f'<article data-tool-card data-category="{e(tool["category"])}" data-search="{e(" ".join([tool["title"], tool["intent"], categories[tool["category"]]["title"], *tool["audience"]]))}">'
        f'<span class="tool-kicker">أداة {tool["id"]} من {len(data["tools"])}</span>'
        f'<span class="category-pill">{e(categories[tool["category"]]["title"])}</span>'
        f'<h2>{e(tool["title"])}</h2><p>{e(tool["intent"])}</p>'
        f'<p><strong>المدة:</strong> {e(tool["duration"])}</p>'
        f'<p><strong>مناسبة لـ:</strong> {e("، ".join(tool["audience"]))}</p>'
        f'<a class="button" href="{PATH}daily-tools/{e(tool["slug"])}/">فتح الأداة</a></article>'
        for tool in data["tools"]
    )


def _search_block(data: dict[str, Any]) -> str:
    options = "".join(f'<option value="{e(item["id"])}">{e(item["title"])}</option>' for item in data["categories"])
    return f'''<section data-tools-summary><h2>ابحث حسب حاجتك</h2>
<div class="summary-strip"><div><strong>{len(data["tools"])}</strong> أداة</div><div><strong>{len(data["categories"])}</strong> مجالات</div><div><strong>{len(data["sources"])}</strong> مصدرًا مؤسسيًا</div></div>
<div class="filters"><label>البحث في العنوان والغرض والجمهور<input type="search" data-tool-search placeholder="مثال: النوم، الأسرة، المدرسة، الحدود" autocomplete="off"></label><label>المجال<select data-tool-category><option value="">كل المجالات</option>{options}</select></label></div>
<p class="status" data-result-count aria-live="polite"></p></section>'''


SEARCH_SCRIPT = r'''<script data-tools-search-v275>
(() => {
  const search = document.querySelector('[data-tool-search]');
  const category = document.querySelector('[data-tool-category]');
  const cards = [...document.querySelectorAll('[data-tool-card]')];
  const status = document.querySelector('[data-result-count]');
  if (!search || !category || !status) return;
  const normalize = value => String(value || '').toLocaleLowerCase('ar').replace(/\s+/g,' ').trim();
  const apply = () => {
    const q = normalize(search.value); const c = category.value; let count = 0;
    cards.forEach(card => { const visible = (!q || normalize(card.dataset.search).includes(q)) && (!c || card.dataset.category === c); card.hidden = !visible; if (visible) count += 1; });
    status.textContent = `تظهر ${count} أداة من أصل ${cards.length}.`;
  };
  search.addEventListener('input', apply); category.addEventListener('change', apply); apply();
})();
</script>'''


EXTRA_STYLE = r'''
.filters{display:grid;grid-template-columns:2fr 1fr;gap:12px;align-items:end}
.summary-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.summary-strip div{padding:14px;border:2px solid var(--mint-line);border-radius:18px;background:#fff;text-align:center}
.summary-strip strong{display:block;font-size:1.6rem;color:var(--berry)}
.category-pill{display:inline-flex;width:fit-content;padding:4px 11px;border-radius:999px;background:var(--butter);color:#4a315f;border:1px solid var(--butter-line);font-weight:900;font-size:.88rem;margin-inline-start:6px}
[data-tool-card][hidden]{display:none!important}.two-columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:700px){.filters,.two-columns{grid-template-columns:1fr}}
@media print{[data-tools-summary],nav,.button,form button{display:none!important}body{background:#fff}header,section,article{box-shadow:none!important;border:1px solid #777!important;break-inside:avoid}}
'''


def enhance_index(data: dict[str, Any], site: Path) -> None:
    path = site / "daily-tools" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace("أدوات نفسية تفاعلية يومية", "100 أداة نفسية وتنظيمية يومية")
    text = text.replace("أدوات تنظيمية عربية تفاعلية غير تشخيصية للتوتر والنوم والأسرة والفقد والحدود، تعمل محليًا بتصميم مارشملو واضح ومتباين.", data["description"])
    pattern = r'(<header>.*?</header>)(<div class="grid">.*?</div>)(<section><h2>المصادر</h2>)'
    replacement = r"\1" + _search_block(data) + '<div class="grid" data-tool-grid>' + _index_cards(data) + "</div>" + SEARCH_SCRIPT + r"\3"
    text, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Daily-tools index grid marker is missing")

    def transform(payload: dict[str, Any]) -> dict[str, Any]:
        payload.update({"name": "100 أداة نفسية وتنظيمية يومية", "description": data["description"], "dateModified": data["reviewed_at"]})
        payload["hasPart"] = [{"@type": "WebApplication", "position": tool["id"], "name": tool["title"], "description": tool["intent"], "url": BASE + "daily-tools/" + tool["slug"] + "/"} for tool in data["tools"]]
        return payload

    path.write_text(_replace_jsonld(text, transform), encoding="utf-8")


def enhance_tool(data: dict[str, Any], tool: dict[str, Any], site: Path) -> None:
    path = site / "daily-tools" / tool["slug"] / "index.html"
    text = path.read_text(encoding="utf-8")
    category = next(item for item in data["categories"] if item["id"] == tool["category"])
    header_extra = f'<p><span class="category-pill">{e(category["title"])}</span></p><p><strong>مناسبة لـ:</strong> {e("، ".join(tool["audience"]))} — <strong>آخر مراجعة:</strong> {e(tool["reviewed_at"])}</p>'
    intent_marker = f'<p>{e(tool["intent"])}</p>'
    text = text.replace(intent_marker, intent_marker + header_extra, 1)
    rich_steps = f'<section><h2>متى تفيد هذه الأداة؟</h2>{list_html(tool["when_to_use"])}</section><section><h2>خطوات الاستخدام المنهجي</h2>{list_html(tool["steps"], ordered=True)}</section><section><h2>أسئلة المراجعة</h2>{list_html(tool["review_questions"])}</section>'
    text, count = re.subn(r'<section><h2>الخطوات</h2><ol>.*?</ol></section>', rich_steps, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Steps marker is missing: {tool['slug']}")
    after_form = '<div class="two-columns">' + f'<section><h2>كيف تقرأ ما سجلته؟</h2>{list_html(tool["interpretation"])}</section><section><h2>ما الخطوة التالية؟</h2>{list_html(tool["next_steps"])}</section></div><section class="note"><h2>ما يجب تجنبه</h2>{list_html(tool["avoid"])}</section>'
    text = text.replace('<section class="note"><h2>السلامة</h2>', after_form + '<section class="note"><h2>السلامة ومتى تطلب المساعدة</h2>', 1)
    related = "".join(f'<li><a href="{PATH}daily-tools/{e(slug)}/">{e(next(item["title"] for item in data["tools"] if item["slug"] == slug))}</a></li>' for slug in tool["related_tools"])
    evidence = f'<section><h2>الأساس المنهجي وحدوده</h2><p>{e(tool["evidence_note"])}</p><p><strong>تاريخ التحقق والمراجعة:</strong> {e(tool["reviewed_at"])}</p>{source_list(data, tool["source_ids"])}</section><section><h2>أدوات مرتبطة</h2><ul>{related}</ul></section>'
    text, count = re.subn(r'<section><h2>مصادر المنهج</h2>.*?</section>', evidence, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Source marker is missing: {tool['slug']}")

    def transform(payload: dict[str, Any]) -> dict[str, Any]:
        graph = payload.get("@graph", [])
        for item in graph:
            if item.get("@type") == "WebApplication":
                item.update({"dateModified": tool["reviewed_at"], "audience": {"@type": "Audience", "audienceType": "، ".join(tool["audience"])}, "about": category["title"], "citation": [next(source["url"] for source in data["sources"] if source["id"] == source_id) for source_id in tool["source_ids"]], "isAccessibleForFree": True})
            if item.get("@type") == "HowTo":
                item["step"] = [{"@type": "HowToStep", "position": index + 1, "text": step} for index, step in enumerate(tool["steps"])]
        graph.append({"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": tool["interpretation"][index]}} for index, question in enumerate(tool["review_questions"])]})
        payload["@graph"] = graph
        return payload

    path.write_text(_replace_jsonld(text, transform), encoding="utf-8")


def patch_homepage(data: dict[str, Any], site: Path) -> None:
    path = site / "index.html"
    text = path.read_text(encoding="utf-8")
    card = '<article class="card" data-daily-tools-v219><h3>100 أداة نفسية وتنظيمية يومية</h3><p>أدوات عربية محلية للتنظيم والمتابعة والتواصل والأسرة والمدرسة والإتاحة وطلب المساعدة، مع حدود غير تشخيصية ومصادر أصلية.</p><a href="daily-tools/">فتح مركز الأدوات</a></article>'
    if "data-daily-tools-v219" in text:
        text = re.sub(r'<article class="card" data-daily-tools-v219>.*?</article>', card, text, count=1, flags=re.S)
    text = text.replace("ثماني أدوات نفسية تفاعلية", "100 أداة نفسية وتنظيمية").replace("أدوات نفسية تفاعلية يومية", "100 أداة نفسية وتنظيمية يومية")
    path.write_text(text, encoding="utf-8")


def patch_api(data: dict[str, Any], site: Path) -> None:
    report_path = site / "api" / "daily-tools-v24.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update({"version": 24, "catalog_version": data["catalog_version"], "content_contract": data["content_contract"], "tools": len(data["tools"]), "categories": len(data["categories"]), "paths": len(data["paths"]), "pages": len(data["tools"]) + len(data["paths"]) + 2, "sources": len(data["sources"]), "rich_guidance": True, "search_and_filter": True, "reviewed_at": data["reviewed_at"]})
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    report_path.write_text(encoded, encoding="utf-8")
    (site / "api" / "daily-tools-v25.json").write_text(encoded, encoding="utf-8")


def enhance_site(data: dict[str, Any], site: Path) -> None:
    enhance_index(data, site)
    for tool in data["tools"]:
        enhance_tool(data, tool, site)
    patch_homepage(data, site)
    patch_api(data, site)
