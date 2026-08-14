from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

BASE='https://healthrenewal.org'
REPORT='api/internal-route-repair-v1.json'
TAG_RE=re.compile(r'<[^>]+>')
H1_RE=re.compile(r'<h1[^>]*>(.*?)</h1>',re.I|re.S)
TITLE_RE=re.compile(r'<title>(.*?)</title>',re.I|re.S)
DESC_RE=re.compile(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)',re.I)
HREF_RE=re.compile(r'href=["\']([^"\']+)',re.I)

HUBS={
 '/special-needs/practical/':('أدوات وتطبيقات عملية لذوي الاحتياجات الخاصة','مركز تطبيقي يجمع الأدلة العملية الجاهزة للاستخدام في المنزل والمدرسة والخدمات، مع إبقاء التقييم الفردي والسلامة في المقدمة.'),
 '/special-needs/early-intervention/':('التدخل المبكر: أدلة عملية للأسرة والفريق','مركز يجمع أدلة التدخل المبكر حول التواصل والحركة والاستعداد للمدرسة والتدريب الأسري والانتقالات، مع التركيز على المشاركة والوظيفة اليومية.'),
 '/special-needs/learning/':('صعوبات التعلم والقراءة والكتابة والرياضيات','مركز عربي يجمع أدلة صعوبات التعلم والقراءة والكتابة والرياضيات والتقييم والدعم المدرسي والأسري بصورة مترابطة.'),
 '/special-needs/education/':('التربية الخاصة والتعليم الدامج','مركز يجمع أدلة التربية الخاصة والتعليم الدامج والخطط الفردية وغرف المصادر والخدمات المساندة والتكييفات والدعم السلوكي.'),
}

