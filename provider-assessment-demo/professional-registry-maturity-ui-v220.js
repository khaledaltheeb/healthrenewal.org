"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  const registry = window.PA_PROFESSIONAL_REGISTRY_V220;
  const form = document.getElementById("professional-record-form");
  if (!data || !registry || !form) return;

  const VERSION = "220.1";
  const completedStatuses = new Set(["completed", "result_imported"]);
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clean = (value, limit = 3000) => String(value || "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, " ").trim().slice(0, limit);
  const toolById = (idValue, nameValue = "") => data.professional.find((tool) => tool.id === idValue || tool.name === nameValue);

  const field = (name, label, attributes = "") => `<label class="field"><span>${escapeHtml(label)}</span><input name="maturity_${escapeHtml(name)}" maxlength="300" ${attributes}></label>`;
  const textarea = (name, label, placeholder = "") => `<label class="field template-full"><span>${escapeHtml(label)}</span><textarea name="maturity_${escapeHtml(name)}" rows="3" maxlength="2400" placeholder="${escapeHtml(placeholder)}"></textarea></label>`;
  const select = (name, label, options) => `<label class="field"><span>${escapeHtml(label)}</span><select name="maturity_${escapeHtml(name)}"><option value="">اختر</option>${options.map(([value, text]) => `<option value="${escapeHtml(value)}">${escapeHtml(text)}</option>`).join("")}</select></label>`;

  const section = document.createElement("section");
  section.id = "professional-maturity-fields-v220";
  section.className = "professional-template-fields";
  section.innerHTML = `
    <div class="template-heading template-full"><p class="eyebrow">عقد السجل المهني v${VERSION}</p><h3>الحقوق والنسخة والمؤهل ومصدر النتيجة</h3><p>هذه الحقول تسجل التطبيق أو التقرير الرسمي فقط. لا تدخل أي بند أو استجابة فردية أو مفتاح تصحيح أو جدول معياري.</p></div>
    <div id="professional-contract-summary-v220" class="callout warning template-full"></div>
    <div class="template-grid">
      ${field("publisher", "الناشر أو الجهة المالكة", 'placeholder="اسم الناشر أو الجهة الرسمية"')}
      ${field("instrumentVersion", "اسم الإصدار أو النموذج", 'placeholder="الإصدار والسنة والوحدة عند الصلة"')}
      ${field("administrationLanguage", "لغة النسخة الرسمية", 'placeholder="العربية، الإنجليزية، نسخة ثنائية اللغة..."')}
      ${field("administratorQualification", "مؤهل المنفذ وترخيصه المهني", 'placeholder="المؤهل أو الدور ورقم مرجعي محلي غير حساس"')}
      ${select("rightsBasis", "أساس الحق في التطبيق أو التسجيل", [["pending_review","قيد مراجعة الحقوق — للتخطيط فقط"],["licensed_original_copy","نسخة أصلية مرخصة"],["official_public_permission","إذن رسمي عام أو مكتوب"],["external_report_only","تسجيل تقرير خارجي فقط"]])}
      ${field("rightsReference", "مرجع الترخيص أو الإذن", 'placeholder="رقم طلب/فاتورة/إذن محلي أو رابط رسمي دون بيانات حساسة"')}
      ${select("scoreSource", "مصدر النتيجة أو الدرجة", [["official_report","تقرير رسمي صادر عن الجهة"],["authorized_scoring_platform","منصة تصحيح مصرح بها"],["qualified_professional_record","سجل مختص مؤهل"],["publisher_output","مخرج صادر عن الناشر"]])}
      ${field("officialSourceReference", "مرجع التقرير أو المخرج الرسمي", 'placeholder="رقم تقرير أو اسم ملف محلي مستعار"')}
      ${textarea("selectionRationale", "مبرر اختيار الأداة", "سؤال الإحالة، ملاءمة العمر واللغة والسياق، ولماذا لا تكفي المصادر الأخرى وحدها")}
      ${textarea("administrationQuality", "جودة التطبيق وشروطه", "الاكتمال، اتباع الدليل، البيئة، الزمن، التكييفات، مشاركة المستجيب أو بذل الجهد")}
      ${textarea("behavioralObservations", "الملاحظات السلوكية والسياقية", "المشاركة، فهم التعليمات، التعب، التواصل، الاستراتيجية، الاختلاف بين المواقف")}
      ${textarea("interpretationLimitations", "قيود التفسير", "اللغة والثقافة والتكييفات ونقص المصادر والنسخة والمعايير وأي عامل يحد الثقة")}
      ${textarea("integrationSummary", "تكامل النتيجة مع بقية المصادر", "نقاط الاتفاق والاختلاف مع التاريخ والملاحظة والأدوات الأخرى، دون تشخيص آلي")}
      ${textarea("recommendations", "التوصيات الناتجة", "إحالة أو دعم أو تكييف أو أداة مكملة مرتبطة مباشرة بالنتيجة والقيود")}
      ${field("followUpDate", "تاريخ المتابعة المخطط", 'type="date"')}
      ${field("reviewedBy", "المراجع المهني", 'placeholder="دور أو اسم مهني مختصر عند وجود مراجعة"')}
      ${select("reviewStatus", "حالة المراجعة", [["not_reviewed","لم تراجع بعد"],["self_checked","مراجعة ذاتية للمنفذ"],["peer_reviewed","مراجعة زميل مؤهل"],["team_reviewed","مراجعة فريق متعدد التخصصات"]])}
      <label class="rights-confirmation template-full"><input name="maturity_noProtectedContent" type="checkbox" required><span>أؤكد أن هذا السجل لا يحتوي بنود الأداة أو استجاباتها الفردية أو مفتاح التصحيح أو الجداول المعيارية، وأن الخلاصة مأخوذة من مصدر رسمي مصرح به.</span></label>
    </div>`;

  const templateContainer = document.getElementById("professional-template-fields");
  if (templateContainer) templateContainer.before(section);
  else form.querySelector(".dialog-actions")?.before(section);

  const inputFor = (name) => form.elements[`maturity_${name}`];
  const maturityNames = [
    "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
    "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
    "selectionRationale", "administrationQuality", "behavioralObservations",
    "interpretationLimitations", "integrationSummary", "recommendations",
    "followUpDate", "reviewedBy", "reviewStatus"
  ];

  const currentTool = () => toolById(form.elements.toolId.value, form.elements.toolName.value);
  const setRequired = (element, required) => {
    if (!element) return;
    element.required = required;
    element.closest("label")?.classList.toggle("required-field", required);
  };

  const updateContractUi = () => {
    const tool = currentTool();
    if (!tool?.professionalContract) return;
    const contract = tool.professionalContract;
    const completed = completedStatuses.has(form.elements.recordStatus.value);
    const summary = document.getElementById("professional-contract-summary-v220");
    if (summary) summary.innerHTML = `<strong>${escapeHtml(tool.name)}:</strong> التطبيق الرقمي داخل المنصة غير متاح. يسمح بتسجيل الخلاصة الرسمية والمرجع فقط. الأدوار المقترحة: ${escapeHtml(contract.recommendedRoles.join("، "))}.`;

    for (const name of maturityNames) setRequired(inputFor(name), false);
    setRequired(inputFor("administratorQualification"), true);
    setRequired(inputFor("rightsBasis"), true);
    setRequired(inputFor("selectionRationale"), true);
    if (completed) for (const name of contract.requiredCompletedFields) setRequired(inputFor(name), true);

    const rights = inputFor("rightsBasis");
    if (rights) {
      for (const option of rights.options) {
        option.disabled = option.value && option.value !== "pending_review" && !contract.permittedRightsBases.includes(option.value);
      }
      if (contract.recordType === "external_official_result_record" && !rights.value) rights.value = "external_report_only";
    }
  };

  const collectStructuredRecord = () => {
    const values = {};
    for (const name of maturityNames) values[name] = clean(inputFor(name)?.value, name.includes("Summary") || ["selectionRationale","administrationQuality","behavioralObservations","interpretationLimitations","recommendations"].includes(name) ? 2400 : 300);
    return {
      schema: "professional-registry-record-v220",
      version: VERSION,
      instrument: {
        publisher: values.publisher,
        version: values.instrumentVersion,
        language: values.administrationLanguage,
      },
      administrator: {
        qualification: values.administratorQualification,
      },
      rights: {
        basis: values.rightsBasis,
        reference: values.rightsReference,
        protectedContentStored: false,
        itemResponsesStored: false,
        scoringKeyStored: false,
        normTablesStored: false,
      },
      officialResultSource: {
        type: values.scoreSource,
        reference: values.officialSourceReference,
      },
      selectionRationale: values.selectionRationale,
      administrationQuality: values.administrationQuality,
      behavioralObservations: values.behavioralObservations,
      interpretationLimitations: values.interpretationLimitations,
      integrationSummary: values.integrationSummary,
      recommendations: values.recommendations,
      followUpDate: values.followUpDate,
      review: {
        status: values.reviewStatus || "not_reviewed",
        reviewedBy: values.reviewedBy,
      },
      recordedAt: new Date().toISOString(),
    };
  };

  const validateBeforeSave = (event) => {
    updateContractUi();
    if (!form.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    const tool = currentTool();
    if (!tool?.professionalContract) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("تعذر تحميل عقد الحقوق لهذه الأداة؛ لم يُحفظ السجل.");
      return;
    }
    const completed = completedStatuses.has(form.elements.recordStatus.value);
    const rightsBasis = inputFor("rightsBasis").value;
    if (completed && (rightsBasis === "pending_review" || !tool.professionalContract.permittedRightsBases.includes(rightsBasis))) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("لا يمكن حفظ تطبيق مكتمل قبل توثيق أساس حق صالح لهذه الأداة.");
      inputFor("rightsBasis").focus();
      return;
    }
    const suspicious = `${form.elements.scoreReference.value} ${form.elements.notes.value}`;
    if (/(مفتاح\s*التصحيح|جدول\s*المعايير|إجابات\s*البنود|نص\s*البند|answer\s*key|norm\s*table)/i.test(suspicious)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("رُفض الحفظ لأن النص قد يتضمن مادة محمية. سجل الخلاصة والمرجع الرسمي فقط.");
      return;
    }

    const payload = collectStructuredRecord();
    const caseId = form.elements.caseId.value;
    const toolId = form.elements.toolId.value;
    const beforeCount = store.cases.find((item) => item.caseId === caseId)?.professionalAssessments?.length || 0;
    queueMicrotask(() => {
      const caseRecord = store.cases.find((item) => item.caseId === caseId);
      const records = caseRecord?.professionalAssessments || [];
      const record = records.length > beforeCount ? records[records.length - 1] : [...records].reverse().find((item) => item.toolId === toolId && !item.professionalMaturity);
      if (!record) return;
      record.professionalMaturity = payload;
      record.professionalContractVersion = VERSION;
      record.digitalAdministrationOccurredInsidePlatform = false;
      record.protectedContentStored = false;
      caseRecord.updatedAt = new Date().toISOString();
      save();
      render();
    });
  };

  const findRecord = (recordId) => {
    for (const caseRecord of store.cases) {
      const record = (caseRecord.professionalAssessments || []).find((item) => item.recordId === recordId);
      if (record) return { caseRecord, record };
    }
    return null;
  };

  const enhanceCatalog = () => {
    document.querySelectorAll("#professional-list .catalog-row").forEach((card) => {
      if (card.querySelector("[data-professional-contract-v220]")) return;
      const title = card.querySelector("h3")?.textContent || "";
      const tool = data.professional.find((item) => title.includes(item.name));
      if (!tool?.professionalContract) return;
      const contract = document.createElement("div");
      contract.className = "callout warning";
      contract.dataset.professionalContractV220 = tool.id;
      contract.innerHTML = `<strong>عقد الحقوق:</strong> ${tool.professionalContract.recordType === "external_official_result_record" ? "تسجيل تقرير خارجي رسمي فقط" : "يتطلب نسخة أصلية وترخيصًا ومؤهلًا موثقًا"}. لا تطبيق رقمي أو تخزين بنود داخل المنصة.`;
      card.querySelector(".professional-card-actions")?.before(contract);
    });
  };

  const enhanceRecords = () => {
    document.querySelectorAll("#professional-record-list .professional-record").forEach((card) => {
      if (card.querySelector("[data-professional-maturity-v220]")) return;
      const recordId = [...card.querySelectorAll(".code")].map((node) => node.textContent.trim()).find((value) => value.startsWith("PRO-"));
      const found = findRecord(recordId);
      const maturity = found?.record?.professionalMaturity;
      if (!maturity) return;
      const panel = document.createElement("section");
      panel.className = "professional-record-notes callout info";
      panel.dataset.professionalMaturityV220 = recordId;
      panel.innerHTML = `<strong>السجل المنظم v${escapeHtml(maturity.version)}</strong><br>
        الناشر/النسخة/اللغة: ${escapeHtml(maturity.instrument.publisher || "غير مسجل")} — ${escapeHtml(maturity.instrument.version || "غير مسجل")} — ${escapeHtml(maturity.instrument.language || "غير مسجل")}<br>
        أساس الحقوق: ${escapeHtml(maturity.rights.basis || "غير مسجل")} · مصدر النتيجة: ${escapeHtml(maturity.officialResultSource.type || "غير مسجل")} · المراجعة: ${escapeHtml(maturity.review.status)}
        <div class="professional-card-actions"><button type="button" class="button ghost small-button" data-export-professional-record="${escapeHtml(recordId)}">تصدير هذا السجل JSON</button></div>`;
      card.appendChild(panel);
    });
  };

  const exportRecord = (recordId) => {
    const found = findRecord(recordId);
    if (!found) return;
    const payload = {
      schema: "professional-record-export-v220",
      ownerUid: identity.uid,
      caseId: found.caseRecord.caseId,
      caseAlias: found.caseRecord.alias,
      exportedAt: new Date().toISOString(),
      record: found.record,
      warning: "Contains a professional result summary only; protected instrument items and scoring materials must not be included.",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${recordId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-professional-tool],#professional-record-new");
    if (trigger) queueMicrotask(updateContractUi);
    const exportButton = event.target.closest("[data-export-professional-record]");
    if (exportButton) exportRecord(exportButton.dataset.exportProfessionalRecord);
  }, true);
  form.elements.recordStatus.addEventListener("change", updateContractUi);
  form.addEventListener("submit", validateBeforeSave, true);

  const refresh = () => {
    enhanceCatalog();
    enhanceRecords();
  };
  new MutationObserver(refresh).observe(document.body, { childList: true, subtree: true });
  refresh();
  window.PA_PROFESSIONAL_REGISTRY_V220_REFRESH = refresh;
})();
