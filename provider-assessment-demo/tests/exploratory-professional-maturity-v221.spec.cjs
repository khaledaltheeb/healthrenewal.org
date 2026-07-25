"use strict";

const { test, expect } = require("@playwright/test");

const activeStore = async (page) => page.evaluate(() => {
  const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
  const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
  const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
  if (!identity?.uid) throw new Error("active UID is missing");
  return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
});

const fillIfPresent = async (page, selector, value, mode = "fill") => {
  const locator = page.locator(selector);
  if (await locator.count()) {
    if (mode === "select") await locator.selectOption(value);
    else if (mode === "check") await locator.check();
    else await locator.fill(value);
  }
};

const createCase = async (page) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  const form = page.locator("#case-form");
  await form.locator('[name="alias"]').fill("حالة عقد النضج 01");
  await form.locator('[name="ageGroup"]').selectOption("child");
  await form.locator('[name="language"]').selectOption("ar");
  await form.locator('[name="informant"]').selectOption("multiple");
  await form.locator('[name="question"]').fill("كيف نوثق نتيجة مهنية رسمية دون حفظ مواد محمية؟");
  await form.locator('[name="notes"]').fill("بيانات اختبار اصطناعية بلا معلومات تعريفية.");
  await form.locator('button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const fillBaseRecord = async (page, status, notes) => {
  const form = page.locator("#professional-record-form");
  await form.locator('[name="recordStatus"]').selectOption(status);
  await form.locator('[name="administrationDate"]').fill("2026-07-25");
  await form.locator('[name="assignedEntityLabel"]').fill("فريق تقييم متعدد التخصصات");
  await form.locator('[name="performerName"]').fill("رمز مختص P-220");
  await form.locator('[name="outcomeLabel"]').fill("خلاصة مهنية منظمة تحتاج دمجًا متعدد المصادر");
  await form.locator('[name="scoreReference"]').fill("OFFICIAL-REPORT-V220-001");
  await form.locator('[name="nextAction"]').selectOption("team_review");
  await form.locator('[name="notes"]').fill(notes);
  await form.locator('[name="rightsConfirmed"]').check();

  await fillIfPresent(page, '#professional-record-form [name="detail_purpose"]', "planning", "select");
  await fillIfPresent(page, '#professional-record-form [name="detail_setting"]', "multiple", "select");
  await fillIfPresent(page, '#professional-record-form [name="detail_validity"]', "qualified", "select");
  await fillIfPresent(page, '#professional-record-form [name="detail_informants"][value="records"]', "", "check");
  await fillIfPresent(page, '#professional-record-form [name="detail_informants"][value="provider"]', "", "check");
  await fillIfPresent(page, '#professional-record-form [name="detail_limitations"]', "التفسير محدود بالنسخة واللغة والسياق والمصدر الرسمي المتاح.");
  await fillIfPresent(page, '#professional-record-form [name="detail_result_summary"]', "خلاصة نتيجة رسمية دون بنود أو استجابات فردية.");
  await fillIfPresent(page, '#professional-record-form [name="detail_domain_findings"]', "تحتاج الخلاصة إلى دمجها مع التاريخ والملاحظة والأداء الوظيفي.");
  await fillIfPresent(page, '#professional-record-form [name="detail_recommendations"]', "مراجعة الفريق وتحديد مصدر مكمل قبل القرار.");
};

