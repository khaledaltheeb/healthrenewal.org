"use strict";

(() => {
  if (typeof store === "undefined" || typeof save !== "function" || typeof identity === "undefined") return;

  const VERSION = "2026.07.24-report.1";
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const dateText = (value) => {
    try { return new Intl.DateTimeFormat("ar-JO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
    catch (_) { return String(value || ""); }
  };
  const ageLabel = (value) => ({ early: "الطفولة المبكرة 0–5", child: "الطفولة 6–12", adolescent: "المراهقة 13–17", adult: "البالغون 18+" })[value] || value;
  const statusLabel = (value) => ({ active: "نشطة", follow_up: "متابعة", closed: "مغلقة", draft: "مسودة", reviewed: "مراجع داخليًا", final: "نهائي داخلي" })[value] || value;
  const nextLabel = (value) => ({ review: "مراجعة مع المختص", another_tool: "إضافة أداة مكملة", collect_sources: "جمع مصادر إضافية", team_review: "مراجعة فريق متعدد التخصصات", support_plan: "إعداد خطة دعم", close: "إغلاق مسار التقييم", urgent_safety: "اتباع مسار السلامة العاجل" })[value] || value;

  const installStyles = () => {
    if (document.getElementById("case-report-styles")) return;
    const style = document.createElement("style");
    style.id = "case-report-styles";
    style.textContent = `
      .report-toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px}
      .report-list{display:grid;gap:14px}.report-card{border:1px solid var(--line);border-radius:18px;background:#fff;padding:18px}
      .report-card header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.report-card h3{margin:.25rem 0}
      .report-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0}.report-meta div{background:#f3faf9;border-radius:11px;padding:9px}.report-meta dt{font-size:.8rem;color:var(--muted)}.report-meta dd{margin:2px 0 0;font-weight:800}
      .report-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.report-full{grid-column:1/-1}
      .report-preview{border:1px solid var(--line);border-radius:18px;padding:22px;background:#fff}.report-preview h3{border-bottom:1px solid var(--line);padding-bottom:8px}.report-preview table{width:100%;border-collapse:collapse}.report-preview th,.report-preview td{border:1px solid var(--line);padding:8px;text-align:right;vertical-align:top}
      .report-actions{display:flex;gap:8px;flex-wrap:wrap}.report-disclaimer{border-right:5px solid #b88912;background:#fff8df;padding:12px 14px;border-radius:12px}
      @media(max-width:800px){.report-meta,.report-form-grid{grid-template-columns:1fr}.report-card header{flex-direction:column}.report-preview{overflow-x:auto}}
      @media print{body.report-print-mode>*:not(#case-report-dialog){display:none!important}body.report-print-mode #case-report-dialog{display:block!important;position:static!important;max-width:none!important;max-height:none!important;width:100%!important;box-shadow:none!important}body.report-print-mode #case-report-dialog::backdrop{display:none}body.report-print-mode #case-report-dialog form>.dialog-heading,body.report-print-mode #case-report-dialog .report-form-grid,body.report-print-mode #case-report-dialog .dialog-actions{display:none!important}}
    `;
    document.head.appendChild(style);
  };

  const allReports = () => store.cases.flatMap((caseRecord) => (caseRecord.reports || []).map((report) => ({ ...report, caseAlias: caseRecord.alias, caseId: caseRecord.caseId })));
  const caseById = (caseId) => store.cases.find((item) => item.caseId === caseId);

  const installView = () => {
    if (document.getElementById("view-reports")) return;
    const tabs = document.querySelector(".tabs");
    const guideTab = tabs?.querySelector('[data-view="guide"]');
    if (!tabs || !guideTab) return;
    const tab = document.createElement("button");
    tab.className = "tab";
    tab.type = "button";
    tab.dataset.view = "reports";
    tab.setAttribute("aria-selected", "false");
    tab.textContent = "التقارير المهنية";
    tabs.insertBefore(tab, guideTab);

    const guidePanel = document.getElementById("view-guide");
    const panel = document.createElement("section");
    panel.id = "view-reports";
    panel.className = "view";
    panel.dataset.viewPanel = "reports";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="section-heading"><div><p class="eyebrow">تقارير محلية مرتبطة بالحالة</p><h2>التقارير المهنية وإصداراتها</h2></div><button id="new-case-report" class="button primary" type="button">إنشاء تقرير</button></div>
      <div class="callout info">يجمع التقرير ملخص الحالة والجلسات والتطبيقات المهنية، ثم يضيف مقدم الخدمة نقاط القوة والاحتياجات والتوصيات وقرار المتابعة. لا تنشئ المنصة تشخيصًا آليًا.</div>
      <div class="report-toolbar"><label class="field"><span>الحالة</span><select id="report-case-filter"><option value="">جميع الحالات</option></select></label><label class="field grow"><span>البحث</span><input id="report-search" type="search" placeholder="الحالة، الغرض، القرار أو المُعد"></label></div>
      <div id="report-stats" class="stats-grid"></div><div id="report-list" class="report-list"></div>`;
    guidePanel?.before(panel);
  };

  const installDialog = () => {
    if (document.getElementById("case-report-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "case-report-dialog";
    dialog.className = "dialog xlarge";
    dialog.innerHTML = `
      <form method="dialog" id="case-report-form">
        <div class="dialog-heading"><div><p class="eyebrow">إصدار تقرير محلي</p><h2 id="case-report-title">تقرير الحالة</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div>
        <input type="hidden" name="reportId">
        <div class="report-form-grid">
          <label class="field"><span>الحالة</span><select name="caseId" required></select></label>
          <label class="field"><span>تاريخ التقرير</span><input name="reportDate" type="date" required></label>
          <label class="field"><span>مُعد التقرير</span><input name="preparedBy" maxlength="120" placeholder="الاسم المهني أو رمز الموظف" required></label>
          <label class="field"><span>الدور أو الاختصاص</span><input name="preparedRole" maxlength="120" placeholder="أخصائي نفسي، نطق، علاج وظيفي..." required></label>
          <label class="field"><span>نوع التقرير</span><select name="reportType" required><option value="initial">تقرير أولي</option><option value="multidisciplinary">تقرير متعدد التخصصات</option><option value="progress">تقرير متابعة</option><option value="review">مراجعة نتائج</option><option value="closure">تقرير إغلاق المسار</option></select></label>
          <label class="field"><span>حالة الإصدار</span><select name="reviewStatus" required><option value="draft">مسودة</option><option value="reviewed">مراجع داخليًا</option><option value="final">نهائي داخلي</option></select></label>
          <label class="field report-full"><span>غرض التقرير وسؤال الإحالة</span><textarea name="purpose" rows="3" maxlength="1200" required></textarea></label>
          <label class="field report-full"><span>نقاط القوة</span><textarea name="strengths" rows="4" maxlength="2400" placeholder="المهارات والموارد والاهتمامات والبيئات التي يظهر فيها أفضل أداء" required></textarea></label>
          <label class="field report-full"><span>الاحتياجات والعوائق</span><textarea name="needs" rows="4" maxlength="2400" placeholder="الاحتياجات الوظيفية والبيئية والتعليمية والتواصلية" required></textarea></label>
          <label class="field report-full"><span>الملخص المتكامل للنتائج</span><textarea name="integratedSummary" rows="6" maxlength="5000" placeholder="ادمج الجلسات والتطبيقات والمصادر والقيود دون الاستنتاج من نتيجة واحدة" required></textarea></label>
          <label class="field report-full"><span>التوصيات وخطة الدعم</span><textarea name="recommendations" rows="6" maxlength="5000" required></textarea></label>
          <label class="field"><span>قرار المسار</span><select name="decision" required><option value="review">مراجعة النتيجة</option><option value="another_tool">إضافة أداة مكملة</option><option value="collect_sources">جمع مصادر إضافية</option><option value="team_review">مراجعة فريق متعدد التخصصات</option><option value="support_plan">الانتقال إلى خطة دعم</option><option value="close">إغلاق مسار التقييم</option><option value="urgent_safety">مسار سلامة عاجل</option></select></label>
          <label class="field"><span>موعد المتابعة</span><input name="followUpDate" type="date"></label>
          <label class="field report-full"><span>المؤشرات التي ستُتابع</span><textarea name="followUpIndicators" rows="3" maxlength="1800" placeholder="مهارات أو سلوكيات أو مؤشرات مشاركة قابلة للملاحظة"></textarea></label>
        </div>
        <section id="case-report-preview" class="report-preview"></section>
        <div class="dialog-actions spread"><div class="report-actions"><button type="button" class="button ghost" id="print-case-report">طباعة</button><button type="button" class="button ghost" id="export-case-report-html">تصدير HTML</button><button type="button" class="button ghost" id="export-case-report-json">تصدير JSON</button></div><div><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" value="default" type="submit">حفظ إصدار التقرير</button></div></div>
      </form>`;
    document.body.appendChild(dialog);
  };

  const selectedPathway = () => {
    try { return JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null"); }
    catch (_) { return null; }
  };

  const sessionRows = (caseRecord) => (caseRecord.sessions || []).map((session) => `
    <tr><td>${esc(dateText(session.completedAt))}</td><td>${esc(D.explorers.find((item) => item.id === session.assessmentId)?.title || session.assessmentId)}</td><td>${esc(session.outcomeLabel || session.outcome || "")}</td><td>${esc(session.summary || "")}</td></tr>`).join("");

  const professionalRows = (caseRecord) => (caseRecord.professionalAssessments || []).map((record) => `
    <tr><td>${esc(record.administrationDate || dateText(record.recordedAt))}</td><td>${esc(record.toolName)}</td><td>${esc(record.assignedEntityLabel || record.assignedEntity || "")}</td><td>${esc(record.outcomeLabel || record.outcome || "")}</td><td>${esc(nextLabel(record.nextAction))}</td></tr>`).join("");

  const reportHtml = (caseRecord, data = {}) => {
    const pathway = selectedPathway();
    const reportId = data.reportId || "مسودة جديدة";
    return `
      <article data-report-preview>
        <header><p class="eyebrow">منصة روافد</p><h2>تقرير تقييم ومتابعة مهني</h2><p><strong>الإصدار:</strong> ${esc(reportId)} — <strong>الحالة:</strong> ${esc(statusLabel(data.reviewStatus || "draft"))}</p></header>
        <section><h3>بيانات الحالة</h3><dl class="summary-grid"><div><dt>الاسم المستعار</dt><dd>${esc(caseRecord.alias)}</dd></div><div><dt>رقم الحالة</dt><dd>${esc(caseRecord.caseId)}</dd></div><div><dt>الفئة العمرية</dt><dd>${esc(ageLabel(caseRecord.ageGroup))}</dd></div><div><dt>اللغة</dt><dd>${esc(caseRecord.language)}</dd></div><div><dt>مصدر المعلومات</dt><dd>${esc(caseRecord.informant)}</dd></div><div><dt>حالة السجل</dt><dd>${esc(statusLabel(caseRecord.status))}</dd></div></dl></section>
        ${pathway ? `<section><h3>مسار الحالة المختار</h3><p><strong>${esc(pathway.title)}</strong></p></section>` : ""}
        <section><h3>غرض التقرير وسؤال الإحالة</h3><p>${esc(data.purpose || caseRecord.question || "غير مسجل")}</p></section>
        <section><h3>نقاط القوة</h3><p>${esc(data.strengths || "تُستكمل بواسطة مقدم الخدمة.")}</p></section>
        <section><h3>الاحتياجات والعوائق</h3><p>${esc(data.needs || "تُستكمل بواسطة مقدم الخدمة.")}</p></section>
        <section><h3>الجلسات الاستكشافية</h3>${(caseRecord.sessions || []).length ? `<table><thead><tr><th>التاريخ</th><th>الأداة</th><th>الخلاصة</th><th>الملخص</th></tr></thead><tbody>${sessionRows(caseRecord)}</tbody></table>` : "<p>لا توجد جلسات استكشافية مسجلة.</p>"}</section>
        <section><h3>التطبيقات المهنية</h3>${(caseRecord.professionalAssessments || []).length ? `<table><thead><tr><th>التاريخ</th><th>المقياس أو الفحص</th><th>المنفذ</th><th>الخلاصة</th><th>الخطوة التالية</th></tr></thead><tbody>${professionalRows(caseRecord)}</tbody></table>` : "<p>لا توجد تطبيقات مهنية مسجلة.</p>"}</section>
        <section><h3>الملخص المتكامل</h3><p>${esc(data.integratedSummary || "تُدمج النتائج والمصادر والقيود هنا بواسطة مقدم الخدمة.")}</p></section>
        <section><h3>التوصيات وخطة الدعم</h3><p>${esc(data.recommendations || "تُستكمل بواسطة مقدم الخدمة.")}</p></section>
        <section><h3>قرار المسار والمتابعة</h3><p><strong>القرار:</strong> ${esc(nextLabel(data.decision || "review"))}</p><p><strong>موعد المتابعة:</strong> ${esc(data.followUpDate || "غير محدد")}</p><p><strong>المؤشرات:</strong> ${esc(data.followUpIndicators || "غير مسجلة")}</p></section>
        <section><h3>إعداد التقرير</h3><p>${esc(data.preparedBy || identity.username || identity.uid)} — ${esc(data.preparedRole || identity.role)} — ${esc(data.reportDate || new Date().toISOString().slice(0, 10))}</p></section>
        <p class="report-disclaimer">هذا التقرير المحلي ينظم المعلومات المسجلة ولا يصدر تشخيصًا آليًا أو قرار أهلية تلقائيًا. يتحمل المراجع المهني مسؤولية التحقق من المصادر والنسخ والتفسير والتوقيع وفق الأنظمة المعمول بها.</p>
      </article>`;
  };

  const formDataObject = (form) => Object.fromEntries([...new FormData(form).entries()].map(([key, value]) => [key, String(value)]));

  const fillCaseOptions = (select, selected = "") => {
    select.innerHTML = store.cases.length ? store.cases.map((item) => `<option value="${esc(item.caseId)}"${item.caseId === selected ? " selected" : ""}>${esc(item.alias)} — ${esc(item.caseId)}</option>`).join("") : '<option value="">لا توجد حالات</option>';
  };

  const refreshPreview = () => {
    const form = document.getElementById("case-report-form");
    const preview = document.getElementById("case-report-preview");
    if (!form || !preview) return;
    const data = formDataObject(form);
    const caseRecord = caseById(data.caseId);
    preview.innerHTML = caseRecord ? reportHtml(caseRecord, data) : '<div class="empty-state">اختر حالة لعرض المعاينة.</div>';
  };

  const openReport = (caseId = "", reportId = "") => {
    const dialog = document.getElementById("case-report-dialog");
    const form = document.getElementById("case-report-form");
    if (!store.cases.length) {
      toast("أنشئ حالة أولًا ثم أضف تقريرًا.");
      newCase();
      return;
    }
    form.reset();
    fillCaseOptions(form.elements.caseId, caseId || selectedCase || store.cases[0].caseId);
    form.elements.reportDate.value = new Date().toISOString().slice(0, 10);
    form.elements.preparedBy.value = identity.username || identity.uid;
    form.elements.preparedRole.value = identity.role === "provider" ? "مقدم خدمة" : "مستخدم محلي";
    const selected = caseById(form.elements.caseId.value);
    form.elements.purpose.value = selected?.question || "";
    const existing = reportId ? (selected?.reports || []).find((item) => item.reportId === reportId) : null;
    if (existing) {
      for (const [key, value] of Object.entries(existing)) if (form.elements[key] && typeof value === "string") form.elements[key].value = value;
      document.getElementById("case-report-title").textContent = `تقرير ${selected.alias} — الإصدار ${existing.versionNumber}`;
    } else {
      document.getElementById("case-report-title").textContent = `تقرير ${selected?.alias || "الحالة"}`;
    }
    refreshPreview();
    open(dialog);
  };

  const saveReport = (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = formDataObject(form);
    const caseRecord = caseById(data.caseId);
    if (!caseRecord) return;
    caseRecord.reports ||= [];
    const now = new Date().toISOString();
    const versionNumber = caseRecord.reports.length + 1;
    const report = {
      ...data,
      reportId: data.reportId || id("RPT"),
      versionNumber,
      createdAt: now,
      createdByUid: identity.uid,
      createdByRole: identity.role,
      sourceSessionCount: (caseRecord.sessions || []).length,
      sourceProfessionalCount: (caseRecord.professionalAssessments || []).length,
      reportVersion: VERSION
    };
    caseRecord.reports.push(report);
    caseRecord.updatedAt = now;
    save();
    close(document.getElementById("case-report-dialog"));
    view("reports");
    renderReports();
    toast("تم حفظ إصدار التقرير داخل سجل الحالة.");
  };

  const renderReports = () => {
    const list = document.getElementById("report-list");
    const stats = document.getElementById("report-stats");
    const filter = document.getElementById("report-case-filter");
    const search = document.getElementById("report-search");
    if (!list || !stats || !filter || !search) return;
    const current = filter.value;
    filter.innerHTML = '<option value="">جميع الحالات</option>' + store.cases.map((item) => `<option value="${esc(item.caseId)}"${item.caseId === current ? " selected" : ""}>${esc(item.alias)}</option>`).join("");
    const query = search.value.trim().toLowerCase();
    const reports = allReports().filter((item) => (!filter.value || item.caseId === filter.value) && (!query || `${item.caseAlias} ${item.purpose} ${item.preparedBy} ${item.decision} ${item.recommendations}`.toLowerCase().includes(query))).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    const finalCount = allReports().filter((item) => item.reviewStatus === "final").length;
    const casesWithReports = new Set(allReports().map((item) => item.caseId)).size;
    stats.innerHTML = `<article class="stat-card"><span>إصدارات التقارير</span><strong>${allReports().length}</strong></article><article class="stat-card"><span>تقارير نهائية داخليًا</span><strong>${finalCount}</strong></article><article class="stat-card"><span>حالات لها تقارير</span><strong>${casesWithReports}</strong></article><article class="stat-card"><span>الحالات دون تقرير</span><strong>${Math.max(store.cases.length - casesWithReports, 0)}</strong></article>`;
    list.innerHTML = reports.length ? reports.map((item) => `<article class="report-card"><header><div><span class="badge ${item.reviewStatus === "final" ? "success" : "neutral"}">${esc(statusLabel(item.reviewStatus))}</span><h3>${esc(item.caseAlias)} — ${esc(item.reportType)}</h3><p>${esc(item.purpose)}</p></div><div><time>${esc(item.reportDate)}</time><div class="code small">${esc(item.reportId)}</div></div></header><dl class="report-meta"><div><dt>الإصدار</dt><dd>${item.versionNumber}</dd></div><div><dt>الجلسات المصدرية</dt><dd>${item.sourceSessionCount}</dd></div><div><dt>التطبيقات المهنية</dt><dd>${item.sourceProfessionalCount}</dd></div><div><dt>القرار</dt><dd>${esc(nextLabel(item.decision))}</dd></div></dl><div class="report-actions"><button class="button primary small-button" type="button" data-open-report="${esc(item.reportId)}" data-report-case="${esc(item.caseId)}">فتح التقرير</button><button class="button ghost small-button" type="button" data-new-version="${esc(item.caseId)}">إصدار جديد</button></div></article>`).join("") : '<div class="empty-state">لا توجد تقارير مطابقة.</div>';
  };

  const download = (name, type, content) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  };

  const currentReportPayload = () => {
    const form = document.getElementById("case-report-form");
    const data = formDataObject(form);
    const caseRecord = caseById(data.caseId);
    return { data, caseRecord, html: caseRecord ? reportHtml(caseRecord, data) : "" };
  };

  const printCurrent = () => {
    document.body.classList.add("report-print-mode");
    window.print();
    setTimeout(() => document.body.classList.remove("report-print-mode"), 100);
  };

  installStyles();
  installView();
  installDialog();

  const originalRender = render;
  render = function reportAwareRender() {
    originalRender();
    renderReports();
  };

  document.getElementById("case-report-form")?.addEventListener("input", refreshPreview);
  document.getElementById("case-report-form")?.addEventListener("change", refreshPreview);
  document.getElementById("case-report-form")?.addEventListener("submit", saveReport);
  document.getElementById("report-case-filter")?.addEventListener("change", renderReports);
  document.getElementById("report-search")?.addEventListener("input", renderReports);
  document.getElementById("new-case-report")?.addEventListener("click", () => openReport());
  document.getElementById("print-case-report")?.addEventListener("click", printCurrent);
  document.getElementById("export-case-report-html")?.addEventListener("click", () => {
    const { data, caseRecord, html } = currentReportPayload();
    if (!caseRecord) return;
    const documentHtml = `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير ${esc(caseRecord.alias)}</title><style>body{font-family:Tahoma,Arial,sans-serif;line-height:1.8;max-width:1000px;margin:auto;padding:30px;color:#173f43}section{margin:24px 0}table{width:100%;border-collapse:collapse}th,td{border:1px solid #b9d7d4;padding:8px;text-align:right;vertical-align:top}.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.summary-grid div{border:1px solid #c8e2df;border-radius:10px;padding:8px}.report-disclaimer{background:#fff8df;border-right:5px solid #b88912;padding:12px}</style></head><body>${html}</body></html>`;
    download(`report-${caseRecord.caseId}-${data.reportDate || "draft"}.html`, "text/html;charset=utf-8", documentHtml);
  });
  document.getElementById("export-case-report-json")?.addEventListener("click", () => {
    const { data, caseRecord } = currentReportPayload();
    if (!caseRecord) return;
    download(`report-${caseRecord.caseId}-${data.reportDate || "draft"}.json`, "application/json;charset=utf-8", JSON.stringify({ schema: "pa-case-report-v1", ownerUid: identity.uid, caseId: caseRecord.caseId, report: data, sourceCounts: { sessions: (caseRecord.sessions || []).length, professionalAssessments: (caseRecord.professionalAssessments || []).length } }, null, 2));
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.openReport) openReport(button.dataset.reportCase, button.dataset.openReport);
    if (button.dataset.newVersion) openReport(button.dataset.newVersion);
    if (button.dataset.caseReport) openReport(button.dataset.caseReport);
  });

  const caseObserver = new MutationObserver(() => {
    const actions = document.querySelector("#case-detail-content .dialog-actions");
    if (!actions || actions.querySelector("[data-case-report]") || !selectedCase) return;
    const button = document.createElement("button");
    button.className = "button secondary";
    button.type = "button";
    button.dataset.caseReport = selectedCase;
    button.textContent = "إنشاء تقرير مهني";
    actions.prepend(button);
  });
  const caseContent = document.getElementById("case-detail-content");
  if (caseContent) caseObserver.observe(caseContent, { childList: true, subtree: true });

  renderReports();
})();
