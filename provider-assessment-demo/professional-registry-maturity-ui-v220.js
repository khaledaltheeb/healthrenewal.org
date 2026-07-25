"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  const registry = window.PA_PROFESSIONAL_REGISTRY_V220;
  const form = document.getElementById("professional-record-form");
  if (!data || !registry || !form) return;

  const VERSION = "220.2";
  const COMPLETED = new Set(["completed", "result_imported"]);
  const REQUIRED_COMPLETED = [
    "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
    "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
    "selectionRationale", "administrationQuality", "interpretationLimitations",
    "integrationSummary", "recommendations", "followUpDate",
  ];
  const PROTECTED_TEXT = /(مفتاح\s*التصحيح|قواعد?\s*التصحيح|جدول\s*المعايير|درجات?\s*المعايير|إجابات?\s*البنود|استجابات?\s*البنود|نصوص?\s*البنود|بنود?\s*الاختبار\s*الكاملة|answer\s*key|scoring\s*(?:key|rule)|norm(?:ative)?\s*table|item\s*(?:text|response))/i;
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const clean = (value, limit = 3000) => String(value || "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, " ")
    .trim().slice(0, limit);
  const registeredTool = () => data.professional.find((tool) =>
    tool.id === form.elements.toolId.value || tool.name === form.elements.toolName.value
  ) || null;

  const syntheticContract = () => {
    const mode = form.elements.administrationMode?.value || "";
    const external = mode === "external_import" || mode === "record_review";
    return {
      version: VERSION,
      recordType: external ? "external_official_result_record" : "licensed_professional_administration_record",
      rightsState: external ? "external_report_only" : "rights_verification_required",
      officialAdministrationInsidePlatform: false,
      protectedContentStorageAllowed: false,
      itemResponsesStorageAllowed: false,
      scoringKeyStorageAllowed: false,
      normTableStorageAllowed: false,
      recommendedRoles: ["مختص مؤهل بحسب الأداة والجهة المنظمة"],
      permittedRightsBases: external
        ? ["external_report_only", "licensed_original_copy", "official_public_permission"]
        : ["licensed_original_copy", "official_public_permission"],
      permittedScoreSources: ["official_report", "authorized_scoring_platform", "qualified_professional_record", "publisher_output"],
      requiredCompletedFields: REQUIRED_COMPLETED,
      customModeBound: true,
    };
  };

  const currentTool = () => {
    const tool = registeredTool();
    if (tool?.professionalContract) return tool;
    return {
      id: form.elements.toolId.value || "custom-professional-record",
      name: form.elements.toolName.value || "سجل مهني مخصص",
      category: form.elements.category.value || "مسار مهني",
      professionalContract: syntheticContract(),
      professionalContractVersion: VERSION,
      customRecord: true,
    };
  };

  const field = (name, label, attributes = "") => `<label class="field"><span>${escapeHtml(label)}</span><input name="maturity_${escapeHtml(name)}" maxlength="300" ${attributes}></label>`;
  const textarea = (name, label, placeholder = "") => `<label class="field template-full"><span>${escapeHtml(label)}</span><textarea name="maturity_${escapeHtml(name)}" rows="3" maxlength="2400" placeholder="${escapeHtml(placeholder)}"></textarea></label>`;
  const select = (name, label, options) => `<label class="field"><span>${escapeHtml(label)}</span><select name="maturity_${escapeHtml(name)}"><option value="">اختر</option>${options.map(([value, text]) => `<option value="${escapeHtml(value)}">${escapeHtml(text)}</option>`).join("")}</select></label>`;

  const section = document.createElement("section");
  section.id = "professional-maturity-fields-v220";
  section.className = "professional-template-fields";
  section.innerHTML = `
    <div class="template-heading template-full"><p class="eyebrow">عقد السجل المهني v${VERSION}</p><h3>الحقوق والنسخة والمؤهل ومصدر النتيجة</h3><p>تسجل هذه الحقول تطبيقًا تم خارج المنصة أو تقريرًا رسميًا فقط. لا تدخل بندًا أو استجابة فردية أو مفتاح تصحيح أو جدولًا معياريًا.</p></div>
    <div id="professional-contract-summary-v220" class="callout warning template-full" role="note"></div>
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

  const maturityNames = [
    "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
    "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
    "selectionRationale", "administrationQuality", "behavioralObservations",
    "interpretationLimitations", "integrationSummary", "recommendations",
    "followUpDate", "reviewedBy", "reviewStatus",
  ];
  const inputFor = (name) => form.elements[`maturity_${name}`];
  const setRequired = (element, required) => {
    if (!element) return;
    element.required = required;
    element.closest("label")?.classList.toggle("required-field", required);
  };

  const updateContractUi = () => {
    const tool = currentTool();
    const contract = tool.professionalContract;
    const completed = COMPLETED.has(form.elements.recordStatus.value);
    const summary = document.getElementById("professional-contract-summary-v220");
    if (summary) summary.innerHTML = `<strong>${escapeHtml(tool.name)}:</strong> التطبيق الرقمي داخل المنصة غير متاح. ${contract.recordType === "external_official_result_record" ? "يسمح بتسجيل التقرير الرسمي ومرجعه فقط." : "يسمح بتوثيق تطبيق تم بواسطة مختص وبنسخة مصرح بها خارج المنصة."} الأدوار المقترحة: ${escapeHtml(contract.recommendedRoles.join("، "))}.`;

    for (const name of maturityNames) setRequired(inputFor(name), false);
    setRequired(inputFor("administratorQualification"), true);
    setRequired(inputFor("rightsBasis"), true);
    setRequired(inputFor("selectionRationale"), true);
    if (completed) for (const name of contract.requiredCompletedFields) setRequired(inputFor(name), true);

    const rights = inputFor("rightsBasis");
    if (rights) {
      for (const option of rights.options) {
        option.disabled = Boolean(option.value && option.value !== "pending_review" && !contract.permittedRightsBases.includes(option.value));
      }
      if (rights.value && rights.value !== "pending_review" && !contract.permittedRightsBases.includes(rights.value)) rights.value = "";
      if (contract.recordType === "external_official_result_record" && !rights.value) rights.value = "external_report_only";
    }
  };

  const collectStructuredRecord = (tool, recordedAt) => {
    const values = {};
    for (const name of maturityNames) {
      const long = name.includes("Summary") || ["selectionRationale", "administrationQuality", "behavioralObservations", "interpretationLimitations", "recommendations"].includes(name);
      values[name] = clean(inputFor(name)?.value, long ? 2400 : 300);
    }
    const contract = tool.professionalContract;
    return {
      schema: "professional-registry-record-v220",
      version: VERSION,
      contractSnapshot: {
        toolId: tool.id,
        toolName: tool.name,
        category: tool.category || form.elements.category.value,
        source: tool.customRecord ? "custom_mode_bound_contract" : "professional_registry",
        recordType: contract.recordType,
        rightsState: contract.rightsState,
        officialAdministrationInsidePlatform: false,
        permittedRightsBases: [...contract.permittedRightsBases],
        permittedScoreSources: [...contract.permittedScoreSources],
      },
      instrument: { publisher: values.publisher, version: values.instrumentVersion, language: values.administrationLanguage },
      administrator: { qualification: values.administratorQualification },
      rights: {
        basis: values.rightsBasis,
        reference: values.rightsReference,
        protectedContentStored: false,
        itemResponsesStored: false,
        scoringKeyStored: false,
        normTablesStored: false,
      },
      officialResultSource: { type: values.scoreSource, reference: values.officialSourceReference },
      selectionRationale: values.selectionRationale,
      administrationQuality: values.administrationQuality,
      behavioralObservations: values.behavioralObservations,
      interpretationLimitations: values.interpretationLimitations,
      integrationSummary: values.integrationSummary,
      recommendations: values.recommendations,
      followUpDate: values.followUpDate,
      review: { status: values.reviewStatus || "not_reviewed", reviewedBy: values.reviewedBy },
      recordedAt,
      auditTrail: [{ event: "structured_record_created", at: recordedAt, actorUid: identity.uid, actorRole: identity.role }],
    };
  };

  const protectedTextIn = (formData) => [...formData.entries()]
    .filter(([name]) => name === "scoreReference" || name === "notes" || name.startsWith("detail_") || /^maturity_(selectionRationale|administrationQuality|behavioralObservations|interpretationLimitations|integrationSummary|recommendations)$/.test(name))
    .map(([, value]) => String(value || ""))
    .join(" ");

  const persistAtomically = (caseRecord, record, now) => {
    caseRecord.professionalAssessments ||= [];
    const previousCaseUpdatedAt = caseRecord.updatedAt;
    const previousStoreUpdatedAt = store.updatedAt;
    caseRecord.professionalAssessments.push(record);
    caseRecord.updatedAt = now;
    store.updatedAt = now;
    const persisted = typeof set === "function" && typeof storeKey === "function"
      ? set(storeKey(identity.uid), store)
      : (save(), true);
    if (persisted) return true;
    caseRecord.professionalAssessments.pop();
    caseRecord.updatedAt = previousCaseUpdatedAt;
    store.updatedAt = previousStoreUpdatedAt;
    return false;
  };

  const saveAtomicProfessionalRecord = (event) => {
    updateContractUi();
    if (!form.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (form.dataset.v220Saving === "true") {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }

    const tool = currentTool();
    const contract = tool.professionalContract;
    const completed = COMPLETED.has(form.elements.recordStatus.value);
    const rightsBasis = inputFor("rightsBasis").value;
    if (completed && (rightsBasis === "pending_review" || !contract.permittedRightsBases.includes(rightsBasis))) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("لا يمكن حفظ تطبيق مكتمل قبل توثيق أساس حق صالح لهذه الأداة.");
      inputFor("rightsBasis").focus();
      return;
    }
    if (rightsBasis !== "pending_review" && !contract.permittedRightsBases.includes(rightsBasis)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("أساس الحق المحدد لا يتوافق مع نوع هذا السجل.");
      inputFor("rightsBasis").focus();
      return;
    }
    const reviewStatus = inputFor("reviewStatus").value;
    if (["peer_reviewed", "team_reviewed"].includes(reviewStatus) && !inputFor("reviewedBy").value.trim()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("سجل اسمًا أو دورًا مهنيًا للمراجع قبل اعتماد مراجعة الزميل أو الفريق.");
      inputFor("reviewedBy").focus();
      return;
    }

    const formData = new FormData(form);
    if (PROTECTED_TEXT.test(protectedTextIn(formData))) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("رُفض الحفظ لأن النص قد يتضمن مادة محمية. سجل الخلاصة والمرجع الرسمي فقط.");
      return;
    }
    const caseRecord = store.cases.find((item) => item.caseId === formData.get("caseId"));
    if (!caseRecord) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("تعذر العثور على الحالة المحددة.");
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    form.dataset.v220Saving = "true";
    try {
      const now = new Date().toISOString();
      const maturity = collectStructuredRecord(tool, now);
      const record = {
        recordId: id("PRO"),
        toolId: clean(formData.get("toolId"), 180),
        toolName: clean(formData.get("toolName"), 240),
        category: clean(formData.get("category"), 180),
        recordStatus: clean(formData.get("recordStatus"), 40) || "planned",
        administrationDate: clean(formData.get("administrationDate"), 20),
        assignedEntityLabel: clean(formData.get("assignedEntityLabel"), 120),
        performerName: clean(formData.get("performerName"), 120),
        administrationMode: clean(formData.get("administrationMode"), 40),
        versionLanguage: clean(formData.get("versionLanguage"), 160),
        practitionerQualification: maturity.administrator.qualification,
        resultSourceType: maturity.officialResultSource.type,
        reportReference: maturity.officialResultSource.reference,
        reportIssuer: maturity.instrument.publisher,
        outcomeLabel: clean(formData.get("outcomeLabel"), 240),
        scoreReference: clean(formData.get("scoreReference"), 240),
        notes: clean(formData.get("notes"), 3000),
        nextAction: clean(formData.get("nextAction"), 60) || "review",
        rightsConfirmed: formData.get("rightsConfirmed") === "on",
        recordedAt: now,
        recordedByUid: identity.uid,
        recordedByRole: identity.role,
        activationVersion: "1.0.0",
        professionalMaturity: maturity,
        professionalContractVersion: VERSION,
        digitalAdministrationOccurredInsidePlatform: false,
        protectedContentStored: false,
      };
      if (!persistAtomically(caseRecord, record, now)) {
        toast("تعذر تثبيت السجل محليًا؛ لم يُضف سجل جزئي.");
        return;
      }
      render();
      const dialog = document.getElementById("professional-record-dialog");
      if (dialog?.open && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      view("professional-records");
      toast("تم حفظ السجل المهني وعقد الحقوق في عملية محلية واحدة.");
    } finally {
      delete form.dataset.v220Saving;
    }
  };

  const fillCaseOptions = (select, selected = "") => {
    select.innerHTML = store.cases.length
      ? store.cases.map((caseRecord) => `<option value="${escapeHtml(caseRecord.caseId)}"${caseRecord.caseId === selected ? " selected" : ""}>${escapeHtml(caseRecord.alias)} — ${escapeHtml(caseRecord.caseId)}</option>`).join("")
      : '<option value="">لا توجد حالات؛ أنشئ حالة أولًا</option>';
  };

  const openRecordForTool = (toolId) => {
    if (!store.cases.length) {
      toast("أنشئ حالة أولًا، ثم وثق التطبيق المهني أو التقرير الرسمي.");
      if (typeof newCase === "function") newCase();
      return;
    }
    const tool = data.professional.find((item) => item.id === toolId);
    if (!tool?.professionalContract) return toast("تعذر تحميل عقد الأداة المهنية.");
    form.reset();
    form.elements.toolId.value = tool.id;
    form.elements.toolName.value = tool.name;
    form.elements.category.value = tool.category || "مسار مهني";
    form.elements.administrationDate.value = new Date().toISOString().slice(0, 10);
    form.elements.administrationMode.value = tool.professionalContract.recordType === "external_official_result_record" ? "external_import" : "in_person";
    fillCaseOptions(form.elements.caseId, (typeof selectedCase !== "undefined" && selectedCase) || store.cases[0]?.caseId);
    const title = document.getElementById("professional-record-title");
    if (title) title.textContent = tool.professionalContract.recordType === "external_official_result_record" ? `تسجيل تقرير ${tool.name}` : `توثيق تطبيق ${tool.name}`;
    updateContractUi();
    const dialog = document.getElementById("professional-record-dialog");
    if (dialog?.showModal) dialog.showModal();
    else dialog?.setAttribute("open", "");
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
      const title = card.querySelector("h3")?.textContent?.trim() || "";
      const tool = data.professional.find((item) => item.name === title || title.includes(item.name));
      if (!tool?.professionalContract) return;
      if (!card.querySelector("[data-professional-contract-v220]")) {
        const contract = document.createElement("div");
        contract.className = "callout warning";
        contract.dataset.professionalContractV220 = tool.id;
        contract.innerHTML = `<strong>عقد الحقوق:</strong> ${tool.professionalContract.recordType === "external_official_result_record" ? "تسجيل تقرير خارجي رسمي فقط" : "يتطلب نسخة أصلية وترخيصًا ومؤهلًا موثقًا"}. لا تطبيق رقمي أو تخزين بنود داخل المنصة.`;
        card.querySelector(".professional-card-actions")?.before(contract) || card.appendChild(contract);
      }
      if (!card.querySelector("[data-v220-record-tool]")) {
        let actions = card.querySelector(".professional-card-actions");
        if (!actions) {
          actions = document.createElement("div");
          actions.className = "professional-card-actions";
          card.appendChild(actions);
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button secondary small-button";
        button.dataset.v220RecordTool = tool.id;
        button.textContent = tool.professionalContract.recordType === "external_official_result_record" ? "تسجيل تقرير رسمي" : "توثيق تطبيق مرخص";
        actions.appendChild(button);
      }
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
    setTimeout(() => URL.revokeObjectURL(url), 500);
  };

  document.addEventListener("click", (event) => {
    const recordTool = event.target.closest("[data-v220-record-tool]");
    if (recordTool) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openRecordForTool(recordTool.dataset.v220RecordTool);
      return;
    }
    const trigger = event.target.closest("#professional-record-new");
    if (trigger) queueMicrotask(updateContractUi);
    const exportButton = event.target.closest("[data-export-professional-record]");
    if (exportButton) exportRecord(exportButton.dataset.exportProfessionalRecord);
  }, true);
  form.elements.recordStatus.addEventListener("change", updateContractUi);
  form.elements.administrationMode.addEventListener("change", updateContractUi);
  form.addEventListener("reset", () => queueMicrotask(updateContractUi));
  form.addEventListener("submit", saveAtomicProfessionalRecord, true);

  const refresh = () => {
    enhanceCatalog();
    enhanceRecords();
  };
  new MutationObserver(refresh).observe(document.body, { childList: true, subtree: true });
  refresh();
  window.PA_PROFESSIONAL_REGISTRY_V220_REFRESH = refresh;
  window.PA_PROFESSIONAL_RECORD_V220 = Object.freeze({ version: VERSION, openRecordForTool, collectStructuredRecord });
})();