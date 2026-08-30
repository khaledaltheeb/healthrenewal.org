#!/usr/bin/env python3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import hashlib, html, json, re

ROOT=Path(__file__).resolve().parents[2]; SCOPE=ROOT/'care-guides'; TARGET=50
SITE='https://healthrenewal.org/'; BRAND='منصة روافد'; SHORT='روافد'; EN='Health Renewal'
IMAGE=SITE+'assets/brand/rawafid-social-card.jpg'
STATE=ROOT/'.github/seo/care-guides-seo-state.json'; MANIFEST=ROOT/'.github/seo/care-guides-semantic-manifest.json'; REPORT=ROOT/'.github/reports/seo-care-guides-latest.json'
NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
MINQ=500; MAXSEED=100; WORKERS=24; TIMEOUT=4
AR_HINT=['ما هو','كيف','دليل','تقييم','تشخيص','علاج','أعراض','أسباب','الفرق بين','للأطفال','للبالغين','للأسرة','أسئلة','متى','لماذا']
EN_HINT=['what is','how to','guide','assessment','diagnosis','treatment','symptoms','causes','screening','children','adults','family','questions','when','why']
AR_LET=list('ابتثجحخدذرزسشصضطظعغفقكلمنهوي'); EN_LET=list('abcdefghijklmnopqrstuvwxyz')
STOP={'من','في','على','إلى','الى','عن','مع','ما','هو','هي','كيف','دليل','the','and','for','with','what','how','guide','of','to','a','an'}
MARK='rawafid:care-guides-seo:v2'

