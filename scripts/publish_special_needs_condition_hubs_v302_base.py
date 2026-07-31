#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, json, re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
BASE='https://healthrenewal.org/'; BP='/'
MANIFEST=ROOT/'content/v302/special-needs-condition-hubs-ar.json'; PROVIDERS=ROOT/'content/v302/special-needs-providers-ar.json'
SOURCE_OVERRIDE_FILE=ROOT/'content/v312/special-needs-condition-source-url-overrides.json'
VERSION=302; UPDATED='2026-07-27'; MARK='data-condition-hubs-v302'; HUB_MARKER=MARK; PROVIDERS_FILE=PROVIDERS; INSERT='<section class="section" id="method">'
BANNED=re.compile(r'(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)')

def e(x): return html.escape(str(x),quote=True)
def read(path):
    try: data=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc: raise SystemExit(f'Invalid JSON {path}: {exc}') from exc
    if not isinstance(data,dict): raise SystemExit(f'JSON object required: {path}')
    return data

def https(url):
    p=urlparse(str(url)); return p.scheme=='https' and bool(p.netloc)

def normalized_host(url): return urlparse(str(url)).netloc.lower().removeprefix('www.')
def official_domain_family(organization,old,new):
    old_host=normalized_host(old); new_host=normalized_host(new)
    if not old_host or not new_host: return False
    if old_host==new_host: return True
    if organization=='ASHA':
        return (old_host=='asha.org' or old_host.endswith('.asha.org')) and (new_host=='asha.org' or new_host.endswith('.asha.org'))
    return False

def validate_provider_data(data):
    if data.get('version')!=VERSION or not isinstance(data.get('providers'),list): raise SystemExit('Provider contract failed')
    ids=set(); types=set(data.get('allowed_types',[])); specs=set(data.get('allowed_specialties',[]))
    for p in data['providers']:
        pid=str(p.get('id','')).strip()
        if not pid or pid in ids: raise SystemExit(f'Invalid provider id: {pid}')
        ids.add(pid)
        if p.get('type') not in types: raise SystemExit(f'Invalid provider type: {pid}')
        if not p.get('specialties') or any(x not in specs for x in p['specialties']): raise SystemExit(f'Invalid specialties: {pid}')
        if any(p.get(k) and not https(p[k]) for k in ('website','maps_url','whatsapp_uri')): raise SystemExit(f'Invalid provider URL: {pid}')
        if p.get('published') is True:
            missing=[k for k in data.get('required_fields_for_publication',[]) if p.get(k) in ('',None,[])]
            if missing or p.get('verification_status')!='verified': raise SystemExit(f'Unverified provider cannot publish: {pid}; {missing}')

validate_providers=validate_provider_data

def apply_source_url_overrides(conditions):
    data=read(SOURCE_OVERRIDE_FILE); overrides=data.get('overrides')
    if data.get('version')!=312 or data.get('language')!='ar' or not isinstance(overrides,dict): raise SystemExit('Source URL override contract failed')
    indexed={}
    for condition in conditions:
        for source in condition.get('sources',[]):
            sid=str(source.get('id','')).strip()
            if not sid or sid in indexed: raise SystemExit(f'Duplicate source id while applying URL overrides: {sid}')
            indexed[sid]=source
    for sid,item in overrides.items():
        if sid not in indexed or not isinstance(item,dict): raise SystemExit(f'Unknown source URL override: {sid}')
        source=indexed[sid]; old=str(item.get('from','')); new=str(item.get('to','')); title=str(item.get('title','')).strip(); organization=str(item.get('organization','')).strip()
        if source.get('url')!=old: raise SystemExit(f'Source URL override no longer matches its declared original: {sid}')
        if not title: raise SystemExit(f'Source URL override title is required: {sid}')
        if not https(new) or not official_domain_family(organization,old,new): raise SystemExit(f'Source URL override must remain on the same verified HTTPS official domain family: {sid}')
        if organization!=source.get('organization'): raise SystemExit(f'Source URL override organization mismatch: {sid}')
        if not str(item.get('reason','')).strip() or not str(item.get('verification_method','')).strip(): raise SystemExit(f'Source URL override requires reason and verification method: {sid}')
        source['url']=new; source['title']=title
    return len(overrides)

