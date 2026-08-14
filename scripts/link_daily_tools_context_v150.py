from __future__ import annotations

import html
import json
import re
from pathlib import Path

SITE_NAME='منصة روافد'
MARK='daily-tools-crosslinks-v150'
REPORT='api/daily-tools-linking-v150.json'
DOMAIN_PATHS={
 'التهدئة وتنظيم الضغط':'/learning-paths/stress-regulation-7-days/',
 'الأفكار والمشاعر':'/learning-paths/thoughts-emotions-7-days/',
 'النوم والطاقة':'/learning-paths/sleep-energy-7-days/',
 'التركيز والتنظيم التنفيذي':'/learning-paths/focus-executive-7-days/',
 'العلاقات والحدود':'/learning-paths/relationships-boundaries-7-days/',
 'الأسرة والوالدية':'/learning-paths/family-parenting-7-days/',
 'رفاه مقدمي الرعاية':'/learning-paths/caregiver-wellbeing-7-days/',
 'الأطفال والمراهقون والتربية الدامجة':'/learning-paths/inclusive-support-7-days/',
 'الفقد والتغير والمرونة':'/learning-paths/change-resilience-7-days/',
 'طلب المساعدة والسلامة':'/learning-paths/help-seeking-safety-7-days/',
}

DOMAIN_HUBS={
 'التهدئة وتنظيم الضغط':('/psychology/stress/','/psychology/anxiety/'),
 'الأفكار والمشاعر':('/psychology/rumination-overthinking/','/psychology/emotion-regulation/'),
 'النوم والطاقة':('/evidence-guides/insomnia-and-sleep/','/evidence-guides/sleep-mental-health-evidence-brief/'),
 'التركيز والتنظيم التنفيذي':('/psychology/attention-concentration/','/psychology/procrastination/'),
 'العلاقات والحدود':('/psychology/boundaries/','/sectors/family/conflict-repair/'),
 'الأسرة والوالدية':('/sectors/child/','/sectors/family/'),
 'رفاه مقدمي الرعاية':('/evidence-guides/caregiver-wellbeing/','/sectors/family/caregiver-burnout/'),
 'الأطفال والمراهقون والتربية الدامجة':('/evidence-guides/inclusive-family-support/','/special-needs/'),
 'الفقد والتغير والمرونة':('/psychology/resilience/','/evidence-guides/grief-and-loss/'),
 'طلب المساعدة والسلامة':('/safety/','/care-guides/family-mental-health-crisis-plan/'),
}
H1_RE=re.compile(r'<h1[^>]*>(.*?)</h1>',re.I|re.S)
DOMAIN_RE=re.compile(r'المجال:\s*([^<]+)</span>',re.I)
LEAD_RE=re.compile(r'<h1[^>]*>.*?</h1>\s*<p>(.*?)</p>',re.I|re.S)
TAG_RE=re.compile(r'<[^>]+>')

def clean(v:str)->str:
 return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',v or ''))).strip()

def url_to_path(site:Path,url:str)->Path:
 return site / url.strip('/') / 'index.html' if url!='/' else site/'index.html'

def extract_h1(path:Path)->str:
 s=path.read_text(encoding='utf-8',errors='ignore'); m=H1_RE.search(s)
 return clean(m.group(1)) if m else path.parent.name

def collect_tools(site:Path):
 tools=[]
 for p in sorted((site/'daily-tools').glob('*/index.html')):
  s=p.read_text(encoding='utf-8',errors='ignore')
  slug=p.parent.name
  h=H1_RE.search(s); d=DOMAIN_RE.search(s); lead=LEAD_RE.search(s)
  title=clean(h.group(1)) if h else slug
  domain=clean(d.group(1)) if d else ('النوم والطاقة' if slug=='sleep-wind-down-plan' else '')
  intent=clean(lead.group(1)) if lead else ''
  if domain not in DOMAIN_HUBS: raise SystemExit(f'Unmapped domain for {slug}: {domain!r}')
  tools.append({'slug':slug,'title':title,'domain':domain,'intent':intent,'path':p})
 if len(tools)!=150: raise SystemExit(f'Expected 150 tools, got {len(tools)}')
 return tools

