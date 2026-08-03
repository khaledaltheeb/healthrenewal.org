#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json,re
from html.parser import HTMLParser
from pathlib import Path
V=222;BASE='/';START='<!-- content-depth-v222:start -->';END='<!-- content-depth-v222:end -->'
W=re.compile(r'[\w\u0600-\u06ff]+',re.U);S=re.compile(r'\s+')
POL={'comparisons':('compare',220),'library':('evidence',230),'magazine':('evidence',230),'encyclopedia':('mental',200),'terms':('mental',200),'hubs':('hub',190),'assessments':('measure',220),'assessment-lab':('measure',220),'guided-assessment':('measure',220),'cognitive-tests':('measure',220),'cognitive-lab':('measure',220),'care-guides':('support',225),'special-needs':('support',225),'tips':('practice',225),'sectors':('practice',225),'daily-tools':('practice',225),'learning-paths':('practice',225),'start-here':('hub',190),'sections':('hub',190),'trust':('evidence',230),'partners':('hub',190),'developers':('hub',190)}
SRC={'mental':(('منظمة الصحة العالمية: ICD-11 السريري','https://www.who.int/publications/i/item/9789240077263'),('منظمة الصحة العالمية: الاضطرابات النفسية','https://www.who.int/news-room/fact-sheets/detail/mental-disorders'),('NICE: الصحة النفسية والنمائية العصبية','https://www.nice.org.uk/guidance/conditions-and-diseases/mental-health-behavioural-and-neurodevelopmental-conditions')),'evidence':(('دليل كوكرين للمراجعات المنهجية','https://training.cochrane.org/handbook'),('منظمة الصحة العالمية: ICD-11 السريري','https://www.who.int/publications/i/item/9789240077263'),('NICE: الإرشادات الصحية','https://www.nice.org.uk/guidance/conditions-and-diseases/mental-health-behavioural-and-neurodevelopmental-conditions')),'measure':(('معايير الاختبارات AERA/APA/NCME','https://www.testingstandards.net/'),('COSMIN: خصائص القياس','https://www.cosmin.nl/'),('منظمة الصحة العالمية: ICF','https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health')),'support':(('منظمة الصحة العالمية: ICF','https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health'),('اليونسكو: الدمج والإنصاف','https://www.unesco.org/en/articles/guide-ensuring-inclusion-and-equity-education-0'),('اليونيسف: رفاه الأسرة','https://www.unicef.org/parenting/mental-health-and-well-being')),'practice':(('منظمة الصحة العالمية: الرعاية الذاتية','https://www.who.int/health-topics/self-care'),('اليونيسف: رفاه الأسرة','https://www.unicef.org/parenting/mental-health-and-well-being'),('منظمة الصحة العالمية: الاضطرابات النفسية','https://www.who.int/news-room/fact-sheets/detail/mental-disorders')),'hub':(('منظمة الصحة العالمية: الاضطرابات النفسية','https://www.who.int/news-room/fact-sheets/detail/mental-disorders'),('منظمة الصحة العالمية: ICF','https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health'),('دليل كوكرين','https://training.cochrane.org/handbook'))}
CSS='.content-depth-v222{margin:2rem auto;padding:1.4rem;border:1px solid #bfded9;border-radius:22px;background:#f5fcfa}.content-depth-v222 h2{color:#075f5b}.content-depth-v222 h3{color:#74304f}.content-depth-v222 p,.content-depth-v222 li{line-height:1.95}.content-depth-v222__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.content-depth-v222__card{padding:1rem;border:1px solid #d7e9e6;border-radius:16px;background:#fff}.content-depth-v222__note{border-inline-start:5px solid #8b315c;padding:.8rem;background:#fff3f8}@media(max-width:760px){.content-depth-v222__grid{grid-template-columns:1fr}}'
class P(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.st=[];self.txt=[];self.h=[];self.t=[]
 def handle_starttag(self,x,a):self.st.append(x.lower())
 def handle_endtag(self,x):
  for i in range(len(self.st)-1,-1,-1):
   if self.st[i]==x.lower():del self.st[i:];break
 def handle_data(self,d):
  d=S.sub(' ',d).strip()
  if not d:return
  if self.st and self.st[-1]=='title':self.t.append(d)
  if 'h1' in self.st:self.h.append(d)
  if not any(x in self.st for x in ('script','style','noscript','svg')):self.txt.append(d)
def parse(x):p=P();p.feed(x);return p
def words(x):return len(W.findall(x))
def esc(x):return html.escape(str(x),quote=True)
def rt(rel):return Path(rel).parts[0] if Path(rel).parts and Path(rel).parts[0]!='index.html' else 'home'
def topic(p,rel):
 x=' '.join(p.h or p.t) or Path(rel).parent.name.replace('-',' ')
 for b in ('منصة روافد','مصطلحات علم النفس'):x=x.replace(b,'')
 return re.split(r'\s*[|—–]\s*',x,maxsplit=1)[0].strip(' -|—–') or 'الموضوع'
def noindex(x):return bool(re.search(r'<meta\b(?=[^>]*name=["\']robots["\'])(?=[^>]*content=["\'][^"\']*noindex)',x,re.I|re.S))
def lang(x):
 m=re.search(r'<html\b[^>]*lang=(["\'])(.*?)\1',x,re.I|re.S);return m.group(2).split('-',1)[0] if m else 'ar'
def card(h,b):return f'<section class="content-depth-v222__card"><h3>{esc(h)}</h3>{b}</section>'
def li(items,ordered=False):tag='ol' if ordered else 'ul';return f'<{tag}>'+''.join(f'<li>{x}</li>' for x in items)+f'</{tag}>'
def source_card(k):return card('مصادر موثوقة للتوسع',li([f'<a href="{esc(u)}" rel="noopener noreferrer">{esc(n)}</a>' for n,u in SRC[k]])+'<p><small>مراجع منهجية لا تغني عن الدليل المتخصص أو التقييم الفردي.</small></p>')
def common(t):return card('محاور الفهم الأساسية',li([f'تعريف {esc(t)} وحدوده وما لا يمكن استنتاجه من علامة واحدة.','البداية والمدة والتكرار والشدة والتغير عبر الزمن.','الأثر في النوم والتعلم والعمل والعلاقات والعناية بالنفس.','السياق النمائي والثقافي والصحي والأدوية والمواد والألم.','العوامل المصاحبة وعوامل الحماية والدعم المتاح.']))+card('من المعرفة إلى خطوة عملية',li(['دوّن أمثلة محددة مع التاريخ والسياق والأثر.','راقب الاتجاه عبر عدة مواقف بدل الحكم من يوم واحد.','حدد أكثر جانب معطل وابدأ بهدف صغير قابل للمراجعة.','اطلب تقييمًا مهنيًا عند الاستمرار أو الشدة أو التعطيل.','راجع الخطة وفق النتائج والآثار غير المرغوبة واحتياجات الشخص.'],True))
def specific(k,t):
 if k=='compare':
  return card('منهجية المقارنة',f'<p>المقارنة بين مكونات {esc(t)} لا تعتمد على كلمة فاصلة؛ افحص البداية والمسار والمحفزات والخبرة الداخلية والأثر الوظيفي والاستجابة للدعم. قد يتشابه المظهر وتختلف الأسباب، وقد يجتمع نمطان عند الشخص نفسه.</p>'+li(['لا تعتمد على عرض واحد.','لا تحول شدة السلوك إلى تشخيص.','لا تتجاهل العمر والثقافة والتواصل.','لا تستخدم اختبارًا منفردًا كحكم نهائي.','افحص الأسباب الطبية والدوائية واحتمال التزامن.']))
 if k=='evidence':
  return card('قراءة الدليل نقديًا',li(['ما سؤال الدراسة ومن المشاركون؟','هل التصميم مناسب للسؤال؟','هل القياس صادق وثابت ومناسب للغة والعمر؟','ما حجم الأثر وعدم اليقين والآثار غير المرغوبة؟','ما التحيز وتضارب المصالح والبيانات المفقودة؟','هل يمكن تطبيق النتائج على السياق المقصود؟']))+card('قرار مبني على الدليل','<p>طابق نوع الدليل بالسؤال، وافصل الارتباط عن السببية والدلالة الإحصائية عن الأهمية العملية. ادمج الدليل مع خبرة المختص وتفضيلات الشخص وإمكان الوصول، وحدد مؤشر متابعة وموعد مراجعة.</p>')
 if k=='measure':
  return card('عقد القياس المهني',li(['الغرض: فحص أو وصف أو متابعة أو تخطيط دعم.','الفئة: العمر واللغة والتعليم والصحة والثقافة.','الصدق والثبات والخطأ القياسي والاستجابة للتغير.','عينة التقنين وحداثتها ومدى تمثيلها للشخص.','شروط التطبيق والتعديلات والترخيص والتصحيح.']))+card('تفسير النتيجة','<p>الدرجة ليست تشخيصًا. تفسر مع المقابلة والملاحظة والتاريخ والمعلومات الوظيفية. نقطة القطع قرار احتمالي، وفي المتابعة تثبت الظروف قدر الإمكان ويسجل أي عامل قد يفسر تغير النتيجة.</p>')
 if k=='support':
  return card('دعم متمحور حول الشخص',li(['ابدأ بأهداف الشخص والأسرة لا باسم الحالة فقط.','افحص النشاط والمشاركة والحواجز البيئية ووسائل التواصل.','راع الحواس والحركة والنوم والصحة والسلامة.','استخدم التعديل الأقل تقييدًا والتقنية المساندة المناسبة.','اجمع بيانات عن الاستقلال والمشاركة والضيق.','وثق الموافقة والخصوصية والحقوق وإمكان الاعتراض.']))+card('هدف وظيفي قابل للقياس','<p>صغ الهدف في سياق يومي مع مستوى المساعدة والزمن ومعيار النجاح. الغاية زيادة الوصول والاختيار والأمان والمشاركة والاستقلال، لا جعل الشخص يبدو أكثر شبهًا بالآخرين.</p>')
 if k=='practice':
  return card('تنفيذ قابل للمراجعة',li(['عرّف المشكلة بمثال قابل للملاحظة لا بحكم على الشخصية.','افحص ما يسبق الموقف وما يليه والنوم والألم والضغط.','اسأل الشخص عما يساعده وطريقة التواصل المفضلة.','اختر خطوة صغيرة آمنة يمكن تكرارها.','سجل الإجراء والنتيجة وقارن ظروفًا متشابهة.']))+card('مؤشرات نتيجة مفيدة',li(['انخفاض الضيق أو وقت التعافي.','زيادة المشاركة أو الاستقلال أو التواصل.','تحسن الروتين أو العلاقات دون ضغط زائد.','إمكان استمرار الخطة وعدم ظهور ضرر أو حرمان.']))
 return card('استخدام القسم بكفاءة',li(['ابدأ بالتعريف والحدود.','راجع الفروق مع الموضوعات القريبة.','انتقل إلى الأدلة العملية عند الحاجة.','استخدم الأدوات ضمن غرضها المعلن.','تحقق من المصدر والتاريخ ودرجة الدليل.','اطلب مساعدة متخصصة للقرار عالي الأثر.']))
def block(k,t):
 src={'compare':'mental','evidence':'evidence','measure':'measure','support':'support','practice':'practice','mental':'mental','hub':'hub'}[k]
 note='<p class="content-depth-v222__note"><strong>السلامة:</strong> المحتوى تثقيفي ولا يثبت تشخيصًا. عند خطر مباشر أو أفكار إيذاء أو تغير حاد في الوعي أو القدرة على العناية بالنفس، استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة.</p>'
 return f'<section class="content-depth-v222" data-content-depth-v222="{k}"><h2>محتوى علمي وعملي موسع حول {esc(t)}</h2><div class="content-depth-v222__grid">{common(t)}{specific(k,t)}{source_card(src)}</div>{note}</section>'
def eligible(rel,x):
 if rel in ('404.html','offline.html','google644f1f7a8b7aaa2b.html') or rel.startswith(('assets/','coverage/','reports/','tmp/','node_modules/','provider-assessment-demo/','en/','es/')):return None,'skipped_special'
 if lang(x)!='ar':return None,'skipped_language'
 if noindex(x):return None,'skipped_noindex'
 return (POL.get(rt(rel)),'eligible') if POL.get(rt(rel)) else (None,'skipped_unclassified')
def enrich(path,site):
 rel=path.relative_to(site).as_posix();x=path.read_text(encoding='utf-8');p=parse(x);before=words(' '.join(p.txt));pol,state=eligible(rel,x);r={'path':rel,'route':rt(rel),'before_words':before,'status':state}
 if not pol:return r
 k,minimum=pol;r.update(kind=k,minimum_words=minimum)
 if START in x:r.update(status='already_enriched',after_words=before,below_minimum=before<minimum);return r
 if before>=minimum:r.update(status='sufficient',after_words=before,below_minimum=False);return r
 href=BASE+'assets/css/content-depth-v222.css'
 if href not in x:
  if '</head>' not in x:raise ValueError('missing head')
  x=x.replace('</head>',f'<link rel="stylesheet" href="{href}"></head>',1)
 z=START+block(k,topic(p,rel))+END
 if '</main>' in x:x=x.replace('</main>',z+'</main>',1)
 elif '</body>' in x:x=x.replace('</body>',z+'</body>',1)
 else:raise ValueError('missing insertion point')
 after=words(' '.join(parse(x).txt));path.write_text(x,encoding='utf-8');r.update(status='enriched',after_words=after,added_words=after-before,below_minimum=after<minimum);return r
def run(site):
 site=Path(site).resolve();css=site/'assets/css/content-depth-v222.css';css.parent.mkdir(parents=True,exist_ok=True);css.write_text(CSS+'\n',encoding='utf-8');res=[];fail=[]
 for p in sorted(site.rglob('*.html')):
  try:res.append(enrich(p,site))
  except Exception as e:fail.append({'path':p.relative_to(site).as_posix(),'error':f'{type(e).__name__}: {e}'})
 elig=[x for x in res if 'minimum_words' in x];rem=[x for x in elig if x.get('below_minimum')];rep={'version':V,'status':'passed' if not fail and not rem else 'failed','pages_scanned':len(res)+len(fail),'eligible_pages':len(elig),'enriched_pages':sum(x.get('status')=='enriched' for x in res),'sufficient_pages':sum(x.get('status')=='sufficient' for x in res),'remaining_below_minimum':len(rem),'failure_count':len(fail),'policies':{k:{'kind':v[0],'minimum_words':v[1]} for k,v in POL.items()},'failures':fail[:200],'remaining':rem[:200],'enriched':[x for x in res if x.get('status')=='enriched'][:500]};out=site/'api/content-depth-v222.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return rep
def main():
 a=argparse.ArgumentParser();a.add_argument('site',nargs='?',default='_site');r=run(a.parse_args().site);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())