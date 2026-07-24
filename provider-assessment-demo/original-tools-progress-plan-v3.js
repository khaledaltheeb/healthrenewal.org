"use strict";

(() => {
  const RELEASE = "2026.07.25-progress-plan.3";
  const STORE_VERSION = "3";
  const PLAN_SCHEMA = "pa-original-progress-plans-v3";
  const idsKey = `pa-demo-identities-v${STORE_VERSION}`;
  const activeKey = `pa-demo-active-v${STORE_VERSION}`;
  const esc = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const read = (key, fallback = null) => { try { const raw = localStorage.getItem(key); return raw === null ? fallback : JSON.parse(raw); } catch (_) { return fallback; } };
  const activeIdentity = () => {
    const identities = read(idsKey, {});
    const active = read(activeKey, null);
    if (active?.role === "provider" && identities?.[active.username]) return identities[active.username];
    return identities?.__visitor__ || null;
  };
  const storageKey = () => activeIdentity()?.uid ? `${PLAN_SCHEMA}:${activeIdentity().uid}` : null;
  const readBook = () => {
    const key = storageKey();
    const value = key ? read(key, null) : null;
    return value?.schema === PLAN_SCHEMA && value?.ownerUid === activeIdentity()?.uid ? value : { schema: PLAN_SCHEMA, release: RELEASE, ownerUid: activeIdentity()?.uid || null, updatedAt: null, plans: [] };
  };
  const writeBook = (book) => {
    const key = storageKey();
    if (!key) throw new Error("active_uid_required");
    book.schema = PLAN_SCHEMA;
    book.release = RELEASE;
    book.ownerUid = activeIdentity().uid;
    book.updatedAt = new Date().toISOString();
    localStorage.setItem(key, JSON.stringify(book));
    window.dispatchEvent(new CustomEvent("pa-original-progress-plan-saved"));
  };
  const getPlans = (caseId) => readBook().plans.filter((item) => item.caseId === caseId);
  const assessmentOptions = (caseId) => {
    const record = window.PA_ORIGINAL_PROGRESS?.findCase?.(caseId);
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
  const savePlan = (data) => {
    const identity = activeIdentity();
    if (!identity?.uid) throw new Error("active_uid_required");
    const book = readBook();
    const id = `${data.caseId}::${data.assessmentId}`;
    const previous = book.plans.find((item) => item.planId === id) || null;
    if (previous && !data.editReason?.trim()) throw new Error("edit_reason_required");
    const now = new Date().toISOString();
    const snapshot = { functionalGoal: data.functionalGoal.trim(), targetDirection: data.targetDirection, reviewDate: data.reviewDate, decisionRule: data.decisionRule.trim() };
    const next = {
      planId: id, caseId: data.caseId, assessmentId: data.assessmentId, ...snapshot,
      createdAt: previous?.createdAt || now, createdByUid: previous?.createdByUid || identity.uid,
      updatedAt: now, updatedByUid: identity.uid,
      auditTrail: [...(previous?.auditTrail || []), previous ? { event: "plan_revised", at: now, actorUid: identity.uid, reason: data.editReason.trim(), previous: { functionalGoal: previous.functionalGoal, targetDirection: previous.targetDirection, reviewDate: previous.reviewDate, decisionRule: previous.decisionRule }, next: snapshot } : { event: "plan_created", at: now, actorUid: identity.uid }]
    };
    book.plans = [next, ...book.plans.filter((item) => item.planId !== id)];
    writeBook(book);
    return next;
  };
  const formHtml = (caseId, options, existing = null) => `<form class="progress-plan-form" data-progress-plan-form="${esc(caseId)}">
    <label>الأداة الأصلية<select name="assessmentId" required>${options.map((item) => `<option value="${esc(item.id)}" ${existing?.assessmentId === item.id ? "selected" : ""}>${esc(item.title)}</option>`).join("")}</select></label>
    <label>الهدف الوظيفي<textarea name="functionalGoal" rows="2" maxlength="500" required>${esc(existing?.functionalGoal || "")}</textarea></label>
    <label>الاتجاه المتوقع<select name="targetDirection" required>${Object.entries(directionLabels).map(([value, label]) => `<option value="${value}" ${existing?.targetDirection === value ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>
    <label>موعد المراجعة<input name="reviewDate" type="date" required value="${esc(existing?.reviewDate || "")}"></label>
    <label>قاعدة القرار المهنية<textarea name="decisionRule" rows="2" maxlength="500" required placeholder="يراجع الفريق الوظيفة والسياق قبل الاستمرار أو التعديل أو الإغلاق.">${esc(existing?.decisionRule || "")}</textarea></label>
    <label ${existing ? "" : "hidden"}>سبب تعديل الخطة<input name="editReason" maxlength="240" ${existing ? "required" : ""}></label>
    <div class="dialog-actions"><button class="button primary small-button" type="submit">${existing ? "حفظ إصدار الخطة" : "إنشاء خطة المتابعة"}</button><button class="button ghost small-button" type="reset">مسح الحقول</button></div>
    <p class="muted">هذه قاعدة متابعة داخلية وليست عتبة سريرية أو معيارية. لا تعلن المنصة تحقق الهدف آليًا.</p><p class="muted" data-progress-plan-status aria-live="polite"></p></form>`;
  const renderPlans = (caseId) => {
    const panel = document.querySelector(`[data-original-progress="${CSS.escape(caseId)}"]`);
    if (!panel) return;
    let host = panel.querySelector("[data-original-progress-plans]");
    if (!host) { host = document.createElement("section"); host.className = "progress-plan-section"; host.dataset.originalProgressPlans = caseId; panel.appendChild(host); }
    const options = assessmentOptions(caseId);
    const plans = getPlans(caseId);
    const series = new Map((window.PA_ORIGINAL_PROGRESS?.buildSeriesByCaseId?.(caseId) || []).map((item) => [item.assessmentId, item]));
    const cards = plans.length ? plans.map((plan) => {
      const status = reviewStatus(plan, series.get(plan.assessmentId));
      const title = options.find((item) => item.id === plan.assessmentId)?.title || plan.assessmentId;
      return `<article class="progress-plan-card"><div><strong>${esc(title)}</strong><span class="comparability-badge ${esc(status.code)}">${esc(status.label)}</span></div><p><b>الهدف:</b> ${esc(plan.functionalGoal)}</p><p><b>الاتجاه:</b> ${esc(directionLabels[plan.targetDirection] || plan.targetDirection)}</p><p><b>المراجعة:</b> ${esc(plan.reviewDate)}</p><p><b>قاعدة القرار:</b> ${esc(plan.decisionRule)}</p><p class="muted">أحداث السجل: ${plan.auditTrail.length}</p><button class="button ghost small-button" type="button" data-edit-progress-plan="${esc(plan.planId)}">تعديل موثق</button></article>`;
    }).join("") : '<p class="muted">لا توجد خطة هدف موثقة لهذه الحالة بعد.</p>';
    host.innerHTML = `<div class="section-heading compact"><div><h4>خطط الأهداف والمراجعة</h4><p class="muted">تربط القياس الوصفي بهدف وظيفي وموعد مراجعة دون حكم سريري آلي.</p></div></div><div class="progress-plan-grid">${cards}</div>${options.length ? formHtml(caseId, options) : '<p>أضف جلسة أداة أصلية أولًا.</p>'}`;
  };
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-progress-plan-form]"); if (!form) return;
    event.preventDefault();
    try { savePlan({ caseId: form.dataset.progressPlanForm, ...Object.fromEntries(new FormData(form)) }); renderPlans(form.dataset.progressPlanForm); }
    catch (error) { const status = form.querySelector("[data-progress-plan-status]"); if (status) status.textContent = error.message === "edit_reason_required" ? "سبب التعديل إلزامي." : "تعذر حفظ الخطة."; }
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-progress-plan]"); if (!button) return;
    const plan = readBook().plans.find((item) => item.planId === button.dataset.editProgressPlan);
    const host = button.closest("[data-original-progress-plans]"); if (!plan || !host) return;
    const wrapper = document.createElement("div"); wrapper.innerHTML = formHtml(plan.caseId, assessmentOptions(plan.caseId), plan);
    host.querySelector("[data-progress-plan-form]")?.replaceWith(wrapper.firstElementChild);
  });
  const inject = () => document.querySelectorAll("[data-original-progress]").forEach((panel) => renderPlans(panel.dataset.originalProgress));
  new MutationObserver(inject).observe(document.body, { childList: true, subtree: true });
  window.addEventListener("pa-original-progress-plan-saved", inject);
  window.addEventListener("pa-original-session-context-saved", inject);
  inject();
  const style = document.createElement("style");
  style.textContent = `.progress-plan-section{margin-top:18px;border-top:1px solid var(--line,#c5e4e0);padding-top:16px}.progress-plan-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.progress-plan-card,.progress-plan-form{border:1px solid var(--line,#c5e4e0);border-radius:14px;padding:12px;background:#fff}.progress-plan-card>div{display:flex;gap:8px;justify-content:space-between;align-items:start}.progress-plan-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.progress-plan-form label{display:grid;gap:5px;font-weight:700}.progress-plan-form textarea,.progress-plan-form input,.progress-plan-form select{width:100%;font:inherit;padding:8px;border:1px solid var(--line,#c5e4e0);border-radius:9px}.progress-plan-form label:nth-child(2),.progress-plan-form label:nth-child(5),.progress-plan-form .dialog-actions,.progress-plan-form .muted{grid-column:1/-1}.comparability-badge.review_ready{background:#dff7ef;color:#075a46}.comparability-badge.context_blocked{background:#fff2d8;color:#704500}@media(max-width:700px){.progress-plan-grid,.progress-plan-form{grid-template-columns:1fr}}`;
  document.head.appendChild(style);
  window.PA_ORIGINAL_PROGRESS_PLANS = { release: RELEASE, schema: PLAN_SCHEMA, getPlans, savePlan, reviewStatus, readBook };
})();