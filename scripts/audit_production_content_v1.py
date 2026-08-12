#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

BASE='https://healthrenewal.org'
TITLE_RE=re.compile(r'<title\b[^>]*>(.*?)</title>',re.I|re.S)
DESC_RE=re.compile(r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*\bcontent=["\']([^"\']*)["\'][^>]*>',re.I|re.S)
H1_RE=re.compile(r'<h1\b[^>]*>(.*?)</h1>',re.I|re.S)
CAN_RE=re.compile(r'<link\b(?=[^>]*\brel=["\'][^"\']*canonical[^"\']*["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',re.I|re.S)
ROB_RE=re.compile(r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*\bcontent=["\']([^"\']*)["\'][^>]*>',re.I|re.S)
HREF_RE=re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']',re.I|re.S)
LD_RE=re.compile(r'<script\b(?=[^>]*type=["\']application/ld\+json["\'])[^>]*>(.*?)</script>',re.I|re.S)
TAG_RE=re.compile(r'<[^>]+>')
SCRIPT_RE=re.compile(r'<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->',re.I|re.S)


def clean_html(s:str)->str:
    return re.sub(r'\s+',' ',unescape(TAG_RE.sub(' ',s))).strip()

def route_of(root:Path,p:Path)->str:
    rel=p.relative_to(root).as_posix()
    if rel=='index.html': return '/'
    if rel.endswith('/index.html'): return '/'+rel[:-10]
    # Standalone HTML files are canonical files, not directory aliases.
    # Keep the extension because production publishers (for example magazine)
    # intentionally expose routes such as /magazine/article.html.
    return '/'+rel

def expected_canonical(route:str)->str:
    if route=='/': return BASE+'/'
    return BASE+route

def normalize_route(href:str,current:str)->str|None:
    href=href.strip()
    if not href or href.startswith(('#','mailto:','tel:','javascript:')): return None
    parsed=urlparse(href)
    if parsed.scheme and parsed.netloc and parsed.netloc not in {'healthrenewal.org','www.healthrenewal.org'}: return None
    path=parsed.path
    if not path:
        path=current
    if not path.startswith('/'):
        base=current if current.endswith('/') else current.rsplit('/',1)[0]+'/'
        parts=(base+path).split('/')
        stack=[]
        for x in parts:
            if x in ('','.'): continue
            if x=='..':
                if stack: stack.pop()
            else: stack.append(x)
        path='/'+('/'.join(stack))
    path=re.sub(r'/+','/',path)
    if path.endswith('/index.html'):
        path=path[:-10]
    # Preserve standalone .html paths exactly; only extensionless directory
    # routes receive a trailing slash.
    if not path.endswith('/') and '.' not in path.rsplit('/',1)[-1]: path+='/'
    return path

def words(text:str)->int:
    body=SCRIPT_RE.sub(' ',text)
    body=TAG_RE.sub(' ',body)
    return len(re.findall(r'[A-Za-z0-9_\u0600-\u06FF]+',unescape(body)))

def fingerprint(text:str)->str:
    body=SCRIPT_RE.sub(' ',text)
    body=clean_html(body).lower()
    body=re.sub(r'\s+',' ',body)
    return hashlib.sha256(body.encode()).hexdigest()

def section(route:str)->str:
    if route=='/': return '[home]'
    return route.strip('/').split('/',1)[0] or '[home]'

def severity_score(row:dict)->int:
    s=0
    if row['indexable']:
        if row['words']<300: s+=7
        elif row['words']<700: s+=4
        elif row['words']<1200: s+=2
        if not row['title']: s+=8
        elif len(row['title'])<20 or len(row['title'])>70: s+=1
        if not row['description']: s+=5
        elif len(row['description'])<70 or len(row['description'])>180: s+=1
        if row['h1Count']!=1: s+=5
        if not row['canonical']: s+=6
        elif not row['canonicalOk']: s+=8
        if not row['hasSchema']: s+=2
        if row['inbound']==0 and row['route']!='/': s+=7
    return s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--out',default='production-content-audit'); a=ap.parse_args()
    root=Path(a.root).resolve(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    pages={}
    raw_links={}
    for p in sorted(root.rglob('*.html')):
        text=p.read_text(encoding='utf-8',errors='replace'); r=route_of(root,p)
        title=clean_html(TITLE_RE.search(text).group(1)) if TITLE_RE.search(text) else ''
        desc=clean_html(DESC_RE.search(text).group(1)) if DESC_RE.search(text) else ''
        h1s=[clean_html(x) for x in H1_RE.findall(text)]
        cans=[x.strip() for x in CAN_RE.findall(text)]
        robots=' '.join(ROB_RE.findall(text)).lower()
        noindex='noindex' in robots
        canonical=cans[0] if len(cans)==1 else ''
        expected=expected_canonical(r)
        canok=canonical==expected if canonical else False
        schemas=[]
        for block in LD_RE.findall(text):
            try:
                obj=json.loads(block); schemas.append(obj)
            except Exception: pass
        pages[r]={
            'route':r,'path':p.relative_to(root).as_posix(),'section':section(r),'words':words(text),
            'title':title,'titleLength':len(title),'description':desc,'descriptionLength':len(desc),
            'h1Count':len(h1s),'h1':h1s[0] if h1s else '', 'canonical':canonical,'canonicalCount':len(cans),'canonicalOk':canok,
            'robots':robots,'indexable':not noindex,'hasSchema':bool(schemas),'schemaBlocks':len(schemas),'fingerprint':fingerprint(text)
        }
        raw_links[r]=HREF_RE.findall(text)
    known=set(pages)
    inbound=Counter(); broken=defaultdict(set); outbound=Counter()
    for src,hrefs in raw_links.items():
        seen=set()
        for href in hrefs:
            rr=normalize_route(href,src)
            if not rr or rr in seen: continue
            seen.add(rr)
            if rr in known:
                inbound[rr]+=1; outbound[src]+=1
            elif not re.search(r'\.(?:css|js|png|jpe?g|webp|svg|ico|pdf|xml|json|txt|woff2?)$',rr,re.I): broken[src].add(rr)
    for r,row in pages.items():
        row['inbound']=inbound[r]; row['outbound']=outbound[r]; row['brokenInternalLinks']=len(broken.get(r,set()))
        row['score']=severity_score(row)
    fp=defaultdict(list); titles=defaultdict(list); descriptions=defaultdict(list)
    for r,row in pages.items():
        if row['indexable']:
            fp[row['fingerprint']].append(r)
            if row['title']: titles[row['title'].lower()].append(r)
            if row['description']: descriptions[row['description'].lower()].append(r)
    dup_content=[v for v in fp.values() if len(v)>1]
    dup_titles=[v for v in titles.values() if len(v)>1]
    dup_desc=[v for v in descriptions.values() if len(v)>1]
    sec=defaultdict(lambda:Counter())
    for row in pages.values():
        c=sec[row['section']]; c['pages']+=1; c['indexable']+=int(row['indexable']); c['words']+=row['words'];
        c['lt300']+=int(row['indexable'] and row['words']<300); c['lt700']+=int(row['indexable'] and row['words']<700)
        c['lt1200']+=int(row['indexable'] and row['words']<1200); c['missingDescription']+=int(row['indexable'] and not row['description'])
        c['badH1']+=int(row['indexable'] and row['h1Count']!=1); c['badCanonical']+=int(row['indexable'] and not row['canonicalOk'])
        c['missingSchema']+=int(row['indexable'] and not row['hasSchema']); c['orphan']+=int(row['indexable'] and row['inbound']==0 and row['route']!='/')
        c['brokenSources']+=int(row['brokenInternalLinks']>0)
    sections=[]
    for name,c in sec.items():
        d=dict(c); d['section']=name; d['avgWords']=round(c['words']/c['pages'],1) if c['pages'] else 0
        d['qualityDebt']=c['lt700']*3+c['missingDescription']*2+c['badH1']*3+c['badCanonical']*4+c['missingSchema']+c['orphan']*4+c['brokenSources']*2
        sections.append(d)
    sections.sort(key=lambda x:(-x['qualityDebt'],-x['pages'],x['section']))
    priority=sorted((r for r in pages.values() if r['indexable']),key=lambda x:(-x['score'],x['words'],x['route']))[:500]
    summary={
        'schemaVersion':2,'status':'passed','routeContract':'index.html => trailing-slash directory; standalone .html => extension-preserving file route',
        'totalHtmlPages':len(pages),'indexablePages':sum(x['indexable'] for x in pages.values()),
        'noindexPages':sum(not x['indexable'] for x in pages.values()),'sections':sections,
        'thin':{'lt300':sum(x['indexable'] and x['words']<300 for x in pages.values()),'lt700':sum(x['indexable'] and x['words']<700 for x in pages.values()),'lt1200':sum(x['indexable'] and x['words']<1200 for x in pages.values())},
        'seo':{'missingTitle':sum(x['indexable'] and not x['title'] for x in pages.values()),'missingDescription':sum(x['indexable'] and not x['description'] for x in pages.values()),'badH1':sum(x['indexable'] and x['h1Count']!=1 for x in pages.values()),'badCanonical':sum(x['indexable'] and not x['canonicalOk'] for x in pages.values()),'missingSchema':sum(x['indexable'] and not x['hasSchema'] for x in pages.values())},
        'graph':{'orphans':sum(x['indexable'] and x['inbound']==0 and x['route']!='/' for x in pages.values()),'pagesWithBrokenInternalLinks':sum(x['brokenInternalLinks']>0 for x in pages.values()),'brokenTargets':len({t for v in broken.values() for t in v})},
        'duplicates':{'contentGroups':len(dup_content),'titleGroups':len(dup_titles),'descriptionGroups':len(dup_desc)},
        'topPriorityPages':priority[:100]
    }
    (out/'production-content-audit-v1.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'production-content-pages-v1.json').write_text(json.dumps(sorted(pages.values(),key=lambda x:x['route']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'production-duplicate-content-v1.json').write_text(json.dumps(dup_content,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'production-duplicate-titles-v1.json').write_text(json.dumps(dup_titles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'production-broken-links-v1.json').write_text(json.dumps({k:sorted(v) for k,v in broken.items()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'production-priority-pages-v1.json').write_text(json.dumps(priority,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
