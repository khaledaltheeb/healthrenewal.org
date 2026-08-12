#!/usr/bin/env python3
"""Finalize production SEO metadata and apply committed reviewed Quick Info overlays.

This is deliberately deterministic: it does not invent article prose. It integrates
reviewed editorial fragments already committed in the repository, normalizes
canonical URLs for every indexable HTML route, marks non-content verification files
noindex, and repairs missing baseline metadata from existing page headings/text.
"""
from __future__ import annotations
import argparse, html, json, re, subprocess, sys
from pathlib import Path

BASE='https://healthrenewal.org'
TITLE_RE=re.compile(r'<title\b[^>]*>.*?</title>',re.I|re.S)
DESC_RE=re.compile(r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*>',re.I|re.S)
ROB_RE=re.compile(r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*>',re.I|re.S)
CAN_RE=re.compile(r'<link\b(?=[^>]*\brel=["\'][^"\']*canonical[^"\']*["\'])[^>]*>',re.I|re.S)
H1_RE=re.compile(r'<h1\b[^>]*>(.*?)</h1>',re.I|re.S)
H_RE=re.compile(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>',re.I|re.S)
TAG_RE=re.compile(r'<[^>]+>')
SCRIPT_RE=re.compile(r'<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->',re.I|re.S)
VERIFY_RE=re.compile(r'^google[0-9a-f]+\.html$',re.I)


def text(fragment:str)->str:
    return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',fragment))).strip()

def route(root:Path,p:Path)->str:
    rel=p.relative_to(root).as_posix()
    if rel=='index.html': return '/'
    if rel.endswith('/index.html'): return '/'+rel[:-10]
    return '/'+rel

def canonical(root:Path,p:Path)->str:
    return BASE+route(root,p)

def visible_text(source:str)->str:
    return text(SCRIPT_RE.sub(' ',source))

def description_from(source:str)->str:
    for frag in H1_RE.findall(source)+H_RE.findall(source):
        v=text(frag)
        if len(v)>=30: return v[:155]
    v=visible_text(source)
    return v[:155] if v else 'صفحة من منصة روافد للمحتوى النفسي والتربوي والصحي المبني على المعرفة.'

def title_from(source:str,p:Path)->str:
    h=H1_RE.search(source)
    if h and text(h.group(1)): return text(h.group(1))[:65]
    hs=H_RE.search(source)
    if hs and text(hs.group(1)): return text(hs.group(1))[:65]
    return p.stem.replace('-',' ')[:65]

def insert_head(source:str,fragment:str)->str:
    m=re.search(r'</head\s*>',source,re.I)
    if not m: return source
    return source[:m.start()]+fragment+'\n'+source[m.start():]

def normalize_page(root:Path,p:Path)->dict:
    source=p.read_text(encoding='utf-8',errors='replace')
    changed=False
    verification=p.parent==root and VERIFY_RE.match(p.name)
    if verification:
        robots='<meta name="robots" content="noindex,nofollow">'
        if ROB_RE.search(source): source=ROB_RE.sub(robots,source,count=1); changed=True
        elif re.search(r'<head\b',source,re.I): source=insert_head(source,robots); changed=True
        if changed: p.write_text(source,encoding='utf-8',newline='\n')
        return {'verificationNoindex':1,'canonicalFixed':0,'titleAdded':0,'descriptionAdded':0}
    c=f'<link rel="canonical" href="{html.escape(canonical(root,p),quote=True)}">'
    if CAN_RE.search(source):
        updated=CAN_RE.sub(c,source,count=1)
        if updated!=source: source=updated; changed=True
    elif re.search(r'<head\b',source,re.I): source=insert_head(source,c); changed=True
    ta=da=0
    if not TITLE_RE.search(source) and re.search(r'<head\b',source,re.I):
        source=insert_head(source,f'<title>{html.escape(title_from(source,p))}</title>'); changed=True; ta=1
    if not DESC_RE.search(source) and re.search(r'<head\b',source,re.I):
        source=insert_head(source,f'<meta name="description" content="{html.escape(description_from(source),quote=True)}">'); changed=True; da=1
    if changed: p.write_text(source,encoding='utf-8',newline='\n')
    return {'verificationNoindex':0,'canonicalFixed':1,'titleAdded':ta,'descriptionAdded':da}

def apply_editorial(site:Path,repo:Path)->dict:
    base=repo/'content'/'quick-info-editorial'
    batches=sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    applied=[]
    for batch in batches:
        fragments=list((base/batch).glob('*.html'))
        if not fragments: continue
        cmd=[sys.executable,str(repo/'scripts'/'apply_quick_info_editorial_batch.py'),'--root',str(site),'--repo-root',str(repo),'--batch',batch,'--minimum-total-words','1500']
        subprocess.run(cmd,check=True)
        applied.append({'batch':batch,'pages':len(fragments)})
    return {'batches':applied,'pages':sum(x['pages'] for x in applied)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--site',required=True); ap.add_argument('--repo-root',default='.'); a=ap.parse_args()
    site=Path(a.site).resolve(); repo=Path(a.repo_root).resolve()
    editorial=apply_editorial(site,repo)
    stats={'verificationNoindex':0,'canonicalFixed':0,'titleAdded':0,'descriptionAdded':0}
    for p in sorted(site.rglob('*.html')):
        for k,v in normalize_page(site,p).items(): stats[k]+=v
    report={'schemaVersion':1,'status':'passed','editorial':editorial,'metadata':stats}
    api=site/'api'; api.mkdir(parents=True,exist_ok=True)
    (api/'production-quality-finalization-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__': main()
