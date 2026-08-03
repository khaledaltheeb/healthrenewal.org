"use strict";

import { RELEASE, SCHEMA, data, esc, now, currentStore, persist, openDialog, closeDialog } from "./institutional-contract-v220-core.js";
import { buildPlanForm } from "./institutional-contract-v220-ui.js";
import { auditProfessionalRecord, renderProfessionalFormQuality, renderPlanQuality, openPlan, savePlan, renderInstitutional, findPlan, showPlan, showToolContract } from "./institutional-contract-v220-plans.js";

const installUi = () => {
  const tabs = document.querySelector(".tabs");
  const guidePanel = document.getElementById("view-guide");
  if (!tabs || !guidePanel || document.getElementById("view-institutional-v220")) return;

  const tab = document.createElement("button");
  tab.className = "tab";
  tab.type = "button";
  tab.dataset.view = "institutional-v220";
  tab.setAttribute("aria-selected", "false");
  tab.textContent = "العقد المؤسسي v220";
  const guideTab = tabs.querySelector('[data-view="guide"]');
  tabs.insertBefore(tab, guideTab);

  const panel = document.createElement("section");
  panel.id = "view-institutional-v220";
  panel.className = "view";
  panel.dataset.viewPanel = "institutional-v220";
  panel.hidden = true;
  panel.innerHTML = `
    <div class="section-heading"><div><p class="eyebrow">حوكمة، صلاحية، تعدد مصادر، وتتبع قرارات</p><h2>العقد المؤسسي للتقييم والسجل المهني v220</h2></div><button id="institutional-plan-new" class="button primary" type="button">إنشاء مخطط تقييم</button></div>
    <div class="callout info">هذه الطبقة لا تضيف تشخيصًا آليًا ولا تفتح مواد محمية. وظيفتها ضبط الغرض، المصادر، البيئات، الصلاحية، الحقوق، المراجعة، والمتابعة قبل اعتماد أي استنتاج.</div>
    <div id="institutional-v220-stats" class="institutional-v220-grid"></div>
    <section class="institutional-v220-section"><header><div><h3>مخططات التقييم المرتبطة بالحالات</h3><p class="muted">إصدارات قابلة للتتبع تشمل سؤال القرار، المصادر، البيئات، التكييفات، السلامة، الفريق والمراجعة.</p></div></header><div id="institutional-v220-plans" class="institutional-v220-plan-list"></div></section>
    <section class="institutional-v220-section"><header><div><h3>بوابات الاعتماد العشر</h3><p class="muted">لا يصبح المخطط جاهزًا مهنيًا لمجرد اختيار أداة.</p></div></header><div class="institutional-v220-contract-grid">
      ${["سؤال إحالة وقرار واضح","مصدران مستقلان على الأقل","بيئتان أو سياقان عند الملاءمة","لغة وثقافة وإتاحة موثقة","موافقة/مشاركة الشخص أو وليه","مراجعة سلامة ومخاطر","مبرر اختيار كل أداة","صلاحية النسخة والمعايير والحقوق","دمج نقاط القوة والاحتياجات","مراجع وإصدار وموعد مراجعة"].map((x,i)=>`<article class="institutional-v220-contract-card"><span class="badge neutral">بوابة ${i+1}</span><h3>${x}</h3></article>`).join("")}
    </div></section>
    <section class="institutional-v220-section"><header><div><h3>مرجعية التصميم</h3><p class="muted">اعتماد الوظيفة والمشاركة والسياق، والفصل بين المراقبة والاستكشاف والتقييم الرسمي.</p></div></header><div class="institutional-v220-basis">
      <article class="institutional-v220-panel"><h3>WHO ICF</h3><p>تنظيم الوظيفة والنشاط والمشاركة والعوامل البيئية بدل اختزال الشخص في تشخيص.</p><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" target="_blank" rel="noopener noreferrer">المصدر الرسمي</a></article>
      <article class="institutional-v220-panel"><h3>Testing Standards</h3><p>صلاحية التفسير، العدالة، الإتاحة، الاستخدام المقصود، والمسؤولية المهنية.</p><a href="https://www.testingstandards.net/" target="_blank" rel="noopener noreferrer">المصدر الرسمي</a></article>
      <article class="institutional-v220-panel"><h3>CDC/AAP</h3><p>المراقبة والاستكشاف والفحص الرسمي عمليات مختلفة ومتكاملة، والنتيجة الإيجابية تقود إلى تقييم ومتابعة.</p><a href="https://www.cdc.gov/act-early/about/developmental-monitoring-and-screening.html" target="_blank" rel="noopener noreferrer">المصدر الرسمي</a></article>
    </div></section>`;
  guidePanel.before(panel);

  const toolDialog = document.createElement("dialog");
  toolDialog.id = "institutional-tool-dialog";
  toolDialog.className = "dialog xlarge";
  toolDialog.innerHTML = '<div id="institutional-tool-content"></div>';
  document.body.appendChild(toolDialog);

  const planDialog = document.createElement("dialog");
  planDialog.id = "institutional-plan-dialog";
  planDialog.className = "dialog xlarge";
  planDialog.innerHTML = buildPlanForm();
  document.body.appendChild(planDialog);

  enhanceProfessionalForm();
  bindEvents();
  renderInstitutional();
  decorateCatalogs();
};

