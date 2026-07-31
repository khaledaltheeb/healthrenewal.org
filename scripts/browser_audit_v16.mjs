import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const outDir = process.env.AUDIT_OUT_DIR || '_site/api';
fs.mkdirSync(outDir, { recursive: true });
const errors = [];
const warnings = [];
const pagesReport = [];

const routes = [
  '', 'tips/', 'tips/better-sleep/', 'assessment-lab/', 'assessment-lab/phq-9-plus/',
  'cognitive-lab/', 'cognitive-lab/simple-reaction/', 'encyclopedia/',
  'encyclopedia/concept-0001/', 'hubs/', 'sectors/family/', 'sectors/child/',
  'sectors/home/', 'sectors/women/', 'comparisons/', 'guided-assessment/', 'library/'
];

async function inspectPage(browser, route, viewport, label) {
  const context = await browser.newContext({ viewport, locale: 'ar-JO', colorScheme: 'light', reducedMotion: 'reduce' });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(String(err)));
  page.on('requestfailed', req => { if (req.url().startsWith(base)) failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`); });
  const started = Date.now();
  let response;
  try {
    response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(500);
  } catch (error) {
    errors.push(`${label}:${route} navigation failed: ${error}`);
  }
  const metrics = await page.evaluate(() => ({
    readyState: document.readyState,
    h1: document.querySelectorAll('h1').length,
    mainVisible: Boolean(document.querySelector('main')?.getBoundingClientRect().height),
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyText: document.body?.innerText?.trim().length || 0,
    title: document.title,
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
  })).catch(() => ({ readyState: 'error', h1: 0, mainVisible: false, scrollWidth: 0, clientWidth: 0, bodyText: 0, title: '', lang: '', dir: '' }));
  const status = response?.status() || 0;
  const durationMs = Date.now() - started;
  if (status !== 200) errors.push(`${label}:${route} HTTP ${status}`);
  if (metrics.h1 !== 1) errors.push(`${label}:${route} h1=${metrics.h1}`);
  if (!metrics.mainVisible) errors.push(`${label}:${route} main not visible`);
  if (metrics.scrollWidth > metrics.clientWidth + 4) errors.push(`${label}:${route} horizontal overflow ${metrics.scrollWidth}/${metrics.clientWidth}`);
  if (metrics.bodyText < 100) errors.push(`${label}:${route} body text too short ${metrics.bodyText}`);
  if (metrics.lang !== 'ar' || metrics.dir !== 'rtl') errors.push(`${label}:${route} language direction invalid`);
  if (durationMs > 5000) warnings.push(`${label}:${route} slow DOMContentLoaded ${durationMs}ms`);
  for (const item of consoleErrors) errors.push(`${label}:${route} console error: ${item}`);
  for (const item of pageErrors) errors.push(`${label}:${route} page error: ${item}`);
  for (const item of failedRequests) errors.push(`${label}:${route} failed request: ${item}`);
  pagesReport.push({ route, label, status, durationMs, ...metrics, consoleErrors, pageErrors, failedRequests });
  await context.close();
}

async function interactionTests(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'ar-JO', colorScheme: 'light' });
  const page = await context.newPage();
  page.on('pageerror', err => errors.push(`interaction page error: ${err}`));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(`interaction console error: ${msg.text()}`); });

  await page.goto(new URL('tips/', base).href, { waitUntil: 'domcontentloaded' });
  const totalTips = await page.locator('[data-search]').count();
  await page.locator('#tips-search').fill('نوم');
  await page.waitForTimeout(100);
  const visibleTips = await page.locator('[data-search]:visible').count();
  if (totalTips !== 20 || visibleTips < 1 || visibleTips >= totalTips) errors.push(`tips search failed total=${totalTips} visible=${visibleTips}`);

  await page.goto(new URL('assessment-lab/phq-9-plus/', base).href, { waitUntil: 'domcontentloaded' });
  const fieldsets = page.locator('fieldset.question');
  const firstStageCount = await fieldsets.count();
  if (firstStageCount < 1) errors.push('assessment first stage missing');
  for (let i = 0; i < firstStageCount; i += 1) await fieldsets.nth(i).locator('input[type=radio]').first().check();
  await page.locator('button.next').click();
  await page.waitForTimeout(100);
  const stageText = await page.locator('.stage-meta strong').innerText();
  if (!stageText.includes('المرحلة 2')) errors.push(`assessment next stage failed: ${stageText}`);
  await page.locator('button.interim').click();
  const assessmentResult = await page.locator('.result-card').innerText();
  if (!assessmentResult.includes('نتيجة') || assessmentResult.length < 80) errors.push('assessment interim result missing');

  await page.goto(new URL('cognitive-lab/simple-reaction/', base).href, { waitUntil: 'domcontentloaded' });
  await page.locator('button.start').click();
  const choices = page.locator('button.choice-button');
  if (await choices.count() !== 4) errors.push(`color choices count=${await choices.count()}`);
  await choices.first().click();
  await page.waitForTimeout(150);
  const feedback = await page.locator('.trial-feedback').innerText();
  if (!feedback.includes('الإجابة') && !feedback.includes('صحيح')) errors.push(`color click feedback missing: ${feedback}`);
  await page.locator('button.interim').click();
  const cognitiveResult = await page.locator('.result-card').innerText();
  if (!cognitiveResult.includes('الدقة') || !cognitiveResult.includes('المحاولات')) errors.push('cognitive result missing');

  await page.goto(new URL('encyclopedia/', base).href, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#ency-results a', { timeout: 10000 });
  const initialResults = await page.locator('#ency-results a').count();
  await page.locator('#ency-q').fill('القلق');
  await page.waitForTimeout(250);
  const filteredResults = await page.locator('#ency-results a').count();
  if (initialResults < 1 || filteredResults < 1) errors.push(`encyclopedia search results invalid ${initialResults}/${filteredResults}`);

  const manifestResponse = await page.request.get(new URL('manifest.webmanifest', base).href);
  if (!manifestResponse.ok()) errors.push(`manifest HTTP ${manifestResponse.status()}`);
  const swResponse = await page.request.get(new URL('sw.js', base).href);
  if (!swResponse.ok()) errors.push(`service worker HTTP ${swResponse.status()}`);
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  for (const route of routes) {
    await inspectPage(browser, route, { width: 390, height: 844 }, 'mobile');
    await inspectPage(browser, route, { width: 1440, height: 900 }, 'desktop');
  }
  await interactionTests(browser);
} finally {
  await browser.close();
}

const report = { version: 16, base, testedRoutes: routes.length, pageRuns: pagesReport.length, pages: pagesReport, warningCount: warnings.length, warnings, errorCount: errors.length, errors };
fs.writeFileSync(path.join(outDir, 'browser-audit-v16.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
