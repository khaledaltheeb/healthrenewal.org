#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib, html, json, re

ROOT=Path(__file__).resolve().parents[1]
MAG=ROOT/'magazine'
TARGET=50
SITE='https://healthrenewal.org/'
BRAND='روافد'
SITE_NAME='منصة روافد'
EN='Health Renewal'
VERSION='magazine-technical-seo-v4'
REPORT=ROOT/'.seo/reports/magazine-v4-latest.json'
MANIFEST=ROOT/'.seo/manifests/magazine-v4.json'
STATE=ROOT/'.seo/state/magazine-v4.json'
NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def norm(s): return re.sub(r'\s+',' ',s or '').strip()
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def attrs(tag): return {m.group(1).lower():html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S)}
def visible(s):
    s=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',s,flags=re.I|re.S)
    return norm(html.unescape(re.sub(r'<[^>]+>',' ',s)))
def get_title(src):
    m=re.search(r'<title\b[^>]*>(.*?)</title>',src,re.I|re.S); return visible(m.group(1)) if m else ''
def get_h1(src):
    m=re.search(r'<h1\b[^>]*>(.*?)</h1>',src,re.I|re.S); return visible(m.group(1)) if m else ''
def body(src):
    m=re.search(r'<body\b',src,re.I); return src[m.start():] if m else ''
def body_hash(src): return sha(body(src))
def meta(src,kind,key):
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower(): return norm(a.get('content',''))
    return ''
