"use strict";

(() => {
  const form = document.getElementById("professional-record-form");
  if (!form || !window.PA_PROFESSIONAL_REGISTRY_V220) return;

  const completedStatuses = new Set(["completed", "result_imported"]);
  const input = (name) => form.elements[`maturity_${name}`];

  const apply = () => {
    const completed = completedStatuses.has(form.elements.recordStatus.value);
    const rights = input("rightsBasis");
    if (!completed && rights && !rights.value) rights.value = "pending_review";

    const confirmation = input("noProtectedContent");
    if (confirmation) {
      confirmation.required = true;
      confirmation.closest("label")?.classList.add("required-field");
    }

    const section = document.getElementById("professional-maturity-fields-v220");
    if (section) {
      section.dataset.recordRequirement = completed ? "completed-strict" : "planning-draft";
      const heading = section.querySelector(".template-heading p:last-child");
      if (heading) heading.textContent = completed
        ? "السجل المكتمل يتطلب توثيق الحقوق والنسخة والمؤهل والمصدر والقيود والمتابعة كاملة."
        : "يمكن حفظ التخطيط أو العمل الجاري مع أساس حقوق قيد المراجعة، لكن يبقى منع المواد المحمية وإقرار ذلك إلزاميًا.";
    }
  };

  const loadEditorUpgrade = () => {
    if (document.querySelector('script[data-professional-edit-v220]')) return;
    const script = document.createElement("script");
    script.src = "professional-registry-edit-v220.js?release=220.2";
    script.defer = true;
    script.dataset.professionalEditV220 = "220.2";
    script.addEventListener("error", () => console.error("Failed to load professional record upgrade editor v220"), { once: true });
    document.head.appendChild(script);
  };

  const scheduleApply = () => queueMicrotask(apply);
  form.elements.recordStatus.addEventListener("change", scheduleApply);
  form.elements.administrationMode.addEventListener("change", scheduleApply);
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-v220-record-tool],#professional-record-new")) setTimeout(apply, 0);
  }, true);
  new MutationObserver(scheduleApply).observe(form, { childList: true, subtree: true });
  apply();
  loadEditorUpgrade();

  window.PA_PROFESSIONAL_PLANNING_COMPAT_V220 = Object.freeze({
    version: "220.2",
    completedStatuses: [...completedStatuses],
    planningDraftAllowed: true,
    completedRightsRequired: true,
    protectedContentConfirmationAlwaysRequired: true,
    requirementOwnership: "professional-registry-maturity-ui-v220",
    legacyRecordsUpgradable: true,
  });
})();