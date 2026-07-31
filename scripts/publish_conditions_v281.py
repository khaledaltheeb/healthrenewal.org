#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, html, json, re, zlib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"content"/"v281"/"conditions-50-ar.json.zlib.b64"
BASE="https://khaledaltheeb.github.io/pterminology-site/"
SECTION="capabilities"
INDEX_ROUTE="capabilities/expanded"
SITEMAP="sitemap-capabilities-v281.xml"
BRIDGE_START="<!-- capabilities-v281:start -->"
BRIDGE_END="<!-- capabilities-v281:end -->"
NS="http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("",NS)

def e(value): return html.escape(str(value),quote=True)
def words(text): return len(re.findall(r"[\u0600-\u06ffA-Za-z0-9]+",text))
def load():
    encoded=DATA.read_text(encoding="ascii").strip()
    data=json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))
    assert data["version"]==281 and len(data["conditions"])==50
    return data

def list_html(items):
    return "<ul>"+"".join(f"<li>{e(x)}</li>" for x in items)+"</ul>"

def layout(title,description,canonical,body,schema):
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{e(canonical)}"><link rel="alternate" hreflang="ar" href="{e(canonical)}">
<link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}"><meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/pterminology-site/assets/css/capabilities-v280.css">
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script>
</head><body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<header class="site-header"><div class="shell"><a href="/pterminology-site/">المنصة</a><nav aria-label="التنقل الرئيسي"><a href="/pterminology-site/special-needs/">مركز ذوي الاحتياجات الخاصة</a><a href="/pterminology-site/capabilities/">أدلة القدرات</a><a href="/pterminology-site/capabilities/expanded/">التوسعة النادرة</a></nav></div></header>
<main id="main" class="shell">{body}</main>
<footer class="site-footer"><div class="shell"><p>محتوى تثقيفي داخلي المراجعة، وليس تشخيصًا أو وصفة علاجية فردية.</p><a href="/pterminology-site/trust/">الثقة والمنهجية</a></div></footer>
</body></html>'''

def condition_page(data,c):
    cat=data["categories"][c["category"]]
    canonical=BASE+SECTION+"/"+c["slug"]+"/"
    description=f"دليل عربي موسع عن {c['title_ar']}: التعريف والأسباب والتشخيص والمتابعة والتدخل وخطة الأسرة ومقدم الخدمة وحدود القدرات."
    body=f'''
