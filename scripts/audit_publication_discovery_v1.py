#!/usr/bin/env python3
"""Fail closed when a published page is missing, broken, orphaned, or not exposed as a visible card."""
from __future__ import annotations
import argparse, html, json, re, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ORIGIN='https://healthrenewal.org'; HOSTS={'healthrenewal.org','www.healthrenewal.org','khaledaltheeb.github.io'}
TEXT={'.html','.htm','.xml','.json','.webmanifest','.txt','.js','.mjs','.css','.svg'}
SKIP_TOP={'.git','.github','node_modules','.venv','venv','dist','build','scripts','tests','docs','reports','content','.v10bundle','.generator-v6','_site'}; SKIP_PARTS={'account-backend','backend','migrations'}
CARD=('card','tile','item','entry','route','tool','path','topic','catalog','directory','grid','journey','alpha'); NAV=('nav','footer','crumb','breadcrumb','header','menu','toc','pagination','language')
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def norm(v,base='/'):
 v=(v or '').strip()
 if not v or v.startswith(('#','mailto:','tel:','javascript:','data:','blob:')): return None
 u=urlparse(urljoin(ORIGIN+base,v))
 if u.netloc and u.netloc.lower() not in HOSTS: return None
 p=re.sub('/+','/',unquote(u.path or '/'))
 if p.startswith('/pterminology-site/'): p=p[len('/pterminology-site'):]
 if p.endswith('/index.html'): p=p[:-10]
 return p or '/'
def visible_text(rx,s):
 m=re.search(rx,s,re.I|re.S)
 return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',m.group(1)))).strip() if m else ''
@dataclass
class Page:
 route:str; path:Path; title:str; h1:str; robots:str; canonical:list[str]
 @property
 def indexable(self): return 'noindex' not in self.robots and self.route!='/404.html' and not re.fullmatch(r'/google[^/]*\.html',self.route,re.I)
def scan_pages(site):
 out={}
 for p in site.rglob('*'):
  if not p.is_file() or p.suffix.lower() not in ('.html','.htm'): continue
  rel=p.relative_to(site).as_posix(); route=('/' if rel=='index.html' else '/'+p.parent.relative_to(site).as_posix().strip('/')+'/') if p.name=='index.html' else '/'+rel
  s=p.read_text(encoding='utf-8',errors='ignore'); robots=' '.join(re.findall(r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']*)',s,re.I)).lower()
  can=re.findall(r'<link\s+[^>]*rel=["\'][^"\']*canonical[^"\']*["\'][^>]*href=["\']([^"\']+)',s,re.I) or re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'][^"\']*canonical',s,re.I)
  out[route]=Page(route,p,visible_text(r'<title[^>]*>(.*?)</title>',s),visible_text(r'<h1[^>]*>(.*?)</h1>',s),robots,can)
 return out
class Parser(HTMLParser):
 def __init__(self): super().__init__(convert_charrefs=True); self.stack=[]; self.links=[]; self.resources=[]
 def handle_starttag(self,tag,attrs):
  tag=tag.lower(); a={k.lower():(v or '') for k,v in attrs}; nodes=self.stack+[(tag,a)]; hidden=card=nav=False
  for t,x in nodes[-7:]:
   c=x.get('class','').lower(); st=x.get('style','').replace(' ','').lower()
   hidden|=('hidden' in x or x.get('aria-hidden','').lower()=='true' or 'display:none' in st or 'visibility:hidden' in st or bool(re.search(r'(^|\s)(hidden|sr-only|visually-hidden)(\s|$)',c)))
   nav|=(t in ('nav','footer','header') or any(k in c for k in NAV)); card|=(t=='article' or any(k in c for k in CARD))
  kind='navigation' if nav else ('card' if card else 'body')
  if tag=='a' and a.get('href'): self.links.append((a['href'],kind,hidden))
  if tag in ('img','script','source','video','audio','iframe') and a.get('src'): self.resources.append((a['src'],tag))
  if tag=='link' and a.get('href') and 'canonical' not in a.get('rel','').lower() and 'alternate' not in a.get('rel','').lower(): self.resources.append((a['href'],tag))
  if tag not in VOID: self.stack.append((tag,a))
 def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs); self.stack=self.stack[:-1] if self.stack and tag.lower() not in VOID else self.stack
 def handle_endtag(self,tag):
  tag=tag.lower()
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag: del self.stack[i:]; break
def exists(site,pages,target):
 if target in pages: return True
 rel=target.lstrip('/')
 return (site/rel).is_file() or (site/rel/'index.html').is_file()
