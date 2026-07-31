from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "content" / "v24" / "daily-tools-learning-paths-ar.json"
CATALOG_DIR = ROOT / "content" / "v24" / "daily-tools-v100"
SOURCES_DATA = ROOT / "content" / "v24" / "daily-tools-sources-v100.json"
CATALOG_CONTRACT = 100

EXT_STYLE = r"""
.controls{position:sticky;top:8px;z-index:3}.search-wrap{display:grid;grid-template-columns:minmax(220px,2fr) minmax(180px,1fr);gap:12px}.chips,.meta-row,.actions{display:flex;gap:10px;flex-wrap:wrap}.meta{display:inline-flex;width:fit-content;padding:4px 11px;border-radius:999px;background:var(--mint);border:1px solid var(--mint-line);font-weight:900;font-size:.88rem}.result-count{color:var(--brand);font-weight:900}.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.field{padding:12px;border:1px solid var(--mint-line);border-radius:15px;background:#fff}.range-output{display:inline-block;min-width:2.2rem;text-align:center;font-weight:900;color:var(--berry)}input[type=range]{padding:0}.step-list{list-style:none;padding:0}.step-list li{padding:12px;margin:8px 0;border:1px solid var(--mint-line);border-radius:14px;background:#fff}.step-list label{display:flex;gap:10px;align-items:flex-start}.step-list input{width:1.25rem;min-height:1.25rem;accent-color:var(--brand)}progress{width:100%;height:18px;accent-color:var(--brand)}[hidden]{display:none!important}@media(max-width:680px){.search-wrap{grid-template-columns:1fr}.controls{position:static}}@media print{nav,.controls,.actions{display:none!important}}
"""


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def norm(value: str) -> str:
    return re.sub(r"[\W_]+", " ", str(value), flags=re.UNICODE).strip().casefold()


def load_data() -> dict[str, Any]:
    data = json.loads(BASE_DATA.read_text(encoding="utf-8"))
    bundles = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CATALOG_DIR.glob("*.json"))]
    if not bundles:
        return data
    data["version"] = CATALOG_CONTRACT
    data["catalog_contract"] = CATALOG_CONTRACT
    data["categories"] = []
    data["tools"] = []
    data["paths"] = []
    for bundle in bundles:
        data["categories"].append({
            "id": bundle["id"], "name": bundle["name"], "description": bundle["description"],
            "audience": bundle["audience"], "source_ids": bundle["source_ids"], "tool_count": len(bundle["tools"]),
        })
        for raw in bundle["tools"]:
            tool = dict(raw)
            tool.setdefault("category_id", bundle["id"])
            tool.setdefault("category", bundle["name"])
            tool.setdefault("audience", bundle["audience"])
            tool.setdefault("safety", bundle["safety"])
            tool.setdefault("source_ids", bundle["source_ids"])
            tool.setdefault("tags", [bundle["name"], *bundle["audience"][:3]])
            data["tools"].append(tool)
        data["paths"].append(bundle["path"])
    data["sources"] = json.loads(SOURCES_DATA.read_text(encoding="utf-8"))["sources"]
    validate_catalog(data)
    return data


def validate_catalog(data: dict[str, Any]) -> None:
    tools, categories, paths = data["tools"], data.get("categories", []), data["paths"]
    if len(tools) < CATALOG_CONTRACT or len(categories) < 10 or len(paths) < 10:
        raise SystemExit("Daily tools v100 catalog is incomplete")
    slugs = [item["slug"] for item in tools + paths]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate daily-tools slug")
    titles = [norm(item["title"]) for item in tools + paths]
    if len(titles) != len(set(titles)):
        raise SystemExit("Duplicate daily-tools title")
    category_ids = {item["id"] for item in categories}
    source_ids = {item["id"] for item in data["sources"]}
    tool_slugs = {item["slug"] for item in tools}
    for tool in tools:
        required = ("title", "intent", "category_id", "category", "audience", "duration", "steps", "save_fields", "safety", "source_ids")
        if any(not tool.get(key) for key in required) or len(tool["steps"]) < 4 or len(tool["save_fields"]) < 3:
            raise SystemExit(f"Incomplete daily tool: {tool.get('slug')}")
        if tool["category_id"] not in category_ids or not set(tool["source_ids"]) <= source_ids:
            raise SystemExit(f"Invalid references in tool: {tool['slug']}")
    for path in paths:
        if len(path["days"]) < 5 or not set(path["related_tools"]) <= tool_slugs:
            raise SystemExit(f"Invalid learning path: {path['slug']}")


