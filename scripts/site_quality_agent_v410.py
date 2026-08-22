#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,re,statistics,time,urllib.parse,urllib.request
from collections import Counter,defaultdict
from html.parser import HTMLParser
from pathlib import Path

VERSION=410
BASE='https://healthrenewal.org/'
SKIP={'.git','.github','node_modules','vendor','dist','build','_site','artifacts','reports','tests','test-results','coverage','__pycache__'}
AUTH={'who.int','cdc.gov','nih.gov','nimh.nih.gov','ncbi.nlm.nih.gov','pubmed.ncbi.nlm.nih.gov','nice.org.uk','cochranelibrary.com','unicef.org','unesco.org','aap.org','psychiatry.org','apa.org','nhs.uk','clinicaltrials.gov','doi.org'}
HIGH=('انتحار','إيذاء النفس','جرعة','دواء','سرطان','كيماوي','إشعاع','صرع','نوبة','تشخيص','علاج','اضطراب','اكتئاب','suicide','self-harm','medication','dose','cancer','chemotherapy','seizure','diagnosis','treatment')
PROHIBITED=('شفاء مضمون','يعالج نهائيًا','علاج نهائي','نتيجة مضمونة','بديل عن الطبيب','أوقف الدواء','guaranteed cure','stop your medication')
SPACE=re.compile(r'\s+'); TOK=re.compile(r'[\w\u0600-\u06ff]+',re.U); AR=re.compile(r'[\u0600-\u06ff]')
CSS=re.compile(r'([^{}]+)\{([^{}]*)\}',re.S); DECL=re.compile(r'([\w-]+)\s*:\s*([^;]+)'); HEX=re.compile(r'#[0-9a-fA-F]{3,8}\b')

def compact(s): return SPACE.sub(' ',s).strip()
def host_ok(h):
 h=h.lower().removeprefix('www.'); return any(h==d or h.endswith('.'+d) for d in AUTH)
def route(path,root):
 r=path.relative_to(root).as_posix(); return '' if r=='index.html' else (r[:-10] if r.endswith('/index.html') else r)
def public_pages(root):
 out=[]
 for p in sorted(root.rglob('*.html')):
  rel=p.relative_to(root)
  if p.name=='404.html' or any(x in SKIP or x.startswith('.') for x in rel.parts): continue
  out.append(p)
 return out

class P(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.stack=[]; self.title=[]; self.h1=[]; self.parts=[]; self.par=[]; self.links=[]; self.images=[]; self.meta={}; self.canonical=[]; self.jsonld=0; self.hero=[]
 def handle_starttag(self,t,a):
  t=t.lower(); v={str(k).lower():(x or '') for k,x in a}; self.stack.append(t)
  if t=='html': self.meta['lang']=v.get('lang',''); self.meta['dir']=v.get('dir','')
  elif t=='meta':
   k=(v.get('name') or v.get('property') or '').lower(); self.meta[k]=v.get('content','')
  elif t=='link' and 'canonical' in v.get('rel','').lower().split(): self.canonical.append(v.get('href',''))
  elif t=='script' and v.get('type','').lower()=='application/ld+json': self.jsonld+=1
  elif t=='a' and v.get('href'): self.links.append(v['href'])
  elif t=='img': self.images.append(v)
  if t in {'header','section','div'} and 'hero' in v.get('class','').lower():
   s=v.get('style','').lower()
   if ('background:' in s or 'background-color:' in s) and 'color:' not in s: self.hero.append('hero_inline_background_without_explicit_text_color')
 def handle_endtag(self,t):
  t=t.lower()
  if t=='p' and self.par:
   self.parts.append(compact(' '.join(self.par))); self.par=[]
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]==t: del self.stack[i:]; break
 def handle_data(self,d):
  x=compact(d)
  if not x or any(t in self.stack for t in ('script','style','svg','template','noscript')): return
  if 'title' in self.stack:self.title.append(x)
  if 'h1' in self.stack:self.h1.append(x)
  if 'p' in self.stack:self.par.append(x)
  self.parts.append(x)
 def facts(self): return {'title':compact(' '.join(self.title)),'h1':compact(' '.join(self.h1)),'text':compact(' '.join(self.parts))}

def parse(p):
 q=P(); q.feed(p.read_text(encoding='utf-8',errors='replace')); q.close(); return q