function enhanceProfessionalForm() {
  const form = document.getElementById("professional-record-form");
  if (!form || form.querySelector("[data-institutional-professional-v220]")) return;
  const rights = form.querySelector(".rights-confirmation");
  const section = document.createElement("fieldset");
  section.className = "institutional-v220-fieldset";
  section.dataset.institutionalProfessionalV220 = "true";
  section.innerHTML = `<legend>عقد التوثيق المؤسسي v220</legend>
    <div class="form-grid">
      <label class="field"><span>سؤال الإحالة/الغرض</span><input name="referralPurpose" maxlength="500" required></label>
      <label class="field"><span>استخدام القرار</span><select name="decisionUseV220" required><option value="">اختر</option><option value="screening">فحص/مسح</option><option value="description">وصف ملف وظيفي</option><option value="planning">تخطيط دعم</option><option value="progress">متابعة تغير</option><option value="diagnostic_component">مكوّن ضمن تقييم شامل</option><option value="external_documentation">توثيق تقرير خارجي</option></select></label>
      <label class="field"><span>صلاحية النتيجة</span><select name="validityStatus" required><option value="">اختر</option><option value="valid">صالحة للغرض المحدد</option><option value="qualified">صالحة بقيود</option><option value="invalid">غير صالحة للتفسير</option><option value="pending">تحتاج مراجعة</option></select></label>
      <label class="field"><span>اكتمال التطبيق</span><select name="completionStatus" required><option value="complete">مكتمل</option><option value="partial">جزئي</option><option value="discontinued">أوقف</option><option value="external_summary">ملخص خارجي فقط</option></select></label>
      <label class="field"><span>ملاءمة النسخة/المعايير</span><select name="normativeFit" required><option value="verified">متحقق منها</option><option value="limited">محدودة أو غير ممثلة بالكامل</option><option value="not_applicable">غير منطبقة</option><option value="unknown">غير معروفة</option></select></label>
      <label class="field"><span>اتساق المصادر</span><select name="crossSourceAgreement" required><option value="consistent">متسقة إجمالًا</option><option value="mixed">مختلطة وتحتاج تفسيرًا</option><option value="single_source">مصدر واحد</option><option value="not_applicable">غير منطبق</option></select></label>
      <label class="field"><span>الموافقة/المشاركة</span><select name="consentV220" required><option value="documented">موثقة</option><option value="verbal">شفوية موثقة</option><option value="not_applicable">غير منطبقة</option><option value="missing">غير مكتملة</option></select></label>
      <label class="field"><span>مراجعة السلامة</span><select name="riskReview" required><option value="clear">لا خطر مباشر</option><option value="plan">مخاوف مع خطة</option><option value="urgent">خطر مباشر/وشيك</option><option value="not_reviewed">لم تراجع</option></select></label>
      <label class="field"><span>المراجع المهني</span><input name="reviewerV220" maxlength="160" required></label>
      <label class="field"><span>موعد المراجعة التالية</span><input type="date" name="reviewDateV220" required></label>
    </div>
    <label class="field"><span>المصادر والبيئات</span><textarea name="sourcesSettings" rows="3" maxlength="1200" required placeholder="من قدم المعلومات؟ وفي أي بيئات؟ وما الفروق بين المصادر؟"></textarea></label>
    <label class="field"><span>التكييفات والانحرافات عن الإجراء</span><textarea name="accommodationsDeviations" rows="3" maxlength="1200" required placeholder="التكييفات، التوقفات، المترجم، التقنية، وأي انحراف قد يؤثر في الصلاحية"></textarea></label>
    <label class="field"><span>نقاط القوة والاحتياجات والوظيفة</span><textarea name="functionalSynthesis" rows="4" maxlength="1800" required></textarea></label>
    <label class="field"><span>التوصيات القابلة للتنفيذ والقياس</span><textarea name="recommendationsV220" rows="4" maxlength="1800" required></textarea></label>
    <label class="field"><span>حدود التفسير</span><textarea name="limitationsV220" rows="3" maxlength="1200" required></textarea></label>
    <div id="professional-v220-quality" class="institutional-v220-score" aria-live="polite"></div>`;
  rights?.before(section);

  let pending = null;
  form.addEventListener("submit", () => {
    const fd = new FormData(form);
    pending = {
      referralPurpose: String(fd.get("referralPurpose") || "").trim(),
      decisionUse: String(fd.get("decisionUseV220") || ""),
      validityStatus: String(fd.get("validityStatus") || ""),
      completionStatus: String(fd.get("completionStatus") || ""),
      normativeFit: String(fd.get("normativeFit") || ""),
      crossSourceAgreement: String(fd.get("crossSourceAgreement") || ""),
      consentStatus: String(fd.get("consentV220") || ""),
      riskReview: String(fd.get("riskReview") || ""),
      reviewer: String(fd.get("reviewerV220") || "").trim(),
      reviewDate: String(fd.get("reviewDateV220") || ""),
      sourcesSettings: String(fd.get("sourcesSettings") || "").trim(),
      accommodationsDeviations: String(fd.get("accommodationsDeviations") || "").trim(),
      functionalSynthesis: String(fd.get("functionalSynthesis") || "").trim(),
      recommendations: String(fd.get("recommendationsV220") || "").trim(),
      limitations: String(fd.get("limitationsV220") || "").trim()
    };
    queueMicrotask(() => {
      const records = currentStore()?.cases?.flatMap((caseRecord) => caseRecord.professionalAssessments || []) || [];
      const record = records.sort((a,b)=>new Date(b.recordedAt)-new Date(a.recordedAt))[0];
      if (!record || !pending) return;
      record.institutionalV220 = { ...pending, schema: SCHEMA, release: RELEASE, capturedAt: now() };
      record.documentationQuality = auditProfessionalRecord(record);
      record.auditTrail ||= [];
      record.auditTrail.push({ event: "institutional_contract_attached", at: now(), byUid: typeof identity !== "undefined" ? identity.uid : "local" });
      persist();
      pending = null;
      renderInstitutional();
      decorateProfessionalRecords();
    });
  }, true);
  form.addEventListener("input", () => renderProfessionalFormQuality(form));
  form.addEventListener("change", () => renderProfessionalFormQuality(form));
}