test("expanded original tools and rights-safe professional records work in Chromium", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));

  await page.goto("/provider-assessment-demo/?release=2026.07.24-live.7#workspace", { waitUntil: "networkidle" });

  await expect.poll(() => page.evaluate(() => window.PA_EXPLORATORY_MATURITY_V220?.toolCount || 0)).toBe(20);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_REGISTRY_V220))).toBe(true);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_RECORD_V220))).toBe(true);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_PLANNING_COMPAT_V220))).toBe(true);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_SCHEMA_COMPAT_V220?.migrationAudited))).toBe(true);
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_PROFESSIONAL_EDIT_V220?.legacyRecordsUpgradable))).toBe(true);

  const maturity = await page.evaluate(() => window.PA_EXPLORATORY_MATURITY_V220);
  expect(maturity.toolCount).toBe(20);
  expect(maturity.minimumQuestions).toBeGreaterThanOrEqual(12);
  expect(maturity.minimumDomains).toBeGreaterThanOrEqual(6);
  expect(maturity.nonDiagnostic).toBe(true);
  expect(maturity.protectedItemsCopied).toBe(false);
  await expect(page.locator("html")).toHaveAttribute("data-exploratory-maturity", "ready");

  await createCase(page);
  await page.locator('button.tab[data-view="professional"]').click();
  const toolButton = page.locator("[data-v220-record-tool]").first();
  await expect(toolButton).toBeVisible();
  const toolId = await toolButton.getAttribute("data-v220-record-tool");
  const contract = await page.evaluate((id) => {
    const tool = window.PA_DEMO_DATA.professional.find((item) => item.id === id);
    return {
      id: tool.id,
      recordType: tool.professionalContract.recordType,
      rightsBasis: tool.professionalContract.permittedRightsBases[0],
      scoreSource: tool.professionalContract.permittedScoreSources[0],
    };
  }, toolId);

  await toolButton.click();
  const dialog = page.locator("#professional-record-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await fillBaseRecord(page, "completed", "خلاصة تقرير رسمي فقط؛ لا توجد مواد أداة محمية داخل السجل.");

  const form = page.locator("#professional-record-form");
  await form.locator('[name="maturity_publisher"]').fill("الناشر أو الجهة الرسمية");
  await form.locator('[name="maturity_instrumentVersion"]').fill("الإصدار الرسمي 2026");
  await form.locator('[name="maturity_administrationLanguage"]').fill("العربية");
  await form.locator('[name="maturity_administratorQualification"]').fill("مختص مؤهل ومرخص حسب الأداة");
  await form.locator('[name="maturity_rightsBasis"]').selectOption(contract.rightsBasis);
  await form.locator('[name="maturity_rightsReference"]').fill("RIGHTS-REFERENCE-V220-001");
  await form.locator('[name="maturity_scoreSource"]').selectOption(contract.scoreSource);
  await form.locator('[name="maturity_officialSourceReference"]').fill("OFFICIAL-SOURCE-V220-001");
  await form.locator('[name="maturity_selectionRationale"]').fill("اختيرت الأداة للإجابة عن سؤال إحالة محدد مع مصادر معلومات مكملة.");
  await form.locator('[name="maturity_administrationQuality"]').fill("تم التطبيق خارج المنصة وفق دليل النسخة الرسمية وفي بيئة مناسبة.");
  await form.locator('[name="maturity_behavioralObservations"]').fill("كانت المشاركة مستقرة وفهم التعليمات موثقًا ضمن التقرير الرسمي.");
  await form.locator('[name="maturity_interpretationLimitations"]').fill("تحد اللغة والسياق والتكييفات من التعميم ولا تسمح بتشخيص آلي.");
  await form.locator('[name="maturity_integrationSummary"]').fill("دُمجت الخلاصة مع التاريخ والملاحظة والأداء الوظيفي ومصادر الأسرة.");
  await form.locator('[name="maturity_recommendations"]').fill("مراجعة الفريق وإضافة مصدر مكمل ومتابعة الأثر الوظيفي.");
  await form.locator('[name="maturity_followUpDate"]').fill("2026-08-25");
  await form.locator('[name="maturity_reviewStatus"]').selectOption("self_checked");
  await form.locator('[name="maturity_noProtectedContent"]').check();
  await form.locator('button[type="submit"]').click();

  await expect(dialog).not.toHaveAttribute("open", "");
  await expect.poll(async () => {
    const state = await activeStore(page);
    return state.cases[0].professionalAssessments[0]?.schemaCompatibilityVersion || "";
  }).toBe("220.2");

  let store = await activeStore(page);
  expect(store.cases[0].professionalAssessments).toHaveLength(1);
  const record = store.cases[0].professionalAssessments[0];
  expect(record.toolId).toBe(contract.id);
  expect(record.professionalMaturity.schema).toBe("professional-registry-record-v220");
  expect(record.digitalAdministrationOccurredInsidePlatform).toBe(false);
  expect(record.protectedContentStored).toBe(false);
  expect(record.professionalMaturity.rights.protectedContentStored).toBe(false);
  expect(record.professionalMaturity.rights.itemResponsesStored).toBe(false);
  expect(record.professionalMaturity.rights.scoringKeyStored).toBe(false);
  expect(record.professionalMaturity.rights.normTablesStored).toBe(false);
  expect(record.professionalMaturity.rights.basis).not.toBe("pending_review");
  expect(record.reportIssuedBy).toBe("الناشر أو الجهة الرسمية");
  expect(record.reportIssuer).toBeUndefined();
  expect(record.metadataAuditTrail.some((entry) => entry.eventType === "schema_alias_migrated")).toBe(true);

  await page.locator('button.tab[data-view="professional"]').click();
  await page.locator(`[data-v220-record-tool="${contract.id}"]`).click();
  await expect(dialog).toHaveAttribute("open", "");
  await fillBaseRecord(page, "planned", "يحتوي هذا النص على مفتاح التصحيح ويجب رفضه بالكامل.");
  await form.locator('button[type="submit"]').click();

  await expect(dialog).toHaveAttribute("open", "");
  await expect(page.locator("#live-region")).toContainText("رُفض الحفظ لأن النص قد يتضمن مادة محمية");
  store = await activeStore(page);
  expect(store.cases[0].professionalAssessments).toHaveLength(1);

  expect(errors).toEqual([]);
});
