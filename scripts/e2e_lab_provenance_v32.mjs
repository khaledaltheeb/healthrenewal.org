import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const site = process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(site, 'api');
fs.mkdirSync(outDir, { recursive: true });

const routes = [];
for (const root of ['assessment-lab', 'cognitive-lab']) {
  for (const entry of fs.readdirSync(path.join(site, root), { withFileTypes: true })) {
    if (entry.isDirectory() && fs.existsSync(path.join(site, root, entry.name, 'index.html'))) routes.push(`${root}/${entry.name}/`);
  }
}
routes.sort();

const profiles = [
  { name: 'mobile', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  { name: 'desktop', viewport: { width: 1440, height: 900 }, isMobile: false, hasTouch: false },
];
const allowedHosts = new Set(['www.who.int','who.int','tdr.who.int','www.nimh.nih.gov','nimh.nih.gov','www.samhsa.gov','samhsa.gov','www.cdc.gov','cdc.gov','pubmed.ncbi.nlm.nih.gov']);
const errors = [], rows = [], sourceUrls = new Set(), classifications = new Map();
if (routes.length !== 93) errors.push(`expected 93 routes, found ${routes.length}`);

const browser = await chromium.launch({ headless: true, args: ['--mute-audio'] });
try {
  for (const profile of profiles) {
    const context = await browser.newContext({ viewport: profile.viewport, isMobile: profile.isMobile, hasTouch: profile.hasTouch, locale: 'ar-JO', reducedMotion: 'reduce' });
    try {
      for (const route of routes) {
        const page = await context.newPage(), runtimeErrors = [], started = Date.now();
        page.on('pageerror', error => runtimeErrors.push(`pageerror:${error}`));
        page.on('console', message => { if (message.type() === 'error') runtimeErrors.push(`console:${message.text()}`); });
        try {
          const response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
          if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
          await page.waitForSelector('.lab-provenance-v32', { timeout: 10000 });
          const definition = await page.locator('#lab-definition').evaluate(node => JSON.parse(node.textContent));
          const result = await page.locator('.lab-provenance-v32').evaluate(section => {
            const rect = section.getBoundingClientRect();
            return {
              heading: section.querySelector('h2')?.textContent.trim() || '', text: section.textContent || '',
              sourceCards: section.querySelectorAll('.lab-provenance-v32__source').length,
              statusTerms: [...section.querySelectorAll('dt')].map(node => node.textContent.trim()),
              links: [...section.querySelectorAll('a[href]')].map(link => ({ href: link.href, rel: link.rel })),
              left: rect.left, right: rect.right, documentWidth: document.documentElement.scrollWidth,
              clientWidth: document.documentElement.clientWidth,
              markerCount: (document.documentElement.innerHTML.match(/lab-provenance-v32:start/g) || []).length,
            };
          });
          const classification = String(definition.provenance_classification || '');
          classifications.set(classification, (classifications.get(classification) || 0) + 1);
          if (definition.provenance_version !== 32) throw new Error(`provenance_version=${definition.provenance_version}`);
          if (!['official_instrument','original_monitor','site_cognitive_task'].includes(classification)) throw new Error(`classification=${classification}`);
          if (!Array.isArray(definition.provenance_source_ids) || definition.provenance_source_ids.length < 1) throw new Error('missing source IDs');
          if (!Array.isArray(definition.provenance_source_urls) || definition.provenance_source_urls.length !== definition.provenance_source_ids.length) throw new Error('source URLs mismatch');
          if (!String(definition.provenance_validation_status || '').trim() || !String(definition.provenance_implementation_scope || '').trim()) throw new Error('missing provenance disclosure');
          if (!result.heading.includes('المصدرية وحالة القياس')) throw new Error(`heading=${result.heading}`);
          for (const term of ['تصنيف الأداة','حالة التحقق','نطاق التنفيذ الحالي']) if (!result.statusTerms.includes(term)) throw new Error(`missing status term ${term}`);
          for (const phrase of ['كيف استُخدمت المصادر؟','قاعدة التفسير','المصادر وحدود كل استشهاد','لا يعني أن الكود أو الترجمة أو البنود']) if (!result.text.includes(phrase)) throw new Error(`missing disclosure ${phrase}`);
          if (result.sourceCards !== definition.provenance_source_ids.length || result.links.length !== definition.provenance_source_urls.length) throw new Error('source card/link count mismatch');
          for (const [index, link] of result.links.entries()) {
            const parsed = new URL(link.href);
            if (parsed.protocol !== 'https:' || !allowedHosts.has(parsed.hostname)) throw new Error(`untrusted source ${link.href}`);
            if (!link.rel.includes('noopener') || !link.rel.includes('noreferrer')) throw new Error(`unsafe rel ${link.rel}`);
            if (link.href !== definition.provenance_source_urls[index]) throw new Error(`visible/definition URL mismatch ${link.href}`);
            sourceUrls.add(link.href);
          }
          if (result.markerCount !== 1) throw new Error(`marker count=${result.markerCount}`);
          if (result.documentWidth > result.clientWidth + 4 || result.left < -4 || result.right > result.clientWidth + 4) throw new Error(`horizontal overflow ${result.documentWidth}/${result.clientWidth}`);
          if (classification === 'original_monitor' && (!result.text.includes('غير معيارية') || !result.text.includes('غير متحققة سيكومتريًا'))) throw new Error('monitor validation disclosure absent');
          if (classification === 'site_cognitive_task' && (!result.text.includes('غير مقننة') || !result.text.includes('لا توجد معايير عمرية'))) throw new Error('cognitive validation disclosure absent');
          if (classification === 'official_instrument' && !result.text.includes('نسخة عربية') && !result.text.includes('عرض إرشادي')) throw new Error('official/adapted distinction absent');
          if (runtimeErrors.length) throw new Error(runtimeErrors.join(' | '));
          rows.push({ profile: profile.name, route, status: 'passed', classification, sources: result.sourceCards, durationMs: Date.now() - started });
        } catch (error) {
          errors.push(`${profile.name}:${route} ${error}`);
          rows.push({ profile: profile.name, route, status: 'failed', error: String(error), durationMs: Date.now() - started });
        } finally { await page.close(); }
      }
    } finally { await context.close(); }
  }
} finally { await browser.close(); }

const expectedClassificationRuns = { official_instrument: 8, original_monitor: 72, site_cognitive_task: 106 };
for (const [key, expected] of Object.entries(expectedClassificationRuns)) if ((classifications.get(key) || 0) !== expected) errors.push(`${key} runs=${classifications.get(key) || 0}, expected=${expected}`);
if (sourceUrls.size < 20) errors.push(`unique source URLs=${sourceUrls.size}`);
const report = { version: 32, status: errors.length ? 'failed' : 'passed', routes: routes.length, profiles: profiles.map(profile => profile.name), expectedRuns: routes.length * profiles.length, completedRuns: rows.length, passedRuns: rows.filter(row => row.status === 'passed').length, failedRuns: rows.filter(row => row.status === 'failed').length, classificationRuns: Object.fromEntries(classifications), uniqueSourceUrls: sourceUrls.size, errors, rows };
fs.writeFileSync(path.join(outDir, 'lab-provenance-e2e-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
