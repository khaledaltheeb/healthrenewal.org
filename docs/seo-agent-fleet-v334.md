# منظومة وكلاء SEO والوصول عبر الذكاء الاصطناعي — v334

تعمل طبقة `seo_agent_fleet_v334_hardened.py` كمهايئ إنتاجي فوق المحرك المراجع `seo_agent_fleet_v334.py`، بحيث تُصحح حالات المسار الفرعي والموارد غير HTML من دون نسخ المحرك أو تفكيك بنيته.

هذه الطبقة لا تستبدل مولدات خرائط الموقع الحالية. وظيفتها تدقيق **ناتج الإنتاج `_site`** بعد اكتمال البناء، ومنع الأخطاء التي تخفض قابلية الزحف والفهرسة والاستشهاد.

## الوكلاء الثمانية

1. **TechnicalIndexabilityAgent**: العنوان والوصف وCanonical وتعارضات robots وGooglebot.
2. **SitemapCoverageAgent**: تطابق جميع الصفحات القابلة للفهرسة مع خرائط الموقع المسجلة في robots.txt.
3. **StructuredDataAgent**: صلاحية JSON-LD، السياق، الأنواع الأساسية، والروابط المطلقة.
4. **ContentSemanticsAgent**: H1، الصفحات الرقيقة، التكرار، اللغة، ومنع حشو meta keywords.
5. **InternalLinkingAgent**: الروابط الداخلية المكسورة والصفحات اليتيمة والنصوص غير الوصفية.
6. **InternationalSeoAgent**: lang وdir وhreflang وx-default وصيغة OpenGraph locale.
7. **MediaAndPreviewAgent**: alt والأبعاد وصور OpenGraph وTwitter/X وتوافق المعاينات.
8. **AiDiscoveryAgent**: وصول محركات البحث ومحركات الإجابة والوكلاء، llms.txt، وضوابط snippets.

## سياسة الوصول

- المحتوى العام مسموح لمحركات البحث ومحركات الإجابة والوكلاء الذين ينفذون طلبات المستخدم.
- السياسة الحالية تسمح أيضًا لروبوتات تدريب/تحسين النماذج، تنفيذًا لقرار مالك المشروع. يمكن فصل هذا القرار لاحقًا عبر الخيار `--disallow-training` من دون حجب Googlebot أو OAI-SearchBot أو PerplexityBot أو Applebot.
- `llms.txt` مساعد اكتشاف تكميلي، وليس بديلًا من robots.txt أو خرائط الموقع أو الروابط الداخلية أو النص القابل للفهرسة.
- السماح بالزحف لا يضمن الفهرسة أو الترتيب أو الاستشهاد داخل إجابة ذكاء اصطناعي.
- لأن الموقع الحالي منشور تحت مسار مشروع GitHub Pages، فإن ملف `robots.txt` داخل `/` ليس ملف التحكم الرسمي للمضيف. الملف الرسمي يجب أن يكون في `https://healthrenewal.org/robots.txt`. الوكيل يبلغ عن هذا كقيد معماري بدل الادعاء بأن سياسة المسار الفرعي ملزمة للزواحف. الانتقال إلى نطاق مخصص أو مستودع صفحة مستخدم يتيح التحكم الرسمي من الجذر.

## صور المعاينة الاجتماعية

يحوّل `normalize_social_previews_v334.py` جميع وسوم `og:image` و`twitter:image` التي تشير إلى SVG إلى بطاقة PNG مراجعة بقياس 1200×630، مع إبقاء رسوم SVG العادية داخل المحتوى دون تغيير. العملية تعمل بعد بناء `_site` وتعمل مرة أخرى قبل نشر GitHub Pages لضمان تطابق المعاينة المنشورة مع الفحص الإنتاجي.

## IndexNow

يُنشئ `submit_indexnow_v334.py` ملف إثبات الملكية داخل حزمة الإنتاج، ثم يقرأ خرائط الموقع المسجلة في `robots.txt` تكراريًا، ويستبعد المضيفات والمسارات الخارجية، ويزيل التكرار، ويرسل حتى 10,000 عنوان في الدفعة الواحدة بعد نجاح نشر GitHub Pages والتحقق الحي منه.

IndexNow يخص Bing والمحركات المشاركة. Google يعتمد Googlebot وخرائط الموقع وSearch Console، ولا يُعامل IndexNow كبديل عنها. فشل خدمة IndexNow الخارجية لا يوقف نشر الموقع؛ يُحفظ تقرير منفصل للمراجعة.

## التشغيل

```bash
python -m unittest discover -s tests -p 'test_*v334*.py' -v
python scripts/normalize_social_previews_v334.py _site \
  --base-url https://healthrenewal.org/
python scripts/seo_agent_fleet_v334_hardened.py _site \
  --base-url https://healthrenewal.org/ \
  --report-dir api/seo-audit-v334 \
  --fail-on critical
```

لإعادة إنشاء ملفات الاكتشاف والسياسة:

```bash
python scripts/seo_agent_fleet_v334.py . \
  --base-url https://healthrenewal.org/ \
  --write-discovery-files
```

للسماح بالبحث والإجابات مع منع تدريب النماذج:

```bash
python scripts/seo_agent_fleet_v334.py . \
  --base-url https://healthrenewal.org/ \
  --write-discovery-files \
  --disallow-training
```

اختبار إعداد IndexNow دون اتصال خارجي:

```bash
python scripts/submit_indexnow_v334.py _site \
  --base-url https://healthrenewal.org/ \
  --key a4f9d7c2e81b4630b5d6f7a912ce3048 \
  --prepare-only \
  --report api/indexnow-preparation-v334.json
```

## مخرجات الإثبات

- `_site/api/seo-audit-v334/seo-agent-report-v334.json`
- `_site/api/seo-audit-v334/seo-agent-report-v334.md`
- `_site/api/social-preview-normalization-v334.json`
- `_site/assets/social-card-v334.png`
- `_site/api/indexnow-preparation-v334.json`
- `_site/api/indexnow-submission-v334.json`
- Artifacts في GitHub Actions لكل فحص إنتاج ولكل إرسال IndexNow.
