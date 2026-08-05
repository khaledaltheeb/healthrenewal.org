#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

HOSTS={'healthrenewal.org','www.healthrenewal.org'}
ATTRS={'a':'href','link':'href','script':'src','img':'src','source':'src','video':'src','audio':'src','form':'action'}
IGNORE={'mailto','tel','javascript','data','blob'}
OLD_BASES=('https://khaledaltheeb.github.io/pterminology-site/','http://khaledaltheeb.github.io/pterminology-site/')
PREFIX_ATTR=re.compile(r'(?P<p>\b(?:href|src|action|content)\s*=\s*["\'])/pterminology-site/',re.I)
PREFIX_JSON=re.compile(r'(["\'])/pterminology-site/')
REFRESH=re.compile(r'<meta\b(?=[^>]*\bhttp-equiv\s*=\s*(["\'])refresh\1)(?=[^>]*\bcontent\s*=\s*(["\'])(?P<c>.*?)\2)[^>]*>',re.I|re.S)
CANON=re.compile(r'(<link\b(?=[^>]*\brel\s*=\s*(["\'])canonical\2)[^>]*\bhref\s*=\s*)(["\'])(.*?)(\3)',re.I|re.S)
BRIDGES={'mental-health/index.html':'/terms/mental-health/','rehabilitation/index.html':'/library/branches/rehabilitation-psychology/','tips/sleep/index.html':'/tips/better-sleep/'}

