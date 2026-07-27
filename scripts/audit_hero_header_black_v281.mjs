import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const siteDir = path.resolve(process.argv[2] || '_site');
const baseUrl = (process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/pterminology-site/').replace(/\/?$/, '/');
const outDir = path.resolve(process.env.AUDIT_OUT_DIR || path.join(siteDir, 'api'));
const concurrency = Math.max(1, Number(process.env.HERO_AUDIT_CONCURRENCY || 6));

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

function toUrl(file) {
  let rel = path.relative(siteDir, file).split(path.sep).join('/');
  if (rel === 'index.html') rel = '';
  else if (rel.endsWith('/index.html')) rel = rel.slice(0, -10);
  return new URL(rel, baseUrl).href;
}

const htmlFiles = walk(siteDir).filter((file) => file.endsWith('.html')).sort();
const browser = await chromium.launch({ headless: true });
const results = [];
let cursor = 0;

async function worker() {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    colorScheme: 'light',
    reducedMotion: 'reduce',
    locale: 'ar',
  });
  const page = await context.newPage();
  while (true) {
    const index = cursor++;
    if (index >= htmlFiles.length) break;
    const file = htmlFiles[index];
    const rel = path.relative(siteDir, file).split(path.sep).join('/');
    const url = toUrl(file);
    const record = { path: rel, url, status: null, textElements: 0, violations: [], hidden: [] };
    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      record.status = response?.status() ?? null;
      await page.emulateMedia({ media: 'screen', reducedMotion: 'reduce', colorScheme: 'light' });
      const audit = await page.evaluate(() => {
        const containers = [...document.querySelectorAll('header, [role="banner"], .hero, [class*="hero"], [id*="hero"]')];
        const nodes = [...new Set(containers.flatMap((container) => [container, ...container.querySelectorAll('*')]))]
          .filter((el) => (el.textContent || '').trim().length > 0)
          .filter((el) => {
            const tag = el.tagName.toLowerCase();
            return !['script', 'style', 'noscript', 'svg', 'path'].includes(tag);
          });
        const violations = [];
        const hidden = [];
        for (const el of nodes) {
          const style = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          const selector = `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${el.classList.length ? `.${[...el.classList].slice(0, 3).join('.')}` : ''}`;
          const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
          if (style.color !== 'rgb(0, 0, 0)') {
            violations.push({ selector, text, color: style.color, backgroundColor: style.backgroundColor });
          }
          const clipped = el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;
          const invisible = style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0 || rect.width === 0 || rect.height === 0;
          if (invisible || clipped) {
            hidden.push({ selector, text, invisible, clipped, overflow: style.overflow, width: rect.width, height: rect.height });
          }
        }
        return { count: nodes.length, violations, hidden };
      });
      record.textElements = audit.count;
      record.violations = audit.violations;
      record.hidden = audit.hidden;
    } catch (error) {
      record.error = String(error);
    }
    results[index] = record;
  }
  await context.close();
}

await Promise.all(Array.from({ length: concurrency }, () => worker()));
await browser.close();

const pagesWithContainers = results.filter((item) => item.textElements > 0);
const violatingPages = results.filter((item) => item.violations.length > 0);
const hiddenPages = results.filter((item) => item.hidden.length > 0);
const failedPages = results.filter((item) => item.error || (item.status !== null && item.status >= 400));
const report = {
  contract: 281,
  requirement: 'Every textual element inside hero/header computes to rgb(0, 0, 0)',
  generatedAt: new Date().toISOString(),
  htmlPages: htmlFiles.length,
  pagesWithHeroOrHeader: pagesWithContainers.length,
  auditedTextElements: results.reduce((sum, item) => sum + item.textElements, 0),
  violatingPages: violatingPages.length,
  violatingElements: results.reduce((sum, item) => sum + item.violations.length, 0),
  pagesWithHiddenOrClippedText: hiddenPages.length,
  failedPages: failedPages.length,
  results,
};
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'hero-header-black-audit-v281.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ ...report, results: undefined }, null, 2));
if (report.violatingPages || report.pagesWithHiddenOrClippedText || report.failedPages) {
  process.exitCode = 1;
}
