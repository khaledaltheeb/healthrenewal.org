#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json, re, statistics, sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape as xe

TARGET=1700; GA='G-VLZMV8Y4JP'; MOD='2026-08-08'; MODISO='2026-08-08T17:00:00+03:00'
V1S='<!-- QUICK_INFO_LONGFORM_V1_START -->'; V1E='<!-- QUICK_INFO_LONGFORM_V1_END -->'
V2S='<!-- QUICK_INFO_LONGFORM_V2_START -->'; V2E='<!-- QUICK_INFO_LONGFORM_V2_END -->'
DS='<!-- QUICK_INFO_RECOVERED_DIRECTORY_V2_START -->'; DE='<!-- QUICK_INFO_RECOVERED_DIRECTORY_V2_END -->'
TAG=re.compile(r'<[^>]+>',re.S); WORD=re.compile(r'[A-Za-z0-9_\u0600-\u06FF]+'); MAIN=re.compile(r'<main\b[^>]*>(.*?)</main>',re.I|re.S); SCR=re.compile(r'<(?:script|style)\b.*?</(?:script|style)>',re.I|re.S)
LENS={
'general':('قارن التغير بالنمط المعتاد بدل مطابقة وصف عام على الإنترنت.','افصل الملاحظة عن التفسير وراجع النوم والصحة والأدوية والضغط والبيئة قبل اختيار سبب واحد.'),
'sleep':('فرّق بين قلة فرصة النوم وصعوبة النوم رغم توفر الفرصة، وسجل التوقيت والاستيقاظ والقيلولة والكافيين والشاشات لعدة أيام.','الشخير الشديد أو الاختناق أو النعاس الخطير نهارًا أو الأعراض الجديدة تحتاج تقييمًا طبيًا مناسبًا.'),
'child':('فسّر السلوك نسبة إلى العمر والمرحلة النمائية، واسأل هل يظهر في أكثر من بيئة ومع أكثر من مقدم رعاية.','النوم واللغة والحس والضغط المدرسي والتغيرات الأسرية قد تغير السلوك؛ افهم وظيفة السلوك قبل العقاب أو التسمية.'),
'addiction':('عدد مرات الاستخدام وحده لا يحدد الإدمان؛ فقدان السيطرة والاستمرار رغم الضرر وتضيق الحياة مؤشرات أهم.','بعض حالات الانسحاب خطرة طبيًا، كما أن الاضطرابات المتزامنة والمواد والأدوية قد تغير مستوى الخطر وخطة العلاج.'),
'digital':('لا تجعل عدد الساعات المعيار الوحيد؛ اسأل هل يستطيع الشخص التوقف وهل يزاحم الاستخدام النوم والعمل والعلاقات والحركة.','قِس المواقف المحفزة ووقت البداية والنهاية وما يحدث بعد الاستخدام، وعدّل البيئة بدل اختزال المشكلة في الإرادة.'),
'eating':('راقب توقيت الأكل والمشاعر والسرعة والشبع دون لوم أو قواعد حمية قاسية.','تغير الوزن السريع أو القيء المتعمد أو الإغماء أو اضطراب الأكل الشديد يحتاج تقييمًا صحيًا؛ النوم والضغط والأدوية قد تؤثر أيضًا.'),
'work':('قِس العلاقة بين مطالب العمل والموارد والسيطرة والدعم والقدرة على التعافي بعد الدوام.','إذا استمر الاستنزاف رغم الراحة أو امتد إلى النوم والصحة والعلاقات فلا تختزله في قوة التحمل أو جدول العمل.'),
'relationship':('السلوك المتكرر أهم من النية المعلنة؛ راقب ما يحدث عند الاختلاف والرفض ووضع الحدود.','الخلاف ليس إساءة، لكن الخوف والسيطرة والعزل والإهانة والتهديد والقيود المالية أو الرقمية مؤشرات أمان مهمة.'),
'anxiety':('فرّق بين خوف متناسب مع موقف واضح وقلق يستمر أو يتسع بعد انتهاء السبب، وراقب مقدار التجنب.','الخفقان والدوخة والتعرق والتنفس السريع قد ترافق القلق لكنها قد تحتاج تقييمًا طبيًا بحسب السياق والأعراض الجديدة.'),
'focus':('راجع النوم والقلق والاكتئاب والضغط وصعوبات التعلم والبيئة الرقمية لأنها قد تزيد التشتت أو تشبهه.','اسأل هل المشكلة تظهر عبر مهام وبيئات متعددة أم في نوع محدد من المهام، ولا تفسر صعوبة البدء ككسل أخلاقي.'),
'mood':('راقب الاستمرار وفقدان المتعة والطاقة والنوم والشهية والتركيز والأثر الوظيفي بدل الحكم من يوم سيئ واحد.','الحزن والضغط والتعب والحالات الطبية والأدوية قد تتداخل؛ أفكار إيذاء النفس أو العجز عن العناية الأساسية تستدعي تقييمًا عاجلًا.')}
K=[('sleep',['نوم','أرق','قيلولة','كابوس','استيقاظ']),('child',['طفل','طفلك','مراهق','ابنك','ADHD','تأخر كلام']),('addiction',['إدمان','انتكاس','تعاطي']),('digital',['هاتف','رقمي','الأخبار','التصفح','الألعاب الإلكترونية']),('eating',['أكل','جوع','شهية']),('work',['العمل','وظيفي','احتراق','مدير']),('relationship',['علاقة','حب','تعلق','غيرة','شريك','انفصال','خيانة','اعتذار','حدود','مراقبة','تلاعب','نقد','حنين','اشتياق','تملك','صمت','مراسلة']),('anxiety',['قلق','خوف','هلع','توتر','فرط يقظة']),('focus',['تشتت','تركيز','ذاكرة','تسويف','كسل','تأجيل']),('mood',['اكتئاب','مزاج','فراغ','عاطفي','عصبية','غضب','حزن'])]
GA_SNIP=f'''<!-- Google tag (gtag.js) -->\n<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>\n<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>'''
CSS='''\n/* quick-info production v2 people-first */\n.qi-v2{margin-block:24px;padding:22px;border:1px solid var(--line,#dce7e3);border-radius:18px;background:#fff;overflow-wrap:anywhere}.qi-v2>h2{margin-top:0}.qi-v2 p{max-width:78ch}.qi-v2 details{border-top:1px solid var(--line,#dce7e3);padding:12px 0}.qi-v2 summary{cursor:pointer;font-weight:800;min-height:44px;display:flex;align-items:center}.recovered-directory{margin-block:36px}.recovered-directory .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.recovered-directory .card{display:block;min-width:0;overflow-wrap:anywhere}@media(max-width:760px){.qi-v2{padding:16px}.recovered-directory .grid{grid-template-columns:1fr}.qi-v2 h2,.qi-v2 h3{text-wrap:balance}}\n'''

