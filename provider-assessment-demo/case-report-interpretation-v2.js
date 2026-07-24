"use strict";

(() => {
  if (typeof store === "undefined" || typeof identity === "undefined" || typeof save !== "function") return;

  const CONTRACT_VERSION = "2026.07.24-report-interpretation.2";
  const TYPE_DEFINITIONS = {
    screening: {
      label: "المسح أو الفرز",
      statement: "يحدد الحاجة إلى تقييم إضافي فقط، ولا يثبت التشخيص أو الأهلية ولا يغني عن التقييم المتعمق.",
      guidance: "سجّل سبب المسح، المصدر، الأداة الرسمية والإصدار واللغة، ثم اذكر خطوة المتابعة دون صياغة تشخيصية."
    },
    diagnostic: {
      label: "التقييم التشخيصي",
      statement: "قرار مهني متعدد المصادر يصدر عن مختص أو فريق مخول، ولا تنتجه المنصة أو درجة منفردة.",
      guidance: "وضّح الأدلة المؤيدة والمخالفة، البدائل التفسيرية، صلاحية النتائج، ومن اتخذ القرار المهني."
    },
    functional: {
      label: "التقييم الوظيفي",
      statement: "يصف النشاط والمشاركة والاستقلال والعوائق والميسرات في البيئات الفعلية.",
      guidance: "اربط النتيجة بمهمة وبيئة ومستوى مساعدة وتكييفات ورأي الشخص والأسرة."
    },
    progress: {
      label: "متابعة التقدم",
      statement: "تقارن مؤشرًا قابلًا للملاحظة بخط أساس وهدف وموعد إعادة قياس في ظروف موثقة.",
      guidance: "عرّف المؤشر ووحدة القياس وتواتر الجمع والظروف وأي تغيير في خطة الدعم."
    }
  };

  const TRACKED_FIELDS = [
    "assessmentType", "purpose", "evidenceSources", "decisionAuthority", "functionalContexts",
    "resultValidity", "interpretationLimitations", "baselineIndicator", "measurementMethod",
    "measurableGoal", "remeasurementDate", "providerInterpretation", "familySummary",
    "strengths", "needs", "integratedSummary", "recommendations", "decision",
    "followUpDate", "followUpIndicators", "reviewStatus"
  ];

  const FIELD_LABELS = {
    assessmentType: "نوع التقييم", purpose: "سؤال الإحالة وغرض القرار", evidenceSources: "مصادر الأدلة",
    decisionAuthority: "صاحب القرار المهني", functionalContexts: "البيئات والمواقف الوظيفية",
    resultValidity: "صلاحية النتيجة", interpretationLimitations: "حدود التفسير",
    baselineIndicator: "مؤشر خط الأساس", measurementMethod: "طريقة ووحدة القياس",
    measurableGoal: "الهدف القابل للقياس", remeasurementDate: "موعد إعادة القياس",
    providerInterpretation: "التفسير المهني", familySummary: "الملخص الموجه للأسرة",
    strengths: "نقاط القوة", needs: "الاحتياجات والعوائق", integratedSummary: "الملخص المتكامل",
    recommendations: "التوصيات", decision: "قرار المسار", followUpDate: "موعد المتابعة",
    followUpIndicators: "مؤشرات المتابعة", reviewStatus: "حالة الإصدار"
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const nowIso = () => new Date().toISOString();
  const caseById = (caseId) => store.cases.find((item) => item.caseId === caseId);
  const formObject = (form) => Object.fromEntries([...new FormData(form).entries()].map(([key, value]) => [key, String(value)]));

  const parseAudit = (value) => {
    if (Array.isArray(value)) return clone(value);
    if (typeof value !== "string" || !value.trim()) return [];
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  };

  const selectedCondition = (caseRecord) => {
    const registry = window.PA_CONDITION_PATHWAYS;
    const saved = caseRecord?.conditionPathway;
    if (saved?.slug) return registry?.conditions?.find((item) => item.slug === saved.slug) || saved;
    try {
      const local = JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null");
      return registry?.conditions?.find((item) => item.slug === local?.slug) || local;
    } catch (_) {
      return null;
    }
  };

  const installStyles = () => {
    if (document.getElementById("report-interpretation-v2-styles")) return;
    const style = document.createElement("style");
    style.id = "report-interpretation-v2-styles";
    style.textContent = `
      .interpretation-contract{grid-column:1/-1;border:1px solid var(--line);border-radius:16px;padding:16px;background:#f7fbfb;display:grid;gap:14px}
      .interpretation-contract legend{font-weight:900;padding:0 8px}.interpretation-contract-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
      .interpretation-contract .full{grid-column:1/-1}.type-guidance{border-right:5px solid #0b6b66;background:#eaf7f5;padding:12px 14px;border-radius:12px}
      .condition-report-context{border:1px dashed #70aaa5;padding:12px;border-radius:12px;background:#fff}.condition-report-context ul{margin:.5rem 0 0}
      .report-contract-sections{display:grid;gap:18px}.report-contract-sections section{border-top:1px solid var(--line);padding-top:12px}
      .report-contract-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.report-contract-grid>div{border:1px solid var(--line);border-radius:10px;padding:9px}
      .report-contract-grid dt{font-size:.82rem;color:var(--muted)}.report-contract-grid dd{margin:3px 0 0;font-weight:700;white-space:pre-wrap}
      .family-facing-summary{background:#f4f8ff;border-right:5px solid #376fa3;padding:12px 14px;border-radius:12px}
      .report-audit-list{margin:0;padding-right:20px}.report-audit-list li{margin:.5rem 0}.required-by-contract>span:first-child::after{content:" *";color:#9b241c}
      @media(max-width:800px){.interpretation-contract-grid,.report-contract-grid{grid-template-columns:1fr}.interpretation-contract .full{grid-column:auto}}
      @media print{.report-contract-sections{display:block}.report-contract-sections section{break-inside:avoid}}
    `;
    document.head.appendChild(style);
  };

  const hiddenInput = (name) => `<input type="hidden" name="${name}">`;

  const installContractFields = () => {
    const form = document.getElementById("case-report-form");
    const grid = form?.querySelector(".report-form-grid");
    if (!form || !grid || form.elements.assessmentType) return;
    form.dataset.interpretationV2 = "true";

    const purpose = form.elements.purpose?.closest("label");
    if (purpose?.querySelector("span")) purpose.querySelector("span").textContent = "سؤال الإحالة وغرض القرار";

    const fieldset = document.createElement("fieldset");
    fieldset.className = "interpretation-contract";
    fieldset.dataset.reportInterpretationContract = "true";
    fieldset.innerHTML = `
      <legend>عقد التفسير وصلاحية النتيجة</legend>
      <div class="interpretation-contract-grid">
        <label class="field"><span>نوع التقييم</span><select name="assessmentType" required><option value="">اختر النوع</option>${Object.entries(TYPE_DEFINITIONS).map(([id, item]) => `<option value="${id}">${esc(item.label)}</option>`).join("")}</select></label>
        <label class="field"><span>صاحب القرار المهني أو الفريق</span><input name="decisionAuthority" maxlength="240" placeholder="الاسم أو الدور أو الفريق المخول"></label>
        <label class="field full"><span>مصادر الأدلة المستخدمة</span><textarea name="evidenceSources" rows="3" maxlength="2400" placeholder="مقابلة، ملاحظة، تقارير، جلسات، نتائج خارجية رسمية، أكثر من بيئة..." required></textarea></label>
        <label class="field full"><span>صلاحية النتيجة</span><textarea name="resultValidity" rows="3" maxlength="2400" placeholder="مدى ملاءمة اللغة والتواصل والسمع والبصر والحركة والحالة الصحية وظروف التطبيق" required></textarea></label>
        <label class="field full"><span>حدود التفسير</span><textarea name="interpretationLimitations" rows="3" maxlength="2400" placeholder="البيانات الناقصة، اختلاف البيئات، التكييفات، الخروج عن الإجراءات أو قيود المصدر" required></textarea></label>
        <label class="field full"><span>البيئات والمواقف الوظيفية</span><textarea name="functionalContexts" rows="3" maxlength="2000" placeholder="البيت، المدرسة، العمل، المجتمع، المهمة، مستوى المساعدة والعوامل البيئية"></textarea></label>
        <label class="field"><span>مؤشر خط الأساس</span><textarea name="baselineIndicator" rows="3" maxlength="1800" placeholder="وصف قابل للملاحظة قبل الخطة"></textarea></label>
        <label class="field"><span>طريقة ووحدة القياس</span><textarea name="measurementMethod" rows="3" maxlength="1800" placeholder="عدد، نسبة، مدة، زمن، مستوى مساعدة، عينة عمل..."></textarea></label>
        <label class="field full"><span>الهدف القابل للقياس</span><textarea name="measurableGoal" rows="3" maxlength="2200" placeholder="في [الموقف] سيؤدي الشخص [السلوك] بمستوى مساعدة [محدد] في [عدد أو نسبة] خلال [مدة]"></textarea></label>
        <label class="field"><span>موعد إعادة القياس</span><input name="remeasurementDate" type="date"></label>
        <label class="field" data-screening-confirmation><span>إقرار المسح غير التشخيصي</span><span class="checkbox-line"><input name="screeningAcknowledgement" type="checkbox" value="confirmed"> أفهم أن المسح لا يثبت التشخيص أو الأهلية.</span></label>
        <label class="field full"><span>التفسير المهني</span><textarea name="providerInterpretation" rows="5" maxlength="5000" placeholder="افصل الأدلة عن الاستنتاج، واذكر المؤيد والمخالف والبدائل والسياق" required></textarea></label>
        <label class="field full"><span>ملخص موجه للأسرة أو الشخص</span><textarea name="familySummary" rows="5" maxlength="4000" placeholder="لغة واضحة ومحترمة: ما الذي ظهر؟ ما حدوده؟ ما نقاط القوة؟ ما الخطوة التالية؟"></textarea></label>
        <label class="field full"><span>سبب إصدار نسخة جديدة أو تعديل التفسير</span><textarea name="revisionReason" rows="2" maxlength="1200" placeholder="يصبح إلزاميًا عند إصدار نسخة مبنية على تقرير محفوظ"></textarea></label>
      </div>
      <div id="report-type-guidance" class="type-guidance" role="note">اختر نوع التقييم لعرض قواعده.</div>
      <div id="report-condition-context" class="condition-report-context" role="note"></div>
      ${hiddenInput("supersedesReportId")}${hiddenInput("sourceVersionNumber")}${hiddenInput("reviewAuditTrail")}${hiddenInput("interpretationContractVersion")}
    `;
    if (purpose) purpose.insertAdjacentElement("afterend", fieldset);
    else grid.prepend(fieldset);
    form.elements.interpretationContractVersion.value = CONTRACT_VERSION;
  };

  const setRequired = (element, required) => {
    if (!element) return;
    element.required = Boolean(required);
    element.closest("label")?.classList.toggle("required-by-contract", Boolean(required));
  };

  const applyTypeRules = () => {
    const form = document.getElementById("case-report-form");
    if (!form?.elements.assessmentType) return;
    const type = form.elements.assessmentType.value;
    const status = form.elements.reviewStatus?.value || "draft";
    const definition = TYPE_DEFINITIONS[type];
    const guidance = document.getElementById("report-type-guidance");
    if (guidance) guidance.innerHTML = definition
      ? `<strong>${esc(definition.label)}:</strong> ${esc(definition.statement)}<br><span>${esc(definition.guidance)}</span>`
      : "اختر نوع التقييم لعرض قواعده.";

    setRequired(form.elements.decisionAuthority, type === "diagnostic");
    setRequired(form.elements.functionalContexts, type === "functional");
    setRequired(form.elements.baselineIndicator, type === "progress");
    setRequired(form.elements.measurementMethod, type === "progress");
    setRequired(form.elements.measurableGoal, type === "progress");
    setRequired(form.elements.remeasurementDate, type === "progress");
    setRequired(form.elements.screeningAcknowledgement, type === "screening");
    setRequired(form.elements.familySummary, status === "reviewed" || status === "final");
    form.querySelector("[data-screening-confirmation]")?.classList.toggle("hidden", type !== "screening");
  };

  const renderConditionContext = () => {
    const form = document.getElementById("case-report-form");
    const box = document.getElementById("report-condition-context");
    const caseRecord = caseById(form?.elements.caseId?.value);
    const condition = selectedCondition(caseRecord);
    if (!box) return;
    if (!condition) {
      box.innerHTML = "<strong>مسار الحالة:</strong> غير مرتبط بعد. يمكن إنشاء التقرير دون مسار، لكن يجب توثيق سؤال الإحالة والمجالات الوظيفية.";
      return;
    }
    const focus = Array.isArray(condition.focus) ? condition.focus.slice(0, 5) : [];
    box.innerHTML = `<strong>مسار الحالة: ${esc(condition.title || condition.slug)}</strong>${condition.summary ? `<p>${esc(condition.summary)}</p>` : ""}${focus.length ? `<span>مجالات تساعد في اختيار خط الأساس والهدف:</span><ul>${focus.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}`;
  };

  const auditText = (item) => {
    const action = item.action === "revision" ? "إصدار مراجعة" : "إنشاء التقرير";
    const changes = Array.isArray(item.changedFields) && item.changedFields.length
      ? ` — الحقول: ${item.changedFields.map((key) => FIELD_LABELS[key] || key).join("، ")}` : "";
    return `${action} في ${item.at || ""} بواسطة ${item.byLabel || item.byUid || "مستخدم محلي"}${changes}${item.reason ? ` — السبب: ${item.reason}` : ""}`;
  };

  const previewSections = (data, caseRecord) => {
    const definition = TYPE_DEFINITIONS[data.assessmentType];
    const audit = parseAudit(data.reviewAuditTrail);
    const condition = selectedCondition(caseRecord);
    return `
      <div class="report-contract-sections" data-report-contract-sections>
        <section><h3>نوع التقييم وحدود القرار</h3><dl class="report-contract-grid"><div><dt>النوع</dt><dd>${esc(definition?.label || "غير محدد")}</dd></div><div><dt>مسار الحالة</dt><dd>${esc(condition?.title || "غير مرتبط")}</dd></div></dl><p class="report-disclaimer">${esc(definition?.statement || "يجب تحديد نوع التقييم قبل اعتماد التقرير.")}</p></section>
        <section><h3>أساس الأدلة وصلاحية التفسير</h3><dl class="report-contract-grid"><div><dt>مصادر الأدلة</dt><dd>${esc(data.evidenceSources || "غير مسجلة")}</dd></div><div><dt>صاحب القرار المهني</dt><dd>${esc(data.decisionAuthority || "غير مسجل")}</dd></div><div><dt>صلاحية النتيجة</dt><dd>${esc(data.resultValidity || "غير مسجلة")}</dd></div><div><dt>حدود التفسير</dt><dd>${esc(data.interpretationLimitations || "غير مسجلة")}</dd></div><div><dt>المواقف الوظيفية</dt><dd>${esc(data.functionalContexts || "غير مسجلة")}</dd></div><div><dt>مواد الأدوات المحمية</dt><dd>تُسجل النتيجة أو مرجع التقرير الخارجي فقط؛ لا تُنسخ البنود أو مفاتيح التصحيح أو المعايير.</dd></div></dl></section>
        <section><h3>التفسير المهني</h3><p>${esc(data.providerInterpretation || "غير مكتمل")}</p></section>
        <section><h3>خط الأساس والهدف وإعادة القياس</h3><dl class="report-contract-grid"><div><dt>خط الأساس</dt><dd>${esc(data.baselineIndicator || "غير محدد")}</dd></div><div><dt>طريقة القياس</dt><dd>${esc(data.measurementMethod || "غير محددة")}</dd></div><div><dt>الهدف</dt><dd>${esc(data.measurableGoal || "غير محدد")}</dd></div><div><dt>إعادة القياس</dt><dd>${esc(data.remeasurementDate || "غير محددة")}</dd></div></dl></section>
        <section class="family-facing-summary"><h3>ملخص موجه للأسرة أو الشخص</h3><p>${esc(data.familySummary || "لم يكتمل بعد في هذا الإصدار.")}</p></section>
        <section><h3>سجل مراجعة التفسير</h3>${audit.length ? `<ol class="report-audit-list">${audit.map((item) => `<li>${esc(auditText(item))}</li>`).join("")}</ol>` : "<p>سيُنشأ سجل المراجعة عند حفظ الإصدار.</p>"}</section>
      </div>`;
  };

  const augmentPreview = () => {
    const form = document.getElementById("case-report-form");
    const preview = document.getElementById("case-report-preview");
    if (!form || !preview) return;
    preview.querySelector("[data-report-contract-sections]")?.remove();
    const data = formObject(form);
    const caseRecord = caseById(data.caseId);
    const article = preview.querySelector("[data-report-preview]");
    if (!article || !caseRecord) return;
    const wrapper = document.createElement("div");
    wrapper.innerHTML = previewSections(data, caseRecord);
    const disclaimer = article.querySelector(":scope > .report-disclaimer");
    article.insertBefore(wrapper.firstElementChild, disclaimer || null);
  };

  const findExistingReport = (caseRecord, reportId) => {
    if (!caseRecord || !reportId) return null;
    return [...(caseRecord.reports || [])].reverse().find((item) => item.reportId === reportId) || null;
  };
  const computeChangedFields = (existing, current) => TRACKED_FIELDS.filter((key) => String(existing?.[key] ?? "") !== String(current?.[key] ?? ""));

  const prepareOpenReport = () => {
    const form = document.getElementById("case-report-form");
    if (!form?.elements.assessmentType) return;
    const caseRecord = caseById(form.elements.caseId.value);
    const existing = findExistingReport(caseRecord, form.elements.reportId.value);
    form.elements.revisionReason.required = Boolean(existing);
    form.elements.revisionReason.closest("label")?.classList.toggle("required-by-contract", Boolean(existing));
    form.elements.supersedesReportId.value = existing?.reportId || "";
    form.elements.sourceVersionNumber.value = existing ? String(existing.versionNumber || "") : "";
    form.elements.reviewAuditTrail.value = existing?.reviewAuditTrail || "";
    form.elements.interpretationContractVersion.value = CONTRACT_VERSION;
    if (!existing && !form.elements.assessmentType.value && form.elements.reportType.value === "progress") form.elements.assessmentType.value = "progress";
    applyTypeRules();
    renderConditionContext();
    setTimeout(augmentPreview, 0);
  };

  const stageAuditAndVersion = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "case-report-form") return;
    applyTypeRules();
    const data = formObject(form);
    const caseRecord = caseById(data.caseId);
    const existing = findExistingReport(caseRecord, data.reportId);

    if (data.assessmentType === "screening" && data.screeningAcknowledgement !== "confirmed") {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("يجب تأكيد أن المسح لا يثبت التشخيص أو الأهلية.");
      form.elements.screeningAcknowledgement.focus();
      return;
    }
    if ((data.reviewStatus === "reviewed" || data.reviewStatus === "final") && !data.familySummary.trim()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("الملخص الموجه للأسرة مطلوب قبل اعتماد التقرير كمراجع أو نهائي.");
      form.elements.familySummary.focus();
      return;
    }
    if (!form.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }

    const changedFields = existing ? computeChangedFields(existing, data) : TRACKED_FIELDS.filter((key) => data[key]);
    if (existing && !changedFields.length) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("لم يتغير أي حقل تفسيري. عدّل التقرير أو أغلق النافذة دون إنشاء إصدار مكرر.");
      return;
    }

    const audit = parseAudit(existing?.reviewAuditTrail);
    audit.push({
      eventId: typeof id === "function" ? id("RPT-AUD") : `RPT-AUD-${Date.now()}`,
      action: existing ? "revision" : "created", at: nowIso(), byUid: identity.uid,
      byRole: identity.role, byLabel: identity.username || identity.uid,
      reviewStatus: data.reviewStatus, assessmentType: data.assessmentType, changedFields,
      reason: data.revisionReason || (existing ? "إصدار مراجعة" : "إنشاء التقرير"),
      supersedesReportId: existing?.reportId || null,
      supersedesVersionNumber: existing?.versionNumber || null,
      contractVersion: CONTRACT_VERSION
    });

    form.elements.reviewAuditTrail.value = JSON.stringify(audit);
    form.elements.supersedesReportId.value = existing?.reportId || "";
    form.elements.sourceVersionNumber.value = existing ? String(existing.versionNumber || "") : "";
    form.elements.interpretationContractVersion.value = CONTRACT_VERSION;
    if (existing) form.elements.reportId.value = "";
  };

  const decorateReportCards = () => {
    document.querySelectorAll("#report-list [data-open-report]").forEach((button) => {
      const card = button.closest(".report-card");
      if (!card || card.dataset.interpretationDecorated === "true") return;
      const caseRecord = caseById(button.dataset.reportCase);
      const report = findExistingReport(caseRecord, button.dataset.openReport);
      if (!report) return;
      const definition = TYPE_DEFINITIONS[report.assessmentType];
      const header = card.querySelector("header > div");
      const meta = card.querySelector(".report-meta");
      if (definition && header) header.insertAdjacentHTML("afterbegin", `<span class="badge neutral">${esc(definition.label)}</span>`);
      if (report.supersedesReportId && meta) meta.insertAdjacentHTML("beforeend", `<div><dt>مبني على</dt><dd class="code small">${esc(report.supersedesReportId)}</dd></div>`);
      card.dataset.interpretationDecorated = "true";
    });
  };

  installStyles();
  installContractFields();
  applyTypeRules();
  renderConditionContext();
  augmentPreview();
  decorateReportCards();

  const form = document.getElementById("case-report-form");
  form?.addEventListener("input", () => { applyTypeRules(); renderConditionContext(); setTimeout(augmentPreview, 0); });
  form?.addEventListener("change", () => { applyTypeRules(); renderConditionContext(); setTimeout(augmentPreview, 0); });
  document.addEventListener("submit", stageAuditAndVersion, true);
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.openReport || button.dataset.newVersion || button.dataset.caseReport || button.id === "new-case-report") setTimeout(prepareOpenReport, 0);
  });

  const dialog = document.getElementById("case-report-dialog");
  if (dialog) new MutationObserver(() => { if (dialog.hasAttribute("open")) prepareOpenReport(); }).observe(dialog, { attributes: true, attributeFilter: ["open"] });
  const reportList = document.getElementById("report-list");
  if (reportList) new MutationObserver(decorateReportCards).observe(reportList, { childList: true, subtree: true });

  window.PA_REPORT_INTERPRETATION_CONTRACT = Object.freeze({
    version: CONTRACT_VERSION,
    assessmentTypes: Object.keys(TYPE_DEFINITIONS),
    requiredCoreFields: ["assessmentType", "evidenceSources", "resultValidity", "interpretationLimitations", "providerInterpretation"],
    progressFields: ["baselineIndicator", "measurementMethod", "measurableGoal", "remeasurementDate"],
    familyField: "familySummary", auditField: "reviewAuditTrail",
    rightsRule: "external-results-and-official-integrations-only-for-protected-instruments"
  });
})();