function decorateCatalogs() {
  document.querySelectorAll("#explorer-list .assessment-card").forEach((card) => {
    const start = card.querySelector("[data-start]");
    if (!start || card.querySelector("[data-explorer-contract]")) return;
    const button = document.createElement("button");
    button.type = "button"; button.className = "button ghost small-button"; button.dataset.explorerContract = start.dataset.start; button.textContent = "العقد العلمي";
    card.querySelector(".card-actions")?.appendChild(button);
  });
  document.querySelectorAll("#professional-list .catalog-row").forEach((row) => {
    if (row.querySelector("[data-professional-contract]")) return;
    const name = row.querySelector("h3")?.textContent?.trim();
    const tool = data.professional.find((item)=>item.name===name);
    if (!tool) return;
    let actions = row.querySelector(".professional-card-actions");
    if (!actions) { actions = document.createElement("div"); actions.className = "institutional-v220-tool-actions"; row.lastElementChild?.appendChild(actions); }
    const button = document.createElement("button");
    button.type = "button"; button.className = "button ghost small-button"; button.dataset.professionalContract = tool.id; button.textContent = "بطاقة الأداة";
    actions.appendChild(button);
  });
}

function decorateProfessionalRecords() {
  document.querySelectorAll("#professional-record-list .professional-record").forEach((node) => {
    if (node.querySelector(".institutional-v220-record-audit")) return;
    const recordCodes = [...node.querySelectorAll(".code.small")].map((item) => item.textContent?.trim()).filter(Boolean);
    const recordId = recordCodes.find((value) => value.startsWith("PRO-")) || recordCodes.at(-1);
    const records = currentStore()?.cases?.flatMap((caseRecord)=>caseRecord.professionalAssessments || []) || [];
    const record = records.find((item)=>item.recordId===recordId);
    if (!record?.institutionalV220) return;
    const audit = record.documentationQuality || auditProfessionalRecord(record);
    const section = document.createElement("div");
    section.className = "institutional-v220-record-audit";
    section.innerHTML = `<div class="institutional-v220-score"><strong>${audit.score}%</strong><span>عقد التوثيق المؤسسي · ${esc(record.institutionalV220.validityStatus)} · مراجعة ${esc(record.institutionalV220.reviewDate)}</span></div><details><summary>عرض التركيب والحدود والتوصيات</summary><p class="institutional-v220-detail"><strong>الغرض:</strong> ${esc(record.institutionalV220.referralPurpose)}
<strong>المصادر والبيئات:</strong> ${esc(record.institutionalV220.sourcesSettings)}
<strong>التكييفات والانحرافات:</strong> ${esc(record.institutionalV220.accommodationsDeviations)}
<strong>التركيب الوظيفي:</strong> ${esc(record.institutionalV220.functionalSynthesis)}
<strong>التوصيات:</strong> ${esc(record.institutionalV220.recommendations)}
<strong>الحدود:</strong> ${esc(record.institutionalV220.limitations)}</p></details>`;
    node.appendChild(section);
  });
}

