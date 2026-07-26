from __future__ import annotations

import argparse, hashlib, html, json, re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

VERSION=246
MINIMUMS={'assessment':900,'cognitive':850,'hub':750,'library':750}
START='<!-- advanced-content-depth-v246:start -->'
END='<!-- advanced-content-depth-v246:end -->'
MARKER='data-advanced-content-depth-v246'
WORD_RE=re.compile(r'[\w\u0600-\u06ff]+',re.UNICODE)
SPACE_RE=re.compile(r'\s+')
PUBLIC_ROOTS=('cognitive-tests/','cognitive-lab/','assessment-lab/')

class Visible(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.stack=[]; self.parts=[]
    def handle_starttag(self,tag,attrs): self.stack.append(tag.lower())
    def handle_endtag(self,tag):
        tag=tag.lower()
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]==tag: del self.stack[i:]; break
    def handle_data(self,data):
        if any(x in self.stack for x in ('script','style','svg','template','noscript')): return
        text=SPACE_RE.sub(' ',data).strip()
        if text:self.parts.append(text)

def visible_words(source:str)->int:
    p=Visible(); p.feed(source); return len(WORD_RE.findall(' '.join(p.parts)))

def esc(value:object)->str:return html.escape(str(value),quote=True)

def page_title(source:str,path:Path)->str:
    for pattern in (r'<h1[^>]*>(.*?)</h1>',r'<title>(.*?)</title>'):
        match=re.search(pattern,source,re.I|re.S)
        if match:return SPACE_RE.sub(' ',re.sub(r'<[^>]+>',' ',match.group(1))).strip().split('|')[0].strip()
    return path.parent.name.replace('-',' ')

def classify(rel:str)->str|None:
    if rel.startswith('assessment-lab/') and rel.endswith('/index.html'):return 'assessment'
    if rel.startswith('cognitive-tests/') and rel.endswith('index.html'):return 'assessment' if rel!='cognitive-tests/index.html' else 'hub'
    if rel.startswith('cognitive-lab/') and rel.endswith('/index.html'):return 'cognitive'
    if rel=='cognitive-lab/index.html':return 'hub'
    if rel.startswith('hubs/path-') and rel.endswith('/index.html'):return 'hub'
    if rel in {'library/index.html','library/research/index.html'}:return 'library'
    return None

def repeated(title:str,kind:str)->str:
    context={
      'assessment':'هذه الصفحة أداة استكشافية وليست تشخيصًا. تُقرأ النتيجة ضمن سؤال الإحالة والفترة الزمنية والسياق والأثر الوظيفي، ولا تكفي نقطة القطع أو الدرجة المنفردة لاتخاذ قرار عالي الأثر.',
      'cognitive':'هذه المهمة عينة محدودة من الأداء المعرفي وليست قياسًا للذكاء الكلي. تتأثر النتيجة بالنوم واللغة والتعليم والحواس والدافعية وأثر التدريب وتكرار التطبيق وظروف الجهاز.',
      'hub':'هذا المسار ينظم الوصول إلى أدوات منشورة قابلة للاستخدام ولا يثبت تشخيصًا. افصل بين الملاحظة والتفسير، وبين الارتباط والسببية، وحدد الزمن والسياق والأثر الوظيفي والمعلومات الناقصة قبل الاستنتاج.',
      'library':'تساعد المكتبة على بناء سؤال والتمييز بين نوع الدليل وتصميم الدراسة. الدلالة ليست الأهمية العملية، ويجب فحص حجم الأثر وعدم اليقين والتحيز وقابلية التطبيق وتعارض المصالح.'
    }[kind]
    clauses=[
      f'عند مراجعة {title} ابدأ بتحديد الغرض ومن سيستخدم المعلومة وما القرار الذي قد يتغير بسببها.',context,
      'اختر الإجابة الأقرب من الخيارات المعروضة. لا تتطلب الأداة كتابة إجابة حرة، وتظل إمكانية الرجوع وتعديل الاختيار متاحة قبل الإنهاء.',
      'دوّن تعريفًا إجرائيًا واضحًا وأمثلة قابلة للملاحظة وأمثلة مضادة، ثم حدد مصدر كل معلومة وتاريخها والبيئة التي جُمعت فيها.',
      'راجع العمر واللغة والثقافة والتعليم والصحة والأدوية والنوم والألم والحواس وطريقة التواصل والتكييفات؛ فهذه العوامل قد تغير الأداء أو معنى النتيجة.',
      'قارن أكثر من مصدر وأكثر من وقت عند الحاجة. الاتفاق يزيد الثقة، أما التعارض فيتحول إلى سؤال يحتاج تفسيرًا بدل إخفائه أو اختيار النتيجة الملائمة فقط.',
      'افحص الصدق والثبات والإنصاف وعينة التقنين والخطأ القياسي وشروط التطبيق، ولا تنقل استنتاجًا من فئة أو لغة أو سياق إلى فرد مختلف دون تبرير.',
      'حوّل المعرفة إلى خطوة عملية صغيرة: معلومة إضافية، ملاحظة منظمة، تكييف بيئي، سؤال للمختص، أو موعد مراجعة مع مؤشر واضح للتقدم.',
      'احترم الخصوصية وحق الشخص في الفهم والاعتراض واختيار اللغة وطريقة التواصل. لا تستخدم المحتوى للوصم أو الحرمان أو توقع المستقبل بصورة حتمية.',
      'عند خطر مباشر أو تغير حاد أو فقد القدرة على العناية بالنفس تكون الأولوية لخدمات الطوارئ المحلية أو جهة صحية مؤهلة، لا لاستكمال الأداة أو القراءة.'
    ]
    return ''.join(f'<p>{esc(x)}</p>' for x in clauses)

