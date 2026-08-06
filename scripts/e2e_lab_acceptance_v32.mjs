import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const site = process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(site, 'api');
fs.mkdirSync(outDir, { recursive: true });
const slugs = root => fs.readdirSync(path.join(site, root), { withFileTypes: true }).filter(item => item.isDirectory()).map(item => item.name).sort();
const assessments = slugs('assessment-lab');
const cognitive = slugs('cognitive-lab');
const errors = [];
const rows = [];
const profiles = [
  { name: 'mobile-touch', context: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ar-JO', reducedMotion: 'reduce' }, touch: true },
  { name: 'desktop-keyboard', context: { viewport: { width: 1440, height: 900 }, locale: 'ar-JO', reducedMotion: 'reduce' }, touch: false },
];
const ignoredConsole = /AudioContext encountered an error|WebAudio renderer/i;

async function activate(locator, touch) {
  await locator.scrollIntoViewIfNeeded();
  if (touch) await locator.tap();
  else { await locator.focus(); await locator.press('Enter'); }
}

async function contextFor(browser, profile) {
  const context = await browser.newContext(profile.context);
  await context.addInitScript(() => {
    const native = window.setTimeout;
    window.setTimeout = (fn, ms, ...args) => native(fn, Math.min(Number(ms) || 0, 200), ...args);
  });
  return context;
}

async function common(page, route) {
  const runtime = [];
  page.on('pageerror', error => runtime.push(`pageerror:${error}`));
  page.on('console', message => {
    if (message.type() === 'error' && !ignoredConsole.test(message.text())) runtime.push(`console:${message.text()}`);
  });
  const response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('[data-v12-lab]', { timeout: 10000 });
  const layout = await page.evaluate(() => ({
    h1: document.querySelectorAll('h1').length,
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    resultLive: document.querySelector('.result-card')?.getAttribute('aria-live') || '',
    buttons: [...document.querySelectorAll('.lab-engine button')].map(node => {
      const rect = node.getBoundingClientRect(); return { width: rect.width, height: rect.height, text: node.textContent.trim() };
    }),
  }));
  if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
  if (layout.h1 !== 1 || layout.lang !== 'ar' || layout.dir !== 'rtl') throw new Error(`document semantics ${JSON.stringify(layout)}`);
  if (layout.scrollWidth > layout.clientWidth + 4) throw new Error(`horizontal overflow ${layout.scrollWidth}/${layout.clientWidth}`);
  if (layout.resultLive !== 'polite') throw new Error(`result aria-live=${layout.resultLive}`);
  const small = layout.buttons.filter(button => button.width < 44 || button.height < 44);
  if (small.length) throw new Error(`targets below 44px ${JSON.stringify(small.slice(0, 5))}`);
  return runtime;
}

async function runAssessment(browser, slug, profile) {
  const context = await contextFor(browser, profile);
  const page = await context.newPage();
  const route = `assessment-lab/${slug}/`;
  const started = Date.now();
  try {
    const runtime = await common(page, route);
    const definition = await page.locator('#lab-definition').evaluate(node => JSON.parse(node.textContent));
    const total = definition.questions.length;
    await page.evaluate(key => localStorage.removeItem(key), `pterminology:v12:${slug}`);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-v12-lab]');

    await activate(page.locator('button.next'), profile.touch);
    const error = page.locator('.lab-inline-error:not([hidden])');
    await error.waitFor({ state: 'visible', timeout: 3000 });
    const focus = await page.evaluate(() => document.activeElement?.getAttribute('name') || '');
    if (focus !== 'q0') throw new Error(`first missing focus=${focus}`);

    const firstStage = page.locator('fieldset.question');
    const firstCount = await firstStage.count();
    for (let i = 0; i < firstCount; i += 1) await firstStage.nth(i).locator('input[type=radio]').first().check();
    await activate(page.locator('button.next'), profile.touch);
    const stage2 = await page.locator('.stage-meta strong').innerText();
    if (!stage2.includes('المرحلة 2')) throw new Error(`next failed ${stage2}`);
    await activate(page.locator('button.prev'), profile.touch);
    const stage1 = await page.locator('.stage-meta strong').innerText();
    if (!stage1.includes('المرحلة 1')) throw new Error(`previous failed ${stage1}`);

    const maxAnswers = {};
    for (let index = 0; index < total; index += 1) {
      const item = definition.questions[index];
      const options = (typeof item === 'object' && item.options) || definition.options || [];
      maxAnswers[index] = Math.max(0, options.length - 1);
    }
    if (slug === 'phq-9-plus') maxAnswers[8] = Math.max(1, maxAnswers[8]);
    await page.evaluate(({ key, state }) => localStorage.setItem(key, JSON.stringify(state)), {
      key: `pterminology:v12:${slug}`,
      state: { stage: 0, answers: maxAnswers },
    });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-v12-lab]');
    await activate(page.locator('button.interim'), profile.touch);
    const result = await page.locator('.result-card').innerText();
    if (!result.includes(`${total} من ${total}`)) throw new Error(`max completion absent: ${result.slice(0, 180)}`);
    if (/تشخيص مؤكد|تم تشخيصك|لديك اضطراب/.test(result)) throw new Error('diagnostic claim');
    if (definition.score_type === 'phq9' && (!result.includes('27 / 27') || !result.includes('20–27') || !result.includes('تنبيه سلامة مستقل'))) throw new Error(`PHQ-9 scoring/safety invalid: ${result}`);
    if (definition.score_type === 'gad7' && (!result.includes('21 / 21') || !result.includes('15–21'))) throw new Error(`GAD-7 scoring invalid: ${result}`);
    if (definition.score_type === 'who5' && (!result.includes('100 / 100') || !result.includes('الدرجة الخام 25 من 25'))) throw new Error(`WHO-5 scoring invalid: ${result}`);
    if (definition.score_type === 'audit_guided' && (result.includes('%') || /أعراض خفيفة|أعراض متوسطة|أعراض شديدة/.test(result) || !result.includes('لم تُحسب درجة AUDIT رسمية'))) throw new Error(`AUDIT must be completion-only: ${result}`);
    if (definition.score_type === 'monitor' && (/أعراض خفيفة|أعراض متوسطة|أعراض شديدة|مرتفع جدًا/.test(result) || !result.includes('لا توجد نقاط قطع'))) throw new Error(`monitor has clinical bands: ${result}`);

    await page.evaluate(key => localStorage.setItem(key, '{corrupt'), `pterminology:v12:${slug}`);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-v12-lab]');
    const fresh = await page.locator('.stage-meta span').innerText();
    if (!fresh.includes(`0/${total}`)) throw new Error(`corrupt storage recovery failed: ${fresh}`);

    await page.locator('fieldset.question').first().locator('input[type=radio]').first().check();
    page.once('dialog', dialog => dialog.accept());
    await activate(page.locator('button.restart'), profile.touch);
    const restarted = await page.locator('.stage-meta span').innerText();
    if (!restarted.includes(`0/${total}`)) throw new Error(`restart failed: ${restarted}`);
    if (runtime.length) throw new Error(runtime.join(' | '));
    rows.push({ kind: 'assessment', slug, profile: profile.name, status: 'passed', questions: total, scoreType: definition.score_type, durationMs: Date.now() - started });
  } catch (error) {
    errors.push(`${profile.name}:${route} ${error}`);
    rows.push({ kind: 'assessment', slug, profile: profile.name, status: 'failed', error: String(error), durationMs: Date.now() - started });
  } finally {
    await context.close();
  }
}

