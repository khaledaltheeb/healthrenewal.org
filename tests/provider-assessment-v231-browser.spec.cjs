const { test, expect } = require('@playwright/test');
const fs = require('fs');

const BASE = 'http://127.0.0.1:4173/provider-assessment-demo/';
const context = { respondent: 'parent', setting: 'home', administrationMode: 'questionnaire', supportLevel: 'usual', note: '', contractVersion: 'pa-original-session-context-v2' };

function seedStore() {
  const identity = { uid: 'UID-V231-BROWSER', username: 'visitor', role: 'visitor', createdAt: '2026-07-25T08:00:00.000Z' };
  return {
    identity,
    store: {
      uid: identity.uid,
      schemaVersion: '3',
      createdAt: '2026-07-25T08:00:00.000Z',
      cases: [
        {
          caseId: 'CASE-V231-TARGET', alias: 'حالة توافق v231', ageGroup: 'child', language: 'ar', informant: 'parent',
          question: 'التحقق من توافق السجل وخطة المتابعة', notes: '', status: 'active', createdAt: '2026-07-25T08:00:00.000Z', updatedAt: '2026-07-25T08:00:00.000Z',
          professionalAssessments: [],
          sessions: [
            { sessionId: 'SES-V231-BASE', assessmentId: 'communication-pathway', completedAt: '2026-07-01T08:30:00.000Z', averageSignal: 1.5, domainSignals: { communication: 3 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'خط أساس', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } },
            { sessionId: 'SES-V231-LATEST', assessmentId: 'communication-pathway', completedAt: '2026-07-20T08:30:00.000Z', averageSignal: 0.75, domainSignals: { communication: 1 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'قياس متابعة', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } },
            { sessionId: 'SES-V231-CURRENT', assessmentId: 'attention-executive', completedAt: '2026-07-22T08:30:00.000Z', averageSignal: 1, domainSignals: { attention: 1 }, outcome: 'continue', outcomeLabel: 'متابعة', summary: 'جلسة حديثة', answers: {}, recommendation: {}, completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context } },
            { sessionId: 'SES-V231-PROTECTED', assessmentId: 'ADOS-2', completedAt: '2026-07-20T09:00:00.000Z', summary: 'مرجع تقرير خارجي فقط' }
          ]
        },
        {
          caseId: 'CASE-V231-EXISTING', alias: 'حالة سابقة', ageGroup: 'adult', language: 'ar', informant: 'self',
          question: 'سجل سابق يجب ألا يتغير', notes: '', status: 'active', createdAt: '2026-07-20T08:00:00.000Z', updatedAt: '2026-07-20T08:00:00.000Z', sessions: [],
          professionalAssessments: [{
            recordId: 'PRO-EXISTING-V231', toolId: 'existing-tool', toolName: 'سجل سابق', category: 'مرجع', recordStatus: 'completed',
            administrationDate: '2026-07-20', assignedEntityLabel: 'مختص سابق', performerName: '', administrationMode: 'record_review', versionLanguage: '',
            outcomeLabel: 'نتيجة سابقة', scoreReference: '', notes: '', nextAction: 'review', rightsConfirmed: true,
            recordedAt: '2026-07-20T09:00:00.000Z', recordedByUid: identity.uid, recordedByRole: 'visitor', activationVersion: '1.0.0',
            institutionalV220: { referralPurpose: 'بيانات سابقة ثابتة', release: 'previous-release' }, documentationQuality: { score: 80 }, auditTrail: [{ event: 'existing', at: '2026-07-20T09:00:00.000Z' }]
          }]
        }
      ]
    }
  };
}

async function boot(page) {
  const seeded = seedStore();
  await page.addInitScript(({ identity, store }) => {
    localStorage.setItem('pa-demo-identities-v3', JSON.stringify({ __visitor__: identity }));
    localStorage.setItem('pa-demo-active-v3', JSON.stringify({ username: 'visitor', role: 'visitor' }));
    localStorage.setItem(`pa-demo-store-v3:${identity.uid}`, JSON.stringify(store));
  }, seeded);
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.evaluate(async () => {
    if (typeof window.PA_LOAD_INSTITUTIONAL_V220 === 'function') await window.PA_LOAD_INSTITUTIONAL_V220();
  });
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_INSTITUTIONAL_COMPAT_V231 && window.PA_V231_SAVE_FALLBACK && window.PA_ORIGINAL_PROGRESS))).toBe(true);
}

