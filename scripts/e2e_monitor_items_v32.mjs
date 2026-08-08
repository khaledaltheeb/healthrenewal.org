import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const site = process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(site, 'api');
fs.mkdirSync(outDir, { recursive: true });

const definitionPattern = /<script type="application\/json" id="lab-definition">(.*?)<\/script>/s;
const genericSuffixes = [
  'كان هذا الجانب صعبًا أو أثر في يومي',
  'احتجت إلى دعم إضافي في هذا الجانب',
  'أريد متابعة تغير هذا الجانب',
];

function readDefinition(file) {
  const source = fs.readFileSync(file, 'utf8');
  const match = source.match(definitionPattern);
  if (!match) throw new Error(`missing lab-definition: ${file}`);
  return JSON.parse(match[1].replaceAll('<\\/', '</'));
}

const assessmentRoot = path.join(site, 'assessment-lab');
const definitions = [];
for (const entry of fs.readdirSync(assessmentRoot, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const file = path.join(assessmentRoot, entry.name, 'index.html');
  if (!fs.existsSync(file)) continue;
  const definition = readDefinition(file);
  if (definition.score_type === 'monitor') definitions.push(definition);
}
definitions.sort((a, b) => a.slug.localeCompare(b.slug, 'ar'));

const staticErrors = [];
const allQuestions = [];
const policyCounts = { burden_tracking: 0, readiness_gaps: 0, safety_flags: 0 };
if (definitions.length !== 36) staticErrors.push(`monitor count=${definitions.length}`);
for (const definition of definitions) {
  const questions = Array.isArray(definition.questions) ? definition.questions : [];
  const options = Array.isArray(definition.options) ? definition.options : [];
  if (questions.length !== 12) staticErrors.push(`${definition.slug}: questions=${questions.length}`);
  if (options.length !== 5 || new Set(options).size !== 5) staticErrors.push(`${definition.slug}: invalid options`);
  if (definition.item_bank_version !== 32) staticErrors.push(`${definition.slug}: item_bank_version=${definition.item_bank_version}`);
  if (definition.scoring_policy !== 'descriptive_tracking_only') staticErrors.push(`${definition.slug}: scoring_policy`);
  if (!(definition.monitor_policy in policyCounts)) staticErrors.push(`${definition.slug}: monitor_policy=${definition.monitor_policy}`);
  else policyCounts[definition.monitor_policy] += 1;
  if (!String(definition.monitor_direction || '').includes('لا تعني تشخيصًا')) staticErrors.push(`${definition.slug}: direction`);
  for (const [index, question] of questions.entries()) {
    if (typeof question !== 'string' || question.length < 35 || !question.includes(':')) staticErrors.push(`${definition.slug}: weak item ${index}`);
    if (genericSuffixes.some(suffix => question.includes(suffix))) staticErrors.push(`${definition.slug}: generic item ${index}`);
    allQuestions.push(question);
  }
}
if (allQuestions.length !== 432) staticErrors.push(`items=${allQuestions.length}`);
if (new Set(allQuestions).size !== 432) staticErrors.push(`unique items=${new Set(allQuestions).size}`);
if (JSON.stringify(policyCounts) !== JSON.stringify({ burden_tracking: 34, readiness_gaps: 1, safety_flags: 1 })) {
  staticErrors.push(`policies=${JSON.stringify(policyCounts)}`);
}

const profiles = [
  { name: 'mobile-touch', context: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ar-JO', reducedMotion: 'reduce' }, touch: true },
  { name: 'desktop-keyboard', context: { viewport: { width: 1440, height: 900 }, locale: 'ar-JO', reducedMotion: 'reduce' }, touch: false },
];

const cases = [
  {
    slug: 'attention-daily',
    answers: Object.fromEntries(Array.from({ length: 12 }, (_, index) => [index, 4])),
    includes: ['مؤشر متابعة وصفي داخل هذه الأداة', '100%', 'لا توجد نقاط قطع'],
    excludes: ['إشارات تحتاج مراجعة مستقلة الآن'],
    alert: false,
  },
  {
    slug: 'relationship-safety',
    answers: { ...Object.fromEntries(Array.from({ length: 12 }, (_, index) => [index, 0])), 3: 1 },
    includes: ['مراجعة إشارات الأمان في العلاقة', '1 إشارات', 'لا تنتج هذه الأداة مجموع أمان', 'إشارات تحتاج مراجعة مستقلة الآن', 'واصل لمسًا أو تواصلًا أو سؤالًا'],
    excludes: ['مؤشر متابعة وصفي داخل هذه الأداة'],
    alert: true,
  },
  {
    slug: 'recovery-safety',
    answers: Object.fromEntries(Array.from({ length: 12 }, (_, index) => [index, 4])),
    includes: ['فجوات خطة الأمان والتعافي', '48 / 48', 'النسبة الوصفية 100%', 'لا تقيس شدة الاعتماد أو خطر الانسحاب', 'إشارات تحتاج مراجعة مستقلة الآن'],
    excludes: ['شدة الأعراض'],
    alert: true,
  },
  {
    slug: 'postpartum-support',
    answers: { ...Object.fromEntries(Array.from({ length: 12 }, (_, index) => [index, 0])), 2: 1 },
    includes: ['مؤشر متابعة وصفي داخل هذه الأداة', 'إشارات تحتاج مراجعة مستقلة الآن', 'أفكار مخيفة عن إيذاء نفسي أو الطفل'],
    excludes: ['تم تشخيصك'],
    alert: true,
  },
  {
    slug: 'sleep-quality',
    answers: { ...Object.fromEntries(Array.from({ length: 12 }, (_, index) => [index, 0])), 9: 1 },
    includes: ['إشارات تحتاج مراجعة مستقلة الآن', 'غلبني النعاس أثناء القيادة'],
    excludes: ['تم تشخيصك'],
    alert: true,
  },
];

const runs = [];
const errors = [...staticErrors];
const browser = await chromium.launch({ headless: true, args: ['--mute-audio'] });
try {
  for (const profile of profiles) {
    const context = await browser.newContext(profile.context);
    try {
      for (const testCase of cases) {
        const page = await context.newPage();
        const runtimeErrors = [];
        page.on('pageerror', error => runtimeErrors.push(`pageerror:${error}`));
        page.on('console', message => {
          if (message.type() === 'error') runtimeErrors.push(`console:${message.text()}`);
        });
        const route = `assessment-lab/${testCase.slug}/`;
        const started = Date.now();
        try {
          const response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
          if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
          await page.waitForSelector('[data-v12-lab="assessment"]', { timeout: 10000 });
          const definition = await page.locator('#lab-definition').evaluate(node => JSON.parse(node.textContent));
          await page.evaluate(({ key, state }) => localStorage.setItem(key, JSON.stringify(state)), {
            key: `pterminology:v12:${testCase.slug}`,
            state: { stage: 0, answers: testCase.answers },
          });
          await page.reload({ waitUntil: 'domcontentloaded' });
          await page.waitForSelector('button.interim', { timeout: 10000 });
          const interim = page.locator('button.interim');
          if (profile.touch) await interim.tap();
          else { await interim.focus(); await interim.press('Enter'); }
          const resultCard = page.locator('.result-card');
          await resultCard.waitFor({ state: 'visible', timeout: 5000 });
          const text = await resultCard.innerText();
          for (const marker of testCase.includes) if (!text.includes(marker)) throw new Error(`missing ${marker}: ${text}`);
          for (const marker of testCase.excludes) if (text.includes(marker)) throw new Error(`forbidden ${marker}: ${text}`);
          const alerts = await resultCard.locator('[role="alert"]').count();
          if (testCase.alert && alerts < 1) throw new Error('expected safety alert');
          if (!testCase.alert && alerts !== 0) throw new Error(`unexpected safety alert count=${alerts}`);
          if (definition.questions.length !== 12 || definition.item_bank_version !== 32) throw new Error('definition contract changed');
          if (runtimeErrors.length) throw new Error(runtimeErrors.join(' | '));
          runs.push({ profile: profile.name, slug: testCase.slug, status: 'passed', durationMs: Date.now() - started });
        } catch (error) {
          const message = `${profile.name}:${route} ${error}`;
          errors.push(message);
          runs.push({ profile: profile.name, slug: testCase.slug, status: 'failed', error: String(error), durationMs: Date.now() - started });
        } finally {
          await page.close();
        }
      }
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}

const report = {
  version: 32,
  status: errors.length ? 'failed' : 'passed',
  monitorDefinitions: definitions.length,
  totalItems: allQuestions.length,
  uniqueItems: new Set(allQuestions).size,
  genericItems: allQuestions.filter(item => genericSuffixes.some(suffix => item.includes(suffix))).length,
  policyCounts,
  profiles: profiles.map(profile => profile.name),
  interactiveCases: cases.length,
  expectedRuns: profiles.length * cases.length,
  completedRuns: runs.length,
  passedRuns: runs.filter(run => run.status === 'passed').length,
  failedRuns: runs.filter(run => run.status === 'failed').length,
  errors,
  runs,
};
fs.writeFileSync(path.join(outDir, 'monitor-items-e2e-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