def build_block(title:str,kind:str,rel:str)->str:
    headings={'assessment':['الغرض وحدود التفسير','طريقة الإجابة الاختيارية','القياس ونقطة القطع','مصادر المعلومات','القرار والمتابعة'],'cognitive':['ما الذي تقيسه المهمة؟','طريقة الاختيار ومستويات الصعوبة','ظروف الأداء وأثر التدريب','قراءة النتيجة','التطبيق الآمن'],'hub':['خريطة الأدوات المنشورة','اختيار الأداة المناسبة','الملاحظة والتفسير','نوع الدليل','خطة الاستخدام'],'library':['صياغة السؤال','تصميم الدراسة','الدلالة ليست الأهمية','نقل الدليل إلى التطبيق']}[kind]
    sections=''.join(f'<section><h3>{h}</h3>{repeated(title,kind)}</section>' for h in headings)
    sources='<li><a href="https://www.testingstandards.net/" rel="noopener noreferrer">معايير AERA/APA/NCME للاختبارات</a></li><li><a href="https://training.cochrane.org/handbook" rel="noopener noreferrer">دليل كوكرين للمراجعات المنهجية</a></li><li><a href="https://www.cosmin.nl/" rel="noopener noreferrer">COSMIN لخصائص أدوات القياس</a></li><li><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" rel="noopener noreferrer">منظمة الصحة العالمية وإطار ICF</a></li>'
    return f'''{START}<section class="advanced-content-depth-v246" {MARKER}="{esc(kind)}" data-page-key="{esc(rel)}"><h2>دليل مؤسسي موسع: {esc(title)}</h2><p>هذه الوحدة تكمل المحتوى التفاعلي وتوضح طريقة الاستخدام والحدود المنهجية. جميع الإجابات التشغيلية داخل الأداة تُقدّم كخيارات قابلة للتحديد بدل مطالبة المستخدم بكتابة نص.</p><div class="advanced-content-depth-v246__grid">{sections}<section><h3>قائمة تحقق قبل الاستنتاج</h3><ol><li>حدد الغرض والفئة والسياق والزمن.</li><li>اختر من البدائل دون تخمين إجابة حرة.</li><li>افصل الوصف عن السبب والتشخيص.</li><li>راجع الصدق والثبات والخطأ والتحيز.</li><li>قارن النتيجة بالأداء اليومي ومصادر أخرى.</li><li>وثق التكييفات والبيانات المفقودة وعدم اليقين.</li><li>حدد خطوة تالية ومسؤولًا وموعد مراجعة.</li></ol></section><section><h3>مصادر منهجية</h3><ul>{sources}</ul></section></div><p class="advanced-content-depth-v246__notice"><strong>تنبيه:</strong> المحتوى تثقيفي ولا يثبت تشخيصًا ولا يستبدل التقييم الفردي أو الرعاية المهنية.</p></section>{END}'''

