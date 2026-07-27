from __future__ import annotations
import json,re,shutil,xml.etree.ElementTree as ET
from pathlib import Path
from scripts import publish_daily_tools_v24_core as core
from scripts.learning_paths_catalog_v326 import load_catalog,REQUIRED_EXISTING_SLUGS

BASE,PATH=core.BASE,core.PATH
STYLE=r"""
.learning-hero{display:grid;gap:16px}.metrics,.chips,.filters{display:flex;gap:9px;flex-wrap:wrap}
.metric,.chip,.filter-button{display:inline-flex;align-items:center;min-height:38px;padding:6px 12px;border:1px solid var(--mint-line);border-radius:999px;background:#fff;font-weight:800}
.catalog-controls{position:sticky;top:8px;z-index:5}.catalog-controls input{max-width:560px}.filter-button{cursor:pointer;font:inherit;color:var(--ink)}
.filter-button[aria-pressed="true"]{background:var(--brand);color:#fff}.path-card[hidden]{display:none}.path-id,.module-meta{font-size:.88rem;color:var(--brand);font-weight:900}
.breadcrumb ol{display:flex;gap:8px;flex-wrap:wrap;list-style:none;padding:0}.breadcrumb li:not(:last-child)::after{content:"←";margin-right:8px}
.module{border-right:7px solid var(--mint-line)}.module:nth-of-type(2n){border-right-color:var(--rose-line)}.module h3{color:var(--berry)}
.application{background:var(--butter);border:1px solid var(--butter-line);border-radius:16px;padding:14px}
details{border:1px solid var(--lilac-line);border-radius:14px;padding:10px 14px;background:var(--lilac);margin:9px 0}summary{cursor:pointer;font-weight:900}
.empty-state{display:none;font-weight:900}@media(max-width:640px){.catalog-controls{position:static}.metrics,.chips,.filters{display:grid}.filter-button{width:100%}}
"""

def maps(catalog,tools):
    return ({x["id"]:x for x in catalog["categories"]},{x["id"]:x for x in catalog["sources"]},{x["slug"]:x for x in tools})

def source_html(path,sources):
    return "<ul class=\"sources\">"+"".join(f'<li><a rel="noopener noreferrer" href="{core.e(sources[s]["url"])}">{core.e(sources[s]["publisher"])} — {core.e(sources[s]["title"])} ({sources[s]["year"]})</a></li>' for s in path["source_ids"])+"</ul>"

def module_html(m):
    points="".join(f"<li>{core.e(x)}</li>" for x in m["key_points"]);checks="".join(f"<li>{core.e(x)}</li>" for x in m["knowledge_check"])
    return f'<article class="module" data-module="{m["position"]}"><p class="module-meta">الوحدة {m["position"]} · {core.e(m["lens"])}</p><h3>{core.e(m["title"])}</h3><p><strong>الهدف:</strong> {core.e(m["objective"])}</p><p>{core.e(m["explanation"])}</p><h4>نقاط العمل</h4><ul>{points}</ul><div class="application"><h4>تطبيق عملي</h4><p>{core.e(m["application"])}</p></div><details><summary>تحقق من الفهم</summary><ol>{checks}</ol></details></article>'

