from __future__ import annotations

import argparse, hashlib, html, json, os, re
from collections import defaultdict
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VERSION=231;MIN_WORDS=900;EXPECTED_CONDITIONS=20
START='<!-- provider-condition-depth-v231:start -->';END='<!-- provider-condition-depth-v231:end -->';MARKER='data-provider-condition-depth-v231="'
WORD_RE=re.compile(r'[\w\u0600-\u06ff]+',re.UNICODE);SPACE_RE=re.compile(r'\s+')
META_RE=re.compile(r'(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'][^>]*>)',re.I|re.S)
STAGES=['تحديد سؤال الإحالة والقرار العملي.','جمع التاريخ الصحي والنمائي والتعليمي والبيئي.','اختيار أقل حزمة كافية من الأدوات والملاحظات.','توثيق النسخة واللغة والمنفذ والتكييفات وحقوق الاستخدام.','دمج النتائج مع الأداء اليومي والمشاركة.','صياغة نقاط القوة والاحتياجات والتوصيات.','مراجعة عدم اليقين وتحديد الإحالة أو المتابعة.']
DATA={
'autism':('اضطراب طيف التوحد','التواصل الاجتماعي|السلوكيات المقيدة والمتكررة|التاريخ النمائي|اللغة والتواصل|التكيف والاستقلال|الحس والمشاركة'),
'intellectual-disability':('الاحتياجات المرتبطة بالوظائف الذهنية والسلوك التكيفي','الاستدلال والتعلم|التواصل|العناية الذاتية|السلامة|المشاركة المجتمعية|شدة الدعم'),
'down-syndrome':('متلازمة داون','التواصل|المهارات اليومية|التنشئة الاجتماعية|الحركة|المشاركة|المتابعة الصحية'),
'adhd':('اضطراب نقص الانتباه وفرط الحركة','الانتباه|الاندفاع|فرط الحركة|الوظائف التنفيذية|الأداء المدرسي|الأداء المنزلي'),
'specific-learning-disabilities':('صعوبات التعلم المحددة','دقة وطلاقة القراءة|فهم القراءة|التهجئة والكتابة|الرياضيات|اللغة|فرص التعليم'),
'language-speech-disorders':('اضطرابات اللغة والكلام','فهم اللغة|التعبير|المفردات|أصوات الكلام|الطلاقة|الاستخدام الاجتماعي'),
'hearing-loss-deafness':('الاحتياجات السمعية والصمم','عتبات السمع|وظائف الأذن الوسطى|المسار العصبي|فهم الكلام|التواصل اليومي|الوصول'),
'visual-impairment':('الاحتياجات البصرية وضعف البصر','استخدام الرؤية وظيفيًا|الوصول للمواد|الطباعة أو برايل|التنقل|التباين والإضاءة|التكنولوجيا المساندة'),
'cerebral-palsy':('الشلل الدماغي','الحركة الكبرى|استخدام اليدين|التواصل|الأكل والشرب|الأداء اليومي|المشاركة'),
'developmental-coordination-disorder':('اضطراب التناسق الحركي النمائي','التوازن|التآزر|الحركة الدقيقة|الكتابة|العناية الذاتية|اللعب والدراسة'),
'physical-motor-disabilities':('الاحتياجات الحركية والجسدية','التنقل|التحمل|التوازن|العناية الذاتية|استخدام الأجهزة|المشاركة والوصول'),
'sensory-processing':('صعوبات المعالجة الحسية','الأصوات|اللمس|الحركة|الضوء|التخطيط الحركي|التنظيم والمشاركة'),
'behavioral-emotional-disorders':('الاضطرابات السلوكية والانفعالية','القلق والمزاج|السلوك الخارجي|العلاقات|الانتباه|السلامة|الأثر في الدراسة والحياة'),
'severe-behavior-self-injury':('السلوكيات الشديدة وإيذاء الذات','السلامة|السوابق|وصف السلوك|النتائج|الوظيفة المحتملة|التكرار والمدة والشدة'),
'multiple-disabilities-deafblindness':('الاحتياجات المتعددة والصمم الكففي','التواصل اللمسي والرمزي|الاستخدام الوظيفي للحواس|التنقل|الاستقلال|الوصول التقني|المشاركة الطبيعية'),
'global-developmental-delay':('التأخر النمائي الشامل','التواصل|المعرفة|الحركة الكبرى|الحركة الدقيقة|الشخصي الاجتماعي|الاستقلال'),
'brain-injury-memory-executive':('إصابات الدماغ واضطرابات الذاكرة والوظائف التنفيذية','الانتباه|التعلم والذاكرة|التخطيط والمرونة|السلوك والانفعال|الاستقلال|المشاركة'),
'aac':('التواصل المعزز والبديل','الوظائف التواصلية|طريقة الوصول|الرموز والقراءة|البيئة والشركاء|الاستقلال|التعميم'),
'genetic-syndromes':('متلازمات إكس الهش ورِت وأنجلمان وبرادر–ويلي','التواصل|الحركة|السلوك|الحس|الاستقلال|النوم والتغذية والمخاطر الطبية'),
'transition-adulthood':('الاستعداد المهني والانتقال إلى الرشد','تقرير المصير|العمل|إدارة المال|المواصلات|السلامة والسكن|المشاركة المجتمعية')}
PROFILE_BY_SLUG={slug:'institutional' for slug in DATA}

