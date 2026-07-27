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
  },
  {
    name: 'mobile-rtl-light-reduced',
    viewport: { width: 390, height: 844 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'light',
    media: 'screen',
    reducedMotion: 'reduce',
  },
  {
    name: 'desktop-rtl-dark-high-contrast',
    viewport: { width: 1440, height: 1000 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'dark',
    media: 'screen',
    reducedMotion: 'reduce',
    forcedColors: 'none',
  },
  {
    name: 'print-rtl',
    viewport: { width: 1024, height: 1400 },
    locale: 'ar',
    direction: 'rtl',
    colorScheme: 'light',
    media: 'print',
    reducedMotion: 'reduce',
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
    forcedColors: profile.forcedColors || 'none',
  });
  await page.evaluate((direction) => {
    document.documentElement.dir = direction;
  }, profile.direction);

  await page.waitForFunction(
    () => document.documentElement.dataset.heroHeaderContrast === 'v283',
    { timeout: 5000 },
  ).catch(() => {});
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));

  return page.evaluate(() => {
    const CONTAINER_SELECTOR = [
      'header',
      '[role="banner"]',
      '[class*="hero"]', '[class*="Hero"]',
      '[id*="hero"]', '[id*="Hero"]',
      '[class*="masthead"]',
      '[class*="banner"]', '[class*="Banner"]',
      '[class*="breadcrumb"]', '[class*="Breadcrumb"]',
    ].join(',');
    const TEXT_SELECTOR = [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'li', 'dt', 'dd', 'small', 'strong', 'em', 'span', 'label', 'blockquote',
      'a', 'button', '[role="button"]', 'summary', 'input', 'select', 'textarea',
    ].join(',');

    function parseColor(value) {
      if (!value || value === 'transparent') return null;
      const match = String(value).match(/rgba?\(([^)]+)\)/i);
      if (!match) return null;
      const parts = match[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
      if (parts.length < 3 || parts.slice(0, 3).some(Number.isNaN)) return null;
      return {
        r: Math.max(0, Math.min(255, parts[0])),
        g: Math.max(0, Math.min(255, parts[1])),
        b: Math.max(0, Math.min(255, parts[2])),
        a: Number.isFinite(parts[3]) ? Math.max(0, Math.min(1, parts[3])) : 1,
      };
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
      const l1 = luminance(a);
      const l2 = luminance(b);
      return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    }

    function colorString(color) {
      return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`;
    }

    function selectorFor(element) {
      return `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ''}${element.classList.length ? `.${[...element.classList].slice(0, 5).join('.')}` : ''}`;
    }

    function visible(element) {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none'
        && style.visibility !== 'hidden'
        && Number(style.opacity || 1) > 0.05
        && rect.width > 0
        && rect.height > 0;
    }

    function effectiveBackground(element) {
      const layers = [];
      let node = element;
      let hasImageOrGradient = false;
      let stableSurface = false;
      let imageBearer = null;

      while (node && node.nodeType === Node.ELEMENT_NODE) {
        const style = getComputedStyle(node);
        const image = style.backgroundImage;
        if (image && image !== 'none') {
          hasImageOrGradient = true;
          if (!imageBearer) imageBearer = selectorFor(node);
        }

        const parsed = parseColor(style.backgroundColor);
        if (parsed && parsed.a > 0.001) {
          layers.push({ selector: selectorFor(node), color: style.backgroundColor, alpha: parsed.a });
          if (parsed.a >= 0.72 || node.matches('.hh-overlay-dark,.hh-overlay-light,[data-surface="light"],[data-surface="dark"]')) {
            stableSurface = true;
          }
          if (parsed.a >= 0.999) break;
        }
        node = node.parentElement;
      }

      let background = { r: 255, g: 255, b: 255, a: 1 };
      for (let index = layers.length - 1; index >= 0; index -= 1) {
        const parsed = parseColor(layers[index].color);
        if (parsed) background = composite(parsed, background);
      }
      return { color: background, hasImageOrGradient, stableSurface, imageBearer, layers };
    }

    function isLargeText(style) {
      const fontSize = Number.parseFloat(style.fontSize) || 0;
      const fontWeight = Number.parseInt(style.fontWeight, 10) || 400;
      return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    }

    function isUiControl(element) {
      return element.matches('button,[role="button"],input,select,textarea,summary,a.btn,a.button,[class*="button"],[class*="Button"]');
    }

    const containers = [...document.querySelectorAll(CONTAINER_SELECTOR)];
    const nodes = [...new Set(containers.flatMap((container) => [
      ...(container.matches(TEXT_SELECTOR) ? [container] : []),
      ...container.querySelectorAll(TEXT_SELECTOR),
    ]))].filter(visible);

    const contrastViolations = [];
    const hiddenOrClipped = [];

    for (const element of nodes) {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const selector = selectorFor(element);
      const text = (element.value || element.innerText || element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
      const foregroundRaw = parseColor(style.color) || { r: 0, g: 0, b: 0, a: 1 };
      const background = effectiveBackground(element);
      const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, background.color) : foregroundRaw;
      const contrastRatio = ratio(foreground, background.color);
      const threshold = isUiControl(element) || isLargeText(style) ? 3 : 4.5;
      const indeterminateBackground = background.hasImageOrGradient && !background.stableSurface;

      if (contrastRatio + 0.001 < threshold || indeterminateBackground) {
        contrastViolations.push({
          selector,
          text,
          foreground: colorString(foreground),
          effectiveBackground: colorString(background.color),
          contrastRatio: Number(contrastRatio.toFixed(2)),
          threshold,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          backgroundImage: style.backgroundImage,
          imageBearer: background.imageBearer,
          stableSurface: background.stableSurface,
          indeterminateBackground,
          reason: indeterminateBackground
            ? 'background image/gradient without a stable readable surface or overlay'
            : 'contrast ratio below WCAG AA threshold',
        });
      }

      const clippedX = element.scrollWidth > element.clientWidth + 1
        && !['visible', 'clip'].includes(style.overflowX);
      const clippedY = element.scrollHeight > element.clientHeight + 1
        && !['visible', 'clip'].includes(style.overflowY);
      const lineClamped = style.webkitLineClamp
        && style.webkitLineClamp !== 'none'
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
      count: nodes.length,
      contrastViolations,
      hidden: hiddenOrClipped,
      runtimeContract: document.documentElement.dataset.heroHeaderContrast || null,
    };
  });
}

async function worker() {
  while (true) {
    const index = cursor++;
    if (index >= htmlFiles.length) break;
    const file = htmlFiles[index];
    const rel = path.relative(siteDir, file).split(path.sep).join('/');
    const url = toUrl(file);
    const record = {
      path: rel,
      url,
      profiles: [],
      textElements: 0,
      contrastViolations: [],
      hidden: [],
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
          textElements: audit.count,
          runtimeContract: audit.runtimeContract,
        });
        record.textElements = Math.max(record.textElements, audit.count);
        record.contrastViolations.push(...audit.contrastViolations.map((item) => ({ profile: profile.name, ...item })));
        record.hidden.push(...audit.hidden.map((item) => ({ profile: profile.name, ...item })));
        if (status !== null && status >= 400) record.failedProfiles.push({ profile: profile.name, status });
        if (audit.runtimeContract !== 'v283') {
          record.failedProfiles.push({ profile: profile.name, error: 'adaptive hero/header runtime contract missing' });
        }
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

const pagesWithContainers = results.filter((item) => item.textElements > 0);
const violatingPages = results.filter((item) => item.contrastViolations.length > 0);
const hiddenPages = results.filter((item) => item.hidden.length > 0);
const failedPages = results.filter((item) => item.failedProfiles.length > 0);
const report = {
  contract: 283,
  requirement: 'Adaptive WCAG AA text/background contrast across hero and header surfaces',
  generatedAt: new Date().toISOString(),
  profiles: profiles.map(({ name, viewport, colorScheme, direction, media, reducedMotion }) => ({
    name, viewport, colorScheme, direction, media, reducedMotion,
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
if (report.contrastViolations || report.pagesWithHiddenOrClippedText || report.failedPages) {
  process.exitCode = 1;
}
