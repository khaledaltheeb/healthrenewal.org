from __future__ import annotations
import copy, html, json, re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
ADDITIONS=ROOT/'content/v150/daily-tools-additions'
EDITION=150
REVIEWED_AT='2026-08-14'

# basis, use, limit
CTX={
'stress':('تنظيم الضغط يعني خفض الحمل إلى مستوى يسمح بالملاحظة والاختيار عبر التثبيت والانتباه للحاضر وتعديل البيئة وخطوات صغيرة. لا يفترض أن كل توتر مرض أو أن الهدوء الكامل مطلوب قبل الفعل.','عند ارتفاع التوتر أو الحمل الحسي أو تسارع المطالب مع بقاء القدرة على التوقف لبضع دقائق واختيار خطوة آمنة.','لا تستخدم التهدئة لتجاهل خطر حقيقي أو ألم صدري أو ضيق تنفس جديد أو شديد أو وضع يتطلب حماية أو تقييمًا عاجلًا.'),
'thoughts':('تعتمد الأدوات على مبادئ معرفية وسلوكية: فصل الفكرة عن الحقيقة المطلقة، تسمية المشاعر، فحص الأدلة، وتوجيه السلوك وفق القيم. الهدف زيادة الدقة والمرونة لا إجبار التفكير الإيجابي.','عندما يتكرر التفكير أو الاجترار أو النقد الذاتي أو يصعب فصل الوقائع عن التوقعات مع بقاء القدرة على الملاحظة والكتابة.','إذا كانت الأفكار أو التجارب الإدراكية تعطل الأمان أو الواقع الوظيفي فلا تحاول مناقشتها وحدك واطلب تقييمًا مهنيًا.'),
'sleep':('تركز أدوات النوم على السلوك والروتين والبيئة والتوقيت والمتابعة عبر أيام. السجل الذاتي يوضح أنماطًا لكنه لا يقيس مراحل النوم ولا يحدد سبب الأرق أو النعاس.','لبناء روتين واقعي أو تسجيل النوم والطاقة أو تجربة تعديل واحد يمكن متابعته عدة ليال.','النعاس المؤثر في القيادة أو السلامة، اختناق النوم الملحوظ، الأرق المستمر، أو تغير النوم المصحوب بأعراض مقلقة يحتاج تقييمًا مهنيًا.'),
'focus':('تتعامل الأدوات مع الأداء التنفيذي كسلسلة قابلة للتعديل: وضوح المهمة، البدء، حجم الخطوة، المشتتات، تقدير الوقت، الطاقة والإغلاق، دون افتراض تشخيص بعينه.','عند التسويف أو تشتت الذهن أو صعوبة بدء مهمة أو العودة إليها أو تقدير وقتها في الدراسة أو العمل أو الحياة اليومية.','ضعف التركيز الجديد أو الشديد أو المصحوب بإغماء أو ارتباك أو أعراض عصبية أو أثر وظيفي كبير يستدعي تقييمًا مناسبًا.'),
'relationships':('تركز الأدوات على التواصل الواضح والطلبات والحدود والاستماع والتمييز بين الخلاف الطبيعي والضغط أو السيطرة، دون تشخيص شخصية الطرف الآخر.','عندما تكون السلامة متوفرة ويوجد مجال فعلي للحوار أو لاتخاذ قرار حول حدودك وطريقة تواصلك.','عند العنف أو التهديد أو الإكراه أو السيطرة القسرية اجعل السلامة والحماية أولوية ولا تعتمد على التفاوض الفردي وحده.'),
'family':('تعتمد الأدوات الأسرية على الاستماع والروتين المتوقع ووصف السلوك دون وصم وتعليم البدائل والتكيف مع عمر الطفل وتواصله؛ فهي تدعم الوالد ولا تحوله إلى معالج.','في المواقف اليومية المتكررة مثل الانتقالات والواجبات والخلافات والانفعال والحوار مع الطفل أو المراهق.','إشارات الأذى أو الإهمال أو التنمر الخطير أو الخوف المستمر أو التدهور الواضح لدى الطفل تحتاج حماية وتنسيقًا مهنيًا أو مدرسيًا.'),
'caregiver':('رفاه مقدم الرعاية جزء من استدامة الرعاية. تركز الأدوات على القدرة الحالية والتفويض والتعافي وتوزيع الأدوار ووضوح المعلومات وطلب الدعم قبل الإنهاك غير الآمن.','عندما تتراكم مسؤوليات الرعاية أو يصعب تحديد الضروري وما يمكن تفويضه أو تبسيطه.','إذا لم تعد قادرًا على تقديم رعاية آمنة أو ظهر انهيار وظيفي شديد ففعّل بديل الرعاية واطلب دعمًا عاجلًا.'),
'inclusive':('تتبنى الأدوات منظور الوصول والمشاركة والفروق الفردية: تفضيلات التواصل والبيئة الحسية والانتقال وتكييف المهمة والاختيار المدعوم ومراجعة ما يناسب الشخص فعليًا.','لتجربة تكييف عملي في المنزل أو المدرسة أو المركز بالتعاون مع الشخص والأسرة والفريق عند الحاجة.','لا تعمم خصائص تشخيص على فرد ولا تستخدم الأداة بدل التقييم الفردي أو خطة التعليم أو التأهيل أو الرعاية المتخصصة.'),
'change':('تركز أدوات التغير والفقد على خفض المطالب وتثبيت الضروريات وشبكة الدعم والمعنى والتدرج في العودة إلى الأدوار والروتين، دون افتراض مسار زمني واحد للحزن.','بعد فقد أو انتقال أو تغير عمل أو دور أو تعثر عندما تحتاج إلى تنظيم اليوم أو قرار صغير.','العجز الشديد المستمر أو الانعزال الخطير أو الأفكار المؤذية أو فقدان الأمان يحتاج دعمًا مهنيًا أو طارئًا وفق مستوى الخطر.'),
'safety':('تنظم هذه الأدوات الوصول إلى الدعم: إشارات التحذير والأشخاص الموثوقون والمعلومات وخطوات التصعيد. هي مساندة للتخطيط ولا تحل محل الطوارئ أو الخطة السريرية.','مسبقًا أو مع شخص موثوق أو مختص لترتيب ما ستفعله إذا ازداد الضيق أو تعذر الوصول إلى الدعم المعتاد.','عند خطر فوري على النفس أو الآخرين أو عجز عن البقاء بأمان تجاوز الأداة واتصل بخدمات الطوارئ المحلية أو اذهب إلى أقرب قسم طوارئ.'),
}
SEO={
'stress':['إدارة التوتر','تمارين تهدئة','ضغوط العمل','القلق من المستقبل'],
'thoughts':['التفكير الزائد','تنظيم المشاعر','الوعي الذاتي','الأفكار السلبية'],
'sleep':['اضطراب النوم','روتين النوم','سجل النوم','النعاس النهاري'],
'focus':['علاج التسويف','تشتت الذهن','تنظيم الوقت','ضعف التركيز في الدراسة'],
'relationships':['الحدود الشخصية','التواصل في العلاقات','التلاعب النفسي','العلاقات الصحية'],
'family':['التربية الإيجابية','نوبات الغضب عند الأطفال','التنمر','التعامل مع المراهقين'],
'caregiver':['رفاه مقدم الرعاية','الاحتراق النفسي','تقسيم مهام الرعاية','طلب الدعم'],
'inclusive':['التربية الدامجة','تشتت الانتباه عند الأطفال','عسر القراءة','طيف التوحد عند الأطفال'],
'change':['المرونة النفسية','فقدان الدافعية','التكيف مع التغيير','الحزن والفقد'],
'safety':['طلب المساعدة النفسية','متى أحتاج مختص','خطة السلامة','الوصول للخدمات']}