def local_target(page,root,href):
 if not href or href.startswith(('#','mailto:','tel:','javascript:','data:','blob:','//')): return None
 u=urllib.parse.urlparse(href)
 if u.scheme in {'http','https'}:
  h=u.netloc.lower().removeprefix('www.')
  if h not in {'healthrenewal.org','khaledaltheeb.github.io'}: return None
  c=root/u.path.lstrip('/')
 elif u.scheme:return None
 else:c=(root/u.path.lstrip('/')) if u.path.startswith('/') else page.parent/u.path
 c=c.resolve()
 try:c.relative_to(root.resolve())
 except ValueError:return None
 if str(u.path).endswith('/'): return c/'index.html'
 if c.suffix:return c
 if (c/'index.html').is_file():return c/'index.html'
 if c.with_suffix('.html').is_file():return c.with_suffix('.html')
 return c

def page_score(path,root):
 p=parse(path); f=p.facts(); text=f['text']; findings=[]; score=100; auth=ext=broken=0
 if not p.meta.get('lang'): findings.append('missing_lang');score-=3
 if (p.meta.get('lang','').startswith('ar') or AR.search(text)) and p.meta.get('dir')!='rtl':findings.append('missing_rtl');score-=3
 if not f['title']:findings.append('missing_title');score-=8
 if not f['h1']:findings.append('missing_h1');score-=8
 if not p.meta.get('description'):findings.append('missing_description');score-=6
 if len(p.canonical)!=1:findings.append('canonical_count_not_one');score-=6
 if p.jsonld==0:findings.append('missing_jsonld');score-=4
 words=len(TOK.findall(text))
 if words<350:findings.append('very_thin_content');score-=18
 elif words<650:findings.append('thin_content');score-=9
 for href in p.links:
  u=urllib.parse.urlparse(href)
  if u.scheme in {'http','https'} and u.netloc:
   h=u.netloc.lower().removeprefix('www.')
   if h not in {'healthrenewal.org','khaledaltheeb.github.io'}:
    ext+=1; auth+=int(host_ok(h))
  else:
   t=local_target(path,root,href)
   if t is not None and not t.exists():broken+=1
 if broken:findings.append('broken_internal_links');score-=min(10,broken*2)
 missing_alt=sum(1 for i in p.images if not i.get('alt','').strip())
 if missing_alt:findings.append('images_missing_alt');score-=min(6,missing_alt*2)
 if p.hero:findings+=p.hero;score-=3
 high=any(x.casefold() in text.casefold() for x in HIGH)
 if high and auth==0:findings.append('high_risk_without_authoritative_source');score-=15
 elif auth==0:findings.append('no_authoritative_source');score-=7
 if any(x.casefold() in text.casefold() for x in PROHIBITED):findings.append('overcertain_health_claim');score-=20
 score=max(0,score); priority=100-score+(20 if high else 0)+(10 if auth==0 else 0)+min(10,broken*2)
 return {'path':path.relative_to(root).as_posix(),'route':route(path,root),'title':f['title'],'h1':f['h1'],'score':score,'priority':priority,'words':words,'risk':'high' if high else 'standard','authoritative_sources':auth,'external_sources':ext,'broken_internal_links':broken,'missing_alt':missing_alt,'findings':sorted(set(findings))}

def lum(c):
 v=[]
 for x in c:
  x=x/255;v.append(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4)
 return .2126*v[0]+.7152*v[1]+.0722*v[2]
def rgb(h):
 h=h.lstrip('#'); h=''.join(x*2 for x in h) if len(h)==3 else h[:6]
 return tuple(int(h[i:i+2],16) for i in (0,2,4)) if len(h)==6 else None
def contrast(a,b):
 a=rgb(a);b=rgb(b)
 if not a or not b:return None
 x,y=sorted((lum(a),lum(b)),reverse=True);return (x+.05)/(y+.05)
def css_audit(root):
 bad=[];hero=[];tiny=[];count=0
 for p in sorted(root.rglob('*.css')):
  rel=p.relative_to(root)
  if any(x in SKIP or x.startswith('.') for x in rel.parts):continue
  count+=1;text=p.read_text(encoding='utf-8',errors='replace')
  for sel,body in CSS.findall(text):
   d={k.lower():v.strip() for k,v in DECL.findall(body)};fg=HEX.search(d.get('color',''));bg=HEX.search(d.get('background-color','') or d.get('background',''))
   if fg and bg:
    r=contrast(fg.group(),bg.group())
    if r and r<4.5:bad.append({'file':rel.as_posix(),'selector':compact(sel)[:200],'ratio':round(r,2),'foreground':fg.group(),'background':bg.group()})
   if 'hero' in sel.lower() and ('background' in d or 'background-color' in d) and 'color' not in d:hero.append({'file':rel.as_posix(),'selector':compact(sel)[:200]})
   m=re.fullmatch(r'([0-9.]+)px',d.get('font-size',''))
   if m and float(m.group(1))<12:tiny.append({'file':rel.as_posix(),'selector':compact(sel)[:200],'font_size':d['font-size']})
 return {'css_files_scanned':count,'low_contrast_count':len(bad),'low_contrast_pairs':bad[:500],'hero_review_count':len(hero),'hero_rules_for_runtime_review':hero[:500],'tiny_font_count':len(tiny),'tiny_font_rules':tiny[:500]}