test('professional record remains saveable as an explicit incomplete draft without contaminating prior records', async ({ page }) => {
  await boot(page);
  await page.locator('[data-view="professional-records"]').click();
  await expect(page.locator('#professional-record-new')).toBeVisible();
  await page.locator('#professional-record-new').click();
  const form = page.locator('#professional-record-form');
  await expect(form).toBeVisible();
  await expect(form.locator('[data-institutional-professional-v220] [required]')).toHaveCount(0);
  await expect(form.locator('#institutional-v231-draft-note')).toContainText('مسودة ناقصة');

  await form.locator('[name="caseId"]').selectOption('CASE-V231-TARGET');
  await form.locator('[name="recordStatus"]').selectOption('planned');
  await form.locator('[name="administrationDate"]').fill('2026-07-25');
  await form.locator('[name="assignedEntityLabel"]').fill('أخصائي نفسي مرخص');
  await form.locator('[name="administrationMode"]').selectOption('record_review');
  await form.locator('[name="outcomeLabel"]').fill('مسودة تخطيط أولية تحتاج استكمال العقد المؤسسي.');
  await form.locator('[name="nextAction"]').selectOption('collect_sources');
  await form.locator('[name="rightsConfirmed"]').check();
  await form.locator('button[type="submit"]').click();
  await page.waitForTimeout(250);

  const diagnostic = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('pa-demo-store-v3:UID-V231-BROWSER'));
    const target = state.cases.find((item) => item.caseId === 'CASE-V231-TARGET');
    return {
      records: target.professionalAssessments || [],
      attempt: window.PA_V231_SAVE_FALLBACK?.lastAttempt || null,
      dialogOpen: Boolean(document.getElementById('professional-record-dialog')?.open),
    };
  });
  expect(diagnostic.records, JSON.stringify(diagnostic)).toHaveLength(1);
  expect(['fallback_saved', 'original_save_succeeded']).toContain(diagnostic.attempt?.status);
  await expect(page.locator('#professional-record-dialog')).not.toHaveAttribute('open', '');
  await expect(page.locator('#professional-record-list')).toContainText('مسودة تخطيط أولية');

  const state = await page.evaluate(() => JSON.parse(localStorage.getItem('pa-demo-store-v3:UID-V231-BROWSER')));
  const target = state.cases.find((item) => item.caseId === 'CASE-V231-TARGET');
  const created = target.professionalAssessments[0];
  expect(created.institutionalV220.documentationState).toBe('progressive_draft_allowed');
  expect(created.documentationQuality.score).toBe(0);
  expect(created.documentationQuality.status).toBe('incomplete');
  expect(created.auditTrail.filter((item) => item.event === 'institutional_contract_attached')).toHaveLength(1);
  expect(created.auditTrail.at(-1).qualityScore).toBe(0);

  const existing = state.cases.find((item) => item.caseId === 'CASE-V231-EXISTING').professionalAssessments[0];
  expect(existing.institutionalV220).toEqual({ referralPurpose: 'بيانات سابقة ثابتة', release: 'previous-release' });
  expect(existing.documentationQuality).toEqual({ score: 80 });
  expect(existing.auditTrail).toEqual([{ event: 'existing', at: '2026-07-20T09:00:00.000Z' }]);
});

test('legacy and current original sessions coexist while protected tools stay excluded and legacy plans remain audited', async ({ page }) => {
  await boot(page);
  await page.locator('[data-view="cases"]').click();
  await page.locator('[data-open-case="CASE-V231-TARGET"]').click();

  const panel = page.locator('[data-original-progress="CASE-V231-TARGET"]');
  await expect(panel).toBeVisible();
  const form = panel.locator('[data-progress-plan-form]');
  await expect(form).toBeVisible();
  const optionValues = await form.locator('[name="assessmentId"] option').evaluateAll((nodes) => nodes.map((node) => node.value));
  expect(optionValues).toContain('communication-pathway');
  expect(optionValues).toContain('attention-executive');
  expect(optionValues).not.toContain('ADOS-2');

  await form.locator('[name="assessmentId"]').selectOption('communication-pathway');
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
  await panel.locator('[data-edit-progress-plan="CASE-V231-TARGET::communication-pathway"]').click();
  const editForm = panel.locator('[data-progress-plan-form]');
  await editForm.locator('[name="functionalGoal"]').fill('زيادة المبادرات التواصلية في المنزل والمدرسة مع توثيق السياق.');
  await editForm.locator('[name="editReason"]').fill('توسيع الهدف بعد مراجعة الفريق.');
  await editForm.locator('button[type="submit"]').click();
  await expect(panel).toContainText('أحداث السجل: 2');

  const state = await page.evaluate(() => JSON.parse(localStorage.getItem('pa-demo-store-v3:UID-V231-BROWSER')));
  const plan = state.cases.find((item) => item.caseId === 'CASE-V231-TARGET').originalProgressPlans.find((item) => item.assessmentId === 'communication-pathway');
  expect(plan.schema).toBe('pa-original-progress-plan-v3');
  expect(plan.licenseBoundary).toBe('original-license-safe-tools-only');
  expect(plan.auditTrail).toHaveLength(2);
  expect(plan.auditTrail[1].actorRole).toBe('visitor');
  expect(plan.auditTrail[1].reason).toBe('توسيع الهدف بعد مراجعة الفريق.');

  const downloadPromise = page.waitForEvent('download');
  await panel.locator('[data-export-progress-plans]').click();
  const download = await downloadPromise;
  const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  expect(exported.schema).toBe('pa-original-progress-plan-export-v3');
  expect(exported.licenseBoundary).toBe('original-license-safe-tools-only');
  expect(exported.interpretationBoundary).toBe('human-review-required-not-diagnostic-not-norm-referenced');
});