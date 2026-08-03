"use strict";

(() => {
  const release = "2026.07.25-v220";
  const compatibilityRelease = "2026.07.25-v231";
  let integrationPromise = null;
  let fallbackTimer = 0;

  const applyReleaseCopy = () => {
    document.documentElement.dataset.release = release;
    document.documentElement.dataset.institutionalContract = release;
    document.documentElement.dataset.compatibilityRelease = compatibilityRelease;
    document.documentElement.dataset.professionalDraftFallback = compatibilityRelease;
    document.documentElement.dataset.professionalTemplateDraft = compatibilityRelease;
    document.title = "عقد التقييم والسجل المهني v220 | منصة روافد";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية مؤسسية لإدارة الحالات والجلسات والأدوات الاستكشافية والسجل المهني ضمن عقد v220 يضبط الغرض والمصادر والبيئات والصلاحية والحقوق والمراجعة وخطط المتابعة، دون تشخيص آلي أو فتح مواد محمية.";
    const productName = document.querySelector(".product-name");
    if (productName) productName.textContent = "عقد التقييم والسجل المهني v220";
    const heroEyebrow = document.querySelector(".hero .eyebrow");
    if (heroEyebrow) heroEyebrow.textContent = "منصة مؤسسية محلية لإدارة الحالات ومسارات التقييم";
    const heroTitle = document.getElementById("hero-title");
    if (heroTitle) heroTitle.textContent = "أنشئ حالة، ابنِ مخطط تقييم متعدد المصادر، ونفّذ الاستكشاف والسجل المهني في مسار واحد قابل للتتبع.";
    const heroLead = document.querySelector(".hero .lead");
    if (heroLead) heroLead.textContent = "إدارة حالات وجلسات متكررة، أدوات استكشافية أصلية، سجل زمني، مخططات تقييم متعددة المصادر والبيئات، وتوثيق مهني يفرض الغرض وصلاحية النتيجة والتكييفات والحدود والمراجعة. تحفظ البيانات محليًا داخل المتصفح بواسطة UID مستقل.";
    const heroCardTitle = document.querySelector(".hero-card > strong");
    if (heroCardTitle) heroCardTitle.textContent = "العقد المؤسسي المنشور v220";
  };

  const loadIntegration = () => {
    if (fallbackTimer) {
      clearTimeout(fallbackTimer);
      fallbackTimer = 0;
    }
    if (integrationPromise) return integrationPromise;
    integrationPromise = import("./institutional-contract-v220-integration.js")
      .then(() => import("./institutional-contract-v231-compat.js"))
      .then(() => import("./institutional-contract-v231-save-fallback.js"))
      .then((module) => {
        applyReleaseCopy();
        return module;
      })
      .catch((error) => {
        integrationPromise = null;
        console.error("تعذر تحميل عقد التقييم المؤسسي v220 أو طبقات التوافق والحفظ v231", error);
        throw error;
      });
    return integrationPromise;
  };

  const loadOnInteraction = () => {
    void loadIntegration();
  };

  applyReleaseCopy();
  for (const eventName of ["pointerdown", "keydown", "focusin"]) {
    document.addEventListener(eventName, loadOnInteraction, { once: true, capture: true, passive: eventName === "pointerdown" });
  }
  window.addEventListener("load", () => {
    fallbackTimer = window.setTimeout(() => void loadIntegration(), 8000);
  }, { once: true });

  window.PA_LOAD_INSTITUTIONAL_V220 = loadIntegration;
})();