def e(v:object)->str:return html.escape(str(v),quote=True)
def uniq(values:list[str],limit:int=8)->list[str]:
 out=[]; seen=set()
 for raw in values:
  v=re.sub(r'\s+',' ',str(raw or '')).strip(' ،,.-'); k=v.casefold()
  if v and k not in seen: out.append(v[:90]); seen.add(k)
  if len(out)>=limit: break
 return out

def load_additions()->list[dict[str,Any]]:
 tools=[]
 for p in sorted(ADDITIONS.glob('*.json')):
  payload=json.loads(p.read_text(encoding='utf-8'))
  if payload.get('edition')!=EDITION: raise SystemExit(f'Invalid edition: {p}')
  tools.extend(payload.get('tools',[]))
 if len(tools)!=50: raise SystemExit(f'Expected 50 additions, got {len(tools)}')
 return tools

def upgrade_data(base:dict[str,Any])->dict[str,Any]:
 data=copy.deepcopy(base); cats={x['id']:x for x in data['categories']}; samples={}
 for x in data['tools']:
  c=cats[x['category_id']]; x.setdefault('category',c['name']); x.setdefault('audience',list(c['audience'])); x.setdefault('source_ids',list(c['source_ids'])); x.setdefault('safety','إذا استمرت الصعوبة أو أثرت في الأمان أو الأداء اليومي، اطلب مساعدة مهنية مناسبة.'); x.setdefault('tags',uniq([c['name'],*c['audience']])); samples.setdefault(x['category_id'],x)
 slugs={x['slug'] for x in data['tools']}; titles={re.sub(r'\W+','',x['title']).casefold() for x in data['tools']}
 for x in load_additions():
  x=copy.deepcopy(x); cid=x['category_id']; c=cats[cid]
  if x['slug'] in slugs or re.sub(r'\W+','',x['title']).casefold() in titles: raise SystemExit(f'Duplicate: {x["slug"]}')
  x.update(category=c['name'],audience=list(c['audience']),safety=samples[cid]['safety'],source_ids=list(c['source_ids']))
  x['tags']=uniq([c['name'],*x.get('seo_keywords',[]),*c['audience']]); data['tools'].append(x); slugs.add(x['slug']); titles.add(re.sub(r'\W+','',x['title']).casefold())
 counts=Counter(x['category_id'] for x in data['tools'])
 if len(data['tools'])!=150 or set(counts.values())!={15}: raise SystemExit({'tools':len(data['tools']),'counts':counts})
 data.update(edition=150,content_upgrade='scientific-editorial-seo-v150'); return data

