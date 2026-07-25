"use strict";

(() => {
  const RELEASE = "2026.07.25-v231";
  const SCHEMA = "institutional-assessment-contract-v220";
  const PLAN_SCHEMA = "pa-original-progress-plan-v3";
  const LICENSE = "original-license-safe-tools-only";
  const ALIASES = Object.freeze({
    "development-pathway": "development-overview",
    "communication-pathway": "communication-participation",
    "attention-pathway": "attention-executive",
    "learning-pathway": "learning-access",
    "adaptive-pathway": "adaptive-daily-living",
    "sensory-pathway": "sensory-regulation",
    "motor-pathway": "motor-participation",
    "emotional-pathway": "emotional-regulation"
  });
  const DIRECTIONS = Object.freeze({ increase: "زيادة الإشارة الوصفية", decrease: "انخفاض الإشارة الوصفية", stable: "ثبات الإشارة الوصفية", observe: "مراقبة دون اتجاه مسبق" });
  const clean = (value) => String(value || "").trim();
  const esc = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clone = (value) => value === undefined ? undefined : JSON.parse(JSON.stringify(value));
  const progress = () => window.PA_ORIGINAL_PROGRESS;
  const identity = () => progress()?.activeIdentity?.() || null;
  const store = () => progress()?.activeStore?.() || null;
  const findCase = (caseId) => progress()?.findCase?.(caseId) || null;
  const persist = (value) => progress()?.persistStore?.(value);
  const tool = (assessmentId) => window.PA_DEMO_DATA?.explorers?.find((item) => item.id === (ALIASES[assessmentId] || assessmentId)) || null;

  function professionalContract(form) {
    const fd = new FormData(form);
    return {
      referralPurpose: clean(fd.get("referralPurpose")), decisionUse: String(fd.get("decisionUseV220") || ""), validityStatus: String(fd.get("validityStatus") || ""),
      completionStatus: String(fd.get("completionStatus") || ""), normativeFit: String(fd.get("normativeFit") || ""), crossSourceAgreement: String(fd.get("crossSourceAgreement") || ""),
      consentStatus: String(fd.get("consentV220") || ""), riskReview: String(fd.get("riskReview") || ""), reviewer: clean(fd.get("reviewerV220")), reviewDate: String(fd.get("reviewDateV220") || ""),
      sourcesSettings: clean(fd.get("sourcesSettings")), accommodationsDeviations: clean(fd.get("accommodationsDeviations")), functionalSynthesis: clean(fd.get("functionalSynthesis")),
      recommendations: clean(fd.get("recommendationsV220")), limitations: clean(fd.get("limitationsV220"))
    };
  }

  function auditProfessional(contract) {
    const gates = [
      ["الغرض", clean(contract.referralPurpose).length >= 8], ["استخدام القرار", Boolean(contract.decisionUse)], ["المصادر والبيئات", clean(contract.sourcesSettings).length >= 10],
      ["الموافقة والسلامة", Boolean(contract.consentStatus) && contract.consentStatus !== "missing" && Boolean(contract.riskReview) && contract.riskReview !== "not_reviewed"],
      ["اكتمال التطبيق وصلاحية النتيجة", Boolean(contract.completionStatus) && Boolean(contract.validityStatus)], ["النسخة والمعايير", Boolean(contract.normativeFit)],
      ["التكييفات والانحرافات", clean(contract.accommodationsDeviations).length >= 10], ["التركيب الوظيفي", clean(contract.functionalSynthesis).length >= 10],
      ["التوصيات والحدود", clean(contract.recommendations).length >= 10 && clean(contract.limitations).length >= 10], ["المراجع وموعد المراجعة", clean(contract.reviewer).length >= 3 && Boolean(contract.reviewDate)]
    ];
    const passed = gates.filter(([, ok]) => ok).length;
    return { score: passed * 10, passed, total: 10, gates, status: passed === 10 ? "complete" : passed >= 8 ? "review" : "incomplete" };
  }

  function renderQuality(form) {
    const box = document.getElementById("professional-v220-quality");
    if (!box) return;
    const audit = auditProfessional(professionalContract(form));
    box.innerHTML = `<strong>${audit.score}%</strong><span>اكتمال عقد التوثيق — ${audit.passed}/10 بوابات. يمكن حفظه كمسودة، ولا يعد مكتملًا مؤسسيًا قبل 100%.</span>`;
  }

  function prepareProfessionalForm() {
    const form = document.getElementById("professional-record-form");
    const fieldset = form?.querySelector("[data-institutional-professional-v220]");
    if (!form || !fieldset || fieldset.dataset.compatV231) return;
    fieldset.dataset.compatV231 = "true";
    const note = document.createElement("p");
    note.id = "institutional-v231-draft-note";
    note.className = "professional-form-note";
    note.textContent = "يمكن حفظ السجل كمسودة ناقصة. لا يصبح مكتملًا مؤسسيًا حتى استيفاء الغرض والصلاحية والمصادر والحدود والمراجعة.";
    fieldset.querySelector("legend")?.after(note);
    fieldset.querySelectorAll("input[required],select[required],textarea[required]").forEach((control) => { control.required = false; control.setAttribute("aria-describedby", note.id); });
    ["decisionUseV220", "validityStatus", "completionStatus", "normativeFit", "crossSourceAgreement", "consentV220", "riskReview"].forEach((name) => {
      const select = form.elements[name];
      if (!select) return;
      const blank = [...select.options].find((option) => option.value === "");
      if (blank) blank.textContent = "غير موثق بعد"; else select.insertBefore(new Option("غير موثق بعد", ""), select.firstChild);
      select.value = "";
    });
    for (const eventName of ["input", "change"]) form.addEventListener(eventName, () => queueMicrotask(() => renderQuality(form)));
    renderQuality(form);
  }

  let pending = null;
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("#professional-record-form");
    if (!form) return;
    const beforeStore = store();
    const fd = new FormData(form);
    pending = {
      caseId: String(fd.get("caseId") || ""), contract: professionalContract(form),
      before: new Map((beforeStore?.cases || []).flatMap((caseRecord) => (caseRecord.professionalAssessments || []).map((record) => [record.recordId, {
        institutionalV220: clone(record.institutionalV220), documentationQuality: clone(record.documentationQuality), auditTrail: clone(record.auditTrail)
      }])) )
    };
    setTimeout(() => {
      const job = pending; pending = null;
      const currentStore = store();
      if (!job || !currentStore) return;
      for (const caseRecord of currentStore.cases || []) for (const record of caseRecord.professionalAssessments || []) {
        const previous = job.before.get(record.recordId);
        if (!previous) continue;
        for (const key of ["institutionalV220", "documentationQuality", "auditTrail"]) {
          if (previous[key] === undefined) delete record[key]; else record[key] = previous[key];
        }
      }
      const currentCase = currentStore.cases?.find((item) => item.caseId === job.caseId);
      const created = (currentCase?.professionalAssessments || []).filter((record) => !job.before.has(record.recordId)).sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
      if (!created) { persist(currentStore); return; }
      const contract = { ...job.contract, schema: SCHEMA, release: RELEASE, capturedAt: new Date().toISOString(), documentationState: "progressive_draft_allowed" };
      created.institutionalV220 = contract;
      created.documentationQuality = auditProfessional(contract);
      created.auditTrail ||= [];
      const last = created.auditTrail.at(-1);
      if (last?.event === "institutional_contract_attached") Object.assign(last, { qualityScore: created.documentationQuality.score, release: RELEASE });
      else created.auditTrail.push({ event: "institutional_contract_attached", at: new Date().toISOString(), byUid: identity()?.uid || "local", qualityScore: created.documentationQuality.score, release: RELEASE });
      persist(currentStore);
      window.PA_V220_HOOKS?.decorateProfessionalRecords?.();
    }, 0);
  }, true);

  const optionsFor = (caseId) => [...new Set((findCase(caseId)?.sessions || []).map((session) => session.assessmentId).filter((id) => tool(id)))].map((id) => ({ id, title: tool(id)?.title || id }));
  const hasLegacySession = (caseId) => (findCase(caseId)?.sessions || []).some((session) => ALIASES[session.assessmentId] && tool(session.assessmentId));
  const plansFor = (caseId) => findCase(caseId)?.originalProgressPlans || [];
  const snapshot = (data) => ({ assessmentPurpose: "progress_monitoring", licenseBoundary: LICENSE, functionalGoal: clean(data.functionalGoal), familyPriority: clean(data.familyPriority), providerObservation: clean(data.providerObservation), measurementContext: clean(data.measurementContext), targetDirection: data.targetDirection, reviewDate: data.reviewDate, reviewOwner: clean(data.reviewOwner), decisionRule: clean(data.decisionRule), interpretationLimit: clean(data.interpretationLimit) });

  function saveLegacyPlan(data) {
    const currentStore = store();
    const active = identity();
    const record = currentStore?.cases?.find((item) => item.caseId === data.caseId);
    if (!currentStore || !active?.uid || !record || !ALIASES[data.assessmentId] || !tool(data.assessmentId)) throw new Error("legacy_original_required");
    if (!(record.sessions || []).some((session) => session.assessmentId === data.assessmentId)) throw new Error("assessment_not_in_case");
    if (!DIRECTIONS[data.targetDirection]) throw new Error("invalid_direction");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data.reviewDate || "") || !Number.isFinite(Date.parse(`${data.reviewDate}T00:00:00`))) throw new Error("invalid_review_date");
    if (["functionalGoal", "familyPriority", "providerObservation", "measurementContext", "reviewOwner", "decisionRule", "interpretationLimit"].some((key) => clean(data[key]).length < 8)) throw new Error("documentation_required");
    const plans = Array.isArray(record.originalProgressPlans) ? record.originalProgressPlans : [];
    const planId = `${data.caseId}::${data.assessmentId}`;
    const previous = plans.find((item) => item.planId === planId) || null;
    if (previous && clean(data.editReason).length < 5) throw new Error("edit_reason_required");
    const nextSnapshot = snapshot(data);
    if (previous && JSON.stringify(snapshot(previous)) === JSON.stringify(nextSnapshot)) throw new Error("no_documented_change");
    const at = new Date().toISOString();
    const actor = { actorUid: active.uid, actorRole: active.role || "visitor" };
    const auditEvent = previous ? { event: "plan_revised", at, ...actor, reason: clean(data.editReason), previous: snapshot(previous), next: nextSnapshot } : { event: "plan_created", at, ...actor, next: nextSnapshot };
    const next = { schema: PLAN_SCHEMA, release: RELEASE, planId, caseId: data.caseId, assessmentId: data.assessmentId, ...nextSnapshot, createdAt: previous?.createdAt || at, createdByUid: previous?.createdByUid || active.uid, createdByRole: previous?.createdByRole || active.role || "visitor", updatedAt: at, updatedByUid: active.uid, updatedByRole: active.role || "visitor", auditTrail: [...(previous?.auditTrail || []), auditEvent] };
    record.originalProgressPlans = [next, ...plans.filter((item) => item.planId !== planId)];
    record.updatedAt = at;
    persist(currentStore);
    return next;
  }

  function statusFor(plan) {
    const series = progress()?.buildSeriesByCaseId?.(plan.caseId)?.find((item) => item.assessmentId === plan.assessmentId);
    if (!series || series.sessions.length < 2) return { code: "baseline_only", label: "بانتظار قياس متابعة" };
    if (!series.comparability?.interpretable) return { code: "context_blocked", label: "المراجعة محجوبة لاختلاف السياق" };
    const due = plan.reviewDate ? new Date(`${plan.reviewDate}T00:00:00`) : null;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    return due && due > today ? { code: "scheduled", label: "المقارنة متاحة والموعد لاحق" } : { code: "review_ready", label: "جاهز للمراجعة المهنية" };
  }

  function formHtml(caseId, options, existing = null) {
    const displayed = existing ? options.filter((item) => item.id === existing.assessmentId) : options;
    const finalOptions = displayed.length ? displayed : [{ id: existing?.assessmentId || "", title: tool(existing?.assessmentId)?.title || existing?.assessmentId || "—" }];
    return `<form class="progress-plan-form" data-progress-plan-form="${esc(caseId)}" data-v231-legacy-plan="true"><div class="notice purpose-boundary"><strong>نوع الاستخدام: متابعة التقدم.</strong> توافق مع المعرفات الأصلية التاريخية فقط؛ الأدوات المهنية المحمية مستبعدة.</div>
      <label>الأداة الأصلية<select name="assessmentId" required>${finalOptions.map((item) => `<option value="${esc(item.id)}" ${existing?.assessmentId === item.id ? "selected" : ""}>${esc(item.title)}</option>`).join("")}</select></label>
      ${[["functionalGoal","الهدف الوظيفي"],["familyPriority","أولوية الأسرة أو الشخص"],["providerObservation","ملاحظة مقدم الخدمة"],["measurementContext","سياق القياس وشروط المقارنة"],["decisionRule","قاعدة القرار المهنية"],["interpretationLimit","حدود التفسير"]].map(([name,label]) => `<label>${label}<textarea name="${name}" rows="2" minlength="8" maxlength="500" required>${esc(existing?.[name] || "")}</textarea></label>`).join("")}
      <label>الاتجاه المتوقع<select name="targetDirection" required>${Object.entries(DIRECTIONS).map(([value, label]) => `<option value="${value}" ${existing?.targetDirection === value ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>
      <label>موعد المراجعة<input name="reviewDate" type="date" required value="${esc(existing?.reviewDate || "")}"></label><label>مسؤول المراجعة<input name="reviewOwner" minlength="8" maxlength="220" required value="${esc(existing?.reviewOwner || "")}"></label>
      <label ${existing ? "" : "hidden"}>سبب تعديل الخطة<input name="editReason" minlength="5" maxlength="240" ${existing ? "required" : ""}></label><div class="dialog-actions"><button class="button primary small-button" type="submit">${existing ? "حفظ إصدار الخطة" : "إنشاء خطة المتابعة"}</button></div><p class="muted" data-progress-plan-status aria-live="polite"></p></form>`;
  }

  function cardsHtml(caseId) {
    return plansFor(caseId).filter((plan) => ALIASES[plan.assessmentId]).map((plan) => {
      const status = statusFor(plan);
      return `<article class="progress-plan-card" data-v231-legacy-card="${esc(plan.planId)}"><div><strong>${esc(tool(plan.assessmentId)?.title || plan.assessmentId)}</strong><span class="comparability-badge ${esc(status.code)}">${esc(status.label)}</span></div><p><b>الهدف:</b> ${esc(plan.functionalGoal)}</p><p><b>سياق القياس:</b> ${esc(plan.measurementContext)}</p><p><b>المراجعة:</b> ${esc(plan.reviewDate)} — ${esc(plan.reviewOwner)}</p><p><b>حدود التفسير:</b> ${esc(plan.interpretationLimit)}</p><p class="muted">أحداث السجل: ${plan.auditTrail?.length || 0}</p><button class="button ghost small-button" type="button" data-edit-progress-plan="${esc(plan.planId)}">تعديل موثق</button></article>`;
    }).join("");
  }

  function renderLegacy(caseId, editing = null) {
    const panel = document.querySelector(`[data-original-progress="${CSS.escape(caseId)}"]`);
    const options = optionsFor(caseId);
    if (!panel || !options.length) return;
    let host = panel.querySelector("[data-original-progress-plans]");
    if (!host) { host = document.createElement("section"); host.className = "progress-plan-section"; host.dataset.originalProgressPlans = caseId; panel.appendChild(host); }
    const currentCards = [...host.querySelectorAll(".progress-plan-card:not([data-v231-legacy-card])")].map((node) => node.outerHTML).join("");
    host.dataset.v231LegacyHost = "true";
    host.innerHTML = `<div class="section-heading compact"><div><h4>خطط الأهداف والمراجعة</h4><p class="muted">توافق آمن مع جلسات الأدوات الأصلية التاريخية، دون فتح أدوات محمية.</p></div><button class="button ghost small-button" type="button" data-export-progress-plans="${esc(caseId)}">تصدير الخطط</button></div><div class="progress-plan-grid">${currentCards}${cardsHtml(caseId) || '<p class="muted">لا توجد خطة موثقة بعد.</p>'}</div>${formHtml(caseId, options, editing)}`;
  }

  function ensureLegacyPanels(force = false) {
    if (!progress()?.findCase || !window.PA_DEMO_DATA?.explorers) return;
    document.querySelectorAll("[data-original-progress]").forEach((panel) => {
      const caseId = panel.dataset.originalProgress;
      if (!hasLegacySession(caseId)) return;
      const host = panel.querySelector("[data-original-progress-plans]");
      if (!force && host?.dataset.v231LegacyHost === "true") return;
      const form = panel.querySelector("[data-progress-plan-form]");
      const hasLegacy = form && [...form.elements.assessmentId?.options || []].some((option) => ALIASES[option.value]);
      if (force || !hasLegacy) renderLegacy(caseId);
    });
  }

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-progress-plan-form]");
    const assessmentId = form?.elements.assessmentId?.value;
    if (!form || !ALIASES[assessmentId]) return;
    event.preventDefault(); event.stopImmediatePropagation();
    try { saveLegacyPlan({ caseId: form.dataset.progressPlanForm, ...Object.fromEntries(new FormData(form)) }); renderLegacy(form.dataset.progressPlanForm); }
    catch (error) {
      const messages = { edit_reason_required: "سبب التعديل إلزامي.", documentation_required: "أكمل الحقول المهنية المطلوبة.", no_documented_change: "لم يتغير محتوى الخطة.", legacy_original_required: "المعرف التاريخي غير معتمد.", invalid_review_date: "تحقق من تاريخ المراجعة." };
      const status = form.querySelector("[data-progress-plan-status]"); if (status) status.textContent = messages[error.message] || "تعذر حفظ الخطة.";
    }
  }, true);

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-progress-plan]");
    const assessmentId = String(button?.dataset.editProgressPlan || "").split("::").at(-1);
    if (!button || !ALIASES[assessmentId]) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const caseId = button.closest("[data-original-progress-plans]")?.dataset.originalProgressPlans;
    const plan = caseId ? plansFor(caseId).find((item) => item.planId === button.dataset.editProgressPlan) : null;
    if (plan) renderLegacy(caseId, plan);
  }, true);

  new MutationObserver(() => { prepareProfessionalForm(); ensureLegacyPanels(); }).observe(document.documentElement, { childList: true, subtree: true });
  prepareProfessionalForm(); ensureLegacyPanels();
  window.addEventListener("pa-original-progress-plan-saved", () => setTimeout(() => ensureLegacyPanels(true), 0));
  window.addEventListener("pa-original-session-context-saved", () => setTimeout(() => ensureLegacyPanels(true), 0));
  window.PA_INSTITUTIONAL_COMPAT_V231 = { release: RELEASE, legacyToolAliases: ALIASES, auditProfessional, saveLegacyPlan, ensureLegacyPanels };
})();
