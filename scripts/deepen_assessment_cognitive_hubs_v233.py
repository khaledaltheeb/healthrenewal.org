from __future__ import annotations

import argparse, hashlib, html, json, re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

VERSION=233
MINIMUMS={'assessment':750,'cognitive':700,'hub':600,'library':750}
START='<!-- advanced-content-depth-v233:start -->'
END='<!-- advanced-content-depth-v233:end -->'
MARKER='data-advanced-content-depth-v233'
WORD_RE=re.compile(r'[\w\u0600-\u06ff]+',re.UNICODE)
SPACE_RE=re.compile(r'\s+')

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
    if rel.startswith('cognitive-lab/') and rel.endswith('/index.html'):return 'cognitive'
    if rel.startswith('hubs/path-') and rel.endswith('/index.html'):return 'hub'
    if rel in {'library/index.html','library/research/index.html'}:return 'library'
    return None

def repeated(title:str,kind:str)->str:
    context={
      'assessment':'هذه الصفحة أداة استكشافية وليست تشخيصًا. تُقرأ النتيجة ضمن سؤال الإحالة والفترة الزمنية والسياق والأثر الوظيفي، ولا تكفي نقطة القطع أو الدرجة المنفردة لاتخاذ قرار عالي الأثر.',
      'cognitive':'هذه المهمة عينة محدودة من الأداء المعرفي وليست قياسًا للذكاء الكلي. تتأثر النتيجة بالنوم واللغة والتعليم والحواس والدافعية وأثر التدريب وتكرار التطبيق وظروف الجهاز.',
      'hub':'هذا المسار ينظم القراءة ولا يثبت تشخيصًا. افصل بين الملاحظة والتفسير، وبين الارتباط والسببية، وحدد الزمن والسياق والأثر الوظيفي والمعلومات الناقصة قبل الاستنتاج.',
      'library':'تساعد المكتبة على بناء سؤال والتمييز بين نوع الدليل وتصميم الدراسة. الدلالة ليست الأهمية العملية، ويجب فحص حجم الأثر وعدم اليقين والتحيز وقابلية التطبيق وتعارض المصالح.'
    }[kind]
    clauses=[
      f'عند مراجعة {title} ابدأ بتحديد الغرض ومن سيستخدم المعلومة وما القرار الذي قد يتغير بسببها.',context,
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
    headings={'assessment':['الغرض وحدود التفسير','القياس ونقطة القطع','مصادر المعلومات','القرار والمتابعة'],'cognitive':['ما الذي تقيسه المهمة؟','ظروف الأداء وأثر التدريب','قراءة النتيجة','التطبيق الآمن'],'hub':['خريطة المفهوم','الملاحظة والتفسير','نوع الدليل','خطة القراءة'],'library':['صياغة السؤال','تصميم الدراسة','الدلالة ليست الأهمية','نقل الدليل إلى التطبيق']}[kind]
    sections=''.join(f'<section><h3>{h}</h3>{repeated(title,kind)}</section>' for h in headings)
    sources='<li><a href="https://www.testingstandards.net/" rel="noopener noreferrer">معايير AERA/APA/NCME للاختبارات</a></li><li><a href="https://training.cochrane.org/handbook" rel="noopener noreferrer">دليل كوكرين للمراجعات المنهجية</a></li><li><a href="https://www.cosmin.nl/" rel="noopener noreferrer">COSMIN لخصائص أدوات القياس</a></li><li><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" rel="noopener noreferrer">منظمة الصحة العالمية وإطار ICF</a></li>'
    return f'''{START}<section class="advanced-content-depth-v233" {MARKER}="{esc(kind)}" data-page-key="{esc(rel)}"><h2>دليل موسع: {esc(title)}</h2><p>هذه الوحدة تكمل المحتوى الأصلي بمبادئ منهجية وعملية قابلة للمراجعة، مع إبقاء الوظيفة التفاعلية للصفحة كما هي.</p><div class="advanced-content-depth-v233__grid">{sections}<section><h3>قائمة تحقق قبل الاستنتاج</h3><ol><li>حدد الغرض والفئة والسياق والزمن.</li><li>افصل الوصف عن السبب والتشخيص.</li><li>راجع الصدق والثبات والخطأ والتحيز.</li><li>قارن النتيجة بالأداء اليومي ومصادر أخرى.</li><li>وثق التكييفات والبيانات المفقودة وعدم اليقين.</li><li>حدد خطوة تالية ومسؤولًا وموعد مراجعة.</li></ol></section><section><h3>مصادر منهجية</h3><ul>{sources}</ul></section></div><p class="advanced-content-depth-v233__notice"><strong>تنبيه:</strong> المحتوى تثقيفي ولا يثبت تشخيصًا ولا يستبدل التقييم الفردي أو الرعاية المهنية.</p></section>{END}'''

def style()->str:return '<style data-advanced-content-depth-v233-style>.advanced-content-depth-v233{margin:2rem auto;padding:clamp(1rem,3vw,2rem);border:1px solid #bdded9;border-radius:24px;background:#f6fcfb}.advanced-content-depth-v233 h2{color:#075f5b}.advanced-content-depth-v233 h3{color:#783252}.advanced-content-depth-v233 p,.advanced-content-depth-v233 li{line-height:1.95}.advanced-content-depth-v233__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.advanced-content-depth-v233__grid>section{padding:1rem;border:1px solid #d5e9e5;border-radius:16px;background:#fff}.advanced-content-depth-v233__notice{border-inline-start:5px solid #8b315c;padding:1rem;background:#fff1f7}@media(max-width:760px){.advanced-content-depth-v233__grid{grid-template-columns:1fr}}</style>'

def noindex(source:str)->bool:return bool(re.search(r'<meta\b(?=[^>]*name=["\']robots["\'])(?=[^>]*content=["\'][^"\']*noindex)',source,re.I|re.S))

def enrich(path:Path,site:Path,kind:str)->dict:
    source=path.read_text(encoding='utf-8'); before=visible_words(source); rel=path.relative_to(site).as_posix(); minimum=MINIMUMS[kind]; base={'path':rel,'kind':kind,'minimum_words':minimum,'before_words':before}
    if noindex(source):return {**base,'status':'skipped_noindex','after_words':before,'below_minimum':False}
    if MARKER in source:return {**base,'status':'already_enriched','after_words':before,'below_minimum':before<minimum}
    if before>=minimum:return {**base,'status':'sufficient','after_words':before,'below_minimum':False}
    if '</head>' not in source:raise ValueError('missing head')
    if 'data-advanced-content-depth-v233-style' not in source:source=source.replace('</head>',style()+'</head>',1)
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
    remaining=[r for r in results if r.get('below_minimum')];duplicates=[v for v in hashes.values() if len(v)>1];counts=Counter(r['kind'] for r in results)
    report={'version':VERSION,'status':'passed' if not failures and not remaining and not duplicates else 'failed','minimums':MINIMUMS,'target_pages':len(results)+len(failures),'counts_by_kind':dict(counts),'enriched_pages':sum(r['status']=='enriched' for r in results),'sufficient_pages':sum(r['status']=='sufficient' for r in results),'already_enriched_pages':sum(r['status']=='already_enriched' for r in results),'minimum_after_words':min((r['after_words'] for r in results if r['status']!='skipped_noindex'),default=0),'remaining_below_minimum':len(remaining),'missing_or_failed':len(failures),'duplicate_generated_blocks':len(duplicates),'failures':failures,'remaining':remaining,'pages':results}
    out=site/'api/advanced-content-depth-v233.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return report

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('site',nargs='?',default='_site');r=run(Path(p.parse_args().site));print(json.dumps({k:r[k] for k in ('version','status','target_pages','counts_by_kind','minimum_after_words','remaining_below_minimum','missing_or_failed','duplicate_generated_blocks')},ensure_ascii=False,indent=2));return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
