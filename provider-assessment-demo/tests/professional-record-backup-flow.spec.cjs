"use strict";

const fs = require("node:fs");
const { test, expect } = require("@playwright/test");

const fill = async (page, selector, value) => {
  const field = page.locator(selector);
  await expect(field).toBeVisible();
  await field.fill(value);
};

const activeStore = async (page) => page.evaluate(() => {
  const uid = document.getElementById("current-uid")?.textContent?.trim();
  if (!uid) throw new Error("active UID is missing");
  const value = localStorage.getItem(`pa-demo-store-v3:${uid}`);
  return { uid, store: JSON.parse(value || "null") };
});

const createCase = async (page, alias) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  const dialog = page.locator("#case-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await page.locator('#case-form [name="alias"]').fill(alias);
  await page.locator('#case-form [name="ageGroup"]').selectOption("child");
  await page.locator('#case-form [name="language"]').selectOption("ar");
  await page.locator('#case-form [name="informant"]').selectOption("parent");
  await page.locator('#case-form [name="question"]').fill("كيف نوثق التقييم المهني والمتابعة دون طمس السجل السابق؟");
  await page.locator('#case-form [name="notes"]').fill("بيانات اختبار آلية دون معلومات تعريف مباشرة.");
  await page.locator('#case-form button[type="submit"]').click();
  await expect(page.locator("#case-detail-dialog")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
};

const updateLifecycle = async (page, status, reason, outcome) => {
  await page.locator("[data-lifecycle-record]").first().click();
  const dialog = page.locator("#professional-lifecycle-dialog");
  await expect(dialog).toHaveAttribute("open", "");
  await page.locator('#professional-lifecycle-form [name="recordStatus"]').selectOption(status);
  await page.locator('#professional-lifecycle-form [name="effectiveDate"]').fill("2026-07-24");
  await fill(page, '#professional-lifecycle-form [name="changeReason"]', reason);
  await fill(page, '#professional-lifecycle-form [name="outcomeLabel"]', outcome);
  await page.locator('#professional-lifecycle-form [name="nextAction"]').selectOption("review");
  await page.locator('#professional-lifecycle-form button[type="submit"]').click();
  await expect(dialog).not.toHaveAttribute("open", "");
};

test("professional record lifecycle, audited amendment, encrypted restore and rollback", async ({ page }) => {
  await page.goto("/provider-assessment-demo/?open=records&release=2026.07.24-live.7#workspace");

  const recordsTab = page.locator('button.tab[data-view="professional-records"]');
  await expect(recordsTab).toBeVisible();
  await expect(recordsTab).toHaveAttribute("aria-selected", "true");

  await createCase(page, "الحالة المهنية الآلية 01");
  await recordsTab.click();

  await page.locator("#professional-record-new").click();
  const recordDialog = page.locator("#professional-record-dialog");
  await expect(recordDialog).toHaveAttribute("open", "");
  await page.locator('#professional-record-form [name="recordStatus"]').selectOption("planned");
  await page.locator('#professional-record-form [name="administrationDate"]').fill("2026-07-24");
  await fill(page, '#professional-record-form [name="assignedEntityLabel"]', "فريق تقييم متعدد التخصصات");
  await fill(page, '#professional-record-form [name="performerName"]', "PROVIDER-01");
  await page.locator('#professional-record-form [name="administrationMode"]').selectOption("record_review");
  await fill(page, '#professional-record-form [name="versionLanguage"]', "مرجع خارجي عربي — إصدار موثق");
  await fill(page, '#professional-record-form [name="outcomeLabel"]', "تم تخطيط مراجعة التقرير الخارجي");
  await fill(page, '#professional-record-form [name="scoreReference"]', "EXT-REPORT-01");
  await fill(page, '#professional-record-form [name="notes"]', "لا تتضمن هذه الملاحظة بنودًا أو مفاتيح تصحيح أو معايير محمية.");
  await page.locator('#professional-record-form [name="nextAction"]').selectOption("review");
  await page.locator('#professional-record-form [name="rightsConfirmed"]').check();
  await page.locator('#professional-record-form button[type="submit"]').click();

  await expect(recordDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);
  await expect(page.locator("#professional-record-list")).toContainText("مخطط");

  await updateLifecycle(page, "scheduled", "تم تثبيت موعد مراجعة التقرير مع الفريق.", "تم تحديد موعد المراجعة");
  await updateLifecycle(page, "in_progress", "بدأ الفريق مراجعة المرجع الخارجي وحدود صلاحيته.", "المراجعة المهنية قيد التنفيذ");
  await updateLifecycle(page, "result_imported", "استُلم التقرير الخارجي ووُثق مرجعه دون نسخ محتواه المحمي.", "تم استلام التقرير الخارجي");

  await page.locator("[data-edit-professional-record]").first().click();
  const editDialog = page.locator("#professional-record-edit-dialog");
  await expect(editDialog).toHaveAttribute("open", "");
  await fill(page, '#professional-record-edit-form [name="practitionerQualification"]', "أخصائي نفسي مرخص — رمز مهني داخلي");
  await page.locator('#professional-record-edit-form [name="resultSourceType"]').selectOption("external_report");
  await fill(page, '#professional-record-edit-form [name="reportReference"]', "EXT-REPORT-01");
  await fill(page, '#professional-record-edit-form [name="reportIssuedBy"]', "جهة تقييم خارجية مختصة");
  await fill(page, '#professional-record-edit-form [name="notes"]', "النتيجة الخارجية دليل واحد ضمن مصادر متعددة، ولا تثبت التشخيص أو الأهلية تلقائيًا.");
  await fill(page, '#professional-record-edit-form [name="editReason"]', "استكمال مصدر النتيجة والمؤهل ومرجع التقرير بعد التحقق.");
  await page.locator('#professional-record-edit-form [name="rightsConfirmed"]').check();
  await page.locator('#professional-record-edit-form button[type="submit"]').click();
  await expect(editDialog).not.toHaveAttribute("open", "");

  const afterAmendment = await activeStore(page);
  expect(afterAmendment.store.cases).toHaveLength(1);
  const record = afterAmendment.store.cases[0].professionalAssessments[0];
  expect(record.recordStatus).toBe("result_imported");
  expect(record.auditTrail).toHaveLength(3);
  expect(record.metadataAuditTrail).toHaveLength(1);
  expect(record.practitionerQualification).toContain("مرخص");
  expect(record.reportReference).toBe("EXT-REPORT-01");
  expect(record.resultSourceType).toBe("external_report");

  await page.locator('button.tab[data-view="analytics"]').click();
  await expect(page.locator("#export-space")).toBeVisible();
  await page.locator("#export-space").click();
  const exportDialog = page.locator("#backup-export-dialog");
  await expect(exportDialog).toHaveAttribute("open", "");
  await page.locator('#backup-export-form [name="encryptBackup"]').check();
  await fill(page, '#backup-export-form [name="passphrase"]', "Secure-Backup-2026!");

  const backupDownloadPromise = page.waitForEvent("download");
  await page.locator('#backup-export-form button[type="submit"]').click();
  const backupDownload = await backupDownloadPromise;
  const backupPath = await backupDownload.path();
  expect(backupPath).toBeTruthy();
  const encryptedPayload = JSON.parse(fs.readFileSync(backupPath, "utf8"));
  expect(encryptedPayload.schema).toBe("pa-demo-uid-backup-encrypted-v1");
  expect(encryptedPayload.kdf).toBe("PBKDF2-SHA-256");
  expect(encryptedPayload.iterations).toBe(250000);
  expect(encryptedPayload.cipher).toBe("AES-GCM-256");
  expect(encryptedPayload.ciphertext.length).toBeGreaterThan(100);

  await createCase(page, "الحالة المؤقتة قبل الاستعادة");
  await expect(page.locator("#case-count")).toHaveText("2");
  await page.locator('button.tab[data-view="analytics"]').click();

  await page.locator("#import-space-file").setInputFiles(backupPath);
  const unlockDialog = page.locator("#backup-unlock-dialog");
  await expect(unlockDialog).toHaveAttribute("open", "");
  await fill(page, '#backup-unlock-form [name="passphrase"]', "Secure-Backup-2026!");
  await page.locator('#backup-unlock-form button[type="submit"]').click();

  const previewDialog = page.locator("#backup-import-preview-dialog");
  await expect(previewDialog).toHaveAttribute("open", "");
  await expect(page.locator("#backup-import-preview-summary")).toContainText("بصمة SHA-256 مطابقة");
  await expect(page.locator("#backup-import-preview-summary")).toContainText("السجلات المهنية");
  await page.locator('#backup-import-preview-form [name="importMode"]').selectOption("replace");
  await page.locator('#backup-import-preview-form button[type="submit"]').click();
  await expect(previewDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#case-count")).toHaveText("1");

  const afterRestore = await activeStore(page);
  const restoredRecord = afterRestore.store.cases[0].professionalAssessments[0];
  expect(restoredRecord.recordStatus).toBe("result_imported");
  expect(restoredRecord.auditTrail).toHaveLength(3);
  expect(restoredRecord.metadataAuditTrail).toHaveLength(1);
  expect(restoredRecord.reportReference).toBe("EXT-REPORT-01");

  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#rollback-space-import").click();
  await expect(page.locator("#case-count")).toHaveText("2");
  const afterRollback = await activeStore(page);
  expect(afterRollback.store.cases).toHaveLength(2);
});