def field_kind(label: str) -> str:
    value = norm(label)
    if any(token in value for token in ("شدة", "مستوى", "طاقة", "جودة", "قدرة", "استعداد")):
        return "range"
    if "تاريخ" in value:
        return "date"
    if value.startswith("وقت ") or value.startswith("موعد "):
        return "time"
    if any(token in value for token in ("ملاحظ", "وصف", "ما ", "خطة", "رسالة", "جملة", "أفكار", "علامات", "خطوات", "أسباب")):
        return "textarea"
    return "text"


def render_field(field: str) -> str:
    escaped, kind = e(field), field_kind(field)
    field_id = "f-" + e(norm(field).replace(" ", "-"))
    if kind == "range":
        return f'<div class="field"><label for="{field_id}">{escaped} <output class="range-output">5</output></label><input id="{field_id}" type="range" min="0" max="10" value="5" data-field="{escaped}" oninput="this.previousElementSibling.querySelector(\'output\').value=this.value"></div>'
    if kind == "textarea":
        return f'<div class="field"><label>{escaped}<textarea data-field="{escaped}" maxlength="1200"></textarea></label></div>'
    return f'<div class="field"><label>{escaped}<input type="{kind}" data-field="{escaped}" maxlength="300"></label></div>'


def save_form(tool: dict) -> str:
    fields = "".join(render_field(field) for field in tool["save_fields"])
    return f'''<section><h2>سجل شخصي على هذا الجهاز</h2><p>لا تُرسل البيانات إلى خادم. احفظ أقل قدر ممكن وتجنب كتابة الأسماء الكاملة وأرقام الهوية والمعلومات الحساسة.</p><form data-tool="{e(tool['slug'])}"><div class="form-grid">{fields}</div><div class="actions"><button type="button" class="button" onclick="saveTool(this.form)">حفظ محلي</button><button type="button" class="button" onclick="downloadTool(this.form)">تصدير JSON</button><button type="button" class="button" onclick="window.print()">طباعة</button><button type="button" class="button" onclick="clearTool(this.form)">مسح</button></div><p aria-live="polite" class="status"></p></form></section><script>function key(f){{return 'pt-v100-'+f.dataset.tool}}function fields(f){{return [...f.querySelectorAll('[data-field]')]}}function snapshot(f){{let v={{}};fields(f).forEach(x=>v[x.dataset.field]=x.value);return {{tool:f.dataset.tool,savedAt:new Date().toISOString(),values:v}}}}function saveTool(f){{try{{localStorage.setItem(key(f),JSON.stringify(snapshot(f)));f.querySelector('.status').textContent='تم الحفظ على هذا الجهاز.'}}catch(e){{f.querySelector('.status').textContent='تعذر الحفظ محليًا.'}}}}function clearTool(f){{localStorage.removeItem(key(f));f.reset();f.querySelectorAll('output').forEach(o=>o.value='5');f.querySelector('.status').textContent='تم المسح.'}}function downloadTool(f){{let b=new Blob([JSON.stringify(snapshot(f),null,2)],{{type:'application/json;charset=utf-8'}}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=f.dataset.tool+'-record.json';a.click();URL.revokeObjectURL(u)}}document.querySelectorAll('form[data-tool]').forEach(f=>{{try{{let p=JSON.parse(localStorage.getItem(key(f))||'{{}}'),v=p.values||p;fields(f).forEach(x=>{{if(Object.prototype.hasOwnProperty.call(v,x.dataset.field))x.value=v[x.dataset.field]}});f.querySelectorAll('input[type=range]').forEach(x=>x.previousElementSibling.querySelector('output').value=x.value)}}catch(e){{}}}})</script>'''


def prepare(core: Any) -> None:
    if EXT_STYLE not in core.STYLE:
        core.STYLE += EXT_STYLE
    core.save_form = save_form


