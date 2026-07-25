"use strict";

const { test, expect } = require("@playwright/test");

const fillCase = async (page) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  const form = page.locator("#case-form");
  await form.locator('[name="alias"]').fill("الحالة المؤسسية v220");
  await form.locator('[name="ageGroup"]').selectOption("child");
  await form.locator('[name="language"]').selectOption("ar");
  await form.locator('[name="informant"]').selectOption("multiple");
  await form.locator('[name="question"]').fill("ما مجالات القوة والاحتياج التي تؤثر في المشاركة اليومية وكيف نتابعها؟");
  await form.locator('[name="notes"]').fill("بيانات اصطناعية لا تتضمن معلومات تعريف مباشرة.");
  await form.locator('button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const completeExploratory = async (page) => {
  const cards = page.locator("#assessment-form .question-card");
  expect(await cards.count()).toBeGreaterThanOrEqual(12);
  for (let index = 0; index < await cards.count(); index += 1) {
    const card = cards.nth(index);
    const safetyNo = card.locator('input[type="radio"][value="no"]');
    const radios = card.locator('input[type="radio"]');
    const checks = card.locator('input[type="checkbox"]');
    const select = card.locator("select");
    const textarea = card.locator("textarea");
    if (await safetyNo.count()) await safetyNo.check();
    else if (await radios.count()) await radios.first().check();
    else if (await checks.count()) await checks.first().check();
    else if (await select.count()) await select.selectOption({ index: 1 });
    else if (await textarea.count()) await textarea.fill("مثال سياقي يوضح الأداء المعتاد والدعم المجرب ونتيجته.");
  }
  await page.locator('#assessment-form [name="sessionNote"]').fill("جمعت الملاحظة من سياقين ومصدرين، والنتيجة وصفية غير تشخيصية.");
};

const fillNewProfessionalDraft = async (page) => {
  const form = page.locator("#professional-record-form");
  await form.locator('[name="recordStatus"]').selectOption("planned");
  await form.locator('[name="assignedEntityLabel"]').fill("فريق تقييم متعدد التخصصات");
  await form.locator('[name="performerName"]').fill("رمز المختص P-220");
  await form.locator('[name="administrationMode"]').selectOption("external_import");
  await form.locator('[name="versionLanguage"]').fill("تقرير خارجي عربي — الإصدار الرسمي");
  await form.locator('[name="outcomeLabel"]').fill("تقرير مخطط للمراجعة متعددة المصادر");
  await form.locator('[name="scoreReference"]').fill("EXT-V220-001");
  await form.locator('[name="nextAction"]').selectOption("team_review");
  await form.locator('[name="notes"]').fill("مرجع التقرير فقط دون بنود أو مفاتيح تصحيح أو جداول معيارية.");
  await form.locator('[name="detail_purpose"]').selectOption("planning");
  await form.locator('[name="detail_setting"]').selectOption("multiple");
  await form.locator('[name="detail_validity"]').selectOption("qualified");
  await form.locator('[name="detail_informants"][value="records"]').check();
  await form.locator('[name="detail_informants"][value="provider"]').check();
  await form.locator('[name="detail_limitations"]').fill("التفسير محدود بالسياقات والمصادر وجودة التقرير الخارجي.");
  await form.locator('[name="detail_result_summary"]').fill("مرجع نتيجة خارجية قيد المراجعة المهنية.");
  await form.locator('[name="detail_domain_findings"]').fill("تدمج النتيجة مع التاريخ والملاحظة قبل أي قرار.");
  await form.locator('[name="detail_recommendations"]').fill("مراجعة المصدر والنسخة والمؤهل وإضافة مصدر مكمل.");
  await form.locator('[name="rightsConfirmed"]').check();
};