def load():
    m=read(MANIFEST); p=read(PROVIDERS); validate_provider_data(p)
    if m.get('version')!=VERSION or len(m.get('condition_files',[]))!=2: raise SystemExit('Condition manifest failed')
    conditions=[read(ROOT/x) for x in m['condition_files']]
    if {x.get('slug') for x in conditions}!={'autism','down-syndrome'}: raise SystemExit('Required condition slugs missing')
    m['_source_url_override_count']=apply_source_url_overrides(conditions)
    for c in conditions:
        if BANNED.search(json.dumps(c,ensure_ascii=False)): raise SystemExit(f'Banned language: {c.get("slug")}')
        sources=c.get('sources',[]); idx={s.get('id'):s for s in sources}
        if len(sources)<5 or len(idx)!=len(sources): raise SystemExit(f'Source contract failed: {c.get("slug")}')
        for s in sources:
            if not https(s.get('url')) or s.get('level') not in {'S1','S2','S3','S4','S5'}: raise SystemExit(f'Invalid source: {s}')
        if len(c.get('sections',[]))<12: raise SystemExit(f'Section depth failed: {c.get("slug")}')
        seen=set()
        for sec in c['sections']:
            sid=sec.get('id'); refs=sec.get('source_ids',[])
            if not sid or sid in seen or len(sec.get('points',[]))<3 or not refs or any(x not in idx for x in refs): raise SystemExit(f'Section contract failed: {c.get("slug")}/{sid}')
            seen.add(sid)
    return m,p,conditions

def provider_cards(data,slug):
    rows=[p for p in data['providers'] if p.get('published') is True and p.get('verification_status')=='verified' and slug in p.get('specialties',[])]
    if not rows:
        return '<div class="empty"><h3>حالة الدليل المحلي</h3><p>لا توجد حاليًا سجلات محلية مكتملة التحقق ومصرح بنشرها لهذا المسار. لا نعرض اسمًا أو وسيلة اتصال قبل التحقق المهني من السجل وموافقة صاحبه على النشر، وتُضاف السجلات المؤهلة عند استيفاء هذه الشروط.</p></div>',0
    out=[]
    for p in sorted(rows,key=lambda x:(str(x.get('country','')),str(x.get('city','')),str(x.get('name_ar','')))):
        links=[]
        if p.get('phone_uri') and p.get('phone_display'): links.append(f'<a href="tel:{e(p["phone_uri"])}">{e(p["phone_display"])}</a>')
        for key,label in [('whatsapp_uri','واتساب'),('website','الموقع'),('maps_url','الخريطة')]:
            if p.get(key): links.append(f'<a href="{e(p[key])}" rel="noopener noreferrer">{label}</a>')
        loc='، '.join(e(x) for x in (p.get('city'),p.get('governorate'),p.get('country')) if x)
        services='، '.join(e(x) for x in p.get('services',[])) or 'الخدمات غير مفصلة'
        out.append(f'<article class="provider"><small>{e(p.get("professional_title") or p["type"])}</small><h3>{e(p["name_ar"])}</h3><p>{services}</p><p><b>الموقع:</b> {loc}</p><p>{" · ".join(links) or "لا توجد وسائل اتصال منشورة"}</p><small>تم التحقق: {e(p.get("verified_at"))}</small></article>')
    return ''.join(out),len(out)

