"use strict";

(() => {
  const VERSION = "220.1";
  const data = window.PA_DEMO_DATA;
  const registry = window.PA_PROFESSIONAL_REGISTRY_V220;
  if (!data || !registry || typeof store === "undefined" || typeof save !== "function") return;

  const completedStatuses = new Set(["completed", "result_imported"]);
  const baseFields = [
    "administrationDate", "assignedEntityLabel", "performerName", "practitionerQualification",
    "administrationMode", "versionLanguage", "resultSourceType", "reportReference",
    "reportIssuedBy", "outcomeLabel", "scoreReference", "notes", "nextAction",
  ];
  const maturityFields = [
    "publisher", "instrumentVersion", "administrationLanguage", "rightsBasis", "rightsReference",
    "scoreSource", "officialSourceReference", "selectionRationale", "administrationQuality",
    "behavioralObservations", "interpretationLimitations", "integrationSummary", "recommendations",
    "followUpDate", "reviewedBy", "reviewStatus",
  ];
  const clean = (value, limit = 3000) => String(value || "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, " ").trim().slice(0, limit);
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

  const allRecords = () => store.cases.flatMap((caseRecord) =>
    (caseRecord.professionalAssessments || []).map((record) => ({ caseRecord, record }))
  );
  const findRecord = (recordId) => allRecords().find(({ record }) => record.recordId === recordId) || null;
  const toolFor = (record) => data.professional.find((tool) => tool.id === record.toolId || tool.name === record.toolName)
    || registry.customRecordTool;

  const createInput = (name, label, type = "text") => `<label class="field"><span>${esc(label)}</span><input name="edit_maturity_${esc(name)}" type="${esc(type)}" maxlength="300"></label>`;
  const createTextarea = (name, label) => `<label class="field report-full"><span>${esc(label)}</span><textarea name="edit_maturity_${esc(name)}" rows="3" maxlength="2400"></textarea></label>`;
  const createSelect = (name, label, options) => `<label class="field"><span>${esc(label)}</span><select name="edit_maturity_${esc(name)}"><option value="">اختر</option>${options.map(([value,text])=>`<option value="${esc(value)}">${esc(text)}</option>`).join("")}</select></label>`;

  const install = () => {
    const form = document.getElementById("professional-record-edit-form");
    if (!form || document.getElementById("professional-record-edit-maturity-v220")) return false;
    const section = document.createElement("section");
    section.id = "professional-record-edit-maturity-v220";
    section.className = "panel report-full";
    section.innerHTML = `<div class="section-heading compact"><div><p class="eyebrow">استكمال عقد السجل v${VERSION}</p><h3>الحقوق والنسخة والمصدر والتكامل</h3></div><span class="badge neutral">تعديل موثق</span></div>
      <div id="professional-edit-contract-summary-v220" class="callout warning"></div>
      <div class="report-form-grid">
        ${createInput("publisher","الناشر أو الجهة المالكة")}
        ${createInput("instrumentVersion","الإصدار أو النموذج")}
        ${createInput("administrationLanguage","لغة النسخة الرسمية")}
        ${createSelect("rightsBasis","أساس الحق",[["pending_review","قيد المراجعة — للتخطيط فقط"],["licensed_original_copy","نسخة أصلية مرخصة"],["official_public_permission","إذن رسمي عام أو مكتوب"],["external_report_only","تقرير خارجي فقط"]])}
        ${createInput("rightsReference","مرجع الحق أو الترخيص")}
        ${createSelect("scoreSource","مصدر النتيجة",[["official_report","تقرير رسمي"],["authorized_scoring_platform","منصة تصحيح مصرح بها"],["qualified_professional_record","سجل مختص مؤهل"],["publisher_output","مخرج الناشر"]])}
        ${createInput("officialSourceReference","مرجع المخرج الرسمي")}
        ${createInput("followUpDate","تاريخ المتابعة","date")}
        ${createTextarea("selectionRationale","مبرر اختيار الأداة")}
        ${createTextarea("administrationQuality","جودة التطبيق وشروطه")}
        ${createTextarea("behavioralObservations","الملاحظات السلوكية والسياقية")}
        ${createTextarea("interpretationLimitations","قيود التفسير")}
        ${createTextarea("integrationSummary","تكامل النتيجة مع المصادر الأخرى")}
        ${createTextarea("recommendations","التوصيات والمتابعة")}
        ${createInput("reviewedBy","المراجع المهني")}
        ${createSelect("reviewStatus","حالة المراجعة",[["not_reviewed","لم تراجع"],["self_checked","مراجعة ذاتية"],["peer_reviewed","مراجعة زميل مؤهل"],["team_reviewed","مراجعة فريق"]])}
        <label class="rights-confirmation report-full"><input name="edit_maturity_noProtectedContent" type="checkbox"><span>أؤكد أن السجل لا يحتوي بنود الأداة أو الاستجابات الفردية أو مفاتيح التصحيح أو الجداول المعيارية.</span></label>
      </div>`;
    form.querySelector('[name="editReason"]')?.closest("label")?.before(section);
    form.addEventListener("submit", saveStructuredEdit, true);
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-edit-professional-record]");
      if (button) setTimeout(() => fill(button.dataset.editProfessionalRecord), 0);
    }, true);
    return true;
  };

  const editInput = (form, name) => form.elements[`edit_maturity_${name}`];
  const fill = (recordId) => {
    const form = document.getElementById("professional-record-edit-form");
    const found = findRecord(recordId);
    if (!form || !found) return;
    const { record } = found;
    const maturity = record.professionalMaturity || {};
    const tool = toolFor(record);
    const values = {
      publisher: maturity.instrument?.publisher || record.reportIssuedBy || "",
      instrumentVersion: maturity.instrument?.version || record.versionLanguage || "",
      administrationLanguage: maturity.instrument?.language || record.versionLanguage || "",
      rightsBasis: maturity.rights?.basis || (record.administrationMode === "external_import" || record.resultSourceType === "external_report" ? "external_report_only" : "pending_review"),
      rightsReference: maturity.rights?.reference || record.reportReference || "",
      scoreSource: maturity.officialResultSource?.type || (record.resultSourceType === "external_report" ? "official_report" : "qualified_professional_record"),
      officialSourceReference: maturity.officialResultSource?.reference || record.reportReference || record.scoreReference || "",
      selectionRationale: maturity.selectionRationale || "",
      administrationQuality: maturity.administrationQuality || "",
      behavioralObservations: maturity.behavioralObservations || "",
      interpretationLimitations: maturity.interpretationLimitations || record.notes || "",
      integrationSummary: maturity.integrationSummary || "",
      recommendations: maturity.recommendations || "",
      followUpDate: maturity.followUpDate || "",
      reviewedBy: maturity.review?.reviewedBy || "",
      reviewStatus: maturity.review?.status || "not_reviewed",
    };
    for (const name of maturityFields) if (editInput(form,name)) editInput(form,name).value = values[name] || "";
    editInput(form,"noProtectedContent").checked = Boolean(maturity.rights && maturity.rights.protectedContentStored === false);
    const summary = document.getElementById("professional-edit-contract-summary-v220");
    if (summary) summary.innerHTML = `<strong>${esc(record.toolName)}:</strong> ${completedStatuses.has(record.recordStatus) ? "السجل مكتمل ويجب استيفاء العقد كاملًا." : "يمكن إبقاء الحقوق قيد المراجعة حتى اكتمال التطبيق."} التطبيق الرقمي داخل المنصة غير متاح.`;
    applyRequirements(form, record, tool);
  };

  const applyRequirements = (form, record, tool) => {
    for (const element of form.querySelectorAll('[name^="edit_maturity_"]')) element.required = false;
    if (!completedStatuses.has(record.recordStatus)) return;
    const required = tool.professionalContract.requiredCompletedFields.filter((name) => name !== "administratorQualification");
    for (const name of required) if (editInput(form,name)) editInput(form,name).required = true;
    editInput(form,"noProtectedContent").required = true;
    form.elements.practitionerQualification.required = true;
  };

  const structured = (form, record) => {
    const values = {};
    for (const name of maturityFields) values[name] = clean(editInput(form,name)?.value, ["selectionRationale","administrationQuality","behavioralObservations","interpretationLimitations","integrationSummary","recommendations"].includes(name) ? 2400 : 300);
    const now = new Date().toISOString();
    const previousAudit = record.professionalMaturity?.auditTrail || [];
    return {
      schema:"professional-registry-record-v220",version:VERSION,
      instrument:{publisher:values.publisher,version:values.instrumentVersion,language:values.administrationLanguage},
      administrator:{qualification:clean(form.elements.practitionerQualification.value,300)},
      rights:{basis:values.rightsBasis,reference:values.rightsReference,protectedContentStored:false,itemResponsesStored:false,scoringKeyStored:false,normTablesStored:false},
      officialResultSource:{type:values.scoreSource,reference:values.officialSourceReference},
      selectionRationale:values.selectionRationale,administrationQuality:values.administrationQuality,
      behavioralObservations:values.behavioralObservations,interpretationLimitations:values.interpretationLimitations,
      integrationSummary:values.integrationSummary,recommendations:values.recommendations,followUpDate:values.followUpDate,
      review:{status:values.reviewStatus||"not_reviewed",reviewedBy:values.reviewedBy},
      recordedAt:record.professionalMaturity?.recordedAt||now,
      updatedAt:now,
      auditTrail:[...previousAudit,{event:"structured_record_updated",at:now,actorUid:identity.uid,actorRole:identity.role}],
    };
  };

  function saveStructuredEdit(event) {
    const form = event.currentTarget;
    const found = findRecord(form.elements.recordId.value);
    if (!found) return;
    const { caseRecord, record } = found;
    const tool = toolFor(record);
    applyRequirements(form, record, tool);
    if (!form.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    const completed = completedStatuses.has(record.recordStatus);
    const rights = editInput(form,"rightsBasis").value;
    if (completed && (rights === "pending_review" || !tool.professionalContract.permittedRightsBases.includes(rights))) {
      event.preventDefault();event.stopImmediatePropagation();toast("لا يمكن اعتماد السجل المكتمل قبل توثيق أساس حق صالح.");return;
    }
    const suspicious = `${form.elements.scoreReference.value} ${form.elements.notes.value}`;
    if (/(مفتاح\s*التصحيح|جدول\s*المعايير|إجابات\s*البنود|نص\s*البند|answer\s*key|norm\s*table)/i.test(suspicious)) {
      event.preventDefault();event.stopImmediatePropagation();toast("رُفض التعديل لأنه قد يتضمن مادة محمية.");return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    const changes = [];
    for (const field of baseFields) {
      const next = clean(form.elements[field]?.value, field === "notes" ? 3000 : 300);
      const previous = String(record[field] || "");
      if (next !== previous) changes.push({field,from:previous,to:next});
      record[field] = next;
    }
    const beforeMaturity = JSON.stringify(record.professionalMaturity || null);
    const nextMaturity = structured(form, record);
    if (beforeMaturity !== JSON.stringify(nextMaturity)) changes.push({field:"professionalMaturity",from:"previous-version",to:VERSION});
    if (!changes.length) return toast("لم تُسجل تغييرات جديدة.");
    const now = new Date().toISOString();
    record.metadataAuditTrail ||= [];
    record.metadataAuditTrail.push({
      auditId:typeof id==="function"?id("META"):`META-${Date.now()}`,eventType:"metadata_updated",changedAt:now,
      changedByUid:identity.uid,changedByRole:identity.role,reason:clean(form.elements.editReason.value,1000),changes,
    });
    record.professionalMaturity = nextMaturity;
    record.professionalContractVersion = VERSION;
    record.digitalAdministrationOccurredInsidePlatform = false;
    record.protectedContentStored = false;
    record.rightsConfirmed = form.elements.rightsConfirmed.checked;
    record.lastUpdatedAt = now;record.lastUpdatedByUid=identity.uid;record.lastUpdatedByRole=identity.role;record.integrityVersion="1.0.0";
    caseRecord.updatedAt=now;save();render();document.getElementById("professional-record-edit-dialog").close();toast("تم استكمال عقد السجل وحفظ التعديل في سجل التدقيق.");
  }

  let attempts = 0;
  const timer = setInterval(() => {
    attempts += 1;
    if (install() || attempts >= 100) clearInterval(timer);
  }, 50);

  window.PA_PROFESSIONAL_EDIT_V220 = Object.freeze({version:VERSION,completedRightsRequired:true,legacyRecordsUpgradable:true});
})();
