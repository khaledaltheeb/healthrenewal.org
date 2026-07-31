from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
BASE = "/"
LAB_SCRIPT = f'<script src="{BASE}assets/js/lab-v12.js" defer></script>'
PAGE_SIZE = 48

INDEX_JS = r'''/* v20 encyclopedia paginated search with stable initial render */
(()=>{'use strict';
 const BASE='/';const PAGE_SIZE=48;
 const q=s=>document.querySelector(s);let all=[],filtered=[],page=1,loaded=false;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function normalize(s){return String(s||'').toLowerCase().normalize('NFKD').replace(/[\u064b-\u065f\u0670]/g,'').replace(/أ|إ|آ/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه')}
 function card(x){return `<article class="ency-v13__card"><span class="ency-v13__tag">${esc(x.category)}</span><h2><a href="${esc(x.url)}">${esc(x.ar)}</a></h2><p lang="en" dir="ltr">${esc(x.en)}</p><p class="ency-v14__meta">${esc(x.domain)} · ${esc(x.facet)}</p></article>`}
 function render(){const grid=q('#ency-results'),count=q('#ency-count'),status=q('#ency-status'),pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages);const start=(page-1)*PAGE_SIZE,end=Math.min(filtered.length,start+PAGE_SIZE);const markup=filtered.slice(start,end).map(card).join('')||'<p class="ency-v14__empty">لا توجد نتائج مطابقة. جرّب كلمة أقصر أو أزل أحد المرشحات.</p>';if(grid.innerHTML!==markup)grid.innerHTML=markup;count.textContent=filtered.length.toLocaleString('ar');status.textContent=`عرض ${filtered.length?start+1:0}–${end} من ${filtered.length.toLocaleString('ar')} · الصفحة ${page} من ${pages}`;q('#ency-prev').disabled=page<=1;q('#ency-next').disabled=page>=pages;grid.setAttribute('aria-busy','false')}
 function apply(){if(!loaded)return;const term=normalize(q('#ency-q').value.trim()),domain=q('#ency-domain').value,category=q('#ency-category').value;filtered=all.filter(x=>(!term||normalize(`${x.ar} ${x.en} ${x.category} ${x.facet} ${x.domain}`).includes(term))&&(!domain||x.domain===domain)&&(!category||x.category===category));page=1;q('#ency-results').setAttribute('aria-busy','true');window.requestAnimationFrame(render)}
 async function load(){try{const response=await fetch(`${BASE}api/encyclopedia-v13.json`,{cache:'force-cache'});if(!response.ok)throw new Error(`HTTP ${response.status}`);const data=await response.json();all=Array.isArray(data.items)?data.items:[];filtered=all;loaded=true;const status=q('#ency-status');if(status)status.textContent=`عرض 1–${Math.min(PAGE_SIZE,all.length)} من ${all.length.toLocaleString('ar')} · الصفحة 1 من ${Math.max(1,Math.ceil(all.length/PAGE_SIZE))}`;q('#ency-next').disabled=all.length<=PAGE_SIZE;q('#ency-results').setAttribute('aria-busy','false')}catch(error){q('#ency-results').innerHTML='<p class="ency-v14__empty">تعذر تحميل فهرس البحث الآن. ما زالت الصفحات متاحة من المراكز الموضوعية وخريطة الموقع.</p>';q('#ency-status').textContent='تعذر تحميل البحث';console.error(error)}}
 let timer=0;q('#ency-q').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(apply,180)});q('#ency-domain').addEventListener('change',apply);q('#ency-category').addEventListener('change',apply);q('#ency-prev').addEventListener('click',()=>{if(page>1){page--;render();scrollTo({top:q('#ency-results').offsetTop-120,behavior:'smooth'})}});q('#ency-next').addEventListener('click',()=>{if(page*PAGE_SIZE<filtered.length){page++;render();scrollTo({top:q('#ency-results').offsetTop-120,behavior:'smooth'})}});load();
})();
'''

PERF_CSS = r'''
.ency-v14__status{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin:18px 0;padding:14px 16px;border-radius:18px;background:linear-gradient(135deg,#fff8fc,#effdfb);border:1px solid #f0dce8;color:#344b57}
.ency-v14__pager{display:flex;gap:10px;justify-content:center;align-items:center;margin:24px 0 48px}
.ency-v14__pager button{min-height:46px;padding:10px 22px;border:1px solid #83d8d0;border-radius:999px;background:#fff;color:#185f62;font:inherit;font-weight:800;cursor:pointer}
.ency-v14__pager button:disabled{opacity:.45;cursor:not-allowed}
.ency-v14__empty{grid-column:1/-1;padding:28px;text-align:center;background:#fff;border-radius:20px;border:1px dashed #d8b7ca}
.ency-v14__meta{font-size:.9rem;color:#526770}
#ency-results{min-height:1180px;align-content:start}
#ency-results[aria-busy="true"]{opacity:.82}
#ency-results .ency-v13__card{content-visibility:auto;contain-intrinsic-size:230px}
@media(max-width:900px){#ency-results{min-height:2200px}}
@media(max-width:640px){.ency-v14__status{display:block}.ency-v14__pager{position:sticky;bottom:8px;z-index:8;padding:8px;border-radius:999px;background:rgba(255,255,255,.92);backdrop-filter:blur(10px)}#ency-results{min-height:5200px}}
'''


