"use strict";

import { RELEASE, SCHEMA, data, esc, now, uid, currentStore, persist, notify, openDialog, closeDialog } from "./institutional-contract-v220-core.js";

export function auditProfessionalRecord(record) {
  const x = record.institutionalV220 || {};
  const gates = [
    ["الغرض", !!x.referralPurpose], ["استخدام القرار", !!x.decisionUse], ["المصادر والبيئات", (x.sourcesSettings || "").length >= 10],
    ["الموافقة", x.consentStatus && x.consentStatus !== "missing"], ["السلامة", x.riskReview && x.riskReview !== "not_reviewed"],
    ["النسخة والمعايير", !!x.normativeFit], ["الصلاحية", !!x.validityStatus], ["التكييفات والانحرافات", (x.accommodationsDeviations || "").length >= 10],
    ["التركيب الوظيفي", (x.functionalSynthesis || "").length >= 10], ["التوصيات والمراجعة", (x.recommendations || "").length >= 10 && !!x.reviewDate]
  ];
  const passed = gates.filter(([,ok])=>ok).length;
  return { score: passed * 10, passed, total: gates.length, gates, status: passed === 10 ? "complete" : passed >= 8 ? "review" : "incomplete" };
}

export function renderProfessionalFormQuality(form) {
  const box = document.getElementById("professional-v220-quality");
  if (!box) return;
  const fd = new FormData(form);
  const fake = { institutionalV220: {
    referralPurpose: fd.get("referralPurpose"), decisionUse: fd.get("decisionUseV220"), validityStatus: fd.get("validityStatus"),
    normativeFit: fd.get("normativeFit"), consentStatus: fd.get("consentV220"), riskReview: fd.get("riskReview"),
    sourcesSettings: fd.get("sourcesSettings"), accommodationsDeviations: fd.get("accommodationsDeviations"),
    functionalSynthesis: fd.get("functionalSynthesis"), recommendations: fd.get("recommendationsV220"), reviewDate: fd.get("reviewDateV220")
  }};
  const audit = auditProfessionalRecord(fake);
  box.innerHTML = `<strong>${audit.score}%</strong><span>اكتمال عقد التوثيق — ${audit.passed}/${audit.total} بوابات</span>`;
}

export function getPlans() {
  return (currentStore()?.cases || []).flatMap((caseRecord) => (caseRecord.assessmentPlans || []).map((plan) => ({...plan, caseAlias: caseRecord.alias})));
}

export function auditPlan(plan) {
  const gates = [
    ["سؤال واضح", (plan.referralQuestion || "").length >= 15],
    ["قرار محدد", !!plan.decisionUse],
    ["مصدران على الأقل", (plan.sources || []).length >= 2],
    ["سياقان على الأقل", (plan.settings || []).length >= 2 || plan.decisionUse === "safety_review"],
    ["اللغة والإتاحة", (plan.languageContext || "").length >= 10 && (plan.accessibility || "").length >= 10],
    ["الموافقة والمشاركة", plan.consentStatus !== "missing" && plan.assentStatus !== "not_obtained"],
    ["السلامة", !["", "not_reviewed"].includes(plan.safetyReview)],
    ["اختيار مبرر", ((plan.explorerIds || []).length + (plan.professionalCategories || []).length) >= 1 && (plan.rationale || "").length >= 15],
    ["حدود وتوصيات", (plan.exclusions || "").length >= 10 && (plan.followUp || "").length >= 10],
    ["مالك ومراجعة", !!plan.reviewer && !!plan.reviewDate]
  ];
  const passed = gates.filter(([,ok])=>ok).length;
  return { score: passed * 10, passed, total: 10, gates, warnings: gates.filter(([,ok])=>!ok).map(([name])=>name), status: passed === 10 ? "ready" : passed >= 8 ? "review" : "incomplete" };
}

