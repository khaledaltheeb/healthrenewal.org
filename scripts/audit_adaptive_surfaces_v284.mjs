import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const siteDir = path.resolve(process.argv[2] || '_site');
const baseUrl = (process.env.AUDIT_BASE_URL || 'http://127.0.0.1:8000/pterminology-site/').replace(/\/?$/, '/');
const outDir = path.resolve(process.env.AUDIT_OUT_DIR || path.join(siteDir, 'api'));
const concurrency = Math.max(1, Number(process.env.HERO_AUDIT_CONCURRENCY || 4));
const timeoutMs = Math.max(5000, Number(process.env.HERO_AUDIT_TIMEOUT_MS || 30000));

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
function familyFor(relativePath) {
  const normalized = relativePath.replace(/\\/g, '/');
  return normalized.includes('/') ? normalized.split('/')[0] : '(root)';
}

const profiles = [
  { name: 'desktop-ltr-light', viewport: { width: 1440, height: 1000 }, locale: 'en', direction: 'ltr', colorScheme: 'light', media: 'screen', reducedMotion: 'no-preference', prefersContrast: 'no-preference' },
  { name: 'mobile-rtl-light-reduced', viewport: { width: 390, height: 844 }, locale: 'ar', direction: 'rtl', colorScheme: 'light', media: 'screen', reducedMotion: 'reduce', prefersContrast: 'no-preference' },
  { name: 'desktop-rtl-dark-high-contrast', viewport: { width: 1440, height: 1000 }, locale: 'ar', direction: 'rtl', colorScheme: 'dark', media: 'screen', reducedMotion: 'reduce', prefersContrast: 'more' },
  { name: 'print-rtl', viewport: { width: 1024, height: 1400 }, locale: 'ar', direction: 'rtl', colorScheme: 'light', media: 'print', reducedMotion: 'reduce', prefersContrast: 'no-preference' },
];

const htmlFiles = walk(siteDir).filter((file) => file.endsWith('.html')).sort();
const browser = await chromium.launch({ headless: true });
const results = new Array(htmlFiles.length);
let cursor = 0;
let completed = 0;

async function createProfilePage(profile) {
  const context = await browser.newContext({ viewport: profile.viewport, colorScheme: profile.colorScheme, reducedMotion: profile.reducedMotion, locale: profile.locale });
  const page = await context.newPage();
  await page.emulateMedia({ media: profile.media, colorScheme: profile.colorScheme, reducedMotion: profile.reducedMotion, forcedColors: 'none' });
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setEmulatedMedia', {
    media: profile.media,
    features: [
      { name: 'prefers-color-scheme', value: profile.colorScheme },
      { name: 'prefers-reduced-motion', value: profile.reducedMotion },
      { name: 'prefers-contrast', value: profile.prefersContrast },
    ],
  });
  return { context, page };
}

