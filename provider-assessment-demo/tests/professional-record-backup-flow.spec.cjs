"use strict";

const fs = require("node:fs");
const { test, expect } = require("@playwright/test");

const fillCase = async (page) => {
  await page.locator('button.tab[data-view="cases"]').click();
  await page.locator("#new-case-button").click();
  await page.locator('#case-form [name="alias"]').fill("الحالة المهنية الآلية 01");
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

test("professional record lifecycle, encrypted backup merge, and rollback remain auditable", async ({ page }) => {
  await page.goto("/provider-assessment-demo/?open=records&release=2026.07.24-live.7#workspace");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator('button.tab[data-view="professional-records"]')).toBeVisible();

  await fillCase(page);

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
  await page.locator('#professional-record-form [name="rightsConfirmed"]').check();
  await page.locator('#professional-record-form button[type="submit"]').click();

  await expect(recordDialog).not.toHaveAttribute("open", "");
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);
  await expect(page.locator("#professional-record-list")).toContainText("EXT-REPORT-2026-001");

  await updateLifecycle(
    page,
    "in_progress",
    "بدأت مراجعة التقرير الخارجي والتحقق من الجهة والإصدار واللغة.",
    "قيد المراجعة المهنية متعددة المصادر"
  );
  await updateLifecycle(
    page,
    "result_imported",
    "اكتملت مراجعة التقرير الخارجي وسُجل المرجع دون نسخ محتواه المحمي.",
    "تقرير خارجي مستلم ومراجع ضمن حدود المصدر"
  );

  await expect(page.locator("#professional-record-list")).toContainText("تقرير خارجي مستلم");
  await expect(page.locator("#professional-record-list details.audit-details")).toContainText("سجل تغيرات الحالة (2)");

  await page.locator('button.tab[data-view="dashboard"]').click();
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
  expect(encryptedJson.cipher).toBe("AES-GCM-256");
  expect(encryptedJson.ciphertext.length).toBeGreaterThan(100);

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
  await page.locator('#backup-import-preview-form [name="importMode"]').selectOption("merge");
  await page.locator('#backup-import-preview-form button[type="submit"]').click();
  await expect(preview).not.toHaveAttribute("open", "");

  await page.locator('button.tab[data-view="professional-records"]').click();
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(2);

  page.once("dialog", (dialog) => dialog.accept());
  await page.locator('button.tab[data-view="dashboard"]').click();
  await page.locator("#rollback-space-import").click();
  await page.locator('button.tab[data-view="professional-records"]').click();
  await expect(page.locator("#professional-record-list .professional-record")).toHaveCount(1);
  await expect(page.locator("#professional-record-list details.audit-details")).toContainText("سجل تغيرات الحالة (2)");

  const stored = await page.evaluate(() => {
    const active = JSON.parse(localStorage.getItem("pa-demo-active-v3") || "null");
    const identities = JSON.parse(localStorage.getItem("pa-demo-identities-v3") || "{}");
    const identity = active?.role === "provider" ? identities[active.username] : identities.__visitor__;
    return JSON.parse(localStorage.getItem(`pa-demo-store-v3:${identity.uid}`));
  });
  expect(stored.cases).toHaveLength(1);
  expect(stored.cases[0].professionalAssessments).toHaveLength(1);
  expect(stored.cases[0].professionalAssessments[0].recordStatus).toBe("result_imported");
  expect(stored.cases[0].professionalAssessments[0].auditTrail).toHaveLength(2);
  expect(stored.cases[0].professionalAssessments[0].scoreReference).toBe("EXT-REPORT-2026-001");
});