def schema(path,category,url):
    return {"@context":"https://schema.org","@graph":[
    {"@type":"Course","@id":url+"#course","name":path["title"],"description":path["summary"],"inLanguage":"ar","isAccessibleForFree":True,"educationalLevel":path["level"],"timeRequired":"PT60M","about":category["title"],"syllabusSections":[{"@type":"Syllabus","name":m["title"],"description":m["objective"]} for m in path["modules"]],"provider":{"@type":"Organization","name":"مصطلحات علم النفس"}},
    {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":BASE},{"@type":"ListItem","position":2,"name":"مسارات التعلم","item":BASE+"learning-paths/"},{"@type":"ListItem","position":3,"name":path["title"],"item":url}]},
    {"@type":"FAQPage","mainEntity":[{"@type":"Question","name":x["question"],"acceptedAnswer":{"@type":"Answer","text":x["answer"]}} for x in path["faq"]]}]}

def patch_home(site):
    p=site/"index.html"
    if not p.is_file(): return
    text=p.read_text(encoding="utf-8")
    pattern=re.compile(r'(<article class="card" data-learning-paths-v219><h3>مسارات التعلم القصيرة</h3><p>).*?(</p>)',re.S)
    text,count=pattern.subn(r"\g<1>مئة مسار تعلم مؤسسي موزعة على عشر عائلات معرفية، تضم نتائج تعلم ووحدات وتطبيقات ومراجع وضوابط سلامة.\g<2>",text,1)
    if count!=1: raise SystemExit("Homepage learning-path card was not found")
    p.write_text(text,encoding="utf-8")

def discovery(site,catalog,tools):
    urls=[BASE+"daily-tools/"]+[BASE+"daily-tools/"+x["slug"]+"/" for x in tools]+[BASE+"learning-paths/"]+[BASE+"learning-paths/"+x["slug"]+"/" for x in catalog["paths"]]
    ns="http://www.sitemaps.org/schemas/sitemap/0.9";ET.register_namespace("",ns);root=ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        n=ET.SubElement(root,f"{{{ns}}}url");ET.SubElement(n,f"{{{ns}}}loc").text=url;ET.SubElement(n,f"{{{ns}}}lastmod").text=catalog["reviewed"];ET.SubElement(n,f"{{{ns}}}changefreq").text="monthly"
    ET.ElementTree(root).write(site/"sitemap-tools-paths.xml",encoding="utf-8",xml_declaration=True)
    rp=site/"api/daily-tools-v24.json";report=json.loads(rp.read_text(encoding="utf-8"))
    report.update({"learning_paths_catalog_version":catalog["version"],"tools":len(tools),"paths":len(catalog["paths"]),"path_categories":len(catalog["categories"]),"path_sources":len(catalog["sources"]),"pages":len(urls),"local_only":True})
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

def publish_learning_paths(catalog,site,tools_list,shell,nav):
    categories,sources,tools=maps(catalog,tools_list);paths=catalog["paths"];out=site/"learning-paths"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    filters='<button class="filter-button" type="button" data-filter="all" aria-pressed="true">كل المسارات</button>'+"".join(f'<button class="filter-button" type="button" data-filter="{c["id"]}" aria-pressed="false">{core.e(c["title"])} <span>10</span></button>' for c in catalog["categories"])
    cards="".join(f'<article class="path-card" data-category="{p["category"]}" data-search="{core.e((p["title"]+" "+p["summary"]+" "+categories[p["category"]]["title"]).casefold())}"><p class="path-id">{p["id"]} · {core.e(categories[p["category"]]["title"])}</p><h2>{core.e(p["title"])}</h2><p>{core.e(p["summary"])}</p><div class="chips"><span class="chip">{core.e(p["level"])}</span><span class="chip">{core.e(p["duration"])}</span></div><a class="button" href="{PATH}learning-paths/{p["slug"]}/">فتح المسار الكامل</a></article>' for p in paths)
    index_schema={"@context":"https://schema.org","@type":"CollectionPage","name":catalog["title"],"description":catalog["description"],"inLanguage":"ar","url":BASE+"learning-paths/","mainEntity":{"@type":"ItemList","numberOfItems":100,"itemListElement":[{"@type":"ListItem","position":i,"name":p["title"],"url":BASE+"learning-paths/"+p["slug"]+"/"} for i,p in enumerate(paths,1)]}}
    js=r"""<script>(()=>{const q=document.querySelector('#path-search'),b=[...document.querySelectorAll('[data-filter]')],c=[...document.querySelectorAll('.path-card')],e=document.querySelector('.empty-state');let a='all';function f(){const t=(q.value||'').trim().toLocaleLowerCase('ar');let n=0;c.forEach(x=>{x.hidden=!((a==='all'||x.dataset.category===a)&&(!t||x.dataset.search.includes(t)));if(!x.hidden)n++});e.style.display=n?'none':'block';document.querySelector('#visible-count').textContent=n}b.forEach(x=>x.addEventListener('click',()=>{a=x.dataset.filter;b.forEach(y=>y.setAttribute('aria-pressed',y===x));f()}));q.addEventListener('input',f);f()})();</script>"""
    body=f'<main>{nav()}<header class="learning-hero"><span class="tool-kicker">موسوعة تعلم عربية منظمة</span><h1>100 مسار تعلم للصحة النفسية وذوي الاحتياجات الخاصة</h1><p>{core.e(catalog["description"])}</p><div class="metrics"><span class="metric"><strong>100</strong> مسار</span><span class="metric"><strong>10</strong> عائلات معرفية</span><span class="metric"><strong>500</strong> وحدة تعلم</span><span class="metric"><strong>{len(sources)}</strong> مرجعًا مؤسسيًا</span></div><p>{core.e(catalog["disclaimer"])}</p></header><section class="catalog-controls"><h2>ابحث وصفِّ المسارات</h2><label for="path-search">البحث في العنوان والهدف والتصنيف</label><input id="path-search" type="search" placeholder="مثال: التوحد، النوم، القلق، الدمج"><div class="filters">{filters}</div><p><strong id="visible-count">100</strong> مسار ظاهر</p></section><div class="grid">{cards}</div><p class="empty-state" role="status">لا توجد نتيجة مطابقة.</p><section class="note"><h2>حدود الاستخدام والسلامة</h2><p>{core.e(catalog["disclaimer"])}</p></section>{js}</main>'
    (out/"index.html").write_text(shell("100 مسار تعلم للصحة النفسية وذوي الاحتياجات الخاصة","موسوعة عربية تضم 100 مسار تعلم منظم في الصحة النفسية والأسرة والنمو العصبي والدمج والممارسة المهنية، مع تطبيقات ومراجع وضوابط سلامة.",BASE+"learning-paths/",index_schema,body).replace("</style>",STYLE+"</style>"),encoding="utf-8")
    for p in paths:
        cat=categories[p["category"]];d=out/p["slug"];d.mkdir();url=BASE+"learning-paths/"+p["slug"]+"/"
        outcomes="".join(f"<li>{core.e(x)}</li>" for x in p["outcomes"]);modules="".join(module_html(x) for x in p["modules"]);check="".join(f'<li><label><input type="checkbox"> {core.e(x)}</label></li>' for x in p["checklist"]);faq="".join(f'<details><summary>{core.e(x["question"])}</summary><p>{core.e(x["answer"])}</p></details>' for x in p["faq"])
        related="".join(f'<li><a href="{PATH}learning-paths/{x["slug"]}/">{core.e(x["title"])}</a></li>' for x in [x for x in paths if x["category"]==p["category"] and x["slug"]!=p["slug"]][:3])
        tool_links="".join(f'<li><a href="{PATH}daily-tools/{s}/">{core.e(tools[s]["title"])}</a></li>' for s in p["related_tools"] if s in tools)
        page=f'<main>{nav()}<nav class="breadcrumb" aria-label="مسار التنقل"><ol><li><a href="{PATH}">الرئيسية</a></li><li><a href="{PATH}learning-paths/">مسارات التعلم</a></li><li>{core.e(p["title"])}</li></ol></nav><header><span class="tool-kicker">{p["id"]} · {core.e(cat["title"])}</span><h1>{core.e(p["title"])}</h1><p>{core.e(p["summary"])}</p><div class="chips"><span class="chip">المستوى: {core.e(p["level"])}</span><span class="chip">الفئة: {core.e(p["audience"])}</span><span class="chip">{core.e(p["duration"])}</span></div></header><section><h2>نتائج التعلم</h2><ul>{outcomes}</ul></section><section><h2>خريطة المسار: خمس وحدات</h2></section>{modules}<section><h2>قائمة تطبيق ومراجعة</h2><ul>{check}</ul><p>علامات الاختيار تعمل داخل الصفحة فقط ولا تُرسل بيانات إلى خادم.</p></section><section><h2>أدوات مرتبطة</h2><ul>{tool_links}</ul></section><section><h2>مسارات تالية من العائلة نفسها</h2><ul>{related}</ul></section><section><h2>أسئلة شائعة</h2>{faq}</section><section><h2>المراجع المؤسسية الخاصة بالمسار</h2>{source_html(p,sources)}</section><section class="note"><h2>السلامة وحدود المسار</h2><p>{core.e(p["safety"])}</p><p>{core.e(p["seek_help"])}</p><p>{core.e(catalog["disclaimer"])}</p></section><section><h2>المراجعة والتحرير</h2><p>آخر مراجعة منهجية: <time datetime="{p["reviewed"]}">{p["reviewed"]}</time>. دورة المراجعة: كل {p["review_cycle_months"]} شهرًا.</p></section></main>'
        (d/"index.html").write_text(shell(p["title"],p["summary"],url,schema(p,cat,url),page).replace("</style>",STYLE+"</style>"),encoding="utf-8")
    patch_home(site);discovery(site,catalog,tools_list)

if __name__=="__main__": raise SystemExit("Run through scripts/publish_daily_tools_v24.py")
