/* v283 — computed-style hero/header contrast guard; v290 element-background-first recovery. */
(() => {
  'use strict';

  const SURFACE_SELECTOR = [
    'header','[role="banner"]','nav','[role="navigation"]','[role="search"]',
    '[class*="hero"]','[class*="Hero"]','[id*="hero"]','[id*="Hero"]',
    '[class*="banner"]','[class*="Banner"]','[class*="masthead"]',
    '[class*="breadcrumb"]','[class*="Breadcrumb"]','footer','[role="contentinfo"]','.site-footer',
  ].join(',');
  const TEXT_SELECTOR = [
    'h1','h2','h3','h4','h5','h6','p','li','dt','dd','small','strong','em','span','label','blockquote','a',
    'button','[role="button"]','input','select','textarea','option','summary','[tabindex]',
  ].join(',');
  const CONTROL_SELECTOR = 'button,[role="button"],input,select,textarea,summary,[tabindex],a.btn,a.button,[class*="button"],[class*="Button"]';
  const OWN_CLASSES = ['hh-text-on-dark', 'hh-text-on-light'];
  const LEGACY_CLASSES = ['auto-contrast-light', 'auto-contrast-dark'];
  const WHITE = { r: 255, g: 255, b: 255, a: 1 };
  const LIGHT_TEXT = { r: 248, g: 252, b: 255, a: 1 };
  const DARK_TEXT = { r: 7, g: 25, b: 28, a: 1 };
  let scheduled = false;
  let scanId = 0;

  document.documentElement.dataset.heroHeaderContrast = 'v283';

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
    return [...String(value).matchAll(/rgba?\([^)]+\)/gi)].map((match) => parseColor(match[0])).filter(Boolean);
  }

  function composite(front, back) {
    const alpha = front.a + back.a * (1 - front.a);
    if (alpha <= 0) return { ...WHITE };
    return { r: (front.r * front.a + back.r * back.a * (1 - front.a)) / alpha, g: (front.g * front.a + back.g * back.a * (1 - front.a)) / alpha, b: (front.b * front.a + back.b * back.a * (1 - front.a)) / alpha, a: alpha };
  }

  function luminance({ r, g, b }) {
    const channels = [r, g, b].map((channel) => { const value = channel / 255; return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4; });
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  }

  function ratio(a, b) { const first = luminance(a); const second = luminance(b); return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05); }
  function cssColor(color) { return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`; }

  function visible(element) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return Boolean((element.innerText || element.value || element.textContent || '').trim()) && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0.05 && rect.width > 0 && rect.height > 0;
  }

  function thresholdFor(element, style) {
    const size = Number.parseFloat(style.fontSize) || 16;
    const weight = Number.parseInt(style.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    return large || element.matches(CONTROL_SELECTOR) ? 3 : 4.5;
  }

  function declaredSurface(surface) {
    if (surface.matches('[data-surface="light"],[data-theme="light"],.surface-light,.theme-light,.hh-surface-light,.hh-overlay-light')) return 'light';
    if (surface.matches('[data-surface="dark"],[data-theme="dark"],.surface-dark,.theme-dark,.hh-surface-dark,.hh-overlay-dark')) return 'dark';
    return null;
  }

  function targetForCandidates(candidates) {
    const lightMinimum = Math.min(...candidates.map((background) => ratio(LIGHT_TEXT, background)));
    const darkMinimum = Math.min(...candidates.map((background) => ratio(DARK_TEXT, background)));
    return darkMinimum >= lightMinimum ? 'light' : 'dark';
  }

  function stabilizeImageSurface(surface) {
    const style = getComputedStyle(surface);
    if (!style.backgroundImage || style.backgroundImage === 'none') return declaredSurface(surface);
    let choice = declaredSurface(surface);
    if (!choice) {
      const own = parseColor(style.backgroundColor);
      const base = own && own.a > 0.001 ? composite(own, WHITE) : { ...WHITE };
      const gradient = colorsFromGradient(style.backgroundImage).map((color) => composite(color, base));
      if (gradient.length) choice = targetForCandidates(gradient);
      else if (own && own.a >= 0.55) choice = luminance(base) >= 0.45 ? 'light' : 'dark';
      else choice = 'dark';
    }
    surface.classList.toggle('hh-overlay-light', choice === 'light');
    surface.classList.toggle('hh-overlay-dark', choice === 'dark');
    surface.dataset.hhAdaptiveOverlay = choice;
    return choice;
  }

  function backgroundInfo(element) {
    const chain = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const style = getComputedStyle(current);
      chain.push({ color: parseColor(style.backgroundColor), image: style.backgroundImage, guarded: current.matches('.hh-overlay-dark,.hh-overlay-light,[data-surface="light"],[data-surface="dark"],[data-theme="light"],[data-theme="dark"],.surface-light,.surface-dark,.theme-light,.theme-dark,.hh-surface-light,.hh-surface-dark') });
      if (chain.at(-1).color?.a >= 0.999) break;
      current = current.parentElement;
    }

    let solid = { ...WHITE };
    for (let index = chain.length - 1; index >= 0; index -= 1) if (chain[index].color?.a > 0.001) solid = composite(chain[index].color, solid);

    const imageLayer = chain.find((layer) => layer.image && layer.image !== 'none' && !layer.guarded);
    if (!imageLayer) return { candidates: [solid], unresolvedImage: false };
    const gradientColors = colorsFromGradient(imageLayer.image);
    if (gradientColors.length) return { candidates: gradientColors.map((color) => composite(color, solid)), unresolvedImage: false };
    return { candidates: [solid], unresolvedImage: /url\(/i.test(imageLayer.image) };
  }

  function minimumRatio(foreground, candidates) { return Math.min(...candidates.map((background) => ratio(foreground.a < 1 ? composite(foreground, background) : foreground, background))); }

  function applyColor(element, target, candidates, source) {
    const light = target === LIGHT_TEXT;
    for (const name of [...OWN_CLASSES, ...LEGACY_CLASSES]) element.classList.remove(name);
    element.classList.add(light ? 'hh-text-on-dark' : 'hh-text-on-light');
    const value = cssColor(target);
    element.style.setProperty('color', value, 'important');
    element.style.setProperty('-webkit-text-fill-color', value, 'important');
    element.style.setProperty('text-shadow', light ? '0 1px 2px rgba(0,0,0,.38)' : 'none', 'important');
    element.dataset.hhInlineContrast = 'true';
    element.dataset.hhExpectedColor = value;
    element.dataset.hhContrast = minimumRatio(target, candidates).toFixed(2);
    element.dataset.hhContrastSource = source;
    element.dataset.hhScan = String(scanId);
  }

  function resolveElement(element) {
    if (!visible(element)) return;
    for (const name of LEGACY_CLASSES) element.classList.remove(name);
    let style = getComputedStyle(element);
    let foregroundRaw = parseColor(style.color);
    if (!foregroundRaw) return;
    let info = backgroundInfo(element);
    const threshold = thresholdFor(element, style);
    let currentRatio = minimumRatio(foregroundRaw, info.candidates);

    if (info.unresolvedImage) {
      const imageSurface = element.closest(SURFACE_SELECTOR);
      if (imageSurface) {
        stabilizeImageSurface(imageSurface);
        style = getComputedStyle(element);
        foregroundRaw = parseColor(style.color) || foregroundRaw;
        info = backgroundInfo(element);
        currentRatio = minimumRatio(foregroundRaw, info.candidates);
      }
    }

    if (!info.unresolvedImage && currentRatio + 0.001 >= threshold) {
      element.dataset.hhContrast = currentRatio.toFixed(2);
      element.dataset.hhContrastSource = 'computed-pass';
      element.dataset.hhScan = String(scanId);
      return;
    }

    const lightRatio = minimumRatio(LIGHT_TEXT, info.candidates);
    const darkRatio = minimumRatio(DARK_TEXT, info.candidates);
    applyColor(element, lightRatio >= darkRatio ? LIGHT_TEXT : DARK_TEXT, info.candidates, info.unresolvedImage ? 'image-overlay-fallback' : 'computed-worst-background');
  }

  function scan() {
    scheduled = false;
    scanId += 1;
    const surfaces = [...document.querySelectorAll(SURFACE_SELECTOR)];
    for (const surface of surfaces) {
      const type = stabilizeImageSurface(surface) || declaredSurface(surface);
      if (type) surface.dataset.hhDeclaredSurface = type;
      if (surface.matches(TEXT_SELECTOR)) resolveElement(surface);
      surface.querySelectorAll(TEXT_SELECTOR).forEach(resolveElement);
    }
    document.documentElement.dataset.heroHeaderContrast = 'v283';
    document.documentElement.dataset.heroHeaderContrastScan = String(scanId);
  }

  function schedule() { if (scheduled) return; scheduled = true; requestAnimationFrame(scan); }

  function resolvedAndPassing(element) {
    if (!(element instanceof Element) || element.dataset.hhInlineContrast !== 'true') return false;
    if (!visible(element)) return true;
    const style = getComputedStyle(element);
    const foreground = parseColor(style.color);
    if (!foreground) return false;
    const info = backgroundInfo(element);
    return !info.unresolvedImage && minimumRatio(foreground, info.candidates) + 0.001 >= thresholdFor(element, style);
  }

  window.__heroHeaderContrastV283 = { scan, version: 290, adaptiveImageSurfaces: true, gradientStops: true };
  scan();
  for (const delay of [0, 50, 250, 1000]) setTimeout(schedule, delay);
  document.addEventListener('DOMContentLoaded', schedule, { once: true });
  window.addEventListener('load', schedule, { once: true });
  window.addEventListener('pageshow', schedule);
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('beforeprint', schedule);
  document.addEventListener('focusin', schedule);
  document.addEventListener('pointerover', schedule, { passive: true });
  for (const query of ['(prefers-color-scheme: dark)', '(prefers-contrast: more)']) {
    const media = matchMedia(query);
    if (media.addEventListener) media.addEventListener('change', schedule);
    else media.addListener(schedule);
  }

  new MutationObserver((mutations) => {
    const shouldScan = mutations.some((mutation) => {
      if (mutation.type === 'childList') return true;
      const target = mutation.target;
      if (!(target instanceof Element)) return true;
      if (target.dataset.hhAdaptiveOverlay && ['class', 'style'].includes(mutation.attributeName)) return !declaredSurface(target);
      return !resolvedAndPassing(target);
    });
    if (shouldScan) schedule();
  }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class','style','data-surface','data-theme','aria-expanded','aria-disabled'] });
})();