def norm(x): return re.sub(r'\s+',' ',x or '').strip()
def hsh(x): return hashlib.sha256(x.encode()).hexdigest()
def rp(p): return p.relative_to(ROOT).as_posix()
def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d
def save(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def vis(x): return norm(html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<(?:script|style|noscript)\b[^>]*>.*?</(?:script|style|noscript)>',' ',x,flags=re.I|re.S))))
def at(tag): return {m.group(1).lower():html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*([\"\'])(.*?)\2',tag,re.S)}
def title(s):
    m=re.search(r'<title\b[^>]*>(.*?)</title>',s,re.I|re.S); return vis(m.group(1)) if m else ''
def h1(s):
    m=re.search(r'<h1\b[^>]*>(.*?)</h1>',s,re.I|re.S); return vis(m.group(1)) if m else ''
def meta(s,k,n):
    for m in re.finditer(r'<meta\b[^>]*>',s,re.I|re.S):
        a=at(m.group())
        if a.get(k,'').lower()==n.lower(): return norm(a.get('content',''))
    return ''
def link(s,n):
    for m in re.finditer(r'<link\b[^>]*>',s,re.I|re.S):
        a=at(m.group())
        if n.lower() in a.get('rel','').lower().split(): return norm(a.get('href',''))
    return ''
def body(s):
    m=re.search(r'<body\b',s,re.I); return s[m.start():] if m else ''
def bh(s): return hsh(body(s))
def url(p):
    x=rp(p); x=x[:-10] if x.endswith('index.html') else x; return SITE+x.lstrip('/')
def core(s):
    t=title(s) or h1(s) or 'دليل رعاية'; t=re.sub(r'\s*[|｜-]\s*(?:منصة\s+)?روافد.*$','',t,flags=re.I); t=re.sub(r'\s*[|｜-]\s*Health\s+Renewal.*$','',t,flags=re.I); return norm(t)
def desc_from(s):
    main=re.search(r'<main\b[^>]*>(.*?)</main>',body(s),re.I|re.S); scope=main.group(1) if main else body(s)
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>',scope,re.I|re.S):
        t=vis(m.group(1))
        if 80<=len(t)<=600:return trim(t)
    return trim(h1(s) or core(s))
def trim(x,n=158):
    x=norm(x)
    if len(x)<=n:return x
    y=x[:n-1]; y=y.rsplit(' ',1)[0] if ' ' in y else y; return y.rstrip('،؛:.-')+'…'
def jsonld(s):
    types=set()
    for i,m in enumerate(re.finditer(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>',s,re.I|re.S),1):
        try:d=json.loads(html.unescape(m.group(1)).strip())
        except Exception as e:return False,f'json-ld-{i}:{e}',types
        q=[d]
        while q:
            x=q.pop()
            if isinstance(x,dict):
                t=x.get('@type'); types.update([t] if isinstance(t,str) else [str(v) for v in t] if isinstance(t,list) else []); q.extend(x.values())
            elif isinstance(x,list):q.extend(x)
    return True,'',types
def sitemap():
    out=set()
    for p in ROOT.glob('sitemap*.xml'):
        try:t=p.read_text(encoding='utf-8',errors='ignore')
        except:continue
        out.update(html.unescape(norm(m.group(1))).rstrip('/') for m in re.finditer(r'<loc>\s*(.*?)\s*</loc>',t,re.I|re.S))
    return out
def indexable(s):
    r=meta(s,'name','robots').lower(); return 'noindex' not in r and 'nofollow' not in r
def goodcan(x,e):
    try:u=urlparse(x); return u.scheme in ('http','https') and u.netloc=='healthrenewal.org' and x.rstrip('/')==e.rstrip('/')
    except:return False

def replace_attr(tag,name,val):
    esc=html.escape(val,quote=True)
    if re.search(r'\b'+re.escape(name)+r'\s*=',tag,re.I):
        return re.sub(r'(\b'+re.escape(name)+r'\s*=\s*)([\"\'])(.*?)\2',lambda m:m.group(1)+m.group(2)+esc+m.group(2),tag,count=1,flags=re.I|re.S)
    return tag[:-1]+f' {name}="{esc}">'
def insert_head(s,x):
    m=re.search(r'</head\s*>',s,re.I); return s[:m.start()]+x+'\n'+s[m.start():] if m else s
def set_title(s,v):
    tag='<title>'+html.escape(v)+'</title>'; m=re.search(r'<title\b[^>]*>.*?</title>',s,re.I|re.S)
    if not m:return insert_head(s,tag),True
    if m.group()==tag:return s,False
    return s[:m.start()]+tag+s[m.end():],True
def set_meta(s,k,n,v,replace=False):
    for m in re.finditer(r'<meta\b[^>]*>',s,re.I|re.S):
        a=at(m.group())
        if a.get(k,'').lower()==n.lower():
            if not replace:return s,False
            new=replace_attr(m.group(),'content',v); return s[:m.start()]+new+s[m.end():],new!=m.group()
    return insert_head(s,f'<meta {k}="{html.escape(n,quote=True)}" content="{html.escape(v,quote=True)}">'),True
def set_can(s,v):
    for m in re.finditer(r'<link\b[^>]*>',s,re.I|re.S):
        if 'canonical' in at(m.group()).get('rel','').lower().split():
            new=replace_attr(m.group(),'href',v); return s[:m.start()]+new+s[m.end():],new!=m.group()
    return insert_head(s,f'<link rel="canonical" href="{html.escape(v,quote=True)}">'),True
def set_lang(s):
    m=re.search(r'<html\b[^>]*>',s,re.I|re.S)
    if not m:return s,False
    if at(m.group()).get('lang','').lower().startswith('ar'):return s,False
    new=replace_attr(m.group(),'lang','ar'); return s[:m.start()]+new+s[m.end():],new!=m.group()
def core_title(t):
    return norm(re.sub(r'\s*[|｜-]\s*(?:منصة\s+)?روافد.*$','',re.sub(r'\s*[|｜-]\s*Health\s+Renewal.*$','',t,flags=re.I),flags=re.I))
def schema_block(can,t,d,types):
    g=[]
    if 'Organization' not in types:g.append({'@type':'Organization','@id':SITE+'#organization','name':BRAND,'alternateName':EN,'url':SITE})
    if 'WebSite' not in types:g.append({'@type':'WebSite','@id':SITE+'#website','name':BRAND,'alternateName':EN,'url':SITE,'inLanguage':'ar'})
    if not ({'WebPage','MedicalWebPage','Article'}&types):g.append({'@type':'WebPage','@id':can+'#webpage','url':can,'name':t,'description':d,'inLanguage':'ar'})
    if 'BreadcrumbList' not in types:
        parts=can.replace(SITE,'').strip('/').split('/'); items=[{'@type':'ListItem','position':1,'name':'الرئيسية','item':SITE}]; cur=SITE
        for i,x in enumerate(parts[:-1],2):cur+=x+'/'; items.append({'@type':'ListItem','position':i,'name':{'care-guides':'أدلة الرعاية','clinical-literacy':'الفهم السريري','aac':'التواصل المعزز والبديل'}.get(x,x.replace('-',' ')),'item':cur})
        items.append({'@type':'ListItem','position':len(items)+1,'name':core_title(t),'item':can}); g.append({'@type':'BreadcrumbList','@id':can+'#breadcrumb','itemListElement':items})
    if not g:return ''
    return f'<!-- {MARK} -->\n<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':g},ensure_ascii=False,separators=(',',':'))+f'</script>\n<!-- /{MARK} -->'

def defects(s,p,sm,tc,dc):
    o=[]; t=title(s); d=meta(s,'name','description'); can=url(p)
    if not t or tc[t]>1 or (SHORT not in t and EN.lower() not in t.lower()):o.append('title')
    if not d or dc[d]>1 or len(d)<70:o.append('description')
    if not goodcan(link(s,'canonical'),can):o.append('canonical')
    if not meta(s,'name','robots'):o.append('robots')
    if can.rstrip('/') not in sm:o.append('sitemap')
    req=[('property','og:type'),('property','og:locale'),('property','og:site_name'),('property','og:title'),('property','og:description'),('property','og:url'),('property','og:image'),('name','twitter:card'),('name','twitter:title'),('name','twitter:description'),('name','twitter:image')]
    if any(not meta(s,k,n) for k,n in req):o.append('social')
    ok,_,ty=jsonld(s)
    if not ok:o.append('invalid-jsonld')
    elif 'Organization' not in ty or 'WebSite' not in ty or 'BreadcrumbList' not in ty or not ({'WebPage','MedicalWebPage','Article'}&ty):o.append('schema')
    m=re.search(r'<html\b[^>]*>',s,re.I|re.S)
    if not m or not at(m.group()).get('lang','').lower().startswith('ar'):o.append('lang')
    return sorted(set(o))

def enhance(s,p,tc,dc):
    old=body(s); ch=[]; can=url(p); t=title(s); nt=t if t and (SHORT in t or EN.lower() in t.lower()) else core(s)+' | '+BRAND
    if not t or tc[t]>1 or nt!=t:s,c=set_title(s,nt); ch+=['title'] if c else []
    d=meta(s,'name','description')
    if not d or dc[d]>1 or len(d)<70:
        nd=desc_from(s)
        if len(nd)>=40:s,c=set_meta(s,'name','description',nd,True); ch+=['description'] if c else []; d=nd
    if not goodcan(link(s,'canonical'),can):s,c=set_can(s,can); ch+=['canonical'] if c else []
    r=meta(s,'name','robots')
    if not r:s,c=set_meta(s,'name','robots','index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1'); ch+=['robots'] if c else []
    elif 'noindex' not in r.lower() and 'max-image-preview' not in r.lower():s,c=set_meta(s,'name','robots',r+',max-image-preview:large',True); ch+=['robots'] if c else []
    s,c=set_lang(s); ch+=['lang'] if c else []
    d=meta(s,'name','description') or desc_from(s); t=title(s)
    socials=[('property','og:type','article'),('property','og:locale','ar_AR'),('property','og:site_name',BRAND),('property','og:title',t),('property','og:description',d),('property','og:url',can),('property','og:image',IMAGE),('property','og:image:alt',core(s)),('name','twitter:card','summary_large_image'),('name','twitter:title',t),('name','twitter:description',d),('name','twitter:image',IMAGE),('name','twitter:image:alt',core(s))]
    sc=False
    for k,n,v in socials:
        x=meta(s,k,n); rep=n in {'og:locale','og:site_name','og:title','og:description','og:url','twitter:title','twitter:description'}
        if not x or (rep and x!=v):s,c=set_meta(s,k,n,v,bool(x)); sc|=c
    if sc:ch.append('og-twitter')
    ok,e,ty=jsonld(s)
    if not ok:return s,ch,e
    b=schema_block(can,t,d,ty)
    if b:
        m=re.search(r'<!-- '+re.escape(MARK)+r' -->.*?<!-- /'+re.escape(MARK)+r' -->',s,re.S)
        s=s[:m.start()]+b+s[m.end():] if m else insert_head(s,b); ch.append('schema')
    if body(s)!=old:return s,ch,'visible-body-changed'
    ok,e,_=jsonld(s); return (s,sorted(set(ch)),'' if ok else e)

def topics(s,p):
    raw=[h1(s),core(s),p.parent.name.replace('-',' ')]
    for m in re.finditer(r'<h[2-3]\b[^>]*>(.*?)</h[2-3]>',body(s),re.I|re.S):raw.append(vis(m.group(1)))
    out=[]
    for x in raw:
        x=norm(x)
        if x and x.casefold() not in {v.casefold() for v in out}:out.append(' '.join(x.split()[:10]))
    return out[:8]
def anchors(s,p):
    a=set()
    for x in topics(s,p):
        for z in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}',x):
            if z.casefold() not in STOP and len(z)>=3:a.add(z.casefold())
    return a
def seeds(s,p):
    ts=topics(s,p); out=[]
    for t in ts[:4]:
        latin=bool(re.search(r'[A-Za-z]',t)) and not re.search(r'[\u0600-\u06FF]',t); hs=EN_HINT if latin else AR_HINT; ls=EN_LET if latin else AR_LET
        out+=[t]+[f'{h} {t}' for h in hs]+[f'{t} {c}' for c in ls]
    seen=[]; keys=set()
    for x in out:
        x=norm(x); k=x.casefold()
        if x and k not in keys:keys.add(k); seen.append(x)
        if len(seen)>=MAXSEED:break
    return seen
def google(q):
    req=Request('https://suggestqueries.google.com/complete/search?client=firefox&hl=ar&q='+quote(q),headers={'User-Agent':'Mozilla/5.0 RawafidSEO/2.0'})
    with urlopen(req,timeout=TIMEOUT) as r:d=json.loads(r.read().decode('utf-8','replace'))
    return [norm(str(x)) for x in d[1]] if isinstance(d,list) and len(d)>1 and isinstance(d[1],list) else []
def ddg(q):
    req=Request('https://duckduckgo.com/ac/?q='+quote(q)+'&type=list',headers={'User-Agent':'Mozilla/5.0 RawafidSEO/2.0'})
    with urlopen(req,timeout=TIMEOUT) as r:d=json.loads(r.read().decode('utf-8','replace'))
    return [norm(str(x.get('phrase',''))) for x in d if isinstance(x,dict) and norm(str(x.get('phrase','')))] if isinstance(d,list) else []
def related(q,a):
    toks={z.casefold() for z in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}',q)}; return bool(toks&a)
def collect(s,p):
    ss=seeds(s,p); a=anchors(s,p); by={}; err=Counter(); jobs=[]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for seed in ss:jobs += [(ex.submit(fn,seed),name) for name,fn in [('google_autocomplete',google),('duckduckgo_autocomplete',ddg)]]
        for f,name in jobs:
            try:vals=f.result()
            except Exception as e:err[name+':'+type(e).__name__]+=1; continue
            for q in vals:
                if not related(q,a):continue
                k=q.casefold(); by.setdefault(k,{'phrase':q,'sources':[]})
                if name not in by[k]['sources']:by[k]['sources'].append(name)
    rows=list(by.values()); rows.sort(key=lambda x:(len(x['sources']),len(x['phrase']),x['phrase']),reverse=True)
    ev={'captured_at':NOW,'policy':'Only phrases actually returned by live public autocomplete endpoints count. Generated seeds never count. Results are filtered for topical overlap.','queried_seed_count':len(ss),'sources':['Google Autocomplete','DuckDuckGo Autocomplete'],'errors':dict(err),'real_relevant_suggestion_count':len(rows),'brand_combinations_not_counted':[core(s)+' '+SHORT,core(s)+' '+EN]}
    return rows[:MINQ],ev

def checks(s,p,sm,q):
    t=title(s); d=meta(s,'name','description'); can=url(p); ok,e,ty=jsonld(s)
    return {'title_present':bool(t),'description_present':len(d)>=40,'canonical_exact':goodcan(link(s,'canonical'),can),'indexable':indexable(s),'sitemap_included':can.rstrip('/') in sm,'jsonld_valid':ok,'schema_supported':bool({'WebPage','MedicalWebPage','Article'}&ty) and 'BreadcrumbList' in ty,'og_consistent':meta(s,'property','og:title')==t and meta(s,'property','og:description')==d and meta(s,'property','og:url').rstrip('/')==can.rstrip('/') and bool(meta(s,'property','og:image')),'twitter_consistent':meta(s,'name','twitter:title')==t and meta(s,'name','twitter:description')==d and bool(meta(s,'name','twitter:image')),'locale_ar':meta(s,'property','og:locale')=='ar_AR','real_query_count':len(q)>=MINQ}
def fingerprint(s,q):return hsh(json.dumps({'title':title(s),'description':meta(s,'name','description'),'canonical':link(s,'canonical'),'robots':meta(s,'name','robots'),'og':meta(s,'property','og:title'),'twitter':meta(s,'name','twitter:title'),'queries':hsh('\n'.join(x['phrase'] for x in q))},ensure_ascii=False,sort_keys=True))

def main():
    if not SCOPE.exists():return 2
    pages=sorted(p for p in SCOPE.rglob('index.html') if p.parent!=SCOPE); sm=sitemap(); docs={}; tc=Counter(); dc=Counter()
    for p in pages:
        try:s=p.read_text(encoding='utf-8')
        except:continue
        docs[p]=s; tc[title(s)]+=bool(title(s)); dc[meta(s,'name','description')]+=bool(meta(s,'name','description'))
    state=load(STATE,{'version':2,'pages':{}}); man=load(MANIFEST,{'version':2,'source_policy':'live-autocomplete-only','pages':{}}); suc=[]; skip=[]; fail=[]; srcerr=Counter(); cand=[]
    for p,s in docs.items():
        ds=defects(s,p,sm,tc,dc)
        if not indexable(s):skip.append({'path':rp(p),'reason':'existing-noindex-or-nofollow'});continue
        if url(p).rstrip('/') not in sm:skip.append({'path':rp(p),'reason':'not-in-sitemap'});continue
        if not ds:skip.append({'path':rp(p),'reason':'no-material-seo-defect'});continue
        if 'invalid-jsonld' in ds:fail.append({'path':rp(p),'reason':'existing-invalid-jsonld'});continue
        cand.append((len(ds),rp(p),p,s))
    cand.sort(key=lambda x:(-x[0],x[1])); intents=set(); qsets=[]
    for _,_,p,s in cand:
        if len(suc)>=TARGET:break
        intent=norm(h1(s) or core(s)).casefold()
        if not intent or intent in intents:skip.append({'path':rp(p),'reason':'duplicate-primary-intent'});continue
        q,ev=collect(s,p); srcerr.update(ev['errors'])
        if len(q)<MINQ:skip.append({'path':rp(p),'reason':'insufficient-live-demand-evidence','real_suggestions':ev['real_relevant_suggestion_count']});continue
        qs={x['phrase'].casefold() for x in q}
        if any(len(qs&z)/max(1,len(qs|z))>=.65 for z in qsets):skip.append({'path':rp(p),'reason':'query-cannibalization-risk'});continue
        oldh=bh(s); ns,ch,e=enhance(s,p,tc,dc)
        if e:fail.append({'path':rp(p),'reason':e});continue
        if not ch or ns==s:skip.append({'path':rp(p),'reason':'no-op-after-analysis'});continue
        if bh(ns)!=oldh:fail.append({'path':rp(p),'reason':'body-hash-changed'});continue
        ck=checks(ns,p,sm,q); ck['visible_body_unchanged']=bh(ns)==oldh
        if not all(ck.values()):fail.append({'path':rp(p),'reason':'verification-failed','checks':ck});continue
        p.write_text(ns,encoding='utf-8'); rr=p.read_text(encoding='utf-8')
        if rr!=ns or bh(rr)!=oldh:p.write_text(s,encoding='utf-8');fail.append({'path':rp(p),'reason':'save-verification-failed'});continue
        fp=fingerprint(ns,q); man['pages'][rp(p)]={'canonical':url(p),'primary_intent':h1(s) or core(s),'fingerprint':fp,'updated_at':NOW,'real_search_phrases':q,'evidence':ev,'brand_combinations':[core(s)+' '+SHORT,core(s)+' '+EN]}; state['pages'][rp(p)]={'fingerprint':fp,'body_hash':oldh,'last_success_at':NOW,'changes':ch}; suc.append({'path':rp(p),'canonical':url(p),'changes':ch,'real_search_phrases':len(q),'checks':ck}); intents.add(intent); qsets.append(qs)
    ft=Counter(); fd=Counter()
    for p in pages:
        try:s=p.read_text(encoding='utf-8')
        except:continue
        if title(s):ft[title(s)]+=1
        if meta(s,'name','description'):fd[meta(s,'name','description')]+=1
    keep=[]; dup=[]
    for x in suc:
        p=ROOT/x['path']; s=p.read_text(encoding='utf-8')
        if ft[title(s)]>1 or fd[meta(s,'name','description')]>1:
            p.write_text(docs[p],encoding='utf-8'); dup.append(x['path']); fail.append({'path':x['path'],'reason':'post-round-title-or-description-duplicate'}); state['pages'].pop(x['path'],None); man['pages'].pop(x['path'],None)
        else:keep.append(x)
    suc=keep; complete=len(suc)>=TARGET; rep={'round':'care-guides-technical-seo','generated_at':NOW,'target':TARGET,'success':len(suc),'skipped_noop_or_ineligible':len(skip),'failed':len(fail),'eligible_candidates_before_round':len(cand),'eligible_remaining_estimate':max(0,len(cand)-len(suc)),'complete':complete,'successes':suc,'skipped':skip,'failures':fail,'source_failures':dict(srcerr),'verification':{'visible_body_unchanged':all(x['checks']['visible_body_unchanged'] for x in suc) if suc else True,'json_ld_validated':all(x['checks']['jsonld_valid'] for x in suc) if suc else True,'semantic_queries_per_success':min((x['real_search_phrases'] for x in suc),default=0),'autocomplete_only_counting':True,'generated_seeds_count_toward_500':False,'topical_filter_applied':True,'sitemap_required_for_success':True,'noindex_pages_modified':False,'title_description_unique_for_successes':not dup},'blocker':None if complete else 'Fewer than 50 care-guide pages passed the live autocomplete-demand and technical verification gates.'}
    state['updated_at']=NOW; man['updated_at']=NOW; save(STATE,state); save(MANIFEST,man); save(REPORT,rep); print(json.dumps({'success':len(suc),'skipped':len(skip),'failed':len(fail),'complete':complete},ensure_ascii=False)); return 0 if complete else 3
if __name__=='__main__':raise SystemExit(main())
