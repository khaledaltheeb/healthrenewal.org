"use strict";

(() => {
  const RELEASE = "2026.07.24-live.7";
  const PATH = "/provider-assessment-demo/";
  const hasNewerInstitutionalContract = () =>
    document.documentElement.dataset.institutionalContract === "2026.07.25-v220" ||
    Boolean(document.querySelector('script[data-institutional-contract-v220]'));

  const replaceText = (root = document) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const replacements = new Map([
      ["خدمة خارجية", "تقرير خارجي فقط"],
      ["منصة روافد", "منصة روافد"],
      ["مقدم خدمة تجريبي", "مقدم خدمة محلي"],
      ["الدخول التجريبي", "مساحة مقدم الخدمة"],
      ["النسخة التجريبية المنشورة", "النسخة المؤسسية المحلية المنشورة"],
      ["منصة التقييم والاستكشاف", "منصة التقييم والسجل المهني"],
    ]);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      let value = node.nodeValue || "";
      for (const [from, to] of replacements) value = value.replaceAll(from, to);
      if (value !== node.nodeValue) node.nodeValue = value;
    }
  };

  const applyInstitutionalCopy = () => {
    if (hasNewerInstitutionalContract()) return;
    document.documentElement.dataset.release = RELEASE;
    document.title = "منصة التقييم والسجل المهني | منصة روافد";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية مؤسسية محلية لإدارة الحالات والجلسات والأدوات الاستكشافية وسجلات الخدمات المهنية، مع 20 دليل حالة وتقارير متعددة الإصدارات. تبقى المقاييس المحمية مقفلة حتى اكتمال الترخيص والمراجعة المؤسسية.";
    const applicationVersion = document.querySelector('meta[name="application-version"]');
    if (applicationVersion) applicationVersion.content = RELEASE;

    const brand = document.querySelector(".brand");
    if (brand) brand.textContent = "منصة روافد";
    const product = document.querySelector(".product-name");
    if (product) product.textContent = "منصة التقييم والسجل المهني";
    const notice = document.querySelector(".notice-bar");
    if (notice) notice.textContent = "الأدوات الاستكشافية الأصلية متاحة للاستخدام غير التشخيصي. المقاييس المهنية المحمية تبقى مقفلة حتى اكتمال الترخيص وحق الرقمنة والمراجعة العلمية والأمنية والمؤسسية.";

    const count = window.PA_OPERATIONAL_COUNT || window.PA_DEMO_DATA?.professional?.length || 0;
    const card = document.querySelector(".hero-card ul");
    if (card) {
      card.innerHTML = `
        <li>UID مستقل لكل مستخدم أو مقدم خدمة.</li>
        <li>سجل حالات وجلسات ونتائج متكررة محفوظ محليًا.</li>
        <li>20 أداة استكشافية أصلية تعمل مباشرة مع متابعة وصفية مشروطة بقابلية المقارنة.</li>
        <li>${count} مقياسًا وفحصًا في دليل الوصول المهني مع حالة حقوق واضحة.</li>
        <li>20 دليل حالة مؤسسيًا مع فريق وحزمة مقاييس وكورس ومخرجات تقرير.</li>
        <li>سجل خدمات ونتائج خارجية دون نسخ بنود أو مفاتيح تصحيح محمية.</li>
        <li>تقارير مهنية متعددة الإصدارات مع عقد تفسير وخط أساس وهدف وسجل مراجعة.</li>
        <li>الإصدار الحي: ${RELEASE}.</li>`;
    }

    const professionalTitle = document.querySelector("#view-professional h2");
    if (professionalTitle) professionalTitle.textContent = "المقاييس والفحوص والبروتوكولات المهنية وحالة التفعيل الحقوقي";
    const professionalCallout = document.querySelector("#view-professional .callout");
    if (professionalCallout) {
      professionalCallout.className = "callout warning";
      professionalCallout.textContent = "تظهر المقاييس المهنية كدليل وصول مصنف. يمكن توثيق الخدمة أو التقرير الخارجي، لكن لا يُفتح تطبيق أداة محمية قبل توثيق الترخيص وحق الرقمنة والمؤهل والنسخة اللغوية والمراجعة المؤسسية.";
    }

    const footer = document.querySelector(".site-footer p");
    if (footer) footer.textContent = `© منصة روافد — منصة التقييم والسجل المهني، الإصدار ${RELEASE}. التخزين محلي داخل UID مستقل؛ لا تشخيص آلي ولا نسخ لأدوات محمية.`;
    replaceText(document.body);
  };

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

  function setRole(element, value) {
    if (element.getAttribute("role") !== value) element.setAttribute("role", value);
  }

  const observeOperationalUi = () => {
    const target = document.getElementById("professional-list") || document.body;
    const observer = new MutationObserver(() => {
      replaceText(target);
      applyTabSemantics();
    });
    observer.observe(target, { childList: true, subtree: true, characterData: true });
  };

  const addScript = (src, datasetName, onload) => {
    if (document.querySelector(`script[data-${datasetName}]`)) {
      if (onload) onload();
      return;
    }
    const script = document.createElement("script");
    script.src = `${src}?release=${encodeURIComponent(RELEASE)}`;
    script.defer = true;
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
    requestAnimationFrame(() => requestAnimationFrame(() => {
      applyInstitutionalCopy();
      applyTabSemantics();
    }));
  });

  if (location.pathname === PATH && !location.search.includes("release=")) {
    const url = new URL(location.href);
    url.searchParams.set("release", RELEASE);
    history.replaceState(null, "", url);
  }
})();
