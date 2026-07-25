"use strict";

(() => {
  const RELEASE = "2026.07.24-live.7";
  const PATH = "/pterminology-site/provider-assessment-demo/";
  const replacements = new Map([
    ["خدمة خارجية", "تقرير خارجي فقط"],
    ["مصطلحات علم النفس", "منصة الصحة النفسية وذوي الاحتياجات الخاصة"],
    ["مقدم خدمة تجريبي", "مقدم خدمة محلي"],
    ["الدخول التجريبي", "مساحة مقدم الخدمة"],
    ["النسخة التجريبية المنشورة", "النسخة المؤسسية المحلية المنشورة"],
    ["منصة التقييم والاستكشاف", "منصة التقييم والسجل المهني"],
  ]);

  const replaceText = (root) => {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      let value = root.nodeValue || "";
      for (const [from, to] of replacements) value = value.replaceAll(from, to);
      if (value !== root.nodeValue) root.nodeValue = value;
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      let value = node.nodeValue || "";
      for (const [from, to] of replacements) value = value.replaceAll(from, to);
      if (value !== node.nodeValue) node.nodeValue = value;
    }
  };

  const applyInstitutionalCopy = () => {
    document.documentElement.dataset.release = RELEASE;
    document.title = "منصة التقييم والسجل المهني | منصة الصحة النفسية وذوي الاحتياجات الخاصة";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية مؤسسية محلية لإدارة الحالات والجلسات والأدوات الاستكشافية وسجلات الخدمات المهنية، مع 20 دليل حالة وتقارير متعددة الإصدارات. تبقى المقاييس المحمية مقفلة حتى اكتمال الترخيص والمراجعة المؤسسية.";
    const applicationVersion = document.querySelector('meta[name="application-version"]');
    if (applicationVersion) applicationVersion.content = RELEASE;

    const brand = document.querySelector(".brand");
    if (brand) brand.textContent = "منصة الصحة النفسية وذوي الاحتياجات الخاصة";
    const product = document.querySelector(".product-name");
    if (product) product.textContent = "منصة التقييم والسجل المهني";
    const notice = document.querySelector(".notice-bar");
    if (notice) notice.textContent = "الأدوات الاستكشافية الأصلية متاحة للاستخدام غير التشخيصي. المقاييس المهنية المحمية تبقى مقفلة حتى اكتمال الترخيص وحق الرقمنة والمراجعة العلمية والأمنية والمؤسسية.";

    const professionalTitle = document.querySelector("#view-professional h2");
    if (professionalTitle) professionalTitle.textContent = "المقاييس والفحوص والبروتوكولات المهنية وحالة التفعيل الحقوقي";
    const professionalCallout = document.querySelector("#view-professional .callout");
    if (professionalCallout) {
      professionalCallout.className = "callout warning";
      professionalCallout.textContent = "تظهر المقاييس المهنية كدليل وصول مصنف. يمكن توثيق الخدمة أو التقرير الخارجي، لكن لا يُفتح تطبيق أداة محمية قبل توثيق الترخيص وحق الرقمنة والمؤهل والنسخة اللغوية والمراجعة المؤسسية.";
    }

    const footer = document.querySelector(".site-footer p");
    if (footer) footer.textContent = `© منصة الصحة النفسية وذوي الاحتياجات الخاصة — منصة التقييم والسجل المهني، الإصدار ${RELEASE}. التخزين محلي داخل UID مستقل؛ لا تشخيص آلي ولا نسخ لأدوات محمية.`;
  };

  function setRole(element, value) {
    if (element.getAttribute("role") !== value) element.setAttribute("role", value);
  }

  const applyTabSemantics = () => {
    const tablist = document.querySelector(".tabs");
    if (tablist) setRole(tablist, "tablist");
    document.querySelectorAll(".tab[data-view]").forEach((tab) => {
      const viewName = tab.dataset.view;
      const panel = document.querySelector(`[data-view-panel="${viewName}"]`);
      const tabId = tab.id || `workspace-tab-${viewName}`;
      tab.id = tabId;
      setRole(tab, "tab");
      if (!panel) return;
      panel.id ||= `view-${viewName}`;
      setRole(panel, "tabpanel");
      tab.setAttribute("aria-controls", panel.id);
      panel.setAttribute("aria-labelledby", tabId);
      panel.setAttribute("tabindex", "0");
    });
  };

  const observeOperationalUi = () => {
    let semanticsFrame = 0;
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) replaceText(node);
      }
      if (!semanticsFrame) {
        semanticsFrame = requestAnimationFrame(() => {
          semanticsFrame = 0;
          applyTabSemantics();
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  };

  const addScript = (src, datasetName, onload) => {
    if (document.querySelector(`script[data-${datasetName}]`)) {
      if (onload) onload();
      return;
    }
    const script = document.createElement("script");
    script.src = `${src}?release=${encodeURIComponent(RELEASE)}`;
    script.dataset[datasetName.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = RELEASE;
    if (onload) script.addEventListener("load", onload, { once: true });
    document.head.appendChild(script);
  };

  const loadAssessmentPathways = () => addScript("assessment-pathways-content.js", "assessment-pathways");
  const loadConditionPathways = () => addScript("conditions/conditions-data-v1.js", "condition-pathways", () => addScript("condition-entry-v1.js", "condition-entry"));
  const loadProfessionalTemplates = () => addScript("professional-templates-v1.js", "professional-templates");
  const loadOriginalProgress = () => addScript("original-tools-session-context-v2.js", "original-session-context-v2", () => addScript("original-tools-progress-v1.js", "original-tools-progress-v1", () => addScript("original-tools-progress-plan-bridge-v3.js", "original-progress-plan-bridge-v3", () => addScript("original-tools-progress-plan-v3.js", "original-progress-plan-v3"))));
  const loadCaseReports = () => addScript("case-report-v1.js", "case-reports", () =>
    addScript("case-report-interpretation-v2.js", "case-report-interpretation-v2", () =>
      addScript("case-report-export-v2.js", "case-report-export-v2")));

  const refreshOldCaches = async () => {
    try {
      const key = "pa-live-release";
      const previous = localStorage.getItem(key);
      if (previous !== RELEASE && "caches" in window) {
        const names = await caches.keys();
        await Promise.all(names.filter((name) => /pterminology|provider-assessment|pa-demo/i.test(name)).map((name) => caches.delete(name)));
      }
      localStorage.setItem(key, RELEASE);
      if ("serviceWorker" in navigator) {
        await navigator.serviceWorker.register(`sw-live-v2.js?release=${encodeURIComponent(RELEASE)}`, { scope: "./", updateViaCache: "none" });
      }
    } catch (error) {
      console.warn("Provider assessment cache refresh skipped", error);
    }
  };

  window.addEventListener("DOMContentLoaded", () => {
    applyInstitutionalCopy();
    applyTabSemantics();
    observeOperationalUi();
    loadAssessmentPathways();
    loadConditionPathways();
    loadProfessionalTemplates();
    loadOriginalProgress();
    loadCaseReports();
    refreshOldCaches();
  }, { once: true });

  if (location.pathname === PATH && !location.search.includes("release=")) {
    const url = new URL(location.href);
    url.searchParams.set("release", RELEASE);
    history.replaceState(null, "", url);
  }
})();