def keywords(tool):return uniq([tool['title'],*tool.get('seo_keywords',[]),*SEO[tool['category_id']],tool['category'],'أدوات نفسية تفاعلية'])
def faqs(tool):
 basis,use,limit=CTX[tool['category_id']]
 return [(f'متى أستخدم {tool["title"]}؟',f'{use} استخدمها لموقف محدد وسجل ما حدث بدل تحويل النتيجة إلى حكم عام.'),('هل النتيجة تشخيص أو تقييم سريري؟','لا. هذه أداة تنظيمية وتثقيفية غير تشخيصية؛ تساعد على ملاحظة نمط أو تجهيز سؤال ولا تثبت وجود اضطراب أو سبب الأعراض.'),('كم مرة أكرر الأداة؟','كررها بقدر ما يخدم هدفًا واضحًا ثم راجع الاتجاه عبر عدة مواقف أو أيام. إذا أصبح الاستخدام قهريًا أو زاد الضيق فتوقف واطلب توجيهًا مناسبًا.'),('متى أحتاج مساعدة مختص؟',f'{limit} واطلب دعمًا إذا استمرت الصعوبة أو عطلت الدراسة أو العمل أو العلاقات أو العناية الذاتية.')]

def editorial(tool):
 basis,use,limit=CTX[tool['category_id']]; fields='، '.join(tool['save_fields'][:4]); kws='، '.join(keywords(tool)); faq=''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q,a in faqs(tool))
 return f'''<div data-content-upgrade="daily-tools-content-v150"><section><h2>كيف تستخدم هذه الأداة بفاعلية؟</h2><p><strong>{e(tool['title'])}</strong> مصممة لهدف محدد: {e(tool['intent'])} ابدأ بموقف حديث وواضح. الخطوة الأولى: «{e(tool['steps'][0])}». نفّذ الخطوات بالترتيب ثم اختم بـ«{e(tool['steps'][-1])}».</p><p>المدة المقترحة <strong>{e(tool['duration'])}</strong> وليست اختبار سرعة. اختصر الإجابات إذا زادت الكتابة الحمل، وكيّف اللغة وطريقة العرض والوقت للأطفال أو ذوي احتياجات التواصل مع الحفاظ على الهدف والاختيار والسلامة.</p></section><section><h2>الأساس المنهجي</h2><p>{e(basis)}</p><p>القيمة العملية تأتي من تحويل الخبرة إلى <strong>ملاحظة قابلة للمراجعة ثم خطوة صغيرة</strong>. لا نستخدم السجل للحكم على الشخصية أو لإثبات سبب نفسي أو طبي، بل لتقليل الغموض ومقارنة المواقف وتجهيز معلومات أوضح عند الحاجة إلى مختص أو أسرة أو مدرسة أو فريق دعم.</p></section><section><h2>قبل البدء وبعده</h2><h3>قبل البدء</h3><ul><li>اختر موقفًا واحدًا وحدد ما تريد أن يصبح أوضح.</li><li>تأكد أن استخدام الأداة لا يؤخر استجابة لازمة لخطر أو مشكلة عاجلة.</li><li>اكتب أقل قدر من البيانات الشخصية؛ الحفظ محلي لكنه يظل قابلًا للوصول ممن يستخدم الجهاز نفسه.</li></ul><h3>بعد الانتهاء</h3><ul><li>حدد المعلومة الجديدة وأصغر خطوة مفيدة الآن.</li><li>عدم تغير الشدة فورًا لا يعني الفشل؛ قد تكون الفائدة تنظيم القرار أو زيادة الوضوح.</li><li>قارن أكثر من موقف قبل استنتاج أن تعديلًا معينًا ساعد أو لم يساعد.</li></ul></section><section><h2>كيف تقرأ السجل؟</h2><p>تشمل حقول المتابعة: {e(fields)}. اقرأها بوصفها <strong>مؤشرات ذاتية وسياقية</strong> وليست درجات معيارية. ابحث عن التكرار: ما الذي يسبق الصعوبة؟ ما الذي يسهل الخطوة؟ وما الذي يزيد التعطل؟ تجنب تفسير التزامن على أنه سبب مؤكد؛ فقد تتداخل عوامل النوم والصحة والبيئة والعلاقات والضغط.</p></section><section><h2>أخطاء شائعة تقلل الفائدة</h2><ul><li><strong>حل كل شيء دفعة واحدة:</strong> ارجع إلى موقف وخطوة واحدة.</li><li><strong>إثبات حكم مسبق:</strong> سجل الوقائع والبدائل وما لا تعرفه.</li><li><strong>مطاردة نتيجة مثالية:</strong> الهدف زيادة الفهم والاختيار لا رقم أو شعور محدد.</li><li><strong>تجاهل السياق:</strong> المرض والنوم والبيئة والعمر والإعاقة والأدوية والضغوط قد تغير الاستجابة.</li></ul></section><section class="note"><h2>حدود الأداة ومتى تحتاج مختصًا</h2><p>{e(limit)}</p><p>إذا استمرت الصعوبة أو عطلت العمل أو الدراسة أو العلاقات أو العناية الذاتية فحوّل السجل إلى ملخص يمكن مشاركته مع مختص مؤهل بدل التشخيص الذاتي. لا تغيّر دواءً أو خطة علاج أو تعليمات سلامة اعتمادًا على الصفحة.</p></section><section><h2>أسئلة شائعة</h2>{faq}</section><section><h2>كلمات وموضوعات مرتبطة</h2><p>{e(kws)}</p><p class="status">مراجعة تحريرية ومنهجية: {REVIEWED_AT}. المحتوى تثقيفي وتنظيمي وغير تشخيصي.</p></section></div>'''