export function readPlanForm(form) {
  const fd = new FormData(form);
  return {
    caseId: String(fd.get("caseId") || ""),
    decisionUse: String(fd.get("decisionUse") || ""),
    planStatus: String(fd.get("planStatus") || "draft"),
    reviewDate: String(fd.get("reviewDate") || ""),
    referralQuestion: String(fd.get("referralQuestion") || "").trim(),
    targetOutcomes: String(fd.get("targetOutcomes") || "").trim(),
    sources: fd.getAll("sources").map(String), settings: fd.getAll("settings").map(String),
    languageContext: String(fd.get("languageContext") || "").trim(), accessibility: String(fd.get("accessibility") || "").trim(),
    consentStatus: String(fd.get("consentStatus") || ""), assentStatus: String(fd.get("assentStatus") || ""), safetyReview: String(fd.get("safetyReview") || ""),
    reviewer: String(fd.get("reviewer") || "").trim(), explorerIds: [...form.elements.explorerIds.selectedOptions].map((o)=>o.value),
    professionalCategories: [...form.elements.professionalCategories.selectedOptions].map((o)=>o.value),
    rationale: String(fd.get("rationale") || "").trim(), exclusions: String(fd.get("exclusions") || "").trim(), followUp: String(fd.get("followUp") || "").trim()
  };
}

