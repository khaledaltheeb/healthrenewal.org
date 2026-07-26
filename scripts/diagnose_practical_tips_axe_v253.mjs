import fs from 'node:fs';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/pterminology-site/';
const out = process.env.AUDIT_OUT || 'practical-tips-axe-v253.json';
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    locale: 'ar-JO',
    colorScheme: 'light',
    reducedMotion: 'reduce',
    serviceWorkers: 'block'
  });
  const page = await context.newPage();
  const response = await page.goto(new URL('tips/', base).href, {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  if (!response || !response.ok()) throw new Error(`navigation ${response?.status() ?? 'none'}`);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  const violations = [];
  for (const violation of results.violations.filter(row => ['critical', 'serious'].includes(row.impact))) {
    const nodes = [];
    for (const node of violation.nodes) {
      const selector = Array.isArray(node.target) ? node.target[0] : node.target;
      let computed = null;
      try {
        computed = await page.locator(selector).first().evaluate(element => {
          const style = getComputedStyle(element);
          const parentStyle = element.parentElement ? getComputedStyle(element.parentElement) : null;
          return {
            tag: element.tagName.toLowerCase(),
            id: element.id || null,
            className: typeof element.className === 'string' ? element.className : null,
            text: (element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 220),
            color: style.color,
            backgroundColor: style.backgroundColor,
            backgroundImage: style.backgroundImage,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            opacity: style.opacity,
            parentTag: element.parentElement?.tagName.toLowerCase() || null,
            parentClassName: typeof element.parentElement?.className === 'string' ? element.parentElement.className : null,
            parentColor: parentStyle?.color || null,
            parentBackgroundColor: parentStyle?.backgroundColor || null,
            parentBackgroundImage: parentStyle?.backgroundImage || null
          };
        });
      } catch (error) {
        computed = { error: String(error) };
      }
      nodes.push({
        target: node.target,
        html: node.html,
        failureSummary: node.failureSummary,
        any: node.any,
        all: node.all,
        none: node.none,
        computed
      });
    }
    violations.push({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      helpUrl: violation.helpUrl,
      nodes
    });
  }
  const report = { route: 'tips/', violations };
  fs.writeFileSync(out, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (!violations.length) console.log('No serious/critical tips violations.');
  await context.close();
} finally {
  await browser.close();
}