class P(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.refs=[]; self.canonical=None; self.refresh=None
 def handle_starttag(self,tag,attrs):
  d={k.lower():(v or '') for k,v in attrs}; tag=tag.lower()
  a=ATTRS.get(tag)
  if a and d.get(a,'').strip(): self.refs.append(d[a].strip())
  if tag=='link' and 'canonical' in d.get('rel','').lower().split(): self.canonical=d.get('href') or None
  if tag=='meta' and d.get('http-equiv','').lower()=='refresh': self.refresh=d.get('content') or None

def route(rel):
 if rel=='index.html': return '/'
 return '/'+(rel[:-10] if rel.endswith('/index.html') else rel)

def exists(path,files):
 p=unquote(path).lstrip('/')
 if not p:return 'index.html' in files
 c=[p,p+'/index.html',p+'.html'] if not p.endswith('/') else [p,p+'index.html']
 return any(x in files for x in c)

def refresh_target(content):
 if not content:return None
 m=re.search(r'(?:^|;)\s*url\s*=\s*(.+?)\s*$',content,re.I)
 return m.group(1).strip().strip('"\'') if m else None

def redirect_page(target,title):
 t=escape(target,quote=True); a='https://healthrenewal.org'+target
 return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="{a}"><meta http-equiv="refresh" content="0;url={t}"><script>location.replace({json.dumps(target,ensure_ascii=False)});</script></head><body><p>تم نقل الصفحة إلى <a href="{t}">{escape(title)}</a>.</p></body></html>'''

def conservative_rights(site):
 out=site/'api/source-rights-registry.json'
 if out.exists():return False
 src=json.loads((site/'api/source-registry.json').read_text(encoding='utf-8'))
 items=[]
 for s in src.get('sources',[]):
  url=s.get('url',''); intended=s.get('intended_use','')
  items.append({'id':s.get('id',''),'name':s.get('name',''),'name_ar':s.get('name_ar',s.get('name','')),'official_url':url,'rights_status':'link_only','access_mode':'official_link_only_pending_rights_review','licence':{'short_name':'غير مؤكد','url':url},'permissions':{'link':'allowed','copy':'not_confirmed','translate':'not_confirmed','adapt':'not_confirmed','redistribute':'not_confirmed','embed':'not_confirmed','commercial_use':'not_confirmed','logo_use':'not_confirmed','automated_catalogue':'not_confirmed'},'requirements':['الرجوع إلى شروط المصدر قبل أي استخدام يتجاوز الربط.','عدم ادعاء الشراكة أو الاعتماد أو التأييد.'],'recommended_platform_use':[intended or 'الإحالة إلى المصدر الرسمي.','الربط والإسناد النصي فقط حتى اكتمال مراجعة الحقوق.'],'review_due':'2026-12-31'})
 out.write_text(json.dumps({'schema_version':'1.0.0','generated_at':datetime.now(timezone.utc).isoformat(),'policy':'conservative_link_only_until_documented_rights_review','notice_ar':'هذا السجل لا يمنح ترخيصًا؛ يسمح بالربط فقط حتى مراجعة الحقوق.','sources':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return True

def repair(site):
 legacy=canon=0
 for page in sorted(site.rglob('*.html')):
  old=page.read_text(encoding='utf-8',errors='replace'); text=old
  for base in OLD_BASES:
   n=text.count(base); text=text.replace(base,'https://healthrenewal.org/'); legacy+=n
  plain='khaledaltheeb.github.io/pterminology-site/'
  n=text.count(plain); text=text.replace(plain,'healthrenewal.org/'); legacy+=n
  text,n=PREFIX_ATTR.subn(lambda m:m.group('p')+'/',text); legacy+=n
  text,n=PREFIX_JSON.subn(lambda m:m.group(1)+'/',text); legacy+=n
  m=REFRESH.search(text)
  target=refresh_target(m.group('c')) if m else None
  if target and target.startswith('/'):
   absolute='https://healthrenewal.org'+target; c=CANON.search(text)
   if c and c.group(4)!=absolute:
    text=CANON.sub(lambda x:x.group(1)+x.group(3)+absolute+x.group(5),text,count=1); canon+=1
  if text!=old:page.write_text(text,encoding='utf-8')
 created=[]
 titles={'mental-health/index.html':'الصحة النفسية','rehabilitation/index.html':'التأهيل','tips/sleep/index.html':'إرشادات النوم'}
 for rel,target in BRIDGES.items():
  p=site/rel
  if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(redirect_page(target,titles[rel]),encoding='utf-8');created.append({'path':rel,'target':target})
 css=site/'assets/addiction/addiction-core.css'; css_created=False
 if not css.exists():css.parent.mkdir(parents=True,exist_ok=True);css.write_text('/* Compatibility alias; platform-core.css supplies the layout. */\n',encoding='utf-8');css_created=True
 rights_created=conservative_rights(site)
 return {'legacyUrlRewrites':legacy,'redirectCanonicalRepairs':canon,'compatibilityRoutesCreated':created,'compatibilityCssCreated':css_created,'sourceRightsRegistryCreated':rights_created}

def collect(site):
 rows=[]
 for page in sorted(site.rglob('*.html')):
  rel=page.relative_to(site).as_posix(); text=page.read_text(encoding='utf-8',errors='replace'); p=P()
  try:p.feed(text)
  except Exception:pass
  rows.append((rel,route(rel),text,p))
 return rows

def internal_path(value,base):
 if not value or value.startswith('#'):return None
 u=urlparse(value)
 if u.scheme.lower() in IGNORE:return None
 if u.scheme in {'http','https'}:
  return u.path if u.netloc.lower() in HOSTS else None
 if u.scheme or value.startswith('//'):return None
 return urlparse(urljoin('https://healthrenewal.org'+base,value)).path

def repair_missing_images(site,rows):
 files={p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}; fallback=site/'assets/brand/rawafid-social-card.jpg'
 if not fallback.is_file():raise RuntimeError('Missing brand fallback image')
 created=[]
 for rel,base,_text,p in rows:
  for value in p.refs:
   path=internal_path(value,base)
   if not path or exists(path,files):continue
   if re.fullmatch(r'/assets/quick-info/cards/[A-Za-z0-9._-]+\.jpg',path):
    dest=site/path.lstrip('/')
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(fallback,dest);files.add(dest.relative_to(site).as_posix());created.append(path)
 return sorted(set(created))

def validate(site):
 files={p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}; missing=defaultdict(set);counts=Counter();badcanon=[];legacy=[];rows=collect(site)
 for rel,base,text,p in rows:
  if 'khaledaltheeb.github.io/pterminology-site' in text or PREFIX_ATTR.search(text) or PREFIX_JSON.search(text):legacy.append({'page':rel})
  target=refresh_target(p.refresh)
  if target and target.startswith('/'):
   expected='https://healthrenewal.org'+target
   if p.canonical!=expected:badcanon.append({'page':rel,'target':target,'canonical':p.canonical,'expected':expected})
  for value in p.refs:
   path=internal_path(value,base)
   if path is None:continue
   counts[path]+=1
   if not exists(path,files):missing[path].add(rel)
 items=[{'path':k,'references':counts[k],'pages':sorted(v)} for k,v in sorted(missing.items(),key=lambda x:(-counts[x[0]],x[0]))]
 return {'htmlPages':len(rows),'siteFiles':len(files),'internalReferencesChecked':sum(counts.values()),'uniqueInternalPathsChecked':len(counts),'missingInternalPaths':len(items),'missingInternalReferences':sum(x['references'] for x in items),'missing':items,'redirectCanonicalMismatches':badcanon,'legacyRouteReferences':legacy}

def run(site):
 site=Path(site).resolve()
 if not (site/'index.html').is_file():raise RuntimeError(f'Invalid site root: {site}')
 repairs=repair(site); rows=collect(site); images=repair_missing_images(site,rows); check=validate(site)
 report={'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(),**repairs,'quickInfoFallbackFilesCreated':len(images),'quickInfoFallbackPaths':images,**check}
 report['status']='passed' if check['missingInternalPaths']==0 and not check['redirectCanonicalMismatches'] and not check['legacyRouteReferences'] else 'failed'
 out=site/'api/final-site-integrity-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if report['status']!='passed':raise RuntimeError('Final site integrity validation failed: '+json.dumps({'missing':check['missing'][:10],'canonical':check['redirectCanonicalMismatches'][:10],'legacy':check['legacyRouteReferences'][:10]},ensure_ascii=False))
 return report

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--site',default='_site');a=ap.parse_args();r=run(a.site)
 print(json.dumps({k:r[k] for k in ('status','htmlPages','siteFiles','internalReferencesChecked','missingInternalPaths','missingInternalReferences','quickInfoFallbackFilesCreated','redirectCanonicalRepairs','legacyUrlRewrites')},ensure_ascii=False))
if __name__=='__main__':main()