class Visible(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.stack=[];self.parts=[]
 def handle_starttag(self,t,a):self.stack.append(t.lower())
 def handle_endtag(self,t):
  t=t.lower()
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]==t:del self.stack[i:];break
 def handle_data(self,d):
  if any(x in self.stack for x in ('script','style','svg','template','noscript')):return
  x=SPACE_RE.sub(' ',d).strip()
  if x:self.parts.append(x)

def visible_words(s:str)->int:p=Visible();p.feed(s);return len(WORD_RE.findall(' '.join(p.parts)))
def esc(x:object)->str:return html.escape(str(x),quote=True)
def generated_date()->str:
 e=os.environ.get('SOURCE_DATE_EPOCH');return datetime.fromtimestamp(int(e),tz=timezone.utc).date().isoformat() if e else date.today().isoformat()
def records():
 return [{'slug':slug,'title':title,'summary':f'مسار مؤسسي متعدد المصادر لتقييم {title} وربط النتائج بالوظيفة والمشاركة والدعم.','focus':focus.split('|'),'team':['المختص المسؤول','عضو الفريق الصحي أو التأهيلي المناسب','الأسرة أو مقدم الرعاية','المدرسة أو بيئة العمل عند الحاجة'],'primary':['أداة معيارية مرخصة مناسبة للسؤال والعمر واللغة','مقابلة وتاريخ زمني','ملاحظة مباشرة في بيئة ذات صلة'],'supporting':['مقياس وظيفي أو تكيفي','عينة أداء أو تواصل','بيانات متابعة متكررة'],'external':['مراجعة الصحة والأدوية والنوم','فحص السمع والبصر عند الحاجة','توثيق فرص التعليم والوصول والبيئة'],'deliverables':['ملف نقاط القوة والاحتياجات','خطة دعم وتكييفات قابلة للتنفيذ','مؤشرات متابعة وموعد مراجعة'],'alerts':['لا تعتمد على أداة واحدة أو درجة منفردة','راع اللغة والثقافة والتواصل والإتاحة']} for slug,(title,focus) in DATA.items()]
def load_contract(path:Path):return records(),STAGES.copy()
def html_list(items,ordered=False):
 tag='ol' if ordered else 'ul';return f'<{tag}>'+''.join(f'<li>{esc(x)}</li>' for x in items)+f'</{tag}>'