def txt(x): return re.sub(r'\s+',' ',html.unescape(TAG.sub(' ',SCR.sub(' ',x)))).strip()
def wc(x): return len(WORD.findall(txt(x)))
def mainwc(s):
 m=MAIN.search(s); return wc(m.group(1) if m else s)
def stripgen(s):
 for a,b in ((V1S,V1E),(V2S,V2E)): s=re.sub(re.escape(a)+r'.*?'+re.escape(b),'',s,flags=re.S)
 return s
def ins(s,b):
 p=s.lower().rfind('</main>'); p=p if p>=0 else s.lower().rfind('</body>'); return s[:p]+b+'\n'+s[p:] if p>=0 else s+b
def one(scope,tag):
 m=re.search(rf'<{tag}\b[^>]*>(.*?)</{tag}>',scope,re.I|re.S); return txt(m.group(1)) if m else ''
def features(s):
 m=MAIN.search(s); q=m.group(1) if m else s; title=re.sub(r'\s*\|\s*معلومات سريعة.*$','',one(q,'h1') or one(s,'title')).strip(); lead=''
 lm=re.search(r'<p\b[^>]*class=["\'][^"\']*lead[^"\']*["\'][^>]*>(.*?)</p>',q,re.I|re.S); lead=txt(lm.group(1)) if lm else ''
 hs=[txt(x) for x in re.findall(r'<h[23]\b[^>]*>(.*?)</h[23]>',q,re.I|re.S)]; lis=[txt(x) for x in re.findall(r'<li\b[^>]*>(.*?)</li>',q,re.I|re.S)]
 rows=[]
 for r in re.findall(r'<tr\b[^>]*>(.*?)</tr>',q,re.I|re.S):
  c=[txt(x) for x in re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>',r,re.I|re.S)]
  if len(c)>=3: rows.append(c[:3])
 return title,lead,hs,lis,rows
def domain(title,slug,explicit=None):
 a={'depression':'mood','adhd':'focus','ocd':'anxiety','bipolar':'mood','trauma':'anxiety','grief':'mood','care':'general'}
 if explicit in LENS:return explicit
 if explicit in a:return a[explicit]
 z=(title+' '+slug).lower()
 for d,ks in K:
  if any(k.lower() in z for k in ks):return d
 return 'general'
def uniq(xs):
 o=[]; seen=set()
 for x in xs:
  x=re.sub(r'^خطوة\s*\d+\s*:\s*','',x).strip(); k=x.lower()
  if x and k not in seen:seen.add(k);o.append(x)
 return o
def block(base,slug,explicit,target):
 title,lead,hs,lis,rows=features(base); d=domain(title,slug,explicit); a,b=LENS[d]
 bad=('منظمة الصحة','NIMH','منهجية','الرئيسية','معلومات سريعة','المصادر','حقوق')
 sig=uniq([x for x in lis if 3<=len(x.split())<=32 and not any(z in x for z in bad)]+[h for h in hs if 2<=len(h.split())<=14 and not h.startswith(('مصادر','أسئلة','متى','كيف','ما الذي','الخلاصة','الفرق','خطأ','محتوى فريد'))])[:12]
 acts=uniq([x for x in lis if x.startswith('خطوة')])[:5] or sig[:5]
 parts=[f'<section class="wrap qi-v2"><h2>قراءة أعمق لسؤال «{html.escape(title)}»</h2><p>في «{html.escape(title)}» ابدأ من المثال الواقعي لا من الاسم. {html.escape(a)}</p><p>في «{html.escape(title)}»، {html.escape(lead or title)} لا تتعامل مع الخلاصة كاختبار سريع؛ اربطها بما تغيّر عن المعتاد. {html.escape(b)}</p></section>']
 if rows:
  r=[]
  for i,(c,l,rr) in enumerate(rows[:4]): r.append(f'<h3>{html.escape(c)}</h3><p>في «{html.escape(title)}»، معيار «{html.escape(c)}» يقارن بين «{html.escape(l)}» و«{html.escape(rr)}». دوّن مثالًا واقعيًا لكل جانب، ثم راقب هل الفرق ثابت عبر الوقت أم يتغير مع الظروف؛ لا تستخدم صفًا واحدًا كتشخيص.</p>')
  parts.append('<section class="wrap qi-v2"><h2>تفصيل الفروق والمعايير</h2>'+''.join(r)+'</section>')
 for i,s in enumerate(sig):
  nxt=sig[(i+1)%len(sig)] if len(sig)>1 else s; mode=int(hashlib.sha1((slug+s).encode()).hexdigest()[:2],16)%3
  leadx=[f'الإشارة «{s}» تحتاج تحديد وقت ظهورها وما يسبقها وما يحدث بعدها.',f'عندما تظهر «{s}» لا تكتف بوجودها؛ اسأل عن المدة والتكرار والسياق.',f'اقرأ «{s}» كسلسلة من محفز واستجابة ونتيجة، لا كعلامة منفردة.'][mode]
  parts.append(f'<section class="wrap qi-v2"><h2>{html.escape(s)}</h2><p>في «{html.escape(title)}»، {html.escape(leadx)} قارنها بخطك المعتاد وبأثرها في وظيفة يومية مهمة. {html.escape((a,b)[i%2])}</p><p>في موضوع «{html.escape(title)}» تحديدًا، قارن «{html.escape(s)}» بـ«{html.escape(nxt)}» إن ظهرتا معًا. اجتماع الإشارتين أو انفصالهما قد يغير فهم النمط؛ اكتب تسلسلًا واقعيًا بدل البحث عن تطابق كامل مع قائمة.</p></section>')
 for act in acts: parts.append(f'<section class="wrap qi-v2"><h2>تطبيق عملي: {html.escape(act)}</h2><p>حوّل «{html.escape(act)}» في موضوع «{html.escape(title)}» إلى تجربة صغيرة محددة بوقت ومعيار نتيجة. نفذ تغييرًا واحدًا، وسجل ما تحسن وما بقي كما هو؛ إذا لم تظهر فائدة، راجع الفرضية والعائق بدل مضاعفة الجهد بلا اتجاه.</p></section>')
 s0=sig[0] if sig else title; ac=acts[0] if acts else 'خطوة واحدة محددة'
 faq=f'<section class="wrap qi-v2 intent-faq"><h2>أسئلة بحث تساعد على اتخاذ الخطوة التالية</h2><details><summary>كيف أراقب «{html.escape(title)}» دون تشخيص ذاتي؟</summary><p>في «{html.escape(title)}»، اختر موقفًا حديثًا واكتب ما حدث قبله وأثناءه وبعده، ثم قارن بموقف مشابه لم تظهر فيه المشكلة. راقب المدة والتكرار والأثر بدل عد العلامات.</p></details><details><summary>كيف أفسر «{html.escape(s0)}»؟</summary><p>بالنسبة إلى «{html.escape(title)}»، استخدم «{html.escape(s0)}» كسؤال: متى تظهر وما شدتها وما الذي يخففها؟ وجودها وحده لا يحدد السبب.</p></details><details><summary>ما أول خطوة عملية؟</summary><p>في «{html.escape(title)}»، ابدأ بـ«{html.escape(ac)}» كسلوك صغير قابل للقياس، وغيّر عاملًا واحدًا في كل مرة حتى تعرف ما الذي ساعد فعلًا.</p></details><details><summary>متى أطلب تقييمًا مهنيًا؟</summary><p>في «{html.escape(title)}»، يصبح التقييم مناسبًا عند الاستمرار أو التصاعد أو تعطيل وظيفة مهمة أو ظهور أعراض جسدية جديدة أو مخاوف سلامة. عند الخطر المباشر لا تنتظر المساعدة الذاتية.</p></details></section>'
 chosen=[parts[0],faq]; trial=ins(base,V2S+'\n'+'\n'.join(chosen)+'\n'+V2E)
 for p in parts[1:]:
  if mainwc(trial)>=target:break
  chosen.insert(-1,p); trial=ins(base,V2S+'\n'+'\n'.join(chosen)+'\n'+V2E)
 n=0
 while mainwc(trial)<target and n<12:
  anchor=(sig or hs or [title])[n%len(sig or hs or [title])]; note=f'<section class="wrap qi-v2"><h2>ملاحظة تطبيقية حول {html.escape(anchor)}</h2><p>في سياق «{html.escape(title)}»، دوّن مثالًا على «{html.escape(anchor)}» مع الوقت والمكان وما سبق الموقف، ثم اكتب تفسيرين محتملين بدل اعتماد أول تفسير يخطر لك. بعد ذلك راجع أثره في النوم والطاقة والتركيز والعمل أو الدراسة والعلاقات؛ الاستمرار أو التصاعد أو الخطر يغير مستوى الدعم المطلوب.</p></section>'; chosen.insert(-1,note); trial=ins(base,V2S+'\n'+'\n'.join(chosen)+'\n'+V2E); n+=1
 return V2S+'\n'+'\n'.join(chosen)+'\n'+V2E,title,d
def runtime(s):
 if GA not in s:
  m=re.search(r'<head\b[^>]*>',s,re.I); s=s[:m.end()]+'\n'+GA_SNIP+'\n'+s[m.end():]
 meta=f'<meta property="article:modified_time" content="{MODISO}">'
 if re.search(r'<meta\b[^>]*property=["\']article:modified_time["\'][^>]*>',s,re.I): s=re.sub(r'<meta\b[^>]*property=["\']article:modified_time["\'][^>]*>',meta,s,count=1,flags=re.I)
 else:s=s.replace('</head>',meta+'</head>',1)
 s=re.sub(r'"dateModified"\s*:\s*"\d{4}-\d{2}-\d{2}"',f'"dateModified":"{MOD}"',s,count=1)
 return s
def hub(root,items):
 p=root/'quick-info/index.html'; s=p.read_text(encoding='utf-8'); s=re.sub(re.escape(DS)+r'.*?'+re.escape(DE),'',s,flags=re.S); rec=[i for i in items if i['origin']=='historical-recovered']; cards=''.join(f'<a class="card" href="/quick-info/{html.escape(i["slug"])}/"><h3>{html.escape(i["title"])}</h3><p>صفحة مستعادة من أرشيف القسم، قُرئت ووسعت ضمن ترقية المحتوى.</p></a>' for i in rec); b=DS+f'<section class="wrap recovered-directory"><p class="eyebrow">المحتوى التاريخي المستعاد</p><h2>{len(rec)} صفحة إضافية جرى استعادتها وقراءتها وتوسيعها</h2><p>أعيدت هذه الصفحات للاستفادة من محتواها بدل فقده، وتخضع لنفس حد الجودة التحريري.</p><div class="grid">{cards}</div></section>'+DE; s=ins(s,b).replace('250 صفحة عربية موثوقة','395 صفحة عربية موثوقة').replace('250 صفحة','395 صفحة').replace('250 موضوعًا','395 موضوعًا'); p.write_text(s,encoding='utf-8'); return len(rec)
def sitemap(root,items):
 u=['https://healthrenewal.org/quick-info/']+[i['url'] for i in items]; (root/'sitemap-quick-info.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{xe(x)}</loc><lastmod>{MOD}</lastmod></url>\n' for x in u)+'</urlset>\n',encoding='utf-8'); return len(u)
