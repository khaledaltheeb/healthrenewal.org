/* v285 — computed-style adaptive surface contrast guard. */
(() => {
  'use strict';

  const SURFACE_SELECTOR = [
    'header',
    '[role="banner"]',
    'nav',
    '[role="navigation"]',
    '[role="search"]',
    '[class*="hero"]', '[class*="Hero"]',
    '[id*="hero"]', '[id*="Hero"]',
    '[class*="banner"]', '[class*="Banner"]',
    '[class*="masthead"]',
    '[class*="breadcrumb"]', '[class*="Breadcrumb"]',
    'footer',
    '[role="contentinfo"]',
    '.site-footer',
  ].join(',');

  const TEXT_SELECTOR = [
    'h1','h2','h3','h4','h5','h6','p','li','dt','dd','small','strong','em','span','label','blockquote','a',
    'button','[role="button"]','input','select','textarea','option','summary','[tabindex]',
  ].join(',');

  const CLASS_NAMES = [
    'hh-text-on-dark',
    'hh-text-on-light',
    'auto-contrast-light',
    'auto-contrast-dark',
  ];

  const WHITE = { r: 255, g: 255, b: 255, a: 1 };
  const LIGHT_TEXT = { r: 248, g: 252, b: 255, a: 1 };
  const DARK_TEXT = { r: 16, g: 42, b: 46, a: 1 };
  let scheduled = false;

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
    const channels = [r, g, b].map((channel) => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  }

  function contrast(a, b) {
    const first = luminance(a);
    const second = luminance(b);
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
  }

  function effectiveBackground(element) {
    let current = element;
    let background = { ...WHITE };
    const layers = [];
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const style = getComputedStyle(current);
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0.001) {
        layers.push({ element: current, color });
        background = composite(color, background);
        if (color.a >= 0.999) break;
      }
      current = current.parentElement;
    }
    return { color: background, layers };
  }

  function visible(element) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return Boolean((element.innerText || element.textContent || '').trim())
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
    const ui = element.matches('button,[role="button"],input,select,textarea,summary,[tabindex],a.btn,a.button,[class*="button"],[class*="Button"]');
    return large || ui ? 3 : 4.5;
  }

  function hasResolution(element) {
    return CLASS_NAMES.some((name) => element.classList.contains(name));
  }

  function resolveElement(element) {
    if (!visible(element)) return;

    const style = getComputedStyle(element);
    const foregroundRaw = parseColor(style.color);
    if (!foregroundRaw) return;
    const background = effectiveBackground(element).color;
    const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, background) : foregroundRaw;
    const threshold = thresholdFor(element, style);
    const currentRatio = contrast(foreground, background);

    /* Keep a correction once applied. The former implementation removed the
     * class as soon as the corrected value passed, which immediately restored
     * the original failing color and created an observer-driven oscillation. */
    if (currentRatio + 0.001 >= threshold) {
      element.dataset.hhContrast = currentRatio.toFixed(2);
      return;
    }

    const lightRatio = contrast(LIGHT_TEXT, background);
    const darkRatio = contrast(DARK_TEXT, background);
    const useLight = lightRatio >= darkRatio;
    const targetClass = useLight ? 'hh-text-on-dark' : 'hh-text-on-light';
    const oppositeClass = useLight ? 'hh-text-on-light' : 'hh-text-on-dark';

    if (!element.classList.contains(targetClass) || element.classList.contains(oppositeClass)) {
      element.classList.remove(oppositeClass, 'auto-contrast-light', 'auto-contrast-dark');
      element.classList.add(targetClass);
    }
    element.dataset.hhContrast = Math.max(lightRatio, darkRatio).toFixed(2);
  }

  function scan() {
    scheduled = false;
    const surfaces = [...document.querySelectorAll(SURFACE_SELECTOR)];
    for (const surface of surfaces) {
      if (surface.matches(TEXT_SELECTOR)) resolveElement(surface);
      surface.querySelectorAll(TEXT_SELECTOR).forEach(resolveElement);
    }
    document.documentElement.dataset.heroHeaderContrast = 'v285';
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    if ('requestIdleCallback' in window) requestIdleCallback(scan, { timeout: 350 });
    else requestAnimationFrame(scan);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', schedule, { once: true });
  } else {
    schedule();
  }

  window.addEventListener('load', schedule, { once: true });
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
    const externalChange = mutations.some((mutation) => {
      if (mutation.type !== 'attributes' || mutation.attributeName !== 'class') return true;
      return !hasResolution(mutation.target);
    });
    if (externalChange) schedule();
  }).observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['class', 'style', 'data-surface', 'data-theme', 'aria-expanded', 'aria-disabled'],
  });

  window.__heroHeaderContrastV283 = {
    scan,
    classes: CLASS_NAMES.slice(),
    version: 285,
  };
})();