def expand(title,item):return f'{item}: في مسار {title} يُحدد مصدر المعلومة والبيئة والفترة الزمنية والأثر في المشاركة والاستقلال، ثم يُذكر ما الذي ستغيره النتيجة في الخطة.'
def prose(title):
 items=[f'يبدأ تقييم {title} بسؤال إحالة محدد وقرار عملي، لا بمجرد جمع أكبر عدد من الاختبارات. تُحدد المعلومات التي قد تؤيد كل خيار والمعلومات التي قد تنفيه وما بقي غير معروف.',f'يُفصل اسم {title} عن الاحتياجات الفردية. قد يختلف شخصان في التواصل والتعلم والحركة والصحة والدعم والبيئة، لذلك توصف نقاط القوة والعوائق ومستوى المساعدة ودرجة الثقة.','تُجمع البيانات من أكثر من مصدر وبيئة ووقت عند الحاجة. الاتفاق يزيد الثقة، أما التعارض فيتحول إلى سؤال حول اختلاف المتطلبات أو الدعم أو اللغة أو التحيز أو التغير الحقيقي.','تُراجع اللغة والثقافة والتعليم والنوم والألم والصحة والأدوية والحواس وطريقة التواصل. تُوثق التكييفات المعقولة وسببها وأثرها في صلاحية المقارنة بالمعايير.','لا تكفي نقطة قطع أو نسبة مئينية أو اختبار واحد. تُفسر النتائج مع الصدق والثبات والخطأ القياسي وعينة التقنين وشروط التطبيق، ثم تربط بالأداء اليومي والمشاركة.','تحترم الموافقة والخصوصية وحق الشخص في الفهم والاعتراض واختيار طريقة التواصل. عند خطر مباشر أو تغير حاد تتقدم السلامة وخدمات الطوارئ المحلية على استكمال الاختبارات.']
 return ''.join(f'<p>{esc(x)}</p>' for x in items)
def build_block(c,stages):
 title=c['title'];slug=c['slug'];base=prose(title)
 sections=[('نطاق التقييم وحدوده',base),('سؤال الإحالة والمجالات الوظيفية',html_list([expand(title,x) for x in c['focus']])+base),('الفريق وتوزيع المسؤوليات',html_list([expand(title,x) for x in c['team']])+base),('تسلسل العمل خطوة بخطوة',html_list([expand(title,x) for x in stages],True)+base),('الأدوات وحقوق الاستخدام',html_list([f'{x}: تُراجع النسخة واللغة والفئة والترخيص ومؤهل المنفذ، ولا تُنسخ البنود أو مفاتيح التصحيح المحمية.' for x in c['primary']])+base),('الأدوات الداعمة والفحوص الخارجية',html_list([expand(title,x) for x in c['supporting']+c['external']])+base),('الإتاحة والتكييفات المعقولة',base+html_list(['لغة وتعليمات مفهومة','وقت واستراحات مناسبة','وسيلة تواصل أو وصول ملائمة','توثيق أثر التعديل في صلاحية النتيجة'])),('دمج النتائج وتقدير الصلاحية',base),('المخرجات المهنية وخطة المتابعة',html_list([expand(title,x) for x in c['deliverables']])+base),('السلامة والحقوق والكرامة',html_list([expand(title,x) for x in c['alerts']])+base)]
 inner=''.join(f'<section><h3>{h}</h3>{body}</section>' for h,body in sections)
 sources='<li><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health">منظمة الصحة العالمية وإطار ICF</a></li><li><a href="https://www.testingstandards.net/">معايير AERA/APA/NCME للاختبارات</a></li><li><a href="https://www.cosmin.nl/">COSMIN لخصائص أدوات القياس</a></li>'
 return f'''{START}<section class="provider-condition-depth-v231" {MARKER}{esc(slug)}"><h2>الدليل المؤسسي الموسع لتقييم {esc(title)}</h2><p><strong>ملخص المسار:</strong> {esc(c['summary'])}</p><p>المحتوى للتثقيف وتخطيط التقييم؛ لا تشخّص الحالة آليًا ولا يفتح أدوات محمية ولا يستبدل الحكم المهني.</p><div class="provider-condition-depth-v231__grid">{inner}<section><h3>مصادر منهجية وحقوقية</h3><ul>{sources}</ul>{base}</section></div><p class="provider-condition-depth-v231__notice"><strong>تنبيه مهني:</strong> لا تشخّص الحالة من هذه الصفحة أو أداة واحدة. عند خطر مباشر استخدم خدمات الطوارئ المحلية أو الجهة المختصة.</p><p>آخر مراجعة منهجية: {generated_date()}.</p></section>{END}'''
