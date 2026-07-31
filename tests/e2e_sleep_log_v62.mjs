import assert from 'node:assert/strict';
import { mkdtemp, mkdir, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const OUT = path.join(ROOT, 'artifacts', 'sleep-log-browser-v62');
const SITE_PATH = '/daily-tools/sleep-wind-down-plan/';
const CHART_ACCESSIBLE_NAME = 'اتجاهات النوم والجودة والطاقة. الوصف النصي المتجدد يظهر قبل الرسم.';

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: 'inherit', ...options });
    child.on('error', reject);
    child.on('exit', (code) => code === 0 ? resolve() : reject(new Error(`${command} exited with ${code}`)));
  });
}

async function waitForServer(url, attempts = 40) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`preview server did not become ready: ${url}`);
}

async function auditViewport(browser, baseUrl, name, viewport) {
  const context = await browser.newContext({ viewport, locale: 'ar-JO', reducedMotion: 'reduce', acceptDownloads: true });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  const badResponses = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('requestfailed', (request) => failedRequests.push(`${request.method()} ${request.url()} :: ${request.failure()?.errorText || 'failed'}`));
  page.on('response', (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`);
  });

  await page.goto(`${baseUrl}${SITE_PATH}`, { waitUntil: 'networkidle' });
  await page.locator('h1').waitFor();
  assert.equal(await page.locator('h1').textContent(), 'سجل النوم المحلي');
  const exportButton = page.locator('[data-export-sleep-chart]');
  await exportButton.waitFor();
  const privacyNotice = page.locator('[data-export-sleep-chart-privacy]');
  await privacyNotice.waitFor();
  const privacyText = (await privacyNotice.textContent()) || '';
  assert.match(privacyText, /تواريخ النوم/);
  assert.match(privacyText, /مدته/);
  assert.match(privacyText, /درجات الجودة والطاقة/);
  assert.match(privacyText, /لا يتضمن الملاحظات النصية/);
  assert.match(privacyText, /راجع الملف قبل مشاركته/);
  assert.match(privacyText, /المشاركة اختيارية وخارج التخزين المحلي/);
  assert.equal(await exportButton.getAttribute('aria-describedby'), await privacyNotice.getAttribute('id'));

  const pageMetrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    direction: getComputedStyle(document.documentElement).direction,
    lang: document.documentElement.lang,
  }));
  assert.equal(pageMetrics.direction, 'rtl');
  assert.equal(pageMetrics.lang, 'ar');
  assert.ok(pageMetrics.scrollWidth <= pageMetrics.clientWidth + 1, `page overflow: ${JSON.stringify(pageMetrics)}`);

  const chartMetrics = await page.locator('.chart-wrap').evaluate((wrap) => {
    const svg = wrap.querySelector('svg');
    const wrapRect = wrap.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    return {
      wrapLeft: wrapRect.left,
      wrapRight: wrapRect.right,
      viewport: document.documentElement.clientWidth,
      overflowX: getComputedStyle(wrap).overflowX,
      svgWidth: svgRect.width,
      wrapClientWidth: wrap.clientWidth,
      wrapScrollWidth: wrap.scrollWidth,
      ariaLabel: svg.getAttribute('aria-label'),
      descriptionText: document.querySelector('[data-sleep-chart-text]')?.textContent?.trim() || '',
      nestedTitles: svg.querySelectorAll('title,desc').length,
    };
  });
  assert.ok(chartMetrics.wrapLeft >= -1 && chartMetrics.wrapRight <= chartMetrics.viewport + 1, `chart container escapes viewport: ${JSON.stringify(chartMetrics)}`);
  assert.ok(['auto', 'scroll'].includes(chartMetrics.overflowX), `chart overflow must be contained: ${chartMetrics.overflowX}`);
  assert.ok(chartMetrics.svgWidth > 0 && chartMetrics.wrapScrollWidth >= chartMetrics.wrapClientWidth);
  assert.equal(chartMetrics.ariaLabel, CHART_ACCESSIBLE_NAME, 'chart accessible name must remain stable');
  assert.match(chartMetrics.descriptionText, /لا توجد بيانات كافية/);
  assert.equal(chartMetrics.nestedTitles, 0, 'chart must not create a second document title in generic audits');

  const axe = await new AxeBuilder({ page }).analyze();
  const blockingViolations = axe.violations.filter((violation) => ['serious', 'critical'].includes(violation.impact));
  assert.deepEqual(blockingViolations, [], `axe blocking violations: ${JSON.stringify(blockingViolations, null, 2)}`);

  await page.keyboard.press('Tab');
  const keyboardTargets = [];
  for (let i = 0; i < 26; i += 1) {
    const target = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        name: el.getAttribute('name'),
        text: (el.textContent || '').trim().slice(0, 80),
        visible: rect.width > 0 && rect.height > 0,
      };
    });
    if (target) keyboardTargets.push(target);
    await page.keyboard.press('Tab');
  }
  assert.ok(keyboardTargets.some((item) => item.name === 'date' && item.visible), 'date field is not keyboard reachable');
  assert.ok(keyboardTargets.some((item) => item.tag === 'button' && item.text.includes('احسب') && item.visible), 'submit button is not keyboard reachable');
  assert.ok(keyboardTargets.some((item) => item.tag === 'button' && item.text.includes('حذف جميع') && item.visible), 'delete-all button is not keyboard reachable');
  assert.ok(keyboardTargets.some((item) => item.tag === 'button' && item.text.includes('تصدير المخطط') && item.visible), 'chart export button is not keyboard reachable');

  await page.locator('button[type="submit"]').click();
  assert.equal(await page.locator('[name="date"]').getAttribute('aria-invalid'), 'true');
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('name')), 'date');

  await page.locator('[name="date"]').fill('2026-07-22');
  await page.locator('[name="bedtime"]').fill('22:30');
  await page.locator('[name="wakeTime"]').fill('06:30');
  await page.locator('[name="quality"]').fill('7');
  await page.locator('[name="energy"]').fill('6');
  await page.locator('[name="note"]').fill('ملاحظة اختبار غير تعريفية');
  await page.locator('[name="localConsent"]').check();
  await page.locator('button[type="submit"]').click();
  await page.locator('[data-sleep-summary]').waitFor();
  assert.ok(!(await page.locator('[data-sleep-summary]').textContent()).includes('أدخل البيانات'));
  assert.equal(await page.locator('[data-sleep-results] tr').count(), 1);

  const populatedChart = await page.evaluate(() => {
    const svg = document.querySelector('[data-sleep-chart]');
    return {
      ariaLabel: svg?.getAttribute('aria-label') || '',
      descriptionText: document.querySelector('[data-sleep-chart-text]')?.textContent?.trim() || '',
      nestedTitles: svg?.querySelectorAll('title,desc').length || 0,
    };
  });
  assert.equal(populatedChart.ariaLabel, CHART_ACCESSIBLE_NAME, 'runtime updates must preserve the stable chart accessible name');
  assert.match(populatedChart.descriptionText, /يعرض المخطط 1 سجلًا/);
  assert.equal(populatedChart.nestedTitles, 0, 'runtime chart updates must not restore nested title elements');

  const downloadPromise = page.waitForEvent('download');
  await exportButton.click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), 'sleep-trends.svg');
  assert.match(await page.locator('form [role="status"]').textContent(), /راجع الملف قبل مشاركته/);

  await page.emulateMedia({ media: 'print' });
  const printState = await page.evaluate(() => ({
    navDisplay: getComputedStyle(document.querySelector('nav')).display,
    actionsDisplay: getComputedStyle(document.querySelector('.actions')).display,
    chartOverflow: getComputedStyle(document.querySelector('.chart-wrap')).overflow,
    svgMinWidth: getComputedStyle(document.querySelector('.chart-wrap svg')).minWidth,
  }));
  assert.equal(printState.navDisplay, 'none');
  assert.equal(printState.actionsDisplay, 'none');
  assert.equal(printState.svgMinWidth, '0px');
  await page.emulateMedia({ media: 'screen' });

  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
  assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join('\n')}`);
  assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join('\n')}`);
  assert.deepEqual(failedRequests, [], `failed requests: ${failedRequests.join('\n')}`);
  assert.deepEqual(badResponses, [], `bad responses: ${badResponses.join('\n')}`);

  await context.close();
  return {
    viewport,
    pageMetrics,
    chartMetrics,
    populatedChart,
    keyboardTargets: keyboardTargets.length,
    axeViolations: axe.violations.length,
    axeBlockingViolations: blockingViolations.length,
    consoleErrors: consoleErrors.length,
    pageErrors: pageErrors.length,
    failedRequests: failedRequests.length,
    badResponses: badResponses.length,
    chartDownload: download.suggestedFilename(),
    privacyNotice: true,
    printState,
  };
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const temp = await mkdtemp(path.join(tmpdir(), 'sleep-log-browser-v62-'));
  const site = path.join(temp, '_site');
  const preview = path.join(temp, 'preview');
  await mkdir(site, { recursive: true });
  await mkdir(preview, { recursive: true });
  await writeFile(path.join(site, 'sitemap.xml'), '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n', 'utf8');
  await writeFile(
    path.join(site, 'index.html'),
    '<!doctype html><html lang="ar" dir="rtl"><head><title>منصة اختبار</title><meta name="keywords" content="الصحة النفسية,ذوو الاحتياجات الخاصة,أدلة الدعم,أدوات التقييم"><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":"https://healthrenewal.org/#home","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة","url":"https://healthrenewal.org/","hasPart":[]}]}</script></head><body><nav><a href="provider-assessment-demo/">منصة التقييم</a></nav><article class="card"><h3>المهام المعرفية</h3><a href="cognitive-tests/">فتح المهام</a></article></body></html>',
    'utf8',
  );
  await run('python', [path.join(ROOT, 'scripts', 'publish_daily_tools_v24.py'), site]);
  await run('python', [path.join(ROOT, 'scripts', 'publish_sleep_log_v49.py'), site]);
  await run('python', [path.join(ROOT, 'scripts', 'patch_sleep_svg_export_v65.py'), site]);
  await run('python', [path.join(ROOT, 'scripts', 'apply_daily_tools_marshmallow_v219.py'), site]);
  await symlink(site, path.join(preview, 'pterminology-site'), 'dir');

  const server = spawn('python', ['-m', 'http.server', '8762', '--directory', preview], { stdio: ['ignore', 'pipe', 'pipe'] });
  try {
    const baseUrl = 'http://127.0.0.1:8762';
    await waitForServer(`${baseUrl}${SITE_PATH}`);
    const browser = await chromium.launch({ headless: true });
    try {
      const results = {
        generatedAt: new Date().toISOString(),
        path: SITE_PATH,
        mobile: await auditViewport(browser, baseUrl, 'mobile-390x844', { width: 390, height: 844 }),
        desktop: await auditViewport(browser, baseUrl, 'desktop-1440x1000', { width: 1440, height: 1000 }),
      };
      await writeFile(path.join(OUT, 'report.json'), `${JSON.stringify(results, null, 2)}\n`, 'utf8');
      console.log(JSON.stringify(results, null, 2));
    } finally {
      await browser.close();
    }
  } finally {
    server.kill('SIGTERM');
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
