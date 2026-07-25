"use strict";

const { test, expect } = require("@playwright/test");

const fillCase = async (page, alias) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  await page.locator('#case-form [name="alias"]').fill(alias);
  await page.locator('#case-form [name="ageGroup"]').selectOption("child");
  await page.locator('#case-form [name="language"]').selectOption("ar");
  await page.locator('#case-form [name="informant"]').selectOption("multiple");
  await page.locator('#case-form [name="question"]').fill("ما مجالات القوة والاحتياج التي تؤثر في المشاركة اليومية وكيف نتابعها؟");
  await page.locator('#case-form [name="notes"]').fill("بيانات اختبار اصطناعية لا تتضمن معلومات تعريف مباشرة.");
  await page.locator('#case-form button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const completeExploratoryForm = async (page) => {
  const cards = page.locator("#assessment-form .question-card");
  const count = await cards.count();
  expect(count).toBeGreaterThanOrEqual(12);
  for (let index = 0; index < count; index += 1) {
    const card = cards.nth(index);
    const radios = card.locator('input[type="radio"]');
    const checkboxes = card.locator('input[type="checkbox"]');
    const select = card.locator("select");
    const textarea = card.locator("textarea");
    if (await radios.count()) {
      const safeNo = radios.filter({ has: page.locator('[value="no"]') });
      if (await card.locator('input[type="radio"][value="no"]').count()) await card.locator('input[type="radio"][value="no"]').check();
      else await radios.first().check();
    } else if (await checkboxes.count()) {
      const preferred = card.locator('input[type="checkbox"]:not([value="none"])').first();
      if (await preferred.count()) await preferred.check();
      else await checkboxes.first().check();
    } else if (await select.count()) {
      await select.selectOption({ index: 1 });
    } else if (await textarea.count()) {
      await textarea.fill("مثال سياقي موثق يوضح الأداء المعتاد والدعم المجرب ونتيجته.");
    }
  }
  await page.locator('#assessment-form [name="sessionNote"]').fill("جمعت الملاحظة من سياقين ومصدرين، والنتيجة وصفية غير تشخيصية.");
};

const fillBaseProfessionalRecord = async (page) => {
  const form = page.locator("#professional-record-form");
  await form.locator('[name="assignedEntityLabel"]').fill("فريق تقييم متعدد التخصصات");
  await form.locator('[name="performerName"]').fill("رمز المختص P-220");
  await form.locator('[name="administrationMode"]').selectOption("external_import");
  await form.locator('[name="versionLanguage"]').fill("تقرير خارجي عربي — الإصدار الرسمي للجهة");
  await form.locator('[name="outcomeLabel"]').fill("تقرير خارجي مخطط للمراجعة متعددة المصادر");
  await form.locator('[name="scoreReference"]').fill("EXT-V220-001");
  await form.locator('[name="nextAction"]').selectOption("team_review");
  await form.locator('[name="notes"]').fill("سُجل مرجع التقرير فقط دون بنود أو مفاتيح تصحيح أو جداول معيارية.");
  await form.locator('[name="detail_purpose"]').selectOption("planning");
  await form.locator('[name="detail_setting"]').selectOption("multiple");
  await form.locator('[name="detail_validity"]').selectOption("qualified");
  await form.locator('[name="detail_informants"][value="records"]').check();
  await form.locator('[name="detail_informants"][value="provider"]').check();
  await form.locator('[name="detail_limitations"]').fill("التفسير محدود بالسياقات والمصادر المتاحة وبجودة التقرير الخارجي.");
  await form.locator('[name="detail_result_summary"]').fill("مرجع نتيجة خارجية قيد المراجعة المهنية، دون نقل مواد محمية.");
  await form.locator('[name="detail_domain_findings"]').fill("تُدمج النتيجة مع التاريخ والملاحظة والأداء الوظيفي قبل أي قرار.");
  await form.locator('[name="detail_recommendations"]').fill("مراجعة المصدر والنسخة والمؤهل وإضافة مصدر مكمل عند الحاجة.");
  await form.locator('[name="rightsConfirmed"]').check();
};

