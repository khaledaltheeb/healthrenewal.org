import fs from 'node:fs';
import path from 'node:path';
import lighthouse from 'lighthouse';
import { launch } from 'chrome-launcher';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import {
  aggregateLighthouseSamples,
  normalizeOddSampleCount
} from './lighthouse_statistics_v201.mjs';

const base = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/pterminology-site/';
const outDir = process.env.AUDIT_OUT_DIR || '_site/api';
fs.mkdirSync(outDir, { recursive: true });

const lighthouseTargets = [
  { route: '', group: 'core', label: 'homepage' },
  { route: 'encyclopedia/', group: 'content', label: 'encyclopedia-index' },
  { route: 'tips/', group: 'content', label: 'tips-index' },
  { route: 'assessment-lab/phq-9-plus/', group: 'labs', label: 'assessment-lab' },
  { route: 'cognitive-lab/simple-reaction/', group: 'labs', label: 'cognitive-lab' },
  { route: 'provider-assessment-demo/', group: 'provider-assessment', label: 'provider-platform' },
  { route: 'provider-assessment-demo/professional-console.html', group: 'provider-assessment', label: 'professional-console' },
  { route: 'provider-assessment-demo/training/', group: 'provider-assessment', label: 'professional-academy' },
  { route: 'provider-assessment-demo/conditions/autism/', group: 'provider-assessment', label: 'autism-pathway' }
];

const axeTargets = [
  { route: '', group: 'core', label: 'homepage' },
  { route: 'encyclopedia/', group: 'content', label: 'encyclopedia-index' },
  { route: 'encyclopedia/concept-0001/', group: 'content', label: 'encyclopedia-concept' },
  { route: 'tips/', group: 'content', label: 'tips-index' },
  { route: 'tips/better-sleep/', group: 'content', label: 'tips-detail' },
  { route: 'assessment-lab/phq-9-plus/', group: 'labs', label: 'assessment-lab' },
  { route: 'cognitive-lab/simple-reaction/', group: 'labs', label: 'cognitive-lab' },
  { route: 'sectors/child/', group: 'content', label: 'child-sector' },
  { route: 'provider-assessment-demo/', group: 'provider-assessment', label: 'provider-platform', ready: '#workspace' },
  { route: 'provider-assessment-demo/professional-console.html', group: 'provider-assessment', label: 'professional-console', ready: 'main' },
  { route: 'provider-assessment-demo/training/', group: 'provider-assessment', label: 'professional-academy', ready: '#training-modules' },
  { route: 'provider-assessment-demo/conditions/autism/', group: 'provider-assessment', label: 'autism-pathway', ready: '#condition-root' }
];

const lighthouseRoutes = lighthouseTargets.map(target => target.route);
const axeRoutes = axeTargets.map(target => target.route);
const mobileHomeSampleCount = normalizeOddSampleCount(process.env.AUDIT_MOBILE_HOME_SAMPLES, 3);

const thresholds = {
  mobile: { performance: 0.75, accessibility: 0.92, bestPractices: 0.90, seo: 0.92, lcp: 4000, cls: 0.10, tbt: 600 },
  desktop: { performance: 0.85, accessibility: 0.92, bestPractices: 0.90, seo: 0.92, lcp: 2500, cls: 0.10, tbt: 300 }
};
const desktopThrottling = { rttMs: 40, throughputKbps: 10240, cpuSlowdownMultiplier: 1, requestLatencyMs: 0, downloadThroughputKbps: 0, uploadThroughputKbps: 0 };
const mobileThrottling = { rttMs: 150, throughputKbps: 1638.4, cpuSlowdownMultiplier: 4, requestLatencyMs: 562.5, downloadThroughputKbps: 1474.56, uploadThroughputKbps: 675 };

const errors = [], warnings = [], lighthouseRuns = [], lighthouseSamples = [], axeRuns = [];

