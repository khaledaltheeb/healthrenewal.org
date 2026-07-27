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

  return page.evaluate(() => {
    const CONTAINER_SELECTOR = [
      'header',
      '[role="banner"]',
      '.hero',
      '[class*="hero"]',
      '[class*="Hero"]',
      '[id*="hero"]',
      '[id*="Hero"]',
      '[class*="masthead"]',
      '[class*="banner"]',
      '[class*="Banner"]',
      '[class*="breadcrumb"]',
      '[class*="Breadcrumb"]',
    ].join(',');

    function parseColor(value) {
      if (!value || value === 'transparent') return null;
      const match = value.match(/rgba?\(([^)]+)\)/i);
      if (!match) return null;
      const parts = match[1].split(',').map((part) => Number.parseFloat(part.trim()));
      if (parts.length < 3 || parts.slice(0, 3).some(Number.isNaN)) return null;
      return {
        r: Math.max(0, Math.min(255, parts[0])),
        g: Math.max(0, Math.min(255, parts[1])),
        b: Math.max(0, Math.min(255, parts[2])),
        a: parts.length >= 4 && Number.isFinite(parts[3]) ? Math.max(0, Math.min(1, parts[3])) : 1,
      };
    }

    function composite(fg, bg) {
      const alpha = fg.a + bg.a * (1 - fg.a);
      if (alpha <= 0) return { r: 255, g: 255, b: 255, a: 1 };
      return {
        r: (fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / alpha,
        g: (fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / alpha,
        b: (fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / alpha,
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

    function effectiveBackground(el) {
      let current = el;
      let accumulated = { r: 255, g: 255, b: 255, a: 1 };
      let hasImageOrGradient = false;
      const layers = [];

      while (current && current.nodeType === Node.ELEMENT_NODE) {
        const style = getComputedStyle(current);
        const image = style.backgroundImage;
        if (image && image !== 'none') hasImageOrGradient = true;
        const parsed = parseColor(style.backgroundColor);
        if (parsed && parsed.a > 0) {
          layers.push({ selector: current.tagName.toLowerCase(), color: style.backgroundColor });
          accumulated = composite(parsed, accumulated);
          if (parsed.a >= 0.999) break;
        }
        current = current.parentElement;
      }

      return { color: accumulated, hasImageOrGradient, layers };
    }

    function isLargeText(style) {
      const fontSize = Number.parseFloat(style.fontSize) || 0;
      const fontWeight = Number.parseInt(style.fontWeight, 10) || 400;
      return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    }

    function isUiControl(el) {
      return el.matches('button, [role="button"], input, select, textarea, a.btn, a.button, [class*="button"], [class*="Button"]');
    }

    function selectorFor(el) {
      return `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${el.classList.length ? `.${[...el.classList].slice(0, 4).join('.')}` : ''}`;
    }

    const containers = [...document.querySelectorAll(CONTAINER_SELECTOR)];
    const nodes = [...new Set(containers.flatMap((container) => [container, ...container.querySelectorAll('*')]))]
      .filter((el) => (el.textContent || '').trim().length > 0)
      .filter((el) => !['script', 'style', 'noscript', 'svg', 'path', 'template'].includes(el.tagName.toLowerCase()));

    const contrastViolations = [];
    const hidden = [];
    for (const el of nodes) {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const selector = selectorFor(el);
      const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
      const foregroundRaw = parseColor(style.color) || { r: 0, g: 0, b: 0, a: 1 };
      const background = effectiveBackground(el);
      const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, background.color) : foregroundRaw;
      const contrastRatio = ratio(foreground, background.color);
      const threshold = isUiControl(el) || isLargeText(style) ? 3 : 4.5;
      const indeterminateImage = background.hasImageOrGradient && background.layers.length === 0;

      if (contrastRatio + 0.001 < threshold || indeterminateImage) {
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
          indeterminateImage,
          reason: indeterminateImage ? 'background image/gradient without an opaque readable surface' : 'contrast ratio below WCAG AA threshold',
        });
      }

      const clippedX = el.scrollWidth > el.clientWidth + 1 && !['visible', 'clip'].includes(style.overflowX);
      const clippedY = el.scrollHeight > el.clientHeight + 1 && !['visible', 'clip'].includes(style.overflowY);
      const invisible = style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0 || rect.width === 0 || rect.height === 0;
      const lineClamped = style.webkitLineClamp && style.webkitLineClamp !== 'none' && Number(style.webkitLineClamp) > 0;
      if (invisible || clippedX || clippedY || lineClamped) {
        hidden.push({
          selector,
          text,
          invisible,
          clippedX,
          clippedY,
          lineClamped,
          overflowX: style.overflowX,
          overflowY: style.overflowY,
          width: rect.width,
          height: rect.height,
        });
      }
    }

    return { count: nodes.length, contrastViolations, hidden };
  });
}

async function worker() {
  while (true) {
    const index = cursor++;
    if (index >= htmlFiles.length) break;
    const file = htmlFiles[index];
    const rel = path.relative(siteDir, file).split(path.sep).join('/');
    const url = toUrl(file);
    const record = { path: rel, url, profiles: [], textElements: 0, contrastViolations: [], hidden: [], failedProfiles: [] };

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
        record.profiles.push({ name: profile.name, status, textElements: audit.count });
        record.textElements = Math.max(record.textElements, audit.count);
        record.contrastViolations.push(...audit.contrastViolations.map((item) => ({ profile: profile.name, ...item })));
        record.hidden.push(...audit.hidden.map((item) => ({ profile: profile.name, ...item })));
        if (status !== null && status >= 400) record.failedProfiles.push({ profile: profile.name, status });
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
  profiles: profiles.map(({ name, viewport, colorScheme, direction, media, reducedMotion }) => ({ name, viewport, colorScheme, direction, media, reducedMotion })),
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