def graph(site,pages):
 incoming=defaultdict(list); broken=[]; resources=[]; count=0
 for route,page in pages.items():
  p=Parser(); p.feed(page.path.read_text(encoding='utf-8',errors='ignore'))
  for href,kind,hidden in p.links:
   target=norm(href,route)
   if target is None: continue
   count+=1; rec={'source':route,'target':target,'href':href,'kind':kind,'hidden':hidden}
   if exists(site,pages,target):
    mapped=target
    if mapped not in pages and not Path(mapped.lstrip('/')).suffix and (site/mapped.lstrip('/')/'index.html').is_file(): mapped='/'+mapped.strip('/')+'/'
    incoming[mapped].append(rec)
   else: broken.append(rec)
  for url,tag in p.resources:
   target=norm(url,route)
   if target is not None and not exists(site,pages,target): resources.append({'source':route,'target':target,'url':url,'tag':tag})
 return incoming,broken,resources,count
def sitemap_routes(site):
 out=set(); invalid=[]
 for p in site.glob('sitemap*.xml'):
  try: root=ET.parse(p).getroot()
  except Exception as e: invalid.append({'file':p.name,'error':str(e)}); continue
  if root.tag.rsplit('}',1)[-1]!='urlset': continue
  for x in root.findall('.//{*}loc'):
   if x.text:
    u=urlparse(x.text.strip())
    if u.netloc.lower() in HOSTS:
     r=norm(u.path,'/')
     if r: out.add(r)
 return out,invalid
def public_files(repo):
 out=[]
 for p in repo.rglob('*'):
  if not p.is_file(): continue
  r=p.relative_to(repo)
  if not r.parts or r.parts[0] in SKIP_TOP or any(x in SKIP_PARTS for x in r.parts) or r.as_posix()=='deployment.json': continue
  if p.suffix.lower() in TEXT or p.name=='CNAME': out.append(r)
 return out
def run(site,repo=None):
 site=site.resolve(); pages=scan_pages(site); incoming,broken,resources,link_count=graph(site,pages); indexable={r:p for r,p in pages.items() if p.indexable}
 orphan=[]; no_card=[]; meta=[]; canon=[]
 for r,p in sorted(indexable.items()):
  if r!='/':
   inc=[x for x in incoming.get(r,[]) if x['source']!=r and not x['hidden']]
   if not inc: orphan.append(r)
   if not any(x['kind']=='card' for x in inc): no_card.append(r)
  if not p.title: meta.append({'route':r,'issue':'missing_title'})
  if not p.h1: meta.append({'route':r,'issue':'missing_h1'})
  if len(p.canonical)!=1: canon.append({'route':r,'issue':f'canonical_count_{len(p.canonical)}'})
  elif norm(urlparse(p.canonical[0]).path,'/')!=r: canon.append({'route':r,'issue':'non_self_canonical','canonical':p.canonical[0]})
 sm,invalid=sitemap_routes(site); sm_missing=sorted(set(indexable)-sm)
 src=public_files(repo.resolve()) if repo else []; src_missing=[x.as_posix() for x in src if not (site/x).is_file()]
 report={'schemaVersion':1,'status':'passed','verifiedAt':datetime.now(timezone.utc).isoformat(),'sourcePublicFiles':len(src),'missingSourceFiles':src_missing,'publishedHtmlRoutes':len(pages),'indexableHtmlRoutes':len(indexable),'internalLinks':link_count,'brokenInternalLinks':broken,'brokenInternalResources':resources,'orphanIndexableRoutes':orphan,'indexableRoutesWithoutVisibleCard':no_card,'sitemapMissingIndexableRoutes':sm_missing,'invalidSitemaps':invalid,'metadataIssues':meta,'canonicalIssues':canon,'families':dict(sorted(Counter('root' if r=='/' else r.strip('/').split('/',1)[0] for r in indexable).items()))}
 failures=sum(len(report[k]) for k in ('missingSourceFiles','brokenInternalLinks','brokenInternalResources','orphanIndexableRoutes','indexableRoutesWithoutVisibleCard','sitemapMissingIndexableRoutes','invalidSitemaps','metadataIssues','canonicalIssues'))
 if failures: report['status']='failed'
 api=site/'api'; api.mkdir(exist_ok=True); (api/'publication-discovery-audit-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in report.items() if k in ('status','sourcePublicFiles','publishedHtmlRoutes','indexableHtmlRoutes','internalLinks','missingSourceFiles','brokenInternalLinks','brokenInternalResources','orphanIndexableRoutes','indexableRoutesWithoutVisibleCard','sitemapMissingIndexableRoutes','invalidSitemaps','metadataIssues','canonicalIssues')},ensure_ascii=False,indent=2))
 if failures: raise SystemExit(json.dumps(report,ensure_ascii=False)[:12000])
 return report
def main():
 a=argparse.ArgumentParser(); a.add_argument('site',type=Path); a.add_argument('--repo-root',type=Path); n=a.parse_args(); run(n.site,n.repo_root)
if __name__=='__main__': main()