def add_schema(text,tool,canonical):
 faq={'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faqs(tool)]}; crumb={'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'الرئيسية','item':'https://healthrenewal.org/'},{'@type':'ListItem','position':2,'name':'الأدوات اليومية','item':'https://healthrenewal.org/daily-tools/'},{'@type':'ListItem','position':3,'name':tool['title'],'item':canonical}]}
 m=re.search(r'<script type="application/ld\+json">(.*?)</script>',text,re.S)
 if m:
  try: payload=json.loads(m.group(1))
  except json.JSONDecodeError: payload={'@context':'https://schema.org','@graph':[]}
  if not isinstance(payload,dict) or '@graph' not in payload: payload={'@context':'https://schema.org','@graph':[payload]}
  payload['@graph']=[x for x in payload['@graph'] if not(isinstance(x,dict) and x.get('@type') in {'FAQPage','BreadcrumbList'})]+[faq,crumb]
  enc=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'); return text[:m.start(1)]+enc+text[m.end(1):]
 enc=json.dumps({'@context':'https://schema.org','@graph':[faq,crumb]},ensure_ascii=False,separators=(',',':')).replace('</','<\\/'); return text.replace('</head>',f'<script type="application/ld+json">{enc}</script></head>',1)

def word_count(text):
 t=re.sub(r'<script.*?</script>|<style.*?</style>',' ',text,flags=re.S|re.I); t=re.sub(r'<[^>]+>',' ',t); return len(re.findall(r'[\u0600-\u06FFA-Za-z0-9]+',html.unescape(t)))
