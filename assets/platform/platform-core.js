(() => {
  'use strict';

  const doc = document;
  const body = doc.body;
  if (!body || body.dataset.ptShellReady === 'true') return;

  body.dataset.ptShellReady = 'true';
  body.classList.add('pt-platform');
  if (!doc.documentElement.lang) doc.documentElement.lang = 'ar';
  if (!doc.documentElement.dir) doc.documentElement.dir = 'rtl';

  const base = '/';
  const url = (path = '') => `${base}${String(path).replace(/^\/+/, '')}`;
  const currentPath = location.pathname.replace(/index\.html$/, '');
  const pageTitle = (doc.querySelector('h1')?.textContent || doc.title || 'منصة روافد').trim();
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  if (!doc.querySelector('script[data-pt-discoverability-loader]')) {
    const discoverabilityScript = doc.createElement('script');
    discoverabilityScript.src = url('assets/platform/discoverability-cards.js?v=1.0.0');
    discoverabilityScript.async = false;
    discoverabilityScript.dataset.ptDiscoverabilityLoader = 'v1';
    doc.head.append(discoverabilityScript);
  }

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
    ['ابدأ هنا', 'start-here/'],
    ['الموسوعة', 'encyclopedia/'],
    ['الأدلة', 'care-guides/'],
    ['ذوو الاحتياجات الخاصة', 'special-needs/'],
    ['المكتبة', 'library/'],
    ['الأدوات', 'daily-tools/'],
    ['المجلة', 'magazine/'],
    ['كل الأقسام', 'sections/']
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
  if (mainId) {
    const existingSkip = [...body.children].find((child) =>
      child.tagName === 'A'
      && (child.classList.contains('skip') || child.getAttribute('href') === `#${mainId}`)
    );
    if (existingSkip) {
      existingSkip.classList.add('pt-skip-link');
      existingSkip.setAttribute('href', `#${mainId}`);
    } else if (!doc.querySelector('.pt-skip-link')) {
      body.prepend(element('a', {
        class: 'pt-skip-link',
        href: `#${mainId}`,
        text: 'تجاوز إلى المحتوى الرئيسي'
      }));
    }
  }

  const nav = element('nav', {
    class: 'pt-global-nav',
    id: 'pt-global-nav',
    'aria-label': 'التنقل الرئيسي في منصة روافد'
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

  const brand = element('a', {
    class: 'pt-global-brand',
    href: url(''),
    'aria-label': 'العودة إلى الصفحة الرئيسية لمنصة روافد'
  }, [
    element('img', { src: url('assets/brand/logo-mark.svg'), alt: '', width: '44', height: '44' }),
    element('span', {}, [
      element('span', { text: 'منصة روافد' }),
      element('small', { text: 'العافية النفسية • الدمج • التمكين' })
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
    'aria-label': 'فتح البحث الذكي في منصة روافد',
    'aria-haspopup': 'dialog',
    'aria-controls': 'pt-platform-search'
  }, [element('span', { text: 'بحث' }), element('span', { 'aria-hidden': 'true', text: '⌕' })]);

  const actions = element('div', { class: 'pt-global-actions' }, [searchButton, menuButton]);
  const shellInner = element('div', { class: 'pt-global-shell__inner' }, [brand, nav, actions]);
  const progress = element('div', { class: 'pt-reading-progress', 'aria-hidden': 'true' });
  const shell = element('header', { class: 'pt-global-shell', 'data-platform-shell': 'v2' }, [shellInner, progress]);

  const context = element('div', { class: 'pt-context-strip' }, [
    element('div', { class: 'pt-context-strip__inner' }, [
      element('span', {}, [
        element('a', { href: url(''), text: 'الرئيسية' }),
        doc.createTextNode(' / '),
        element('span', { text: pageTitle })
      ]),
      element('span', { text: 'معرفة موثوقة • لغة إنسانية • حدود مهنية واضحة' })
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
    placeholder: 'ابحث عن موضوع أو حالة أو دليل أو أداة…',
    'aria-label': 'عبارة البحث'
  });

  const searchForm = element('form', { action: url('ai-search/'), method: 'get', role: 'search' }, [
    searchInput,
    element('button', { type: 'submit', text: 'بحث' })
  ]);

  dialog.append(element('div', { class: 'pt-search-dialog__body' }, [
    element('div', { class: 'pt-search-dialog__head' }, [
      element('div', {}, [
        element('h2', { id: 'pt-search-title', text: 'ابحث في منصة روافد' }),
        element('p', { text: 'اكتب ما تبحث عنه بلغة طبيعية للوصول إلى الصفحات والأدلة والأدوات الأقرب إلى مقصدك.' })
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

  const existingTopFooter = [...body.children].find((child) => child.tagName === 'FOOTER');
  if (existingTopFooter) {
    existingTopFooter.hidden = true;
    existingTopFooter.setAttribute('aria-hidden', 'true');
    existingTopFooter.dataset.replacedByPlatformShell = 'true';
  }

  const footer = element('footer', { class: 'pt-global-footer', 'data-platform-footer': 'v2' }, [
    element('div', { class: 'pt-global-footer__inner' }, [
      element('p', { text: `© ${new Date().getFullYear()} منصة روافد. جميع الحقوق محفوظة.` }),
      element('nav', { 'aria-label': 'روابط الحوكمة والشفافية' }, [
        element('a', { href: url('about/'), text: 'عن روافد' }),
        element('a', { href: url('trust/'), text: 'الثقة والمنهجية' }),
        element('a', { href: url('accessibility/'), text: 'الإتاحة' }),
        element('a', { href: url('contact/'), text: 'تواصل معنا' }),
        element('a', { href: url('copyright/'), text: 'حقوق النشر' }),
        element('a', { href: url('sections/'), text: 'دليل الأقسام' })
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

  doc.addEventListener('click', (event) => {
    if (!nav.classList.contains('is-open')) return;
    if (!nav.contains(event.target) && !menuButton.contains(event.target)) closeMobileNav();
  });

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
      // Link audits handle malformed third-party URLs.
    }
  });
})();