const receiveExternalResult = async (page) => {
  await page.locator("[data-lifecycle-record]").first().click();
  const dialog = page.locator("#professional-lifecycle-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await dialog.locator('[name="recordStatus"]').selectOption("result_imported");
  await dialog.locator('[name="changeReason"]').fill("استلم التقرير الرسمي وبدأت مراجعة الحقوق والنسخة والمصدر.");
  await dialog.locator('[name="outcomeLabel"]').fill("نتيجة خارجية مستلمة وتحتاج استكمال العقد المنظم");
  await dialog.locator('button[type="submit"]').click();
  await expect(dialog).not.toHaveAttribute("open", "");
};

const fillProfessionalUpgrade = async (page) => {
  const form = page.locator("#professional-record-edit-form");
  await form.locator('[name="practitionerQualification"]').fill("أخصائي نفسي مرخص — رمز داخلي");
  await form.locator('[name="resultSourceType"]').selectOption("external_report");
  await form.locator('[name="reportReference"]').fill("EXT-V220-001");
  await form.locator('[name="reportIssuedBy"]').fill("جهة تقييم خارجية مختصة");
  const values = {
    publisher: "الجهة المالكة الرسمية",
    instrumentVersion: "الإصدار الرسمي 2026",
    administrationLanguage: "العربية",
    rightsReference: "إذن مراجعة التقرير الخارجي EXT-RIGHTS-220",
    officialSourceReference: "EXT-V220-001",
    selectionRationale: "اختير التقرير للإجابة عن سؤال الإحالة مع دمجه بملاحظة وسجل وظيفي مستقلين.",
    administrationQuality: "تحققت هوية الجهة والنسخة واللغة واكتمال التقرير وظروف التطبيق.",
    behavioralObservations: "كانت المشاركة كافية مع حاجة إلى دعم لغوي في بعض المواقف.",
    interpretationLimitations: "لا توجد بيانات خام داخل المنصة والتفسير محدود بالتقرير والسياقات.",
    integrationSummary: "تتفق الخلاصة جزئيًا مع التاريخ والملاحظة وتحتاج مصدرًا مكملًا.",
    recommendations: "مراجعة فريق متعدد التخصصات وتجربة تكييف ثم إعادة القياس.",
    reviewedBy: "فريق المراجعة P-220",
  };
  for (const [name, value] of Object.entries(values)) await form.locator(`[name="edit_maturity_${name}"]`).fill(value);
  await form.locator('[name="edit_maturity_rightsBasis"]').selectOption("external_report_only");
  await form.locator('[name="edit_maturity_scoreSource"]').selectOption("official_report");
  await form.locator('[name="edit_maturity_followUpDate"]').fill("2026-09-25");
  await form.locator('[name="edit_maturity_reviewStatus"]').selectOption("team_reviewed");
  await form.locator('[name="edit_maturity_noProtectedContent"]').check();
  await form.locator('[name="editReason"]').fill("استكمال الحقوق والنسخة والمصدر والقيود بعد استلام التقرير الرسمي.");
  await form.locator('[name="rightsConfirmed"]').check();
};

const fillReport = async (page) => {
  const form = page.locator("#case-report-form");
  const values = {
    preparedBy: "رمز المُعد REP-220",
    preparedRole: "أخصائي نفسي مرخص",
    purpose: "دمج الجلسة الاستكشافية مع التقرير الخارجي ضمن سؤال إحالة واحد.",
    strengths: "قوة في الاستجابة للدعم البصري والمشاركة عندما تكون التوقعات واضحة.",
    needs: "الحاجة إلى تعميم المهارات وجمع مصدر مستقل من سياق ثانٍ.",
    integratedSummary: "دُمجت الجلسة والتقرير والقيود والحقوق دون الاعتماد على مصدر واحد.",
    recommendations: "دعم وظيفي محدد ومراجعة الفريق وإعادة القياس في الموعد.",
    followUpIndicators: "الاستقلال ونوع الدعم وعدد السياقات التي ظهر فيها التقدم.",
    evidenceSources: "جلسة استكشافية وتقرير رسمي وتاريخ الحالة وملاحظة متعددة السياقات.",
    resultValidity: "تحققت النسخة واللغة والمؤهل والمصدر وقيود التفسير.",
    interpretationLimitations: "لا توجد بيانات خام أو مصدر مدرسي مستقل.",
    functionalContexts: "المنزل والخدمات والمشاركة اليومية.",
    baselineIndicator: "أداء خط الأساس موثق وصفيا قبل خطة الدعم.",
    measurementMethod: "ملاحظة أسبوعية ثابتة لمستوى الدعم والأداء الوظيفي.",
    measurableGoal: "زيادة المشاركة المستقلة في أربع من خمس فرص ضمن سياقين.",
    providerInterpretation: "النتائج دليل واحد ضمن تكامل متعدد المصادر وغير تشخيصي.",
    familySummary: "الخطوة التالية دعم قابل للقياس ومراجعة مشتركة.",
  };
  for (const [name, value] of Object.entries(values)) {
    const field = form.locator(`[name="${name}"]`);
    if (await field.count()) await field.fill(value);
  }
  await form.locator('[name="reportType"]').selectOption("review");
  await form.locator('[name="reviewStatus"]').selectOption("final");
  await form.locator('[name="assessmentType"]').selectOption("functional");
  await form.locator('[name="decision"]').selectOption("support_plan");
  await form.locator('[name="followUpDate"]').fill("2026-09-25");
  await form.locator('[name="remeasurementDate"]').fill("2026-09-25");
};

const activeStore = async (page) => page.evaluate(() => {
  const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
  const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
  const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
  return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
});

test("v220 keeps exploration, professional rights, legacy upgrade, and final report auditable", async ({ page }) => {
  await page.goto("/provider-assessment-demo/?release=2026.07.25-live.8#workspace");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.exploratoryMaturity)).toBe("ready");
  await expect.poll(() => page.evaluate(() => window.PA_EXPLORATORY_MATURITY_V220?.toolCount)).toBe(20);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_REGISTRY_V220?.customRecordContract))).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_PLANNING_COMPAT_V220?.planningDraftAllowed)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_EDIT_V220?.legacyRecordsUpgradable)).toBe(true);

  await fillCase(page);
  await page.locator('button.tab[data-view="explorers"]').click();
  await expect(page.locator('[data-v220-card="development-overview"]')).toContainText("مسار موسع");
  await page.locator('[data-start="development-overview"]').click();
  await expect(page.locator("#assessment-dialog")).toHaveAttribute("open", "");
  await expect(page.locator('[data-v220-protocol="development-overview"]')).toBeVisible();
  await completeExploratory(page);
  await page.locator('#assessment-form button[type="submit"]').click();
  await expect(page.locator("#result-dialog")).toHaveAttribute("open", "");
  await expect(page.locator('[data-v220-quality="development-overview"]')).toContainText("جودة المعلومات");
  await page.keyboard.press("Escape");

  await page.locator('button.tab[data-view="professional-records"]').click();
  await page.locator("#professional-record-new").click();
  await expect(page.locator("#professional-record-dialog")).toHaveAttribute("open", "");
  await expect(page.locator("#professional-maturity-fields-v220")).toHaveAttribute("data-record-requirement", "planning-draft");
  await fillNewProfessionalDraft(page);
  await page.locator('#professional-record-form button[type="submit"]').click();
  await expect(page.locator("#professional-record-dialog")).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);

  await receiveExternalResult(page);
  await page.locator("[data-edit-professional-record]").first().click();
  await expect(page.locator("#professional-record-edit-dialog")).toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-edit-maturity-v220")).toBeVisible();
  await fillProfessionalUpgrade(page);
  await page.locator('#professional-record-edit-form button[type="submit"]').click();
  await expect(page.locator("#professional-record-edit-dialog")).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list [data-professional-maturity-v220]")).toContainText("السجل المنظم v220.1");

  const upgraded = await activeStore(page);
  const professional = upgraded.cases[0].professionalAssessments[0];
  expect(professional.recordStatus).toBe("result_imported");
  expect(professional.professionalMaturity.schema).toBe("professional-registry-record-v220");
  expect(professional.professionalMaturity.rights.basis).toBe("external_report_only");
  expect(professional.professionalMaturity.auditTrail.at(-1).event).toBe("structured_record_updated");
  expect(professional.protectedContentStored).toBe(false);

  await page.locator('button.tab[data-view="reports"]').click();
  await page.locator("#new-case-report").click();
  await expect(page.locator("#case-report-dialog")).toHaveAttribute("open", "");
  await fillReport(page);
  await expect(page.locator('[data-professional-report-v220="220.1"]')).toContainText("جميع التطبيقات المكتملة تحمل عقدًا منظمًا");
  await page.locator('#case-report-form button[type="submit"]').click();
  await expect(page.locator("#case-report-dialog")).not.toHaveAttribute("open", "");

  const finalStore = await activeStore(page);
  const report = finalStore.cases[0].reports[0];
  expect(report.reviewStatus).toBe("final");
  expect(report.professionalSourcesContract.schema).toBe("case-report-professional-sources-v220");
  expect(report.professionalSourcesContract.rightsValidCompletedRecords).toBe(1);
  expect(report.professionalSourcesContract.incompleteCompletedRecordIds).toEqual([]);
  expect(report.professionalSourcesContract.protectedContentStored).toBe(false);
});
