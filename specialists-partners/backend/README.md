# Specialist Sector Gateway

طبقة خلفية مستقلة لقطاع المختصين والشراكات المهنية. صُممت لتعمل خلف موقع GitHub Pages دون وضع البريد الخاص أو مفاتيح الخدمات في ملفات الموقع العامة.

## الوظائف

- استقبال طلبات انضمام المختصين والمراكز وإرسال نسخة إلى إدارة المنصة.
- حفظ الطلب برقم متابعة داخل Cloudflare D1.
- إنشاء محادثة خاصة بين الزائر والمختص.
- إرسال إشعار بريدي للمختص والزائر وإدارة المنصة.
- روابط وصول عشوائية، مع تخزين بصمة SHA-256 فقط وانتهاء صلاحية تلقائي.
- حماية Turnstile، وحدود يومية حسب بصمة عنوان الاتصال، وسجل تدقيق.
- عدم دعم المرفقات في النسخة الأولى لتقليل مخاطر تسرب الوثائق الحساسة.

## النشر

1. أنشئ Cloudflare Worker وقاعدة D1.
2. انسخ `wrangler.toml.example` إلى `wrangler.toml` وأدخل معرف قاعدة D1.
3. نفّذ الترحيل:

```bash
wrangler d1 execute pterminology-specialists --remote --file=migrations/0001_initial.sql
```

4. أضف الأسرار:

```bash
wrangler secret put RESEND_API_KEY
wrangler secret put TURNSTILE_SECRET
wrangler secret put ADMIN_API_KEY
```

5. تحقق من نطاق إرسال البريد لدى مزود البريد، ثم اضبط `FROM_EMAIL`.
6. انشر العامل:

```bash
wrangler deploy
```

7. ضع رابط العامل العام ومفتاح Turnstile العام داخل:

```text
specialists-partners/assets/runtime-config.js
```

## إضافة بريد مختص إلى النظام الخاص

بعد نشر ملف المختص العام في `data/providers.json`، أضف بريده الخاص إلى D1 عبر المسار الإداري. هذا البريد لا يظهر في الدليل.

```bash
curl -X POST "https://YOUR-WORKER.example/v1/admin/providers" \
  -H "content-type: application/json" \
  -H "x-admin-key: YOUR_ADMIN_KEY" \
  -d '{
    "providerId":"provider-public-id",
    "displayName":"الاسم المهني",
    "email":"private-notification@example.com",
    "status":"active",
    "notificationEnabled":true
  }'
```

## متغيرات البيئة

| المتغير | الغرض |
|---|---|
| `DB` | ربط قاعدة D1 |
| `OWNER_EMAIL` | البريد الذي يستقبل طلبات الانضمام وإشعارات الإدارة |
| `RESEND_API_KEY` | مفتاح إرسال البريد |
| `FROM_EMAIL` | عنوان إرسال موثّق |
| `TURNSTILE_SECRET` | التحقق الخادمي من Turnstile |
| `ADMIN_API_KEY` | حماية مسارات الإدارة |
| `ALLOWED_ORIGINS` | النطاقات المسموح لها باستدعاء الواجهة |
| `PORTAL_BASE_URL` | رابط بوابة المحادثة في الموقع |
| `RATE_LIMIT_SALT` | قيمة سرية لبصمة عناوين الاتصال |

## حدود النسخة الأولى

- روابط الوصول صالحة لمدة 90 يومًا ويمكن إصدار أكثر من رابط للدور نفسه دون إبطال الروابط السابقة.
- لا توجد مرفقات، مكالمات، دفع، مواعيد، أو تشخيص آلي.
- يلزم لاحقًا إضافة لوحة إدارة كاملة، سياسة احتفاظ زمنية، تصدير بيانات، وحذف ذاتي موثّق قبل التوسع الكبير.
