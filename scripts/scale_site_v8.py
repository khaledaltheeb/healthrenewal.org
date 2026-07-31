from __future__ import annotations

import csv
import html
import json
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path('_site')
BASE = os.environ.get('SITE_BASE', 'https://healthrenewal.org/').rstrip('/') + '/'
TODAY = date.today().isoformat()

DOMAINS = [
    ('القلق','Anxiety','اضطرابات القلق'),('الاكتئاب','Depression','اضطرابات المزاج'),('الوسواس القهري','Obsessive-Compulsive Disorder','الوسواس والطقوس'),
    ('اضطراب الهلع','Panic Disorder','اضطرابات القلق'),('الرهاب الاجتماعي','Social Anxiety','اضطرابات القلق'),('الصدمة النفسية','Psychological Trauma','الصدمة والتعافي'),
    ('اضطراب ما بعد الصدمة','PTSD','الصدمة والتعافي'),('الاحتراق النفسي','Burnout','الصحة المهنية'),('الضغط النفسي','Stress','الصحة العامة'),
    ('الحزن','Grief','الفقد والتكيف'),('الفقد','Loss','الفقد والتكيف'),('الوحدة','Loneliness','العلاقات'),('تقدير الذات','Self-Esteem','الذات والشخصية'),
    ('الثقة بالنفس','Self-Confidence','الذات والشخصية'),('تنظيم الانفعال','Emotion Regulation','الانفعالات'),('الذكاء العاطفي','Emotional Intelligence','الانفعالات'),
    ('الغضب','Anger','الانفعالات'),('الخوف','Fear','الانفعالات'),('الخجل','Shyness','العلاقات'),('التعاطف','Empathy','العلاقات'),
    ('التعلق','Attachment','العلاقات'),('التعلق الآمن','Secure Attachment','العلاقات'),('التعلق القلق','Anxious Attachment','العلاقات'),('التعلق التجنبي','Avoidant Attachment','العلاقات'),
    ('العلاقات السامة','Toxic Relationships','العلاقات'),('الحدود النفسية','Psychological Boundaries','العلاقات'),('التواصل الحازم','Assertive Communication','العلاقات'),
    ('المرونة النفسية','Psychological Resilience','النمو والتعافي'),('التقبل','Acceptance','النمو والتعافي'),('اليقظة الذهنية','Mindfulness','النمو والتعافي'),
    ('التسويف','Procrastination','الدافعية والسلوك'),('الدافعية','Motivation','الدافعية والسلوك'),('العادات','Habits','الدافعية والسلوك'),('ضبط النفس','Self-Control','الدافعية والسلوك'),
    ('اتخاذ القرار','Decision Making','المعرفي'),('التفكير النقدي','Critical Thinking','المعرفي'),('التحيزات المعرفية','Cognitive Biases','المعرفي'),
    ('الاجترار الفكري','Rumination','المعرفي'),('التفكير الكارثي','Catastrophizing','المعرفي'),('التشوهات المعرفية','Cognitive Distortions','المعرفي'),
    ('الذاكرة','Memory','علم النفس المعرفي'),('الذاكرة العاملة','Working Memory','علم النفس المعرفي'),('الانتباه','Attention','علم النفس المعرفي'),
    ('التركيز','Concentration','علم النفس المعرفي'),('الإدراك','Perception','علم النفس المعرفي'),('التعلم','Learning','علم النفس التربوي'),
    ('صعوبات التعلم','Learning Difficulties','علم النفس التربوي'),('الدافعية الدراسية','Academic Motivation','علم النفس التربوي'),('قلق الاختبار','Test Anxiety','علم النفس التربوي'),
    ('النوم','Sleep','الصحة والسلوك'),('الأرق','Insomnia','الصحة والسلوك'),('الأكل العاطفي','Emotional Eating','الصحة والسلوك'),('صورة الجسد','Body Image','الصحة والسلوك'),
    ('الإدمان','Addiction','الإدمان والتعافي'),('إدمان الإنترنت','Internet Addiction','الإدمان والتعافي'),('إدمان الألعاب','Gaming Disorder','الإدمان والتعافي'),
    ('فرط الحركة وتشتت الانتباه','ADHD','النمو العصبي'),('التوحد','Autism','النمو العصبي'),('الحساسية الحسية','Sensory Sensitivity','النمو العصبي'),
    ('الشخصية','Personality','الشخصية'),('الانبساط','Extraversion','الشخصية'),('الانطواء','Introversion','الشخصية'),('العصابية','Neuroticism','الشخصية'),
    ('الكمالية','Perfectionism','الشخصية'),('النرجسية','Narcissism','الشخصية'),('التلاعب النفسي','Psychological Manipulation','العلاقات'),
    ('التنمر','Bullying','علم النفس الاجتماعي'),('العنف الأسري','Domestic Violence','علم النفس الاجتماعي'),('الوصمة النفسية','Mental Health Stigma','علم النفس الاجتماعي'),
    ('الهوية','Identity','النمو والشخصية'),('أزمة الهوية','Identity Crisis','النمو والشخصية'),('المراهقة','Adolescence','علم النفس النمائي'),('الطفولة المبكرة','Early Childhood','علم النفس النمائي'),
    ('الشيخوخة النفسية','Psychological Aging','علم النفس النمائي'),('الأبوة والأمومة','Parenting','الأسرة'),('التربية الإيجابية','Positive Parenting','الأسرة'),
    ('الإرشاد النفسي','Psychological Counseling','العلاج والإرشاد'),('العلاج المعرفي السلوكي','Cognitive Behavioral Therapy','العلاج والإرشاد'),('العلاج بالقبول والالتزام','Acceptance and Commitment Therapy','العلاج والإرشاد'),
    ('العلاج الجدلي السلوكي','Dialectical Behavior Therapy','العلاج والإرشاد'),('العلاج الأسري','Family Therapy','العلاج والإرشاد'),('العلاج الجماعي','Group Therapy','العلاج والإرشاد'),
    ('القياس النفسي','Psychometrics','البحث والقياس'),('الاختبارات النفسية','Psychological Testing','البحث والقياس'),('الصدق والثبات','Validity and Reliability','البحث والقياس'),
    ('علم النفس الاجتماعي','Social Psychology','فروع علم النفس'),('علم النفس المعرفي','Cognitive Psychology','فروع علم النفس'),('علم النفس الإكلينيكي','Clinical Psychology','فروع علم النفس'),
    ('علم النفس التربوي','Educational Psychology','فروع علم النفس'),('علم النفس التنظيمي','Organizational Psychology','فروع علم النفس'),('علم النفس العصبي','Neuropsychology','فروع علم النفس'),
]