def schema(c,count):
    url=f'{BASE}/special-needs/{c["slug"]}/'
    graph=[{'@type':'MedicalWebPage','@id':url+'#page','url':url,'name':c['page_title'],'description':c['meta_description'],'inLanguage':'ar','dateModified':UPDATED,'about':{'@id':url+'#condition'}},{'@type':'MedicalCondition','@id':url+'#condition','name':c['short_title'],'alternateName':c['english_title'],'description':c['definition']},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'الرئيسية','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'ذوو الاحتياجات الخاصة','item':BASE+'/special-needs/'},{'@type':'ListItem','position':3,'name':c['short_title'],'item':url}]}]
    if count: graph.append({'@type':'ItemList','@id':url+'#providers','name':'مقدمو الخدمات','numberOfItems':count})
    return json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#123f43;line-height:1.9;background:linear-gradient(145deg,#fff,#effaf7)}a{color:#056a64}.wrap{width:min(1180px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;padding:8px;z-index:50}header{position:sticky;top:0;z-index:20;background:#fffffff5;border-bottom:1px solid #c6e2df}.head{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:10px 0}.brand{display:flex;align-items:center;gap:9px;text-decoration:none;font-weight:900;color:#123f43}.brand img{width:46px}nav{display:flex;gap:9px;flex-wrap:wrap}nav a{text-decoration:none;font-weight:800}.hero{padding:48px 0 24px}.hero-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:20px}.kicker{font-weight:900;color:#7d3153;margin:0}h1{font-size:clamp(2.2rem,5vw,4.4rem);line-height:1.18;margin:.15em 0}h2{font-size:clamp(1.45rem,3vw,2.2rem);line-height:1.35}.lead,.summary{color:#506d70}.panel,.section,.evidence-section,.empty,.provider,.sources{background:#fff;border:1px solid #c6e2df;border-radius:19px;padding:19px;box-shadow:0 14px 36px #104c4c18}.notice{border-right:6px solid #7d3153;background:#fff2f6;padding:13px;border-radius:13px}.actions{display:flex;gap:8px;flex-wrap:wrap}.btn{padding:9px 13px;border-radius:11px;background:#a9ebdf;color:#103f42;text-decoration:none;font-weight:900}.grid{display:grid;grid-template-columns:270px 1fr;gap:18px;align-items:start;padding:26px 0}.toc{position:sticky;top:78px;max-height:calc(100vh - 95px);overflow:auto}.toc a{display:block;padding:5px;border-bottom:1px solid #e4f0ee;text-decoration:none}.stack{display:grid;gap:15px}.title-row{display:flex;justify-content:space-between;gap:12px}.ref{font-weight:900;text-decoration:none;background:#effaf7;padding:2px 5px;border-radius:7px}.directory,.source-area{padding:34px 0}.provider-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.provider{display:flex;flex-direction:column}.sources li{margin:1rem 0;border-bottom:1px solid #e1eeec;padding-bottom:.8rem}.sources small{display:block;color:#506d70}.level{background:#e9f8f5;border:1px solid #b8deda;border-radius:7px;padding:1px 5px;font-weight:900}code{direction:ltr;unicode-bidi:embed;background:#eef5f4;padding:2px 4px}footer{border-top:1px solid #c6e2df;padding:26px 0;color:#506d70}@media(max-width:880px){.hero-grid,.grid{grid-template-columns:1fr}.toc{position:static;max-height:none}.provider-grid{grid-template-columns:1fr 1fr}}@media(max-width:620px){.head{align-items:flex-start;flex-direction:column}.provider-grid{grid-template-columns:1fr}.title-row{display:block}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.actions,.toc{display:none}.grid{display:block}.panel,.section,.provider,.sources{box-shadow:none}}'''

def render(c,pdata,status):
    idx={s['id']:s for s in c['sources']}; cards,count=provider_cards(pdata,c['slug']); url=f'{BASE}/special-needs/{c["slug"]}/'
    toc=''.join(f'<a href="#{e(s["id"])}">{e(s["title"])}</a>' for s in c['sections'])
    sections=[]
    for s in c['sections']:
        refs=' '.join(f'<a class="ref" href="#{e(r)}">[{e(r)}]</a>' for r in s['source_ids'])
        pts=''.join(f'<li>{e(x)}</li>' for x in s['points'])
        sections.append(f'<section class="evidence-section" id="{e(s["id"])}"><div class="title-row"><div><p class="kicker">محور علمي</p><h2>{e(s["title"])}</h2></div><div>{refs}</div></div><p class="summary">{e(s["summary"])}</p><ul>{pts}</ul></section>')
    sources=''.join(f'<li id="{e(s["id"])}"><span class="level">{e(s["level"])}</span> <b>{e(s["id"])} — {e(s["organization"])}</b>: <a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["title"])}</a><small>تاريخ المراجعة المسجل: {e(s["reviewed"])}</small></li>' for s in c['sources'])
    audiences=''.join(f'<li>{e(x)}</li>' for x in c['audiences'])
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(c['page_title'])}</title><meta name="description" content="{e(c['meta_description'])}"><meta name="keywords" content="{e(','.join(c['keywords']))}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><link rel="icon" href="{BP}assets/brand/logo-mark.svg"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(c['page_title'])}"><meta property="og:description" content="{e(c['meta_description'])}"><meta property="og:image" content="{BASE}/assets/brand/social-card.svg"><script type="application/ld+json">{schema(c,count)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a class="brand" href="{BP}"><img src="{BP}assets/brand/logo-mark.svg" alt=""><span>منصة الصحة النفسية وذوي الاحتياجات الخاصة</span></a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BP}assessment-lab/">منصة التقييم</a><a href="{BP}trust/">المنهجية</a></nav></div></header><main id="main"><section class="hero"><div class="wrap hero-grid"><div><p class="kicker">مرجع علمي عبر مراحل الحياة</p><h1>{e(c['short_title'])}</h1><p class="lead">{e(c['lead'])}</p><div class="actions"><a class="btn" href="#definition">التعريف</a><a class="btn" href="#directory">الأطباء والمراكز</a><a class="btn" href="#sources">المراجع</a></div><p class="notice"><b>حالة المراجعة:</b> {e(status)}. آخر تحديث {UPDATED}. يلزم تحقق سريري خارجي قبل وصف الصفحة بأنها معتمدة سريريًا.</p></div><aside class="panel"><h2 id="definition">التعريف المرجعي</h2><p>{e(c['definition'])}</p><h3>الفئات المستفيدة</h3><ul>{audiences}</ul><p><b>تنبيه:</b> الصفحة لا تشخص الحالة ولا تستبدل التقييم الفردي.</p></aside></div></section><div class="wrap grid"><aside class="panel toc"><h2>محاور الدليل</h2>{toc}</aside><article class="stack">{''.join(sections)}</article></div><section class="directory" id="directory"><div class="wrap"><p class="kicker">دليل خدمات قابل للتحديث</p><h2>أطباء ومراكز وخدمات مرتبطة بـ{e(c['short_title'])}</h2><p>لا تمثل القائمة تزكية. تحقق من الترخيص والمؤهلات ونطاق الخدمة والتكلفة وسياسة الحماية قبل الحجز.</p><div class="provider-grid">{cards}</div></div></section><section class="source-area" id="sources"><div class="wrap sources"><p class="kicker">قابلية التتبع العلمي</p><h2>المراجع الأصلية</h2><p>S1 جهة أو إرشاد رسمي، وS4 بوابة ممارسة مهنية.</p><ol>{sources}</ol></div></section></main><footer><div class="wrap"><p>محتوى تثقيفي لا يقدم تشخيصًا أو وصفة فردية. استخدم خدمات الطوارئ المحلية عند الخطر.</p><a href="{BP}special-needs/">العودة إلى المركز</a></div></footer></body></html>''',count

