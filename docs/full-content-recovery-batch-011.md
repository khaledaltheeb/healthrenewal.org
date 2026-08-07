# استعادة المحتوى — الدفعة 011

تاريخ التدقيق: 2026-08-07

## خط الأساس والحالة

- PR: #1094.
- الفرع: `agent/full-content-recovery-v4`.
- رأس الفرع قبل هذه الدفعة: `9ae5350804ccf91ca1d714ae8bfdb05b219230c0`.
- أحدث `main` عند الفحص: `93747007bbdd16d64a0fac1fa2c4d94c1a1c5fc2` بعد دمج PR #1109.
- المقارنة: الفرع متباعد عن `main`؛ merge-base هو `abbb018b205a40d2d6388eda934a342bebe839a6`، والفرع كان ahead 7 / behind 10 عند بدء الدفعة.

## فحص التداخل مع أحدث main

منذ merge-base غيّر `main` أربعة مسارات فقط:

- `.github/workflows/validate-daily-tools-v24.yml`
- `scripts/publish_special_needs_cdls_v337.py`
- `scripts/recover_content_full_history_v3.py`
- `tests/test_recovery_private_surface_guard_v1.py`

المسار المتداخل الوحيد مع PR #1094 هو `scripts/recover_content_full_history_v3.py`.

المقارنة النصية أثبتت أن نسخة فرع الاستعادة لا تسقط حارس `main`: فهي تحتفظ بالحظر الحالي لكل من:

- `professional-assessment-hub/`
- `provider-assessment-platform/`
- `specialists-partners/admin/`
- `specialists-partners/portal/`

وتضيف فوقه حارس عدم الاختصار `restore_without_shortening()`؛ لذلك اتجاه الدمج الصحيح هو الاحتفاظ بحراس `main` مع حارس no-shortening، لا استبدال أحدهما بالآخر.

## عقد اختبار جديد

أضيف:

`tests/test_recovery_no_shortening_guard_v1.py`

ويغطي ثلاث حالات مستقلة:

1. **منع الاختصار:** محاكاة حالة `guided-assessment/index.html`، حيث يحاول محرك تاريخي استبدال 1308 كلمة بـ714 كلمة؛ يجب إعادة النسخة الحالية حرفيًا وعدم قبول الاستعادة المختصرة.
2. **السماح بالنسخة الأغنى:** إذا كانت النسخة التاريخية مساوية أو أطول، تبقى مؤهلة ولا يتدخل الحارس.
3. **استعادة الصفحة المفقودة:** المسار غير الموجود أصلًا يظل قابلًا للاستعادة؛ حارس no-shortening لا يمنع استعادة الصفحات المفقودة.

هذا الاختبار يحول سياسة «لا تحذف ولا تختصر» من قرار توثيقي إلى عقد انحدار قابل للتنفيذ.

## الطلبات المفتوحة المحجوزة

فُحصت الطلبات المفتوحة المحدثة. لم تُمس ملفات:

- #1092: المختبر والمقاييس v32.
- #1095: `learning-paths/caregiver-foundations/**`.
- #1107: عقد مصادر المناصرة الذاتية.
- #1108: Workflow تاريخي لـIssue #20.
- #1110: تدقيق التقييم المهني.
- #1111: إعادة توليد أسطح إصدار المجلة بعد recovery.

## قرار الدمج

لا دمج في هذه الدفعة. الفرع ما يزال يحتاج إعادة تأسيس/مزامنة فوق أحدث `main` ثم تشغيل الاختبارات على الرأس النهائي. نجاح اختبار no-shortening وحده غير كافٍ؛ يلزم كذلك نجاح HTML والروابط وRTL والهاتف والطباعة وSchema وWCAG وArtifact الإنتاج وPages/live SHA حسب عقد Issue #158.