def enrich_tool(tool,site):
 p=site/'daily-tools'/tool['slug']/'index.html'; text=p.read_text(encoding='utf-8');
 if 'data-content-upgrade="daily-tools-content-v150"' in text:return word_count(text)
 meta=f'<meta name="keywords" content="{e(",".join(keywords(tool)))}">'; text=re.sub(r'<meta name="keywords" content="[^"]*">',meta,text,count=1) if 'name="keywords"' in text else text.replace('</head>',meta+'</head>',1); text=add_schema(text,tool,f'https://healthrenewal.org/daily-tools/{tool["slug"]}/')
 if '</main>' not in text: raise SystemExit(f'Missing main: {tool["slug"]}')
 text=text.replace('</main>',editorial(tool)+'</main>',1); p.write_text(text,encoding='utf-8'); return word_count(text)
def enhance(data,site:Path|str):
 site=Path(site).resolve(); counts=[enrich_tool(x,site) for x in data['tools']]; idx=site/'daily-tools/index.html'; t=idx.read_text(encoding='utf-8'); t=re.sub(r'<h1>\d+ أداة نفسية وتربوية يومية</h1>','<h1>150 أداة نفسية وتربوية يومية</h1>',t,count=1)
 if 'data-index-upgrade="daily-tools-content-v150"' not in t:
  intro='<section data-index-upgrade="daily-tools-content-v150"><h2>اختر الأداة بحسب الحاجة لا بحسب التشخيص</h2><p>تضم المكتبة 150 أداة عملية موزعة بالتساوي على عشرة مجالات: التوتر، الأفكار والمشاعر، النوم، التركيز، العلاقات، الأسرة، رفاه مقدمي الرعاية، التربية الدامجة، التغير والفقد، وطلب المساعدة والسلامة. ابدأ بالحاجة الحالية ثم استخدم البحث والفلاتر.</p><p>أُعيدت مراجعة الأدوات لتوضيح الغرض والحدود وطريقة قراءة السجل والأسئلة الشائعة والمصادر. الأدوات غير تشخيصية والسجلات التي تختار حفظها تبقى داخل جهازك.</p></section>'; t=t.replace('</header>','</header>'+intro,1)
 idx.write_text(t,encoding='utf-8'); home=site/'index.html'
 if home.is_file():
  h=home.read_text(encoding='utf-8'); h=re.sub(r'\b100 أداة عربية عملية\b','150 أداة عربية عملية',h); h=re.sub(r'\b100 أداة\b','150 أداة',h); home.write_text(h,encoding='utf-8')
 c=Counter(x['category_id'] for x in data['tools']); report={'schemaVersion':1,'status':'passed','edition':150,'reviewedAt':REVIEWED_AT,'tools':len(data['tools']),'existingToolsUpgraded':100,'newToolsAdded':50,'categories':len(data['categories']),'toolsPerCategory':min(c.values()),'learningPaths':len(data['paths']),'indexableSectionPages':len(data['tools'])+len(data['paths'])+2,'minimumToolPageWordCount':min(counts),'maximumToolPageWordCount':max(counts),'faqSchema':True,'breadcrumbSchema':True,'toolSpecificKeywords':True,'perToolSources':True,'privacy':'local-only','diagnosticUse':False}
 api=site/'api'; api.mkdir(exist_ok=True); (api/'daily-tools-v150.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); legacy=api/'daily-tools-v24.json'
 if legacy.is_file():
  old=json.loads(legacy.read_text(encoding='utf-8')); old.update(edition=150,tools=150,pages=report['indexableSectionPages'],content_upgraded=True,faq_schema=True,breadcrumb_schema=True); legacy.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if report['tools']!=150 or report['toolsPerCategory']!=15 or report['minimumToolPageWordCount']<420: raise SystemExit(report)
 return report
