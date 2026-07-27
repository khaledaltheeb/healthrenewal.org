/* v283 — computed-style hero/header contrast guard. */
(() => {
  'use strict';

  const CONTAINER_SELECTOR = [
    'header',
    '[role="banner"]',
    '[class*="hero"]', '[class*="Hero"]',
    '[id*="hero"]', '[id*="Hero"]',
    '[class*="banner"]', '[class*="Banner"]',
    '[class*="masthead"]',
    '[class*="breadcrumb"]', '[class*="Breadcrumb"]',
  ].join(',');

  const TEXT_SELECTOR = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'li', 'dt', 'dd', 'small', 'strong', 'em', 'span', 'label', 'blockquote',
    'a', 'button', '[role="button"]', 'summary', 'input', 'select', 'textarea',
  ].join(',');

  const CLASS_NAMES = [
    'hh-text-on-light', 'hh-text-on-dark',
    'auto-contrast-light', 'auto-contrast-dark',
  ];

  let scheduled = false;
  const pendingRoots = new Set();

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

  function luminance({ r, g, b }) {
    const channels = [r, g, b].map((channel) => {
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
    let imageBearer = null;

    while (node && node.nodeType === Node.ELEMENT_NODE) {
      const style = getComputedStyle(node);
      if (!imageBearer && style.backgroundImage && style.backgroundImage !== 'none') {
        imageBearer = node;
      }
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0.001) {
        layers.push(color);
        if (color.a >= 0.999) break;
      }
      node = node.parentElement;
    }

    let background = { r: 255, g: 255, b: 255, a: 1 };
    for (let index = layers.length - 1; index >= 0; index -= 1) {
      background = composite(layers[index], background);
    }
    return { color: background, imageBearer };
  }

  function isLargeText(style) {
    const size = Number.parseFloat(style.fontSize) || 0;
    const weight = Number.parseInt(style.fontWeight, 10) || 400;
    return size >= 24 || (size >= 18.66 && weight >= 700);
  }

  function isUiControl(element) {
    return element.matches('button,[role="button"],input,select,textarea,summary,a.btn,a.button,[class*="button"],[class*="Button"]');
  }

  function setTextClass(element, className) {
    CLASS_NAMES.forEach((name) => {
      if (name !== className) element.classList.remove(name);
    });
    if (className) element.classList.add(className);
  }

  function classifyContainer(container) {
    container.classList.remove('hh-surface-light', 'hh-surface-dark');
    const explicitLight = container.matches('[data-surface="light"],[data-theme="light"],.surface-light,.theme-light');
    const explicitDark = container.matches('[data-surface="dark"],[data-theme="dark"],.surface-dark,.theme-dark');
    const style = getComputedStyle(container);
    const hasImage = style.backgroundImage && style.backgroundImage !== 'none';

    if (hasImage && !explicitLight && !explicitDark) {
      container.classList.add('hh-overlay-dark', 'hh-surface-dark');
      container.classList.remove('hh-overlay-light');
      return;
    }

    container.classList.remove('hh-overlay-dark', 'hh-overlay-light');
    if (explicitDark) {
      container.classList.add('hh-surface-dark');
      return;
    }
    if (explicitLight) {
      container.classList.add('hh-surface-light');
      return;
    }

    const background = effectiveBackground(container).color;
    container.classList.add(luminance(background) < 0.42 ? 'hh-surface-dark' : 'hh-surface-light');
  }

  function fixText(element) {
    if (!visible(element)) return;
    const text = (element.value || element.textContent || '').trim();
    if (!text && !element.matches('input,select,textarea')) return;

    const style = getComputedStyle(element);
    const backgroundInfo = effectiveBackground(element);
    const foregroundRaw = parseColor(style.color);
    if (!foregroundRaw) return;

    const foreground = foregroundRaw.a < 1
      ? composite(foregroundRaw, backgroundInfo.color)
      : foregroundRaw;
    const threshold = isUiControl(element) || isLargeText(style) ? 3 : 4.5;
    const currentRatio = ratio(foreground, backgroundInfo.color);

    if (currentRatio + 0.01 >= threshold) {
      setTextClass(element, null);
      return;
    }

    const light = { r: 248, g: 252, b: 255, a: 1 };
    const dark = { r: 16, g: 42, b: 46, a: 1 };
    const lightRatio = ratio(light, backgroundInfo.color);
    const darkRatio = ratio(dark, backgroundInfo.color);
    setTextClass(element, lightRatio >= darkRatio ? 'hh-text-on-dark' : 'hh-text-on-light');
  }

  function scanContainer(container) {
    classifyContainer(container);
    if (container.matches(TEXT_SELECTOR)) fixText(container);
    container.querySelectorAll(TEXT_SELECTOR).forEach(fixText);
  }

  function scanRoot(root) {
    if (!(root instanceof Element) && root !== document) return;
    const containers = [];
    if (root instanceof Element && root.matches(CONTAINER_SELECTOR)) containers.push(root);
    containers.push(...root.querySelectorAll(CONTAINER_SELECTOR));
    [...new Set(containers)].forEach(scanContainer);
    document.documentElement.dataset.heroHeaderContrast = 'v283';
  }

  function run() {
    scheduled = false;
    const roots = pendingRoots.size ? [...pendingRoots] : [document];
    pendingRoots.clear();
    roots.forEach(scanRoot);
  }

  function schedule(root = document) {
    pendingRoots.add(root);
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => requestAnimationFrame(run));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => schedule(document), { once: true });
  } else {
    schedule(document);
  }

  if (document.fonts?.ready) document.fonts.ready.then(() => schedule(document));

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => schedule(document), 120);
  }, { passive: true });

  ['focusin', 'focusout', 'pointerover', 'pointerout', 'change'].forEach((eventName) => {
    document.addEventListener(eventName, (event) => {
      const container = event.target instanceof Element ? event.target.closest(CONTAINER_SELECTOR) : null;
      if (container) schedule(container);
    }, { passive: true });
  });

  ['(prefers-color-scheme: dark)', '(prefers-contrast: more)'].forEach((query) => {
    const media = window.matchMedia(query);
    media.addEventListener?.('change', () => schedule(document));
  });

  new MutationObserver((records) => {
    records.forEach((record) => record.addedNodes.forEach((node) => {
      if (node instanceof Element) schedule(node);
    }));
  }).observe(document.documentElement, { subtree: true, childList: true });
})();
