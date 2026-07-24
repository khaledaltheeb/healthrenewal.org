"use strict";

(() => {
  const RELEASE = "2026.07.24-live.7";
  const PATH = "/pterminology-site/provider-assessment-demo/";

  const replaceText = (root = document) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const replacements = new Map([
      ["مقفل", "مسار عمل متاح"],
      ["دليل فقط", "مسار عمل متاح"],
      ["خدمة خارجية", "مسار نتيجة متاح"],
      ["مصطلحات علم النفس", "منصة الصحة النفسية وذوي الاحتياجات الخاصة"],
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
    document.documentElement.dataset.release = RELEASE;
    document.title = "منصة التقييم والسجل المهني | منصة الصحة النفسية وذوي الاحتياجات الخاصة";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية مؤسسية محلية لإدارة الحالات والجلسات والأدوات الاستكشافية ومسارات تطبيق المقاييس المهنية، مع 20 دليل حالة وتقارير متعددة الإصدارات تتضمن نوع التقييم وصلاحية النتيجة وخط الأساس والهدف والملخص الأسري داخل UID مستقل.";
    const applicationVersion = document.querySelector('meta[name="application-version"]');
    if (applicationVersion) applicationVersion.content = RELEASE;

    const brand = document.querySelector(".brand");
    if (brand) brand.textContent = "منصة الصحة النفسية وذوي الاحتياجات الخاصة";
    const product = document.querySelector(".product-name");
    if (product) product.textContent = "منصة التقييم والسجل المهني";
    const notice = document.querySelector(".notice-bar");
    if (notice) notice.textContent = "جميع الأدوات الظاهرة تملك مسار عمل فعّالًا وقالب تطبيق يناسب نوعها، مع تقارير مهنية متعددة الإصدارات وسجل مراجعة. لا تُنسخ مواد تجارية محمية دون حق استخدامها.";

    const count = window.PA_OPERATIONAL_COUNT || window.PA_DEMO_DATA?.professional?.length || 0;
    const card = document.querySelector(".hero-card ul");
    if (card) {
      card.innerHTML = `
        <li>UID مستقل لكل مستخدم أو مقدم خدمة.</li>
        <li>سجل حالات وجلسات ونتائج متكررة محفوظ محليًا.</li>
        <li>20 أداة استكشافية أصلية تعمل مباشرة.</li>
        <li>${count} مقياسًا وفحصًا وبروتوكولًا بمسار عمل مهني فعّال.</li>
        <li>20 دليل حالة مؤسسيًا مع فريق وحزمة مقاييس وكورس ومخرجات تقرير.</li>
        <li>قوالب إدخال متخصصة حسب نوع الأداة والفحص.</li>
        <li>تقارير مهنية متعددة الإصدارات مع عقد تفسير وخط أساس وهدف وسجل مراجعة.</li>
        <li>الإصدار الحي: ${RELEASE}.</li>`;
    }

    const professionalTitle = document.querySelector("#view-professional h2");
    if (professionalTitle) professionalTitle.textContent = "المقاييس والفحوص والبروتوكولات المهنية الفعّالة";
    const professionalCallout = document.querySelector("#view-professional .callout");
    if (professionalCallout) {
      professionalCallout.className = "callout info";
      professionalCallout.textContent = "اختر أي عنصر ثم ابدأ سجلًا مهنيًا مرتبطًا بالحالة. تتغير حقول النموذج تلقائيًا بحسب نوع الأداة، مع توثيق المنفذ والتاريخ والنسخة واللغة والنتيجة والقيود والخطوة التالية.";
    }

    const footer = document.querySelector(".site-footer p");
    if (footer) footer.textContent = `© منصة الصحة النفسية وذوي الاحتياجات الخاصة — منصة التقييم والسجل المهني، الإصدار ${RELEASE}. التخزين محلي داخل UID مستقل.`;
    replaceText(document.body);
  };

  const observeOperationalUi = () => {
    const target = document.getElementById("professional-list") || document.body;
    const observer = new MutationObserver(() => {
      replaceText(target);
      target.querySelectorAll(".badge.danger,.badge.warning").forEach((badge) => {
        if (["مسار عمل متاح", "مسار نتيجة متاح"].includes(badge.textContent.trim())) {
          badge.classList.remove("danger", "warning", "neutral");
          badge.classList.add("success");
        }
      });
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
  const loadCaseReports = () => addScript("case-report-v1.js", "case-reports", () => addScript("case-report-interpretation-v2.js", "case-report-interpretation-v2"));

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
    observeOperationalUi();
    loadAssessmentPathways();
    loadConditionPathways();
    loadProfessionalTemplates();
    loadCaseReports();
    refreshOldCaches();
    requestAnimationFrame(() => requestAnimationFrame(applyInstitutionalCopy));
  });

  if (location.pathname === PATH && !location.search.includes("release=")) {
    const url = new URL(location.href);
    url.searchParams.set("release", RELEASE);
    history.replaceState(null, "", url);
  }
})();