import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/';
const site = process.env.AUDIT_SITE_ROOT || '_site';
const outDir = process.env.AUDIT_OUT_DIR || path.join(site, 'api');
fs.mkdirSync(outDir, { recursive: true });
const dirs = root => fs.readdirSync(path.join(site, root), { withFileTypes: true })
  .filter(entry => entry.isDirectory()).map(entry => entry.name).sort();
const routes = [
  ...dirs('assessment-lab').map(slug => `assessment-lab/${slug}/`),
  ...dirs('cognitive-lab').map(slug => `cognitive-lab/${slug}/`),
];
const profiles = [
  { name: 'mobile', context: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ar-JO', reducedMotion: 'reduce' } },
  { name: 'desktop', context: { viewport: { width: 1440, height: 900 }, locale: 'ar-JO', reducedMotion: 'reduce' } },
];
const errors = [];
const rows = [];
const browser = await chromium.launch({ headless: true });
try {
  for (const profile of profiles) {
    const context = await browser.newContext(profile.context);
    const page = await context.newPage();
    for (const route of routes) {
      try {
        const response = await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
        if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
        await page.waitForSelector('[data-v12-lab]', { timeout: 10000 });
        const result = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
          .analyze();
        const severe = result.violations.filter(item => item.impact === 'critical' || item.impact === 'serious');
        if (severe.length) {
          errors.push(`${profile.name}:${route} ${severe.map(item => `${item.id}:${item.impact}:${item.nodes.length}`).join(', ')}`);
        }
        rows.push({
          profile: profile.name,
          route,
          violations: result.violations.length,
          seriousCritical: severe.length,
          seriousCriticalNodes: severe.reduce((sum, item) => sum + item.nodes.length, 0),
        });
      } catch (error) {
        errors.push(`${profile.name}:${route} ${error}`);
        rows.push({ profile: profile.name, route, failed: true, error: String(error) });
      }
    }
    await context.close();
  }
} finally {
  await browser.close();
}

const report = {
  version: 32,
  status: errors.length ? 'failed' : 'passed',
  tools: routes.length,
  profiles: profiles.map(profile => profile.name),
  expectedRuns: routes.length * profiles.length,
  completedRuns: rows.length,
  seriousCriticalViolations: rows.reduce((sum, row) => sum + (row.seriousCritical || 0), 0),
  seriousCriticalNodes: rows.reduce((sum, row) => sum + (row.seriousCriticalNodes || 0), 0),
  errors,
  rows,
};
fs.writeFileSync(path.join(outDir, 'lab-axe-v32.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