function decorateResult() {
  const content = document.getElementById("result-content");
  if (!content || content.querySelector("[data-session-validity-v220]") || !content.querySelector(".result-hero")) return;
  const sessionId = content.querySelector(".eyebrow")?.textContent?.split("—")?.pop()?.trim();
  if (!sessionId) return;
  let found = null, caseRecord = null;
  for (const c of currentStore()?.cases || []) { const s = (c.sessions || []).find((item)=>item.sessionId===sessionId); if (s) { found=s; caseRecord=c; break; } }
  if (!found || !caseRecord) return;
  const answers = Object.values(found.answers || {});
  const unknown = answers.filter((value)=>value==="unknown" || (Array.isArray(value)&&value.includes("unknown"))).length;
  const total = answers.length || 1;
  const completion = Math.round(((total-unknown)/total)*100);
  const activePlan = (caseRecord.assessmentPlans || []).filter((p)=>["ready","active","review_due"].includes(p.planStatus)).sort((a,b)=>new Date(b.updatedAt)-new Date(a.updatedAt))[0];
  const sources = activePlan?.sources?.length || 1;
  const validity = completion >= 90 && sources >= 2 ? "قوية وصفيًا" : completion >= 70 ? "متوسطة وتحتاج دمج مصادر" : "محدودة";
  found.institutionalValidity ||= { schema:SCHEMA, release:RELEASE, completionPercent:completion, unknownAnswers:unknown, sourceCount:sources, validity, evaluatedAt:now() };
  persist();
  const box = document.createElement("div");
  box.dataset.sessionValidityV220 = "true";
  box.className = "callout info";
  box.innerHTML = `<strong>صلاحية الخلاصة الوصفية: ${esc(validity)}</strong><br>اكتمال الإجابات ${completion}%، وعدد المصادر الموثقة ${sources}. هذه ليست صلاحية تشخيصية ولا معيارية.`;
  content.querySelector(".result-hero")?.after(box);
}

