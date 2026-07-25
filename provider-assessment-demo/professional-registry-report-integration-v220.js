"use strict";

(() => {
  const VERSION = "220.1";
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const completed = new Set(["completed", "result_imported"]);
  const reportForm = document.getElementById("case-report-form");
  if (!reportForm || typeof store === "undefined") return;

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
    return value.rights.protectedContentStored === false
      && value.rights.itemResponsesStored === false
      && value.rights.scoringKeyStored === false
      && value.rights.normTablesStored === false;
  };

  const recordsFor = (caseRecord) => caseRecord?.professionalAssessments || [];
  const completedRecords = (caseRecord) => recordsFor(caseRecord).filter((record) => completed.has(record.recordStatus));
  const incompleteCompletedRecords = (caseRecord) => completedRecords(caseRecord).filter((record) => !maturityValid(record));

  const detailedTable = (records) => `<div class="analytics-table-wrap"><table class="analytics-table professional-maturity-report-table">
    <thead><tr><th>الأداة والحالة</th><th>النسخة والحقوق</th><th>المنفذ والمصدر</th><th>جودة التطبيق والقيود</th><th>التكامل والمتابعة</th></tr></thead>
    <tbody>${records.map((record) => {
      const value = record.professionalMaturity;
      if (!value) return `<tr><td><strong>${esc(record.toolName)}</strong><br>${esc(record.recordStatus)}</td><td colspan="4"><span class="badge warning">سجل قديم غير منظم</span> يجب استكمال عقد الحقوق والنسخة والمصدر قبل اعتماد التقرير نهائيًا.</td></tr>`;
      return `<tr>
        <td><strong>${esc(record.toolName)}</strong><br>${esc(record.recordStatus)} · ${esc(record.administrationDate)}</td>
        <td>${esc(value.instrument.publisher)}<br>${esc(value.instrument.version)} · ${esc(value.instrument.language)}<br><strong>الحقوق:</strong> ${esc(value.rights.basis)} · ${esc(value.rights.reference)}</td>
        <td>${esc(record.assignedEntityLabel)}${record.performerName ? ` — ${esc(record.performerName)}` : ""}<br>${esc(value.administrator.qualification)}<br><strong>المصدر:</strong> ${esc(value.officialResultSource.type)} · ${esc(value.officialResultSource.reference)}</td>
        <td><strong>الجودة:</strong> ${esc(value.administrationQuality || "غير مسجلة")}<br><strong>القيود:</strong> ${esc(value.interpretationLimitations || "غير مسجلة")}</td>
        <td><strong>التكامل:</strong> ${esc(value.integrationSummary || "غير مسجل")}<br><strong>التوصيات:</strong> ${esc(value.recommendations || "غير مسجلة")}<br><strong>المتابعة:</strong> ${esc(value.followUpDate || "غير محددة")} · ${esc(value.review?.status || "not_reviewed")}</td>
      </tr>`;
    }).join("")}</tbody></table></div>`;

  const enhancePreview = () => {
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

  const reportContractSnapshot = (caseRecord) => {
    const records = recordsFor(caseRecord);
    const completedList = completedRecords(caseRecord);
    const valid = completedList.filter(maturityValid);
    return {
      schema: "case-report-professional-sources-v220",
      version: VERSION,
      professionalRecordIds: records.map((record) => record.recordId),
      totalProfessionalRecords: records.length,
      completedProfessionalRecords: completedList.length,
      structuredProfessionalRecords: records.filter((record) => record.professionalMaturity).length,
      rightsValidCompletedRecords: valid.length,
      incompleteCompletedRecordIds: completedList.filter((record) => !maturityValid(record)).map((record) => record.recordId),
      protectedContentStored: false,
      capturedAt: new Date().toISOString(),
    };
  };

  const validateAndAttach = (event) => {
    const caseId = reportForm.elements.caseId?.value;
    const caseRecord = caseById(caseId);
    if (!caseRecord) return;
    const finalRequested = reportForm.elements.reviewStatus?.value === "final";
    const incomplete = incompleteCompletedRecords(caseRecord);
    if (finalRequested && incomplete.length) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast(`لا يمكن اعتماد التقرير نهائيًا: ${incomplete.length} تطبيق مهني مكتمل يحتاج استكمال الحقوق والنسخة والمصدر والقيود.`);
      return;
    }

    const snapshot = reportContractSnapshot(caseRecord);
    const beforeCount = caseRecord.reports?.length || 0;
    queueMicrotask(() => {
      const current = caseById(caseId);
      const reports = current?.reports || [];
      if (reports.length !== beforeCount + 1) return;
      const report = reports[reports.length - 1];
      if (report.professionalSourcesContract) return;
      report.professionalSourcesContract = snapshot;
      report.reportMaturityVersion = VERSION;
      report.auditTrail = [...(report.auditTrail || []), {
        event: "professional_sources_snapshot_attached",
        at: new Date().toISOString(),
        actorUid: identity.uid,
        actorRole: identity.role,
      }];
      current.updatedAt = new Date().toISOString();
      save();
    });
  };

  reportForm.addEventListener("submit", validateAndAttach, true);
  reportForm.addEventListener("input", () => queueMicrotask(enhancePreview));
  reportForm.addEventListener("change", () => queueMicrotask(enhancePreview));
  new MutationObserver(enhancePreview).observe(document.getElementById("case-report-dialog") || document.body, { childList: true, subtree: true });
  enhancePreview();

  window.PA_PROFESSIONAL_REPORT_V220 = Object.freeze({ version: VERSION, maturityValid, reportContractSnapshot });
})();
