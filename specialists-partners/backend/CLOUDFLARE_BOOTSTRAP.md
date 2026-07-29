# تهيئة Cloudflare لقطاع المختصين

هذه الوثيقة مخصصة لتشغيل Workflow باسم **Bootstrap specialists Cloudflare**. ينشئ المسار الموارد المطلوبة أو يعيد استخدام الموارد الموجودة، ثم يطبق ترحيلات D1 وينشر Worker ويربط الواجهة العامة.

## الحد اليدوي الوحيد

لا يمكن لملف المستودع إنشاء رمز الوصول الأول بنفسه. يجب إنشاء **Account API Token** مرة واحدة من لوحة Cloudflare ثم حفظه في GitHub Secrets. لا يوضع الرمز في Issue أو Commit أو رسالة محادثة.

## حساب Cloudflare المستهدف

- Account ID: `826ac34927c1e045c06145a327c2ac52`
- Worker: `pterminology-specialists`
- D1: `pterminology-specialists`
- Turnstile widget: `pterminology-specialists-forms`
- Allowed hostname: `khaledaltheeb.github.io`

## صلاحيات رمز Cloudflare

أنشئ Custom Account API Token باسم واضح مثل:

`pterminology-specialists-github-deploy`

أضف صلاحيات الحساب التالية فقط:

| النطاق | الصلاحية | المستوى |
|---|---|---|
| Account | Workers Scripts | Edit |
| Account | D1 | Edit |
| Account | Turnstile Sites | Edit |

قيد الموارد على الحساب المحدد فقط. لا تمنح صلاحيات DNS أو Billing أو Account Members أو API Tokens Edit.

لا تضف تقييد IP للرمز المستخدم من GitHub-hosted runners لأن عناوينها متغيرة. يمكن وضع تاريخ انتهاء مناسب ثم تدوير الرمز عند نقل المشروع إلى الحساب النهائي.

## GitHub Secrets المطلوبة

أضف القيم التالية من:

`Repository Settings → Secrets and variables → Actions → New repository secret`

| الاسم | القيمة |
|---|---|
| `CLOUDFLARE_API_TOKEN` | رمز Cloudflare محدود الصلاحيات |
| `RESEND_API_KEY` | مفتاح إرسال البريد من Resend |
| `SPECIALISTS_ADMIN_API_KEY` | مفتاح عشوائي لا يقل عن 32 حرفًا |
| `SPECIALISTS_RATE_LIMIT_SALT` | قيمة عشوائية لا تقل عن 32 حرفًا |
| `SPECIALISTS_FROM_EMAIL` | عنوان مرسل موثق، مثل `منصة المختصين <notifications@example.org>` |

يمكن إضافة مفتاحين اختياريين عند تفويض أدوار محدودة:

| الاسم | الصلاحية |
|---|---|
| `SPECIALISTS_REVIEWER_API_KEY` | مراجعة الطلبات والملفات دون اعتماد أو نشر |
| `SPECIALISTS_MODERATOR_API_KEY` | الإشراف على المحادثات دون الوصول إلى اعتماد الملفات |

يجب أن يكون كل مفتاح مستقلًا ولا يقل عن 32 حرفًا. يمكن إنشاء القيم العشوائية
محليًا دون إرسالها لأي شخص:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

شغّل الأمر مرة مستقلة لكل سر عشوائي واحفظ كل قيمة في السر المناسب.

## ما ينفذه Workflow تلقائيًا

1. يتحقق من أن Cloudflare token فعال.
2. يبحث عن قاعدة D1 بالاسم المحدد وينشئها إذا لم تكن موجودة.
3. يبحث عن Turnstile widget وينشئه أو يدور سره مع فترة انتقال.
4. يتأكد من وجود Workers subdomain للحساب.
5. يولد `wrangler.toml` وملف الأسرار مؤقتًا داخل runner.
6. يطبق جميع ترحيلات D1 البعيدة.
7. ينشر Worker مع الأسرار المشفرة.
8. يفعّل عنوان `workers.dev` للخدمة.
9. يفحص مسار `/health` بعد النشر.
10. يحدث `specialists-partners/assets/runtime-config.js` بالقيم العامة فقط.
11. يحذف الملفات المؤقتة التي احتوت أسرارًا.

## التشغيل

من تبويب Actions اختر:

`Bootstrap specialists Cloudflare → Run workflow`

اترك القيم الافتراضية ما لم يتغير الحساب أو اسم الموارد.

## معايير النجاح

- نجاح جميع خطوات Workflow.
- استجابة `/health` بحالة HTTP 200 و`ok: true`.
- ظهور `apiBase` و`turnstileSiteKey` في `runtime-config.js` دون أي قيمة سرية.
- نجاح إرسال طلب انضمام تجريبي إلى بريد الإدارة.
- نجاح إنشاء محادثة ووصول إشعار للمختص والزائر.
- بقاء البريد الخاص ووثائق التحقق خارج ملفات GitHub Pages العامة.
