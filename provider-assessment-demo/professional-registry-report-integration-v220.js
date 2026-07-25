"use strict";

(() => {
  const VERSION = "220.2";
  const BASE_REPORT_VERSION = "2026.07.24-report.1";
  const COMPLETED = new Set(["completed", "result_imported"]);
  const NON_DRAFT = new Set(["reviewed", "final"]);
  const reportForm = document.getElementById("case-report-form");
  if (!reportForm || typeof store === "undefined" || typeof identity === "undefined") return;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const formObject = (form) => Object.fromEntries(
    [...new FormData(form).entries()].map(([key, value]) => [key, String(value)])
  );
  const caseById = (caseId) => store.cases.find((item) => item.caseId === caseId);

  const maturityValid = (record) => {
    const value = record?.professionalMaturity;
    if (!value || value.schema !== "professional-registry-record-v220") return false;
    if (!value.instrument?.publisher || !value.instrument?.version || !value.instrument?.language) return false;
    if (!value.administrator?.qualification) return false;
    if (!value.rights?.basis || value.rights.basis === "pending_review" || !value.rights?.reference) return false;
    if (!value.officialResultSource?.type || !value.officialResultSource?.reference) return false;
    if (!value.selectionRationale || !value.administrationQuality || !value.interpretationLimitations) return false;
    if (!value.integrationSummary || !value.recommendations || !value.followUpDate) return false;
    const contract = value.contractSnapshot;
    if (!contract || contract.officialAdministrationInsidePlatform !== false) return false;
    if (!Array.isArray(contract.permittedRightsBases) || !contract.permittedRightsBases.includes(value.rights.basis)) return false;
    if (!Array.isArray(contract.permittedScoreSources) || !contract.permittedScoreSources.includes(value.officialResultSource.type)) return false;
    return value.rights.protectedContentStored === false
      && value.rights.itemResponsesStored === false
      && value.rights.scoringKeyStored === false
      && value.rights.normTablesStored === false
      && record.digitalAdministrationOccurredInsidePlatform === false
      && record.protectedContentStored === false;
  };

  const recordsFor = (caseRecord) => caseRecord?.professionalAssessments || [];
  const completedRecords = (caseRecord) => recordsFor(caseRecord).filter((record) => COMPLETED.has(record.recordStatus));
  const incompleteCompletedRecords = (caseRecord) => completedRecords(caseRecord).filter((record) => !maturityValid(record));

  const detailedTable = (records) => `<div class="analytics-table-wrap"><table class="analytics-table professional-maturity-report-table">
    <thead><tr><th>الأداة والحالة</th><th>النسخة والحقوق</th><th>المنفذ والمصدر</th><th>جودة التطبيق والقيود</th><th>التكامل والمتابعة</th></tr></thead>
    <tbody>${records.map((record) => {
      const value = record.professionalMaturity;
      if (!value || value.schema !== "professional-registry-record-v220") {
        return `<tr><td><strong>${esc(record.toolName)}</strong><br>${esc(record.recordStatus)}</td><td colspan="4"><span class="badge warning">سجل قديم غير منظم</span> يجب استكمال عقد الحقوق والنسخة والمصدر قبل اعتماد التقرير.</td></tr>`;
      }
      return `<tr>
        <td><strong>${esc(record.toolName)}</strong><br>${esc(record.recordStatus)} · ${esc(record.administrationDate)}</td>
        <td>${esc(value.instrument?.publisher || "غير مسجل")}<br>${esc(value.instrument?.version || "غير مسجل")} · ${esc(value.instrument?.language || "غير مسجلة")}<br><strong>الحقوق:</strong> ${esc(value.rights?.basis || "غير مسجل")} · ${esc(value.rights?.reference || "غير مسجل")}</td>
        <td>${esc(record.assignedEntityLabel)}${record.performerName ? ` — ${esc(record.performerName)}` : ""}<br>${esc(value.administrator?.qualification || "غير مسجل")}<br><strong>المصدر:</strong> ${esc(value.officialResultSource?.type || "غير مسجل")} · ${esc(value.officialResultSource?.reference || "غير مسجل")}</td>
        <td><strong>الجودة:</strong> ${esc(value.administrationQuality || "غير مسجلة")}<br><strong>القيود:</strong> ${esc(value.interpretationLimitations || "غير مسجلة")}</td>
        <td><strong>التكامل:</strong> ${esc(value.integrationSummary || "غير مسجل")}<br><strong>التوصيات:</strong> ${esc(value.recommendations || "غير مسجلة")}<br><strong>المتابعة:</strong> ${esc(value.followUpDate || "غير محددة")} · ${esc(value.review?.status || "not_reviewed")}</td>
      </tr>`;
    }).join("")}</tbody></table></div>`;

  const reportContractSnapshot = (caseRecord, capturedAt = new Date().toISOString()) => {
    const records = recordsFor(caseRecord);
    const completedList = completedRecords(caseRecord);
    const summaries = records.map((record) => ({
      recordId: record.recordId,
      toolId: record.toolId,
      toolName: record.toolName,
      recordStatus: record.recordStatus,
      administrationDate: record.administrationDate,
      contractVersion: record.professionalContractVersion || null,
      recordType: record.professionalMaturity?.contractSnapshot?.recordType || null,
      rightsBasis: record.professionalMaturity?.rights?.basis || null,
      rightsValid: !COMPLETED.has(record.recordStatus) || maturityValid(record),
      digitalAdministrationOccurredInsidePlatform: record.digitalAdministrationOccurredInsidePlatform === true,
      protectedContentStored: record.protectedContentStored === true,
    }));
    const valid = completedList.filter(maturityValid);
    return {
      schema: "case-report-professional-sources-v220",
      version: VERSION,
      professionalRecordIds: records.map((record) => record.recordId),
      professionalRecordSummaries: summaries,
      totalProfessionalRecords: records.length,
      completedProfessionalRecords: completedList.length,
      structuredProfessionalRecords: records.filter((record) => record.professionalMaturity?.schema === "professional-registry-record-v220").length,
      rightsValidCompletedRecords: valid.length,
      incompleteCompletedRecordIds: completedList.filter((record) => !maturityValid(record)).map((record) => record.recordId),
      digitalAdministrationOccurredInsidePlatform: summaries.some((item) => item.digitalAdministrationOccurredInsidePlatform),
      protectedContentStored: summaries.some((item) => item.protectedContentStored),
      capturedAt,
    };
  };

  const ensureSnapshotField = () => {
    let input = reportForm.elements.professionalSourcesContractJson;
    if (input) return input;
    input = document.createElement("input");
    input.type = "hidden";
    input.name = "professionalSourcesContractJson";
    reportForm.appendChild(input);
    return input;
  };

  const refreshSnapshotField = () => {
    const caseRecord = caseById(reportForm.elements.caseId?.value);
    ensureSnapshotField().value = caseRecord ? JSON.stringify(reportContractSnapshot(caseRecord)) : "";
  };

  const enhancePreview = () => {
    refreshSnapshotField();
    const preview = document.getElementById("case-report-preview");
    if (!preview || preview.querySelector("[data-professional-report-v220]")) return;
    const caseRecord = caseById(reportForm.elements.caseId?.value);
    const records = recordsFor(caseRecord);
    if (!records.length) return;
    const sections = [...preview.querySelectorAll("section")];
    const target = sections.find((section) => section.querySelector("h3")?.textContent.trim() === "التطبيقات المهنية");
    if (!target) return;
    const expanded = document.createElement("section");
    expanded.dataset.professionalReportV220 = VERSION;
    const incomplete = incompleteCompletedRecords(caseRecord);
    expanded.innerHTML = `<h3>تفاصيل التطبيقات المهنية والحقوق</h3>
      <div class="callout ${incomplete.length ? "warning" : "info"}">${incomplete.length
        ? `يوجد ${incomplete.length} تطبيق مكتمل أو نتيجة مستلمة دون عقد v220 صالح؛ يمكن حفظ التقرير كمسودة فقط حتى استكماله.`
        : "جميع التطبيقات المكتملة تحمل عقدًا منظمًا للنسخة والحقوق والمؤهل والمصدر والقيود."}</div>
      ${detailedTable(records)}`;
    target.insertAdjacentElement("afterend", expanded);
  };

  const persistAtomically = (caseRecord, report, now) => {
    caseRecord.reports ||= [];
    const previousCaseUpdatedAt = caseRecord.updatedAt;
    const previousStoreUpdatedAt = store.updatedAt;
    caseRecord.reports.push(report);
    caseRecord.updatedAt = now;
    store.updatedAt = now;
    const persisted = typeof set === "function" && typeof storeKey === "function"
      ? set(storeKey(identity.uid), store)
      : (save(), true);
    if (persisted) return true;
    caseRecord.reports.pop();
    caseRecord.updatedAt = previousCaseUpdatedAt;
    store.updatedAt = previousStoreUpdatedAt;
    return false;
  };

  const saveAtomicReport = (event) => {
    if (reportForm.dataset.v220Saving === "true") {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (!reportForm.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    const data = formObject(reportForm);
    const caseRecord = caseById(data.caseId);
    if (!caseRecord) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("تعذر العثور على الحالة المحددة؛ لم يُحفظ التقرير.");
      return;
    }
    const incomplete = incompleteCompletedRecords(caseRecord);
    if (NON_DRAFT.has(data.reviewStatus) && incomplete.length) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast(`لا يمكن اعتماد التقرير كمراجع أو نهائي: ${incomplete.length} تطبيق مهني مكتمل يحتاج استكمال الحقوق والنسخة والمصدر والقيود.`);
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    reportForm.dataset.v220Saving = "true";
    try {
      const now = new Date().toISOString();
      const snapshot = reportContractSnapshot(caseRecord, now);
      const cleanData = { ...data };
      delete cleanData.professionalSourcesContractJson;
      const report = {
        ...cleanData,
        reportId: cleanData.reportId || id("RPT"),
        versionNumber: (caseRecord.reports || []).length + 1,
        createdAt: now,
        createdByUid: identity.uid,
        createdByRole: identity.role,
        sourceSessionCount: (caseRecord.sessions || []).length,
        sourceProfessionalCount: recordsFor(caseRecord).length,
        reportVersion: BASE_REPORT_VERSION,
        professionalSourcesContract: snapshot,
        reportMaturityVersion: VERSION,
        auditTrail: [{
          event: "professional_sources_snapshot_created",
          at: now,
          actorUid: identity.uid,
          actorRole: identity.role,
          professionalRecordIds: [...snapshot.professionalRecordIds],
          incompleteCompletedRecordIds: [...snapshot.incompleteCompletedRecordIds],
        }],
      };
      if (!persistAtomically(caseRecord, report, now)) {
        toast("تعذر تثبيت التقرير محليًا؛ لم يُضف إصدار جزئي.");
        return;
      }
      render();
      const dialog = document.getElementById("case-report-dialog");
      if (dialog?.open && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      view("reports");
      toast("تم حفظ التقرير ولقطة المصادر المهنية في عملية محلية واحدة.");
    } finally {
      delete reportForm.dataset.v220Saving;
    }
  };

  reportForm.addEventListener("submit", saveAtomicReport, true);
  reportForm.addEventListener("input", () => queueMicrotask(enhancePreview));
  reportForm.addEventListener("change", () => queueMicrotask(enhancePreview));
  new MutationObserver(enhancePreview).observe(
    document.getElementById("case-report-dialog") || document.body,
    { childList: true, subtree: true }
  );
  enhancePreview();

  window.PA_PROFESSIONAL_REPORT_V220 = Object.freeze({
    version: VERSION,
    maturityValid,
    reportContractSnapshot,
    saveAtomicReport,
    nonDraftStatuses: [...NON_DRAFT],
  });
})();