<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/pterminology-site/">الرئيسية</a> ← <a href="/pterminology-site/capabilities/">أدلة القدرات</a> ← <a href="/pterminology-site/capabilities/expanded/">50 حالة إضافية</a></nav>
<article>
<header class="hero"><p class="eyebrow">الحالة رقم {c["rank"]} · {e(cat["label"])}</p><h1>{e(c["title_ar"])}</h1><p lang="en">{e(c["title_en"])}</p>
<p class="lead">{e(description)}</p><div class="notice"><strong>حدود الدليل:</strong> {e(data["scope_note"])}</div></header>
<section><h2>الوصف العالمي المعتمد للحالة</h2><p>{e(c["pattern"])}</p><p>يُستخدم الاسم بوصفه مدخلًا لتنظيم التقييم والمتابعة، لا وصفًا كاملًا للشخص. الشدة والاحتياجات والقدرات تختلف، لذلك يجب توثيق الوظيفة الفعلية في التواصل والتعلم والحركة والعناية الذاتية والمشاركة.</p></section>
<section><h2>ما هي الحالة؟</h2><p>{e(c["cause"])}</p><p>لا يثبت التشخيص من التشابه الشكلي أو من قائمة أعراض على الإنترنت. يجب تفسير النتيجة الجينية أو العصبية أو الاستقلابية داخل السياق السريري، وشرح ما تؤكده وما لا تستطيع التنبؤ به.</p></section>
<section><h2>العلامات والأعراض والتباين</h2><p>{e(c["pattern"])}</p><p>قد لا تظهر جميع السمات، وقد تتغير الأولويات مع العمر والعلاج والبيئة. التغير الجديد عن خط الأساس يحتاج سببًا قابلًا للفحص مثل الألم أو النوم أو النوبات أو العدوى أو فقد الوصول، ولا يوصف مباشرة بأنه سلوك.</p></section>
<section><h2>مسار التشخيص والتقييم</h2><p>{e(c["diagnosis"])}</p>{list_html(["تاريخ نمائي وصحي وعائلي موثق مع خط زمني للتغيرات.","فحص طبي وعصبي ووظيفي يحدد الأعضاء والمهارات المتأثرة.","اختبار جيني أو إنزيمي أو كهربائي مناسب مع تأكيد النتيجة عند الحاجة.","تقييم سمع وبصر وبلع ونوم وتواصل وحركة عندما تؤثر في تفسير الأداء.","استشارة وراثية أو تخصصية تشرح احتمال التكرار وحدود التنبؤ."])}</section>
<section><h2>المراقبة الصحية والوقاية</h2><p>{e(c["medical_focus"])}</p><p>تُكتب المراقبة في جدول يحدد المسؤول والتكرار وما الذي يستدعي التقديم المبكر للموعد. لا يُطلب فحص أو تصوير لمجرد وجود التشخيص إذا لم تدعمه الإرشادات أو الأعراض.</p></section>
<section><h2>بروتوكول العلاج والتدخل</h2><p>{e(c["care"])}</p>{list_html(["تثبيت الأمان والصحة والنوم والألم والتغذية قبل رفع متطلبات التدريب.","اختيار هدف وظيفي يوافق عليه الشخص أو أسرته ويمكن قياسه في الحياة اليومية.","تجربة تكييف واحد في كل مرة وقياس أثره في الجودة والاستقلال والتعب.","تدريب المهارة الكاملة في سياقها ثم اختبار نقلها إلى شخص أو مكان آخر.","مراجعة الخطة دوريًا والاستمرار أو التعديل أو التوقف وفق البيانات والاختيار."])}</section>
<section><h2>خطة قابلة للتطبيق للأهل</h2>{list_html(cat["family_actions"])}<p><strong>نموذج 12 أسبوعًا:</strong> أسبوعان لخط الأساس والأمان، ثلاثة أسابيع لمقارنة وسائل التواصل والوصول، ثلاثة للتدريب الوظيفي، أسبوعان للتعميم، وأسبوعان للمراجعة واتخاذ القرار.</p></section>
<section><h2>خطة مقدم الخدمة</h2>{list_html(cat["provider_actions"])}<p>يجب توثيق من اتخذ القرار، وما مستوى المساعدة، وما الذي تغير في البيئة. لا يُنسب نجاح الشريك أو الأداة إلى الشخص دون التحقق من اختياره ومراجعته للناتج.</p></section>
<section><h2>التواصل والتعليم والوصول</h2>{list_html(cat["accommodations"])}<p>يظل AAC متاحًا حتى عند ظهور الكلام؛ وجود كلمات قليلة لا يعني أن الكلام يكفي للألم والرفض والتعلم والقرار. يجب تدريب الشركاء وعدم حصر النظام في جلسة العلاج.</p></section>
<section><h2>القدرات المحتملة وكيف تُكتشف</h2><p>{e(c["opportunity"])}</p>{list_html(["صياغة فرضية محددة قابلة للنفي بدل وصف عام مثل موهوب.","اختبار المهمة في نسختين متكافئتين تختلفان في قناة العرض أو الأداة أو البيئة.","قياس الدقة والاستقلال والرغبة والتعب والتعميم عبر يومين على الأقل.","إيقاف الفرضية إذا سببت ألمًا أو ضغطًا أو لم تتكرر أو لم تخدم هدفًا يهم الشخص."])}</section>
<section><h2>أفكار إبداعية خارج الصندوق</h2>{list_html(cat["creative"])}</section>
<section><h2>ما الذي يجب تجنبه؟</h2>{list_html(["اختزال الشخص في التشخيص أو التنبؤ بذكائه ومهنته من اسم الحالة.","تغيير دواء أو حمية أو مكمل أو خطة نوبات استنادًا إلى هذه الصفحة.","إجبار التواصل البصري أو الكلام أو المشي عندما توجد وسيلة أكثر أمانًا وفاعلية.","تفسير الألم أو النوبات أو الهوس أو التدهور أو الحرمان من النوم كنقطة قوة.","نشر بيانات الشخص أو صوره أو نتائج اختباره دون موافقة واضحة وقابلة للوصول."])}</section>
<section><h2>علامات الخطر ومتى نطلب المساعدة</h2><p>{e(c["safety"])}</p><p>عند الشك في طارئ، تُتبع خطة الفريق وخدمات الطوارئ المحلية. هذه الصفحة لا تحدد الجرعات ولا تستبدل التقييم المباشر.</p></section>
<section><h2>المصدر المباشر وحدود الدليل</h2><p><a href="{e(c["source_url"])}" rel="noopener noreferrer">{e(c["source_title"])}</a></p>{list_html([f'{s["publisher"]}: {s["title"]} — {s["url"]}' for s in data["common_sources"]])}<p><strong>حالة المراجعة:</strong> {e(data["review_status"])}</p></section>
</article>'''
    schema={"@context":"https://schema.org","@graph":[
      {"@type":"MedicalWebPage","@id":canonical+"#page","url":canonical,"name":c["title_ar"],"headline":c["title_ar"],"description":description,"inLanguage":"ar","dateModified":data["updated_at"],"isPartOf":{"@type":"CollectionPage","url":BASE+"capabilities/expanded/"},"author":{"@type":"Organization","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة"},"reviewedBy":{"@type":"Organization","name":"المراجعة المنهجية الداخلية للمنصة"},"citation":[c["source_url"]]+[s["url"] for s in data["common_sources"]]},
      {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":BASE},{"@type":"ListItem","position":2,"name":"أدلة القدرات","item":BASE+"capabilities/"},{"@type":"ListItem","position":3,"name":c["title_ar"],"item":canonical}]}
    ]}
    page=layout(f"{c['title_ar']} | دليل الحالة والخطة التطبيقية",description,canonical,body,schema)
    if words(re.sub("<[^>]+>"," ",page))<700:
        raise AssertionError((c["slug"],words(re.sub("<[^>]+>"," ",page))))
    return page

def index_page(data):
    canonical=BASE+INDEX_ROUTE+"/"
    cards="".join(f'<article class="card"><p class="eyebrow">#{c["rank"]}</p><h2><a href="/pterminology-site/capabilities/{e(c["slug"])}/">{e(c["title_ar"])}</a></h2><p lang="en">{e(c["title_en"])}</p><p>{e(c["pattern"])}</p></article>' for c in data["conditions"])
    body=f'''<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/pterminology-site/">الرئيسية</a> ← <a href="/pterminology-site/capabilities/">أدلة القدرات</a></nav>