def source_list(data: dict, ids: list[str]) -> str:
    allowed = set(ids)
    selected = [item for item in data["sources"] if item["id"] in allowed]
    return "<ul>" + "".join(f'<li><a rel="noopener noreferrer" href="{e(item["url"])}">{e(item["publisher"])} — {e(item["title"])} ({e(item["year"])})</a></li>' for item in selected) + "</ul>"


def index_script() -> str:
    return r"""<script>const cards=[...document.querySelectorAll('[data-tool-card]')],q=document.querySelector('[data-tool-search]'),s=document.querySelector('[data-category-select]'),c=document.querySelector('[data-result-count]');function n(v){return(v||'').toLocaleLowerCase('ar').replace(/[إأآ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه').trim()}function filterTools(){let x=n(q.value),k=s.value,z=0;cards.forEach(a=>{a.hidden=!((!x||n(a.dataset.search).includes(x))&&(!k||a.dataset.category===k));if(!a.hidden)z++});c.textContent=`${z} أداة ظاهرة من ${cards.length}`}q.addEventListener('input',filterTools);s.addEventListener('change',filterTools);document.querySelectorAll('[data-category-button]').forEach(b=>b.addEventListener('click',()=>{s.value=b.dataset.categoryButton;filterTools();document.querySelector('#tools-grid').scrollIntoView({behavior:'smooth'})}));filterTools()</script>"""


