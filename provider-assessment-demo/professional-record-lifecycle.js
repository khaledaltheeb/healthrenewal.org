"use strict";

(() => {
  const STATUS = {
    planned: "مخطط",
    scheduled: "موعد محدد",
    in_progress: "قيد التنفيذ",
    completed: "مكتمل",
    result_imported: "تقرير خارجي مستلم",
    incomplete_invalid: "غير مكتمل أو غير صالح",
    cancelled: "ملغى",
  };

  const TRANSITIONS = {
    planned: ["scheduled", "in_progress", "cancelled"],
    scheduled: ["in_progress", "cancelled"],
    in_progress: ["completed", "result_imported", "incomplete_invalid", "cancelled"],
    completed: ["incomplete_invalid"],
    result_imported: ["incomplete_invalid"],
    incomplete_invalid: ["planned", "scheduled", "cancelled"],
    cancelled: ["planned"],
  };

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

  function installDialog() {
    if (document.getElementById("professional-lifecycle-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "professional-lifecycle-dialog";
    dialog.className = "dialog large";
    dialog.innerHTML = `
      <form method="dialog" id="professional-lifecycle-form">
        <div class="dialog-heading">
          <div><p class="eyebrow">تحديث مضبوط مع سجل تدقيق</p><h2>تحديث حالة السجل المهني</h2></div>
          <button class="icon-button" value="cancel" aria-label="إغلاق">×</button>
        </div>
        <input type="hidden" name="recordId">
        <div id="professional-lifecycle-summary" class="callout info"></div>
        <div class="form-grid">
          <label class="field"><span>الحالة الجديدة</span><select name="recordStatus" required></select></label>
          <label class="field"><span>تاريخ السريان</span><input name="effectiveDate" type="date" required></label>
        </div>
        <label class="field"><span>سبب التحديث أو الملاحظة المهنية</span><textarea name="changeReason" rows="4" minlength="5" maxlength="1000" required placeholder="اذكر ما تغير، مصدر المعلومة، وحدود القرار"></textarea></label>
        <label class="field"><span>الخلاصة المهنية المحدثة</span><input name="outcomeLabel" maxlength="240" required></label>
        <label class="field"><span>الخطوة التالية</span><select name="nextAction" required>
          <option value="review">مراجعة النتيجة مع المختص</option>
          <option value="another_tool">إضافة مقياس مكمل</option>
          <option value="collect_sources">جمع مصادر معلومات إضافية</option>
          <option value="team_review">مراجعة فريق متعدد التخصصات</option>
          <option value="support_plan">إعداد خطة دعم</option>
          <option value="close">إغلاق مسار التقييم</option>
          <option value="urgent_safety">اتباع مسار السلامة العاجل</option>
        </select></label>
        <div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">حفظ التحديث</button></div>
      </form>`;
    document.body.appendChild(dialog);
  }

  function openLifecycle(recordId) {
    const found = findRecord(recordId);
    if (!found) return toast("تعذر العثور على السجل المهني.");
    const { record } = found;
    const form = document.getElementById("professional-lifecycle-form");
    const select = form.elements.recordStatus;
    const allowed = TRANSITIONS[record.recordStatus] || [];
    select.innerHTML = allowed.length
      ? allowed.map((value) => `<option value="${esc(value)}">${esc(STATUS[value] || value)}</option>`).join("")
      : `<option value="${esc(record.recordStatus)}">لا يوجد انتقال متاح</option>`;
    select.disabled = allowed.length === 0;
    form.querySelector('button[type="submit"]').disabled = allowed.length === 0;
    form.elements.recordId.value = record.recordId;
    form.elements.effectiveDate.value = new Date().toISOString().slice(0, 10);
    form.elements.changeReason.value = "";
    form.elements.outcomeLabel.value = record.outcomeLabel || "";
    form.elements.nextAction.value = record.nextAction || "review";
    document.getElementById("professional-lifecycle-summary").textContent = `${record.toolName} — الحالة الحالية: ${STATUS[record.recordStatus] || record.recordStatus}.`;
    if (typeof open === "function") open(document.getElementById("professional-lifecycle-dialog"));
    else document.getElementById("professional-lifecycle-dialog").showModal();
  }

  function saveLifecycle(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const found = findRecord(String(data.get("recordId") || ""));
    if (!found) return toast("تعذر العثور على السجل المهني.");
    const { caseRecord, record } = found;
    const nextStatus = String(data.get("recordStatus") || "");
    const allowed = TRANSITIONS[record.recordStatus] || [];
    if (!allowed.includes(nextStatus)) return toast("الانتقال المطلوب غير مسموح ضمن دورة العمل الحالية.");

    const now = new Date().toISOString();
    record.auditTrail ||= [];
    record.auditTrail.push({
      auditId: typeof id === "function" ? id("AUD") : `AUD-${Date.now()}`,
      changedAt: now,
      effectiveDate: String(data.get("effectiveDate") || ""),
      changedByUid: identity.uid,
      changedByRole: identity.role,
      fromStatus: record.recordStatus,
      toStatus: nextStatus,
      reason: String(data.get("changeReason") || "").trim(),
      previousOutcomeLabel: record.outcomeLabel || "",
      previousNextAction: record.nextAction || "",
    });
    record.recordStatus = nextStatus;
    record.outcomeLabel = String(data.get("outcomeLabel") || "").trim();
    record.nextAction = String(data.get("nextAction") || "review");
    record.lastUpdatedAt = now;
    record.lastUpdatedByUid = identity.uid;
    caseRecord.updatedAt = now;
    save();
    render();
    document.getElementById("professional-lifecycle-dialog").close();
    toast("تم تحديث السجل مع حفظ أثر التدقيق.");
  }

  function enhanceCards() {
    document.querySelectorAll(".professional-record").forEach((card) => {
      if (card.querySelector("[data-lifecycle-record]")) return;
      const recordId = card.querySelector(".code.small")?.textContent?.trim();
      const found = findRecord(recordId);
      if (!found) return;
      const actions = document.createElement("div");
      actions.className = "professional-card-actions";
      actions.innerHTML = `<button class="button secondary small-button" type="button" data-lifecycle-record="${esc(recordId)}">تحديث الحالة</button>
        <details class="audit-details"><summary>سجل التدقيق (${found.record.auditTrail?.length || 0})</summary><ol>${(found.record.auditTrail || []).slice().reverse().map((entry) => `<li><strong>${esc(STATUS[entry.fromStatus] || entry.fromStatus)} ← ${esc(STATUS[entry.toStatus] || entry.toStatus)}</strong><br><span>${esc(entry.reason)}</span><br><time>${esc(entry.changedAt)}</time></li>`).join("") || "<li>لا توجد تحديثات لاحقة.</li>"}</ol></details>`;
      card.appendChild(actions);
    });
  }

  installDialog();
  document.getElementById("professional-lifecycle-form")?.addEventListener("submit", saveLifecycle);
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-lifecycle-record]");
    if (button) openLifecycle(button.dataset.lifecycleRecord);
  });

  const observer = new MutationObserver(enhanceCards);
  observer.observe(document.body, { childList: true, subtree: true });
  enhanceCards();
})();
