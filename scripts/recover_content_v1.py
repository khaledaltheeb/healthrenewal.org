#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json, os, re, shutil, subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

W=re.compile(r'[A-Za-z0-9_\u0600-\u06FF]+')
DROP=re.compile(r'<(script|style|noscript|svg)\b[^>]*>.*?</\1>',re.I|re.S)
TAG=re.compile(r'<[^>]+>',re.S); SEC=re.compile(r'<section\b[^>]*>.*?</section>',re.I|re.S)
TITLE=re.compile(r'<title\b[^>]*>(.*?)</title>',re.I|re.S); H1=re.compile(r'<h1\b[^>]*>(.*?)</h1>',re.I|re.S)
REDIR=re.compile(r'http-equiv\s*=\s*["\']refresh|location\.replace\s*\(',re.I)
SKIP={'.git','.github','node_modules','.venv','venv','dist','build','scripts','tests','docs','reports','content','_site','backend','account-backend','migrations'}
NONEDITORIAL={'assets','api','account','auth','admin','login','register','search','downloads','static','css','js','images','img'}
GENERIC={'منصة','روافد','الصحة','العافية','النفسية','دليل','موسوعة','health','renewal','platform','guide','page','home'}

def git(args,check=False,binary=False):
 p=subprocess.run(['git',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if check and p.returncode: raise RuntimeError(p.stderr.decode('utf-8','replace'))
 if p.returncode:return b'' if binary else ''
 return p.stdout if binary else p.stdout.decode('utf-8','replace')

def clean(s):
 s=DROP.sub(' ',s);s=TAG.sub(' ',s);s=html.unescape(s)
 return re.sub(r'\s+',' ',s).strip()

def norm(s):
 s=clean(s).lower();s=re.sub(r'[^a-z0-9\u0600-\u06ff]+',' ',s)
 return re.sub(r'\s+',' ',s).strip()

def first(rx,s):
 m=rx.search(s);return clean(m.group(1)) if m else ''

def metrics(path,s):
 text=clean(s); words=W.findall(text); n=norm(s)
 rep=0
 if len(words)>80:
  chunks=[' '.join(words[i:i+8]).lower() for i in range(0,len(words)-7,8)]
  if chunks: rep=max(0,(.70-len(set(chunks))/len(chunks))*len(words)*.8)
 headings=len(re.findall(r'<h[1-6]\b',s,re.I)); sections=len(SEC.findall(s)); paras=len(re.findall(r'<p\b',s,re.I)); items=len(re.findall(r'<li\b',s,re.I)); links=len(re.findall(r'<a\b[^>]*href\s*=\s*["\']https?://',s,re.I))
 redirect=bool(REDIR.search(s)); score=len(words)+18*headings+28*sections+2.5*min(paras,80)+1.2*min(items,120)+4*min(links,40)-rep
 if redirect:score=min(score,10)
 data=s.encode('utf-8','ignore')
 return {'path':path,'title':first(TITLE,s),'h1':first(H1,s),'words':len(words),'headings':headings,'sections':sections,'paragraphs':paras,'listItems':items,'externalLinks':links,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'bodyHash':hashlib.sha256(n.encode()).hexdigest(),'score':round(score,2),'redirect':redirect}

def public(p):
 if not p.parts:return False
 if p.parts[0] in SKIP:return False
 if p.parts[0].startswith('.') and p.parts[0]!='.well-known':return False
 return not any(x in {'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'} for x in p.parts)

def copy_source(root,site):
 count=0
 for cur,dirs,files in os.walk(root):
  base=Path(cur); rel=base.relative_to(root); dirs[:]=[d for d in dirs if public(rel/d)]
  for name in files:
   src=base/name; rp=src.relative_to(root)
   if not public(rp) or src.is_symlink():continue
   dst=site/rp;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);count+=1
 return count

def html_files(site):return sorted(p for p in site.rglob('*') if p.is_file() and p.suffix.lower() in {'.html','.htm'})
def safe(path):
 p=PurePosixPath(path)
 return not p.is_absolute() and '..' not in p.parts and p.suffix.lower() in {'.html','.htm'} and public(Path(*p.parts))

def history(since,limit=4):
 out=git(['log','--all',f'--since={since}','--no-renames','--diff-filter=AM','--numstat','--format=@@%H','--','*.html','*.htm'])
 commit='';seq=0;rank=defaultdict(list)
 for line in out.splitlines():
  if line.startswith('@@'):commit=line[2:].strip();seq+=1;continue
  parts=line.split('\t',2)
  if len(parts)!=3 or not commit or not safe(parts[2]):continue
  a=int(parts[0]) if parts[0].isdigit() else 0;d=int(parts[1]) if parts[1].isdigit() else 0
  rank[parts[2]].append((a+d,-seq,commit))
 chosen={}
 for path,vals in rank.items():
  cs=[]
  for _,_,c in sorted(vals,key=lambda x:x[1]):
   if c not in cs:cs.append(c);break
  for _,_,c in sorted(vals,reverse=True):
   if c not in cs:cs.append(c)
   if len(cs)>=limit:break
  chosen[path]=cs
 return chosen

def show(commit,path):
 b=git(['show',f'{commit}:{path}'],binary=True)
 return b.decode('utf-8','replace') if b else None

def restore(site,since):
 hist=history(since);current={p.relative_to(site).as_posix() for p in html_files(site)};restored=[]
 for i,path in enumerate(sorted(current|set(hist)),1):
  candidates=[];dst=site/path
  if dst.is_file():
   s=dst.read_text(encoding='utf-8',errors='replace');candidates.append(('HEAD',s,metrics(path,s)))
  for c in hist.get(path,[]):
   s=show(c,path)
   if s:
    m=metrics(path,s)
    if not m['redirect']:candidates.append((c,s,m))
  if not candidates:continue
  best=max(candidates,key=lambda x:(x[2]['score'],x[2]['words'],x[2]['sections'],x[2]['bytes']))
  cur=next((x for x in candidates if x[0]=='HEAD'),None)
  use=cur is None or (best[0]!='HEAD' and (best[2]['words']>=cur[2]['words']+80 or best[2]['score']>=cur[2]['score']*1.08 or (cur[2]['words']<450 and best[2]['words']>cur[2]['words'])))
  if use:
   dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(best[1],encoding='utf-8')
   restored.append({'path':path,'from':best[0],'previousWords':cur[2]['words'] if cur else 0,'restoredWords':best[2]['words'],'previousScore':cur[2]['score'] if cur else 0,'restoredScore':best[2]['score']})
  if i%500==0:print({'processed':i,'restored':len(restored)})
 return restored

def title_key(m):
 tokens=[x for x in W.findall(norm(m['h1'] or m['title'])) if x not in GENERIC]
 return ' '.join(tokens[:18])
def shingles(s):
 x=W.findall(norm(s));return {' '.join(x[i:i+4]) for i in range(len(x)-3)} if len(x)>=4 else set(x)
def jac(a,b):return len(a&b)/len(a|b) if a and b else 0
def route(path):
 p=PurePosixPath(path)
 if p.name=='index.html':
  parent=p.parent.as_posix().strip('.')
  return '/' if not parent else '/'+parent.strip('/')+'/'
 return '/'+p.as_posix()
def preference(path,m):
 p=PurePosixPath(path);numeric=sum(bool(re.fullmatch(r'(?:concept-)?\d+',x)) for x in p.parts)
 return (m['score']+(10 if p.name=='index.html' else 0)-5*numeric,-len(p.parts),-len(path))
def insert(primary,blocks):
 if not blocks:return primary
 payload='\n<!-- content-recovery-merged-sections -->\n'+'\n'.join(blocks)+'\n'
 low=primary.lower()
 for marker in ('</main>','</article>','</body>'):
  i=low.rfind(marker)
  if i!=-1:return primary[:i]+payload+primary[i:]
 return primary+payload
def redirect(target,title):
 t=html.escape(target,quote=True);q=json.dumps(target,ensure_ascii=False);z=html.escape(title or 'تم دمج هذه الصفحة')
 return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{z}</title><link rel="canonical" href="{t}"><meta http-equiv="refresh" content="0;url={t}"><script>location.replace({q});</script></head><body><main><h1>{z}</h1><p>دُمج محتوى هذه الصفحة في النسخة الأكثر اكتمالًا.</p><p><a href="{t}">الانتقال إلى الصفحة الكاملة</a></p></main></body></html>'''

def consolidate(site):
 content={};ms={}
 for p in html_files(site):
  r=p.relative_to(site).as_posix();s=p.read_text(encoding='utf-8',errors='replace');m=metrics(r,s)
  if not m['redirect']:content[r]=s;ms[r]=m
 exact=defaultdict(set);titles=defaultdict(set)
 for p,m in ms.items():
  if m['words']>=80:exact[m['bodyHash']].add(p)
  k=title_key(m)
  if len(k)>=6 and m['words']>=80:titles[k].add(p)
 groups=[set(g) for g in exact.values() if len(g)>1];cache={}
 for paths in titles.values():
  if not 2<=len(paths)<=20:continue
  graph=defaultdict(set);arr=sorted(paths)
  for i,a in enumerate(arr):
   cache.setdefault(a,shingles(content[a]))
   for b in arr[i+1:]:
    cache.setdefault(b,shingles(content[b]))
    if jac(cache[a],cache[b])>=.62:graph[a].add(b);graph[b].add(a)
  seen=set()
  for n in graph:
   if n in seen:continue
   stack=[n];g=set()
   while stack:
    x=stack.pop()
    if x in seen:continue
    seen.add(x);g.add(x);stack.extend(graph[x]-seen)
   if len(g)>1:groups.append(g)
 merged=[]
 for g in groups:
  overlap=[x for x in merged if x&g]
  if not overlap:merged.append(set(g));continue
  u=set(g)
  for x in overlap:u|=x;merged.remove(x)
  merged.append(u)
 results=[];section_reports=[]
 for g in sorted(merged,key=lambda x:(-len(x),sorted(x)[0])):
  valid=[x for x in g if (site/x).is_file()]
  if len(valid)<2:continue
  primary=max(valid,key=lambda x:preference(x,metrics(x,(site/x).read_text(encoding='utf-8',errors='replace'))))
  pc=(site/primary).read_text(encoding='utf-8',errors='replace');known={hashlib.sha256(norm(x).encode()).hexdigest() for x in SEC.findall(pc) if len(W.findall(clean(x)))>=30};adds=[];sources=[]
  for secondary in sorted(x for x in valid if x!=primary):
   sc=(site/secondary).read_text(encoding='utf-8',errors='replace')
   for block in SEC.findall(sc):
    fp=hashlib.sha256(norm(block).encode()).hexdigest()
    if len(W.findall(clean(block)))>=35 and fp not in known:known.add(fp);adds.append(block);sources.append(secondary)
  if adds:(site/primary).write_text(insert(pc,adds),encoding='utf-8');pc=(site/primary).read_text(encoding='utf-8',errors='replace');section_reports.append({'primary':primary,'sectionsAdded':len(adds),'sources':sorted(set(sources))})
  target=route(primary);title=metrics(primary,pc)['h1'] or metrics(primary,pc)['title']
  for secondary in sorted(x for x in valid if x!=primary):
   sm=metrics(secondary,(site/secondary).read_text(encoding='utf-8',errors='replace'));(site/secondary).write_text(redirect(target,sm['h1'] or sm['title'] or title),encoding='utf-8');results.append({'duplicate':secondary,'canonical':primary,'target':target,'duplicateWords':sm['words']})
 return results,section_reports

def threshold(path):
 parts=set(PurePosixPath(path).parts);depth=len(PurePosixPath(path).parts)
 if parts&NONEDITORIAL:return 80
 if path=='index.html' or depth<=2:return 250
 if 'daily-tools' in parts or 'tools' in parts:return 150
 return 450

def inventory(site):
 all=[];thin=[]
 for p in html_files(site):
  r=p.relative_to(site).as_posix();m=metrics(r,p.read_text(encoding='utf-8',errors='replace'));t=threshold(r);m.update({'route':route(r),'threshold':t,'complete':m['redirect'] or m['words']>=t});all.append(m)
  if not m['complete']:thin.append({'path':r,'route':m['route'],'title':m['h1'] or m['title'],'words':m['words'],'threshold':t})
 return sorted(all,key=lambda x:x['path']),sorted(thin,key=lambda x:(x['words'],x['path']))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--site',default='_site');ap.add_argument('--days',type=int,default=10);a=ap.parse_args()
 root=Path(a.root).resolve();site=Path(a.site).resolve();shutil.rmtree(site,ignore_errors=True);site.mkdir(parents=True)
 copied=copy_source(root,site)
 if not (site/'index.html').is_file():raise SystemExit('index.html missing')
 since=(datetime.now(timezone.utc)-timedelta(days=max(a.days,7))).date().isoformat();restored=restore(site,since);duplicates,merged=consolidate(site);pages,thin=inventory(site)
 non=[x for x in pages if not x['redirect']];complete=[x for x in non if x['complete']];ratio=round(len(complete)/len(non),4) if non else 0
 report={'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(),'status':'passed' if ratio>=.9 else 'recovered_with_editorial_backlog','source':'current main plus all Git refs and recent history','historySince':since,'publicFilesCopied':copied,'htmlPages':len(pages),'historicalPagesRestored':len(restored),'duplicateRoutesConsolidated':len(duplicates),'duplicateGroupsMerged':len(merged),'remainingThinPages':len(thin),'nonRedirectPages':len(non),'completePages':len(complete),'completenessRatio':ratio,'restored':restored,'consolidated':duplicates,'mergedSections':merged,'thinPages':thin}
 api=site/'api';api.mkdir(parents=True,exist_ok=True);(api/'content-recovery-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(api/'content-page-inventory.json').write_text(json.dumps({'schemaVersion':1,'pages':pages},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if len(pages)<100:raise SystemExit({'html_inventory_too_small':len(pages)})
 (site/'.nojekyll').touch();print(json.dumps({k:report[k] for k in ('status','htmlPages','historicalPagesRestored','duplicateRoutesConsolidated','duplicateGroupsMerged','remainingThinPages','completenessRatio')},ensure_ascii=False))
if __name__=='__main__':main()