FACETS = [
    ('التعريف والمفهوم','definition and concept'),('الأعراض والعلامات','symptoms and signs'),('الأسباب والعوامل','causes and factors'),('التقييم النفسي','psychological assessment'),
    ('التشخيص التفريقي','differential diagnosis'),('العلاج النفسي','psychotherapy'),('العلاج المعرفي السلوكي','cognitive behavioral treatment'),('الدعم الذاتي','self-help'),
    ('استراتيجيات التعامل','coping strategies'),('الوقاية','prevention'),('التدخل المبكر','early intervention'),('لدى الأطفال','in children'),('لدى المراهقين','in adolescents'),
    ('لدى البالغين','in adults'),('لدى كبار السن','in older adults'),('في الأسرة','in families'),('في العلاقات','in relationships'),('في مكان العمل','in the workplace'),
    ('في المدرسة والجامعة','in school and university'),('والنوم','and sleep'),('والتغذية','and nutrition'),('والرياضة','and exercise'),('والصحة الجسدية','and physical health'),
    ('والضغط النفسي','and stress'),('والمرونة النفسية','and resilience'),('والوعي الذاتي','and self-awareness'),('والتواصل','and communication'),('والحدود النفسية','and boundaries'),
    ('والدافعية','and motivation'),('وجودة الحياة','and quality of life')
]

STYLE = """body{font-family:system-ui,-apple-system,'Segoe UI',Tahoma,Arial,sans-serif;background:#f6f3ea;color:#172a2a;margin:0;line-height:1.85}header,main,footer{max-width:1080px;margin:auto;padding:20px}.top{background:#123f3a;color:#fff}.top a{color:#fff}.hero{padding:48px 20px;background:linear-gradient(135deg,#123f3a,#1e665d);color:#fff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.card{background:#fff;border:1px solid #ddd5c7;border-radius:16px;padding:20px}.tag{display:inline-block;background:#e4efe9;border-radius:999px;padding:5px 11px;margin:3px;font-size:.9rem}a{color:#0c6258;text-decoration:none}a:hover{text-decoration:underline}h1,h2,h3{line-height:1.35}.search{width:100%;max-width:720px;padding:16px;border:1px solid #bbb;border-radius:12px;font-size:1.05rem}.muted{color:#5d6867}.crumbs{font-size:.92rem;margin:12px 0}.count{font-weight:700;color:#b88a28}@media(max-width:600px){.hero{padding:30px 16px}header,main,footer{padding:16px}}"""