def enhance_index(data: dict, site: Path) -> None:
    path = site / "daily-tools/index.html"
    text = path.read_text(encoding="utf-8")
    cards = "".join(
        f'<article data-tool-card data-category="{e(tool["category_id"])}" data-search="{e(" ".join([tool["title"],tool["intent"],tool["category"],*tool["audience"]]))}"><span class="tool-kicker">{e(tool["category"])}</span><h2>{e(tool["title"])}</h2><p>{e(tool["intent"])}</p><div class="meta-row"><span class="meta">{e(tool["duration"])}</span><span class="meta">{e("، ".join(tool["audience"][:2]))}</span></div><a class="button" href="/daily-tools/{e(tool["slug"])}/">فتح الأداة</a></article>'
        for tool in data["tools"]
    )
    options = "".join(f'<option value="{e(item["id"])}">{e(item["name"])} ({item["tool_count"]})</option>' for item in data["categories"])
    category_cards = "".join(f'<article><span class="tool-kicker">{item["tool_count"]} أدوات</span><h3>{e(item["name"])}</h3><p>{e(item["description"])}</p><button type="button" class="button" data-category-button="{e(item["id"])}">عرض المجال</button></article>' for item in data["categories"])
    controls = f'<section><h2>المجالات</h2><div class="grid">{category_cards}</div></section><section class="controls"><h2>ابحث عن الأداة المناسبة</h2><div class="search-wrap"><label>بحث<input type="search" data-tool-search placeholder="مثال: نوم، حدود، طفل، ضغط"></label><label>المجال<select data-category-select><option value="">كل المجالات</option>{options}</select></label></div><p class="result-count" data-result-count aria-live="polite"></p></section><div class="grid" id="tools-grid">{cards}</div>'
    text, count = re.subn(r'<div class="grid">.*?</div>(?=<section><h2>المصادر</h2>)', controls, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("Daily-tools index grid marker changed")
    text = re.sub(r'<h1>أدوات نفسية تفاعلية يومية</h1>', f'<h1>{len(data["tools"])} أداة نفسية وتربوية يومية</h1>', text, count=1)
    text = text.replace("تصميم مارشملو متباين", "مكتبة عملية مبنية على مصادر مؤسسية", 1)
    text = text.replace("</main>", index_script() + "</main>", 1)
    path.write_text(text, encoding="utf-8")


def enhance_tool_pages(data: dict, site: Path) -> None:
    by_category: dict[str, list[dict]] = {}
    for tool in data["tools"]:
        by_category.setdefault(tool["category_id"], []).append(tool)
    for tool in data["tools"]:
        path = site / "daily-tools" / tool["slug"] / "index.html"
        text = path.read_text(encoding="utf-8")
        meta = f'<div class="meta-row"><span class="meta">المجال: {e(tool["category"])}</span><span class="meta">الفئة: {e("، ".join(tool["audience"]))}</span></div>'
        marker = f'<p><strong>المدة:</strong> {e(tool["duration"])}</p>'
        if marker in text:
            text = text.replace(marker, marker + meta, 1)
        step_match = re.search(r'<section><h2>الخطوات</h2><ol>(.*?)</ol></section>', text, re.S)
        if step_match:
            items = re.findall(r'<li>(.*?)</li>', step_match.group(1), re.S)
            rendered = "".join(f'<li><label><input type="checkbox" data-step-check><span><strong>الخطوة {i+1}:</strong> {item}</span></label></li>' for i, item in enumerate(items))
            replacement = f'<section><h2>خطوات الاستخدام</h2><progress data-step-progress value="0" max="{len(items)}"></progress><p class="status" data-step-status aria-live="polite">أُنجز 0 من {len(items)}</p><ol class="step-list">{rendered}</ol></section>'
            text = text[:step_match.start()] + replacement + text[step_match.end():]
        related = [item for item in by_category[tool["category_id"]] if item["slug"] != tool["slug"]][:4]
        related_html = "<section><h2>أدوات مرتبطة</h2><ul>" + "".join(f'<li><a href="/daily-tools/{e(item["slug"])}/">{e(item["title"])}</a></li>' for item in related) + "</ul></section>"
        sources_html = f'<section><h2>مصادر المنهج الخاصة بهذه الأداة</h2>{source_list(data, tool["source_ids"])}</section>'
        text, count = re.subn(r'<section><h2>مصادر المنهج</h2>.*?</section>', related_html + sources_html, text, count=1, flags=re.S)
        if count != 1:
            raise SystemExit(f"Source marker changed for {tool['slug']}")
        runtime = "<script>function updateStepProgress(){let a=[...document.querySelectorAll('[data-step-check]')],d=a.filter(x=>x.checked).length,p=document.querySelector('[data-step-progress]');if(p){p.value=d;document.querySelector('[data-step-status]').textContent=`أُنجز ${d} من ${a.length}`}}document.querySelectorAll('[data-step-check]').forEach(x=>x.addEventListener('change',updateStepProgress));updateStepProgress()</script>"
        text = text.replace("</main>", runtime + "</main>", 1)
        path.write_text(text, encoding="utf-8")


def enhance_homepage(data: dict, site: Path) -> None:
    path = site / "index.html"
    text = path.read_text(encoding="utf-8")
    tools_card = f'<article class="card" data-daily-tools-v219><h3>الأدوات النفسية التفاعلية</h3><p>{len(data["tools"])} أداة عربية عملية موزعة على {len(data["categories"])} مجالات، تعمل محليًا دون تشخيص أو إرسال البيانات إلى خادم.</p><a href="daily-tools/">فتح الأدوات التفاعلية</a></article>'
    paths_card = f'<article class="card" data-learning-paths-v219><h3>مسارات التعلم القصيرة</h3><p>{len(data["paths"])} مسارات مترابطة تحول المعرفة إلى خطة أيام وأدوات عملية قابلة للمراجعة.</p><a href="learning-paths/">فتح مسارات التعلم</a></article>'
    text = re.sub(r'<article class="card" data-daily-tools-v219>.*?</article>', tools_card, text, count=1, flags=re.S)
    text = re.sub(r'<article class="card" data-learning-paths-v219>.*?</article>', paths_card, text, count=1, flags=re.S)
    path.write_text(text, encoding="utf-8")


def rewrite_report(data: dict, site: Path) -> None:
    path = site / "api/daily-tools-v24.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report.update({"version": CATALOG_CONTRACT, "catalog_contract": CATALOG_CONTRACT, "tools": len(data["tools"]), "categories": len(data["categories"]), "paths": len(data["paths"]), "pages": len(data["tools"]) + len(data["paths"]) + 2, "search_and_filters": True, "per_tool_sources": True})
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def enhance(data: dict, site: Path | str) -> None:
    target = Path(site).resolve()
    enhance_index(data, target)
    enhance_tool_pages(data, target)
    enhance_homepage(data, target)
    rewrite_report(data, target)
