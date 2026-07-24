const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:4173/provider-assessment-demo/';
const sharedContext = {
  respondent: 'parent',
  setting: 'home',
  administrationMode: 'questionnaire',
  supportLevel: 'usual',
  note: '',
  contractVersion: 'pa-original-session-context-v2'
};

test('original tools only expose longitudinal direction when administration context is comparable', async ({ page }) => {
  await page.addInitScript((context) => {
    const identity = { uid: 'UID-VIS-PROGRESS-TEST', username: 'visitor', role: 'visitor', createdAt: new Date().toISOString() };
    localStorage.setItem('pa-demo-identities-v3', JSON.stringify({ __visitor__: identity }));
    localStorage.setItem('pa-demo-active-v3', JSON.stringify({ username: 'visitor', role: 'visitor' }));
    localStorage.setItem(`pa-demo-store-v3:${identity.uid}`, JSON.stringify({
      uid: identity.uid,
      schemaVersion: '3',
      createdAt: '2026-07-01T08:00:00.000Z',
      cases: [{
        caseId: 'CASE-PROGRESS-001',
        alias: 'حالة متابعة وصفية',
        ageGroup: 'child',
        language: 'ar',
        informant: 'parent',
        question: 'متابعة تغير الإشارات الوصفية عبر الوقت',
        notes: '',
        status: 'active',
        createdAt: '2026-07-01T08:00:00.000Z',
        updatedAt: '2026-07-20T08:00:00.000Z',
        sessions: [
          {
            sessionId: 'SES-BASELINE-001', assessmentId: 'communication-pathway', completedAt: '2026-07-01T08:30:00.000Z',
            averageSignal: 1.5, domainSignals: { communication: 3, participation: 2 }, outcome: 'continue',
            outcomeLabel: 'جمع معلومات أو تقييم متخصص', summary: 'خط أساس وصفي', answers: {}, recommendation: { assessmentId: null, label: 'متابعة' },
            completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context }
          },
          {
            sessionId: 'SES-LATEST-002', assessmentId: 'communication-pathway', completedAt: '2026-07-20T08:30:00.000Z',
            averageSignal: 0.75, domainSignals: { communication: 1, participation: 1 }, outcome: 'continue',
            outcomeLabel: 'استكمال أداة استكشافية تالية', summary: 'متابعة وصفية ثانية', answers: {}, recommendation: { assessmentId: null, label: 'متابعة' },
            completedByUid: identity.uid, completedByRole: 'visitor', administrationContext: { ...context }
          }
        ]
      }]
    }));
  }, sharedContext);

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await expect.poll(() => page.evaluate(() => Boolean(window.PA_ORIGINAL_SESSION_CONTEXT && window.PA_ORIGINAL_PROGRESS))).toBe(true);
  await page.locator('[data-view="cases"]').click();
  await page.locator('[data-open-case="CASE-PROGRESS-001"]').click();

  let panel = page.locator('[data-original-progress="CASE-PROGRESS-001"]');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('قابل للمقارنة وصفياً');
  await expect(panel).toContainText('انخفاض وصفي -0.75');
  await expect(panel).toContainText('والد أو مقدم رعاية');
  await expect(panel).toContainText('المنزل');

  await page.locator('[data-close="case-detail-dialog"]').click();
  await page.evaluate(() => {
    const key = 'pa-demo-store-v3:UID-VIS-PROGRESS-TEST';
    const store = JSON.parse(localStorage.getItem(key));
    store.cases[0].sessions[1].administrationContext.respondent = 'teacher';
    localStorage.setItem(key, JSON.stringify(store));
  });
  await page.locator('[data-open-case="CASE-PROGRESS-001"]').click();
  panel = page.locator('[data-original-progress="CASE-PROGRESS-001"]');
  await expect(panel).toContainText('غير قابل للمقارنة مباشرة');
  await expect(panel).toContainText('اختلاف المجيب');
  await expect(panel).toContainText('لا يُفسر الاتجاه');
  await expect(panel).not.toContainText('انخفاض وصفي -0.75');

  const downloadPromise = page.waitForEvent('download');
  await panel.locator('[data-export-original-progress]').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('CASE-PROGRESS-001-original-tools-progress.json');
  const path = await download.path();
  const fs = require('fs');
  const payload = JSON.parse(fs.readFileSync(path, 'utf8'));
  expect(payload.schema).toBe('pa-original-tools-progress-v2');
  expect(payload.ownerUid).toBe('UID-VIS-PROGRESS-TEST');
  expect(payload.interpretationBoundary).toBe('descriptive-comparison-only-when-context-comparable-not-diagnostic-not-norm-referenced');
  expect(payload.comparabilityContract).toBe('same-respondent-setting-administration-mode-and-support');
  expect(payload.series[0].observedDifference).toBe(-0.75);
  expect(payload.series[0].descriptiveDelta).toBeNull();
  expect(payload.series[0].comparability.status).toBe('context_changed');
  expect(payload.series[0].baseline.administrationContext.respondent).toBe('parent');
  expect(payload.series[0].latest.administrationContext.respondent).toBe('teacher');
});