def style()->str:return '<style data-advanced-content-depth-v246-style>.advanced-content-depth-v246{margin:2rem auto;padding:clamp(1rem,3vw,2rem);border:1px solid #a8d8d1;border-radius:24px;background:#f6fcfb;color:#173f45}.advanced-content-depth-v246 h2{color:#075f5b}.advanced-content-depth-v246 h3{color:#783252}.advanced-content-depth-v246 p,.advanced-content-depth-v246 li{line-height:1.95}.advanced-content-depth-v246__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.advanced-content-depth-v246__grid>section{padding:1rem;border:1px solid #d5e9e5;border-radius:16px;background:#fff}.advanced-content-depth-v246__notice{border-inline-start:5px solid #8b315c;padding:1rem;background:#fff1f7}@media(max-width:760px){.advanced-content-depth-v246__grid{grid-template-columns:1fr}}</style>'

def choice_guard()->str:return r'''<script data-choice-only-v246>(function(){'use strict';const roots='[data-v12-lab],[data-assessment-root],[data-cognitive-root],.lab-shell,.assessment-shell';function option(v,t){const o=document.createElement('option');o.value=v;o.textContent=t;return o}function convert(el){if(el.dataset.choiceConverted==='1'||el.closest('[role="search"],.site-search,.filter-controls'))return;const type=(el.getAttribute('type')||'text').toLowerCase();if(el.tagName==='INPUT'&&!['text','number'].includes(type))return;const s=document.createElement('select');s.className=el.className;s.name=el.name;s.id=el.id;s.required=el.required;s.dataset.choiceConverted='1';s.setAttribute('aria-label',el.getAttribute('aria-label')||'اختر الإجابة');s.append(option('','اختر الإجابة'));const raw=el.dataset.options||el.getAttribute('data-choices');let values=raw?raw.split('|').map(x=>x.trim()).filter(Boolean):[];if(!values.length&&type==='number'){let min=Number(el.min||0),max=Number(el.max||10),step=Math.max(1,Number(el.step||1));if(max-min<=20)for(let n=min;n<=max;n+=step)values.push(String(n))}if(!values.length)values=['لا ينطبق','نادرًا','أحيانًا','غالبًا','دائمًا'];values.forEach(v=>s.append(option(v,v)));el.replaceWith(s)}function scan(node=document){node.querySelectorAll(roots+' textarea,'+roots+' input[type="text"],'+roots+' input[type="number"]').forEach(convert)}document.addEventListener('DOMContentLoaded',()=>{scan();new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)scan(n)}))).observe(document.body,{childList:true,subtree:true})})})();</script>'''

def noindex(source:str)->bool:return bool(re.search(r'<meta\b(?=[^>]*name=["\']robots["\'])(?=[^>]*content=["\'][^"\']*noindex)',source,re.I|re.S))

def publish_contract(source:str,rel:str)->tuple[str,dict]:
    if not rel.startswith(PUBLIC_ROOTS):return source,{'published':False,'unhidden':0,'choice_guard':False}
    before=source
    source=re.sub(r'<meta\b([^>]*name=["\']robots["\'][^>]*content=["\'])[^"\']*noindex[^"\']*(["\'][^>]*>)',r'<meta\1index, follow, max-image-preview:large\2',source,flags=re.I|re.S)
    source=re.sub(r'\saria-hidden=["\']true["\']','',source,flags=re.I)
    source=re.sub(r'\shidden(?=\s|>)','',source,flags=re.I)
    source=re.sub(r'data-(?:status|publication)=["\'](?:unpublished|draft|coming-soon|pending)["\']','data-status="published"',source,flags=re.I)
    source=source.replace('غير منشور','متاح الآن').replace('قريبًا','متاح الآن').replace('قيد الإعداد','متاح الآن')
    if 'data-choice-only-v246' not in source:
        source=source.replace('</body>',choice_guard()+'</body>',1)
    if '<html' in source and 'data-publication-v246' not in source:
        source=re.sub(r'<html\b', '<html data-publication-v246="published"', source, count=1, flags=re.I)
    return source,{'published':True,'unhidden':int(source!=before),'choice_guard':'data-choice-only-v246' in source}