export function renderPlanQuality(form) {
  const box = document.getElementById("institutional-plan-quality");
  if (!box) return;
  const audit = auditPlan(readPlanForm(form));
  box.innerHTML = `<strong>${audit.score}%</strong><div><span>اكتمال المخطط — ${audit.passed}/${audit.total} بوابات</span>${audit.warnings.length ? `<ul class="institutional-v220-warning-list">${audit.warnings.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul>` : "<p>جميع البوابات الأساسية مكتملة.</p>"}</div>`;
}

export function fillPlanCaseOptions(select, selected = "") {
  const cases = currentStore()?.cases || [];
  select.innerHTML = cases.length ? cases.map((caseRecord)=>`<option value="${esc(caseRecord.caseId)}"${caseRecord.caseId===selected?" selected":""}>${esc(caseRecord.alias)} — ${esc(caseRecord.caseId)}</option>`).join("") : '<option value="">أنشئ حالة أولًا</option>';
}

export function setChecks(form, name, values) {
  const set = new Set(values || []);
  form.querySelectorAll(`input[name="${name}"]`).forEach((input)=>{ input.checked = set.has(input.value); });
}

export function setMulti(select, values) {
  const set = new Set(values || []);
  [...select.options].forEach((option)=>{ option.selected = set.has(option.value); });
}

export function openPlan(caseId = "", basePlanId = "") {
  const dialog = document.getElementById("institutional-plan-dialog");
  const form = document.getElementById("institutional-plan-form");
  if (!dialog || !form) return;
  if (!(currentStore()?.cases || []).length) { notify("أنشئ حالة أولًا."); if (typeof newCase === "function") newCase(); return; }
  form.reset();
  const base = getPlans().find((plan)=>plan.planId===basePlanId);
  form.elements.basePlanId.value = basePlanId || "";
  fillPlanCaseOptions(form.elements.caseId, caseId || base?.caseId || currentStore().cases[0].caseId);
  form.elements.reviewDate.value = base?.reviewDate || new Date(Date.now()+30*86400000).toISOString().slice(0,10);
  document.getElementById("institutional-plan-title").textContent = base ? `إصدار جديد من ${base.planId}` : "إنشاء مخطط تقييم";
  if (base) {
    ["decisionUse","planStatus","referralQuestion","targetOutcomes","languageContext","accessibility","consentStatus","assentStatus","safetyReview","reviewer","rationale","exclusions","followUp"].forEach((name)=>{ if (form.elements[name]) form.elements[name].value = base[name] || ""; });
    setChecks(form,"sources",base.sources); setChecks(form,"settings",base.settings); setMulti(form.elements.explorerIds,base.explorerIds); setMulti(form.elements.professionalCategories,base.professionalCategories);
  }
  renderPlanQuality(form);
  openDialog(dialog);
}

export function savePlan(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const payload = readPlanForm(form);
  const caseRecord = currentStore()?.cases?.find((item)=>item.caseId===payload.caseId);
  if (!caseRecord) { notify("تعذر العثور على الحالة."); return; }
  const audit = auditPlan(payload);
  if (payload.safetyReview === "urgent") { notify("يوجد خطر مباشر: أوقف التقييم واتبع مسار السلامة المحلي."); }
  caseRecord.assessmentPlans ||= [];
  const basePlanId = String(form.elements.basePlanId.value || "");
  const base = caseRecord.assessmentPlans.find((plan)=>plan.planId===basePlanId);
  if (base) base.planStatus = "superseded";
  const plan = {
    ...payload, planId: uid("PLAN"), version: base ? Number(base.version || 1)+1 : 1, supersedes: base?.planId || null,
    schema: SCHEMA, release: RELEASE, qualityAudit: audit, createdAt: now(), updatedAt: now(), createdByUid: typeof identity !== "undefined" ? identity.uid : "local",
    auditTrail: [{event:"created",at:now(),byUid:typeof identity!=="undefined"?identity.uid:"local",score:audit.score}]
  };
  caseRecord.assessmentPlans.push(plan);
  caseRecord.updatedAt = now();
  persist();
  closeDialog(document.getElementById("institutional-plan-dialog"));
  renderInstitutional();
  notify(`حُفظ مخطط التقييم بدرجة اكتمال ${audit.score}%.`);
}

export function planStatusLabel(value) {
  return ({draft:"مسودة",ready:"جاهز للمراجعة",active:"قيد التنفيذ",review_due:"مراجعة مستحقة",closed:"مغلق",superseded:"مستبدل بإصدار أحدث"})[value] || value;
}

export function decisionLabel(value) {
  return ({exploration:"استكشاف منظم",support_planning:"تخطيط دعم",progress_monitoring:"متابعة تغير",comprehensive_evaluation:"تقييم شامل",transition:"انتقال واستعداد",safety_review:"مراجعة سلامة"})[value] || value;
}

export function renderInstitutional() {
  const stats = document.getElementById("institutional-v220-stats");
  const list = document.getElementById("institutional-v220-plans");
  if (!stats || !list) return;
  const plans = getPlans().sort((a,b)=>new Date(b.createdAt)-new Date(a.createdAt));
  const ready = plans.filter((plan)=>plan.qualityAudit?.score===100).length;
  stats.innerHTML = `
    <article class="stat-card"><span>الأدوات الاستكشافية</span><strong>${data.explorers.length}</strong></article>
    <article class="stat-card"><span>عناصر الدليل المهني</span><strong>${data.professional.length}</strong></article>
    <article class="stat-card"><span>مخططات التقييم</span><strong>${plans.length}</strong></article>
    <article class="stat-card"><span>مكتملة البوابات</span><strong>${ready}</strong></article>`;
  list.innerHTML = plans.length ? plans.map((plan)=>`<article class="institutional-v220-plan">
    <header><div><span class="badge ${plan.qualityAudit?.score===100?"success":plan.qualityAudit?.score>=80?"warning":"danger"}">${plan.qualityAudit?.score||0}% اكتمال</span><h3>${esc(plan.caseAlias)} — ${esc(decisionLabel(plan.decisionUse))}</h3><p class="code small">${esc(plan.planId)} · الإصدار ${esc(plan.version)}</p></div><span class="badge neutral">${esc(planStatusLabel(plan.planStatus))}</span></header>
    <p><strong>سؤال القرار:</strong> ${esc(plan.referralQuestion)}</p>
    <dl><div><dt>المصادر</dt><dd>${(plan.sources||[]).length}</dd></div><div><dt>البيئات</dt><dd>${(plan.settings||[]).length}</dd></div><div><dt>الأدوات/الفئات</dt><dd>${(plan.explorerIds||[]).length+(plan.professionalCategories||[]).length}</dd></div><div><dt>المراجعة</dt><dd>${esc(plan.reviewDate)}</dd></div></dl>
    <div class="institutional-v220-plan-actions"><label class="field"><span>الحالة</span><select data-plan-status="${esc(plan.planId)}"><option value="draft"${plan.planStatus==="draft"?" selected":""}>مسودة</option><option value="ready"${plan.planStatus==="ready"?" selected":""}>جاهز للمراجعة</option><option value="active"${plan.planStatus==="active"?" selected":""}>قيد التنفيذ</option><option value="review_due"${plan.planStatus==="review_due"?" selected":""}>مراجعة مستحقة</option><option value="closed"${plan.planStatus==="closed"?" selected":""}>مغلق</option><option value="superseded"${plan.planStatus==="superseded"?" selected":""}>مستبدل</option></select></label><button class="button secondary small-button" type="button" data-plan-view="${esc(plan.planId)}">عرض العقد</button><button class="button ghost small-button" type="button" data-plan-clone="${esc(plan.planId)}" data-case-id="${esc(plan.caseId)}">إنشاء إصدار جديد</button></div>
  </article>`).join("") : '<div class="institutional-v220-empty">لا توجد مخططات بعد. أنشئ حالة ثم ابنِ عقد التقييم قبل اختيار الأدوات.</div>';
  window.PA_V220_HOOKS?.decorateProfessionalRecords?.();
}

export function findPlan(planId) { return getPlans().find((plan)=>plan.planId===planId); }

export function showPlan(planId) {
  const plan = findPlan(planId); if (!plan) return;
  const dialog = document.getElementById("institutional-tool-dialog");
  const content = document.getElementById("institutional-tool-content");
  const audit = plan.qualityAudit || auditPlan(plan);
  content.innerHTML = `<div class="dialog-heading"><div><p class="eyebrow">${esc(plan.planId)} · الإصدار ${esc(plan.version)}</p><h2>عقد تقييم ${esc(plan.caseAlias)}</h2></div><button class="icon-button" data-close-institutional aria-label="إغلاق">×</button></div>
    <div class="institutional-v220-score"><strong>${audit.score}%</strong><span>${audit.passed}/${audit.total} بوابات مكتملة</span></div>
    <div class="institutional-v220-contract-grid">
      <article class="institutional-v220-contract-card"><h3>سؤال القرار</h3><p>${esc(plan.referralQuestion)}</p><p><strong>الاستخدام:</strong> ${esc(decisionLabel(plan.decisionUse))}</p></article>
      <article class="institutional-v220-contract-card"><h3>النتائج المستهدفة</h3><p>${esc(plan.targetOutcomes)}</p></article>
      <article class="institutional-v220-contract-card"><h3>المصادر والبيئات</h3><p>${esc((plan.sources||[]).join("، "))}</p><p>${esc((plan.settings||[]).join("، "))}</p></article>
      <article class="institutional-v220-contract-card"><h3>اللغة والإتاحة</h3><p>${esc(plan.languageContext)}</p><p>${esc(plan.accessibility)}</p></article>
      <article class="institutional-v220-contract-card"><h3>الاختيار والتسلسل</h3><p>${esc(plan.rationale)}</p></article>
      <article class="institutional-v220-contract-card"><h3>الحدود والمتابعة</h3><p>${esc(plan.exclusions)}</p><p>${esc(plan.followUp)}</p></article>
    </div>
    <div class="institutional-v220-gates">${audit.gates.map(([name,ok])=>`<div class="institutional-v220-gate"><span>${esc(name)}</span><div class="institutional-v220-track"><div class="institutional-v220-fill" style="width:${ok?100:0}%"></div></div><strong>${ok?"مكتمل":"ناقص"}</strong></div>`).join("")}</div>`;
  openDialog(dialog);
}

export function showToolContract(type, toolId) {
  const tool = type === "explorer" ? data.explorers.find((x)=>x.id===toolId) : data.professional.find((x)=>x.id===toolId);
  if (!tool) return;
  const c = tool.institutionalContract;
  const dialog = document.getElementById("institutional-tool-dialog");
  const content = document.getElementById("institutional-tool-content");
  if (type === "explorer") {
    content.innerHTML = `<div class="dialog-heading"><div><p class="eyebrow">${esc(c.instrumentType)} · ${esc(c.release)}</p><h2>${esc(tool.title)}</h2></div><button class="icon-button" data-close-institutional aria-label="إغلاق">×</button></div>
      <div class="institutional-v220-contract-grid">
        <article class="institutional-v220-contract-card"><h3>الغرض والاستخدام</h3><p>${esc(c.purpose)}</p><ul>${c.decisionUse.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul></article>
        <article class="institutional-v220-contract-card"><h3>السكان والزمن</h3><p>${esc(c.ageGroups.join("، "))}</p><p>${esc(c.referenceWindow)}</p><p>${esc(c.estimatedDuration)} · ${c.itemCount} عناصر</p></article>
        <article class="institutional-v220-contract-card"><h3>المجالات والمصادر</h3><p><strong>المجالات:</strong> ${esc(c.domains.join("، "))}</p><p><strong>المصادر:</strong> ${esc(c.dataSources.join("، "))}</p></article>
        <article class="institutional-v220-contract-card"><h3>التصحيح والتفسير</h3><p>${esc(c.scoring)}</p><p>${esc(c.interpretation)}</p><p>${esc(c.missingData)}</p></article>
        <article class="institutional-v220-contract-card"><h3>العوامل المربكة</h3><ul>${c.confounders.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul></article>
        <article class="institutional-v220-contract-card"><h3>السلامة والمتابعة</h3><ul>${c.redFlags.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul><p>${esc(c.repeatInterval)}</p></article>
        <article class="institutional-v220-contract-card"><h3>الإتاحة</h3><p>${esc(c.accessibility)}</p></article>
        <article class="institutional-v220-contract-card"><h3>الحوكمة</h3><p>${esc(c.governance)}</p></article>
      </div>`;
  } else {
    content.innerHTML = `<div class="dialog-heading"><div><p class="eyebrow">بطاقة أداة مهنية دون مواد محمية</p><h2>${esc(tool.name)}</h2></div><button class="icon-button" data-close-institutional aria-label="إغلاق">×</button></div>
      <div class="callout warning">هذه البطاقة توثق وظيفة الأداة ومتطلبات استخدامها فقط. لا تعرض بنودًا أو تعليمات تصحيح أو معايير أو محتوى محميًا.</div>
      <div class="institutional-v220-contract-grid">
        <article class="institutional-v220-contract-card"><h3>الغرض</h3><p>${esc(c.purpose)}</p><p>${esc(c.decisionUse)}</p></article>
        <article class="institutional-v220-contract-card"><h3>المؤهل والتطبيق</h3><p>${esc(c.administrationRequirements)}</p><p>${esc(c.recommendedRoles.join("، "))}</p></article>
        <article class="institutional-v220-contract-card"><h3>الصلاحية</h3><p>${esc(c.validityRequirements)}</p><p>${esc(c.interpretationRule)}</p></article>
        <article class="institutional-v220-contract-card"><h3>الحالات/المجالات</h3><p>${esc(c.conditions.join("، "))}</p></article>
        <article class="institutional-v220-contract-card"><h3>الحد الأدنى للسجل</h3><ul>${c.recordMinimum.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul></article>
        <article class="institutional-v220-contract-card"><h3>الاستخدامات المحظورة</h3><ul>${c.prohibitedUse.map((x)=>`<li>${esc(x)}</li>`).join("")}</ul></article>
        <article class="institutional-v220-contract-card"><h3>الحقوق والوصول</h3><p>${esc(c.rightsStatus)}</p><p>${esc(tool.note || "")}</p></article>
        <article class="institutional-v220-contract-card"><h3>صيغة الإدخال</h3><p>${esc(c.inputMode)}</p></article>
      </div>`;
  }
  openDialog(dialog);
}
