# مصطلحات علم النفس | Psychology Terminology

موسوعة عربية منظمة في علم النفس والصحة النفسية، مرتبطة بالمحتوى المرئي المنشور عبر **@pterminology**، ويجري تطويرها كبنية مؤسسية قابلة للتوسع في الصحة النفسية والأشخاص ذوي الاحتياجات الخاصة والتربية الدامجة.

## الروابط الرسمية

- الموقع: https://khaledaltheeb.github.io/pterminology-site/
- الموسوعة الموسعة: https://khaledaltheeb.github.io/pterminology-site/encyclopedia/
- المعجم الأساسي: https://khaledaltheeb.github.io/pterminology-site/terms/
- المراكز الموضوعية: https://khaledaltheeb.github.io/pterminology-site/hubs/
- واجهة API: https://khaledaltheeb.github.io/pterminology-site/api/
- Instagram: https://www.instagram.com/pterminology/
- YouTube: https://www.youtube.com/@psychology-term
- Sitemap Index: https://khaledaltheeb.github.io/pterminology-site/sitemap.xml

## الإصدار المؤسسي

- أكثر من 2000 صفحة مفهوم وموضوع نفسي مستقلة.
- 200 صفحة مركزية تربط المحتوى في مجموعات موضوعية صغيرة.
- أكثر من 2000 عنوان قابل للفهرسة عبر Sitemap Index مجزأ.
- واجهة بحث عربية/إنجليزية ومسارات متعددة اللغات.
- صفحات مستقلة بعناوين ووصف وCanonical وhreflang وJSON-LD.
- إثراء موضوعي آلي للكلمات المفتاحية ووسوم Schema.org لكل صفحة عامة قابلة للفهرسة.
- فهرس API موحد للصفحات، وتصنيف موضوعي للأقسام واللغات والوسوم.
- كتالوج دورات لا ينشر أي بيانات خارجية إلا بعد اجتياز تحقق الإذن والترخيص والهوية والرابط القانوني.
- ملفات API وCSV وJSON Schema قابلة للاستخدام في التكاملات المصرح بها.
- نظام استيراد مستقبلي من CSV دون تعديل القوالب.
- اختبارات تمنع التكرار ونقص الصفحات وفساد خرائط الموقع والروابط اليتيمة وضعف بيانات الاكتشاف.
- ملف تحقق Google Search Console محفوظ في جذر الموقع.

## خرائط الموقع

- `sitemap.xml`: الفهرس الرئيسي.
- `sitemap-terms-1.xml`: أول 1000 صفحة.
- `sitemap-terms-2.xml`: ثاني 1000 صفحة.
- `sitemap-hubs.xml`: المراكز الموضوعية.
- `sitemap-core.xml`: الصفحات الأساسية والأدلة والأدوات.

## واجهة البيانات

- `api/v1/platform.json`: هوية المنصة والأقسام والقدرات ونقاط التكامل.
- `api/v1/content-index.json`: فهرس الصفحات العامة بعناوينها وأوصافها وأقسامها ولغاتها ووسومها.
- `api/v1/taxonomy.json`: التصنيف الموضوعي واللغوي وعدد الصفحات المرتبطة بكل وسم.
- `api/v1/courses.json`: كتالوج بيانات الدورات المخولة؛ يبقى فارغًا عند عدم وجود إذن صالح.
- `api/v1/openapi.json`: عقد OpenAPI 3.1 للواجهات العامة.
- `api/v1/courses.schema.json`: JSON Schema لتغذية بيانات الدورات المخولة.

## توسيع المحتوى

لاستيراد صفحات موسوعية جديدة، استخدم الملف:

```text
content/import-template.csv
```

وتفاصيل الحقول والقواعد موجودة في:

```text
content/README.md
```

لإضافة تغذية دورات بعد الحصول على الإذن، تُراجع القواعد في:

```text
content/authorized-course-feeds/README.md
```

## منهج المحتوى

المحتوى للتثقيف العام، ويُبنى على الوضوح، والربط الداخلي، والتمييز بين المفاهيم، وتجنب التشخيص السريع والوصم والادعاءات المطلقة. تُعطى الأولوية للمصادر الرسمية، والإرشادات المهنية، والمراجعات المنهجية، والدراسات الأصلية الملائمة للسؤال، مع توضيح حدود الدليل والاستخدام.

## سياسة النشر

يُبنى الموقع ويُنشر من أحدث `main` فقط بعد نجاح بوابات الإنتاج، مع ختم `deployment.json` ومطابقة SHA والملفات الحرجة على النسخة الحية. تعمل طبقات الإثراء الموضوعي وفهارس API والتحقق من تغذيات الدورات ضمن مسار البناء، بحيث تمنع بوابات الجودة إصدار نسخة ناقصة أو غير مخولة.

---

**Psychology Terminology** is an Arabic-first structured psychology encyclopedia with more than 2,000 indexable concept pages, 200 topic hubs, split sitemaps, reusable data imports, automated topical metadata, public discovery indexes, authorized course feeds, and automated release validation.