async function runCognitive(browser, slug, profile) {
  const context = await contextFor(browser, profile);
  const page = await context.newPage();
  const route = `cognitive-lab/${slug}/`;
  const started = Date.now();
  try {
    const runtime = await common(page, route);
    const definition = await page.locator('#lab-definition').evaluate(node => JSON.parse(node.textContent));
    await page.evaluate(key => localStorage.removeItem(key), `pterminology:v12:${slug}`);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-v12-lab]');
    await activate(page.locator('button.start'), profile.touch);
    await page.waitForSelector('button.choice-button', { timeout: 6000 });
    const choices = page.locator('button.choice-button');
    const labels = (await choices.allTextContents()).map(value => value.trim());
    if (labels.length < 2 || new Set(labels).size !== labels.length) throw new Error(`invalid choices ${JSON.stringify(labels)}`);
    if (profile.touch) await choices.first().tap(); else { await choices.first().focus(); await choices.first().press('Enter'); }
    const feedbackNode = page.locator('.trial-feedback');
    await feedbackNode.waitFor({ state: 'visible', timeout: 3000 });
    const feedback = await feedbackNode.innerText();
    if (!feedback.trim()) throw new Error('missing feedback');
    const saved = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), `pterminology:v12:${slug}`);
    const last = saved?.trials?.at(-1);
    if (!last || !Number.isFinite(Number(last.time)) || Number(last.time) < 0 || typeof last.correct !== 'boolean') throw new Error(`invalid saved trial ${JSON.stringify(last)}`);
    await activate(page.locator('button.interim'), profile.touch);
    const result = await page.locator('.result-card').innerText();
    if (!result.includes('70% دقة و30% سرعة') || !result.includes('ليس درجة IQ') || !result.includes('أزمنة صالحة')) throw new Error(`metric disclosure missing: ${result}`);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-v12-lab]');
    const resume = await page.locator('.stage-meta span').innerText();
    if (!resume.includes('1 محاولة')) throw new Error(`resume failed ${resume}`);
    page.once('dialog', dialog => dialog.accept());
    await activate(page.locator('button.restart'), profile.touch);
    const restarted = await page.locator('.stage-meta span').innerText();
    if (!restarted.includes('0 محاولة')) throw new Error(`restart failed ${restarted}`);
    if (runtime.length) throw new Error(runtime.join(' | '));
    rows.push({ kind: 'cognitive', slug, profile: profile.name, status: 'passed', stages: definition.stages, trialsPerStage: definition.trials_per_stage, durationMs: Date.now() - started });
  } catch (error) {
    errors.push(`${profile.name}:${route} ${error}`);
    rows.push({ kind: 'cognitive', slug, profile: profile.name, status: 'failed', error: String(error), durationMs: Date.now() - started });
  } finally {
    await context.close();
  }
}

const browser = await chromium.launch({ headless: true, args: ['--mute-audio', '--autoplay-policy=no-user-gesture-required'] });
try {
  for (const profile of profiles) {
    for (const slug of assessments) await runAssessment(browser, slug, profile);
    for (const slug of cognitive) await runCognitive(browser, slug, profile);
  }
} finally {
  await browser.close();
}

const report = {
  version: 32,
  status: errors.length ? 'failed' : 'passed',
  assessmentDefinitions: assessments.length,
  cognitiveDefinitions: cognitive.length,
  profiles: profiles.map(item => item.name),
  expectedRuns: (assessments.length + cognitive.length) * profiles.length,
  completedRuns: rows.length,
  passedRuns: rows.filter(row => row.status === 'passed').length,
  failedRuns: rows.filter(row => row.status === 'failed').length,
  errorCount: errors.length,
  errors,
  tools: rows,
};
fs.writeFileSync(path.join(outDir, 'lab-acceptance-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
