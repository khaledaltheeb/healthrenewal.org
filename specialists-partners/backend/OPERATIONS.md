# تشغيل قطاع المختصين والمحادثات

**النسخة التشغيلية:** v4 — جلسات إدارية قصيرة، صلاحيات أدوار، سجل ملفات عام حي، اعتماد ونشر وتعليق، مراجعة دورية، محادثات آمنة، إشعارات، وسجل إصدارات وتدقيق.

هذه الوثيقة تغطي تشغيل البنية الخلفية لقطاع «فريقنا وشركاؤنا ذوو الاختصاص». الواجهة العامة مستضافة على GitHub Pages، بينما تحفظ الطلبات والمحادثات والبيانات الخاصة داخل Cloudflare D1 خلف Cloudflare Worker.

## مبدأ فصل البيانات

- `specialists-partners/data/providers.json`: حقول عامة فقط، بعد التحقق والموافقة الكتابية.
- `providers_private`: بريد المختص وحالة الإشعارات واستقبال الطلبات. لا يُصدّر إلى GitHub Pages.
- `provider_profiles`: الملف العام المنقح وحالات النشر والتحقق والموافقة.
- `provider_review_records`: قائمة التحقق والأعداد والملاحظات الخاصة؛ لا تُعرض للعامة.
- `provider_profile_versions`: نسخ غير قابلة للاستبدال لاستعادة تاريخ التغيير.
- `admin_sessions`: بصمات جلسات إدارية قصيرة؛ لا يُخزن رمز الجلسة الأصلي.
- `applications`: طلبات الانضمام الكاملة للمراجعة الإدارية.
- `conversations` و`messages`: المحادثات الخاصة.
- `conversation_tokens`: بصمات SHA-256 للروابط؛ لا تخزن الرموز الأصلية.
- `email_events`: حالة الإرسال وبصمة المستلم فقط، دون تخزين نص الرسالة أو البريد في سجل الإرسال.
- `audit_log`: سجل تغييرات تشغيلي لا يستبدل سجلًا قانونيًا أو طبيًا.

## الأسرار المطلوبة في GitHub

أضفها من إعدادات المستودع، ولا تضع قيمها في ملف أو تعليق أو Issue:

| السر | الاستخدام |
|---|---|
| `CLOUDFLARE_API_TOKEN` | نشر Worker وتطبيق D1 migrations |
| `CLOUDFLARE_ACCOUNT_ID` | حساب Cloudflare |
| `SPECIALISTS_D1_DATABASE_ID` | معرف قاعدة D1 |
| `RESEND_API_KEY` | إرسال الإشعارات |
| `TURNSTILE_SECRET` | التحقق الإلزامي من النماذج |
| `SPECIALISTS_ADMIN_API_KEY` | حماية لوحة الإدارة، 32 حرفًا عشوائيًا على الأقل |
| `SPECIALISTS_REVIEWER_API_KEY` | اختياري: مراجع يستطيع بدء المراجعة دون اعتماد أو نشر |
| `SPECIALISTS_MODERATOR_API_KEY` | اختياري: مشرف للمحادثات دون صلاحية الملفات |
| `SPECIALISTS_RATE_LIMIT_SALT` | تمليح بصمات عناوين IP، 32 حرفًا عشوائيًا على الأقل |
| `SPECIALISTS_FROM_EMAIL` | مرسل من نطاق موثق في Resend |

قيمة `SPECIALISTS_FROM_EMAIL` تكون مثل:

```text
منصة المختصين <notifications@example.org>
```

يجب توثيق النطاق في Resend قبل الإرسال إلى المختصين والزوار. وضع الاختبار الافتراضي في Resend لا يكفي للإرسال إلى عناوين عامة.

## الإعداد في Cloudflare

1. أنشئ D1 باسم `pterminology-specialists`.
2. أنشئ Turnstile Widget مقيّدًا بالنطاق `khaledaltheeb.github.io`.
3. أنشئ API Token محدودًا بالحساب وبصلاحيات Workers وD1 المطلوبة فقط.
4. أضف أسرار GitHub السابقة.
5. شغّل Workflow: `Deploy specialists messaging backend`.
6. أدخل عنوان Worker العام ومفتاح Turnstile العام.
7. اترك تطبيق migrations وتحديث إعداد الواجهة مفعّلين في أول نشر.

