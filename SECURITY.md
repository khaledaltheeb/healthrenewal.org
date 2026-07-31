# سياسة الإبلاغ عن الثغرات الأمنية

## الإبلاغ الخاص

لا تنشر تفاصيل ثغرة أمنية أو خطوات استغلال أو بيانات شخصية أو صحية أو مفاتيح أو رموز وصول في Issues أو Discussions أو Pull Requests العامة.

استخدم أولًا **Private vulnerability reporting** من صفحة **Security → Advisories → Report a vulnerability** لهذا المستودع. إذا لم يظهر خيار الإبلاغ الخاص، استخدم نموذج **طلب قناة خاصة للإبلاغ الأمني** فقط لطلب وسيلة تواصل خاصة، من دون تسمية نوع الثغرة أو إضافة تفاصيل تقنية أو بيانات حساسة:

`https://github.com/khaledaltheeb/healthrenewal.org/issues/new?template=security-contact.yml`

ينشر بناء GitHub Pages الحالي بيانات الاتصال القابلة للقراءة الآلية في مسارين متطابقين:

- `https://healthrenewal.org/.well-known/security.txt` — المسار القياسي داخل موقع المشروع.
- `https://healthrenewal.org/security.txt` — مسار توافق إضافي.

لأن المنصة تعمل كموقع مشروع تحت `/`، فلا يوجد الملف عند جذر النطاق `https://healthrenewal.org/.well-known/security.txt`. يتطلب الاكتشاف من جذر النطاق نطاقًا مخصصًا أو نشرًا تحت جذر حساب GitHub Pages.

## ما يجب تضمينه داخل البلاغ الخاص فقط

- عنوان مختصر ووصف للأثر المحتمل.
- المسار أو المكوّن المتأثر والإصدار أو commit SHA عند معرفته.
- خطوات إعادة إنتاج محدودة وآمنة.
- المتصفح أو نظام التشغيل والبيئة ذات الصلة.
- أدلة منقحة من البيانات الشخصية والأسرار.
- اقتراح تخفيف أو إصلاح إن توفر.

## حدود الاختبار الآمن

- لا تصل إلى بيانات لا تخصك، ولا تغيّر بيانات أو صلاحيات أو محتوى منشورًا.
- لا تستخدم الهندسة الاجتماعية أو التصيد أو حجب الخدمة أو الاختبارات كثيفة الموارد.
- لا ترفع ملفات خبيثة، ولا تنشئ وصولًا مستمرًا، ولا تنشر أسرارًا أو بيانات صحية أو شخصية.
- أوقف الاختبار فور ظهور بيانات حساسة، واحتفظ بأقل قدر لازم من الأدلة المنقحة ثم احذفها بأمان.

## المعالجة والإفصاح

سيجري فرز البلاغ والتحقق منه وتحديد نطاق الإصلاح قبل أي إفصاح عام. لا يوجد برنامج مكافآت أو تعهد دفع ما لم يُعلن ذلك صراحةً. لا تمثل هذه السياسة تفويضًا لاختبار غير قانوني أو ضار.

---

# Security vulnerability reporting policy

## Private reporting

Do not publish vulnerability details, exploit steps, personal or health data, credentials, or tokens in public Issues, Discussions, or Pull Requests.

First use GitHub **Private vulnerability reporting** through **Security → Advisories → Report a vulnerability**. If private reporting is unavailable, use the **Request a private security contact** issue form only to request a private channel. Do not identify the vulnerability class or include technical details or sensitive data:

`https://github.com/khaledaltheeb/healthrenewal.org/issues/new?template=security-contact.yml`

The current GitHub Pages build publishes identical machine-readable contacts at:

- `https://healthrenewal.org/.well-known/security.txt` — the standards-based location within the project site.
- `https://healthrenewal.org/security.txt` — an additional compatibility location.

Because the platform is a project site under `/`, the file is not available at the origin root `https://healthrenewal.org/.well-known/security.txt`. Origin-root discovery requires a custom domain or publication from the GitHub Pages account root.

## Include only in the private report

- A concise title and impact description.
- The affected path, component, version, or commit SHA when known.
- Safe and minimal reproduction steps.
- Relevant browser, operating system, and environment details.
- Evidence redacted of personal data and secrets.
- A mitigation or fix suggestion when available.

## Safe-testing boundaries

Do not access or modify data that is not yours, perform social engineering, phishing, denial of service, resource-intensive testing, persistence, malware uploads, or disclosure of secrets, health data, or personal information. Stop immediately if sensitive data appears and retain only the minimum redacted evidence needed for the report.

## Handling and disclosure

Reports will be triaged, validated, scoped, and remediated before public disclosure. No bounty or payment is offered unless explicitly announced. This policy does not authorize unlawful or harmful testing.