def module_re(kind:str):
 return re.compile(r'<section\b[^>]*data-'+re.escape(MARK)+r'="'+re.escape(kind)+r'"[^>]*>.*?</section>',re.I|re.S)

def without_module(text:str,kind:str)->str:
 return module_re(kind).sub('',text)

def inject_before_main_end(text:str,module:str)->str:
 i=text.lower().rfind('</main>')
 if i<0: raise SystemExit('Missing </main>')
 return text[:i]+module+'\n'+text[i:]

def upsert_module(text:str,kind:str,module:str)->str:
 m=module_re(kind).search(text)
 if m:
  if m.group(0)==module: return text
  return text[:m.start()]+module+text[m.end():]
 return inject_before_main_end(text,module)

def hub_module(domain:str, tools:list[dict])->str:
 items=''.join(f'<li><a href="/daily-tools/{html.escape(t["slug"],quote=True)}/">{html.escape(t["title"])}</a></li>' for t in tools)
 return (f'<section data-{MARK}="hub"><h2>أدوات عملية مرتبطة بهذا الموضوع</h2>'
         f'<p>يمكن الانتقال من القراءة إلى تطبيق منظم عبر أدوات روافد اليومية. هذه الأدوات تثقيفية وغير تشخيصية وتحفظ السجلات محليًا على الجهاز.</p>'
         f'<ul>{items}</ul><p><a href="/daily-tools/">استعرض جميع الأدوات اليومية</a></p></section>')

def path_module(tools:list[dict], existing:set[str])->str:
 extra=[t for t in tools if f'/daily-tools/{t["slug"]}/' not in existing]
 if not extra: return ''
 items=''.join(f'<li><a href="/daily-tools/{html.escape(t["slug"],quote=True)}/">{html.escape(t["title"])}</a></li>' for t in extra)
 return (f'<section data-{MARK}="path"><h2>أدوات إضافية بعد المسار الأساسي</h2>'
         f'<p>يحافظ المسار أعلاه على تسلسله الأساسي القصير. ويمكن التوسع عند الحاجة بهذه الأدوات من المجال نفسه دون ضرورة تنفيذها كلها.</p><ul>{items}</ul></section>')

def tool_module(hubs:list[tuple[str,str]], path_info:tuple[str,str])->str:
 links=' · '.join(f'<a href="{html.escape(url,quote=True)}">{html.escape(title)}</a>' for url,title in hubs)
 purl,ptitle=path_info
 return (f'<section data-{MARK}="tool"><h2>مسار وقراءة أوسع مرتبطة بالأداة</h2>'
         f'<p><strong>مسار تعلم:</strong> <a href="{html.escape(purl,quote=True)}">{html.escape(ptitle)}</a></p>'
         f'<p><strong>أدلة موضوعية:</strong> {links}</p><p>استخدم الأدلة لفهم السياق والحدود، ثم عد إلى الأداة للتطبيق العملي دون اعتبارها تشخيصًا أو بديلًا عن الرعاية المهنية.</p></section>')

