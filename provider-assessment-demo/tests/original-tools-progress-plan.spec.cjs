const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:4173/provider-assessment-demo/';
const sharedContext = { respondent: 'parent', setting: 'home', administrationMode: 'questionnaire', supportLevel: 'usual', note: '', contractVersion: 'pa-original-session-context-v2' };

test('original tool progress plans require functional goals, human review and audited revisions', async ({ page }) => {
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
  const form = panel.locator('[data-progress-plan-form]');
  await form.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية الوظيفية أثناء الروتين اليومي.');
  await form.locator('[name="targetDirection"]').selectOption('decrease');
  await form.locator('[name="reviewDate"]').fill('2026-07-15');
  await form.locator('[name="decisionRule"]').fill('يراجع الفريق الملاحظة الوظيفية والسياق قبل الاستمرار أو تعديل الخطة.');
  await form.locator('button[type="submit"]').click();

  await expect(panel).toContainText('جاهز للمراجعة المهنية');
  await expect(panel).toContainText('لا تعلن المنصة تحقق الهدف آليًا');
  await panel.locator('[data-edit-progress-plan]').click();
  const editForm = panel.locator('[data-progress-plan-form]');
  await editForm.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية في المنزل والمدرسة مع توثيق السياق.');
  await editForm.locator('[name="editReason"]').fill('توسيع الهدف بعد مراجعة الفريق.');
  await editForm.locator('button[type="submit"]').click();
  await expect(panel).toContainText('أحداث السجل: 2');

  const book = await page.evaluate(() => JSON.parse(localStorage.getItem('pa-original-progress-plans-v3:UID-GOAL-PLAN-TEST')));
  expect(book.schema).toBe('pa-original-progress-plans-v3');
  expect(book.ownerUid).toBe('UID-GOAL-PLAN-TEST');
  expect(book.plans).toHaveLength(1);
  expect(book.plans[0].auditTrail).toHaveLength(2);
  expect(book.plans[0].auditTrail[1].event).toBe('plan_revised');
  expect(book.plans[0].auditTrail[1].reason).toBe('توسيع الهدف بعد مراجعة الفريق.');
  expect(book.plans[0].decisionRule).toContain('يراجع الفريق');
});