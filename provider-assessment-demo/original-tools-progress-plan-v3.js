"use strict";

(() => {
  const RELEASE = "2026.07.25-progress-plan.4";
  const PLAN_SCHEMA = "pa-original-progress-plan-v3";
  const ASSESSMENT_PURPOSE = "progress_monitoring";
  const esc = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clean = (value) => String(value || "").trim();
  const progress = () => window.PA_ORIGINAL_PROGRESS;
  const getPlans = (caseId) => progress()?.findCase?.(caseId)?.originalProgressPlans || [];
  const assessmentOptions = (caseId) => {
    const record = progress()?.findCase?.(caseId);
    const ids = [...new Set((record?.sessions || []).map((item) => item.assessmentId).filter(Boolean))];
    return ids.map((id) => ({ id, title: window.PA_DEMO_DATA?.explorers?.find((item) => item.id === id)?.title || id }));
  };
  const directionLabels = { increase: "زيادة الإشارة الوصفية", decrease: "انخفاض الإشارة الوصفية", stable: "ثبات الإشارة الوصفية", observe: "مراقبة دون اتجاه مسبق" };
  const reviewStatus = (plan, series) => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const due = plan.reviewDate ? new Date(`${plan.reviewDate}T00:00:00`) : null;
    if (!series || series.sessions.length < 2) return { code: "baseline_only", label: "بانتظار قياس متابعة" };
    if (!series.comparability?.interpretable) return { code: "context_blocked", label: "المراجعة محجوبة لاختلاف السياق" };
    if (due && due > today) return { code: "scheduled", label: "المقارنة متاحة والموعد لاحق" };
    return { code: "review_ready", label: "جاهز للمراجعة المهنية" };
  };
  const snapshotFrom = (data) => ({
    assessmentPurpose: ASSESSMENT_PURPOSE,
    functionalGoal: clean(data.functionalGoal),
    familyPriority: clean(data.familyPriority),
    providerObservation: clean(data.providerObservation),
    measurementContext: clean(data.measurementContext),
    targetDirection: data.targetDirection,
    reviewDate: data.reviewDate,
    reviewOwner: clean(data.reviewOwner),
    decisionRule: clean(data.decisionRule),
    interpretationLimit: clean(data.interpretationLimit)
  });
  const validatePlan = (data, record, previous) => {
    const allowedAssessments = new Set((record.sessions || []).map((item) => item.assessmentId).filter(Boolean));
    if (!allowedAssessments.has(data.assessmentId)) throw new Error("assessment_not_in_case");
    if (previous && previous.assessmentId !== data.assessmentId) throw new Error("assessment_change_forbidden");
    if (!directionLabels[data.targetDirection]) throw new Error("invalid_direction");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data.reviewDate || "") || !Number.isFinite(Date.parse(`${data.reviewDate}T00:00:00`))) throw new Error("invalid_review_date");
    const required = ["functionalGoal", "familyPriority", "providerObservation", "measurementContext", "reviewOwner", "decisionRule", "interpretationLimit"];
    if (required.some((key) => clean(data[key]).length < 8)) throw new Error("documentation_required");
    if (previous && clean(data.editReason).length < 5) throw new Error("edit_reason_required");
  };
  const savePlan = (data) => {
    const store = progress()?.activeStore?.();
    const identity = progress()?.activeIdentity?.();
    const record = store?.cases?.find((item) => item.caseId === data.caseId);
    if (!store || !identity?.uid || !record) throw new Error("active_case_required");
    const plans = Array.isArray(record.originalProgressPlans) ? record.originalProgressPlans : [];
    const id = `${data.caseId}::${data.assessmentId}`;
    const previous = plans.find((item) => item.planId === id) || null;
    validatePlan(data, record, previous);
    const now = new Date().toISOString();
    const snapshot = snapshotFrom(data);
    const event = previous
      ? { event: "plan_revised", at: now, actorUid: identity.uid, reason: clean(data.editReason), previous: snapshotFrom(previous), next: snapshot }
      : { event: "plan_created", at: now, actorUid: identity.uid, next: snapshot };
    const next = {
      schema: PLAN_SCHEMA, release: RELEASE, planId: id, caseId: data.caseId, assessmentId: data.assessmentId, ...snapshot,
      createdAt: previous?.createdAt || now, createdByUid: previous?.createdByUid || identity.uid,
      updatedAt: now, updatedByUid: identity.uid,
      auditTrail: [...(previous?.auditTrail || []), event].slice(-200)
    };
    record.originalProgressPlans = [next, ...plans.filter((item) => item.planId !== id)];
    record.updatedAt = now;
    progress().persistStore(store);
    window.dispatchEvent(new CustomEvent("pa-original-progress-plan-saved", { detail: { caseId: data.caseId, planId: id } }));
    return next;
  };
  const exportPlans = (caseId) => {
    const identity = progress()?.activeIdentity?.();
    const record = progress()?.findCase?.(caseId);
    if (!identity?.uid || !record) return;
    const payload = {
      schema: "pa-original-progress-plan-export-v3", release: RELEASE, ownerUid: identity.uid, caseId,
      generatedAt: new Date().toISOString(), assessmentPurpose: ASSESSMENT_PURPOSE,
      interpretationBoundary: "human-review-required-not-diagnostic-not-norm-referenced",
      purposeBoundary: "progress-monitoring-not-screening-not-diagnostic-not-standalone-functional-assessment",
      backupLocation: "embedded-in-case-record", plans: getPlans(caseId)
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${caseId}-original-progress-plans.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  };
  const formHtml = (caseId, options, existing = null) => {
    const allowedOptions = existing ? options.filter((item) => item.id === existing.assessmentId) : options;
    const displayOptions = allowedOptions.length ? allowedOptions : [{ id: existing?.assessmentId || "", title: existing?.assessmentId || "—" }];
    return `<form class="progress-plan-form" data-progress-plan-form="${esc(caseId)}">
      <div class="notice purpose-boundary"><strong>نوع الاستخدام: متابعة التقدم.</strong> ليست هذه الخطة مسحًا أو فرزًا، ولا تقييمًا تشخيصيًا، ولا تقييمًا وظيفيًا مستقلًا. تُفسر مع سؤال الإحالة والتقييم الوظيفي ومصادر الأسرة ومقدم الخدمة.</div>
      <label>الأداة الأصلية<select name="assessmentId" required>${displayOptions.map((item) => `<option value="${esc(item.id)}" ${existing?.assessmentId === item.id ? "selected" : ""}>${esc(item.title)}</option>`).join("")}</select></label>
      <label>الهدف الوظيفي<textarea name="functionalGoal" rows="2" minlength="8" maxlength="500" required>${esc(existing?.functionalGoal || "")}</textarea></label>
      <label>أولوية الأسرة أو الشخص<textarea name="familyPriority" rows="2" minlength="8" maxlength="500" required>${esc(existing?.familyPriority || "")}</textarea></label>
      <label>ملاحظة مقدم الخدمة<textarea name="providerObservation" rows="2" minlength="8" maxlength="500" required>${esc(existing?.providerObservation || "")}</textarea></label>
      <label>سياق القياس وشروط المقارنة<textarea name="measurementContext" rows="2" minlength="8" maxlength="500" required placeholder="البيئة، المجيب، طريقة التطبيق، مستوى الدعم، والتهيئات.">${esc(existing?.measurementContext || "")}</textarea></label>
      <label>الاتجاه المتوقع<select name="targetDirection" required>${Object.entries(directionLabels).map(([value, label]) => `<option value="${value}" ${existing?.targetDirection === value ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>
      <label>موعد المراجعة<input name="reviewDate" type="date" required value="${esc(existing?.reviewDate || "")}"></label>
      <label>مسؤول المراجعة<input name="reviewOwner" minlength="8" maxlength="220" required value="${esc(existing?.reviewOwner || "")}" placeholder="الدور أو اسم عضو الفريق المخول"></label>
      <label>قاعدة القرار المهنية<textarea name="decisionRule" rows="2" minlength="8" maxlength="500" required placeholder="يراجع الفريق الوظيفة والسياق قبل الاستمرار أو التعديل أو الإغلاق.">${esc(existing?.decisionRule || "")}</textarea></label>
      <label>حدود التفسير<textarea name="interpretationLimit" rows="2" minlength="8" maxlength="500" required placeholder="ما الذي لا يمكن استنتاجه من هذه السلسلة؟">${esc(existing?.interpretationLimit || "")}</textarea></label>
      <label ${existing ? "" : "hidden"}>سبب تعديل الخطة<input name="editReason" minlength="5" maxlength="240" ${existing ? "required" : ""}></label>
      <div class="dialog-actions"><button class="button primary small-button" type="submit">${existing ? "حفظ إصدار الخطة" : "إنشاء خطة المتابعة"}</button><button class="button ghost small-button" type="reset">مسح الحقول</button></div>
      <p class="muted">لا تعلن المنصة تحقق الهدف أو التحسن السريري آليًا. اختلاف السياق أو المجيب أو طريقة التطبيق قد يمنع المقارنة، ولا تُحوّل الإشارة الوصفية إلى درجة معيارية أو تشخيص.</p><p class="muted" data-progress-plan-status aria-live="polite"></p></form>`;
  };
  const renderPlans = (caseId) => {
    const panel = document.querySelector(`[data-original-progress="${CSS.escape(caseId)}"]`);
    if (!panel) return;
    let host = panel.querySelector("[data-original-progress-plans]");
    if (!host) { host = document.createElement("section"); host.className = "progress-plan-section"; host.dataset.originalProgressPlans = caseId; panel.appendChild(host); }
    const options = assessmentOptions(caseId);
    const plans = getPlans(caseId);
    const series = new Map((progress()?.buildSeriesByCaseId?.(caseId) || []).map((item) => [item.assessmentId, item]));
    const cards = plans.length ? plans.map((plan) => {
      const status = reviewStatus(plan, series.get(plan.assessmentId));
      const title = options.find((item) => item.id === plan.assessmentId)?.title || plan.assessmentId;
      return `<article class="progress-plan-card"><div><strong>${esc(title)}</strong><span class="comparability-badge ${esc(status.code)}">${esc(status.label)}</span></div><p><b>الغرض:</b> متابعة التقدم</p><p><b>الهدف:</b> ${esc(plan.functionalGoal)}</p><p><b>أولوية الأسرة أو الشخص:</b> ${esc(plan.familyPriority || "غير موثقة")}</p><p><b>ملاحظة مقدم الخدمة:</b> ${esc(plan.providerObservation || "غير موثقة")}</p><p><b>سياق القياس:</b> ${esc(plan.measurementContext || "غير موثق")}</p><p><b>الاتجاه:</b> ${esc(directionLabels[plan.targetDirection] || plan.targetDirection)}</p><p><b>المراجعة:</b> ${esc(plan.reviewDate)} — ${esc(plan.reviewOwner || "لم يحدد المسؤول")}</p><p><b>قاعدة القرار:</b> ${esc(plan.decisionRule)}</p><p><b>حدود التفسير:</b> ${esc(plan.interpretationLimit || "غير موثقة")}</p><p class="muted">أحداث السجل: ${plan.auditTrail.length}</p><button class="button ghost small-button" type="button" data-edit-progress-plan="${esc(plan.planId)}">تعديل موثق</button></article>`;
    }).join("") : '<p class="muted">لا توجد خطة هدف موثقة لهذه الحالة بعد.</p>';
    host.innerHTML = `<div class="section-heading compact"><div><h4>خطط الأهداف والمراجعة</h4><p class="muted">تربط متابعة التقدم بهدف وظيفي وأولوية الأسرة وملاحظة مقدم الخدمة وسياق قابل للمقارنة، وتدخل ضمن نسخة الحالة الاحتياطية.</p></div><button class="button ghost small-button" type="button" data-export-progress-plans="${esc(caseId)}">تصدير الخطط</button></div><div class="progress-plan-grid">${cards}</div>${options.length ? formHtml(caseId, options) : '<p>أضف جلسة أداة أصلية أولًا.</p>'}`;
  };
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-progress-plan-form]"); if (!form) return;
    event.preventDefault();
    try { savePlan({ caseId: form.dataset.progressPlanForm, ...Object.fromEntries(new FormData(form)) }); renderPlans(form.dataset.progressPlanForm); }
    catch (error) { const status = form.querySelector("[data-progress-plan-status]"); if (status) status.textContent = error.message === "edit_reason_required" ? "سبب التعديل إلزامي." : error.message === "documentation_required" ? "أكمل أولوية الأسرة وملاحظة مقدم الخدمة وسياق القياس ومسؤول المراجعة وحدود التفسير." : "تحقق من الأداة والتاريخ والحقول المطلوبة."; }
  });
  document.addEventListener("click", (event) => {
    const exportButton = event.target.closest("[data-export-progress-plans]");
    if (exportButton) { exportPlans(exportButton.dataset.exportProgressPlans); return; }
    const button = event.target.closest("[data-edit-progress-plan]"); if (!button) return;
    const host = button.closest("[data-original-progress-plans]");
    const caseId = host?.dataset.originalProgressPlans;
    const plan = caseId ? getPlans(caseId).find((item) => item.planId === button.dataset.editProgressPlan) : null;
    if (!plan || !host) return;
    const wrapper = document.createElement("div"); wrapper.innerHTML = formHtml(plan.caseId, assessmentOptions(plan.caseId), plan);
    host.querySelector("[data-progress-plan-form]")?.replaceWith(wrapper.firstElementChild);
  });
  const injectNew = () => document.querySelectorAll("[data-original-progress]").forEach((panel) => { if (!panel.querySelector("[data-original-progress-plans]")) renderPlans(panel.dataset.originalProgress); });
  const refreshAll = () => document.querySelectorAll("[data-original-progress]").forEach((panel) => renderPlans(panel.dataset.originalProgress));
  new MutationObserver(injectNew).observe(document.body, { childList: true, subtree: true });
  window.addEventListener("pa-original-progress-plan-saved", refreshAll);
  window.addEventListener("pa-original-session-context-saved", refreshAll);
  injectNew();
  const style = document.createElement("style");
  style.textContent = `.progress-plan-section{margin-top:18px;border-top:1px solid var(--line,#c5e4e0);padding-top:16px}.progress-plan-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.progress-plan-card,.progress-plan-form{border:1px solid var(--line,#c5e4e0);border-radius:14px;padding:12px;background:#fff}.progress-plan-card>div{display:flex;gap:8px;justify-content:space-between;align-items:start}.progress-plan-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.progress-plan-form label{display:grid;gap:5px;font-weight:700}.progress-plan-form textarea,.progress-plan-form input,.progress-plan-form select{width:100%;font:inherit;padding:8px;border:1px solid var(--line,#c5e4e0);border-radius:9px}.progress-plan-form .purpose-boundary,.progress-plan-form label:nth-of-type(2),.progress-plan-form label:nth-of-type(3),.progress-plan-form label:nth-of-type(4),.progress-plan-form label:nth-of-type(5),.progress-plan-form label:nth-of-type(9),.progress-plan-form label:nth-of-type(10),.progress-plan-form .dialog-actions,.progress-plan-form .muted{grid-column:1/-1}.comparability-badge.review_ready{background:#dff7ef;color:#075a46}.comparability-badge.context_blocked{background:#fff2d8;color:#704500}@media(max-width:700px){.progress-plan-grid,.progress-plan-form{grid-template-columns:1fr}}`;
  document.head.appendChild(style);
  window.PA_ORIGINAL_PROGRESS_PLANS = { release: RELEASE, schema: PLAN_SCHEMA, assessmentPurpose: ASSESSMENT_PURPOSE, getPlans, savePlan, reviewStatus, exportPlans, validatePlan };
})();