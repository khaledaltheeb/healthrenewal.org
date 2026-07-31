(() => {
  'use strict';

  const doc = document;
  const body = doc.body;
  if (!body || body.dataset.ptShellReady === 'true') return;

  body.dataset.ptShellReady = 'true';
  body.classList.add('pt-platform');
  if (!doc.documentElement.lang) doc.documentElement.lang = 'ar';
  if (!doc.documentElement.dir) doc.documentElement.dir = 'rtl';

  const projectSegment = '/';
  const base = location.pathname.includes(projectSegment) ? projectSegment : '/';
  const url = (path = '') => `${base}${String(path).replace(/^\/+/, '')}`;
  const currentPath = location.pathname.replace(/index\.html$/, '');
  const pageTitle = (doc.querySelector('h1')?.textContent || doc.title || 'المنصة').trim();
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Preserve section-level navigation, but avoid rendering the old home header
  // directly below the new global platform shell.
  const existingTopHeader = [...body.children].find((child) => child.tagName === 'HEADER');
  if (existingTopHeader) {
    if (currentPath === base) {
      existingTopHeader.hidden = true;
      existingTopHeader.setAttribute('aria-hidden', 'true');
      existingTopHeader.dataset.replacedByPlatformShell = 'true';
    } else {
      existingTopHeader.classList.add('pt-section-header');
      existingTopHeader.dataset.localNavigation = 'true';
    }
  }

  const navItems = [
    ['ابدأ', 'start-here/'],
    ['البحث الذكي', 'ai-search/'],
    ['الموسوعة', 'encyclopedia/'],
    ['المقارنات', 'comparisons/'],
    ['المكتبة', 'library/'],
    ['الأدلة', 'care-guides/'],
    ['ذوو الاحتياجات الخاصة', 'special-needs/'],
    ['الفريق والشركاء', 'specialists-partners/'],
    ['المجلة', 'magazine/'],
    ['الأدوات', 'daily-tools/'],
    ['الثقة', 'trust/']
  ];

  const element = (tag, attrs = {}, children = []) => {
    const node = doc.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    });
    (Array.isArray(children) ? children : [children]).filter(Boolean).forEach((child) => {
      node.append(child instanceof Node ? child : doc.createTextNode(String(child)));
    });
    return node;
  };

  const ensureMainId = () => {
    const main = doc.querySelector('main');
    if (!main) return null;
    if (!main.id) main.id = 'main-content';
    return main.id;
  };

  const mainId = ensureMainId();
  if (mainId && !doc.querySelector('.pt-skip-link')) {
    const skip = element('a', {
      class: 'pt-skip-link',
      href: `#${mainId}`,
      text: 'تجاوز إلى المحتوى الرئيسي'
    });
    body.prepend(skip);
  }

  const nav = element('nav', {
    class: 'pt-global-nav',
    id: 'pt-global-nav',
    'aria-label': 'التنقل الرئيسي في المنصة'
  });

  navItems.forEach(([label, path]) => {
    const href = url(path);
    const link = element('a', { href, text: label });
    const normalizedHref = new URL(href, location.origin).pathname.replace(/index\.html$/, '');
    if (currentPath === normalizedHref || (normalizedHref !== base && currentPath.startsWith(normalizedHref))) {
      link.setAttribute('aria-current', 'page');
    }
    nav.append(link);
  });

  const brand = element('a', { class: 'pt-global-brand', href: url(''), 'aria-label': 'العودة إلى الصفحة الرئيسية' }, [
    element('img', { src: url('assets/brand/logo-mark.svg'), alt: '', width: '44', height: '44' }),
    element('span', {}, [
      element('span', { text: 'منصة الصحة النفسية' }),
      element('small', { text: 'معرفة تحترم الإنسان' })
    ])
  ]);

  const menuButton = element('button', {
    class: 'pt-menu-button',
    type: 'button',
    'aria-controls': 'pt-global-nav',
    'aria-expanded': 'false',
    'aria-label': 'فتح قائمة التنقل',
    text: 'القائمة'
  });

  menuButton.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'إغلاق قائمة التنقل' : 'فتح قائمة التنقل');
  });

  const searchButton = element('button', {
    class: 'pt-search-button',
    type: 'button',
    'aria-label': 'فتح البحث الدلالي في المنصة',
    'aria-haspopup': 'dialog',
    'aria-controls': 'pt-platform-search'
  }, [element('span', { text: 'بحث ذكي' }), element('span', { 'aria-hidden': 'true', text: '⌕' })]);

  const actions = element('div', { class: 'pt-global-actions' }, [searchButton, menuButton]);
  const shellInner = element('div', { class: 'pt-global-shell__inner' }, [brand, nav, actions]);
  const progress = element('div', { class: 'pt-reading-progress', 'aria-hidden': 'true' });
  const shell = element('header', { class: 'pt-global-shell', 'data-platform-shell': 'v1' }, [shellInner, progress]);

  const context = element('div', { class: 'pt-context-strip' }, [
    element('div', { class: 'pt-context-strip__inner' }, [
      element('span', {}, [
        element('a', { href: url(''), text: 'الرئيسية' }),
        doc.createTextNode(' / '),
        element('span', { text: pageTitle })
      ]),
      element('span', { text: 'محتوى تثقيفي موثّق بحدود مهنية واضحة' })
    ])
  ]);

  const firstNonSkip = [...body.children].find((child) => !child.classList?.contains('pt-skip-link'));
  if (firstNonSkip) {
    body.insertBefore(shell, firstNonSkip);
    body.insertBefore(context, firstNonSkip);
  } else {
    body.append(shell, context);
  }

  const dialogSupported = typeof HTMLDialogElement !== 'undefined';
  const dialog = element(dialogSupported ? 'dialog' : 'div', {
    class: 'pt-search-dialog',
    id: 'pt-platform-search',
    'aria-labelledby': 'pt-search-title'
  });

  if (!dialogSupported) {
    dialog.hidden = true;
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
  }

  const closeSearch = () => {
    if (dialogSupported && dialog.open) dialog.close();
    else dialog.hidden = true;
    searchButton.focus();
  };

  const closeButton = element('button', {
    class: 'pt-icon-button',
    type: 'button',
    'aria-label': 'إغلاق البحث',
    text: 'إغلاق'
  });
  closeButton.addEventListener('click', closeSearch);

  const searchInput = element('input', {
    type: 'search',
    name: 'q',
    maxlength: '300',
    autocomplete: 'off',
    spellcheck: 'false',
    placeholder: 'اكتب سؤالك أو الحالة أو الدليل المطلوب…',
    'aria-label': 'سؤال البحث الدلالي'
  });

  const searchForm = element('form', { action: url('ai-search/'), method: 'get', role: 'search' }, [
    searchInput,
    element('button', { type: 'submit', text: 'ابحث بذكاء' })
  ]);

  dialog.append(element('div', { class: 'pt-search-dialog__body' }, [
    element('div', { class: 'pt-search-dialog__head' }, [
      element('div', {}, [
        element('h2', { id: 'pt-search-title', text: 'البحث الذكي في المنصة' }),
        element('p', { text: 'اكتب سؤالك بلغتك الطبيعية. يستخدم البحث multilingual-e5-small لترتيب صفحات المنصة حسب تقارب المعنى.' })
      ]),
      closeButton
    ]),
    searchForm
  ]));
  body.append(dialog);

  searchButton.addEventListener('click', () => {
    if (dialogSupported) dialog.showModal();
    else dialog.hidden = false;
    window.setTimeout(() => searchInput.focus(), 30);
  });

  dialog.addEventListener('click', (event) => {
    if (dialogSupported && event.target === dialog) closeSearch();
  });

  doc.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      searchButton.click();
    }
    if (event.key === 'Escape' && !dialogSupported && !dialog.hidden) closeSearch();
  });

  const footer = element('footer', { class: 'pt-global-footer', 'data-platform-footer': 'v1' }, [
    element('div', { class: 'pt-global-footer__inner' }, [
      element('p', { text: `© ${new Date().getFullYear()} منصة الصحة النفسية وذوي الاحتياجات الخاصة. جميع الحقوق محفوظة.` }),
      element('nav', { 'aria-label': 'روابط الحوكمة والشفافية' }, [
        element('a', { href: url('platform/'), text: 'دليل المنصة' }),
        element('a', { href: url('trust/'), text: 'الثقة والمنهجية' }),
        element('a', { href: url('accessibility/'), text: 'الإتاحة' }),
        element('a', { href: url('copyright/'), text: 'حقوق النشر' }),
        element('a', { href: url('sitemap-html/'), text: 'دليل الأقسام' }),
        element('a', { href: url('api/'), text: 'واجهة البيانات' })
      ])
    ])
  ]);
  body.append(footer);

  const backToTop = element('button', {
    class: 'pt-back-to-top',
    type: 'button',
    'aria-label': 'العودة إلى أعلى الصفحة',
    title: 'العودة إلى أعلى الصفحة',
    text: '↑'
  });
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: reducedMotion.matches ? 'auto' : 'smooth' });
  });
  body.append(backToTop);

  let ticking = false;
  const updateScrollUi = () => {
    const scrollTop = doc.documentElement.scrollTop || body.scrollTop;
    const max = Math.max(1, doc.documentElement.scrollHeight - doc.documentElement.clientHeight);
    const percent = Math.min(100, Math.max(0, (scrollTop / max) * 100));
    progress.style.width = `${percent}%`;
    backToTop.classList.toggle('is-visible', scrollTop > 700);
    ticking = false;
  };

  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(updateScrollUi);
      ticking = true;
    }
  }, { passive: true });
  updateScrollUi();

  const closeMobileNav = () => {
    nav.classList.remove('is-open');
    menuButton.setAttribute('aria-expanded', 'false');
  };
  nav.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMobileNav();
  });

  // Make external links explicit without altering downloadable or internal resources.
  doc.querySelectorAll('main a[href^="http"]').forEach((link) => {
    try {
      const target = new URL(link.href);
      if (target.origin !== location.origin) {
        link.rel = `${link.rel || ''} noopener noreferrer`.trim();
        if (!link.getAttribute('aria-label') && !link.textContent.includes('يفتح')) {
          link.title = link.title || 'رابط خارجي';
        }
      }
    } catch (_) {
      // Ignore malformed third-party URLs; link audits handle them separately.
    }
  });
})();