PATHS={
 '/learning-paths/institutional-resources/':{
  'title':'مسار استخدام المصادر المؤسسية الموثوقة',
  'desc':'مسار عملي للوصول إلى المصادر المؤسسية، فهم نوع الدليل وحدوده، ثم توثيق المصدر ومراجعته قبل استخدامه في محتوى أو قرار.',
  'steps':[
   ('ابدأ بدليل المصادر الموثقة','/verified-resources/','تعرف إلى الجهات والموارد التي راجعتها روافد، وما الذي يمكن أن يقدمه كل نوع من المصادر.'),
   ('تحقق من سجل المصدر','/source-registry/','راجع هوية المصدر ونطاقه وحالته بدل الاعتماد على اسم المؤسسة وحده.'),
   ('راجع منهج الثقة','/trust/','افهم كيف تفصل المنصة بين الدليل والتفسير وحدود الاستخدام والتحديث.'),
  ]},
 '/learning-paths/special-education/':{
  'title':'مسار أساسيات التربية الخاصة والتعليم الدامج',
  'desc':'مسار تطبيقي لفهم التعليم الدامج والخطة الفردية وغرفة المصادر والخدمات المساندة والتكييفات وقياس التقدم دون اختزال الطالب في تشخيص.',
  'steps':[
   ('ابدأ بمركز التربية الخاصة','/special-needs/education/','كوّن صورة عامة عن الأدلة التعليمية المتاحة قبل اختيار أداة أو إجراء.'),
   ('افهم الخطة الفردية','/family-guide/tools/individualized-education-plan/','حوّل الاحتياجات إلى أهداف قابلة للقياس وأدوار واضحة ومراجعة دورية.'),
   ('راجع دور غرفة المصادر','/special-needs/education/resource-room/','ميّز بين الدعم الموجه للمهارة وبين مجرد فصل الطالب عن الصف.'),
   ('نسّق الخدمات المساندة','/special-needs/education/related-services/','اربط الخدمة بهدف وظيفي وتعليمي واضج بدل جمع خدمات بلا أولوية.'),
   ('فرّق بين التيسير والتعديل','/family-guide/tools/accommodations-modifications/','اختر ما يزيل حاجز الوصول وما يغيّر متطلبات المهمة بوضوح.'),
  ]},
 '/learning-paths/writing-spelling-intervention-arabic/':{
  'title':'مسار تدخلات الكتابة والإملاء بالعربية',
  'desc':'مسار عربي يربط تقييم صعوبات الكتابة بالتدخل المنظم والتيسيرات المنزلية والمدرسية ومراقبة التقدم بدل الاكتفاء بكثرة النسخ والتكرار.',
  'steps':[
   ('افهم نمط صعوبة الكتابة','/special-needs/learning/dysgraphia/','ميّز بين الخط والتهجئة والتعبير الكتابي والمكونات الحركية واللغوية.'),
   ('حوّل المشكلة إلى دعم منزلي محدد','/family-guide/learning-support/writing-difficulties-at-home/','اختر هدفًا صغيرًا قابلًا للملاحظة بدل تدريب عام غير محدد.'),
   ('أزل حواجز الوصول','/family-guide/tools/accommodations-modifications/','استخدم التيسيرات عندما يكون الهدف إتاحة التعبير لا اختبار سرعة الكتابة اليدوية.'),
   ('راقب التقدم','/family-guide/tools/progress-monitoring/','قارن عينات متكررة بالمؤشر نفسه قبل تغيير الخطة.'),
  ]},
 '/learning-paths/intensive-arabic-reading-intervention/':{
  'title':'مسار التدخل المكثف في القراءة العربية',
  'desc':'مسار عربي متدرج من الوعي الصوتي وفك الترميز إلى الطلاقة والفهم، مع ربط التقييم بنوع التدخل ومراقبة الاستجابة بدل استخدام تدريب واحد لكل صعوبة قراءة.',
  'steps':[
   ('ابدأ بالوعي الصوتي وعلاقته بالعربية','/special-needs/learning/arabic-phonological-awareness-reading-difficulties/','حدّد ما إذا كانت الصعوبة في تحليل الأصوات والدمج والتجزئة وعلاقتها بالخط والتشكيل.'),
   ('افهم عسر القراءة وفك الترميز','/special-needs/learning/dyslexia/','اربط العلامات بالتقييم التعليمي ولا تستخدم تشخيصًا ذاتيًا من عرض منفرد.'),
   ('ابنِ الطلاقة بعد الدقة','/special-needs/learning/arabic-reading-fluency/','درّب القراءة المتصلة والسرعة المناسبة من دون التضحية بالدقة أو المعنى.'),
   ('افصل الفهم عن فك الكلمات','/special-needs/learning/reading-comprehension-learning-difficulties-arabic/','إذا كانت القراءة الدقيقة لا تتحول إلى فهم فراجع اللغة والمفردات والاستدلال وبنية النص.'),
   ('انقل الخطة إلى المنزل','/family-guide/learning-support/reading-difficulties-at-home/','اجعل التدريب قصيرًا ومتكررًا ومتسقًا مع هدف المدرسة بدل الواجبات الطويلة المرهقة.'),
  ]},
 '/learning-paths/evidence-guided/inclusive-education-foundations/':{
  'title':'مسار أسس التعليم الدامج المبني على الدليل',
  'desc':'مسار يربط مبادئ التعليم الدامج والتصميم الشامل لل٪علم بالتكييفات والتقييم القابل للوصول وماراجعة أثراللدعم في الصفخ.'),
  'steps':[
   ('افهم الوصول والمشاركة','/special-needs/science/inclusive-education-access/','ابدأ من العوائق الوظيفية في البيئة لا من تسمية التشنيص وحدها.'),
   ('استخدم متادئ UDL','/special-needs/reference/udlinclusive-education-guide/','نوّل طرض الوصول والمشاركة والتعبير قبل اللجوء الى حلول فردية معزولة.'),
   ('خطط لتكييف الصف','/special-needs/inclusive-classroom-adjustments-plan/','اربط كل تكييفب بحاجز محدد ومإشر نجاح وموعد مراجعة.'),
   ('اجعل التق؊يم قابلاً للوصول','/special-needs/accessible-classroom-assessment-design/','افصل ما تريد ق؊اسه عن العوائق الوغير المقمصودة في طريقة عرض الاختبار أو الاستتابة.'),
   ('حوّل المتادئ إلى درس','/special-needs/udl-lesson-planning-rubric/','راجع تصميم الدرس نفصه بدل انتظار فشل الٷالب ثم إضافة تعديلات متأخرة.'),
  ]},
 '/learning-paths/positive-behavior-support/':{
  'title':'مسار الدعم السلوكي الإتجابي',
  'desc':'مسار عملي لفهم وظيفة السلوك، جمع المتاجعات باسلتملر، تعليم بدائل قابل للاستخخدام وق؊اس أثر الدعم د؈ن وصص الطفل الأقرب.',
  'steps':[
   ('ابدأ بالسياق والوظيفة','/special-needs/education/classroom-behavior-support/','ص؁ ما يحدث قبل السلوك وبعده وما اللذي قد يحافظ عليه بدل تفسير؇ كصفة شخصية.'),
   ('اجمع ملاحظات منظمة','/family-guide/tools/behavior-log/','استخدم سجلًا مختصرً للنماط المتكرجة مع تجنب تشخيص الفهم إلى مراقبة عابرة.'),
   ('ابن خطة دعم وظيفية','/family-guide/tools/functional-behavior-support-plan/','حدد مهارة بديلة وتعديلا بيئيًا واستجابة متسقة قابلة للتنفيذ.'),
   ('راجع دليل الدعم الإيجابي','/special-needs/guides/sensory-behavior/positive-behavior-support/','وازن بين الوقاية والتعليم والاستجابة مم مراعاة التواصل والحساسية الحسية.'),
   ('تابع الً6موك بصورة يومية','/daily-tools/positive-behavior-observation/','استخخدم أداة المتتابعة اليومية لمقارنة السياقات من دون تتحويلها إلى تشخيص.'),
  ]},
 '/learning-paths/accessible-content-creator/':{
  'title':'مسار منش☃b�ffb�b�f#f$�b�fb�b�b�f(�b�ffb�b�f�fff#b�f#f��(�����͌��fb�b�băb�fff(�fb�fb�b��fb�b�f#f$�b�b�b�f(�b�fff(�f+fff�b�ff#b�f#f�b�ff+f�b�ff+b��b�fb�ff+b��f#b�b�b�b�b���fb�b��fb�b�fb��fffb�b�b�b�b0�b�f#b�fb�]��ff#b�b�f �b�b�ff+ff+b��fb�fb��f#b�b�b�b�b�băb�fb�b�b�b�b�b�b�f�fb�f�b�ffb�bĸ���(����ѕ�̜�l(�����b�b�b�b��b�b�ffb�b�f#f$�b�fb�b�b�f(�b�ffb�b�f�fff#b�f#f����������������̽�����ͥ�����Ʌ��������х�����ѕ�м���b�b�b�b�b�ffb�b��f#b�fb�ff+b��f#b�fb�b�b�b�f�f#b�ffb�b�b�b��b�b�băb�ffb�b�f�f#fb�b�b�b�b��b�fb�b�b�b�����(�����b�b�f�]�ff(�b�fb�b�ff�b�fb�fff(����������������̽����х�����ɹ���������ͥ������ݍ���ȼ���b�b#f�fb�b�b�b�b�fb�b�b�b�f�f#b�fb�b�b�f+f�f#b�ffff�f#b�ffb�b�fb��b�ff$�fb�b�fb�b�b��fb�b�fb��ffb�b�b�b�b�bĸ���(�����b�b�f�ff#b�b��b�b�f�fb�fb�����������������̽�����ͥ�������ɹ������ѕɥ��̵�Ʌ�������f#ffGfăb�b�b�b�f�f#b�b�b�b��fffb�bԃf#b�fb�f#b��f#b�fb�f#b�b��f#b�b�f+fb��b�fb�fb�b�f�b�b�b��b�ffb�f����(�����b�b�b�b�băb�fb�fb+f+f�fffff����������������̽�����ͥ���������ɽ�����͕�͵��е��ͥ������b�b�fb��b�f�f#b�b�fb��b�fb�ff+f+f�fb��b�ff+b̃b�b�b�f�b�ff#b�f#f�b�b�f�b�ffb�b�fb��b�f �b�fffb�b�b��b�ffbfb�f#b�b�����(�����b�b�b�b�b�fb�fb�b�b�f�f#b�ffb�bȜ�����ٕ�����̽���ѕ�е��͍�ٕ�伜��b�ff?b��ff�b�f�b�fb�fb�ff(�ffb�b�ffb�b�f+b�fا�1����aسلوكز�افيسض تمارкآص للموتوم لؼسج�ويمين والمحوولوخˉ�K�_K�B�,