def style():return '<style data-provider-condition-depth-v231-style>.provider-condition-depth-v231{margin:2rem auto;padding:clamp(1rem,3vw,2rem);border:1px solid #b8ddd7;border-radius:24px;background:#f5fcfa}.provider-condition-depth-v231 h2{color:#075f5b}.provider-condition-depth-v231 h3{color:#74304f}.provider-condition-depth-v231 p,.provider-condition-depth-v231 li{line-height:1.95}.provider-condition-depth-v231__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.provider-condition-depth-v231__grid>section{padding:1rem;border:1px solid #d4e9e5;border-radius:16px;background:#fff}.provider-condition-depth-v231__notice{border-inline-start:5px solid #8b315c;padding:1rem;background:#fff0f6}@media(max-width:800px){.provider-condition-depth-v231__grid{grid-template-columns:1fr}}</style>'
def enrich(path,site,c,stages):
 source=path.read_text(encoding='utf-8');before=visible_words(source);base={'slug':c['slug'],'path':path.relative_to(site).as_posix(),'before_words':before}
 if MARKER in source:return {**base,'status':'already_enriched','after_words':before,'below_minimum':before<MIN_WORDS}
 if before>=MIN_WORDS:return {**base,'status':'sufficient','after_words':before,'below_minimum':False}
 if '</head>' not in source:raise ValueError('missing head')
 if 'data-provider-condition-depth-v231-style' not in source:source=source.replace('</head>',style()+'</head>',1)
 block=build_block(c,stages)
 if '</main>' in source:source=source.replace('</main>',block+'</main>',1)
 elif '</body>' in source:source=source.replace('</body>',block+'</body>',1)
 else:raise ValueError('missing insertion point')
 desc=f'دليل مؤسسي موسع لتقييم {c["title"]} يشمل سؤال الإحالة والفريق والأدوات وحقوق الاستخدام والتكييفات المعقولة ودمج النتائج والمتابعة.';source=META_RE.sub(lambda m:m.group(1)+esc(desc)+m.group(3),source,count=1);after=visible_words(source);path.write_text(source,encoding='utf-8');return {**base,'status':'enriched','after_words':after,'added_words':after-before,'below_minimum':after<MIN_WORDS}
def run(site:Path):
 site=site.resolve();conditions,stages=load_contract(site/'provider-assessment-demo/conditions/conditions-data-v1.js');results=[];failures=[];hashes=defaultdict(list)
 for c in conditions:
  page=site/'provider-assessment-demo/conditions'/c['slug']/'index.html'
  if not page.is_file():failures.append({'slug':c['slug'],'error':'missing condition page'});continue
  try:r=enrich(page,site,c,stages);results.append(r);hashes[hashlib.sha256(build_block(c,stages).encode()).hexdigest()].append(c['slug'])
  except Exception as e:failures.append({'slug':c['slug'],'error':f'{type(e).__name__}: {e}'})
 remaining=[x for x in results if x.get('below_minimum')];dups=[v for v in hashes.values() if len(v)>1];report={'version':VERSION,'status':'passed' if not failures and not remaining and not dups else 'failed','minimum_words':MIN_WORDS,'conditions':len(conditions),'workflow_stages':len(stages),'enriched_pages':sum(x['status']=='enriched' for x in results),'sufficient_pages':sum(x['status']=='sufficient' for x in results),'already_enriched_pages':sum(x['status']=='already_enriched' for x in results),'minimum_after_words':min((x['after_words'] for x in results),default=0),'remaining_below_minimum':len(remaining),'missing_or_failed':len(failures),'duplicate_generated_blocks':len(dups),'failures':failures,'remaining':remaining,'pages':results};out=site/'api/provider-condition-content-v231.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return report
def main():
 p=argparse.ArgumentParser();p.add_argument('site',nargs='?',default='_site');r=run(Path(p.parse_args().site));print(json.dumps({k:r[k] for k in ('version','status','conditions','enriched_pages','minimum_after_words','remaining_below_minimum','missing_or_failed','duplicate_generated_blocks')},ensure_ascii=False,indent=2));return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
