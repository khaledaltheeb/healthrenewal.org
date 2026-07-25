"use strict";

const { test, expect } = require("@playwright/test");

const activeStore = async (page) => page.evaluate(() => {
  const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
  const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
  const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
  if (!identity?.uid) throw new Error("active UID is missing");
  return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
});

const createCase = async (page) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  const form = page.locator("#case-form");
  await form.locator('[name="alias"]').fill("حالة ترقية سجل مهني 221");
  await form.locator('[name="ageGroup"]').selectOption("adult");
  await form.locator('[name="language"]').selectOption("ar");
  await form.locator('[name="informant"]').selectOption("self");
  await form.locator('[name="question"]').fill("كيف ندمج تقريرًا مهنيًا خارجيًا دون حفظ مواد محمية؟");
  await form.locator('[name="notes"]').fill("حالة اصطناعية مخصصة لاختبار ترقية السجل محليًا.");
  await form.locator('button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const fillOptionalProfessionalTemplate = async (form) => {
  const select = async (name, value) => {
    const field = form.locator(`[name="${name}"]`);
    if (await field.count()) await field.selectOption(value);
  };
  const fill = async (name, value) => {
    const field = form.locator(`[name="${name}"]`);
    if (await field.count()) await field.fill(value);
  };
  const check = async (selector) => {
    const field = form.locator(selector);
    if (await field.count()) await field.check();
  };
  await select("detail_purpose", "planning");
  await select("detail_setting", "multiple");
  await select("detail_validity", "qualified");
  await check('[name="detail_informants"][value="records"]');
  await check('[name="detail_informants"][value="provider"]');
  await fill("detail_limitations", "التفسير محدود بالنسخة واللغة والسياق والمصدر الرسمي.");
  await fill("detail_result_summary", "خلاصة تقرير رسمي دون بنود أو استجابات فردية.");
  await fill("detail_domain_findings", "تحتاج النتيجة إلى دمجها مع التاريخ والملاحظة والأداء الوظيفي.");
  await fill("detail_recommendations", "استكمال الحقوق والنسخة والمصدر قبل اعتماد التقرير.");
};

