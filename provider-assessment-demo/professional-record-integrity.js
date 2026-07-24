"use strict";

(() => {
  const FIELD_LABELS = {
    administrationDate: "تاريخ التطبيق أو التخطيط",
    assignedEntityLabel: "الجهة أو الدور المنفذ",
    performerName: "اسم المنفذ",
    practitionerQualification: "المؤهل أو الصفة المهنية",
    administrationMode: "طريقة التطبيق",
    versionLanguage: "الإصدار واللغة",
    resultSourceType: "مصدر النتيجة",
    reportReference: "مرجع التقرير أو الوثيقة",
    reportIssuedBy: "الجهة المصدرة للتقرير",
    outcomeLabel: "الخلاصة المهنية",
    scoreReference: "الدرجة أو المرجع المسجل",
    notes: "الملاحظات وحدود التفسير",
    nextAction: "الخطوة التالية",
  };

  const STATUS_LABELS = {
    planned: "مخطط",
    scheduled: "موعد محدد",
    in_progress: "قيد التنفيذ",
    completed: "مكتمل",
    result_imported: "تقرير خارجي مستلم",
    incomplete_invalid: "غير مكتمل أو غير صالح",
    cancelled: "ملغى",
  };

  const SOURCE_LABELS = {
    direct_administration: "تطبيق مباشر موثق",
    external_report: "تقرير خارجي صادر عن جهة مختصة",
    record_review: "مراجعة سجل أو وثيقة",
    interview_observation: "مقابلة أو ملاحظة مهنية",
    other: "مصدر آخر موثق",
  };

  const NEXT_LABELS = {
    review: "مراجعة النتيجة مع المختص",
    another_tool: "إضافة مقياس مكمل",
    collect_sources: "جمع مصادر معلومات إضافية",
    team_review: "مراجعة فريق متعدد التخصصات",
    support_plan: "إعداد خطة دعم",
    close: "إغلاق مسار التقييم",
    urgent_safety: "اتباع مسار السلامة العاجل",
  };

  const MODE_LABELS = {
    in_person: "حضوري",
    remote: "عن بُعد",
    external_import: "استيراد نتيجة خارجية",
    record_review: "مراجعة سجل أو تقرير",
    other: "أخرى",
  };

  const EDITABLE_FIELDS = [
    "administrationDate",
    "assignedEntityLabel",
    "performerName",
    "practitionerQualification",
    "administrationMode",
    "versionLanguage",
    "resultSourceType",
    "reportReference",
    "reportIssuedBy",
    "outcomeLabel",
    "scoreReference",
    "notes",
    "nextAction",
  ];

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const allRecords = () => store.cases.flatMap((caseRecord) =>
    (caseRecord.professionalAssessments || []).map((record) => ({ caseRecord, record }))
  );

  const findRecord = (recordId) => allRecords().find(({ record }) => record.recordId === recordId) || null;

  const defaultSource = (record) => {
    if (record.resultSourceType) return record.resultSourceType;
    if (record.administrationMode === "external_import") return "external_report";
    if (record.administrationMode === "record_review") return "record_review";
    return "direct_administration";
  };

  const normaliseRecord = (record) => {
    record.practitionerQualification ||= "";
    record.resultSourceType ||= defaultSource(record);
    record.reportReference ||= "";
    record.reportIssuedBy ||= "";
    record.metadataAuditTrail ||= [];
  };

  const recordEvents = (record) => {
    const creation = [{
      eventId: `CREATE-${record.recordId}`,
      eventType: "created",
      eventAt: record.recordedAt,
      title: "إنشاء السجل المهني",
      detail: `أُنشئ بواسطة ${record.recordedByRole || "دور غير مسجل"} داخل UID ${record.recordedByUid || "غير مسجل"}.`,
    }];

    const lifecycle = (record.auditTrail || []).map((entry) => ({
      eventId: entry.auditId,
      eventType: "status_changed",
      eventAt: entry.changedAt,
      title: `${STATUS_LABELS[entry.fromStatus] || entry.fromStatus} ← ${STATUS_LABELS[entry.toStatus] || entry.toStatus}`,
      detail: entry.reason || "تحديث حالة دون ملاحظة مسجلة.",
      actor: entry.changedByUid,
      effectiveDate: entry.effectiveDate,
    }));

    const metadata = (record.metadataAuditTrail || []).map((entry) => ({
      eventId: entry.auditId,
      eventType: "metadata_updated",
      eventAt: entry.changedAt,
      title: "تعديل بيانات السجل",
      detail: entry.reason,
      actor: entry.changedByUid,
      changes: entry.changes || [],
    }));

    return [...creation, ...lifecycle, ...metadata]
      .filter((event) => event.eventAt)
      .sort((a, b) => new Date(b.eventAt) - new Date(a.eventAt));
  };

  function installStyles() {
    if (document.getElementById("professional-record-integrity-styles")) return;
    const style = document.createElement("style");
    style.id = "professional-record-integrity-styles";
    style.textContent = `
      .record-integrity-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
      .record-event-log{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
      .record-event-log summary{cursor:pointer;font-weight:700;color:#155e59}
      .record-event-log ol{margin:10px 0 0;padding-inline-start:22px}
      .record-event-log li{margin:0 0 10px}
      .record-event-log small{display:block;color:var(--muted);margin-top:3px}
      .record-change-list{margin:6px 0 0;padding-inline-start:18px}
      .record-integrity-badge{display:inline-flex;align-items:center;gap:6px;margin-top:8px;font-size:.86rem;color:#0b5f5a}
      @media print{.record-integrity-actions,.professional-card-actions{display:none!important}.professional-record{break-inside:avoid}}
    `;
    document.head.appendChild(style);
  }

  function installDialog() {
    if (document.getElementById("professional-record-edit-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "professional-record-edit-dialog";
    dialog.className = "dialog xlarge";
    dialog.innerHTML = `
      <form method="dialog" id="professional-record-edit-form">
        <div class="dialog-heading">
          <div><p class="eyebrow">تصحيح موثق دون طمس السجل السابق</p><h2>تحرير بيانات السجل المهني</h2></div>
          <button class="icon-button" value="cancel" aria-label="إغلاق">×</button>
        </div>
        <input type="hidden" name="recordId">
        <div id="professional-record-edit-summary" class="callout info"></div>
        <div class="form-grid">
          <label class="field"><span>تاريخ التطبيق أو التخطيط</span><input name="administrationDate" type="date" required></label>
          <label class="field"><span>الجهة أو الدور المنفذ</span><input name="assignedEntityLabel" maxlength="120" required></label>
          <label class="field"><span>اسم المنفذ</span><input name="performerName" maxlength="120"></label>
          <label class="field"><span>المؤهل أو الصفة المهنية</span><input name="practitionerQualification" maxlength="180" placeholder="مثال: أخصائي نفسي مرخص، أخصائي نطق ولغة"></label>
          <label class="field"><span>طريقة التطبيق</span><select name="administrationMode" required>
            <option value="in_person">حضوري</option><option value="remote">عن بُعد</option><option value="external_import">استيراد نتيجة خارجية</option><option value="record_review">مراجعة سجل أو تقرير</option><option value="other">أخرى</option>
          </select></label>
          <label class="field"><span>الإصدار واللغة</span><input name="versionLanguage" maxlength="160" placeholder="اسم النسخة واللغة والإصدار دون نسخ مواد محمية"></label>
          <label class="field"><span>مصدر النتيجة</span><select name="resultSourceType" required>
            <option value="direct_administration">تطبيق مباشر موثق</option><option value="external_report">تقرير خارجي صادر عن جهة مختصة</option><option value="record_review">مراجعة سجل أو وثيقة</option><option value="interview_observation">مقابلة أو ملاحظة مهنية</option><option value="other">مصدر آخر موثق</option>
          </select></label>
          <label class="field"><span>مرجع التقرير أو الوثيقة</span><input name="reportReference" maxlength="240" placeholder="رقم داخلي أو اسم ملف محلي غير حساس"></label>
          <label class="field"><span>الجهة المصدرة للتقرير</span><input name="reportIssuedBy" maxlength="180" placeholder="اسم الجهة أو الدور دون بيانات شخصية حساسة"></label>
          <label class="field"><span>الخلاصة المهنية</span><input name="outcomeLabel" maxlength="240" required></label>
          <label class="field"><span>الدرجة أو المرجع المسجل</span><input name="scoreReference" maxlength="240" placeholder="لا تدخل مفاتيح تصحيح أو معايير محمية"></label>
          <label class="field"><span>الخطوة التالية</span><select name="nextAction" required>
            <option value="review">مراجعة النتيجة مع المختص</option><option value="another_tool">إضافة مقياس مكمل</option><option value="collect_sources">جمع مصادر معلومات إضافية</option><option value="team_review">مراجعة فريق متعدد التخصصات</option><option value="support_plan">إعداد خطة دعم</option><option value="close">إغلاق مسار التقييم</option><option value="urgent_safety">اتباع مسار السلامة العاجل</option>
          </select></label>
        </div>
        <label class="field"><span>الملاحظات وحدود التفسير</span><textarea name="notes" rows="5" maxlength="3000"></textarea></label>
        <label class="field"><span>سبب التصحيح</span><textarea name="editReason" rows="3" minlength="5" maxlength="1000" required placeholder="اذكر لماذا عُدلت البيانات وما مصدر التصحيح"></textarea></label>
        <label class="rights-confirmation"><input name="rightsConfirmed" type="checkbox" required><span>أؤكد أن التعديل لا يتضمن بنودًا أو مفاتيح تصحيح أو معايير محمية، وأن مرجع التقرير وبيانات المؤهل موثقة قدر الإمكان.</span></label>
        <p class="professional-form-note">تُحفظ القيم السابقة ضمن سجل التدقيق المحلي ولا تتوفر وظيفة لحذف أثر التعديل من الواجهة.</p>
        <div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">حفظ التصحيح الموثق</button></div>
      </form>`;
    document.body.appendChild(dialog);
  }

  function openEditor(recordId) {
    const found = findRecord(recordId);
    if (!found) return toast("تعذر العثور على السجل المهني.");
    const { record } = found;
    normaliseRecord(record);
    const form = document.getElementById("professional-record-edit-form");
    form.reset();
    form.elements.recordId.value = record.recordId;
    EDITABLE_FIELDS.forEach((field) => {
      if (form.elements[field]) form.elements[field].value = record[field] || "";
    });
    form.elements.resultSourceType.value = defaultSource(record);
    form.elements.rightsConfirmed.checked = false;
    document.getElementById("professional-record-edit-summary").textContent = `${record.toolName} — ${STATUS_LABELS[record.recordStatus] || record.recordStatus}. لا يمكن تغيير حالة التطبيق من شاشة التحرير؛ استخدم دورة الحياة المخصصة.`;
    if (typeof open === "function") open(document.getElementById("professional-record-edit-dialog"));
    else document.getElementById("professional-record-edit-dialog").showModal();
  }

  function saveEditor(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const found = findRecord(String(data.get("recordId") || ""));
    if (!found) return toast("تعذر العثور على السجل المهني.");
    const { caseRecord, record } = found;
    normaliseRecord(record);

    const nextValues = {};
    const changes = [];
    EDITABLE_FIELDS.forEach((field) => {
      const value = String(data.get(field) || "").trim();
      nextValues[field] = value;
      const previous = String(record[field] || "");
      if (previous !== value) changes.push({ field, label: FIELD_LABELS[field] || field, from: previous, to: value });
    });

    if (!changes.length) {
      toast("لم تُسجل تغييرات جديدة.");
      return;
    }

    const now = new Date().toISOString();
    record.metadataAuditTrail.push({
      auditId: typeof id === "function" ? id("META") : `META-${Date.now()}`,
      eventType: "metadata_updated",
      changedAt: now,
      changedByUid: identity.uid,
      changedByRole: identity.role,
      reason: String(data.get("editReason") || "").trim(),
      changes,
    });
    Object.assign(record, nextValues, {
      rightsConfirmed: data.get("rightsConfirmed") === "on",
      lastUpdatedAt: now,
      lastUpdatedByUid: identity.uid,
      lastUpdatedByRole: identity.role,
      integrityVersion: "1.0.0",
    });
    caseRecord.updatedAt = now;
    save();
    render();
    document.getElementById("professional-record-edit-dialog").close();
    toast("تم حفظ التصحيح مع الاحتفاظ بالقيم السابقة في سجل التدقيق.");
  }

  function eventHtml(event) {
    const changes = event.changes?.length
      ? `<ul class="record-change-list">${event.changes.map((change) => `<li><strong>${esc(change.label || change.field)}:</strong> ${esc(change.from || "غير مسجل")} ← ${esc(change.to || "غير مسجل")}</li>`).join("")}</ul>`
      : "";
    const meta = [event.actor ? `UID: ${event.actor}` : "", event.effectiveDate ? `سريان: ${event.effectiveDate}` : ""].filter(Boolean).join(" — ");
    return `<li><strong>${esc(event.title)}</strong><div>${esc(event.detail || "")}</div>${changes}<small>${esc(new Date(event.eventAt).toLocaleString("ar-JO"))}${meta ? ` — ${esc(meta)}` : ""}</small></li>`;
  }

  function printableDocument(caseRecord, record) {
    const events = recordEvents(record);
    return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>سجل مهني — ${esc(record.toolName)}</title><style>
      body{font-family:Arial,sans-serif;line-height:1.7;color:#17343a;margin:32px}h1,h2{color:#0b5f5a}header{border-bottom:2px solid #0b5f5a;margin-bottom:22px;padding-bottom:12px}dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}dl div{border:1px solid #cbdedb;border-radius:10px;padding:10px}dt{font-size:.85rem;color:#587074}dd{margin:4px 0 0;font-weight:700}.note{white-space:pre-wrap}.warning{border:1px solid #d4b65d;background:#fff9e8;padding:12px;border-radius:10px}li{margin-bottom:10px}small{color:#587074}@media print{body{margin:12mm}}
    </style></head><body><header><p>منصة التقييم والسجل المهني</p><h1>${esc(record.toolName)}</h1><p>${esc(caseRecord.alias)} — ${esc(caseRecord.caseId)} — ${esc(record.recordId)}</p></header>
    <div class="warning">هذا تقرير توثيق محلي لسير العمل، وليس نسخة من أداة محمية ولا تقرير تشخيص آلي أو إثبات أهلية قانونية.</div>
    <h2>بيانات التطبيق</h2><dl>
      <div><dt>الحالة</dt><dd>${esc(STATUS_LABELS[record.recordStatus] || record.recordStatus)}</dd></div><div><dt>التاريخ</dt><dd>${esc(record.administrationDate || "غير مسجل")}</dd></div>
      <div><dt>المنفذ</dt><dd>${esc(record.assignedEntityLabel || "غير مسجل")}${record.performerName ? ` — ${esc(record.performerName)}` : ""}</dd></div><div><dt>المؤهل</dt><dd>${esc(record.practitionerQualification || "غير مسجل")}</dd></div>
      <div><dt>طريقة التطبيق</dt><dd>${esc(MODE_LABELS[record.administrationMode] || record.administrationMode || "غير مسجل")}</dd></div><div><dt>الإصدار واللغة</dt><dd>${esc(record.versionLanguage || "غير مسجل")}</dd></div>
      <div><dt>مصدر النتيجة</dt><dd>${esc(SOURCE_LABELS[defaultSource(record)] || defaultSource(record))}</dd></div><div><dt>مرجع التقرير</dt><dd>${esc(record.reportReference || record.scoreReference || "غير مسجل")}</dd></div>
      <div><dt>الجهة المصدرة</dt><dd>${esc(record.reportIssuedBy || "غير مسجل")}</dd></div><div><dt>الخطوة التالية</dt><dd>${esc(NEXT_LABELS[record.nextAction] || record.nextAction || "غير مسجل")}</dd></div>
    </dl><h2>الخلاصة</h2><p>${esc(record.outcomeLabel || "غير مسجل")}</p>${record.notes ? `<h2>الملاحظات وحدود التفسير</h2><p class="note">${esc(record.notes)}</p>` : ""}
    <h2>سجل الأحداث</h2><ol>${events.map(eventHtml).join("")}</ol><script>window.addEventListener("load",()=>window.print())<\/script></body></html>`;
  }

  function printRecord(recordId) {
    const found = findRecord(recordId);
    if (!found) return toast("تعذر العثور على السجل المهني.");
    const popup = window.open("", "_blank");
    if (!popup) return toast("تعذر فتح نافذة الطباعة. اسمح بالنوافذ المنبثقة لهذه الصفحة.");
    popup.opener = null;
    popup.document.open();
    popup.document.write(printableDocument(found.caseRecord, found.record));
    popup.document.close();
  }

  function cardRecordId(card) {
    const codes = card.querySelectorAll(".code.small");
    return codes.length ? codes[codes.length - 1].textContent.trim() : "";
  }

  function enhanceCards() {
    allRecords().forEach(({ record }) => normaliseRecord(record));
    document.querySelectorAll(".professional-record").forEach((card) => {
      const recordId = cardRecordId(card);
      const found = findRecord(recordId);
      if (!found) return;
      card.dataset.recordId = recordId;
      if (card.querySelector("[data-record-integrity]")) return;
      const events = recordEvents(found.record);
      const wrapper = document.createElement("div");
      wrapper.dataset.recordIntegrity = "true";
      wrapper.innerHTML = `<div class="record-integrity-actions"><button class="button secondary small-button" type="button" data-edit-professional-record="${esc(recordId)}">تحرير البيانات</button><button class="button ghost small-button" type="button" data-print-professional-record="${esc(recordId)}">طباعة السجل</button></div>
        <span class="record-integrity-badge">سجل إنشاء وتعديلات محفوظ محليًا — ${events.length} حدث</span>
        <details class="record-event-log"><summary>سجل الأحداث الموحد (${events.length})</summary><ol>${events.map(eventHtml).join("")}</ol></details>`;
      card.appendChild(wrapper);
    });
  }

  installStyles();
  installDialog();
  document.getElementById("professional-record-edit-form")?.addEventListener("submit", saveEditor);
  document.addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-edit-professional-record]");
    if (editButton) openEditor(editButton.dataset.editProfessionalRecord);
    const printButton = event.target.closest("[data-print-professional-record]");
    if (printButton) printRecord(printButton.dataset.printProfessionalRecord);
  });

  const observer = new MutationObserver(enhanceCards);
  observer.observe(document.body, { childList: true, subtree: true });
  enhanceCards();
})();
