# منصة روافد | Rawafid Platform

موسوعة عربية منظمة في علم النفس والصحة النفسية، مرتبطة بالمحتوى المرئي المنشور عبر **@pterminology**.

## الروابط الرسمية

- الموقع: https://healthrenewal.org/
- الموسوعة الموسعة: https://healthrenewal.org/encyclopedia/
- المعجم الأساسي: https://healthrenewal.org/terms/
- المراكز الموضوعية: https://healthrenewal.org/hubs/
- بوابة كوكرين العربية للأدلة والتعلّم: https://healthrenewal.org/cochrane/
- أكاديمية الدليل الصحي العربية: https://healthrenewal.org/cochrane/evidence-academy/
- فهرس موارد كوكرين بصيغة JSON: https://healthrenewal.org/api/v1/cochrane-resources.json
- فهرس أكاديمية الدليل بصيغة JSON: https://healthrenewal.org/api/v1/cochrane-evidence-academy.json
- سجل المصادر ومسارات التكامل: https://healthrenewal.org/source-registry/
- سجل المصادر بصيغة JSON: https://healthrenewal.org/api/source-registry.json
- إفادة الإتاحة وخطة التوافق: https://healthrenewal.org/accessibility/
- Instagram: https://www.instagram.com/pterminology/
- YouTube: https://www.youtube.com/@psychology-term
- Sitemap Index: https://healthrenewal.org/sitemap-index.xml

## الإصدار الثامن

- 2000 صفحة مفهوم وموضوع نفسي مستقلة.
- 200 صفحة مركزية تربط المحتوى في مجموعات صغيرة.
- أكثر من 2000 عنوان قابل للفهرسة عبر Sitemap Index مجزأ.
- واجهة بحث عربية/إنجليزية.
- صفحات مستقلة بعناوين ووصف وCanonical وhreflang وJSON-LD.
- ملفات API وCSV قابلة للتنزيل.
- سجل محكوم للمصادر الرسمية المرشحة، يفصل بين المصدر والشريك ويمنع الاستيراد قبل مراجعة الحقوق والجودة.
- بوابة عربية مستقلة لموارد كوكرين الرسمية، مع فصل واضح بين الإحالة والشراكة والترجمة وإعادة الاستخدام.
- أكاديمية عربية موسعة للأدلة تضم مسارات للثقافة الدليلية والبحث والاستخدام، التعلم والمشاركة والترجمة، الصحة النفسية والإدمان، الطفولة والتأهيل والاحتياجات الخاصة والإنصاف، والحقوق والمنهجيات والندوات.
- نظام استيراد مستقبلي من CSV دون تعديل القوالب.
- اختبارات تمنع التكرار ونقص الصفحات وفساد خرائط الموقع.
- ملف تحقق Google Search Console محفوظ في جذر الموقع.

## الإتاحة

الهدف الهندسي المعلن هو الوصول إلى توافق موثق مع **WCAG 2.2 بالمستوى AA** والتقييم وفق **WCAG-EM 2.0**. لا يوجد حاليًا ادعاء امتثال كامل أو مراجعة مستقلة مكتملة أو شهادة خارجية. تسجل صفحة الإتاحة الحالة والقيود وخطة الاختبار بصياغة قابلة للمراجعة.

## خرائط الموقع

- `sitemap.xml`: الفهرس الرئيسي.
- `sitemap-terms-1.xml`: أول 1000 صفحة.
- `sitemap-terms-2.xml`: ثاني 1000 صفحة.
- `sitemap-hubs.xml`: المراكز الموضوعية.
- `sitemap-core.xml`: الصفحات الأساسية والأدلة والأدوات.
- `sitemap-source-registry.xml`: سجل المصادر ومسارات التكامل.
- `sitemap-cochrane.xml`: بوابة كوكرين وفهرس مواردها القابل للقراءة آليًا.
- `sitemap-cochrane-evidence-academy.xml`: أكاديمية الدليل وصفحاتها المتخصصة وملف البيانات.

## توسيع المحتوى

استخدم الملف:

```text
content/import-template.csv
```

وتفاصيل الحقول والقواعد موجودة في:

```text
content/README.md
```

## منهج المحتوى

المحتوى للتثقيف العام، ويُبنى على الوضوح، الربط الداخلي، التمييز بين المفاهيم، وتجنب التشخيص السريع والوصم والادعاءات المطلقة.

## حوكمة المصادر الخارجية

إدراج جهة في سجل المصادر لا يعني شراكة أو اعتمادًا أو مراجعة أو تأييدًا. الحالة `candidate` تسمح بالاكتشاف والربط المبدئي فقط؛ أما الترجمة أو الاستيراد أو إعادة الاستخدام أو استخدام الشعارات فتحتاج مراجعة حقوقية وتقنية وتحريرية مستقلة.

## سياسة النشر

يُبنى الموقع ويُنشر من أحدث `main` فقط بعد نجاح بوابات الإنتاج، مع ختم `deployment.json` ومطابقة SHA والملفات الحرجة على النسخة الحية.

---

**Rawafid Platform** is an Arabic-first structured psychology encyclopedia with 2,000 indexable concept pages, 200 topic hubs, split sitemaps, reusable data imports, a governed external-source registry, and automated release validation.