Workflow يطبق ملفات `migrations/` بالترتيب، يرفع الأسرار مع نسخة Worker، يفحص `/health`، ثم يحدّث `runtime-config.js` بالقيم العامة فقط.

## لوحة الإدارة

المسار:

```text
/specialists-partners/admin/
```

اللوحة `noindex` ولا تحفظ المفتاح في `localStorage` أو `sessionStorage`. أدخل:

- عنوان Worker العام.
- `SPECIALISTS_ADMIN_API_KEY` للمالك، أو أحد المفتاحين المحدودين للمراجع ومشرف
  المحادثات. تعرض اللوحة الدور الفعلي وتخفي الإجراءات غير المسموحة تلقائيًا.

يُرسل المفتاح مرة واحدة لإنشاء جلسة Bearer قصيرة، ثم يُمسح من الحقل والذاكرة.

الوظائف:

- مؤشرات الطلبات والمحادثات والحسابات وفشل البريد.
- مراجعة طلبات الانضمام وتغيير حالتها.
- نقل الطلب إلى محرر الملف بضغطة واحدة.
- إضافة شخص أو مركز يدويًا.
- حفظ مسودة، إرسال للمراجعة، اعتماد ونشر، تعليق، سحب موافقة، وأرشفة.
- منع النشر حتى اكتمال الهوية والمؤهل والنطاق والترخيص/التسجيل والتواصل والموافقة وموعد المراجعة.
- فتح أو إغلاق أو حظر أو أرشفة المحادثات.
- تفعيل أو تعطيل إشعارات المختص واستقبال الطلبات.
- مراجعة سجل التدقيق.

قبول الطلب وحده لا يكفي للنشر. زر «اعتماد ونشر» يطبق بوابة التحقق الخادمية
ويكتب النسخة العامة المنقحة في D1. يقرأ الدليل `/v1/providers` أولًا ويعود إلى
`providers.json` كنسخة احتياطية عامة فقط عند تعذر الخدمة.

## فحص ما قبل الإطلاق

- `/health` يعيد `200` وجميع checks بقيمة `true`.
- نموذج الانضمام يولد مرجع `APP-*` ويصل إشعاره إلى `pterminology@gmail.com`.
- الطلب يظهر في لوحة الإدارة.
- حساب المختص الخاص مرتبط بالمعرف نفسه المستخدم في `providers.json`.
- فتح محادثة يولد مرجع `CONV-*`.
- يصل رابط مختلف للزائر والمختص.
- يستطيع المختص الرد وإغلاق المحادثة وإعادة فتحها.
- لا يظهر بريد المختص الخاص في مصدر الصفحة أو JSON العام.
- Turnstile يرفض الرمز المنتهي أو المعاد استخدامه.
- فشل Resend يظهر في `email_events` ومؤشر لوحة الإدارة.

## النسخ الاحتياطي والاستجابة للحوادث

- استخدم نسخ D1 الاحتياطية قبل migrations الجوهرية.
- دوّر `SPECIALISTS_ADMIN_API_KEY` فور الاشتباه بالتسرب.
- دوّر `RESEND_API_KEY` و`TURNSTILE_SECRET` من مزودي الخدمة، ثم حدّث GitHub Secrets.
- عند إساءة الاستخدام، حوّل المحادثة إلى `blocked` وعلّق حساب المختص عند الحاجة بدل حذف الأدلة فورًا.
- لا ترسل قواعد البيانات أو سجلات المحادثة في Issues عامة.
- راجع الاحتفاظ بالبيانات وفق القوانين والسياسات المعتمدة قبل استقبال بيانات حقيقية.

## المراجع التشغيلية الرسمية

- Cloudflare Workers GitHub Actions: https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- Cloudflare D1 migrations: https://developers.cloudflare.com/d1/reference/migrations/
- Cloudflare Turnstile server validation: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- Resend Send Email API: https://resend.com/docs/api-reference/emails/send-email
