const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:4173/provider-assessment-demo/';
const sharedContext = { respondent: 'parent', setting: 'home', administrationMode: 'questionnaire', supportLevel: 'usual', note: '', contractVersion: 'pa-original-session-context-v2' };

test('original tool progress plans are rights-safe, functional and fully audited', async ({ page }) => {
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
          { sessionId: 'SES-GOAL-LATEST', assessmentId: 'communication-pathway', completedAt: '2026-07-20T08:30:00.000Z', averageSignal: 0.75, domainSignals: { communication: 1 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'قياس متابعة', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } },
          { sessionId: 'SES-PROTECTED-REF', assessmentId: 'ADOS-2', completedAt: '2026-07-20T09:00:00.000Z', summary: 'مرجع تقرير خارجي فقط' }
        ]
      }]
    }));
  }, sharedContext);

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_ORIGINAL_PROGRESS && window.PA_ORIGINAL_PROGRESS_PLANS))).toBe(true);
  await page.locator('[data-view="cases"]').click();
  await page.locator('[data-open-case="CASE-GOAL-001"]').click();

  const panel = page.locator('[data-original-progress="CASE-GOAL-001"]');
  const form = panel.locator('[data-progress-plan-form]');
  await expect(form.locator('[name="assessmentId"] option')).toHaveCount(1);
  await expect(form.locator('[name="assessmentId"]')).not.toContainText('ADOS-2');
  await form.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية الوظيفية أثناء الروتين اليومي.');
  await form.locator('[name="familyPriority"]').fill('تريد الأسرة زيادة طلب الاحتياجات اليومية دون مساعدة مباشرة.');
  await form.locator('[name="providerObservation"]').fill('يبدأ التواصل عند استخدام صور الاختيار ويحتاج تلميحًا أقل.');
  await form.locator('[name="measurementContext"]').fill('المنزل، الأم مجيبة، استبانة، دعم معتاد، ولوحة التواصل نفسها.');
  await form.locator('[name="targetDirection"]').selectOption('decrease');
  await form.locator('[name="reviewDate"]').fill('2026-07-15');
  await form.locator('[name="reviewOwner"]').fill('أخصائي التواصل ومنسق الحالة');
  await form.locator('[name="decisionRule"]').fill('يراجع الفريق الوظيفة والسياق قبل الاستمرار أو تعديل الخطة.');
  await form.locator('[name="interpretationLimit"]').fill('لا تثبت السلسلة تشخيصًا ولا تسمح بالمقارنة إذا تغير المجيب أو الدعم.');
  await form.locator('button[type="submit"]').click();

  await expect(panel).toContainText('جاهز للمراجعة المهنية');
  await panel.locator('[data-edit-progress-plan]').click();
  const editForm = panel.locator('[data-progress-plan-form]');
  await editForm.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية في المنزل والمدرسة مع توثيق السياق.');
  await editForm.locator('[name="editReason"]').fill('توسيع الهدف بعد مراجعة الفريق.');
  await editForm.locator('button[type="submit"]').click();
  await expect(panel).toContainText('أحداث السجل: 2');

  const store = await page.evaluate(() => JSON.parse(localStorage.getItem('pa-demo-store-v3:UID-GOAL-PLAN-TEST')));
  const plan = store.cases[0].originalProgressPlans[0];
  expect(plan.licenseBoundary).toBe('original-license-safe-tools-only');
  expect(plan.auditTrail).toHaveLength(2);
  expect(plan.auditTrail[1].actorRole).toBe('visitor');
  expect(plan.auditTrail[1].reason).toBe('توسيع الهدف بعد مراجعة الفريق.');

  const downloadPromise = page.waitForEvent('download');
  await panel.locator('[data-export-progress-plans]').click();
  const download = await downloadPromise;
  const fs = require('fs');
  const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  expect(exported.schema).toBe('pa-original-progress-plan-export-v3');
  expect(exported.licenseBoundary).toBe('original-license-safe-tools-only');
  expect(exported.interpretationBoundary).toBe('human-review-required-not-diagnostic-not-norm-referenced');
});
