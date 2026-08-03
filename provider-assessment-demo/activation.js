"use strict";

(() => {
  const activationVersion = "1.0.0";
  const professionalList = document.getElementById("professional-list");
  const professionalSearch = document.getElementById("professional-search");
  const professionalFilter = document.getElementById("professional-category-filter");
  const guidePanel = document.getElementById("view-guide");
  const tabs = document.querySelector(".tabs");

  if (!professionalList || !professionalSearch || !professionalFilter || !guidePanel || !tabs) return;

  const professionalRecords = () => store.cases.flatMap((caseRecord) =>
    (caseRecord.professionalAssessments || []).map((record) => ({
      ...record,
      caseId: caseRecord.caseId,
      caseAlias: caseRecord.alias,
    }))
  );

  const statusLabel = (value) => ({
    planned: "مخطط",
    scheduled: "موعد محدد",
    in_progress: "قيد التطبيق",
    completed: "مكتمل",
    result_imported: "نتيجة مستلمة",
    incomplete_invalid: "غير مكتمل أو غير صالح",
    cancelled: "ملغى",
  })[value] || value;

  const nextLabel = (value) => ({
    review: "مراجعة النتيجة مع المختص",
    another_tool: "إضافة مقياس مكمل",
    collect_sources: "جمع مصادر معلومات إضافية",
    team_review: "مراجعة فريق متعدد التخصصات",
    support_plan: "إعداد خطة دعم",
    close: "إغلاق مسار التقييم",
    urgent_safety: "اتباع مسار السلامة العاجل",
  })[value] || value;

  const installStyles = () => {
    if (document.getElementById("assessment-activation-styles")) return;
    const style = document.createElement("style");
    style.id = "assessment-activation-styles";
    style.textContent = `
      .professional-operational-bar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin:0 0 18px;padding:16px 18px;border:1px solid #9fd5cf;border-radius:16px;background:#eefaf8}
      .professional-operational-bar p{margin:0;color:#345e61}.professional-operational-bar strong{display:block;color:#0b5f5a}
      .professional-card-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.professional-card-actions .button{text-decoration:none}
      .professional-records-grid{display:grid;gap:12px}.professional-record{border:1px solid var(--line);border-radius:18px;padding:18px;background:#fff}
      .professional-record header{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.professional-record h3{margin:.25rem 0}.professional-record dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}.professional-record dl div{background:#f4faf9;border-radius:12px;padding:10px}.professional-record dt{font-size:.82rem;color:var(--muted)}.professional-record dd{margin:3px 0 0;font-weight:700}
      .professional-record-notes{white-space:pre-wrap}.professional-record-toolbar{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
      .professional-form-note{font-size:.92rem;color:var(--muted);margin-top:-4px}.rights-confirmation{display:flex;gap:10px;align-items:flex-start;border:1px solid #e4c97a;background:#fff9e7;border-radius:14px;padding:12px}
      @media(max-width:800px){.professional-record dl,.professional-record-toolbar{grid-template-columns:1fr}.professional-record header{flex-direction:column}}
    `;
    document.head.appendChild(style);
  };

  const installRecordsView = () => {
    if (document.getElementById("view-professional-records")) return;

    const tab = document.createElement("button");
    tab.className = "tab";
    tab.type = "button";
    tab.dataset.view = "professional-records";
    tab.setAttribute("aria-selected", "false");
    tab.textContent = "السجل المهني";
    const guideTab = tabs.querySelector('[data-view="guide"]');
    tabs.insertBefore(tab, guideTab);

    const panel = document.createElement("section");
    panel.id = "view-professional-records";
    panel.className = "view";
    panel.dataset.viewPanel = "professional-records";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="section-heading">
        <div><p class="eyebrow">تخطيط وتوثيق ومتابعة</p><h2>سجل التطبيقات المهنية</h2></div>
        <button id="professional-record-new" class="button primary" type="button">إضافة تطبيق مهني</button>
      </div>
      <div class="callout info">هذا السجل يدير سير العمل والنتائج والملاحظات. لا ينسخ بنود المقاييس أو مفاتيح التصحيح المحمية، ولا يحول النتيجة إلى تشخيص آلي.</div>
      <div class="professional-record-toolbar">
        <label class="field"><span>الحالة</span><select id="professional-record-case-filter"><option value="">جميع الحالات</option></select></label>
        <label class="field"><span>البحث</span><input id="professional-record-search" type="search" placeholder="اسم المقياس، المنفذ، النتيجة أو الملاحظة"></label>
      </div>
      <div id="professional-record-stats" class="stats-grid"></div>
      <div id="professional-record-list" class="professional-records-grid"></div>`;
    guidePanel.before(panel);
  };

  const installRecordDialog = () => {
    if (document.getElementById("professional-record-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "professional-record-dialog";
    dialog.className = "dialog xlarge";
    dialog.innerHTML = `
      <form method="dialog" id="professional-record-form">
        <div class="dialog-heading">
          <div><p class="eyebrow">مسار مهني مرتبط بسجل الحالة</p><h2 id="professional-record-title">إضافة تطبيق مهني</h2></div>
          <button class="icon-button" value="cancel" aria-label="إغلاق">×</button>
        </div>
        <input type="hidden" name="toolId"><input type="hidden" name="toolName"><input type="hidden" name="category">
        <div class="form-grid">
          <label class="field"><span>الحالة</span><select name="caseId" required></select></label>
          <label class="field"><span>حالة التطبيق</span><select name="recordStatus" required>
            <option value="planned">مخطط</option><option value="scheduled">موعد محدد</option><option value="in_progress">قيد التطبيق</option><option value="completed">مكتمل</option><option value="result_imported">نتيجة مستلمة</option><option value="incomplete_invalid">غير مكتمل أو غير صالح</option><option value="cancelled">ملغى</option>
          </select></label>
          <label class="field"><span>تاريخ التطبيق أو التخطيط</span><input name="administrationDate" type="date" required></label>
          <label class="field"><span>الجهة أو الدور المنفذ</span><input name="assignedEntityLabel" maxlength="120" placeholder="أخصائي نفسي، أخصائي نطق، مركز..." required></label>
          <label class="field"><span>اسم المنفذ</span><input name="performerName" maxlength="120" placeholder="اختياري"></label>
          <label class="field"><span>طريقة التطبيق</span><select name="administrationMode" required><option value="in_person">حضوري</option><option value="remote">عن بُعد</option><option value="external_import">استيراد نتيجة خارجية</option><option value="record_review">مراجعة سجل أو تقرير</option><option value="other">أخرى</option></select></label>
          <label class="field"><span>الإصدار واللغة</span><input name="versionLanguage" maxlength="160" placeholder="مثال: النسخة العربية المرخصة، إصدار 2025"></label>
          <label class="field"><span>الخلاصة المهنية المسجلة</span><input name="outcomeLabel" maxlength="240" placeholder="وصف موجز دون تشخيص آلي" required></label>
          <label class="field"><span>الدرجة أو مرجع التقرير</span><input name="scoreReference" maxlength="240" placeholder="اختياري؛ لا تدخل مفاتيح تصحيح محمية"></label>
          <label class="field"><span>الخطوة التالية</span><select name="nextAction" required><option value="review">مراجعة النتيجة مع المختص</option><option value="another_tool">إضافة مقياس مكمل</option><option value="collect_sources">جمع مصادر معلومات إضافية</option><option value="team_review">مراجعة فريق متعدد التخصصات</option><option value="support_plan">إعداد خطة دعم</option><option value="close">إغلاق مسار التقييم</option><option value="urgent_safety">اتباع مسار السلامة العاجل</option></select></label>
        </div>
        <label class="field"><span>الملاحظات والتفسير وحدود التطبيق</span><textarea name="notes" rows="5" maxlength="3000" placeholder="السياق، مصدر البيانات، القيود، ما يجب متابعته..."></textarea></label>
        <label class="rights-confirmation"><input name="rightsConfirmed" type="checkbox" required><span>أؤكد أن أي تطبيق رسمي تم باستخدام نسخة أصلية مصرح بها، بواسطة شخص مؤهل، ووفق حقوق الاستخدام والرقمنة المعمول بها.</span></label>
        <p class="professional-form-note">يُحفظ السجل محليًا داخل UID الحالي. لا تدخل أسماء كاملة أو أرقام هوية أو ملفات طبية حساسة في النسخة العامة.</p>
        <div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" value="default" type="submit">حفظ السجل المهني</button></div>
      </form>`;
    document.body.appendChild(dialog);
  };

  const patchStaticCopy = () => {
    document.title = "منصة التقييم وإدارة السجلات | منصة روافد";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية تشغيلية لإدارة الحالات والجلسات الاستكشافية ومسارات تطبيق المقاييس المهنية وتوثيق النتائج محليًا ضمن UID مستقل.";

    const notice = document.querySelector(".notice-bar");
    if (notice) notice.textContent = "الأدوات الاستكشافية لا تنتج تشخيصًا أو أهلية قانونية. مسارات المقاييس المهنية متاحة للتخطيط والتوثيق، بينما تبقى البنود ومفاتيح التصحيح المحمية مرتبطة بالترخيص والمؤهل المهني.";

    const heroEyebrow = document.querySelector(".hero .eyebrow");
    if (heroEyebrow) heroEyebrow.textContent = "نسخة تشغيل محلية لإدارة الحالات ومسارات التقييم";
    const heroTitle = document.getElementById("hero-title");
    if (heroTitle) heroTitle.textContent = "أنشئ حالة، نفّذ جلسات، وسجّل التطبيقات المهنية في مسار واحد.";
    const heroLead = document.querySelector(".hero .lead");
    if (heroLead) heroLead.textContent = "إدارة حالات متعددة، جلسات متكررة، سجل زمني، مقارنة وصفية، ومسارات تطبيق للمقاييس المهنية. تحفظ هذه النسخة البيانات محليًا داخل المتصفح بواسطة UID مستقل.";
    const heroCardTitle = document.querySelector(".hero-card > strong");
    if (heroCardTitle) heroCardTitle.textContent = "النسخة التشغيلية المحلية";

    const professionalHeading = document.querySelector("#view-professional .section-heading h2");
    if (professionalHeading) professionalHeading.textContent = "المقاييس المهنية ومسارات التشغيل";
    const professionalEyebrow = document.querySelector("#view-professional .section-heading .eyebrow");
    if (professionalEyebrow) professionalEyebrow.textContent = "سجل مصنف مع تشغيل وتوثيق — دون نسخ مواد محمية";
    const professionalCallout = document.querySelector("#view-professional .callout");
    if (professionalCallout) {
      professionalCallout.className = "callout info";
      professionalCallout.textContent = "كل مقياس يفتح مسارًا لتحديد الحالة والمنفذ والتاريخ والنسخة والنتيجة والخطوة التالية. التطبيق الرسمي للبنود والدرجات المعيارية يتطلب النسخة الأصلية والترخيص والمؤهل المناسب.";
    }

    const footer = document.querySelector(".site-footer p");
    if (footer) footer.textContent = "© منصة منصة روافد — تشغيل محلي لإدارة الاستكشاف ومسارات التقييم. لا تستخدم للطوارئ أو التشخيص الآلي أو تقرير الأهلية.";
  };

  const patchLocalAccount = () => {
    const accountTitle = document.querySelector("#account-dialog h2");
    const accountNote = document.querySelector("#account-dialog .callout");
    const usernameLabel = document.querySelector('#account-dialog label[for="login-username"]');
    const credentials = document.querySelector("#account-dialog .demo-credentials");
    const passwordField = el.pass?.closest(".field");

    if (accountTitle) accountTitle.textContent = "فتح مساحة مقدم خدمة محلية";
    if (accountNote) accountNote.textContent = "ينشئ هذا الخيار مساحة محلية منفصلة بواسطة UID على هذا الجهاز. المصادقة المؤسسية السحابية ليست مفعلة في استضافة GitHub Pages الحالية.";
    if (usernameLabel) usernameLabel.querySelector("span").textContent = "اسم المساحة المحلية";
    if (credentials) credentials.textContent = "لا توجد كلمة مرور تجريبية. اكتب اسمًا للمساحة المحلية فقط.";
    if (passwordField) passwordField.hidden = true;
    if (el.pass) el.pass.required = false;

    el.af.addEventListener("submit", (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const username = el.user.value.trim().toLowerCase();
      if (!/^[a-z0-9._-]{3,40}$/.test(username)) {
        toast("استخدم اسمًا إنجليزيًا من 3 إلى 40 رمزًا.");
        return;
      }
      const records = identities();
      if (!records[username]) {
        records[username] = { uid: id("UID-PROV"), username, role: "provider", createdAt: new Date().toISOString() };
      }
      set(`pa-demo-identities-v3`, records);
      use(records[username]);
      close(el.ad);
      el.af.reset();
      toast("فُتحت مساحة مقدم الخدمة المحلية.");
    }, true);
  };

  const updateOperationalLabels = () => {
    const provider = identity?.role === "provider";
    if (el.badge) el.badge.textContent = provider ? `مقدم خدمة محلي: ${identity.username}` : "وضع الزائر";
    if (el.account) el.account.textContent = provider ? "تبديل المساحة" : "مساحة مقدم الخدمة";
    if (el.role) el.role.textContent = provider ? "مقدم خدمة محلي" : "زائر استكشافي";
  };

  const renderProfessionalOperational = () => {
    const query = professionalSearch.value.trim().toLowerCase();
    const category = professionalFilter.value;
    const records = Array.isArray(D.professional) ? D.professional : [];
    const filtered = records.filter((item) =>
      (!category || item.category === category) &&
      (!query || `${item.name} ${item.kind} ${item.note} ${item.category} ${(item.conditions || []).join(" ")}`.toLowerCase().includes(query))
    );

    const bar = `
      <div class="professional-operational-bar">
        <div><strong>${records.length} مقياسًا وفحصًا في السجل المهني</strong><p>التشغيل متاح لتخطيط التطبيق وتوثيق النتيجة وربطها بالحالة.</p></div>
        <button class="button secondary" type="button" data-open-professional-records>فتح السجل المهني</button>
      </div>`;

    professionalList.innerHTML = bar + (filtered.length ? filtered.map((item) => {
      const external = item.status === "external";
      const conditions = Array.isArray(item.conditions) && item.conditions.length ? item.conditions.join("، ") : "بحسب التقييم المهني";
      return `<article class="catalog-row">
        <div><span class="catalog-category">${E(item.category)}</span><h3>${E(item.name)}</h3><p>${E(item.kind)}</p></div>
        <div><strong>التشغيل</strong><p>${external ? "تسجيل أو استيراد نتيجة صادرة عن الجهة المختصة" : "تخطيط التطبيق، تعيين المنفذ، توثيق النتيجة والخطوة التالية"}</p><p class="muted">الحالات: ${E(conditions)}</p></div>
        <div><span class="badge success">${external ? "مسار نتيجة متاح" : "مسار عمل متاح"}</span><p>${E(item.note || "تستخدم المواد الأصلية المرخصة عند التطبيق الرسمي.")}</p><div class="professional-card-actions"><button class="button primary small-button" type="button" data-professional-tool="${E(item.id)}">بدء سجل مهني</button></div></div>
      </article>`;
    }).join("") : '<div class="empty-state">لا توجد نتائج مطابقة.</div>');
  };

  const fillCaseOptions = (select, selected = "") => {
    select.innerHTML = store.cases.length
      ? store.cases.map((caseRecord) => `<option value="${E(caseRecord.caseId)}"${caseRecord.caseId === selected ? " selected" : ""}>${E(caseRecord.alias)} — ${E(caseRecord.caseId)}</option>`).join("")
      : '<option value="">لا توجد حالات؛ أنشئ حالة أولًا</option>';
  };

  const openProfessionalRecord = (toolId = "", preferredCaseId = "") => {
    if (!store.cases.length) {
      toast("أنشئ حالة أولًا، ثم ابدأ السجل المهني.");
      newCase();
      return;
    }
    const tool = D.professional.find((item) => item.id === toolId) || null;
    const dialog = document.getElementById("professional-record-dialog");
    const form = document.getElementById("professional-record-form");
    form.reset();
    form.elements.toolId.value = tool?.id || "custom-professional-record";
    form.elements.toolName.value = tool?.name || "تطبيق مهني مخصص";
    form.elements.category.value = tool?.category || "مسار مهني";
    form.elements.administrationDate.value = new Date().toISOString().slice(0, 10);
    document.getElementById("professional-record-title").textContent = tool ? `تطبيق ${tool.name}` : "إضافة تطبيق مهني";
    fillCaseOptions(form.elements.caseId, preferredCaseId || selectedCase || store.cases[0]?.caseId);
    open(dialog);
  };

  const saveProfessionalRecord = (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const caseRecord = store.cases.find((item) => item.caseId === data.get("caseId"));
    if (!caseRecord) {
      toast("تعذر العثور على الحالة المحددة.");
      return;
    }
    caseRecord.professionalAssessments ||= [];
    const now = new Date().toISOString();
    caseRecord.professionalAssessments.push({
      recordId: id("PRO"),
      toolId: String(data.get("toolId") || ""),
      toolName: String(data.get("toolName") || ""),
      category: String(data.get("category") || ""),
      recordStatus: String(data.get("recordStatus") || "planned"),
      administrationDate: String(data.get("administrationDate") || ""),
      assignedEntityLabel: String(data.get("assignedEntityLabel") || "").trim(),
      performerName: String(data.get("performerName") || "").trim(),
      administrationMode: String(data.get("administrationMode") || ""),
      versionLanguage: String(data.get("versionLanguage") || "").trim(),
      outcomeLabel: String(data.get("outcomeLabel") || "").trim(),
      scoreReference: String(data.get("scoreReference") || "").trim(),
      notes: String(data.get("notes") || "").trim(),
      nextAction: String(data.get("nextAction") || "review"),
      rightsConfirmed: data.get("rightsConfirmed") === "on",
      recordedAt: now,
      recordedByUid: identity.uid,
      recordedByRole: identity.role,
      activationVersion,
    });
    caseRecord.updatedAt = now;
    save();
    render();
    close(document.getElementById("professional-record-dialog"));
    view("professional-records");
    toast("تم حفظ السجل المهني داخل الحالة الحالية.");
  };

  const renderProfessionalRecords = () => {
    const list = document.getElementById("professional-record-list");
    const stats = document.getElementById("professional-record-stats");
    const caseFilter = document.getElementById("professional-record-case-filter");
    const search = document.getElementById("professional-record-search");
    if (!list || !stats || !caseFilter || !search) return;

    const current = caseFilter.value;
    caseFilter.innerHTML = '<option value="">جميع الحالات</option>' + store.cases.map((caseRecord) => `<option value="${E(caseRecord.caseId)}"${caseRecord.caseId === current ? " selected" : ""}>${E(caseRecord.alias)}</option>`).join("");

    const query = search.value.trim().toLowerCase();
    const filtered = professionalRecords()
      .filter((record) => (!caseFilter.value || record.caseId === caseFilter.value) && (!query || `${record.toolName} ${record.category} ${record.assignedEntityLabel} ${record.performerName} ${record.outcomeLabel} ${record.notes}`.toLowerCase().includes(query)))
      .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));

    const completed = professionalRecords().filter((record) => ["completed", "result_imported"].includes(record.recordStatus)).length;
    const active = professionalRecords().filter((record) => ["planned", "scheduled", "in_progress"].includes(record.recordStatus)).length;
    const affectedCases = new Set(professionalRecords().map((record) => record.caseId)).size;
    stats.innerHTML = `
      <article class="stat-card"><span>السجلات المهنية</span><strong>${professionalRecords().length}</strong></article>
      <article class="stat-card"><span>قيد التنفيذ</span><strong>${active}</strong></article>
      <article class="stat-card"><span>مكتمل أو مستلم</span><strong>${completed}</strong></article>
      <article class="stat-card"><span>الحالات المرتبطة</span><strong>${affectedCases}</strong></article>`;

    list.innerHTML = filtered.length ? filtered.map((record) => `<article class="professional-record">
      <header><div><span class="badge success">${E(statusLabel(record.recordStatus))}</span><h3>${E(record.toolName)}</h3><p>${E(record.caseAlias)} — <span class="code small">${E(record.caseId)}</span></p></div><div><time>${E(record.administrationDate)}</time><div class="code small">${E(record.recordId)}</div></div></header>
      <dl><div><dt>المنفذ</dt><dd>${E(record.assignedEntityLabel)}${record.performerName ? ` — ${E(record.performerName)}` : ""}</dd></div><div><dt>النسخة واللغة</dt><dd>${E(record.versionLanguage || "غير مسجل")}</dd></div><div><dt>الخطوة التالية</dt><dd>${E(nextLabel(record.nextAction))}</dd></div></dl>
      <p><strong>الخلاصة:</strong> ${E(record.outcomeLabel)}</p>${record.scoreReference ? `<p><strong>الدرجة أو المرجع:</strong> ${E(record.scoreReference)}</p>` : ""}${record.notes ? `<p class="professional-record-notes"><strong>الملاحظات:</strong> ${E(record.notes)}</p>` : ""}
    </article>`).join("") : '<div class="empty-state">لا توجد سجلات مهنية مطابقة.</div>';
  };

  installStyles();
  installRecordsView();
  installRecordDialog();
  patchStaticCopy();
  patchLocalAccount();

  const originalRender = render;
  render = function activatedRender() {
    originalRender();
    updateOperationalLabels();
    renderProfessionalOperational();
    renderProfessionalRecords();
  };

  professionalSearch.addEventListener("input", renderProfessionalOperational);
  professionalFilter.addEventListener("change", renderProfessionalOperational);
  document.getElementById("professional-record-case-filter")?.addEventListener("change", renderProfessionalRecords);
  document.getElementById("professional-record-search")?.addEventListener("input", renderProfessionalRecords);
  document.getElementById("professional-record-form")?.addEventListener("submit", saveProfessionalRecord);

  document.addEventListener("click", (event) => {
    const target = event.target.closest("button");
    if (!target) return;
    if (target.dataset.professionalTool) openProfessionalRecord(target.dataset.professionalTool);
    if (target.matches("[data-open-professional-records]")) view("professional-records");
    if (target.id === "professional-record-new") openProfessionalRecord();
  });

  updateOperationalLabels();
  renderProfessionalOperational();
  renderProfessionalRecords();
})();
