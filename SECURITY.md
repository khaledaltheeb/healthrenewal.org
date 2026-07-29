# سياسة الإبلاغ عن الثغرات الأمنية

## الإبلاغ الخاص

لا تنشر تفاصيل ثغرة أمنية أو بيانات شخصية أو صحية أو مفاتيح أو رموز وصول في Issues أو Discussions أو Pull Requests العامة.

استخدم **Private vulnerability reporting** في GitHub من صفحة **Security → Advisories → Report a vulnerability** لهذا المستودع. إذا لم يظهر زر الإبلاغ الخاص، لا تنشر التفاصيل علنًا؛ افتح Issue عامة مقتضبة تطلب قناة تواصل خاصة من دون ذكر نوع الثغرة أو خطوات استغلالها أو أي بيانات حساسة.

## ما يجب تضمينه

- عنوان مختصر ووصف للأثر المحتمل.
- المسار أو المكوّن المتأثر والإصدار أو commit SHA عند معرفته.
- خطوات إعادة إنتاج محدودة وآمنة.
- المتصفح أو نظام التشغيل والبيئة ذات الصلة.
- أدلة منقحة من البيانات الشخصية والأسرار.
- اقتراح تخفيف أو إصلاح إن توفر.

## حدود الاختبار الآمن

- لا تصل إلى بيانات لا تخصك، ولا تغيّر بيانات أو صلاحيات أو محتوى منشورًا.
- لا تستخدم الهندسة الاجتماعية أو التصيد أو حجب الخدمة أو الاختبارات التي تستهلك موارد كبيرة.
- لا ترفع ملفات خبيثة ولا تنفذ وصولًا مستمرًا ولا تنشر أسرارًا أو بيانات صحية أو شخصية.
- أوقف الاختبار فور ظهور بيانات حساسة، واحتفظ بأقل قدر لازم من الأدلة المنقحة ثم احذفها بأمان.

## المعالجة والإفصاح

سيجري فرز البلاغ والتحقق منه وتحديد نطاق الإصلاح قبل أي إفصاح عام. لا يوجد برنامج مكافآت أو تعهد دفع ما لم يُعلن ذلك صراحةً في المستقبل. لا تمثل هذه السياسة تفويضًا لاختبار غير قانوني أو ضار.

---

# Security vulnerability reporting policy

## Private reporting

Do not publish vulnerability details, personal or health data, credentials, tokens, or exploit steps in public Issues, Discussions, or Pull Requests.

Use GitHub **Private vulnerability reporting** through **Security → Advisories → Report a vulnerability** for this repository. If that button is unavailable, do not disclose technical details publicly; open a minimal public issue requesting a private contact channel without naming the vulnerability class or including reproduction steps.

## Include

- A concise title and impact description.
- The affected path, component, version, or commit SHA when known.
- Safe and minimal reproduction steps.
- Relevant browser, operating system, and environment details.
- Evidence redacted of personal data and secrets.
- A mitigation or fix suggestion when available.

## Safe-testing boundaries

Do not access or modify data that is not yours, perform social engineering, phishing, denial of service, resource-intensive testing, persistence, malware uploads, or disclosure of secrets, health data, or personal information. Stop immediately if sensitive data appears and retain only the minimum redacted evidence needed for the report.

## Handling and disclosure

Reports will be triaged, validated, scoped, and remediated before public disclosure. No bounty or payment is offered unless explicitly announced in the future. This policy does not authorize unlawful or harmful testing.
