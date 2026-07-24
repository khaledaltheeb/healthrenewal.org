const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:4173/provider-assessment-demo/';
const sharedContext = { respondent: 'parent', setting: 'home', administrationMode: 'questionnaire', supportLevel: 'usual', note: '', contractVersion: 'pa-original-session-context-v2' };

test('original tool progress plans document family provider context and audited human review', async ({ page }) => {
  await page.addInitScript((context) => {
    const identity = { uid: 'UID-GOAL-PLAN-TEST', username: 'visitor', role: 'visitor', createdAt: new Date().toISOString() };
    localStorage.setItem('pa-demo-identities-v3', JSON.stringify({ __visitor__: identity }));
    localStorage.setItem('pa-demo-active-v3', JSON.stringify({ username: 'visitor', role: 'visitor' }));
    localStorage.setItem(`pa-demo-store-v3:${identity.uid}`, JSON.stringify({
      uid: identity.uid, schemaVersion: '3', createdAt: '2026-07-01T08:00:00.000Z',
      cases: [{
        caseId: 'CASE-GOAL-001', alias: 'حالة خطة هدف', ageGroup: 'child', language: 'ar', informant: 'parent',
        question: 'ربط المتابعة الوصفية بهدف وظيفي', notes: '', status: 'active', createdAt: '2026-07-01T08:00:00.000Z', updatedAt: '2026-07-20T08:00:00.000Z',
        sessions: [
          { sessionId: 'SES-GOAL-BASE', assessmentId: 'communication-pathway', completedAt: '2026-07-01T08:30:00.000Z', averageSignal: 1.5, domainSignals: { communication: 3 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'خط أساس', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } },
          { sessionId: 'SES-GOAL-LATEST', assessmentId: 'communication-pathway', completedAt: '2026-07-20T08:30:00.000Z', averageSignal: 0.75, domainSignals: { communication: 1 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'قياس متابعة', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } }
        ]
      }]
    }));
  }, sharedContext);

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_ORIGINAL_PROGRESS && window.PA_ORIGINAL_PROGRESS_PLANS))).toBe(true);
  await page.locator('[data-view="cases"]').click();
  await page.locator('[data-open-case="CASE-GOAL-001"]').click();

  const panel = page.locator('[data-original-progress="CASE-GOAL-001"]');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('ليست هذه الخطة مسحًا أو فرزًا');
  const form = panel.locator('[data-progress-plan-form]');
  await form.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية الوظيفية أثناء الروتين اليومي.');
  await form.locator('[name="familyPriority"]').fill('تريد الأسرة زيادة طلب الاحتياجات اليومية دون مساعدة مباشرة.');
  await form.locator('[name="providerObservation"]').fill('يبدأ التواصل عندما تستخدم صور الاختيار ويحتاج تلميحًا لفظيًا أقل.');
  await form.locator('[name="measurementContext"]').fill('المنزل، الأم مجيبة، استبانة، دعم معتاد، مع استخدام لوحة التواصل نفسها.');
  await form.locator('[name="targetDirection"]').selectOption('decrease');
  await form.locator('[name="reviewDate"]').fill('2026-07-15');
  await form.locator('[name="reviewOwner"]').fill('أخصائي التواصل ومنسق الحالة');
  await form.locator('[name="decisionRule"]').fill('يراجع الفريق الملاحظة الوظيفية والسياق قبل الاستمرار أو تعديل الخطة.');
  await form.locator('[name="interpretationLimit"]').fill('لا تثبت السلسلة تشخيصًا ولا تسمح بالمقارنة إذا تغير المجيب أو مستوى الدعم.');
  await form.locator('button[type="submit"]').click();

  await expect(panel).toContainText('جاهز للمراجعة المهنية');
  await expect(panel).toContainText('أولوية الأسرة أو الشخص');
  await expect(panel).toContainText('ملاحظة مقدم الخدمة');
  await expect(panel).toContainText('لا تعلن المنصة تحقق الهدف أو التحسن السريري آليًا');
  await panel.locator('[data-edit-progress-plan]').click();
  const editForm = panel.locator('[data-progress-plan-form]');
  await editForm.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية في المنزل والمدرسة مع توثيق السياق.');
  await editForm.locator('[name="editReason"]').fill('توسيع الهدف بعد مراجعة الفريق.');
  await editForm.locator('button[type="submit"]').click();
  await expect(panel).toContainText('أحداث السجل: 2');

  const store = await page.evaluate(() => JSON.parse(localStorage.getItem('pa-demo-store-v3:UID-GOAL-PLAN-TEST')));
  const plans = store.cases[0].originalProgressPlans;
  expect(plans).toHaveLength(1);
  expect(plans[0].schema).toBe('pa-original-progress-plan-v3');
  expect(plans[0].assessmentPurpose).toBe('progress_monitoring');
  expect(plans[0].familyPriority).toContain('الأسرة');
  expect(plans[0].providerObservation).toContain('التواصل');
  expect(plans[0].measurementContext).toContain('المنزل');
  expect(plans[0].reviewOwner).toContain('أخصائي');
  expect(plans[0].interpretationLimit).toContain('تشخيص');
  expect(plans[0].createdByUid).toBe('UID-GOAL-PLAN-TEST');
  expect(plans[0].auditTrail).toHaveLength(2);
  expect(plans[0].auditTrail[1].event).toBe('plan_revised');
  expect(plans[0].auditTrail[1].reason).toBe('توسيع الهدف بعد مراجعة الفريق.');

  const downloadPromise = page.waitForEvent('download');
  await panel.locator('[data-export-progress-plans]').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('CASE-GOAL-001-original-progress-plans.json');
  const fs = require('fs');
  const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  expect(exported.schema).toBe('pa-original-progress-plan-export-v3');
  expect(exported.ownerUid).toBe('UID-GOAL-PLAN-TEST');
  expect(exported.assessmentPurpose).toBe('progress_monitoring');
  expect(exported.purposeBoundary).toContain('not-screening-not-diagnostic');
  expect(exported.backupLocation).toBe('embedded-in-case-record');
  expect(exported.interpretationBoundary).toBe('human-review-required-not-diagnostic-not-norm-referenced');
  expect(exported.plans[0].auditTrail).toHaveLength(2);
});