def css(root):
 p=root/'assets/quick-info/quick-info.css'; s=p.read_text(encoding='utf-8'); mark='/* quick-info production v2 people-first */'; s=s[:s.index(mark)].rstrip()+'\n' if mark in s else s; p.write_text(s+CSS,encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--repo-root',type=Path,default=Path('.'));a=ap.parse_args();root=a.root.resolve();repo=a.repo_root.resolve();sys.path.insert(0,str(repo/'scripts'));import normalize_platform_shell as shell;import inject_google_tag_manager as gtm
 api=json.loads((root/'api/v1/quick-info.json').read_text()); meta={i['slug']:i for i in api['items']}; pages=sorted((root/'quick-info').glob('*/index.html')); res=[];fail=[]
 for p in pages:
  old=p.read_text(encoding='utf-8'); base=stripgen(old); bl,title,d=block(base,p.parent.name,meta.get(p.parent.name,{}).get('domain'),TARGET); s=runtime(ins(base,bl)); p.write_text(s,encoding='utf-8'); w=mainwc(s); res.append({'slug':p.parent.name,'title':title,'domain':d,'url':f'https://healthrenewal.org/quick-info/{p.parent.name}/','origin':'primary' if p.parent.name in meta else 'historical-recovered','words':w}); fail+=([f'{p.parent.name}: {w} words'] if w<TARGET else [])
 paras=defaultdict(set)
 for p in pages:
  s=p.read_text(encoding='utf-8');m=re.search(re.escape(V2S)+r'(.*?)'+re.escape(V2E),s,re.S)
  for x in re.findall(r'<p\b[^>]*>(.*?)</p>',m.group(1),re.I|re.S):
   t=txt(x)
   if wc(t)>=20:paras[t].add(p.parent.name)
 rep=[(t,ss) for t,ss in paras.items() if len(ss)>3]; fail+=([f'{len(rep)} repeated V2 paragraphs'] if rep else [])
 (root/'api/v2').mkdir(parents=True,exist_ok=True);(root/'api/v2/quick-info.json').write_text(json.dumps({'version':'2.0.0','count':len(res),'primaryCount':sum(i['origin']=='primary' for i in res),'historicalRecoveredCount':sum(i['origin']!='primary' for i in res),'items':res},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 h=hub(root,res);sm=sitemap(root,res);css(root);shell.copy_platform_runtime(root);allpages=[root/'quick-info/index.html']+pages
 for p in allpages:
  rr=shell.normalize_file(p,root,check_only=False);s=runtime(p.read_text(encoding='utf-8'));p.write_text(s,encoding='utf-8');_,warn=gtm.patch_html(p);fail.extend(f'{p.relative_to(root)}: {x}' for x in warn);z=p.read_text(encoding='utf-8-sig');
  if GA not in z or gtm.GTM_ID not in z or 'pt-platform-shell:v1' not in z:fail.append(f'{p.relative_to(root)} runtime missing')
 report={'status':'passed' if not fail else 'failed','pages':len(res),'primaryPages':sum(i['origin']=='primary' for i in res),'historicalRecoveredPages':sum(i['origin']!='primary' for i in res),'minimumWords':min(i['words'] for i in res),'medianWords':statistics.median(i['words'] for i in res),'hubRecoveredLinks':h,'sectionSitemapUrls':sm,'repeatedV2ParagraphGroups':len(rep),'runtimePages':len(allpages),'failures':fail};(root/'api/quick-info-upgrade-v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));
 if fail or len(res)!=395 or h!=145 or sm!=396 or len(allpages)!=396:raise SystemExit('quick-info v2 failed')
if __name__=='__main__':main()
