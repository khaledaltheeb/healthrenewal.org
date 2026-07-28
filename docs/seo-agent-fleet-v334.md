# منظومة وكلاء SEO والوصول عبر الذكاء الاصطناعي — v334

هذه الطبقة لا تستبدل مولدات خرائط الموقع الحالية. وظيفتها تدقيق ناتج النشر الكامل ومنع الأخطاء التي تخفض قابلية الزحف والفهرسة والاستشهاد.

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

## التشغيل

```bash
python -m unittest discover -s tests -p 'test_seo_agent_fleet_v334.py' -v
python scripts/seo_agent_fleet_v334.py . \
  --base-url https://khaledaltheeb.github.io/pterminology-site/ \
  --report-dir seo-audit \
  --fail-on critical
```

لإعادة إنشاء ملفات الاكتشاف والسياسة:

```bash
python scripts/seo_agent_fleet_v334.py . \
  --base-url https://khaledaltheeb.github.io/pterminology-site/ \
  --write-discovery-files
```

للسماح بالبحث والإجابات مع منع تدريب النماذج:

```bash
python scripts/seo_agent_fleet_v334.py . \
  --base-url https://khaledaltheeb.github.io/pterminology-site/ \
  --write-discovery-files \
  --disallow-training
```

## مخرجات الإثبات

- `seo-audit/seo-agent-report-v334.json`
- `seo-audit/seo-agent-report-v334.md`
- Artifact دائم في GitHub Actions لكل تشغيل.
