"use strict";

const fs = require("node:fs");
const { test, expect } = require("@playwright/test");

const fill = async (page, name, value) => {
  const field = page.locator(`#case-report-form [name="${name}"]`);
  await expect(field).toBeVisible();
  await field.fill(value);
};

test("unified console creates an immutable report revision and exports complete files", async ({ page }) => {
  await page.goto("/provider-assessment-demo/professional-console.html");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: /اختر المقياس أو الفحص/ })).toBeVisible();

  await Promise.all([
    page.waitForURL(/open=reports/),
    page.getByRole("link", { name: "فتح التقارير المهنية" }).click(),
  ]);

  const reportsTab = page.locator('button.tab[data-view="reports"]');
  await expect(reportsTab).toBeVisible();
  await expect(reportsTab).toHaveAttribute("aria-selected", "true");

  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  await expect(page.locator("#case-dialog")).toHaveAttribute("open", "");
  await page.locator('#case-form [name="alias"]').fill("الحالة الآلية 01");
  await page.locator('#case-form [name="ageGroup"]').selectOption("child");
  await page.locator('#case-form [name="language"]').selectOption("ar");
  await page.locator('#case-form [name="informant"]').selectOption("parent");
  await page.locator('#case-form [name="question"]').fill("كيف نتابع تطور التواصل الوظيفي خلال خطة الدعم؟");
  await page.locator('#case-form [name="notes"]').fill("بيانات اختبار آلية دون معلومات تعريف مباشرة.");
  await page.locator('#case-form button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");

  await reportsTab.click();
  await page.locator("#new-case-report").click();
  const reportDialog = page.locator("#case-report-dialog");
  await expect(reportDialog).toHaveAttribute("open", "");

  await page.locator('#case-report-form [name="reviewStatus"]').selectOption("reviewed");
  await page.locator('#case-report-form [name="reportType"]').selectOption("progress");
  await page.locator('#case-report-form [name="assessmentType"]').selectOption("progress");
  await fill(page, "evidenceSources", "مقابلة الأسرة، ملاحظة مباشرة، وسجل الجلسات المحلية.");
  await fill(page, "resultValidity", "تمت المراجعة في بيئة مألوفة وباللغة الأساسية مع توثيق ظروف التطبيق.");
  await fill(page, "interpretationLimitations", "لا توجد عينة مدرسية مستقلة في هذا الإصدار، لذلك يبقى التفسير محدودًا بالسياق المسجل.");
  await fill(page, "functionalContexts", "المنزل، جلسة الدعم، والمواقف اليومية التي تتطلب طلب المساعدة.");
  await fill(page, "baselineIndicator", "يبدأ طلبًا وظيفيًا مستقلًا في موقف واحد من كل خمس فرص.");
  await fill(page, "measurementMethod", "عدد المبادرات المستقلة من خمس فرص موثقة أسبوعيًا.");
  await fill(page, "measurableGoal", "خلال أربعة أسابيع يبدأ طلبًا وظيفيًا مستقلًا في أربع فرص من خمس عبر سياقين.");
  await page.locator('#case-report-form [name="remeasurementDate"]').fill("2026-08-24");
  await fill(page, "providerInterpretation", "تشير البيانات الحالية إلى حاجة لدعم المبادرة الوظيفية مع الحفاظ على التفسير متعدد المصادر.");
  await fill(page, "familySummary", "تظهر نقطة قوة في الاستجابة، والخطوة التالية هي تدريب المبادرة وقياسها أسبوعيًا دون اعتبار النتيجة تشخيصًا.");
  await fill(page, "strengths", "يستجيب للتوجيه البصري ويشارك عندما تكون المهمة واضحة.");
  await fill(page, "needs", "زيادة المبادرات الوظيفية وتعميمها بين أكثر من موقف.");
  await fill(page, "integratedSummary", "تتفق الملاحظة وسجل الأسرة على أن الاستجابة أفضل من المبادرة، مع حاجة إلى بيانات إضافية من سياق ثانٍ.");
  await fill(page, "recommendations", "استخدام فرص قصيرة متكررة، تقليل المساعدة تدريجيًا، وتوثيق المبادرات أسبوعيًا.");
  await page.locator('#case-report-form [name="decision"]').selectOption("support_plan");
  await page.locator('#case-report-form [name="followUpDate"]').fill("2026-08-24");
  await fill(page, "followUpIndicators", "عدد المبادرات المستقلة، مستوى المساعدة، وعدد السياقات التي ظهر فيها السلوك.");
  await page.locator('#case-report-form button[type="submit"]').click();

  await expect(reportDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#report-list .report-card")).toHaveCount(1);
  await expect(page.locator("#report-stats")).toContainText("1");

  await page.locator("#report-list [data-open-report]").first().click();
  await expect(reportDialog).toHaveAttribute("open", "");
  await fill(page, "providerInterpretation", "تؤكد المراجعة استمرار الحاجة إلى دعم المبادرة، مع تحسن أولي يستدعي تثبيت طريقة القياس نفسها.");
  await fill(page, "revisionReason", "إضافة مراجعة تفسيرية بعد تدقيق الهدف وطريقة القياس.");
  await page.locator('#case-report-form button[type="submit"]').click();

  await expect(page.locator("#report-list .report-card")).toHaveCount(2);
  await expect(page.locator("#report-list")).toContainText("الإصدار");
  await expect(page.locator("#report-list")).toContainText("مبني على");

  await page.locator("#report-list [data-open-report]").first().click();
  await expect(reportDialog).toHaveAttribute("open", "");

  const htmlDownloadPromise = page.waitForEvent("download");
  await page.locator("#export-case-report-html").click();
  const htmlDownload = await htmlDownloadPromise;
  const htmlPath = await htmlDownload.path();
  expect(htmlPath).toBeTruthy();
  const exportedHtml = fs.readFileSync(htmlPath, "utf8");
  expect(exportedHtml).toContain('<html lang="ar" dir="rtl">');
  expect(exportedHtml).toContain("ملخص موجه للأسرة أو الشخص");
  expect(exportedHtml).toContain("سجل مراجعة التفسير");
  expect(exportedHtml).toContain("خط الأساس والهدف وإعادة القياس");

  const jsonDownloadPromise = page.waitForEvent("download");
  await page.locator("#export-case-report-json").click();
  const jsonDownload = await jsonDownloadPromise;
  const jsonPath = await jsonDownload.path();
  expect(jsonPath).toBeTruthy();
  const exportedJson = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  expect(exportedJson.ownerUid).toBeTruthy();
  expect(exportedJson.report.assessmentType).toBe("progress");
  expect(exportedJson.report.familySummary).toContain("نقطة قوة");
  expect(exportedJson.report.reviewAuditTrail).toContain("revision");
  expect(exportedJson.report.supersedesReportId).toBeTruthy();
});
