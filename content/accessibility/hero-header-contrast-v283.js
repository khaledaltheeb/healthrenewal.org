/* v283 — computed-style hero/header contrast guard; v288 adaptive image/gradient surfaces. */
(() => {
  'use strict';

  const TOP_SURFACE_SELECTOR = [
    'header','[role="banner"]','nav','[role="navigation"]','[role="search"]',
    '[class*="hero"]','[class*="Hero"]','[id*="hero"]','[id*="Hero"]',
    '[class*="banner"]','[class*="Banner"]','[class*="masthead"]',
    '[class*="breadcrumb"]','[class*="Breadcrumb"]',
  ].join(',');
  const SURFACE_SELECTOR = [TOP_SURFACE_SELECTOR, 'footer','[role="contentinfo"]','.site-footer'].join(',');
  const TEXT_SELECTOR = [
    'h1','h2','h3','h4','h5','h6','p','li','dt','dd','small','strong','em','span','label','blockquote','a',
    'button','[role="button"]','input','select','textarea','option','summary','[tabindex]',
  ].join(',');
  const CLASS_NAMES = ['hh-text-on-dark','hh-text-on-light','auto-contrast-light','auto-contrast-dark'];
  const KNOWN_LIGHT_ROUTE_SUFFIXES = [
    '/terms/psychological-well-being/',
    '/terms/psychological-well-being/index.html',
  ];
  const WHITE = { r: 255, g: 255, b: 255, a: 1 };
  const LIGHT_TEXT = { r: 248, g: 252, b: 255, a: 1 };
  const DARK_TEXT = { r: 7, g: 25, b: 28, a: 1 };
  let scheduled = false;
  let applying = false;

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

  function cssColor(color) {
    return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`;
  }

  function effectiveBackground(element) {
    let current = element;
    const chain = [];
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const style = getComputedStyle(current);
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0.001) chain.push(color);
      if (color?.a >= 0.999) break;
      current = current.parentElement;
    }
    let background = { ...WHITE };
    for (let index = chain.length - 1; index >= 0; index -= 1) {
      background = composite(chain[index], background);
    }
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
    const ui = element.matches('button,[role="button"],input,select,textarea,summary,[tabindex],a.btn,a.button,[class*="button"],[class*="Button"]');
    return large || ui ? 3 : 4.5;
  }

  function hasResolution(element) {
    return CLASS_NAMES.some((name) => element.classList.contains(name))
      || element.dataset.hhInlineContrast === 'true';
  }

  function isKnownLightRoute() {
    const pathname = window.location.pathname.replace(/\/{2,}/g, '/');
    return KNOWN_LIGHT_ROUTE_SUFFIXES.some((suffix) => pathname.endsWith(suffix));
  }

  function hasOwnDarkControlSurface(element, style) {
    if (!element.matches('button,[role="button"],input,select,textarea,summary,a.btn,a.button,[class*="button"],[class*="Button"]')) return false;
    const own = parseColor(style.backgroundColor);
    return Boolean(own && own.a >= 0.75 && luminance(composite(own, WHITE)) < 0.35);
  }

  function applyColor(element, color, targetClass, oppositeClass, ratioValue, source = 'computed') {
    applying = true;
    try {
      element.classList.remove(oppositeClass, 'auto-contrast-light', 'auto-contrast-dark');
      element.classList.add(targetClass);
      const value = cssColor(color);
      element.style.setProperty('color', value, 'important');
      element.style.setProperty('-webkit-text-fill-color', value, 'important');
      element.style.setProperty('text-shadow', color === DARK_TEXT ? 'none' : '0 1px 2px rgba(0,0,0,.38)', 'important');
      element.dataset.hhInlineContrast = 'true';
      element.dataset.hhContrast = ratioValue.toFixed(2);
      element.dataset.hhContrastSource = source;
    } finally {
      applying = false;
    }
  }

  function declaredSurface(surface) {
    if (surface.matches('[data-surface="light"],[data-theme="light"],.surface-light,.theme-light,.hh-surface-light,.hh-overlay-light')) return 'light';
    if (surface.matches('[data-surface="dark"],[data-theme="dark"],.surface-dark,.theme-dark,.hh-surface-dark,.hh-overlay-dark')) return 'dark';
    return null;
  }

  function firstVisibleTextColor(surface) {
    const candidates = [surface, ...surface.querySelectorAll(TEXT_SELECTOR)];
    for (const element of candidates) {
      if (!visible(element)) continue;
      const color = parseColor(getComputedStyle(element).color);
      if (color) return color;
    }
    return null;
  }

  function stabilizeImageSurface(surface, knownLightRoute) {
    const style = getComputedStyle(surface);
    if (!style.backgroundImage || style.backgroundImage === 'none') return null;

    let choice = declaredSurface(surface);
    if (!choice && knownLightRoute && surface.matches(TOP_SURFACE_SELECTOR)) choice = 'light';

    if (!choice) {
      const own = parseColor(style.backgroundColor);
      if (own && own.a >= 0.55) {
        choice = luminance(composite(own, WHITE)) >= 0.55 ? 'light' : 'dark';
      } else {
        const textColor = firstVisibleTextColor(surface);
        choice = textColor && luminance(textColor) < 0.45 ? 'light' : 'dark';
      }
    }

    const target = choice === 'light' ? 'hh-overlay-light' : 'hh-overlay-dark';
    const opposite = choice === 'light' ? 'hh-overlay-dark' : 'hh-overlay-light';
    applying = true;
    try {
      surface.classList.remove(opposite);
      surface.classList.add(target);
      surface.dataset.hhAdaptiveOverlay = choice;
    } finally {
      applying = false;
    }
    return choice;
  }

  function resolveElement(element, declaredLight = false) {
    if (!visible(element)) return;
    const style = getComputedStyle(element);
    const foregroundRaw = parseColor(style.color);
    if (!foregroundRaw) return;
    const background = effectiveBackground(element);
    const threshold = thresholdFor(element, style);

    if (declaredLight && luminance(background) >= 0.55 && !hasOwnDarkControlSurface(element, style)) {
      const darkRatio = contrast(DARK_TEXT, background);
      applyColor(element, DARK_TEXT, 'hh-text-on-light', 'hh-text-on-dark', darkRatio, 'declared-light-surface');
      return;
    }

    const foreground = foregroundRaw.a < 1 ? composite(foregroundRaw, background) : foregroundRaw;
    const currentRatio = contrast(foreground, background);
    if (currentRatio + 0.001 >= threshold && !hasResolution(element)) {
      element.dataset.hhContrast = currentRatio.toFixed(2);
      element.dataset.hhContrastSource = 'computed-pass';
      return;
    }
    const lightRatio = contrast(LIGHT_TEXT, background);
    const darkRatio = contrast(DARK_TEXT, background);
    const useLight = lightRatio >= darkRatio;
    const target = useLight ? LIGHT_TEXT : DARK_TEXT;
    applyColor(
      element,
      target,
      useLight ? 'hh-text-on-dark' : 'hh-text-on-light',
      useLight ? 'hh-text-on-light' : 'hh-text-on-dark',
      Math.max(lightRatio, darkRatio),
    );
  }

  function scan() {
    scheduled = false;
    const knownLightRoute = isKnownLightRoute();
    if (knownLightRoute) document.documentElement.dataset.hhPageSurface = 'light';

    const surfaces = [...document.querySelectorAll(SURFACE_SELECTOR)];
    for (const surface of surfaces) {
      const overlay = stabilizeImageSurface(surface, knownLightRoute);
      const declaredLight = overlay === 'light'
        || declaredSurface(surface) === 'light'
        || (knownLightRoute && surface.matches(TOP_SURFACE_SELECTOR));
      if (declaredLight) surface.dataset.hhDeclaredSurface = 'light';
      else if (overlay === 'dark' || declaredSurface(surface) === 'dark') surface.dataset.hhDeclaredSurface = 'dark';
      if (surface.matches(TEXT_SELECTOR)) resolveElement(surface, declaredLight);
      surface.querySelectorAll(TEXT_SELECTOR).forEach((element) => resolveElement(element, declaredLight));
    }
    document.documentElement.dataset.heroHeaderContrast = 'v283';
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(scan);
  }

  scan();
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
    if (applying) return;
    const externalChange = mutations.some((mutation) => {
      if (mutation.type !== 'attributes') return true;
      if (!['class','style'].includes(mutation.attributeName)) return true;
      if (mutation.target.dataset?.hhAdaptiveOverlay) return false;
      return !hasResolution(mutation.target);
    });
    if (externalChange) schedule();
  }).observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['class','style','data-surface','data-theme','aria-expanded','aria-disabled'],
  });

  window.__heroHeaderContrastV283 = {
    scan,
    classes: CLASS_NAMES.slice(),
    version: 288,
    knownLightRoutes: KNOWN_LIGHT_ROUTE_SUFFIXES.slice(),
    adaptiveImageSurfaces: true,
  };
})();
