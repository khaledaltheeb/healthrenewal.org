# سياسة البيانات المنظمة للموقع — v332

تطبّق هذه الحزمة طبقة `Schema.org` بصيغة `JSON-LD` على **كل صفحة HTML مولّدة**، مع بوابة تحقق تمنع البيانات الطبية غير المدعومة أو المخفية.

## ما الذي يُنشأ تلقائيًا

- `Organization` و`WebSite` بهويات ثابتة وروابط القنوات الرسمية.
- نوع الصفحة الأنسب: `CollectionPage` أو `MedicalWebPage` أو `WebPage`.
- `BreadcrumbList` مشتق من المسار العام للصفحة.
- `Article` لقراءات المجلة والأبحاث، مع `citation` للروابط المؤسسية وDOI/PubMed الظاهرة.
- `WebApplication` للأدوات والمختبرات التفاعلية.
- `FAQPage` فقط للأسئلة والأجوبة الظاهرة فعليًا داخل الصفحة.
- `MedicalCondition` فقط عند وجود تصريح صريح في الصفحة؛ لا يحوّل المحرك كل مصطلح نفسي أو مورد دامج إلى تشخيص.

## عقد البيانات الطبية الصريح

لإضافة `MedicalCondition` إلى صفحة حالة، تستخدم بيانات المصدر واحدًا أو أكثر من الحقول التالية:

```html
<meta name="schema:type" content="MedicalCondition">
<meta name="medical-condition-name" content="اسم الحالة">
<meta name="medical-code" content="6A02">
<meta name="medical-coding-system" content="ICD-11">
<meta name="medical-symptoms" content="علامة أولى، علامة ثانية">
<meta name="medical-causes" content="عامل أول، عامل ثانٍ">
<meta name="medical-treatments" content="تدخل أول، تدخل ثانٍ">
<meta name="medical-risk-factors" content="عامل خطر أول، عامل خطر ثانٍ">
<meta name="medical-tests" content="تقييم أول، تقييم ثانٍ">
```

لا يُصدر المحرك كودًا طبيًا إلا إذا وُجدت **قيمة الكود ونظام الترميز معًا**. يمنع ذلك تخمين ICD أو SNOMED أو MeSH من عنوان الصفحة.

## المراجعة الطبية وE-E-A-T

يدعم المحرك `reviewedBy` عندما يتحقق شرطان معًا:

1. وجود اسم المراجع في `meta name="reviewed-by"`.
2. ظهور الاسم نفسه للمستخدم داخل النص المرئي للصفحة.

لا ينشئ المحرك أسماء أطباء أو لجان مراجعة افتراضية، ولا يصف المحتوى بأنه خضع لمراجعة سريرية دون دليل منشور. ويمكن إضافة رابط الملف المهني الموثق عبر:

```html
<meta name="reviewer-url" content="https://example.org/reviewer-profile/">
```

## المقالات العلمية

قراءات الموقع النقدية وملخصاته تُوسم افتراضيًا `Article`، لأنها ليست الورقة الأصلية نفسها. لا يُستخدم `MedicalScholarlyArticle` إلا بتصريح صريح:

```html
<meta name="schema:type" content="MedicalScholarlyArticle">
<meta name="publication-type" content="Randomized Controlled Trial">
```

هذا يمنع نسبة البحث الأصلي إلى المنصة أو الخلط بين الملخص العربي والدراسة المنشورة.

## FAQPage

يستخرج المحرك الأسئلة من عناصر `<details><summary>...</summary>...</details>` أو من بنية `data-faq-item`. لا يضيف إجابة غير مرئية، ويختبر أن السؤال والجواب موجودان في النص المقروء.

وجود `FAQPage` صحيح دلاليًا لا يعني ضمان ظهور نتيجة غنية. جوجل يقرر العرض خوارزميًا، وأصبح ظهور FAQ الغني مقصورًا عادة على مواقع حكومية وصحية موثوقة ومعروفة.

## الإصلاح والتحقق

الأمر الإنتاجي:

```bash
python scripts/apply_structured_data_v332.py _site --strict --min-pages 1000
```

المخرجات:

```text
_site/api/structured-data-v332.json
```

بوابة التحقق تضمن:

- تغطية كل صفحة HTML مؤهلة.
- صلاحية JSON-LD الذي تديره الحزمة.
- وجود صفحة وBreadcrumb في كل مخطط.
- تطابق FAQ مع المحتوى المرئي.
- عدم إخراج `reviewedBy` غير المرئي.
- إزالة أي كتلة JSON-LD قديمة تالفة قبل إضافة المخطط المُدار.
- ثبات النتيجة عند التشغيل المتكرر دون تكرار الوسم.

## المراجع التقنية

- Google Search Central — General structured data guidelines: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Google Search Central — Introduction to structured data: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- Google Search Central — FAQ rich result changes: https://developers.google.com/search/blog/2023/08/howto-faq-changes
- Schema.org — MedicalCondition: https://schema.org/MedicalCondition
- Schema.org — MedicalScholarlyArticle: https://schema.org/MedicalScholarlyArticle
- Schema.org — reviewedBy: https://schema.org/reviewedBy