const updateLifecycle = async (page, status) => {
  await page.locator("[data-lifecycle-record]").first().click();
  const dialog = page.locator("#professional-lifecycle-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await dialog.locator('[name="recordStatus"]').selectOption(status);
  await dialog.locator('[name="changeReason"]').fill("استلم التقرير الرسمي وبدأت مراجعة الحقوق والنسخة والمصدر ضمن عقد v220.");
  await dialog.locator('[name="outcomeLabel"]').fill("نتيجة خارجية مستلمة وتحتاج استكمال العقد المنظم");
  await dialog.locator('button[type="submit"]').click();
  await expect(dialog).not.toHaveAttribute("open", "");
};

const fillMaturityEdit = async (page) => {
  const form = page.locator("#professional-record-edit-form");
  await form.locator('[name="practitionerQualification"]').fill("أخصائي نفسي مرخص — رمز مهني داخلي");
  await form.locator('[name="resultSourceType"]').selectOption("external_report");
  await form.locator('[name="reportReference"]').fill("EXT-V220-001");
  await form.locator('[name="reportIssuedBy"]').fill("جهة تقييم خارجية مختصة");
  await form.locator('[name="edit_maturity_publisher"]').fill("الجهة المالكة الرسمية");
  await form.locator('[name="edit_maturity_instrumentVersion"]').fill("الإصدار الرسمي 2026");
  await form.locator('[name="edit_maturity_administrationLanguage"]').fill("العربية");
  await form.locator('[name="edit_maturity_rightsBasis"]').selectOption("external_report_only");
  await form.locator('[name="edit_maturity_rightsReference"]').fill("إذن مراجعة التقرير الخارجي EXT-RIGHTS-220");
  await form.locator('[name="edit_maturity_scoreSource"]').selectOption("official_report");
  await form.locator('[name="edit_maturity_officialSourceReference"]').fill("EXT-V220-001");
  await form.locator('[name="edit_maturity_selectionRationale"]').fill("اختير التقرير للإجابة عن سؤال الإحالة مع دمجه بملاحظة وسجل وظيفي مستقلين.");
  await form.locator('[name="edit_maturity_administrationQuality"]').fill("تحققت هوية الجهة والنسخة واللغة واكتمال التقرير وظروف التطبيق المسجلة.");
  await form.locator('[name="edit_maturity_behavioralObservations"]').fill("كانت المشاركة كافية مع حاجة إلى دعم لغوي وتوضيح التعليمات في بعض المواقف.");
  await form.locator('[name="edit_maturity_interpretationLimitations"]').fill("لا تتوفر بنود أو بيانات خام داخل المنصة، والتفسير محدود بالتقرير والسياقات المسجلة.");
  await form.locator('[name="edit_maturity_integrationSummary"]').fill("تتفق الخلاصة جزئيًا مع التاريخ والملاحظة، مع اختلاف يحتاج مصدرًا مكملًا قبل القرار.");
  await form.locator('[name="edit_maturity_recommendations"]').fill("مراجعة فريق متعدد التخصصات وتجربة تكييف وظيفي ثم إعادة القياس في سياقين.");
  await form.locator('[name="edit_maturity_followUpDate"]').fill("2026-09-25");
  await form.locator('[name="edit_maturity_reviewedBy"]').fill("فريق المراجعة P-220");
  await form.locator('[name="edit_maturity_reviewStatus"]').selectOption("team_reviewed");
  await form.locator('[name="edit_maturity_noProtectedContent"]').check();
  await form.locator('[name="editReason"]').fill("استكمال عقد الحقوق والنسخة والمصدر والقيود بعد استلام التقرير الرسمي.");
  await form.locator('[name="rightsConfirmed"]').check();
};

const fillReport = async (page) => {
  const form = page.locator("#case-report-form");
  await form.locator('[name="preparedBy"]').fill("رمز المُعد REP-220");
  await form.locator('[name="preparedRole"]').fill("أخصائي نفسي مرخص");
  await form.locator('[name="reportType"]').selectOption("review");
  await form.locator('[name="reviewStatus"]').selectOption("final");
  await form.locator('[name="purpose"]').fill("دمج الجلسة الاستكشافية مع التقرير المهني الخارجي ضمن سؤال إحالة واحد.");
  await form.locator('[name="strengths"]').fill("توجد نقاط قوة في الاستجابة للدعم البصري والمشاركة عندما تكون التوقعات واضحة.");
  await form.locator('[name="needs"]').fill("تحتاج الحالة إلى تعميم المهارات وجمع مصدر مستقل من سياق ثانٍ.");
  await form.locator('[name="integratedSummary"]').fill("دُمجت الجلسة الاستكشافية والتقرير الخارجي والقيود والحقوق دون الاعتماد على مصدر واحد أو إصدار تشخيص آلي.");
  await form.locator('[name="recommendations"]').fill("تنفيذ دعم وظيفي محدد، مراجعة الفريق، وإعادة القياس الوصفي في موعد المتابعة.");
  await form.locator('[name="decision"]').selectOption("support_plan");
  await form.locator('[name="followUpDate"]').fill("2026-09-25");
  await form.locator('[name="followUpIndicators"]').fill("مستوى الاستقلال، نوع الدعم، وعدد السياقات التي ظهر فيها التقدم.");

  const optionalFields = {
    assessmentType: "review",
    evidenceSources: "جلسة استكشافية، تقرير رسمي، تاريخ الحالة، وملاحظة متعددة السياقات.",
    resultValidity: "تحققت النسخة واللغة والمؤهل والمصدر وقيود التفسير.",
    interpretationLimitations: "التفسير محدود بعدم وجود بيانات خام أو مصدر مدرسي مستقل.",
    functionalContexts: "المنزل، الخدمات، والمشاركة اليومية.",
    baselineIndicator: "أداء خط الأساس موثق وصفيا قبل خطة الدعم.",
    measurementMethod: "ملاحظة أسبوعية ثابتة للسلوك الوظيفي ومستوى الدعم.",
    measurableGoal: "زيادة المشاركة المستقلة في أربعة من خمسة مواقف ضمن سياقين.",
    remeasurementDate: "2026-09-25",
    providerInterpretation: "النتائج دليل واحد ضمن تكامل متعدد المصادر وغير تشخيصي.",
    familySummary: "نقاط القوة واضحة والخطوة التالية دعم قابل للقياس ومراجعة مشتركة.",
  };
  for (const [name, value] of Object.entries(optionalFields)) {
    const field = form.locator(`[name="${name}"]`);
    if (!await field.count()) continue;
    const tag = await field.evaluate((element) => element.tagName);
    if (tag === "SELECT") await field.selectOption(value);
    else await field.fill(value);
  }
};

const activeStore = async (page) => page.evaluate(() => {
  const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
  const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
  const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
  return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
});

test("expanded exploratory tool, professional rights upgrade, and final report remain one auditable flow", async ({ page }) => {
  await page.goto("/provider-assessment-demo/?release=2026.07.25-live.8#workspace");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.exploratoryMaturity)).toBe("ready");
  await expect.poll(() => page.evaluate(() => window.PA_EXPLORATORY_MATURITY_V220?.toolCount)).toBe(20);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_REGISTRY_V220?.customRecordContract))).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_PLANNING_COMPAT_V220?.planningDraftAllowed)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_EDIT_V220?.legacyRecordsUpgradable)).toBe(true);

  await fillCase(page, "الحالة المؤسسية v220");

  await page.locator('button.tab[data-view="explorers"]').click();
  const card = page.locator('[data-v220-card="development-overview"]');
  await expect(card).toContainText("مسار موسع");
  await page.locator('[data-start="development-overview"]').click();
  await expect(page.locator("#assessment-dialog")).toHaveAttribute("open", "");
  await expect(page.locator('[data-v220-protocol="development-overview"]')).toBeVisible();
  await completeExploratoryForm(page);
  await page.locator('#assessment-form button[type="submit"]').click();
  await expect(page.locator("#result-dialog")).toHaveAttribute("open", "");
  await expect(page.locator('[data-v220-quality="development-overview"]')).toContainText("جودة المعلومات");
  await page.keyboard.press("Escape");

  await page.locator('button.tab[data-view="professional-records"]').click();
  await page.locator("#professional-record-new").click();
  const recordDialog = page.locator("#professional-record-dialog");
  await expect(recordDialog).toHaveAttribute("open", "");
  await expect(page.locator("#professional-maturity-fields-v220")).toHaveAttribute("data-record-requirement", "planning-draft");
  await page.locator('#professional-record-form [name="recordStatus"]').selectOption("planned");
  await fillBaseProfessionalRecord(page);
  await page.locator('#professional-record-form button[type="submit"]').click();
  await expect(recordDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);

  await updateLifecycle(page, "result_imported");
  await page.locator("[data-edit-professional-record]").first().click();
  const editDialog = page.locator("#professional-record-edit-dialog");
  await expect(editDialog).toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-edit-maturity-v220")).toBeVisible();
  await fillMaturityEdit(page);
  await page.locator('#professional-record-edit-form button[type="submit"]').click();
  await expect(editDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list [data-professional-maturity-v220]")).toContainText("السجل المنظم v220.1");

  const afterUpgrade = await activeStore(page);
  const professional = afterUpgrade.cases[0].professionalAssessments[0];
  expect(professional.recordStatus).toBe("result_imported");
  expect(professional.professionalMaturity.schema).toBe("professional-registry-record-v220");
  expect(professional.professionalMaturity.rights.basis).toBe("external_report_only");
  expect(professional.professionalMaturity.auditTrail.at(-1).event).toBe("structured_record_updated");
  expect(professional.protectedContentStored).toBe(false);

  await page.locator('button.tab[data-view="reports"]').click();
  await page.locator("#new-case-report").click();
  const reportDialog = page.locator("#case-report-dialog");
  await expect(reportDialog).toHaveAttribute("open", "");
  await fillReport(page);
  await expect(page.locator('[data-professional-report-v220="220.1"]')).toContainText("جميع التطبيقات المكتملة تحمل عقدًا منظمًا");
  await page.locator('#case-report-form button[type="submit"]').click();
  await expect(reportDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#report-list .report-card")).toHaveCount(1);

  const finalStore = await activeStore(page);
  const report = finalStore.cases[0].reports[0];
  expect(report.reviewStatus).toBe("final");
  expect(report.professionalSourcesContract.schema).toBe("case-report-professional-sources-v220");
  expect(report.professionalSourcesContract.rightsValidCompletedRecords).toBe(1);
  expect(report.professionalSourcesContract.incompleteCompletedRecordIds).toEqual([]);
  expect(report.professionalSourcesContract.protectedContentStored).toBe(false);
});