def remove_lab_script_from_non_lab_pages() -> tuple[int, int]:
    removed = 0
    kept = 0
    lab_roots = ("assessment-lab/", "cognitive-lab/", "assessments/", "cognitive-tests/")
    verification = SITE / "google644f1f7a8b7aaa2b.html"
    for page in SITE.rglob("*.html"):
        if page == verification:
            continue
        rel = page.relative_to(SITE).as_posix()
        text = page.read_text(encoding="utf-8")
        if any(rel.startswith(root) for root in lab_roots):
            kept += text.count(LAB_SCRIPT)
            continue
        new = text.replace(LAB_SCRIPT, "")
        if new != text:
            removed += text.count(LAB_SCRIPT)
            page.write_text(new, encoding="utf-8")
    return removed, kept


def python_card(item: dict) -> str:
    return (
        '<article class="ency-v13__card">'
        f'<span class="ency-v13__tag">{html.escape(str(item.get("category", "")))}</span>'
        f'<h2><a href="{html.escape(str(item.get("url", "")), quote=True)}">{html.escape(str(item.get("ar", "")))}</a></h2>'
        f'<p lang="en" dir="ltr">{html.escape(str(item.get("en", "")))}</p>'
        f'<p class="ency-v14__meta">{html.escape(str(item.get("domain", "")))} · {html.escape(str(item.get("facet", "")))}</p>'
        '</article>'
    )


def build_lightweight_index() -> dict[str, int]:
    data_path = SITE / "api" / "encyclopedia-v13.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if len(items) != 2000:
        raise SystemExit(f"Expected 2000 encyclopedia items, found {len(items)}")
    domains = sorted({str(x.get("domain", "")) for x in items if x.get("domain")})
    categories = sorted({str(x.get("category", "")) for x in items if x.get("category")})
    domain_options = "".join(f'<option value="{html.escape(x, quote=True)}">{html.escape(x)}</option>' for x in domains)
    category_options = "".join(f'<option value="{html.escape(x, quote=True)}">{html.escape(x)}</option>' for x in categories)
    initial_cards = "".join(python_card(item) for item in items[:PAGE_SIZE])
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    path = SITE / "encyclopedia" / "index.html"
    old = path.read_text(encoding="utf-8")
    head_match = re.search(r"<head>(.*?)</head>", old, re.S)
    if not head_match:
        raise SystemExit("Encyclopedia index head not found")
    head = head_match.group(1)
    if "encyclopedia-v14.css" not in head:
        head += f'<link rel="stylesheet" href="{BASE}assets/css/encyclopedia-v14.css">'
    body = f'''<!doctype html><html lang="ar" dir="rtl"><head>{head}</head><body><main class="ency-v13"><header class="ency-v13__hero"><h1>الموسوعة النفسية العربية</h1><p>مئة موضوع أساسي وعشرون زاوية تحريرية لكل موضوع، مع فهرس سريع لا يحمّل آلاف البطاقات دفعة واحدة.</p><p><strong id="ency-count">2000</strong> صفحة مستقلة موجودة في خريطة الموقع والمراكز الموضوعية.</p><div class="ency-v13__search"><label>البحث<input id="ency-q" type="search" inputmode="search" autocomplete="off" placeholder="ابحث بالعربية أو الإنجليزية"></label><label>الموضوع<select id="ency-domain"><option value="">كل الموضوعات</option>{domain_options}</select></label><label>التصنيف<select id="ency-category"><option value="">كل التصنيفات</option>{category_options}</select></label></div></header><section class="ency-v14__status"><span id="ency-status" role="status" aria-live="polite">عرض 1–{PAGE_SIZE} من ٢٠٠٠ · الصفحة 1 من {total_pages}</span><a href="{BASE}hubs/">التصفح عبر 200 مركز موضوعي</a></section><section id="ency-results" class="ency-v13__grid" aria-busy="false">{initial_cards}</section><nav class="ency-v14__pager" aria-label="صفحات نتائج الموسوعة"><button id="ency-prev" type="button" disabled>السابق</button><button id="ency-next" type="button">التالي</button></nav></main><noscript><main class="ency-v13"><p class="ency-v14__empty">البحث التفاعلي يحتاج JavaScript. استخدم <a href="{BASE}hubs/">المراكز الموضوعية</a> لتصفح جميع الموضوعات.</p></main></noscript><script src="{BASE}assets/js/encyclopedia-v14.js" defer></script><script src="{BASE}assets/js/app-v10.js" defer></script></body></html>'''
    path.write_text(body, encoding="utf-8")
    css_dir = SITE / "assets" / "css"
    js_dir = SITE / "assets" / "js"
    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    (css_dir / "encyclopedia-v14.css").write_text(PERF_CSS, encoding="utf-8")
    (js_dir / "encyclopedia-v14.js").write_text(INDEX_JS, encoding="utf-8")
    return {"items": len(items), "domains": len(domains), "categories": len(categories), "initial_cards": PAGE_SIZE}


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Site root not found: {SITE}")
    removed, kept = remove_lab_script_from_non_lab_pages()
    index = build_lightweight_index()
    runtime = (SITE / "assets" / "js" / "lab-v12.js").read_text(encoding="utf-8")
    page = (SITE / "encyclopedia" / "index.html").read_text(encoding="utf-8")
    checks = {
        "mutation_observer_removed": "MutationObserver" not in runtime,
        "computed_style_scan_removed": "getComputedStyle" not in runtime,
        "no_2000_static_cards": page.count("ency-v13__card") == PAGE_SIZE,
        "paginated_runtime_loaded": "encyclopedia-v14.js" in page,
        "lab_runtime_removed_from_index": "lab-v12.js" not in page,
        "page_size_48": "PAGE_SIZE=48" in INDEX_JS,
        "stable_initial_render": page.count("ency-v13__card") == PAGE_SIZE,
    }
    if not all(checks.values()):
        raise SystemExit({"checks": checks})
    report = {"version": 20, "removed_lab_script_tags": removed, "kept_lab_script_tags": kept, **index, **checks}
    (SITE / "api" / "performance-v14.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