def hub_section(conditions):
    cards=''.join(f'<article class="path-card"><p class="eyebrow">بوابة حالة متخصصة</p><h3>{e(c["short_title"])}</h3><p>{e(c["meta_description"])}</p><a href="{BP}special-needs/{e(c["slug"])}/">فتح الدليل العلمي الشامل</a></article>' for c in conditions)
    return f'<section class="section" {MARK} aria-labelledby="condition-hubs-title"><div class="wrap"><p class="eyebrow">بوابات علمية متخصصة</p><h2 id="condition-hubs-title">التوحد ومتلازمة داون: أدلة مستقلة عبر مراحل الحياة</h2><p class="section-intro">صفحتان موسعتان تربطان التعريف والتشخيص والرعاية والتدخل والتعليم والرشد بالمراجع الأصلية، مع قسم جاهز لإضافة الأطباء والمراكز بعد التحقق.</p><div class="path-grid">{cards}</div></div></section>'

def patch_hub(site,conditions):
    path=site/'special-needs/index.html'; source=path.read_text(encoding='utf-8'); section=hub_section(conditions)
    if MARK in source: source,n=re.subn(rf'<section class="section" {MARK}.*?</section>',section,source,count=1,flags=re.S)
    else:
        if source.count(INSERT)!=1: raise SystemExit('Hub insertion point failed')
        source=source.replace(INSERT,section+INSERT,1); n=1
    if n!=1 or source.count(MARK)!=1: raise SystemExit('Hub idempotence failed')
    path.write_text(source,encoding='utf-8')