function bindEvents() {
  const form = document.getElementById("institutional-plan-form");
  form?.addEventListener("submit", savePlan);
  form?.addEventListener("input", ()=>renderPlanQuality(form));
  form?.addEventListener("change", ()=>renderPlanQuality(form));
  document.addEventListener("click", (event) => {
    const target = event.target.closest("button"); if (!target) return;
    if (target.id === "institutional-plan-new") openPlan();
    if (target.dataset.planClone) openPlan(target.dataset.caseId, target.dataset.planClone);
    if (target.dataset.planView) showPlan(target.dataset.planView);
    if (target.dataset.explorerContract) showToolContract("explorer", target.dataset.explorerContract);
    if (target.dataset.professionalContract) showToolContract("professional", target.dataset.professionalContract);
    if (target.hasAttribute("data-close-institutional")) closeDialog(target.closest("dialog"));
  });
  document.addEventListener("change", (event) => {
    const select = event.target.closest("[data-plan-status]"); if (!select) return;
    const plan = findPlan(select.dataset.planStatus); if (!plan) return;
    plan.planStatus = select.value; plan.updatedAt = now(); plan.auditTrail ||= []; plan.auditTrail.push({event:"status_changed",value:select.value,at:now(),byUid:typeof identity!=="undefined"?identity.uid:"local"});
    persist(); renderInstitutional();
  });
  new MutationObserver(() => { decorateCatalogs(); decorateProfessionalRecords(); decorateResult(); }).observe(document.getElementById("workspace") || document.body,{subtree:true,childList:true});
}

const previousRender = typeof render === "function" ? render : null;
if (previousRender) {
  render = function institutionalRenderV220() {
    previousRender();
    renderInstitutional();
    queueMicrotask(()=>{ decorateCatalogs(); decorateProfessionalRecords(); });
  };
}

const patchReleaseCopy = () => {
  document.documentElement.dataset.institutionalContract = RELEASE;
  const meta = document.querySelector('meta[name="application-version"]'); if (meta) meta.content = RELEASE;
  const notice = document.querySelector(".notice-bar"); if (notice) notice.textContent = "الأدوات الاستكشافية تعمل ضمن عقد غير تشخيصي، والسجل المهني يفرض الغرض والمصادر والبيئات والصلاحية والحقوق والمراجعة. المواد المحمية تبقى مقفلة حتى الترخيص والمؤهل المناسب.";
  const footer = document.querySelector(".site-footer p"); if (footer) footer.textContent = `© منصة روافد — عقد التقييم والسجل المهني ${RELEASE}. تخزين محلي داخل UID مستقل؛ لا تشخيص آلي ولا أهلية من أداة منفردة.`;
};

window.PA_V220_HOOKS = { decorateProfessionalRecords };
installUi();
patchReleaseCopy();
if (typeof applyTabSemantics === "function") applyTabSemantics();
renderInstitutional();