function warningTaxonomy() {
  const auditPath = path.join(outDir, 'full-site-audit-v16.json');
  if (!fs.existsSync(auditPath)) {
    return { available: false, reason: 'full-site-audit-v16.json missing' };
  }
  const audit = JSON.parse(fs.readFileSync(auditPath, 'utf8'));
  const total = Number(audit.warning_count || 0);
  const renderBlocking = Number(audit.blocking_scripts || 0);
  const emptyLinks = Number(audit.empty_links || 0);
  const residual = Math.max(0, total - renderBlocking - emptyLinks);
  const sample = Array.isArray(audit.warnings) ? audit.warnings : [];
  const sampledCategories = {
    headingStructure: sample.filter(value => value.startsWith('Heading jump ')).length,
    missingStructuredData: sample.filter(value => value.startsWith('JSON-LD missing ')).length,
    missingSocialMetadata: sample.filter(value => /^Missing (?:og:|twitter:)/.test(value)).length,
    missingPwaMetadata: sample.filter(value => value.startsWith('Manifest link missing ') || value.startsWith('theme-color missing ')).length,
    imageDimensions: sample.filter(value => value.startsWith('Image dimensions missing ')).length,
    fixedWidthOverflow: sample.filter(value => value.startsWith('Potential fixed-width overflow ')).length,
    insecureExternalReference: sample.filter(value => value.startsWith('Non-HTTPS external reference ')).length,
    oversizedAsset: sample.filter(value => value.startsWith('Large asset over ')).length
  };
  const budgets = {
    totalWarnings: { baseline: 4436, actual: total, regressed: total > 4436 },
    renderBlockingScripts: { baseline: 3438, actual: renderBlocking, regressed: renderBlocking > 3438 },
    emptyLinkText: { baseline: 111, actual: emptyLinks, regressed: emptyLinks > 111 }
  };
  const regressions = Object.entries(budgets).filter(([, value]) => value.regressed).map(([name, value]) => `${name} ${value.actual} > ${value.baseline}`);
  if (regressions.length) warnings.push(`Full-site warning debt regression: ${regressions.join(', ')}`);
  return {
    available: true,
    sourceVersion: audit.version,
    contentPages: audit.content_pages,
    totalWarnings: total,
    categories: {
      renderBlockingScripts: {
        count: renderBlocking,
        priority: 'performance-debt',
        blocking: false,
        action: 'Convert safe external scripts to defer/module while preserving execution order.'
      },
      emptyLinkText: {
        count: emptyLinks,
        priority: 'accessibility-review',
        blocking: false,
        action: 'Review accessible names; Axe serious/critical findings remain the blocking source of truth.'
      },
      otherWarnings: {
        count: residual,
        priority: 'metadata-and-structure-debt',
        blocking: false,
        sampledFrom: sample.length,
        sampledCategories
      }
    },
    budgets,
    regressionCount: regressions.length,
    regressions
  };
}