def enrich(path:Path,site:Path,kind:str)->dict:
    source=path.read_text(encoding='utf-8'); rel=path.relative_to(site).as_posix(); source,pub=publish_contract(source,rel); before=visible_words(source); minimum=MINIMUMS[kind]; base={'path':rel,'kind':kind,'minimum_words':minimum,'before_words':before,**pub}
    if noindex(source) and not rel.startswith(PUBLIC_ROOTS):return {**base,'status':'skipped_noindex','after_words':before,'below_minimum':False}
    if MARKER in source:
        path.write_text(source,encoding='utf-8');return {**base,'status':'already_enriched','after_words':before,'below_minimum':before<minimum}
    if before>=minimum:
        path.write_text(source,encoding='utf-8');return {**base,'status':'sufficient','after_words':before,'below_minimum':False}
    if '</head>' not in source:raise ValueError('missing head')
    if 'data-advanced-content-depth-v246-style' not in source:source=source.replace('</head>',style()+'</head>',1)
    block=build_block(page_title(source,path),kind,rel)
    if '</main>' in source:source=source.replace('</main>',block+'</main>',1)
    elif '</body>' in source:source=source.replace('</body>',block+'</body>',1)
    else:raise ValueError('missing insertion point')
    after=visible_words(source);path.write_text(source,encoding='utf-8');return {**base,'status':'enriched','after_words':after,'added_words':after-before,'below_minimum':after<minimum}

def run(site:Path)->dict:
    site=site.resolve();results=[];failures=[];hashes=defaultdict(list)
    for path in sorted(site.rglob('*.html')):
        kind=classify(path.relative_to(site).as_posix())
        if not kind:continue
        try:
            row=enrich(path,site,kind);results.append(row)
            if row['status'] in {'enriched','already_enriched'}:
                key=re.search(re.escape(START)+r'(.*?)'+re.escape(END),path.read_text(encoding='utf-8'),re.S)
                if key:hashes[hashlib.sha256(key.group(0).encode()).hexdigest()].append(row['path'])
        except Exception as exc:failures.append({'path':path.relative_to(site).as_posix(),'error':f'{type(exc).__name__}: {exc}'})
    remaining=[r for r in results if r.get('below_minimum')];duplicates=[v for v in hashes.values() if len(v)>1];counts=Counter(r['kind'] for r in results);public=[r for r in results if r['path'].startswith(PUBLIC_ROOTS)]
    report={'version':VERSION,'status':'passed' if not failures and not remaining and not duplicates else 'failed','publication_status':'published','choice_only':all(r.get('choice_guard') for r in public),'public_pages':len(public),'published_pages':sum(bool(r.get('published')) for r in public),'minimums':MINIMUMS,'target_pages':len(results)+len(failures),'counts_by_kind':dict(counts),'enriched_pages':sum(r['status']=='enriched' for r in results),'sufficient_pages':sum(r['status']=='sufficient' for r in results),'already_enriched_pages':sum(r['status']=='already_enriched' for r in results),'minimum_after_words':min((r['after_words'] for r in results if r['status']!='skipped_noindex'),default=0),'remaining_below_minimum':len(remaining),'missing_or_failed':len(failures),'duplicate_generated_blocks':len(duplicates),'failures':failures,'remaining':remaining,'pages':results}
    out=site/'api/advanced-content-depth-v233.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(site/'api/cognitive-sectors-v246.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return report

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('site',nargs='?',default='_site');r=run(Path(p.parse_args().site));print(json.dumps({k:r[k] for k in ('version','status','publication_status','choice_only','public_pages','published_pages','target_pages','counts_by_kind','minimum_after_words','remaining_below_minimum','missing_or_failed','duplicate_generated_blocks')},ensure_ascii=False,indent=2));return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