def link(src,relname):
    for m in re.finditer(r'<link\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if relname.lower() in a.get('rel','').lower().split(): return norm(a.get('href',''))
    return ''
def insert_head(src,tag):
    m=re.search(r'</head\s*>',src,re.I)
    return src[:m.start()]+tag+'\n'+src[m.start():] if m else src
def set_title(src,val):
    tag='<title>'+html.escape(val)+'</title>'; m=re.search(r'<title\b[^>]*>.*?</title>',src,re.I|re.S)
    return (src[:m.start()]+tag+src[m.end():] if m else insert_head(src,tag))
def set_meta(src,kind,key,val):
    esc=html.escape(val,quote=True)
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower():
            old=m.group()
            if re.search(r'\bcontent\s*=',old,re.I):
                new=re.sub(r'(\bcontent\s*=\s*)(["\'])(.*?)\2',lambda x:x.group(1)+x.group(2)+esc+x.group(2),old,count=1,flags=re.I|re.S)
            else: new=old[:-1]+f' content="{esc}">'
            return src[:m.start()]+new+src[m.end():]
    return insert_head(src,f'<meta {kind}="{html.escape(key,quote=True)}" content="{esc}">')
def set_link(src,relname,href,hreflang=None):
    esc=html.escape(href,quote=True)
    for m in re.finditer(r'<link\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if relname.lower() in a.get('rel','').lower().split() and (hreflang is None or a.get('hreflang','').lower()==hreflang.lower()):
            old=m.group()
            if re.search(r'\bhref\s*=',old,re.I): new=re.sub(r'(\bhref\s*=\s*)(["\'])(.*?)\2',lambda x:x.group(1)+x.group(2)+esc+x.group(2),old,count=1,flags=re.I|re.S)
            else: new=old[:-1]+f' href="{esc}">'
            return src[:m.start()]+new+src[m.end():]
    extra=f' hreflang="{hreflang}"' if hreflang else ''
    return insert_head(src,f'<link rel="{relname}" href="{esc}"{extra}>')
def set_lang(src):
    m=re.search(r'<html\b[^>]*>',src,re.I|re.S)
    if not m:return src
    old=m.group()
    if re.search(r'\blang\s*=',old,re.I): new=re.sub(r'(\blang\s*=\s*)(["\'])(.*?)\2',r'\1\2ar\2',old,count=1,flags=re.I|re.S)
    else:new=old[:-1]+' lang="ar">'
    return src[:m.start()]+new+src[m.end():]
def canonical_for(p):
    q=rel(p)
    if q.endswith('/index.html'): q=q[:-10]
    return SITE+q.lstrip('/')
def first_para(src):
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>',body(src),re.I|re.S):
        t=visible(m.group(1))
        if len(t)>=80 and not t.startswith(('تنبيه','ملاحظة','إخلاء')): return t
    return ''
def trim(s,n=158):
    s=norm(s)
    if len(s)<=n:return s
    x=s[:n-1].rsplit(' ',1)[0].rstrip('،؛:.-')
    return x+'…'
def base_title(src):
    t=get_title(src) or get_h1(src)
    t=re.sub(r'\s*[|｜]\s*(?:منصة\s+)?روافد\s*$','',t,flags=re.I)
    t=re.sub(r'\s*[|｜]\s*Health\s+Renewal\s*$','',t,flags=re.I)
    return norm(t)
def headings(src):
    out=[]
    for m in re.finditer(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>',src,re.I|re.S):
        t=visible(m.group(1))
        if 5<=len(t)<=140 and t not in out and not re.match(r'^(المراجع|المصادر|المحتويات)$',t): out.append(t)
    return out[:30]
def jsonlds(src):
    out=[]
    for m in re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',src,re.I|re.S):
        try: out.append(json.loads(html.unescape(m.group(1)).strip()))
        except Exception: pass
    return out
def schema_terms(src):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ('about','keywords','name') and isinstance(v,str) and 3<=len(norm(v))<=140: out.append(norm(v))
                elif k=='about' and isinstance(v,list):
                    for z in v:
                        if isinstance(z,str): out.append(norm(z))
                        elif isinstance(z,dict) and isinstance(z.get('name'),str): out.append(norm(z['name']))
                walk(v)
        elif isinstance(x,list):
            for z in x: walk(z)
    for j in jsonlds(src): walk(j)
    seen=[]
    for x in out:
        if x and x not in seen: seen.append(x)
    return seen[:30]
def local_image_ok(url):
    if not url:return False
    if url.startswith('http://') or url.startswith('https://'):
        if not url.startswith(SITE): return True
        q=url[len(SITE):].split('?',1)[0].lstrip('/')
    else:q=url.split('?',1)[0].lstrip('/')
    return (ROOT/q).is_file()
def sitemap_urls():
    urls=set()
    for p in ROOT.glob('sitemap*.xml'):
        try:s=p.read_text(encoding='utf-8',errors='ignore')
        except Exception:continue
        for u in re.findall(r'<loc>\s*(.*?)\s*</loc>',s,re.I|re.S): urls.add(html.unescape(norm(u)))
    return urls

def build_queries(src,main):
    concepts=[]
    def addc(x):
        x=norm(x).strip(' -–—|،؛:.')
        if 4<=len(x)<=150 and x.casefold() not in {z.casefold() for z in concepts}: concepts.append(x)
    addc(main)
    for x in headings(src): addc(x)
    for x in schema_terms(src): addc(x)
    text=visible(body(src))
    year=re.search(r'\b(20(?:2[0-9]|3[0-9]))\b',text)
    if year:addc(main+' '+year.group(1))
    scientific=[]
    markers=[('تجربة عشوائية','RCT'),('تجربة سريرية','clinical trial'),('مراجعة منهجية','systematic review'),('تحليل تلوي','meta-analysis'),('دراسة أترابية','cohort'),('دراسة مقطعية','cross-sectional'),('دراسة نوعية','qualitative study'),('دراسة طولية','longitudinal study'),('DOI','DOI'),('PMID','PMID')]
    low=text.casefold()
    for ar,en in markers:
        if ar.casefold() in low or en.casefold() in low: scientific.append(ar)
    for x in scientific:addc(main+' '+x)
    concepts=concepts[:28]
    frames=[
      '{}','دراسة {}','بحث عن {}','أبحاث {}','الدليل العلمي حول {}','ملخص {}','شرح {}','شرح عربي لـ {}',
      'نتائج {}','نتائج دراسة {}','ماذا وجدت دراسة {}','ما نتائج {}','ما الذي وجدته الأبحاث عن {}','هل يدعم الدليل {}',
      'تصميم دراسة {}','منهجية دراسة {}','منهجية البحث في {}','حجم العينة في {}','عينة دراسة {}','المتابعة في دراسة {}',
      'النتيجة الرئيسية في {}','النتائج الثانوية في {}','حجم الأثر في {}','الدلالة الإحصائية في {}','تفسير نتائج {}',
      'جودة الدليل حول {}','قوة الدليل حول {}','حدود دراسة {}','قيود دراسة {}','احتمال التحيز في {}','قابلية تعميم نتائج {}',
      'التطبيق العملي لنتائج {}','مقارنة نتائج {}','المصدر الأصلي لـ {}','DOI دراسة {}','PMID دراسة {}','دراسة {} بالعربي',
      'أحدث أبحاث {}','أحدث دراسة عن {}','أسئلة عن دراسة {}','أسئلة شائعة عن {}','كيف صممت دراسة {}','كيف نفسر دراسة {}',
      'هل نتائج {} موثوقة','ما حدود الدليل في {}','ما أهمية {}','روافد {}','{} روافد','Health Renewal {}','{} Health Renewal',
      'مجلة روافد {}','المجلة والأبحاث {}','مرجع عربي عن {}','مصادر علمية عن {}','ورقة علمية عن {}','دراسة علمية عن {}'
    ]
    out=[]; seen=set()
    for c in concepts:
        for f in frames:
            q=norm(f.format(c)).strip(' -–—|،؛:.')
            k=q.casefold()
            if 4<=len(q)<=190 and k not in seen:
                seen.add(k);out.append(q)
    # Page-specific paired concepts are still grounded in visible headings/schema.
    mainc=concepts[0] if concepts else main
    for c in concepts[1:]:
        for f in ('{} و{}','نتائج {} في سياق {}','الدليل حول {} وعلاقته بـ {}','مقارنة {} و{}','أسئلة البحث حول {} و{}','تطبيق نتائج {} على {}'):
            q=norm(f.format(mainc,c)).strip(' -–—|،؛:.');k=q.casefold()
            if 4<=len(q)<=190 and k not in seen:seen.add(k);out.append(q)
    return out[:800]

def supported_faq_nodes(src):
    txt=visible(body(src)).casefold(); valid=[]
    for j in jsonlds(src):
        nodes=[]
        if isinstance(j,dict) and isinstance(j.get('@graph'),list):nodes+=j['@graph']
        elif isinstance(j,dict):nodes.append(j)
        for n in nodes:
            if isinstance(n,dict) and n.get('@type')=='FAQPage':
                qs=[]
                for e in n.get('mainEntity',[]):
                    if isinstance(e,dict) and isinstance(e.get('name'),str):qs.append(norm(e['name']))
                if qs and all(q.casefold() in txt for q in qs):valid.append(n)
    return valid

def seo_schema_block(src,canonical,title,desc):
    faq=supported_faq_nodes(src)
    article_type='Article'
    existing=jsonlds(src)
    for j in existing:
        dump=json.dumps(j,ensure_ascii=False)
        if 'ScholarlyArticle' in dump: article_type='ScholarlyArticle';break
        if 'MedicalWebPage' in dump: article_type='MedicalWebPage'
    graph=[
      {'@type':'Organization','@id':SITE+'#organization','name':SITE_NAME,'alternateName':EN,'url':SITE,'logo':{'@type':'ImageObject','url':SITE+'assets/brand/rawafid-logo.png'}},
      {'@type':'WebSite','@id':SITE+'#website','url':SITE,'name':SITE_NAME,'alternateName':EN,'inLanguage':'ar','publisher':{'@id':SITE+'#organization'}},
      {'@type':'CollectionPage','@id':SITE+'magazine/#collection','url':SITE+'magazine/','name':'المجلة والأبحاث | روافد','isPartOf':{'@id':SITE+'#website'},'inLanguage':'ar'},
      {'@type':'WebPage','@id':canonical+'#webpage','url':canonical,'name':title,'description':desc,'inLanguage':'ar','isPartOf':{'@id':SITE+'#website'},'about':{'@id':canonical+'#article'}},
      {'@type':article_type,'@id':canonical+'#article','url':canonical,'headline':base_title(src),'description':desc,'mainEntityOfPage':{'@id':canonical+'#webpage'},'isPartOf':{'@id':SITE+'magazine/#collection'},'publisher':{'@id':SITE+'#organization'},'inLanguage':'ar'}
    ]
    # Preserve only factual existing publication dates if present.
    for j in existing:
        nodes=j.get('@graph',[]) if isinstance(j,dict) else []
        if isinstance(j,dict):nodes=[j]+(nodes if isinstance(nodes,list) else [])
        for n in nodes:
            if isinstance(n,dict) and n.get('@type') in ('Article','ScholarlyArticle'):
                for k in ('datePublished','dateModified'):
                    if isinstance(n.get(k),str) and n[k]: graph[-1][k]=n[k]
                break
    if faq:
        # FAQ stays in its original validated JSON-LD; do not duplicate or invent it.
        pass
    data=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False,separators=(',',':'))
    block='<script type="application/ld+json" id="rawafid-magazine-seo-v4">'+data+'</script>'
    m=re.search(r'<script\b[^>]*id=["\']rawafid-magazine-seo-v4["\'][^>]*>.*?</script>',src,re.I|re.S)
    return src[:m.start()]+block+src[m.end():] if m else insert_head(src,block)

def verify(src,p,canonical,title,desc,surls,queries):
    errs=[]
    if get_title(src)!=title:errs.append('title')
    if meta(src,'name','description')!=desc:errs.append('description')
    if link(src,'canonical')!=canonical:errs.append('canonical')
    r=meta(src,'name','robots').lower()
    if 'index' not in r or 'follow' not in r or 'noindex' in r or 'nofollow' in r:errs.append('robots')
    if 'max-snippet:-1' not in r or 'max-image-preview:large' not in r or 'max-video-preview:-1' not in r:errs.append('robots-preview')
    if meta(src,'property','og:title')!=title or meta(src,'name','twitter:title')!=title:errs.append('social-title')
    if meta(src,'property','og:description')!=desc or meta(src,'name','twitter:description')!=desc:errs.append('social-desc')
    if meta(src,'property','og:url')!=canonical:errs.append('og-url')
    if meta(src,'property','og:type')!='article':errs.append('og-type')
    if meta(src,'property','og:site_name')!=SITE_NAME or meta(src,'property','og:locale')!='ar_AR':errs.append('locale')
    if meta(src,'name','twitter:card')!='summary_large_image':errs.append('twitter-card')
    hm=re.search(r'<html\b[^>]*>',src,re.I|re.S)
    if not hm or attrs(hm.group()).get('lang','').lower()!='ar':errs.append('lang')
    if canonical not in surls:errs.append('sitemap')
    if len(queries)<500:errs.append('semantic-map')
    found=False
    for m in re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',src,re.I|re.S):
        try: json.loads(html.unescape(m.group(1)).strip());found=True
        except Exception: errs.append('json-ld-invalid')
    if not found:errs.append('json-ld-missing')
    return errs

def optimize(src,p,surls):
    canonical=canonical_for(p); main=base_title(src)
    if not main:return None,'missing-title'
    olddesc=meta(src,'name','description')
    desc=olddesc if len(olddesc)>=60 else trim(first_para(src))
    if len(desc)<60:return None,'missing-description-source'
    title=get_title(src)
    newtitle=title if re.search(r'(^|[|｜]\s*)(?:منصة\s+)?روافد\s*$',title,re.I) else main+' | روافد'
    queries=build_queries(src,main)
    if len(queries)<500:return None,'semantic-map-under-500'
    if canonical not in surls:return None,'not-in-sitemap'
    out=set_lang(src)
    out=set_title(out,newtitle)
    out=set_meta(out,'name','description',desc)
    out=set_link(out,'canonical',canonical)
    out=set_meta(out,'name','robots','index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1')
    out=set_meta(out,'property','og:type','article')
    out=set_meta(out,'property','og:title',newtitle)
    out=set_meta(out,'property','og:description',desc)
    out=set_meta(out,'property','og:url',canonical)
    out=set_meta(out,'property','og:site_name',SITE_NAME)
    out=set_meta(out,'property','og:locale','ar_AR')
    oi=meta(src,'property','og:image')
    ti=meta(src,'name','twitter:image')
    img=oi if local_image_ok(oi) else (ti if local_image_ok(ti) else SITE+'assets/brand/rawafid-social-card.jpg')
    out=set_meta(out,'property','og:image',img)
    out=set_meta(out,'name','twitter:card','summary_large_image')
    out=set_meta(out,'name','twitter:title',newtitle)
    out=set_meta(out,'name','twitter:description',desc)
    out=set_meta(out,'name','twitter:image',img)
    # Preserve existing hreflang; do not invent foreign alternates. If an Arabic alternate already exists, align it to canonical.
    if re.search(r'<link\b[^>]*hreflang=["\']ar["\']',out,re.I): out=set_link(out,'alternate',canonical,'ar')
    out=seo_schema_block(out,canonical,newtitle,desc)
    errs=verify(out,p,canonical,newtitle,desc,surls,queries)
    if body_hash(src)!=body_hash(out):errs.append('body-changed')
    if errs:return None,'verify:'+','.join(sorted(set(errs)))
    changes=[]
    pairs=[('title',get_title(src),get_title(out)),('description',meta(src,'name','description'),meta(out,'name','description')),('canonical',link(src,'canonical'),link(out,'canonical')),('robots',meta(src,'name','robots'),meta(out,'name','robots')),('og-twitter',meta(src,'property','og:title')+'|'+meta(src,'name','twitter:title'),meta(out,'property','og:title')+'|'+meta(out,'name','twitter:title')),('schema','rawafid-magazine-seo-v4' in src,'rawafid-magazine-seo-v4' in out)]
    for k,a,b in pairs:
        if a!=b:changes.append(k)
    if out==src:return None,'already-optimal'
    if not changes:changes=['metadata-normalization']
    return {'out':out,'canonical':canonical,'title':newtitle,'description':desc,'main':main,'queries':queries,'changes':changes},None

def main():
    surls=sitemap_urls(); pages=sorted([p for p in MAG.rglob('*.html') if p.is_file()]) if MAG.is_dir() else []
    # pre-scan existing title/desc duplicates to avoid worsening cannibalization
    titles=Counter(); descs=Counter()
    for p in pages:
        try:s=p.read_text(encoding='utf-8')
        except Exception:continue
        if get_title(s):titles[get_title(s).casefold()]+=1
        d=meta(s,'name','description')
        if d:descs[d.casefold()]+=1
    candidates=[]; failures=[]; skipped=[]; primary_seen=set(); planned_titles=set(); planned_descs=set()
    for p in pages:
        rp=rel(p)
        try:src=p.read_text(encoding='utf-8')
        except Exception as e:failures.append({'path':rp,'reason':'read:'+type(e).__name__});continue
        if '<head' not in src.lower() or '<body' not in src.lower():skipped.append({'path':rp,'reason':'non-document'});continue
        # Research/article intent gate: article element, research schema, DOI/PMID, or study/research terms.
        vt=visible(body(src))[:10000].casefold()
        if not ('<article' in src.lower() or any(x in src for x in ('ScholarlyArticle','"Article"','MedicalWebPage')) or any(x in vt for x in ('دراسة','بحث','doi','pmid','تجربة','مراجعة منهجية','ورقة علمية'))):
            skipped.append({'path':rp,'reason':'non-research-page'});continue
        opt,reason=optimize(src,p,surls)
        if not opt:
            (skipped if reason=='already-optimal' else failures).append({'path':rp,'reason':reason});continue
        pi=norm(opt['main']).casefold()
        if pi in primary_seen:skipped.append({'path':rp,'reason':'primary-intent-collision'});continue
        nt=opt['title'].casefold();nd=opt['description'].casefold()
        if nt in planned_titles or nd in planned_descs:skipped.append({'path':rp,'reason':'planned-metadata-duplicate'});continue
        # If an unchanged description is already duplicated elsewhere, do not count this page.
        oldd=meta(src,'name','description')
        if oldd==opt['description'] and descs[oldd.casefold()]>1:skipped.append({'path':rp,'reason':'existing-description-duplicate'});continue
        primary_seen.add(pi);planned_titles.add(nt);planned_descs.add(nd)
        candidates.append((p,src,opt))
    selected=candidates[:TARGET]
    success=[]; manifest_pages={}; state_pages={}
    for p,src,opt in selected:
        p.write_text(opt['out'],encoding='utf-8')
        rp=rel(p); outsha=sha(opt['out']); qsha=sha('\n'.join(opt['queries']))
        success.append({'path':rp,'canonical':opt['canonical'],'title':opt['title'],'changes':opt['changes'],'query_count':len(opt['queries']),'source_sha256':sha(src),'output_sha256':outsha})
        manifest_pages[rp]={'primary_intent':opt['main'],'query_count':len(opt['queries']),'queries':opt['queries'],'query_sha256':qsha,'canonical':opt['canonical']}
        state_pages[rp]={'version':VERSION,'optimized_at':NOW,'source_sha256':sha(src),'output_sha256':outsha,'primary_intent':opt['main'],'manifest_sha256':qsha,'status':'verified-success'}
    REPORT.parent.mkdir(parents=True,exist_ok=True);MANIFEST.parent.mkdir(parents=True,exist_ok=True);STATE.parent.mkdir(parents=True,exist_ok=True)
    report={'version':VERSION,'generated_at':NOW,'target':TARGET,'candidate_pages':len(pages),'material_verified_candidates':len(candidates),'success':len(success),'skipped_noop':len(skipped),'failed':len(failures),'eligible_remaining':max(0,len(candidates)-len(selected)),'round_complete':len(success)>=TARGET,'changed_pages':success,'skipped':skipped,'failures':failures,'change_totals':dict(Counter(x for r in success for x in r['changes'])),'verification':{'visible_body_unchanged':all(body_hash(src)==body_hash(opt['out']) for p,src,opt in selected),'semantic_queries_per_success_min':min([len(opt['queries']) for p,src,opt in selected],default=0),'canonical_self_checked':True,'robots_indexability_checked':True,'og_twitter_consistency_checked':True,'json_ld_validated':True,'locale_lang_checked':True,'sitemap_inclusion_checked':True,'title_description_uniqueness_checked':True,'primary_intent_cannibalization_checked':True}}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    MANIFEST.write_text(json.dumps({'version':VERSION,'generated_at':NOW,'pages':manifest_pages},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    STATE.write_text(json.dumps({'version':VERSION,'updated_at':NOW,'pages':state_pages},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'target':TARGET,'success':len(success),'skipped_noop':len(skipped),'failed':len(failures),'eligible_remaining':report['eligible_remaining'],'round_complete':report['round_complete']},ensure_ascii=False))
    if len(success)<TARGET: raise SystemExit(2)

if __name__=='__main__': main()
