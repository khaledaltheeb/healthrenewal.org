#!/usr/bin/env python3
"""Publish static discovery cards and complete section catalogues."""
from __future__ import annotations
import argparse, html, json, re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ORIGIN='https://healthrenewal.org'
CATALOG_FAMILIES=('developers','guides','library','outside-the-box','provider-assessment-demo','sectors','special-needs')
REPLACEMENTS={
 'href="/tips/sleep/"':'href="/tips/better-sleep/"',
 "href='/tips/sleep/'":"href='/tips/better-sleep/'",
 'href="/mental-health/"':'href="/guides/mental-health-guide/"',
 "href='/mental-health/'":"href='/guides/mental-health-guide/'",
}
STYLE='''<style data-complete-discovery-style-v1>.complete-discovery{padding:2.5rem 0;background:#f8fafc;color:#172033}.complete-discovery-wrap{width:min(1180px,calc(100% - 2rem));margin:auto}.complete-discovery h2{font-size:clamp(1.5rem,3vw,2.15rem);margin:.2rem 0 .6rem}.complete-discovery-intro{max-width:78ch;color:#475569}.complete-discovery-search{display:block;width:min(100%,560px);margin:1rem 0;padding:.85rem 1rem;border:1px solid #94a3b8;border-radius:.8rem;font:inherit;background:#fff;color:#111827}.complete-discovery-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:1rem;margin-top:1rem}.complete-discovery-card{display:flex;flex-direction:column;gap:.65rem;padding:1.1rem;border:1px solid #cbd5e1;border-radius:1rem;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.06)}.complete-discovery-card h3{font-size:1.05rem;margin:0}.complete-discovery-card p{margin:0;color:#475569;line-height:1.75;flex:1}.complete-discovery-card a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.6rem .85rem;border-radius:.7rem;background:#0f766e;color:#fff;text-decoration:none;font-weight:700}.complete-discovery-card a:focus-visible,.complete-discovery-search:focus-visible{outline:3px solid #f59e0b;outline-offset:3px}</style>'''

def esc(s): return html.escape(s or '',quote=True)
def text(rx,s):
 m=re.search(rx,s,re.I|re.S)
 return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',m.group(1)))).strip() if m else ''
@dataclass
class Page:
 route:str; path:Path; title:str; h1:str; desc:str; robots:str; refresh:str
 @property
 def indexable(self): return 'noindex' not in self.robots and self.route!='/404.html' and not re.fullmatch(r'/google[^/]*\.html',self.route,re.I)
 @property
 def label(self): return self.h1 or self.title or self.route

def pages(site):
 out={}
 for p in site.rglob('*'):
  if not p.is_file() or p.suffix.lower() not in ('.html','.htm'): continue
  rel=p.relative_to(site).as_posix()
  route=('/' if rel=='index.html' else '/'+p.parent.relative_to(site).as_posix().strip('/')+'/') if p.name=='index.html' else '/'+rel
  s=p.read_text(encoding='utf-8',errors='ignore')
  dm=re.search(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)',s,re.I) or re.search(r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description',s,re.I)
  rm=' '.join(re.findall(r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']*)',s,re.I)).lower()
  rf=re.search(r'<meta\s+[^>]*http-equiv=["\']refresh["\'][^>]*content=["\']([^"\']*)',s,re.I)
  out[route]=Page(route,p,text(r'<title[^>]*>(.*?)</title>',s),text(r'<h1[^>]*>(.*?)</h1>',s),html.unescape(dm.group(1)).strip() if dm else '',rm,rf.group(1) if rf else '')
 return out

def card(p,href=None):
 d=(p.desc or f'صفحة منشورة ضمن المنصة حول {p.label}.')[:190]
 return f'<article class="complete-discovery-card"><h3>{esc(p.label)}</h3><p>{esc(d)}</p><a href="{esc(href or p.route)}">فتح الصفحة ←</a></article>'