def esc(value: str) -> str:
    return html.escape(value, quote=True)

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def page(title: str, description: str, path: str, body: str, schema: dict | list | None = None) -> str:
    canonical = BASE + path.lstrip('/')
    ld = '' if schema is None else '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(',', ':')) + '</script>'
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar" href="{canonical}"><link rel="alternate" hreflang="x-default" href="{canonical}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="article"><meta property="og:url" content="{canonical}"><style>{STYLE}</style>{ld}</head><body><div class="top"><header><a href="{BASE}">مصطلحات علم النفس</a> · <a href="{BASE}encyclopedia/">الموسوعة</a> · <a href="{BASE}hubs/">المراكز الموضوعية</a> · <a href="{BASE}terms/">المعجم الأساسي</a></header></div>{body}<footer><p>مصطلحات علم النفس — موسوعة عربية منظمة للمفاهيم النفسية.</p></footer></body></html>'''

def make_slug(index: int) -> str:
    return f'concept-{index:04d}'

def build_entries() -> list[dict]:
    entries: list[dict] = []
    index = 1
    for ar, en, category in DOMAINS:
        for facet_ar, facet_en in FACETS:
            title_ar = f'{ar}: {facet_ar}'
            title_en = f'{en}: {facet_en}'
            entries.append({'id': index, 'slug': make_slug(index), 'ar': title_ar, 'en': title_en, 'domain_ar': ar, 'domain_en': en, 'category': category, 'facet': facet_ar})
            index += 1
    return entries[:2000]

def concept_body(item: dict, related: list[dict]) -> str:
    rel = ''.join(f'<li><a href="{BASE}encyclopedia/{r["slug"]}/">{esc(r["ar"])}</a></li>' for r in related)
    return f'''<main><div class="crumbs"><a href="{BASE}">الرئيسية</a> ← <a href="{BASE}encyclopedia/">الموسوعة</a> ← {esc(item['category'])}</div><article class="card"><span class="tag">{esc(item['category'])}</span><h1>{esc(item['ar'])}</h1><p class="muted" lang="en" dir="ltr">{esc(item['en'])}</p><h2>ما المقصود بهذا الموضوع؟</h2><p>يتناول هذا المدخل <strong>{esc(item['facet'])}</strong> في سياق <strong>{esc(item['domain_ar'])}</strong>. الهدف هو تقديم إطار واضح يساعد القارئ على فهم المصطلح، والتمييز بين المعرفة العامة والتقييم المهني، وربط المفهوم بالسياق اليومي والبحث العلمي.</p><h2>لماذا يهم فهمه؟</h2><p>الفهم الدقيق يقلل الخلط بين المصطلحات المتشابهة، ويدعم التواصل الأفضل مع المختصين، ويساعد على ملاحظة الأنماط دون تحويل المعلومات العامة إلى تشخيص ذاتي. تختلف شدة الظواهر النفسية ومدتها وتأثيرها من شخص إلى آخر.</p><h2>نقاط عملية للفهم</h2><ul><li>انظر إلى المدة والتكرار والسياق، لا إلى علامة منفردة.</li><li>قارن الأثر على الدراسة والعمل والعلاقات والنوم.</li><li>انتبه إلى العوامل الجسدية والدوائية والبيئية.</li><li>اطلب تقييمًا مهنيًا عندما يصبح الأثر مستمرًا أو معطلًا.</li></ul><h2>مصطلحات وموضوعات مرتبطة</h2><ul>{rel}</ul></article></main>'''

def build_concepts(entries: list[dict]) -> list[str]:
    urls: list[str] = []
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_domain[e['domain_ar']].append(e)
    for e in entries:
        group = by_domain[e['domain_ar']]
        pos = group.index(e)
        related = [group[(pos + i) % len(group)] for i in range(1, 6)]
        path = f'encyclopedia/{e["slug"]}/'
        description = f'{e["ar"]}: شرح عربي منظم يتناول المفهوم والسياق والنقاط العملية والموضوعات المرتبطة.'
        schema = {'@context':'https://schema.org','@type':'DefinedTerm','name':e['ar'],'alternateName':e['en'],'description':description,'inDefinedTermSet':BASE+'encyclopedia/','url':BASE+path}
        write(ROOT / path / 'index.html', page(f'{e["ar"]} | مصطلحات علم النفس', description, path, concept_body(e, related), schema))
        urls.append(BASE + path)
    return urls

def build_hubs(entries: list[dict]) -> list[str]:
    urls: list[str] = []
    cards = []
    for i in range(200):
        group = entries[i*10:(i+1)*10]
        slug = f'hub-{i+1:03d}'
        title = f'المجموعة النفسية {i+1:03d}'
        links = ''.join(f'<li><a href="{BASE}encyclopedia/{x["slug"]}/">{esc(x["ar"])}</a> <span class="muted" lang="en">— {esc(x["en"])}</span></li>' for x in group)
        body = f'<main><div class="crumbs"><a href="{BASE}">الرئيسية</a> ← <a href="{BASE}hubs/">المراكز الموضوعية</a></div><section class="card"><h1>{title}</h1><p>صفحة مركزية تجمع عشرة مداخل مترابطة لتسهيل التصفح الداخلي وبناء مسارات موضوعية واضحة لمحركات البحث والقارئ.</p><ol>{links}</ol></section></main>'
        path = f'hubs/{slug}/'
        description = f'{title}: عشرة مفاهيم نفسية مترابطة ضمن موسوعة مصطلحات علم النفس.'
        write(ROOT / path / 'index.html', page(f'{title} | مصطلحات علم النفس', description, path, body, {'@context':'https://schema.org','@type':'CollectionPage','name':title,'url':BASE+path}))
        urls.append(BASE + path)
        cards.append(f'<article class="card"><h2><a href="{BASE}{path}">{title}</a></h2><p>{esc(group[0]["domain_ar"])} وما يرتبط بها.</p></article>')
    index_body = '<section class="hero"><main><h1>200 مركز موضوعي</h1><p>صفحات تجمع 2000 مفهوم نفسي في مجموعات صغيرة مترابطة.</p></main></section><main><div class="grid">'+''.join(cards)+'</div></main>'
    write(ROOT/'hubs/index.html', page('المراكز الموضوعية | مصطلحات علم النفس','مئتا صفحة مركزية تربط ألفي مفهوم نفسي في مجموعات قابلة للتصفح.','hubs/',index_body,{'@context':'https://schema.org','@type':'CollectionPage','name':'المراكز الموضوعية','url':BASE+'hubs/'}))
    urls.append(BASE+'hubs/')
    return urls

def build_encyclopedia_index(entries: list[dict]) -> list[str]:
    data = [{'id':e['id'],'slug':e['slug'],'ar':e['ar'],'en':e['en'],'category':e['category'],'domain':e['domain_ar']} for e in entries]
    write(ROOT/'api/encyclopedia-v8.json', json.dumps({'version':'8','count':len(data),'items':data},ensure_ascii=False,separators=(',',':')))
    with (ROOT/'downloads/encyclopedia-2000.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','slug','ar','en','category','domain']);w.writeheader();w.writerows(data)
    cards = ''.join(f'<article class="card item" data-q="{esc((e["ar"]+" "+e["en"]+" "+e["category"]).lower())}"><span class="tag">{esc(e["category"])}</span><h2><a href="{BASE}encyclopedia/{e["slug"]}/">{esc(e["ar"])}</a></h2><p class="muted" lang="en" dir="ltr">{esc(e["en"])}</p></article>' for e in entries)
    script = """<script>const q=document.getElementById('q'),items=[...document.querySelectorAll('.item')],n=document.getElementById('n');function run(){const s=q.value.trim().toLowerCase();let c=0;items.forEach(x=>{const ok=!s||x.dataset.q.includes(s);x.hidden=!ok;if(ok)c++});n.textContent=c}q.addEventListener('input',run);run()</script>"""
    body = f'<section class="hero"><main><h1>الموسوعة النفسية العربية</h1><p><span class="count">2000</span> مفهوم وموضوع نفسي، مع بحث فوري وصفحات مستقلة قابلة للفهرسة.</p><input id="q" class="search" type="search" placeholder="ابحث بالعربية أو الإنجليزية"><p>النتائج: <strong id="n">2000</strong></p></main></section><main><div class="grid">{cards}</div></main>{script}'
    write(ROOT/'encyclopedia/index.html', page('الموسوعة النفسية العربية — 2000 مفهوم','موسوعة عربية تضم 2000 مفهوم وموضوع في علم النفس والصحة النفسية مع بحث فوري وصفحات مستقلة.','encyclopedia/',body,{'@context':'https://schema.org','@type':'CollectionPage','name':'الموسوعة النفسية العربية','numberOfItems':2000,'url':BASE+'encyclopedia/'}))
    return [BASE+'encyclopedia/',BASE+'api/encyclopedia-v8.json',BASE+'downloads/encyclopedia-2000.csv']

def existing_urls() -> list[str]:
    urls=[]
    for p in ROOT.rglob('index.html'):
        rel=p.relative_to(ROOT).parent.as_posix()
        if rel=='.': urls.append(BASE)
        else: urls.append(BASE+rel.strip('/')+'/')
    for name in ['google644f1f7a8b7aaa2b.html','feed.xml','opensearch.xml','manifest.webmanifest','llms.txt']:
        if (ROOT/name).exists(): urls.append(BASE+name)
    return sorted(set(urls))

def urlset(urls: list[str]) -> str:
    root=ET.Element('urlset',{'xmlns':'http://www.sitemaps.org/schemas/sitemap/0.9'})
    for u in urls:
        node=ET.SubElement(root,'url');ET.SubElement(node,'loc').text=u;ET.SubElement(node,'lastmod').text=TODAY
    return ET.tostring(root,encoding='unicode',xml_declaration=True)

def build_sitemaps(all_urls: list[str], concept_urls: list[str], hub_urls: list[str]) -> None:
    concept_chunks=[concept_urls[i:i+1000] for i in range(0,len(concept_urls),1000)]
    maps=[]
    for i,chunk in enumerate(concept_chunks,1):
        name=f'sitemap-terms-{i}.xml';write(ROOT/name,urlset(chunk));maps.append(name)
    write(ROOT/'sitemap-hubs.xml',urlset(hub_urls));maps.append('sitemap-hubs.xml')
    other=sorted(set(all_urls)-set(concept_urls)-set(hub_urls))
    write(ROOT/'sitemap-core.xml',urlset(other));maps.append('sitemap-core.xml')
    idx=ET.Element('sitemapindex',{'xmlns':'http://www.sitemaps.org/schemas/sitemap/0.9'})
    for name in maps:
        sm=ET.SubElement(idx,'sitemap');ET.SubElement(sm,'loc').text=BASE+name;ET.SubElement(sm,'lastmod').text=TODAY
    write(ROOT/'sitemap.xml',ET.tostring(idx,encoding='unicode',xml_declaration=True))
    write(ROOT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')

def create_import_templates() -> None:
    readme='''# نظام المحتوى القابل للتوسع\n\nأضف المصطلحات المستقبلية إلى ملف CSV بالأعمدة: `slug,ar,en,category,description,keywords,related`.\n\nقواعد النشر:\n- slug فريد وثابت.\n- عنوان عربي وإنجليزي.\n- وصف أصلي لا يقل عن 120 حرفًا.\n- تصنيف واضح.\n- مراجعة التكرار قبل الدمج.\n\nتشغّل GitHub Actions المولّد والاختبارات تلقائيًا.\n'''
    write(Path('content/README.md'),readme)
    write(Path('content/import-template.csv'),'slug,ar,en,category,description,keywords,related\nexample-term,مثال,Example,تصنيف,وصف أصلي موسع,كلمة1|كلمة2,term-a|term-b\n')


def main() -> None:
    if not ROOT.exists():
        raise SystemExit('_site does not exist; build v7 first')
    entries=build_entries()
    if len(entries)!=2000 or len({e['slug'] for e in entries})!=2000 or len({e['ar'] for e in entries})!=2000:
        raise SystemExit('entry uniqueness/count validation failed')
    concept_urls=build_concepts(entries)
    hub_urls=build_hubs(entries)
    extra_urls=build_encyclopedia_index(entries)
    create_import_templates()
    all_urls=sorted(set(existing_urls()+extra_urls+concept_urls+hub_urls))
    build_sitemaps(all_urls,concept_urls,hub_urls)
    report={'version':8,'concepts':len(concept_urls),'hubs':200,'all_indexable_urls':len(all_urls),'sitemap_index':True,'generated':TODAY}
    write(ROOT/'api/build-report-v8.json',json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    main()