async function auditLoadedPage(page, profile) {
  await page.evaluate((direction) => { document.documentElement.dir = direction; }, profile.direction);
  await page.waitForFunction(() => document.documentElement.dataset.heroHeaderContrast === 'v283', null, { timeout: Math.min(timeoutMs, 5000) }).catch(() => null);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));

  return page.evaluate(async ({ media }) => {
    const CONTAINER_SELECTOR = [
      'header', '[role="banner"]', 'nav', '[role="navigation"]', '[role="search"]',
      '[class*="hero"]', '[class*="Hero"]', '[id*="hero"]', '[id*="Hero"]',
      '[class*="masthead"]', '[class*="banner"]', '[class*="Banner"]',
      '[class*="breadcrumb"]', '[class*="Breadcrumb"]',
      'footer', '[role="contentinfo"]', '.site-footer',
    ].join(',');
    const TEXT_SELECTOR = [
      'h1','h2','h3','h4','h5','h6','p','li','dt','dd','small','strong','em','span','label','blockquote','a',
      'button','[role="button"]','input','select','textarea','option','summary','[tabindex]',
    ].join(',');
    const CONTROL_SELECTOR = 'button,[role="button"],input,select,textarea,option,summary,[tabindex],a.btn,a.button,[class*="button"],[class*="Button"]';
    const STATE_ATTRS = ['data-hh-force-hover','data-hh-force-focus','data-hh-force-visited','data-hh-force-disabled'];

    function parseColor(value) {
      if (!value || value === 'transparent') return null;
      const match = String(value).match(/rgba?\(([^)]+)\)/i);
      if (!match) return null;
      const parts = match[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      if (parts.length < 3 || parts.slice(0, 3).some(Number.isNaN)) return null;
      return { r: Math.max(0, Math.min(255, parts[0])), g: Math.max(0, Math.min(255, parts[1])), b: Math.max(0, Math.min(255, parts[2])), a: Number.isFinite(parts[3]) ? Math.max(0, Math.min(1, parts[3])) : 1 };
    }
    function colorsFromGradient(value) {
      if (!value || value === 'none' || !/gradient\(/i.test(value)) return [];
      return [...value.matchAll(/rgba?\([^)]+\)/gi)].map((match) => parseColor(match[0])).filter(Boolean);
    }
    function composite(front, back) {
      const alpha = front.a + back.a * (1 - front.a);
      if (alpha <= 0) return { r: 255, g: 255, b: 255, a: 1 };
      return { r: (front.r * front.a + back.r * back.a * (1 - front.a)) / alpha, g: (front.g * front.a + back.g * back.a * (1 - front.a)) / alpha, b: (front.b * front.a + back.b * back.a * (1 - front.a)) / alpha, a: alpha };
    }
    function luminance(color) {
      const channels = [color.r, color.g, color.b].map((channel) => { const value = channel / 255; return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4; });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }
    function ratio(a, b) { const first = luminance(a); const second = luminance(b); return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05); }
    function colorString(color) { return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`; }
    function selectorFor(element) { return `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ''}${element.classList.length ? `.${[...element.classList].slice(0, 5).join('.')}` : ''}`; }
    function isVisible(element, style, rect) { return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0.05 && rect.width > 0 && rect.height > 0; }
    function isLargeText(style) { const fontSize = Number.parseFloat(style.fontSize) || 0; const fontWeight = Number.parseInt(style.fontWeight, 10) || 400; return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700); }
    function isUiControl(element) { return element.matches(CONTROL_SELECTOR); }
    function effectiveBackground(element) {
      const chain = [];
      let current = element;
      while (current && current.nodeType === Node.ELEMENT_NODE) {
        const style = getComputedStyle(current);
        chain.push({ selector: selectorFor(current), color: parseColor(style.backgroundColor), colorRaw: style.backgroundColor, image: style.backgroundImage, guarded: current.matches('.hh-overlay-dark,.hh-overlay-light,[data-surface="light"],[data-surface="dark"],[data-theme="light"],[data-theme="dark"],.surface-light,.surface-dark,.theme-light,.theme-dark,.hh-surface-light,.hh-surface-dark') });
        if (chain.at(-1).color?.a >= 0.999) break;
        current = current.parentElement;
      }
      let solid = { r: 255, g: 255, b: 255, a: 1 };
      for (let index = chain.length - 1; index >= 0; index -= 1) if (chain[index].color?.a > 0.001) solid = composite(chain[index].color, solid);
      const imageLayer = chain.find((layer) => layer.image && layer.image !== 'none' && !layer.guarded);
      let candidates = [solid];
      let unresolvedImage = false;
      if (imageLayer) {
        const gradientColors = colorsFromGradient(imageLayer.image);
        if (gradientColors.length) candidates = gradientColors.map((color) => composite(color, solid));
        else if (/url\(/i.test(imageLayer.image)) unresolvedImage = true;
      }
      return { candidates, unresolvedImage, layers: chain.map(({ selector, colorRaw, image, guarded }) => ({ selector, color: colorRaw, image, guarded })) };
    }

    const containers = [...document.querySelectorAll(CONTAINER_SELECTOR)];
    const allNodes = () => [...new Set(containers.flatMap((container) => [...(container.matches(TEXT_SELECTOR) ? [container] : []), ...container.querySelectorAll(TEXT_SELECTOR)]))];

    function snapshot(state, onlyControls = false, includeClipping = false) {
      const contrastViolations = [];
      const hiddenOrClipped = [];
      let visibleTextElements = 0;
      for (const element of allNodes()) {
        if (onlyControls && !isUiControl(element)) continue;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        if (!isVisible(element, style, rect)) continue;
        const text = (element.innerText || element.value || element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
        if (!text) continue;
        visibleTextElements += 1;
        const selector = selectorFor(element);
        const background = effectiveBackground(element);
        const foregroundRaw = parseColor(style.color) || { r: 0, g: 0, b: 0, a: 1 };
        const threshold = isUiControl(element) || isLargeText(style) ? 3 : 4.5;
        const ratios = background.candidates.map((candidate) => { const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, candidate) : foregroundRaw; return { foreground, background: candidate, ratio: ratio(foreground, candidate) }; });
        const worst = ratios.reduce((minimum, item) => item.ratio < minimum.ratio ? item : minimum, ratios[0]);
        if (worst.ratio + 0.001 < threshold || background.unresolvedImage) {
          contrastViolations.push({ state, selector, text, foreground: colorString(worst.foreground), effectiveBackground: colorString(worst.background), contrastRatio: Number(worst.ratio.toFixed(2)), threshold, fontSize: style.fontSize, fontWeight: style.fontWeight, backgroundImage: style.backgroundImage, unresolvedImage: background.unresolvedImage, layers: background.layers, reason: background.unresolvedImage ? 'background image without a stable adaptive surface or overlay' : 'contrast ratio below WCAG AA threshold' });
        }
        if (!includeClipping) continue;
        const hasOwnText = [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
        if (hasOwnText || isUiControl(element)) {
          const clippedX = element.scrollWidth > element.clientWidth + 1 && !['visible', 'clip'].includes(style.overflowX);
          const clippedY = element.scrollHeight > element.clientHeight + 1 && !['visible', 'clip'].includes(style.overflowY);
          const lineClamped = style.webkitLineClamp && style.webkitLineClamp !== 'none' && Number(style.webkitLineClamp) > 0 && element.scrollHeight > element.clientHeight + 1;
          if (clippedX || clippedY || lineClamped) hiddenOrClipped.push({ selector, text, clippedX, clippedY, lineClamped, overflowX: style.overflowX, overflowY: style.overflowY, width: rect.width, height: rect.height, scrollWidth: element.scrollWidth, scrollHeight: element.scrollHeight });
        }
      }
      return { state, visibleTextElements, contrastViolations, hiddenOrClipped };
    }

    function transformedStateCss(state) {
      const pseudo = {
        hover: [/:hover\b/g, '[data-hh-force-hover]'],
        focus: [/:focus-visible\b/g, '[data-hh-force-focus]', /:focus\b/g, '[data-hh-force-focus]'],
        visited: [/:visited\b/g, '[data-hh-force-visited]'],
        disabled: [/:disabled\b/g, '[data-hh-force-disabled]'],
      }[state];
      const out = [];
      function transformSelector(selector) { let value = selector; for (let index = 0; index < pseudo.length; index += 2) value = value.replace(pseudo[index], pseudo[index + 1]); return value; }
      function walkRules(rules) {
        for (const rule of rules) {
          try {
            if (rule.type === CSSRule.STYLE_RULE && rule.selectorText) {
              const marker = state === 'focus' ? /:focus(?:-visible)?\b/ : new RegExp(`:${state}\\b`);
              if (!marker.test(rule.selectorText)) continue;
              const selector = transformSelector(rule.selectorText);
              if (selector !== rule.selectorText) out.push(`${selector}{${rule.style.cssText}}`);
            } else if (typeof CSSMediaRule !== 'undefined' && rule instanceof CSSMediaRule) {
              if (matchMedia(rule.conditionText).matches) walkRules(rule.cssRules);
            } else if (typeof CSSSupportsRule !== 'undefined' && rule instanceof CSSSupportsRule) {
              if (CSS.supports(rule.conditionText)) walkRules(rule.cssRules);
            } else if (rule.cssRules) walkRules(rule.cssRules);
          } catch { /* inaccessible or unsupported CSS rule */ }
        }
      }
      for (const sheet of document.styleSheets) { try { walkRules(sheet.cssRules); } catch { /* cross-origin stylesheet */ } }
      return out.join('\n');
    }

    const restoreDisabled = [];
    function applyState(state) {
      const style = document.createElement('style');
      style.dataset.hhStateAudit = state;
      style.textContent = transformedStateCss(state);
      document.head.append(style);
      if (state === 'hover') {
        for (const container of containers) { container.setAttribute('data-hh-force-hover', ''); container.querySelectorAll('*').forEach((element) => element.setAttribute('data-hh-force-hover', '')); }
      } else if (state === 'focus') allNodes().filter(isUiControl).forEach((element) => element.setAttribute('data-hh-force-focus', ''));
      else if (state === 'visited') allNodes().filter((element) => element.matches('a[href]')).forEach((element) => element.setAttribute('data-hh-force-visited', ''));
      else if (state === 'disabled') {
        allNodes().filter(isUiControl).forEach((element) => {
          restoreDisabled.push({ element, disabled: 'disabled' in element ? element.disabled : null, aria: element.getAttribute('aria-disabled') });
          element.setAttribute('data-hh-force-disabled', '');
          element.setAttribute('aria-disabled', 'true');
          if ('disabled' in element) element.disabled = true;
        });
      }
      window.__heroHeaderContrastV283?.scan?.();
    }

    function clearState() {
      document.querySelectorAll('style[data-hh-state-audit]').forEach((style) => style.remove());
      document.querySelectorAll(STATE_ATTRS.map((attribute) => `[${attribute}]`).join(',')).forEach((element) => STATE_ATTRS.forEach((attribute) => element.removeAttribute(attribute)));
      for (const record of restoreDisabled.splice(0)) {
        if (record.disabled !== null) record.element.disabled = record.disabled;
        if (record.aria === null) record.element.removeAttribute('aria-disabled');
        else record.element.setAttribute('aria-disabled', record.aria);
      }
      window.__heroHeaderContrastV283?.scan?.();
    }

    async function settle() { await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); }
    const snapshots = [snapshot('default', false, true)];
    if (media === 'screen') {
      for (const state of ['hover','focus','visited','disabled']) {
        applyState(state);
        await settle();
        snapshots.push(snapshot(state, true, false));
        clearState();
        await settle();
      }
    }
    return { containers: containers.length, guardVersion: document.documentElement.dataset.heroHeaderContrast || null, snapshots, stateMethod: media === 'screen' ? 'authored pseudo-state selectors transformed to equal-specificity audit attributes, then recomputed after the runtime guard' : 'default print computed style' };
  }, { media: profile.media });
}

async function worker(workerIndex) {
  const profilePages = [];
  try {
    for (const profile of profiles) profilePages.push({ profile, ...(await createProfilePage(profile)) });
    while (true) {
      const index = cursor++;
      if (index >= htmlFiles.length) break;
      const file = htmlFiles[index];
      const relative = path.relative(siteDir, file).split(path.sep).join('/');
      const url = toUrl(file);
      const record = { path: relative, family: familyFor(relative), url, profiles: [], textElements: 0, contrastViolations: [], hiddenOrClipped: [], failedProfiles: [] };
      for (const { profile, page } of profilePages) {
        try {
          const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
          const status = response?.status() ?? null;
          const audit = await auditLoadedPage(page, profile);
          const defaultSnapshot = audit.snapshots.find((item) => item.state === 'default');
          record.profiles.push({ name: profile.name, status, containers: audit.containers, visibleTextElements: defaultSnapshot?.visibleTextElements || 0, guardVersion: audit.guardVersion, states: audit.snapshots.map((item) => item.state), stateMethod: audit.stateMethod });
          record.textElements = Math.max(record.textElements, defaultSnapshot?.visibleTextElements || 0);
          for (const snapshot of audit.snapshots) {
            record.contrastViolations.push(...snapshot.contrastViolations.map((item) => ({ profile: profile.name, ...item })));
            if (snapshot.state === 'default') record.hiddenOrClipped.push(...snapshot.hiddenOrClipped.map((item) => ({ profile: profile.name, ...item })));
          }
          if (status !== null && status >= 400) record.failedProfiles.push({ profile: profile.name, status });
          if (audit.guardVersion !== 'v283') record.failedProfiles.push({ profile: profile.name, error: 'adaptive contrast guard did not initialize' });
        } catch (error) { record.failedProfiles.push({ profile: profile.name, error: String(error) }); }
      }
      results[index] = record;
      completed += 1;
      if (completed % 100 === 0 || completed === htmlFiles.length) console.error(`[adaptive-audit] ${completed}/${htmlFiles.length} pages complete (worker ${workerIndex})`);
    }
  } finally { await Promise.all(profilePages.map(({ context }) => context.close())); }
}

await Promise.all(Array.from({ length: Math.min(concurrency, htmlFiles.length || 1) }, (_, index) => worker(index + 1)));
await browser.close();

const safeResults = results.filter(Boolean);
const pagesWithContainers = safeResults.filter((item) => item.profiles.some((profile) => profile.containers > 0));
const violatingPages = safeResults.filter((item) => item.contrastViolations.length > 0);
const hiddenPages = safeResults.filter((item) => item.hiddenOrClipped.length > 0);
const failedPages = safeResults.filter((item) => item.failedProfiles.length > 0);
const familySummary = {};
const stateSummary = {};
for (const item of safeResults) {
  const entry = familySummary[item.family] ||= { pages: 0, violatingPages: 0, contrastViolations: 0, hiddenOrClippedPages: 0, hiddenOrClipped: 0, failedPages: 0 };
  entry.pages += 1;
  if (item.contrastViolations.length) entry.violatingPages += 1;
  entry.contrastViolations += item.contrastViolations.length;
  if (item.hiddenOrClipped.length) entry.hiddenOrClippedPages += 1;
  entry.hiddenOrClipped += item.hiddenOrClipped.length;
  if (item.failedProfiles.length) entry.failedPages += 1;
  for (const violation of item.contrastViolations) stateSummary[violation.state] = (stateSummary[violation.state] || 0) + 1;
}

const report = {
  contract: 290,
  legacyContract: 284,
  requirement: 'Adaptive WCAG AA text/background contrast across header, hero, navigation, breadcrumb, search and footer surfaces',
  generatedAt: new Date().toISOString(),
  executionModel: 'reused browser contexts per worker/profile; every HTML page remains audited; interactive authored states are emulated and recomputed',
  stateCoverage: {
    default: 'computed on every visible text element in every profile',
    hover: 'authored :hover rules transformed to equal-specificity attributes and computed for all controls on screen profiles',
    focus: 'authored :focus and :focus-visible rules transformed and computed for all controls on screen profiles',
    visited: 'authored :visited rules transformed and computed without relying on private browsing history',
    disabled: 'native disabled and aria-disabled states applied and computed for all controls on screen profiles',
  },
  profiles,
  htmlPages: htmlFiles.length,
  completedPages: safeResults.length,
  pagesWithHeroOrHeader: pagesWithContainers.length,
  auditedTextElements: safeResults.reduce((sum, item) => sum + item.textElements, 0),
  contrastViolatingPages: violatingPages.length,
  contrastViolations: safeResults.reduce((sum, item) => sum + item.contrastViolations.length, 0),
  stateSummary,
  pagesWithHiddenOrClippedText: hiddenPages.length,
  hiddenOrClippedText: safeResults.reduce((sum, item) => sum + item.hiddenOrClipped.length, 0),
  failedPages: failedPages.length,
  familySummary,
  results: safeResults,
};

fs.mkdirSync(outDir, { recursive: true });
const serialized = JSON.stringify(report, null, 2);
fs.writeFileSync(path.join(outDir, 'hero-header-contrast-audit-v290.json'), serialized);
fs.writeFileSync(path.join(outDir, 'hero-header-contrast-audit-v284.json'), serialized);
fs.writeFileSync(path.join(outDir, 'hero-header-contrast-audit-v283.json'), serialized);
console.log(JSON.stringify({ ...report, results: undefined }, null, 2));
if (report.completedPages !== report.htmlPages || report.contrastViolations || report.pagesWithHiddenOrClippedText || report.failedPages) process.exitCode = 1;