def q(root,name): return root.tag.split('}',1)[0]+'}'+name if root.tag.startswith('{') else name

def sitemap(site,conditions):
    ET.register_namespace('','http://www.sitemaps.org/schemas/sitemap/0.9'); path=site/'sitemap-special-needs.xml'; tree=ET.parse(path); root=tree.getroot()
    if root.tag.rsplit('}',1)[-1]!='urlset': raise SystemExit('Sitemap must be urlset')
    for c in conditions:
        url=f'{BASE}/special-needs/{c["slug"]}/'; rows=[x for x in root.findall('{*}url') if (x.findtext('{*}loc') or '').strip()==url]
        if len(rows)>1: raise SystemExit(f'Duplicate sitemap URL: {url}')
        row=rows[0] if rows else ET.SubElement(root,q(root,'url'))
        for key,val in {'loc':url,'lastmod':UPDATED,'changefreq':'monthly','priority':'0.92'}.items():
            node=row.find(f'{{*}}{key}')
            if node is None: node=ET.SubElement(row,q(root,key))
            node.text=val
    tree.write(path,encoding='utf-8',xml_declaration=True)

def publish(site):
    manifest,providers,conditions=load(); pages=[]; counts={}
    for c in conditions:
        page,count=render(c,providers,manifest['review_status']); target=site/f'special-needs/{c["slug"]}/index.html'; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(page,encoding='utf-8')
        if BANNED.search(page) or page.count('<h1')!=1 or page.count('application/ld+json')!=1 or page.count('evidence-section')<12: raise SystemExit(f'Render contract failed: {target}')
        pages.append(target.relative_to(site).as_posix()); counts[c['slug']]=count
    patch_hub(site,conditions); sitemap(site,conditions)
    report={'version':VERSION,'status':'passed','review_status':manifest['review_status'],'condition_count':2,'condition_slugs':[c['slug'] for c in conditions],'generated_page_count':2,'generated_pages':pages,'provider_source':PROVIDERS.relative_to(ROOT).as_posix(),'published_provider_count':sum(counts.values()),'provider_counts':counts,'hub_section_added':True,'sitemap_registered':True,'source_count':sum(len(c['sources']) for c in conditions),'source_url_override_count':manifest.get('_source_url_override_count',0),'source_url_override_source':SOURCE_OVERRIDE_FILE.relative_to(ROOT).as_posix(),'updated':UPDATED}
    (site/'api').mkdir(parents=True,exist_ok=True); (site/'api/special-needs-condition-hubs-v302.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('site',type=Path); site=ap.parse_args().site.resolve()
    if not site.is_dir(): raise SystemExit(f'Missing site: {site}')
    print(json.dumps(publish(site),ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
