"use strict";

const fs = require("node:fs");
const { test, expect } = require("@playwright/test");

const fillCase = async (page, alias) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  await page.locator('#case-form [name="alias"]').fill(alias);
  await page.locator('#case-form [name="ageGroup"]').selectOption("child");
  await page.locator('#case-form [name="language"]').selectOption("ar");
  await page.locator('#case-form [name="informant"]').selectOption("multiple");
  await page.locator('#case-form [name="question"]').fill("كيف نوثق نتيجة خارجية ونراجعها ضمن دورة مهنية قابلة للتدقيق؟");
  await page.locator('#case-form [name="notes"]').fill("بيانات اصطناعية لا تتضمن معلومات تعريف مباشرة.");
  await page.locator('#case-form button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const updateLifecycle = async (page, status, reason, outcome) => {
  await page.locator("[data-lifecycle-record]").first().click();
  const dialog = page.locator("#professional-lifecycle-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await page.locator('#professional-lifecycle-form [name="recordStatus"]').selectOption(status);
  await page.locator('#professional-lifecycle-form [name="changeReason"]').fill(reason);
  await page.locator('#professional-lifecycle-form [name="outcomeLabel"]').fill(outcome);
  await page.locator('#professional-lifecycle-form button[type="submit"]').click();
  await expect(dialog).not.toHaveAttribute("open", "");
};

const activeStore = async (page) => page.evaluate(() => {
  const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
  const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
  const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
  if (!identity?.uid) throw new Error("active UID is missing");
  return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
});

test("professional record lifecycle, audited amendment, encrypted replacement, and rollback remain intact", async ({ page }) => {
  await page.goto("/provider-assessment-demo/?open=records&release=2026.07.24-live.7#workspace");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator('button.tab[data-view="professional-records"]')).toBeVisible();

  await fillCase(page, "الحالة المهنية الآلية 01");

  await page.locator('button.tab[data-view="professional-records"]').click();
  await page.locator("#professional-record-new").click();
  const recordDialog = page.locator("#professional-record-dialog");
  await expect(recordDialog).toHaveAttribute("open", "");
  await page.locator('#professional-record-form [name="recordStatus"]').selectOption("planned");
  await page.locator('#professional-record-form [name="assignedEntityLabel"]').fill("فريق تقييم متعدد التخصصات");
  await page.locator('#professional-record-form [name="performerName"]').fill("رمز المختص P-01");
  await page.locator('#professional-record-form [name="administrationMode"]').selectOption("external_import");
  await page.locator('#professional-record-form [name="versionLanguage"]').fill("تقرير خارجي عربي — إصدار الجهة المالكة");
  await page.locator('#professional-record-form [name="outcomeLabel"]').fill("بانتظار استلام التقرير الخارجي ومراجعته مهنيًا");
  await page.locator('#professional-record-form [name="scoreReference"]').fill("EXT-REPORT-2026-001");
  await page.locator('#professional-record-form [name="nextAction"]').selectOption("team_review");
  await page.locator('#professional-record-form [name="notes"]').fill("لم تُنسخ بنود أو مفاتيح تصحيح أو معايير؛ سُجل مرجع التقرير فقط.");
  await page.locator('#professional-record-form [name="detail_purpose"]').selectOption("planning");
  await page.locator('#professional-record-form [name="detail_setting"]').selectOption("multiple");
  await page.locator('#professional-record-form [name="detail_validity"]').selectOption("qualified");
  await page.locator('#professional-record-form [name="detail_informants"][value="records"]').check();
  await page.locator('#professional-record-form [name="detail_informants"][value="provider"]').check();
  await page.locator('#professional-record-form [name="detail_limitations"]').fill("التفسير محدود بملخص التقرير الخارجي والسياقات المتاحة للمراجعة.");
  await page.locator('#professional-record-form [name="detail_result_summary"]').fill("مرجع نتيجة خارجية قيد المراجعة؛ لا توجد مواد محمية داخل المنصة.");
  await page.locator('#professional-record-form [name="detail_domain_findings"]').fill("تحتاج النتيجة إلى دمجها مع التاريخ والملاحظة والسياق الوظيفي.");
  await page.locator('#professional-record-form [name="detail_recommendations"]').fill("مراجعة الفريق وتحديد الحاجة إلى مصدر مكمل قبل اتخاذ القرار.");
  await page.locator('#professional-record-form [name="rightsConfirmed"]').check();
  await page.locator('#professional-record-form button[type="submit"]').click();

  await expect(recordDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);
  await expect(page.locator("#professional-record-list")).toContainText("EXT-REPORT-2026-001");

  await updateLifecycle(page, "in_progress", "بدأت مراجعة التقرير الخارجي والتحقق من الجهة والإصدار واللغة.", "قيد المراجعة المهنية متعددة المصادر");
  await updateLifecycle(page, "result_imported", "اكتملت مراجعة التقرير الخارجي وسُجل المرجع دون نسخ محتواه المحمي.", "تقرير خارجي مستلم ومراجع ضمن حدود المصدر");

  await expect(page.locator("#professional-record-list")).toContainText("تقرير خارجي مستلم");
  await expect(page.locator("#professional-record-list details.audit-details")).toContainText("سجل تغيرات الحالة (2)");

  await page.locator("[data-edit-professional-record]").first().click();
  const editDialog = page.locator("#professional-record-edit-dialog");
  await expect(editDialog).toHaveAttribute("open", "");
  await page.locator('#professional-record-edit-form [name="practitionerQualification"]').fill("أخصائي نفسي مرخص — رمز مهني داخلي");
  await page.locator('#professional-record-edit-form [name="resultSourceType"]').selectOption("external_report");
  await page.locator('#professional-record-edit-form [name="reportReference"]').fill("EXT-REPORT-2026-001");
  await page.locator('#professional-record-edit-form [name="reportIssuedBy"]').fill("جهة تقييم خارجية مختصة");
  await page.locator('#professional-record-edit-form [name="notes"]').fill("النتيجة الخارجية دليل واحد ضمن مصادر متعددة، ولا تثبت التشخيص أو الأهلية تلقائيًا.");
  await page.locator('#professional-record-edit-form [name="editReason"]').fill("استكمال مصدر النتيجة والمؤهل ومرجع التقرير بعد التحقق.");
  await page.locator('#professional-record-edit-form [name="rightsConfirmed"]').check();
  await page.locator('#professional-record-edit-form button[type="submit"]').click();
  await expect(editDialog).not.toHaveAttribute("open", "");

  const afterAmendment = await activeStore(page);
  const amendedRecord = afterAmendment.cases[0].professionalAssessments[0];
  expect(amendedRecord.recordStatus).toBe("result_imported");
  expect(amendedRecord.auditTrail).toHaveLength(2);
  expect(amendedRecord.metadataAuditTrail).toHaveLength(1);
  expect(amendedRecord.practitionerQualification).toContain("مرخص");
  expect(amendedRecord.resultSourceType).toBe("external_report");
  expect(amendedRecord.reportReference).toBe("EXT-REPORT-2026-001");
  expect(amendedRecord.reportIssuedBy).toContain("جهة تقييم");

  await page.locator('button.tab[data-view="analytics"]').click();
  await expect(page.locator("#export-space")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#export-space").click();
  await expect(page.locator("#backup-export-dialog")).toHaveAttribute("open", "");
  await page.locator('#backup-export-form [name="encryptBackup"]').check();
  await page.locator('#backup-export-form [name="passphrase"]').fill("Secure-Backup-2026!");
  await page.locator('#backup-export-form button[type="submit"]').click();
  const encryptedDownload = await downloadPromise;
  const encryptedPath = await encryptedDownload.path();
  expect(encryptedPath).toBeTruthy();
  const encryptedJson = JSON.parse(fs.readFileSync(encryptedPath, "utf8"));
  expect(encryptedJson.schema).toBe("pa-demo-uid-backup-encrypted-v1");
  expect(encryptedJson.kdf).toBe("PBKDF2-SHA-256");
  expect(encryptedJson.iterations).toBe(250000);
  expect(encryptedJson.cipher).toBe("AES-GCM-256");
  expect(encryptedJson.ciphertext.length).toBeGreaterThan(100);

  await fillCase(page, "الحالة المؤقتة قبل الاستعادة");
  await expect(page.locator("#case-count")).toHaveText("2");
  await page.locator('button.tab[data-view="analytics"]').click();

  const chooserPromise = page.waitForEvent("filechooser");
  await page.locator("#import-space").click();
  const chooser = await chooserPromise;
  await chooser.setFiles(encryptedPath);
  await expect(page.locator("#backup-unlock-dialog")).toHaveAttribute("open", "");
  await page.locator('#backup-unlock-form [name="passphrase"]').fill("Secure-Backup-2026!");
  await page.locator('#backup-unlock-form button[type="submit"]').click();

  const preview = page.locator("#backup-import-preview-dialog");
  await expect(preview).toHaveAttribute("open", "");
  await expect(page.locator("#backup-import-preview-summary")).toContainText("بصمة SHA-256 مطابقة");
  await expect(page.locator("#backup-import-preview-summary")).toContainText("السجلات المهنية");
  await page.locator('#backup-import-preview-form [name="importMode"]').selectOption("replace");
  await page.locator('#backup-import-preview-form button[type="submit"]').click();
  await expect(preview).not.toHaveAttribute("open", "");
  await expect(page.locator("#case-count")).toHaveText("1");

  const restored = await activeStore(page);
  expect(restored.cases).toHaveLength(1);
  const restoredRecord = restored.cases[0].professionalAssessments[0];
  expect(restoredRecord.auditTrail).toHaveLength(2);
  expect(restoredRecord.metadataAuditTrail).toHaveLength(1);
  expect(restoredRecord.practitionerQualification).toContain("مرخص");
  expect(restoredRecord.reportReference).toBe("EXT-REPORT-2026-001");

  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#rollback-space-import").click();
  await expect(page.locator("#case-count")).toHaveText("2");

  const rolledBack = await activeStore(page);
  expect(rolledBack.cases).toHaveLength(2);
  const originalRecord = rolledBack.cases.flatMap((item) => item.professionalAssessments || [])[0];
  expect(originalRecord.recordStatus).toBe("result_imported");
  expect(originalRecord.auditTrail).toHaveLength(2);
  expect(originalRecord.metadataAuditTrail).toHaveLength(1);
  expect(originalRecord.scoreReference).toBe("EXT-REPORT-2026-001");
});
