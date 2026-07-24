"use strict";

(() => {
  const RELEASE = "2026.07.24-runtime-a11y.3";
  const data = window.PA_DEMO_DATA;

  if (Array.isArray(data?.professional)) {
    data.professional.forEach((item, index) => {
      item.id ||= `professional-${index + 1}`;
      const external = item.status === "external"
        || String(item.activationStatus || "").startsWith("external")
        || String(item.inputMode || "").includes("external");
      item.status = external ? "external" : "locked";
      item.activationStatus = external ? "external_result_workflow" : "locked_pending_rights";
      item.rightsStatus = external ? "locked_or_link_only" : "locked_pending_rights";
      item.access = external
        ? "تسجيل نتيجة خارجية أو رابط رسمي فقط؛ لا تُعرض البنود أو مفاتيح التصحيح أو المعايير"
        : "مقفل حتى اكتمال الترخيص وحق الرقمنة والتحقق من النسخة واللغة والمؤهل";
    });
  }

  const applyTabSemantics = () => {
    const tablist = document.querySelector(".tabs");
    if (!tablist) return;
    tablist.setAttribute("role", "tablist");

    document.querySelectorAll(".tab[data-view]").forEach((tab, index) => {
      const view = tab.dataset.view || String(index);
      const panel = document.querySelector(`[data-view-panel="${CSS.escape(view)}"]`);
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

  const boot = () => {
    applyTabSemantics();
    const tablist = document.querySelector(".tabs");
    if (tablist) new MutationObserver(applyTabSemantics).observe(tablist, { childList: true });
    document.documentElement.dataset.runtimeAccessibility = RELEASE;
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
