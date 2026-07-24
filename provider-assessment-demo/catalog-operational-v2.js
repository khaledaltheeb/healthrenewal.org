"use strict";

(() => {
  const RELEASE = "2026.07.24-live.2";
  const data = window.PA_DEMO_DATA;
  if (!data || !Array.isArray(data.professional)) return;

  const normalize = (item, index) => {
    const isExternal = item.status === "external" || String(item.activationStatus || "").startsWith("external");
    item.id ||= `professional-${index + 1}`;
    item.status = isExternal ? "external" : "workflow";
    item.operational = true;
    item.release = RELEASE;
    item.activationStatus = isExternal ? "external_result_workflow" : "workflow_available";
    item.access = isExternal
      ? "مسار متاح لتسجيل الفحص الخارجي أو استيراد النتيجة وربطها بالحالة"
      : "مسار عمل متاح للتخطيط والتعيين والتطبيق المصرح وتسجيل النتيجة والخطوة التالية";
    item.note = isExternal
      ? "يُسجل تقرير الجهة المختصة أو نتيجتها داخل سجل الحالة مع التاريخ والمنفذ والملاحظات."
      : "يعمل مسار الإدارة والتوثيق كاملًا. عند استخدام مواد ناشر تجاري تُستخدم النسخة الأصلية المصرح بها بواسطة مختص مؤهل.";
    item.conditions ||= ["بحسب سؤال الإحالة والتقييم المهني"];
    item.recommendedRoles ||= ["مختص مؤهل", "فريق متعدد التخصصات عند الحاجة"];
    item.inputMode ||= isExternal ? "external_result" : "authorized_or_platform_workflow";
    return item;
  };

  data.professional = data.professional.map(normalize);
  window.PA_OPERATIONAL_RELEASE = RELEASE;
  window.PA_OPERATIONAL_COUNT = data.professional.length;
})();