def inject(path,marker,block):
 s=path.read_text(encoding='utf-8'); wrap=f'<!-- BEGIN {marker} -->\n{block}\n<!-- END {marker} -->'
 rx=re.compile(rf'<!--\s*BEGIN {re.escape(marker)}\s*-->.*?<!--\s*END {re.escape(marker)}\s*-->',re.I|re.S)
 if rx.search(s): s=rx.sub(wrap,s,1)
 elif '</main>' in s: s=s.replace('</main>',wrap+'\n</main>',1)
 else: s=s.replace('</body>',wrap+'\n</body>',1)
 path.write_text(s,encoding='utf-8')
def urlset(path,routes):
 today=date.today().isoformat(); lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
 for r in sorted(set(routes)): lines.append(f'  <url><loc>{esc(ORIGIN+r)}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
 path.write_text('\n'.join(lines+['</urlset>'])+'\n',encoding='utf-8')
def register(site,name):
 p=site/'sitemap-index.xml'; s=p.read_text(encoding='utf-8'); u=f'{ORIGIN}/{name}'
 if u not in s: s=s.replace('</sitemapindex>',f'  <sitemap><loc>{u}</loc><lastmod>{date.today().isoformat()}</lastmod></sitemap>\n</sitemapindex>')
 p.write_text(s,encoding='utf-8')
def directory(root,rootpage,entries,route):
 cards='\n'.join(card(p) for p in entries)
 schema={'@context':'https://schema.org','@type':'CollectionPage','name':f'الفهرس الكامل: {rootpage.label}','url':ORIGIN+route,'inLanguage':'ar','numberOfItems':len(entries)}
 return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>الفهرس الكامل: {esc(rootpage.label)} | منصة الصحة النفسية</title><meta name="description" content="بطاقات ثابتة لكل الصفحات المنشورة ضمن {esc(rootpage.label)}."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{ORIGIN}{route}">{STYLE}<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(',',':'))}</script></head><body><main><section class="complete-discovery"><div class="complete-discovery-wrap"><p><a href="/{root}/">العودة إلى القسم</a> · <a href="/sections/">جميع الأقسام</a></p><h1>الفهرس الكامل: {esc(rootpage.label)}</h1><p class="complete-discovery-intro">جميع الصفحات المنشورة في بطاقات HTML ثابتة. العدد: {len(entries)}.</p><label for="q">ابحث داخل القسم</label><input id="q" class="complete-discovery-search" type="search"><div class="complete-discovery-grid">{cards}</div></div></section></main><script>(()=>{{const q=document.getElementById('q'),c=[...document.querySelectorAll('.complete-discovery-card')];q.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase();c.forEach(x=>x.hidden=v&&!x.textContent.toLowerCase().includes(v))}})}})()</script></body></html>'''

def run(site):
 site=site.resolve(); changed=0
 for p in site.rglob('*.html'):
  s=p.read_text(encoding='utf-8',errors='ignore'); u=s
  for a,b in REPLACEMENTS.items(): u=u.replace(a,b)
  if u!=s: p.write_text(u,encoding='utf-8'); changed+=1
 ps=pages(site)
 fg=ps['/family-guide/']; conditions=sorted([p for r,p in ps.items() if r.startswith('/family-guide/conditions/') and p.indexable],key=lambda x:x.label)
 cards='\n'.join(card(p) for p in conditions); s=fg.path.read_text(encoding='utf-8')
 rx=re.compile(r'(<div\s+[^>]*id=["\']conditions-grid["\'][^>]*>)(.*?)(</div>)',re.I|re.S); m=rx.search(s)
 if not m: raise SystemExit('family-guide conditions-grid missing')
 s=s[:m.start()]+m.group(1)+'\n'+cards+'\n'+m.group(3)+s[m.end():]
 if 'data-complete-discovery-style-v1' not in s: s=s.replace('</head>',STYLE+'</head>',1)
 fg.path.write_text(s,encoding='utf-8')
 ps=pages(site); catalogs=[]
 for family in CATALOG_FAMILIES:
  rr=f'/{family}/'; root=ps.get(rr)
  if not root or not root.indexable: continue
  entries=sorted([p for r,p in ps.items() if r.startswith(rr) and r!=rr and p.indexable and not p.refresh and '/all-pages/' not in r],key=lambda x:(x.label,x.route))
  if not entries: continue
  cr=f'/{family}/all-pages/'; cp=site/family/'all-pages/index.html'; cp.parent.mkdir(parents=True,exist_ok=True); cp.write_text(directory(family,root,entries,cr),encoding='utf-8')
  block=f'<section class="complete-discovery"><div class="complete-discovery-wrap"><h2>الفهرس الكامل للقسم</h2><p class="complete-discovery-intro">كل الصفحات المنشورة في هذا القسم مجمعة في بطاقات ثابتة وقابلة للبحث.</p><div class="complete-discovery-grid">{card(Page(cr,cp,"الفهرس الكامل",f"جميع صفحات {root.label}",f"{len(entries)} صفحة منشورة",'',""),cr)}</div></div></section>{STYLE}'
  inject(root.path,f'COMPLETE {family.upper()} DIRECTORY V1',block); catalogs.append({'family':family,'route':cr,'entries':len(entries)})
 ep=ps.get('/encyclopedia/'); ea=ps.get('/encyclopedia/all/')
 if ep and ea: inject(ep.path,'COMPLETE ENCYCLOPEDIA DISCOVERY V1',f'<section class="complete-discovery"><div class="complete-discovery-wrap"><h2>كل صفحات الموسوعة</h2><div class="complete-discovery-grid">{card(ea)}</div></div></section>{STYLE}')
 ps=pages(site); sec=ps['/sections/']; roots=sorted([p for r,p in ps.items() if p.indexable and r not in ('/','/sections/') and len([x for x in r.strip('/').split('/') if x])==1],key=lambda x:x.label)
 inject(sec.path,'COMPLETE ROOT DISCOVERY V1',f'<section class="complete-discovery"><div class="complete-discovery-wrap"><h2>صفحات المنصة العامة</h2><p class="complete-discovery-intro">بطاقات ثابتة لكل صفحة رئيسية منشورة.</p><div class="complete-discovery-grid">{"".join(card(p) for p in roots)}</div></div></section>{STYLE}')
 ps=pages(site); fr=[r for r,p in ps.items() if p.indexable and (r=='/family-guide/' or r.startswith('/family-guide/conditions/') or r.startswith('/family-guide/tools/'))]
 urlset(site/'sitemap-family-guide.xml',fr); phase=[]; ap=site/'api/family-guide-v1-phase8.json'
 if ap.is_file(): phase=[f"/family-guide/conditions/{x['slug']}/" for x in json.loads(ap.read_text(encoding='utf-8')).get('conditions',[])]
 urlset(site/'sitemap-family-guide-phase8.xml',phase)
 ps=pages(site); indexable=[r for r,p in ps.items() if p.indexable]; urlset(site/'sitemap-complete-discovery-v1.xml',indexable)
 for n in ('sitemap-family-guide.xml','sitemap-family-guide-phase8.xml','sitemap-complete-discovery-v1.xml'): register(site,n)
 report={'schemaVersion':1,'status':'published','changedBrokenLinkFiles':changed,'staticFamilyGuideCards':len(conditions),'catalogs':catalogs,'rootCards':len(roots),'indexableRoutes':len(indexable)}
 (site/'api').mkdir(exist_ok=True); (site/'api/discovery-publication-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))

def main():
 a=argparse.ArgumentParser(); a.add_argument('site',type=Path); ns=a.parse_args(); run(ns.site)
if __name__=='__main__': main()
