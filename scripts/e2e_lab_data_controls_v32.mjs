import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const site = process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(site, 'api');
fs.mkdirSync(outDir, { recursive: true });
const errors = [];
const rows = [];
const dirs = root => fs.readdirSync(path.join(site, root), { withFileTypes: true })
  .filter(entry => entry.isDirectory()).map(entry => entry.name).sort();
const assessments = dirs('assessment-lab');
const cognitive = dirs('cognitive-lab');

async function verifyPresence(page, root, slug) {
  const route = `${root}/${slug}/`;
  const response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
  if (!response?.ok()) throw new Error(`${route}: HTTP ${response?.status()}`);
  await page.waitForSelector('.lab-data-controls-v32', { timeout: 10000 });
  const state = await page.evaluate(() => {
    const section = document.querySelector('.lab-data-controls-v32');
    const host = document.querySelector('[data-v12-lab]');
    const buttons = [...section.querySelectorAll('button')].map(node => {
      const rect = node.getBoundingClientRect();
      return { text: node.textContent.trim(), width: rect.width, height: rect.height };
    });
    return {
      count: document.querySelectorAll('.lab-data-controls-v32').length,
      outsideEngineHost: !!host && !host.contains(section),
      export: !!section.querySelector('[data-lab-export]'),
      print: !!section.querySelector('[data-lab-print]'),
      remove: !!section.querySelector('[data-lab-delete]'),
      live: section.querySelector('[role=status]')?.getAttribute('aria-live') || '',
      buttons,
    };
  });
  if (state.count !== 1 || !state.outsideEngineHost || !state.export || !state.print || !state.remove || state.live !== 'polite') {
    throw new Error(`${route}: invalid controls ${JSON.stringify(state)}`);
  }
  if (state.buttons.some(button => button.width < 44 || button.height < 44)) {
    throw new Error(`${route}: target below 44px ${JSON.stringify(state.buttons)}`);
  }
  rows.push({ route, status: 'present' });
}

async function verifyFunction(browser, root, slug, state) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, acceptDownloads: true, locale: 'ar-JO' });
  const page = await context.newPage();
  const requests = [];
  let trackControlRequests = false;
  page.on('request', request => {
    if (trackControlRequests && (request.resourceType() === 'fetch' || request.resourceType() === 'xhr')) requests.push(request.url());
  });
  const route = `${root}/${slug}/`;
  await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.lab-data-controls-v32');
  await page.evaluate(({ slug, state }) => localStorage.setItem(`pterminology:v12:${slug}`, JSON.stringify(state)), { slug, state });
  trackControlRequests = true;

  const downloadPromise = page.waitForEvent('download');
  await page.locator('[data-lab-export]').click();
  const download = await downloadPromise;
  const suggested = download.suggestedFilename();
  const saved = await download.path();
  if (!saved || suggested !== `${slug}-local-session.json`) throw new Error(`${route}: export filename/path invalid`);
  const payload = JSON.parse(fs.readFileSync(saved, 'utf8'));
  if (payload.slug !== slug || payload.storage !== 'local-only' || payload.schema_version !== 32) throw new Error(`${route}: export contract invalid`);
  if (JSON.stringify(payload.state) !== JSON.stringify(state)) throw new Error(`${route}: exported state differs`);

  await page.evaluate(() => { window.__printCalled = 0; window.print = () => { window.__printCalled += 1; }; });
  await page.locator('[data-lab-print]').click();
  if (await page.evaluate(() => window.__printCalled) !== 1) throw new Error(`${route}: print not invoked`);

  page.once('dialog', dialog => dialog.accept());
  await page.locator('[data-lab-delete]').click();
  await page.waitForTimeout(30);
  const immediate = await page.evaluate(slug => localStorage.getItem(`pterminology:v12:${slug}`), slug);
  if (immediate !== null) throw new Error(`${route}: local state not synchronously deleted`);
  if (requests.length) throw new Error(`${route}: control actions emitted network requests ${JSON.stringify(requests)}`);
  trackControlRequests = false;

  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('.lab-data-controls-v32');
  const after = await page.evaluate(slug => localStorage.getItem(`pterminology:v12:${slug}`), slug);
  if (after !== null) throw new Error(`${route}: local state returned after reload`);
  rows.push({ route, status: 'functional', exported: suggested, deleted: true, printed: true, networkRequests: 0 });
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'ar-JO' });
  const page = await context.newPage();
  for (const slug of assessments) {
    try { await verifyPresence(page, 'assessment-lab', slug); }
    catch (error) { errors.push(String(error)); }
  }
  for (const slug of cognitive) {
    try { await verifyPresence(page, 'cognitive-lab', slug); }
    catch (error) { errors.push(String(error)); }
  }
  await context.close();
  try { await verifyFunction(browser, 'assessment-lab', 'phq-9-plus', { stage: 1, answers: { 0: 1, 1: 2 } }); }
  catch (error) { errors.push(String(error)); }
  try { await verifyFunction(browser, 'cognitive-lab', 'simple-reaction', { stage: 1, trial: 2, trials: [{ correct: true, time: 420 }], seen: [] }); }
  catch (error) { errors.push(String(error)); }
} finally {
  await browser.close();
}

const report = {
  version: 32,
  status: errors.length ? 'failed' : 'passed',
  assessmentPages: assessments.length,
  cognitivePages: cognitive.length,
  expectedPresenceChecks: assessments.length + cognitive.length,
  presenceChecks: rows.filter(row => row.status === 'present').length,
  functionalChecks: rows.filter(row => row.status === 'functional').length,
  errors,
  rows,
};
fs.writeFileSync(path.join(outDir, 'lab-data-controls-e2e-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