test("planned custom record can be upgraded atomically after an official result arrives", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));

  await page.goto("/provider-assessment-demo/?release=2026.07.24-live.7#workspace", { waitUntil: "networkidle" });
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_REGISTRY_V220?.customContractForMode))).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_PLANNING_COMPAT_V220?.planningDraftAllowed)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_SCHEMA_COMPAT_V220?.migrationAudited)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.PA_PROFESSIONAL_EDIT_V220?.legacyRecordsUpgradable)).toBe(true);

  await createCase(page);
  await page.locator('button.tab[data-view="professional-records"]').click();
  await page.locator("#professional-record-new").click();
  const dialog = page.locator("#professional-record-dialog");
  await expect(dialog).toHaveAttribute("open", "");

  const form = page.locator("#professional-record-form");
  await form.locator('[name="recordStatus"]').selectOption("planned");
  await form.locator('[name="administrationDate"]').fill("2026-07-25");
  await form.locator('[name="assignedEntityLabel"]').fill("جهة تقييم خارجية");
  await form.locator('[name="performerName"]').fill("رمز المختص EXT-221");
  await form.locator('[name="administrationMode"]').selectOption("external_import");
  await form.locator('[name="versionLanguage"]').fill("تقرير خارجي عربي — النسخة الرسمية");
  await form.locator('[name="outcomeLabel"]').fill("تقرير مخطط للاستلام والمراجعة");
  await form.locator('[name="scoreReference"]').fill("EXT-REPORT-221");
  await form.locator('[name="nextAction"]').selectOption("team_review");
  await form.locator('[name="notes"]').fill("مرجع التقرير فقط دون بنود أو مفاتيح تصحيح أو جداول معيارية.");
  await fillOptionalProfessionalTemplate(form);
  await form.locator('[name="rightsConfirmed"]').check();
  await expect(page.locator("#professional-maturity-fields-v220")).toHaveAttribute("data-record-requirement", "planning-draft");
  await form.locator('button[type="submit"]').click();
  await expect(dialog).not.toHaveAttribute("open", "");

  let state = await activeStore(page);
  expect(state.cases[0].professionalAssessments).toHaveLength(1);
  expect(state.cases[0].professionalAssessments[0].recordStatus).toBe("planned");
  expect(state.cases[0].professionalAssessments[0].professionalMaturity?.rights?.basis).toBe("pending_review");

  await page.locator("[data-lifecycle-record]").first().click();
  const lifecycle = page.locator("#professional-lifecycle-dialog");
  await expect(lifecycle).toHaveAttribute("open", "");
  await lifecycle.locator('[name="recordStatus"]').selectOption("result_imported");
  await lifecycle.locator('[name="changeReason"]').fill("استلم التقرير الرسمي ويجب استكمال عقد الحقوق والنسخة والمصدر.");
  await lifecycle.locator('[name="outcomeLabel"]').fill("نتيجة خارجية مستلمة وتحت المراجعة المهنية");
  await lifecycle.locator('button[type="submit"]').click();
  await expect(lifecycle).not.toHaveAttribute("open", "");

  await page.locator("[data-edit-professional-record]").first().click();
  const editDialog = page.locator("#professional-record-edit-dialog");
  await expect(editDialog).toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-edit-maturity-v220")).toBeVisible();
  const edit = page.locator("#professional-record-edit-form");
  await edit.locator('[name="practitionerQualification"]').fill("أخصائي مرخص — رمز مهني داخلي");
  await edit.locator('[name="resultSourceType"]').selectOption("external_report");
  await edit.locator('[name="reportReference"]').fill("EXT-REPORT-221");
  await edit.locator('[name="reportIssuedBy"]').fill("الجهة المهنية المصدرة");
  await edit.locator('[name="edit_maturity_publisher"]').fill("الناشر أو الجهة المالكة الرسمية");
  await edit.locator('[name="edit_maturity_instrumentVersion"]').fill("الإصدار الرسمي 2026");
  await edit.locator('[name="edit_maturity_administrationLanguage"]').fill("العربية");
  await edit.locator('[name="edit_maturity_rightsBasis"]').selectOption("external_report_only");
  await edit.locator('[name="edit_maturity_rightsReference"]').fill("RIGHTS-EXT-221");
  await edit.locator('[name="edit_maturity_scoreSource"]').selectOption("official_report");
  await edit.locator('[name="edit_maturity_officialSourceReference"]').fill("EXT-REPORT-221");
  await edit.locator('[name="edit_maturity_selectionRationale"]').fill("اختير التقرير للإجابة عن سؤال الإحالة مع دمجه بمصادر وظيفية مستقلة.");
  await edit.locator('[name="edit_maturity_administrationQuality"]').fill("تحققت الجهة والنسخة واللغة واكتمال التقرير وظروف التطبيق.");
  await edit.locator('[name="edit_maturity_behavioralObservations"]').fill("المشاركة موثقة مع حاجة إلى دعم لغوي في بعض المواقف.");
  await edit.locator('[name="edit_maturity_interpretationLimitations"]').fill("لا توجد بيانات خام داخل المنصة والتفسير محدود بالتقرير والسياقات.");
  await edit.locator('[name="edit_maturity_integrationSummary"]').fill("تتفق الخلاصة جزئيًا مع التاريخ والملاحظة وتحتاج مصدرًا مكملًا.");
  await edit.locator('[name="edit_maturity_recommendations"]').fill("مراجعة فريق متعدد التخصصات وتجربة تكييف ثم متابعة الأثر.");
  await edit.locator('[name="edit_maturity_followUpDate"]').fill("2026-09-25");
  await edit.locator('[name="edit_maturity_reviewedBy"]').fill("فريق المراجعة EXT-221");
  await edit.locator('[name="edit_maturity_reviewStatus"]').selectOption("team_reviewed");
  await edit.locator('[name="edit_maturity_noProtectedContent"]').check();
  await edit.locator('[name="editReason"]').fill("استكمال عقد الحقوق والنسخة والمصدر بعد استلام التقرير الرسمي.");
  await edit.locator('[name="rightsConfirmed"]').check();
  await edit.locator('button[type="submit"]').click();
  await expect(editDialog).not.toHaveAttribute("open", "");

  state = await activeStore(page);
  const record = state.cases[0].professionalAssessments[0];
  expect(record.recordStatus).toBe("result_imported");
  expect(record.reportIssuedBy).toBe("الجهة المهنية المصدرة");
  expect(record.reportIssuer).toBeUndefined();
  expect(record.professionalMaturity.schema).toBe("professional-registry-record-v220");
  expect(record.professionalMaturity.rights.basis).toBe("external_report_only");
  expect(record.professionalMaturity.contractSnapshot.source).toBe("custom_mode_bound_contract");
  expect(record.professionalMaturity.auditTrail.at(-1).event).toBe("structured_record_updated");
  expect(record.protectedContentStored).toBe(false);
  expect(record.metadataAuditTrail.some((entry) => entry.eventType === "metadata_updated")).toBe(true);
  expect(errors).toEqual([]);
});
