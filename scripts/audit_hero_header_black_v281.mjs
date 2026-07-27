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

const profiles = [
  {
    name: 'desktop-ltr-light',
    viewport: { width: 1440, height: 1000 },
    locale: 'en',
    direction: 'ltr',
    colorScheme: 'light',
    media: 'screen',
    reducedMotion: 'no-preference',
    prefersContrast: 'no-preference',
  },
  {
    name: 'mobile-rtl-light-reduced',
    viewport: { width: 390, height: 844 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'light',
    media: 'screen',
    reducedMotion: 'reduce',
    prefersContrast: 'no-preference',
  },
  {
    name: 'desktop-rtl-dark-high-contrast',
    viewport: { width: 1440, height: 1000 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'dark',
    media: 'screen',
    reducedMotion: 'reduce',
    prefersContrast: 'more',
  },
  {
    name: 'print-rtl',
    viewport: { width: 1024, height: 1400 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'light',
    media: 'print',
    reducedMotion: 'reduce',
    prefersContrast: 'no-preference',
  },
];

const htmlFiles = walk(siteDir).filter((file) => file.endsWith('.html')).sort();
const browser = await chromium.launch({ headless: true });
const results = [];
let cursor = 0;

async function auditPage(page, profile) {
  await page.emulateMedia({
    media: profile.media,
    colorScheme: profile.colorScheme,
    reducedMotion: profile.reducedMotion,
    forcedColors: 'none',
  });

  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setEmulatedMedia', {
    media: profile.media,
    features: [
      { name: 'prefers-color-scheme', value: profile.colorScheme },
      { name: 'prefers-reduced-motion', value: profile.reducedMotion },
      { name: 'prefers-contrast', value: profile.prefersContrast },
    ],
  });

  await page.evaluate((direction) => {
    document.documentElement.dir = direction;
  }, profile.direction);

  await page.waitForFunction(
    () => document.documentElement.dataset.heroHeaderContrast === 'v283',
    null,
    { timeout: Math.min(timeoutMs, 5000) },
  ).catch(() => null);

  return page.evaluate(() => {
    const CONTAINER_SELECTOR = [
      'header',
      '[role="banner"]',
      'nav',
      '[role="navigation"]',
      '[role="search"]',
      '[class*="hero"]', '[class*="Hero"]',
      '[id*="hero"]', '[id*="Hero"]',
      '[class*="masthead"]',
      '[class*="banner"]', '[class*="Banner"]',
      '[class*="breadcrumb"]', '[class*="Breadcrumb"]',
      'footer',
      '[role="contentinfo"]',
      '.site-footer',
    ].join(',');

    const TEXT_SELECTOR = [
      'h1','h2','h3','h4','h5','h6','p','li','dt','dd','small','strong','em','span','label','blockquote','a',
      'button','[role="button"]','input','select','textarea','summary','[tabindex]',
    ].join(',');

    function parseColor(value) {
      if (!value || value === 'transparent') return null;
      const match = String(value).match(/rgba?\(([^)]+)\)/i);
      if (!match) return null;
      const parts = match[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      if (parts.length < 3 || parts.slice(0, 3).some(Number.isNaN)) return null;
      return {
        r: Math.max(0, Math.min(255, parts[0])),
        g: Math.max(0, Math.min(255, parts[1])),
        b: Math.max(0, Math.min(255, parts[2])),
        a: Number.isFinite(parts[3]) ? Math.max(0, Math.min(1, parts[3])) : 1,
      };
    }

    function colorsFromGradient(value) {
      if (!value || value === 'none' || !/gradient\(/i.test(value)) return [];
      return [...value.matchAll(/rgba?\([^)]+\)/gi)]
        .map((match) => parseColor(match[0]))
        .filter(Boolean);
    }

    function composite(front, back) {
      const alpha = front.a + back.a * (1 - front.a);
      if (alpha <= 0) return { r: 255, g: 255, b: 255, a: 1 };
      return {
        r: (front.r * front.a + back.r * back.a * (1 - front.a)) / alpha,
        g: (front.g * front.a + back.g * back.a * (1 - front.a)) / alpha,
        b: (front.b * front.a + back.b * back.a * (1 - front.a)) / alpha,
        a: alpha,
      };
    }

    function luminance(color) {
      const channels = [color.r, color.g, color.b].map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }

    function ratio(a, b) {
      const first = luminance(a);
      const second = luminance(b);
      return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
    }

    function colorString(color) {
      return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`;
    }

    function effectiveBackground(element) {
      let current = element;
      let solid = { r: 255, g: 255, b: 255, a: 1 };
      const gradientCandidates = [];
      const layers = [];
      let unresolvedImage = false;

      while (current && current.nodeType === Node.ELEMENT_NODE) {
        const style = getComputedStyle(current);
        const image = style.backgroundImage;
        const parsed = parseColor(style.backgroundColor);
        const guarded = current.classList.contains('hh-overlay-dark')
          || current.classList.contains('hh-overlay-light')
          || current.matches('[data-surface="light"],[data-surface="dark"],[data-theme="light"],[data-theme="dark"],.surface-light,.surface-dark,.theme-light,.theme-dark,.hh-surface-light,.hh-surface-dark');

        if (image && image !== 'none') {
          const gradientColors = colorsFromGradient(image);
          if (gradientColors.length && !guarded) gradientCandidates.push(...gradientColors);
          else if (/url\(/i.test(image) && !guarded) unresolvedImage = true;
        }

        if (parsed && parsed.a > 0.001) {
          layers.push({ selector: current.tagName.toLowerCase(), color: style.backgroundColor, guarded });
          solid = composite(parsed, solid);
          if (parsed.a >= 0.999) break;
        }
        current = current.parentElement;
      }

      const candidates = gradientCandidates.length
        ? gradientCandidates.map((color) => composite(color, solid))
        : [solid];
      return { candidates, unresolvedImage, layers };
    }

    function isLargeText(style) {
      const fontSize = Number.parseFloat(style.fontSize) || 0;
      const fontWeight = Number.parseInt(style.fontWeight, 10) || 400;
      return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    }

    function isUiControl(element) {
      return element.matches('button,[role="button"],input,select,textarea,summary,[tabindex],a.btn,a.button,[class*="button"],[class*="Button"]');
    }

    function selectorFor(element) {
      return `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ''}${element.classList.length ? `.${[...element.classList].slice(0, 5).join('.')}` : ''}`;
    }

    function isVisible(element, style, rect) {
      return style.display !== 'none'
        && style.visibility !== 'hidden'
        && Number(style.opacity || 1) > 0.05
        && rect.width > 0
        && rect.height > 0;
    }

    const containers = [...document.querySelectorAll(CONTAINER_SELECTOR)];
    const nodes = [...new Set(containers.flatMap((container) => [
      ...(container.matches(TEXT_SELECTOR) ? [container] : []),
      ...container.querySelectorAll(TEXT_SELECTOR),
    ]))];

    const contrastViolations = [];
    const hiddenOrClipped = [];
    let visibleTextElements = 0;

    for (const element of nodes) {
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
      const ratios = background.candidates.map((candidate) => {
        const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, candidate) : foregroundRaw;
        return { foreground, background: candidate, ratio: ratio(foreground, candidate) };
      });
      const worst = ratios.reduce((minimum, item) => item.ratio < minimum.ratio ? item : minimum, ratios[0]);

      if (worst.ratio + 0.001 < threshold || background.unresolvedImage) {
        contrastViolations.push({
          selector,
          text,
          foreground: colorString(worst.foreground),
          effectiveBackground: colorString(worst.background),
          contrastRatio: Number(worst.ratio.toFixed(2)),
          threshold,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          backgroundImage: style.backgroundImage,
          unresolvedImage: background.unresolvedImage,
          layers: background.layers,
          reason: background.unresolvedImage
            ? 'background image without a stable adaptive surface or overlay'
            : 'contrast ratio below WCAG AA threshold',
        });
      }

      const clippedX = element.scrollWidth > element.clientWidth + 1 && !['visible', 'clip'].includes(style.overflowX);
      const clippedY = element.scrollHeight > element.clientHeight + 1 && !['visible', 'clip'].includes(style.overflowY);
      const lineClamped = style.webkitLineClamp && style.webkitLineClamp !== 'none'
        && Number(style.webkitLineClamp) > 0
        && element.scrollHeight > element.clientHeight + 1;
      if (clippedX || clippedY || lineClamped) {
        hiddenOrClipped.push({
          selector,
          text,
          clippedX,
          clippedY,
          lineClamped,
          overflowX: style.overflowX,
          overflowY: style.overflowY,
          width: rect.width,
          height: rect.height,
          scrollWidth: element.scrollWidth,
          scrollHeight: element.scrollHeight,
        });
      }
    }

    return {
      containers: containers.length,
      visibleTextElements,
      guardVersion: document.documentElement.dataset.heroHeaderContrast || null,
      contrastViolations,
      hiddenOrClipped,
    };
  });
}

async function worker() {
  while (true) {
    const index = cursor++;
    if (index >= htmlFiles.length) break;
    const file = htmlFiles[index];
    const relative = path.relative(siteDir, file).split(path.sep).join('/');
    const url = toUrl(file);
    const record = {
      path: relative,
      url,
      profiles: [],
      textElements: 0,
      contrastViolations: [],
      hiddenOrClipped: [],
      failedProfiles: [],
    };

    for (const profile of profiles) {
      const context = await browser.newContext({
        viewport: profile.viewport,
        colorScheme: profile.colorScheme,
        reducedMotion: profile.reducedMotion,
        locale: profile.locale,
      });
      const page = await context.newPage();
      try {
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
        const status = response?.status() ?? null;
        const audit = await auditPage(page, profile);
        record.profiles.push({
          name: profile.name,
          status,
          containers: audit.containers,
          visibleTextElements: audit.visibleTextElements,
          guardVersion: audit.guardVersion,
        });
        record.textElements = Math.max(record.textElements, audit.visibleTextElements);
        record.contrastViolations.push(...audit.contrastViolations.map((item) => ({ profile: profile.name, ...item })));
        record.hiddenOrClipped.push(...audit.hiddenOrClipped.map((item) => ({ profile: profile.name, ...item })));
        if (status !== null && status >= 400) record.failedProfiles.push({ profile: profile.name, status });
        if (audit.guardVersion !== 'v283') record.failedProfiles.push({ profile: profile.name, error: 'adaptive contrast guard did not initialize' });
      } catch (error) {
        record.failedProfiles.push({ profile: profile.name, error: String(error) });
      } finally {
        await context.close();
      }
    }
    results[index] = record;
  }
}

await Promise.all(Array.from({ length: concurrency }, () => worker()));
await browser.close();

const pagesWithContainers = results.filter((item) => item.profiles.some((profile) => profile.containers > 0));
const violatingPages = results.filter((item) => item.contrastViolations.length > 0);
const hiddenPages = results.filter((item) => item.hiddenOrClipped.length > 0);
const failedPages = results.filter((item) => item.failedProfiles.length > 0);
const report = {
  contract: 283,
  requirement: 'Adaptive WCAG AA text/background contrast across header, hero, navigation, breadcrumb, search and footer surfaces',
  generatedAt: new Date().toISOString(),
  profiles: profiles.map(({ name, viewport, colorScheme, direction, media, reducedMotion, prefersContrast }) => ({
    name, viewport, colorScheme, direction, media, reducedMotion, prefersContrast,
  })),
  htmlPages: htmlFiles.length,
  pagesWithHeroOrHeader: pagesWithContainers.length,
  auditedTextElements: results.reduce((sum, item) => sum + item.textElements, 0),
  contrastViolatingPages: violatingPages.length,
  contrastViolations: results.reduce((sum, item) => sum + item.contrastViolations.length, 0),
  pagesWithHiddenOrClippedText: hiddenPages.length,
  failedPages: failedPages.length,
  results,
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'hero-header-contrast-audit-v283.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ ...report, results: undefined }, null, 2));
if (report.contrastViolations || report.pagesWithHiddenOrClippedText || report.failedPages) process.exitCode = 1;
