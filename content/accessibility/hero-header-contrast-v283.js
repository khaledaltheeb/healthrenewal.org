/* v283 — computed-style hero/header contrast guard; v289 deterministic late-style recovery. */
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
    return {
      r: Math.max(0, Math.min(255, parts[0])),
      g: Math.max(0, Math.min(255, parts[1])),
      b: Math.max(0, Math.min(255, parts[2])),
      a: Number.isFinite(parts[3]) ? Math.max(0, Math.min(1, parts[3])) : 1,
    };
  }

  function composite(front, back) {
    const alpha = front.a + back.a * (1 - front.a);
    if (alpha <= 0) return { ...WHITE };
    return {
      r: (front.r * front.a + back.r * back.a * (1 - front.a)) / alpha,
      g: (front.g * front.a + back.g * back.a * (1 - front.a)) / alpha,
      b: (front.b * front.a + back.b * back.a * (1 - front.a)) / alpha,
      a: alpha,
    };
  }

  function luminance({ r, g, b }) {
    const c = [r, g, b].map((channel) => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722;
  }

  function ratio(a, b) {
    const first = luminance(a);
    const second = luminance(b);
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
  }

  function cssColor(color) {
    return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`;
  }

  function effectiveBackground(element) {
    const chain = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const style = getComputedStyle(current);
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0.001) chain.push(color);
      if (color?.a >= 0.999) break;
      current = current.parentElement;
    }
    let background = { ...WHITE };
    for (let index = chain.length - 1; index >= 0; index -= 1) background = composite(chain[index], background);
    return background;
  }

  function visible(element) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return Boolean((element.innerText || element.value || element.textContent || '').trim())
      && style.display !== 'none'
      && style.visibility !== 'hidden'
      && Number(style.opacity || 1) > 0.05
      && rect.width > 0
      && rect.height > 0;
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

  function stabilizeImageSurface(surface) {
    const style = getComputedStyle(surface);
    if (!style.backgroundImage || style.backgroundImage === 'none') return declaredSurface(surface);
    let choice = declaredSurface(surface);
    if (!choice) {
      const own = parseColor(style.backgroundColor);
      if (own && own.a >= 0.55) choice = luminance(composite(own, WHITE)) >= 0.55 ? 'light' : 'dark';
      else {
        const sample = [...surface.querySelectorAll(TEXT_SELECTOR)].find(visible);
        const text = sample ? parseColor(getComputedStyle(sample).color) : null;
        choice = text && luminance(text) < 0.45 ? 'light' : 'dark';
      }
    }
    surface.classList.toggle('hh-overlay-light', choice === 'light');
    surface.classList.toggle('hh-overlay-dark', choice === 'dark');
    surface.dataset.hhAdaptiveOverlay = choice;
    return choice;
  }

  function ownDarkControl(element, style) {
    if (!element.matches(CONTROL_SELECTOR)) return false;
    const own = parseColor(style.backgroundColor);
    return Boolean(own && own.a >= 0.75 && luminance(composite(own, WHITE)) < 0.35);
  }

  function applyColor(element, target, background, source) {
    const light = target === LIGHT_TEXT;
    for (const name of [...OWN_CLASSES, ...LEGACY_CLASSES]) element.classList.remove(name);
    element.classList.add(light ? 'hh-text-on-dark' : 'hh-text-on-light');
    const value = cssColor(target);
    element.style.setProperty('color', value, 'important');
    element.style.setProperty('-webkit-text-fill-color', value, 'important');
    element.style.setProperty('text-shadow', light ? '0 1px 2px rgba(0,0,0,.38)' : 'none', 'important');
    element.dataset.hhInlineContrast = 'true';
    element.dataset.hhExpectedColor = value;
    element.dataset.hhContrast = ratio(target, background).toFixed(2);
    element.dataset.hhContrastSource = source;
    element.dataset.hhScan = String(scanId);
  }

  function resolveElement(element, surfaceType) {
    if (!visible(element)) return;
    const style = getComputedStyle(element);
    const foregroundRaw = parseColor(style.color);
    if (!foregroundRaw) return;
    const background = effectiveBackground(element);
    const threshold = thresholdFor(element, style);
    const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, background) : foregroundRaw;
    const currentRatio = ratio(foreground, background);

    if (surfaceType === 'light' && !ownDarkControl(element, style)) {
      if (currentRatio + 0.001 < threshold || luminance(foreground) > 0.55) applyColor(element, DARK_TEXT, background, 'light-surface');
      return;
    }
    if (surfaceType === 'dark' && !element.matches(CONTROL_SELECTOR)) {
      if (currentRatio + 0.001 < threshold || luminance(foreground) < 0.45) applyColor(element, LIGHT_TEXT, background, 'dark-surface');
      return;
    }
    if (currentRatio + 0.001 >= threshold) {
      element.dataset.hhContrast = currentRatio.toFixed(2);
      element.dataset.hhContrastSource = 'computed-pass';
      return;
    }
    const lightRatio = ratio(LIGHT_TEXT, background);
    const darkRatio = ratio(DARK_TEXT, background);
    applyColor(element, lightRatio >= darkRatio ? LIGHT_TEXT : DARK_TEXT, background, 'computed-fail');
  }

  function scan() {
    scheduled = false;
    scanId += 1;
    const surfaces = [...document.querySelectorAll(SURFACE_SELECTOR)];
    for (const surface of surfaces) {
      const type = stabilizeImageSurface(surface) || declaredSurface(surface);
      if (type) surface.dataset.hhDeclaredSurface = type;
      if (surface.matches(TEXT_SELECTOR)) resolveElement(surface, type);
      surface.querySelectorAll(TEXT_SELECTOR).forEach((element) => resolveElement(element, type));
    }
    document.documentElement.dataset.heroHeaderContrast = 'v283';
    document.documentElement.dataset.heroHeaderContrastScan = String(scanId);
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(scan);
  }

  function resolvedAndPassing(element) {
    if (!(element instanceof Element) || element.dataset.hhInlineContrast !== 'true') return false;
    if (!visible(element)) return true;
    const style = getComputedStyle(element);
    const foreground = parseColor(style.color);
    if (!foreground) return false;
    return ratio(foreground, effectiveBackground(element)) + 0.001 >= thresholdFor(element, style);
  }

  window.__heroHeaderContrastV283 = { scan, version: 289, adaptiveImageSurfaces: true };
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
  }).observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['class','style','data-surface','data-theme','aria-expanded','aria-disabled'],
  });
})();