def query(item):
 raw=item['route'];parts=[x for x in re.split(r'[/_.-]+',raw.lower()) if len(x)>2 and x not in {'index','html','care','guides','special','needs','conditions','library','hubs','sections'} and not x.isdigit()]
 return ' '.join(parts[-10:]) or item['title'] or item['h1']
def getjson(url):
 req=urllib.request.Request(url,headers={'User-Agent':'RawafidSiteQualityAgent/410 (+https://healthrenewal.org/)','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
def research(item,n,email):
 q=query(item);out={'path':item['path'],'query':q,'providers':{},'errors':{},'official_targets':[f'site:{d} {q}' for d in ('who.int','nice.org.uk','cdc.gov','nih.gov','unicef.org','unesco.org')],'policy':'Candidate evidence only; verify claim-level relevance, population, design, recency and limitations before editing health content.'}
 try:
  term=f'({q}) AND (systematic review[pt] OR meta-analysis[pt] OR practice guideline[pt] OR randomized controlled trial[pt] OR review[pt])';par={'db':'pubmed','term':term,'retmode':'json','retmax':str(n),'sort':'pub date','tool':'rawafid_site_quality_agent'}
  if email:par['email']=email
  key=os.getenv('NCBI_API_KEY','').strip()
  if key:par['api_key']=key
  s=getjson('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'+urllib.parse.urlencode(par));ids=s.get('esearchresult',{}).get('idlist',[]);time.sleep(.12 if key else .36)
  out['providers']['pubmed']=[{'pmid':x,'url':f'https://pubmed.ncbi.nlm.nih.gov/{x}/'} for x in ids]
 except Exception as e:out['errors']['pubmed']=str(e)[:300];out['providers']['pubmed']=[]
 try:
  par={'query.bibliographic':q,'rows':str(n),'sort':'relevance'}
  if email:par['mailto']=email
  data=getjson('https://api.crossref.org/works?'+urllib.parse.urlencode(par));out['providers']['crossref']=[{'title':(x.get('title') or [''])[0],'doi':x.get('DOI',''),'type':x.get('type',''),'cited_by':x.get('is-referenced-by-count',0)} for x in data.get('message',{}).get('items',[])[:n]]
 except Exception as e:out['errors']['crossref']=str(e)[:300];out['providers']['crossref']=[]
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('site',nargs='?',default='.',type=Path);a.add_argument('--output-dir',default='artifacts/site-quality-agent-v410',type=Path);a.add_argument('--research',action='store_true');a.add_argument('--research-limit',type=int,default=60);a.add_argument('--per-provider',type=int,default=5);a.add_argument('--research-cycle-seed',type=int,default=int(os.getenv('GITHUB_RUN_NUMBER','0') or 0));x=a.parse_args();root=x.site.resolve();out=x.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 pages=[page_score(p,root) for p in public_pages(root)];pages.sort(key=lambda z:(-z['priority'],z['score'],z['path']));visual=css_audit(root);dossiers=[]
 if x.research and pages:
  limit=min(max(0,x.research_limit),len(pages));top=max(1,limit//2);sel=pages[:top];pool=pages[top:]
  for i in range(limit-len(sel)):
   if pool:sel.append(pool[(x.research_cycle_seed+i)%len(pool)])
  dossiers=[research(i,max(1,min(x.per_provider,20)),os.getenv('RESEARCH_CONTACT_EMAIL','')) for i in sel]
 summary={'pages_scanned':len(pages),'average_score':round(statistics.mean([p['score'] for p in pages]),2) if pages else 0,'pages_below_80':sum(p['score']<80 for p in pages),'high_risk_pages':sum(p['risk']=='high' for p in pages),'broken_internal_links':sum(p['broken_internal_links'] for p in pages),'images_missing_alt':sum(p['missing_alt'] for p in pages),'css_files_scanned':visual['css_files_scanned'],'low_contrast_css_pairs':visual['low_contrast_count'],'research_dossiers':len(dossiers)}
 report={'version':VERSION,'status':'passed','summary':summary,'policy':{'medical':'No medical/psychological claim is auto-rewritten from search results.','visual':'Static CSS checks complement repository Axe/Lighthouse runtime checks.'},'finding_counts':dict(Counter(c for p in pages for c in p['findings'])),'visual_audit':visual,'upgrade_queue':pages,'research_dossiers':dossiers}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(out/'upgrade-queue.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(out/'research-dossiers.json').write_text(json.dumps(dossiers,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