async function runLighthouseSample(url, formFactor, target) {
  const chrome = await launch({ chromeFlags: ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage'] });
  try {
    const config = {
      extends: 'lighthouse:default',
      settings: {
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
        formFactor,
        screenEmulation: formFactor === 'mobile'
          ? { mobile: true, width: 390, height: 844, deviceScaleFactor: 2, disabled: false }
          : { mobile: false, width: 1440, height: 900, deviceScaleFactor: 1, disabled: false },
        throttlingMethod: 'simulate',
        throttling: formFactor === 'mobile' ? mobileThrottling : desktopThrottling,
        locale: 'ar'
      }
    };
    const result = await lighthouse(url, { port: chrome.port, output: 'json', logLevel: 'error' }, config);
    const lhr = result.lhr;
    return {
      route: target.route,
      group: target.group,
      label: target.label,
      formFactor,
      performance: lhr.categories.performance.score,
      accessibility: lhr.categories.accessibility.score,
      bestPractices: lhr.categories['best-practices'].score,
      seo: lhr.categories.seo.score,
      fcp: lhr.audits['first-contentful-paint']?.numericValue ?? null,
      lcp: lhr.audits['largest-contentful-paint']?.numericValue ?? null,
      cls: lhr.audits['cumulative-layout-shift']?.numericValue ?? null,
      tbt: lhr.audits['total-blocking-time']?.numericValue ?? null,
      speedIndex: lhr.audits['speed-index']?.numericValue ?? null,
      interactive: lhr.audits.interactive?.numericValue ?? null,
      totalByteWeight: lhr.audits['total-byte-weight']?.numericValue ?? null,
      unusedJavascript: lhr.audits['unused-javascript']?.numericValue ?? null,
      unusedCss: lhr.audits['unused-css-rules']?.numericValue ?? null
    };
  } finally {
    await chrome.kill();
  }
}

function evaluateLighthouse(metrics) {
  const limit = thresholds[metrics.formFactor];
  for (const key of ['performance', 'accessibility', 'bestPractices', 'seo']) {
    if ((metrics[key] ?? 0) < limit[key]) {
      errors.push(`Lighthouse ${metrics.formFactor} ${metrics.route || '/'} ${key}=${metrics[key]} < ${limit[key]}`);
    }
  }
  if ((metrics.lcp ?? Infinity) > limit.lcp) {
    errors.push(`Lighthouse ${metrics.formFactor} ${metrics.route || '/'} LCP=${Math.round(metrics.lcp)}ms > ${limit.lcp}ms`);
  }
  if ((metrics.cls ?? Infinity) > limit.cls) {
    errors.push(`Lighthouse ${metrics.formFactor} ${metrics.route || '/'} CLS=${metrics.cls} > ${limit.cls}`);
  }
  if ((metrics.tbt ?? Infinity) > limit.tbt) {
    errors.push(`Lighthouse ${metrics.formFactor} ${metrics.route || '/'} TBT=${Math.round(metrics.tbt)}ms > ${limit.tbt}ms`);
  }
  if ((metrics.totalByteWeight ?? 0) > 1_500_000) {
    warnings.push(`Large page weight ${metrics.formFactor} ${metrics.route || '/'} ${Math.round(metrics.totalByteWeight / 1024)}KB`);
  }
}

async function measureRoute(target, formFactor, sampleCount) {
  const samples = [];
  const url = new URL(target.route, base).href;
  for (let index = 1; index <= sampleCount; index += 1) {
    const sample = await runLighthouseSample(url, formFactor, target);
    const recorded = { ...sample, sampleIndex: index, sampleCount };
    samples.push(recorded);
    lighthouseSamples.push(recorded);
  }
  const aggregate = { ...aggregateLighthouseSamples(samples), group: target.group, label: target.label };
  lighthouseRuns.push(aggregate);
  evaluateLighthouse(aggregate);
}

async function runAxe() {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const target of axeTargets) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'ar-JO', colorScheme: 'light', reducedMotion: 'reduce', serviceWorkers: 'block' });
      const page = await context.newPage();
      const runtimeErrors = [];
      page.on('pageerror', error => runtimeErrors.push(error.message));
      const response = await page.goto(new URL(target.route, base).href, { waitUntil: 'networkidle', timeout: 30000 });
      if (!response || !response.ok()) errors.push(`Axe navigation failed ${target.route}: ${response?.status() ?? 'no response'}`);
      if (target.ready) await page.locator(target.ready).first().waitFor({ state: 'attached', timeout: 12000 });
      if (runtimeErrors.length) errors.push(`Runtime errors on ${target.route || '/'}: ${runtimeErrors.slice(0, 5).join(' | ')}`);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
      const serious = results.violations.filter(v => ['critical', 'serious'].includes(v.impact));
      const moderate = results.violations.filter(v => v.impact === 'moderate');
      axeRuns.push({
        route: target.route,
        group: target.group,
        label: target.label,
        runtimeErrors: runtimeErrors.length,
        violations: results.violations.length,
        serious: serious.length,
        moderate: moderate.length,
        details: results.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.length }))
      });
      if (serious.length) errors.push(`WCAG serious/critical violations on ${target.route || '/'}: ${serious.map(v => `${v.id}(${v.nodes.length})`).join(', ')}`);
      if (moderate.length) warnings.push(`WCAG moderate violations on ${target.route || '/'}: ${moderate.map(v => `${v.id}(${v.nodes.length})`).join(', ')}`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

for (const target of lighthouseTargets) {
  await measureRoute(target, 'mobile', target.route === '' ? mobileHomeSampleCount : 1);
  await measureRoute(target, 'desktop', 1);
}
await runAxe();

const scoreSummary = {};
for (const factor of ['mobile', 'desktop']) {
  const rows = lighthouseRuns.filter(x => x.formFactor === factor);
  scoreSummary[factor] = {
    minimumPerformance: Math.min(...rows.map(x => x.performance)),
    minimumAccessibility: Math.min(...rows.map(x => x.accessibility)),
    minimumBestPractices: Math.min(...rows.map(x => x.bestPractices)),
    minimumSeo: Math.min(...rows.map(x => x.seo)),
    maximumLcpMs: Math.max(...rows.map(x => x.lcp ?? 0)),
    maximumCls: Math.max(...rows.map(x => x.cls ?? 0)),
    maximumTbtMs: Math.max(...rows.map(x => x.tbt ?? 0))
  };
}

const providerLighthouse = lighthouseRuns.filter(row => row.group === 'provider-assessment');
const providerAxe = axeRuns.filter(row => row.group === 'provider-assessment');
const routeCoverage = {
  lighthouse: {
    total: lighthouseTargets.length,
    providerAssessment: lighthouseTargets.filter(target => target.group === 'provider-assessment').length,
    targets: lighthouseTargets
  },
  axe: {
    total: axeTargets.length,
    providerAssessment: axeTargets.filter(target => target.group === 'provider-assessment').length,
    targets: axeTargets.map(({ ready, ...target }) => target)
  },
  providerAssessment: {
    lighthouseRuns: providerLighthouse.length,
    axeRuns: providerAxe.length,
    runtimeErrors: providerAxe.reduce((sum, row) => sum + row.runtimeErrors, 0),
    seriousViolations: providerAxe.reduce((sum, row) => sum + row.serious, 0),
    moderateViolations: providerAxe.reduce((sum, row) => sum + row.moderate, 0)
  }
};

const report = {
  version: 24,
  base,
  note: 'Lighthouse provides laboratory LCP/CLS/TBT. The mobile homepage uses an odd number of independent samples and median lab metrics to reduce runner variance; accessibility, best-practices and SEO retain the strict minimum sample. INP requires real-user field data and is not claimed here.',
  aggregationPolicy: {
    mobileHomepageSamples: mobileHomeSampleCount,
    labMetrics: 'median',
    qualityScores: 'minimum',
    thresholdsUnchanged: true
  },
  routeCoverage,
  warningTaxonomy: warningTaxonomy(),
  lighthouseRoutes: lighthouseRoutes.length,
  axeRoutes: axeRoutes.length,
  scoreSummary,
  lighthouseRuns,
  lighthouseSamples,
  axeRuns,
  warningCount: warnings.length,
  warnings,
  errorCount: errors.length,
  errors
};
fs.writeFileSync(path.join(outDir, 'global-quality-v20.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (errors.length) process.exit(1);
