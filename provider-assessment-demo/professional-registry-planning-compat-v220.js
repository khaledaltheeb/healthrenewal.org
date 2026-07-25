"use strict";

(() => {
  const form = document.getElementById("professional-record-form");
  if (!form || !window.PA_PROFESSIONAL_REGISTRY_V220) return;

  const completedStatuses = new Set(["completed", "result_imported"]);
  const contractFields = [
    "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
    "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
    "selectionRationale", "administrationQuality", "interpretationLimitations",
    "integrationSummary", "recommendations", "followUpDate",
  ];
  const input = (name) => form.elements[`maturity_${name}`];
  const currentTool = () => window.PA_DEMO_DATA?.professional?.find((tool) =>
    tool.id === form.elements.toolId.value || tool.name === form.elements.toolName.value
  );
  const maturityInputs = () => [...form.elements].filter((element) => String(element.name || "").startsWith("maturity_"));

  const apply = () => {
    const completed = completedStatuses.has(form.elements.recordStatus.value);
    const tool = currentTool();
    for (const element of maturityInputs()) {
      element.required = false;
      element.closest("label")?.classList.remove("required-field");
    }
    if (completed && tool?.professionalContract) {
      for (const name of contractFields) {
        const element = input(name);
        if (!element) continue;
        element.required = true;
        element.closest("label")?.classList.add("required-field");
      }
      const confirmation = input("noProtectedContent");
      if (confirmation) confirmation.required = true;
    } else {
      const rights = input("rightsBasis");
      if (rights && !rights.value) rights.value = "pending_review";
      const confirmation = input("noProtectedContent");
      if (confirmation) confirmation.required = false;
    }
    const section = document.getElementById("professional-maturity-fields-v220");
    if (section) {
      section.dataset.recordRequirement = completed ? "completed-strict" : "planning-draft";
      const heading = section.querySelector(".template-heading p:last-child");
      if (heading) heading.textContent = completed
        ? "السجل المكتمل يتطلب توثيق الحقوق والنسخة والمؤهل والمصدر والقيود والمتابعة كاملة."
        : "يمكن حفظ التخطيط أو العمل الجاري كمسودة. تصبح الحقول كاملة إلزامية قبل حالة مكتمل أو نتيجة مستلمة.";
    }
  };

  const nativeReportValidity = form.reportValidity.bind(form);
  form.reportValidity = () => {
    const completed = completedStatuses.has(form.elements.recordStatus.value);
    if (completed) return nativeReportValidity();

    const rights = input("rightsBasis");
    if (rights && !rights.value) rights.value = "pending_review";
    for (const element of maturityInputs()) {
      element.required = false;
      element.closest("label")?.classList.remove("required-field");
    }
    const valid = nativeReportValidity();
    queueMicrotask(apply);
    return valid;
  };

  const loadUpgradePath = () => {
    if (document.querySelector('script[data-professional-schema-compat-v220]')) return;
    const schema = document.createElement("script");
    schema.src = "professional-registry-schema-compat-v220.js?release=220.1";
    schema.defer = true;
    schema.dataset.professionalSchemaCompatV220 = "220.1";
    schema.addEventListener("load", () => {
      if (document.querySelector('script[data-professional-edit-v220]')) return;
      const edit = document.createElement("script");
      edit.src = "professional-registry-edit-v220.js?release=220.1";
      edit.defer = true;
      edit.dataset.professionalEditV220 = "220.1";
      edit.addEventListener("error", () => console.error("Failed to load professional record upgrade editor v220"), { once: true });
      document.head.appendChild(edit);
    }, { once: true });
    schema.addEventListener("error", () => console.error("Failed to load professional schema compatibility v220"), { once: true });
    document.head.appendChild(schema);
  };

  const scheduleApply = () => queueMicrotask(() => queueMicrotask(apply));
  form.elements.recordStatus.addEventListener("change", scheduleApply);
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-professional-tool],[data-v220-record-tool],#professional-record-new")) {
      setTimeout(apply, 0);
    }
  }, true);
  new MutationObserver(scheduleApply).observe(form, { childList: true, subtree: true });
  apply();
  loadUpgradePath();

  window.PA_PROFESSIONAL_PLANNING_COMPAT_V220 = Object.freeze({
    version: "220.2",
    completedStatuses: [...completedStatuses],
    planningDraftAllowed: true,
    completedRightsRequired: true,
    baseFormValidationPreserved: true,
    legacyRecordsUpgradable: true,
    schemaMigrationAudited: true,
  });
})();
