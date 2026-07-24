"use strict";

(() => {
  const RELEASE = "2026.07.24-live.7";
  const data = window.PA_DEMO_DATA;
  if (!data || !Array.isArray(data.professional)) return;

  const normalize = (item, index) => {
    const isExternal = item.status === "external"
      || String(item.activationStatus || "").startsWith("external")
      || String(item.inputMode || "").includes("external");
    item.id ||= `professional-${index + 1}`;
    item.status = isExternal ? "external" : "locked";
    item.operational = true;
    item.release = RELEASE;
    item.activationStatus = isExternal ? "external_result_workflow" : "locked_pending_rights";
    item.rightsStatus = isExternal ? "locked_or_link_only" : "locked_pending_rights";
    item.access = isExternal
      ? "تسجيل نتيجة خارجية أو رابط رسمي فقط؛ لا تُعرض البنود أو مفاتيح التصحيح أو المعايير"
      : "مقفل حتى اكتمال الترخيص وحق الرقمنة والتحقق من النسخة واللغة والمؤهل";
    item.note = isExternal
      ? "يُسجل تقرير الجهة المختصة أو نتيجتها داخل سجل الحالة مع التاريخ والمنفذ والملاحظات دون نسخ المواد المحمية."
      : "لا يُفتح التطبيق المهني قبل موافقة حقوقية وعلمية وأمنية ومؤسسية موثقة.";
    item.conditions ||= ["بحسب سؤال الإحالة والتقييم المهني"];
    item.recommendedRoles ||= ["مختص مؤهل", "فريق متعدد التخصصات عند الحاجة"];
    item.inputMode ||= isExternal ? "external_result" : "authorized_or_platform_workflow";
    return item;
  };

  data.professional = data.professional.map(normalize);
  window.PA_OPERATIONAL_RELEASE = RELEASE;
  window.PA_OPERATIONAL_COUNT = data.professional.length;

  if (typeof document === "undefined") return;

  const applyTabSemantics = () => {
    const tablist = document.querySelector(".tabs");
    if (!tablist) return;
    tablist.setAttribute("role", "tablist");
    document.querySelectorAll(".tab[data-view]").forEach((tab, index) => {
      const view = tab.dataset.view || String(index);
      const escapedView = typeof CSS !== "undefined" && typeof CSS.escape === "function" ? CSS.escape(view) : view.replace(/[^a-zA-Z0-9_-]/g, "");
      const panel = document.querySelector(`[data-view-panel="${escapedView}"]`);
      const tabId = `workspace-tab-${view}`;
      tab.id = tabId;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", panel?.id || `view-${view}`);
      tab.tabIndex = tab.getAttribute("aria-selected") === "true" ? 0 : -1;
      if (panel) {
        panel.setAttribute("role", "tabpanel");
        panel.setAttribute("aria-labelledby", tabId);
      }
    });
  };

  const bootAccessibility = () => {
    applyTabSemantics();
    const tablist = document.querySelector(".tabs");
    if (tablist) new MutationObserver(applyTabSemantics).observe(tablist, { childList: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootAccessibility, { once: true });
  else bootAccessibility();
})();
