"use strict";

(() => {
  const RELEASE = "2026.07.25-v231";
  const SCHEMA = "institutional-assessment-contract-v220";
  const TEMPLATE_NOTE_ID = "institutional-v231-template-draft-note";
  const clean = (value) => String(value || "").trim();
  const progress = () => window.PA_ORIGINAL_PROGRESS;
  const activeIdentity = () => progress()?.activeIdentity?.() || null;
  const activeStore = () => progress()?.activeStore?.() || null;
  const persistStore = (store) => progress()?.persistStore?.(store);
  const api = { release: RELEASE, lastAttempt: null };
  const makeId = () => {
    const uuid = globalThis.crypto?.randomUUID?.();
    const token = uuid ? uuid.replaceAll("-", "").slice(0, 16) : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 9)}`;
    return `PRO-${token.toUpperCase()}`;
  };

  const contractFrom = (fd) => ({
    referralPurpose: clean(fd.get("referralPurpose")),
    decisionUse: String(fd.get("decisionUseV220") || ""),
    validityStatus: String(fd.get("validityStatus") || ""),
    completionStatus: String(fd.get("completionStatus") || ""),
    normativeFit: String(fd.get("normativeFit") || ""),
    crossSourceAgreement: String(fd.get("crossSourceAgreement") || ""),
    consentStatus: String(fd.get("consentV220") || ""),
    riskReview: String(fd.get("riskReview") || ""),
    reviewer: clean(fd.get("reviewerV220")),
    reviewDate: String(fd.get("reviewDateV220") || ""),
    sourcesSettings: clean(fd.get("sourcesSettings")),
    accommodationsDeviations: clean(fd.get("accommodationsDeviations")),
    functionalSynthesis: clean(fd.get("functionalSynthesis")),
    recommendations: clean(fd.get("recommendationsV220")),
    limitations: clean(fd.get("limitationsV220")),
  });

  const baseRecordFrom = (fd) => ({
    caseId: String(fd.get("caseId") || ""),
    toolId: String(fd.get("toolId") || "custom-professional-record"),
    toolName: String(fd.get("toolName") || "تطبيق مهني مخصص"),
    category: String(fd.get("category") || "مسار مهني"),
    recordStatus: String(fd.get("recordStatus") || "planned"),
    administrationDate: String(fd.get("administrationDate") || ""),
    assignedEntityLabel: clean(fd.get("assignedEntityLabel")),
    performerName: clean(fd.get("performerName")),
    administrationMode: String(fd.get("administrationMode") || ""),
    versionLanguage: clean(fd.get("versionLanguage")),
    outcomeLabel: clean(fd.get("outcomeLabel")),
    scoreReference: clean(fd.get("scoreReference")),
    notes: clean(fd.get("notes")),
    nextAction: String(fd.get("nextAction") || "review"),
    rightsConfirmed: fd.get("rightsConfirmed") === "on",
  });

  const baseRecordIsValid = (record) => Boolean(
    record.caseId && record.administrationDate && record.assignedEntityLabel &&
    record.administrationMode && record.outcomeLabel && record.nextAction && record.rightsConfirmed
  );
  api.baseRecordIsValid = baseRecordIsValid;

  const prepareTemplateDraftFields = () => {
    const container = document.getElementById("professional-template-fields");
    if (!container) return false;
    let note = document.getElementById(TEMPLATE_NOTE_ID);
    if (!note) {
      note = document.createElement("p");
      note.id = TEMPLATE_NOTE_ID;
      note.className = "professional-form-note";
      note.textContent = "تفاصيل القالب المهني موسعة واختيارية في المسودة. يُوثق النقص ضمن درجة الجودة، ولا يمنع حفظ سجل التخطيط الأولي.";
      const heading = container.querySelector(".template-heading");
      if (heading) heading.after(note); else container.prepend(note);
    }
    container.querySelectorAll('[name^="detail_"][required]').forEach((control) => {
      control.required = false;
      control.setAttribute("aria-describedby", TEMPLATE_NOTE_ID);
    });
    container.querySelectorAll('select[name^="detail_"]').forEach((select) => {
      const blank = [...select.options].find((option) => option.value === "");
      if (blank && blank.textContent !== "غير موثق بعد") blank.textContent = "غير موثق بعد";
    });
    if (container.dataset.compatV231Draft !== "true") container.dataset.compatV231Draft = "true";
    return true;
  };
  api.prepareTemplateDraftFields = prepareTemplateDraftFields;

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-professional-tool],#professional-record-new")) return;
    queueMicrotask(prepareTemplateDraftFields);
    setTimeout(prepareTemplateDraftFields, 0);
  }, true);
  new MutationObserver(prepareTemplateDraftFields).observe(document.documentElement, { childList: true, subtree: true });
  prepareTemplateDraftFields();

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("#professional-record-form");
    if (!form) return;
    const beforeStore = activeStore();
    if (!beforeStore) {
      api.lastAttempt = { status: "missing_store_at_submit" };
      return;
    }
    const beforeIds = new Set((beforeStore.cases || []).flatMap((item) => (item.professionalAssessments || []).map((record) => record.recordId)));
    const fd = new FormData(form);
    const baseRecord = baseRecordFrom(fd);
    const contractDraft = contractFrom(fd);
    api.lastAttempt = { status: "scheduled", baseRecord: { ...baseRecord } };

    setTimeout(() => {
      try {
        const store = activeStore();
        const identity = activeIdentity();
        if (!store || !identity?.uid) {
          api.lastAttempt = { status: "missing_active_context", hasStore: Boolean(store), hasIdentity: Boolean(identity?.uid), baseRecord: { ...baseRecord } };
          return;
        }
        const alreadyCreated = (store.cases || []).flatMap((item) => item.professionalAssessments || []).some((record) => !beforeIds.has(record.recordId));
        if (alreadyCreated) {
          api.lastAttempt = { status: "original_save_succeeded" };
          return;
        }
        if (!baseRecordIsValid(baseRecord)) {
          api.lastAttempt = { status: "invalid_base_record", baseRecord: { ...baseRecord } };
          return;
        }
        const caseRecord = store.cases?.find((item) => item.caseId === baseRecord.caseId);
        if (!caseRecord) {
          api.lastAttempt = { status: "missing_case", caseId: baseRecord.caseId };
          return;
        }

        const at = new Date().toISOString();
        const contract = { ...contractDraft, schema: SCHEMA, release: RELEASE, capturedAt: at, documentationState: "progressive_draft_allowed" };
        const audit = window.PA_INSTITUTIONAL_COMPAT_V231?.auditProfessional?.(contract) || { score: 0, passed: 0, total: 10, gates: [], status: "incomplete" };
        const record = {
          recordId: makeId(),
          toolId: baseRecord.toolId,
          toolName: baseRecord.toolName,
          category: baseRecord.category,
          recordStatus: baseRecord.recordStatus,
          administrationDate: baseRecord.administrationDate,
          assignedEntityLabel: baseRecord.assignedEntityLabel,
          performerName: baseRecord.performerName,
          administrationMode: baseRecord.administrationMode,
          versionLanguage: baseRecord.versionLanguage,
          outcomeLabel: baseRecord.outcomeLabel,
          scoreReference: baseRecord.scoreReference,
          notes: baseRecord.notes,
          nextAction: baseRecord.nextAction,
          rightsConfirmed: true,
          recordedAt: at,
          recordedByUid: identity.uid,
          recordedByRole: identity.role || "visitor",
          activationVersion: "1.0.0-v231-fallback",
          institutionalV220: contract,
          documentationQuality: audit,
          auditTrail: [{ event: "institutional_contract_attached", at, byUid: identity.uid, qualityScore: audit.score, release: RELEASE, source: "v231_save_fallback" }],
        };

        caseRecord.professionalAssessments ||= [];
        caseRecord.professionalAssessments.push(record);
        caseRecord.updatedAt = at;
        persistStore(store);
        api.lastAttempt = { status: "fallback_saved", caseId: caseRecord.caseId, recordId: record.recordId, qualityScore: audit.score };

        try {
          if (typeof window.render === "function") window.render();
        } catch (renderError) {
          api.lastAttempt.renderError = String(renderError?.stack || renderError);
          console.error("تعذر تحديث واجهة السجل بعد حفظ مسودة v231", renderError);
        } finally {
          const dialog = document.getElementById("professional-record-dialog");
          if (dialog?.open && typeof dialog.close === "function") dialog.close();
          window.PA_V220_HOOKS?.decorateProfessionalRecords?.();
          window.dispatchEvent(new CustomEvent("pa-professional-record-v231-fallback-saved", { detail: { caseId: caseRecord.caseId, recordId: record.recordId } }));
        }
      } catch (error) {
        api.lastAttempt = { status: "fallback_error", error: String(error?.stack || error), baseRecord: { ...baseRecord } };
        console.error("تعذر حفظ مسودة السجل المهني عبر fallback v231", error);
      }
    }, 0);
  }, true);

  window.PA_V231_SAVE_FALLBACK = api;
})();