<header class="hero"><p class="eyebrow">الإصدار 281</p><h1>{e(data["title"])}</h1><p class="lead">خمسون دليلًا غير مكرر للحالات النادرة، تربط الوصف الطبي بالمتابعة والتأهيل والتعليم وخطة الأسرة ومقدم الخدمة.</p><div class="notice">{e(data["review_status"])}</div></header>
<section><h2>منهجية الدفعة</h2>{list_html(["كل حالة لها مصدر مباشر من جهة صحية أو مرجع GeneReviews/NCBI.","لا توجد جرعات أو تشخيص آلي أو ادعاء اعتماد خارجي.","القدرات فرضيات فردية تُختبر في مهمة حقيقية، وليست مواهب مرتبطة بالتشخيص.","تحتوي كل صفحة على خطة للأهل ومقدم الخدمة ومراقبة صحية وحدود أمان."])}</section>
<section><h2>الحالات الخمسون</h2><div class="grid">{cards}</div></section>'''
    schema={"@context":"https://schema.org","@type":"CollectionPage","url":canonical,"name":data["title"],"description":"50 دليلًا عربيًا للحالات والمتلازمات النادرة","inLanguage":"ar","dateModified":data["updated_at"],"hasPart":[{"@type":"MedicalWebPage","url":BASE+"capabilities/"+c["slug"]+"/","name":c["title_ar"]} for c in data["conditions"]]}
    return layout(data["title"],"50 دليلًا عربيًا موسعًا للحالات والمتلازمات النادرة.",canonical,body,schema)

def inject_bridge(path):
    if not path.is_file(): return
    text=path.read_text(encoding="utf-8")
    block=f'''{BRIDGE_START}<section class="capabilities-v281-bridge"><h2>50 دليلًا إضافيًا للحالات النادرة</h2><p>دفعة منهجية جديدة غير مكررة تشمل متلازمات نمائية عصبية واضطرابات صرعية واستقلابية.</p><a href="/pterminology-site/capabilities/expanded/">استعرض الدفعة الجديدة</a></section>{BRIDGE_END}'''
    text=re.sub(re.escape(BRIDGE_START)+r".*?"+re.escape(BRIDGE_END),"",text,flags=re.S)
    if "</main>" in text: text=text.replace("</main>",block+"</main>",1)
    elif "</body>" in text: text=text.replace("</body>",block+"</body>",1)
    path.write_text(text,encoding="utf-8")

def write_sitemap(root,data):
    urls=[BASE+INDEX_ROUTE+"/"]+[BASE+"capabilities/"+c["slug"]+"/" for c in data["conditions"]]
    urlset=ET.Element(f"{{{NS}}}urlset")
    for url in urls:
        node=ET.SubElement(urlset,f"{{{NS}}}url")
        ET.SubElement(node,f"{{{NS}}}loc").text=url
        ET.SubElement(node,f"{{{NS}}}lastmod").text=data["updated_at"]
    ET.ElementTree(urlset).write(root/SITEMAP,encoding="utf-8",xml_declaration=True)
    sm=root/"sitemap.xml"
    if sm.is_file():
        text=sm.read_text(encoding="utf-8")
        target=BASE+SITEMAP
        if target not in text:
            if "<sitemapindex" in text:
                text=text.replace("</sitemapindex>",f"<sitemap><loc>{target}</loc><lastmod>{data['updated_at']}</lastmod></sitemap></sitemapindex>")
            else:
                text += f"\n<!-- v281 sitemap: {target} -->\n"
            sm.write_text(text,encoding="utf-8")
    return urls

def publish(root):
    data=load(); root=Path(root)
    (root/"capabilities"/"expanded").mkdir(parents=True,exist_ok=True)
    (root/"capabilities"/"expanded"/"index.html").write_text(index_page(data),encoding="utf-8")
    hashes=set()
    for c in data["conditions"]:
        path=root/"capabilities"/c["slug"]; path.mkdir(parents=True,exist_ok=True)
        page=condition_page(data,c); digest=hash(page)
        assert digest not in hashes; hashes.add(digest)
        (path/"index.html").write_text(page,encoding="utf-8")
    inject_bridge(root/"capabilities"/"index.html"); inject_bridge(root/"special-needs"/"index.html")
    urls=write_sitemap(root,data)
    (root/"api").mkdir(exist_ok=True)
    report={"version":281,"status":"passed","condition_count":50,"detail_page_count":50,"generated_page_count":51,"sitemap_url_count":len(urls),"external_clinical_review_completed":False,"diagnostic_automation":False,"slugs":[c["slug"] for c in data["conditions"]]}
    (root/"api"/"capabilities-v281.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False)); return report

def main():
    p=argparse.ArgumentParser(); p.add_argument("root",type=Path); args=p.parse_args(); publish(args.root)
if __name__=="__main__": main()