def apply(site:Path|str)->dict:
 site=Path(site).resolve(); tools=collect_tools(site)
 grouped={d:[] for d in DOMAIN_HUBS}
 for t in tools: grouped[t['domain']].append(t)
 hub_titles={}; path_titles={}; changed_hubs=changed_paths=changed_tools=0
 # Validate hubs, then inject complete category lists into two broad topical hubs.
 for domain,hubs in DOMAIN_HUBS.items():
  if len(grouped[domain])!=15: raise SystemExit(f'{domain}: expected 15 tools, got {len(grouped[domain])}')
  for url in hubs:
   p=url_to_path(site,url)
   if not p.is_file(): raise SystemExit(f'Missing hub: {url}')
   hub_titles[url]=extract_h1(p)
   text=p.read_text(encoding='utf-8',errors='ignore')
   out=upsert_module(text,'hub',hub_module(domain,grouped[domain]))
   if out!=text: p.write_text(out,encoding='utf-8'); changed_hubs+=1
 # Expand each learning path with optional tools from the same domain while preserving its core sequence.
 for domain,purl in DOMAIN_PATHS.items():
  p=url_to_path(site,purl)
  if not p.is_file(): raise SystemExit(f'Missing learning path: {purl}')
  path_titles[purl]=extract_h1(p)
  text=p.read_text(encoding='utf-8',errors='ignore'); base=without_module(text,'path')
  existing=set(re.findall(r'href=["\'](/daily-tools/[^"\']+/)["\']',base,re.I))
  module=path_module(grouped[domain],existing)
  out=upsert_module(text,'path',module) if module else text
  if out!=text: p.write_text(out,encoding='utf-8'); changed_paths+=1
 # Reciprocal links from every tool to its learning path and two topical hubs.
 for t in tools:
  hubs=[(u,hub_titles[u]) for u in DOMAIN_HUBS[t['domain']]]
  purl=DOMAIN_PATHS[t['domain']]; path_info=(purl,path_titles[purl])
  text=t['path'].read_text(encoding='utf-8',errors='ignore')
  out=upsert_module(text,'tool',tool_module(hubs,path_info))
  if out!=text: t['path'].write_text(out,encoding='utf-8'); changed_tools+=1
 # Strict validation.
 errors=[]; expected_inlinks={t['slug']:0 for t in tools}
 for domain,hubs in DOMAIN_HUBS.items():
  for url in hubs:
   text=url_to_path(site,url).read_text(encoding='utf-8',errors='ignore')
   if text.count(f'data-{MARK}="hub"')!=1: errors.append(f'{url}: hub module count')
   for t in grouped[domain]:
    href=f'/daily-tools/{t["slug"]}/'
    if href not in text: errors.append(f'{url}: missing {href}')
    else: expected_inlinks[t['slug']]+=1
 # Every learning path must now expose all 15 tools in its domain (core + optional).
 learning_path_coverage={}
 for domain,purl in DOMAIN_PATHS.items():
  text=url_to_path(site,purl).read_text(encoding='utf-8',errors='ignore')
  linked=set(re.findall(r'href=["\'](/daily-tools/[^"\']+/)["\']',text,re.I))
  expected={f'/daily-tools/{t["slug"]}/' for t in grouped[domain]}
  missing=expected-linked
  if missing: errors.append(f'{purl}: missing {len(missing)} domain tools')
  learning_path_coverage[domain]=len(expected & linked)
 for t in tools:
  text=t['path'].read_text(encoding='utf-8',errors='ignore')
  if text.count(f'data-{MARK}="tool"')!=1: errors.append(f'{t["slug"]}: tool module count')
  for u in DOMAIN_HUBS[t['domain']]:
   if f'href="{u}"' not in text: errors.append(f'{t["slug"]}: missing reciprocal {u}')
  purl=DOMAIN_PATHS[t['domain']]
  if f'href="{purl}"' not in text: errors.append(f'{t["slug"]}: missing learning path {purl}')
  if expected_inlinks[t['slug']]<2: errors.append(f'{t["slug"]}: only {expected_inlinks[t["slug"]]} external hub inlinks')
 if errors: raise SystemExit('Daily tools contextual linking failed:\n'+'\n'.join(errors[:100]))
 report={
  'status':'passed','contract':'v150-contextual-linking','tools':150,'domains':10,
  'topicalHubs':sum(len(v) for v in DOMAIN_HUBS.values()),
  'minimumExternalTopicalHubInlinksPerTool':min(expected_inlinks.values()),
  'maximumExternalTopicalHubInlinksPerTool':max(expected_inlinks.values()),
  'reciprocalHubLinksPerTool':2,'learningPathsEnhanced':10,'toolsLinkedFromLearningPaths':sum(learning_path_coverage.values()),'learningPathLinksPerTool':1,'hubModulesChanged':changed_hubs,'learningPathModulesChanged':changed_paths,'toolModulesChanged':changed_tools,
 }
 out=site/REPORT; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return report

if __name__=='__main__':
 import sys
 print(json.dumps(apply(Path(sys.argv[1] if len(sys.argv)>1 else '_site')),ensure_ascii=False,indent=2))
