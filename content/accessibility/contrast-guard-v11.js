/* v11 — runtime contrast guard for all current and future content pages; v290 defers adaptive shell surfaces to v283. */
(() => {
  'use strict';

  const CANDIDATES = 'h1,h2,h3,h4,h5,h6,p,li,dt,dd,small,strong,em,span,label,blockquote,a';
  const ADAPTIVE_SCOPE = [
    'header','[role="banner"]','nav','[role="navigation"]','[role="search"]',
    '[class*="hero"]','[class*="Hero"]','[id*="hero"]','[id*="Hero"]',
    '[class*="banner"]','[class*="Banner"]','[class*="masthead"]',
    '[class*="breadcrumb"]','[class*="Breadcrumb"]','footer','[role="contentinfo"]','.site-footer',
  ].join(',');
  const DARK_HINT = /(dark|gradient|overlay|cover)/i;
  let scheduled = false;
  const pendingRoots = new Set();

  const parseColor = (value) => {
    const match = String(value || '').match(/rgba?\(([^)]+)\)/i);
    if (!match) return null;
    const parts = match[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    if (parts.length < 3 || parts.slice(0, 3).some(Number.isNaN)) return null;
    return [parts[0], parts[1], parts[2], Number.isFinite(parts[3]) ? parts[3] : 1];
  };

  const blend = (front, back) => {
    const a = front[3] + back[3] * (1 - front[3]);
    if (a <= 0) return [255, 255, 255, 1];
    return [
      (front[0] * front[3] + back[0] * back[3] * (1 - front[3])) / a,
      (front[1] * front[3] + back[1] * back[3] * (1 - front[3])) / a,
      (front[2] * front[3] + back[2] * back[3] * (1 - front[3])) / a,
      a,
    ];
  };

  const luminance = ([r, g, b]) => {
    const linear = [r, g, b].map((channel) => {
      const v = channel / 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  };

  const ratio = (a, b) => {
    const l1 = luminance(a);
    const l2 = luminance(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };

  const effectiveBackground = (element) => {
    const chain = [];
    let node = element;
    let darkHint = false;
    while (node && node.nodeType === 1) {
      const style = getComputedStyle(node);
      chain.push(style);
      const hintText = `${node.className || ''} ${node.id || ''} ${node.getAttribute?.('data-theme') || ''} ${node.getAttribute?.('data-surface') || ''}`;
      if (DARK_HINT.test(hintText) && style.backgroundImage !== 'none') darkHint = true;
      node = node.parentElement;
    }

    let background = [255, 255, 255, 1];
    for (let i = chain.length - 1; i >= 0; i -= 1) {
      const parsed = parseColor(chain[i].backgroundColor);
      if (parsed && parsed[3] > 0.01) background = blend(parsed, background);
    }
    if (darkHint && luminance(background) > 0.35) background = [20, 43, 48, 1];
    return background;
  };

  const hasReadableText = (element) => {
    const text = (element.textContent || '').trim();
    if (!text) return false;
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && Number(style.opacity || 1) > 0.05;
  };

  const ownedByAdaptiveGuard = (element) => Boolean(
    element.closest(ADAPTIVE_SCOPE)
    || element.dataset.hhInlineContrast === 'true'
    || element.classList.contains('hh-text-on-dark')
    || element.classList.contains('hh-text-on-light')
  );

  const setContrastClass = (element, desired) => {
    const hasLight = element.classList.contains('auto-contrast-light');
    const hasDark = element.classList.contains('auto-contrast-dark');
    if (desired === 'light') {
      if (!hasLight) element.classList.add('auto-contrast-light');
      if (hasDark) element.classList.remove('auto-contrast-dark');
    } else if (desired === 'dark') {
      if (!hasDark) element.classList.add('auto-contrast-dark');
      if (hasLight) element.classList.remove('auto-contrast-light');
    } else {
      if (hasLight) element.classList.remove('auto-contrast-light');
      if (hasDark) element.classList.remove('auto-contrast-dark');
    }
  };

  const fixElement = (element) => {
    if (ownedByAdaptiveGuard(element) || !hasReadableText(element)) return;
    const style = getComputedStyle(element);
    const foreground = parseColor(style.color);
    if (!foreground) return;
    const background = effectiveBackground(element);
    const fontSize = parseFloat(style.fontSize || '16');
    const fontWeight = parseInt(style.fontWeight || '400', 10) || 400;
    const largeText = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    const minimum = largeText ? 3 : 4.5;
    const current = ratio(foreground, background);
    if (current >= minimum) {
      setContrastClass(element, null);
      return;
    }
    const light = [248, 252, 255, 1];
    const dark = [16, 42, 46, 1];
    setContrastClass(element, ratio(light, background) >= ratio(dark, background) ? 'light' : 'dark');
  };

  const scanRoot = (root) => {
    if (!(root instanceof Element) && root !== document) return;
    if (root instanceof Element && root.matches(CANDIDATES)) fixElement(root);
    root.querySelectorAll(CANDIDATES).forEach(fixElement);
  };

  const scan = () => {
    scheduled = false;
    const roots = pendingRoots.size ? [...pendingRoots] : [document];
    pendingRoots.clear();
    roots.forEach(scanRoot);
    document.documentElement.dataset.contrastGuard = 'v11';
  };

  const schedule = (root = document) => {
    pendingRoots.add(root);
    if (scheduled) return;
    scheduled = true;
    if ('requestIdleCallback' in window) requestIdleCallback(scan, { timeout: 500 });
    else requestAnimationFrame(scan);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => schedule(document), { once: true });
  else schedule(document);

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => schedule(document), 150);
  }, { passive: true });

  new MutationObserver((records) => {
    records.forEach((record) => record.addedNodes.forEach((node) => {
      if (node instanceof Element) schedule(node);
    }));
  }).observe(document.body, { subtree: true, childList: true });
})();
