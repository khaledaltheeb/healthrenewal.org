from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
JS_PATH = SITE / "assets/js/encyclopedia-v14.js"
CSS_PATH = SITE / "assets/css/encyclopedia-v14.css"

RUNTIME = r'''/* v31 encyclopedia search: prerender first results, honor shared query URLs, and defer full index until intent */
(()=>{'use strict';
 const BASE='/';const PAGE_SIZE=48;
 const q=s=>document.querySelector(s);let all=[],filtered=[],page=1,loaded=false,loading=null,timer=0;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function normalize(s){return String(s||'').toLowerCase().normalize('NFKD').replace(/[\u064b-\u065f\u0670]/g,'').replace(/أ|إ|آ/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه')}
 function card(x){return `<article class="ency-v13__card"><span class="ency-v13__tag">${esc(x.category)}</span><h2><a href="${esc(x.url)}">${esc(x.ar)}</a></h2><p lang="en" dir="ltr">${esc(x.en)}</p><p class="ency-v14__meta">${esc(x.domain)} · ${esc(x.facet)}</p></article>`}
 function render(){const grid=q('#ency-results'),count=q('#ency-count'),status=q('#ency-status'),pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages);const start=(page-1)*PAGE_SIZE,end=Math.min(filtered.length,start+PAGE_SIZE);const markup=filtered.slice(start,end).map(card).join('')||'<p class="ency-v14__empty">لا توجد نتائج مطابقة. جرّب كلمة أقصر أو أزل أحد المرشحات.</p>';grid.innerHTML=markup;count.textContent=filtered.length.toLocaleString('ar');status.textContent=`عرض ${filtered.length?start+1:0}–${end} من ${filtered.length.toLocaleString('ar')} · الصفحة ${page} من ${pages}`;q('#ency-prev').disabled=page<=1;q('#ency-next').disabled=page>=pages;grid.setAttribute('aria-busy','false')}
 function syncQueryUrl(term){const url=new URL(location.href);if(term)url.searchParams.set('q',term);else url.searchParams.delete('q');history.replaceState(null,'',url)}
 function apply(){if(!loaded)return;const raw=q('#ency-q').value.trim(),term=normalize(raw),domain=q('#ency-domain').value,category=q('#ency-category').value;syncQueryUrl(raw);filtered=all.filter(x=>(!term||normalize(`${x.ar} ${x.en} ${x.category} ${x.facet} ${x.domain}`).includes(term))&&(!domain||x.domain===domain)&&(!category||x.category===category));page=1;q('#ency-results').setAttribute('aria-busy','true');requestAnimationFrame(render)}
 async function ensureLoad(){if(loaded)return all;if(loading)return loading;const status=q('#ency-status');if(status)status.textContent='جارٍ تجهيز البحث الكامل…';loading=fetch(`${BASE}api/encyclopedia-v13.json`,{cache:'force-cache'}).then(response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json()}).then(data=>{all=Array.isArray(data.items)?data.items:[];filtered=all;loaded=true;q('#ency-next').disabled=all.length<=PAGE_SIZE;return all}).catch(error=>{q('#ency-status').textContent='تعذر تحميل البحث الكامل';console.error(error);throw error});return loading}
 function searchFromIntent(){clearTimeout(timer);timer=setTimeout(()=>ensureLoad().then(apply).catch(()=>{}),80)}
 const input=q('#ency-q');const initialQuery=new URLSearchParams(location.search).get('q')||'';
 input.addEventListener('input',searchFromIntent);input.addEventListener('focus',()=>ensureLoad().catch(()=>{}),{once:true});q('#ency-domain').addEventListener('change',()=>ensureLoad().then(apply).catch(()=>{}));q('#ency-category').addEventListener('change',()=>ensureLoad().then(apply).catch(()=>{}));q('#ency-prev').addEventListener('click',()=>ensureLoad().then(()=>{if(page>1){page--;render();scrollTo({top:q('#ency-results').offsetTop-120,behavior:'smooth'})}}));q('#ency-next').addEventListener('click',()=>ensureLoad().then(()=>{if(page*PAGE_SIZE<filtered.length){page++;render();scrollTo({top:q('#ency-results').offsetTop-120,behavior:'smooth'})}}));
 if(initialQuery.trim()){input.value=initialQuery;ensureLoad().then(apply).catch(()=>{})}else{setTimeout(()=>ensureLoad().catch(()=>{}),10000)}
})();
'''


def main() -> None:
    if not JS_PATH.exists() or not CSS_PATH.exists():
        raise SystemExit("Encyclopedia runtime assets missing")
    JS_PATH.write_text(RUNTIME, encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")
    css += "\n#ency-results .ency-v13__card:nth-child(-n+12){content-visibility:visible!important;contain:none!important}\n"
    CSS_PATH.write_text(css, encoding="utf-8")
    report = {
        "version": 31,
        "full_index_deferred_ms": 10000,
        "loads_on_search_intent": True,
        "loads_from_query_parameter": True,
        "shareable_query_url": True,
        "first_twelve_cards_immediately_visible": True,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "encyclopedia-runtime-v20.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
