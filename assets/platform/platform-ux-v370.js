(() => {
  'use strict';

  const doc = document;
  const body = doc.body;
  if (!body || body.dataset.ptUxV370Ready === 'true') return;
  body.dataset.ptUxV370Ready = 'true';

  const menuButton = doc.querySelector('.pt-menu-button');
  const navigation = doc.querySelector('.pt-global-nav');
  const searchDialog = doc.querySelector('.pt-search-dialog');
  const globalActions = doc.querySelector('.pt-global-actions');
  const mobileQuery = window.matchMedia('(max-width: 1060px)');

  const syncNavigationState = () => {
    if (!menuButton || !navigation) return;
    const open = navigation.classList.contains('is-open');
    menuButton.setAttribute('aria-expanded', String(open));
    if (mobileQuery.matches) {
      navigation.setAttribute('aria-hidden', String(!open));
    } else {
      navigation.removeAttribute('aria-hidden');
    }
    body.classList.toggle('pt-navigation-open', open && mobileQuery.matches);
  };

  if (menuButton && navigation) {
    menuButton.addEventListener('click', () => {
      window.setTimeout(() => {
        syncNavigationState();
        if (navigation.classList.contains('is-open')) {
          navigation.querySelector('a')?.focus({ preventScroll: true });
        }
      }, 0);
    });

    doc.addEventListener('pointerdown', (event) => {
      if (!navigation.classList.contains('is-open')) return;
      if (navigation.contains(event.target) || menuButton.contains(event.target)) return;
      navigation.classList.remove('is-open');
      syncNavigationState();
    });

    doc.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !navigation.classList.contains('is-open')) return;
      navigation.classList.remove('is-open');
      syncNavigationState();
      menuButton.focus();
    });

    mobileQuery.addEventListener?.('change', () => {
      navigation.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
      syncNavigationState();
    });
    syncNavigationState();
  }

  if (searchDialog) {
    const syncDialogState = () => {
      const open = searchDialog.matches('dialog') ? searchDialog.open : !searchDialog.hidden;
      body.classList.toggle('pt-modal-open', open);
    };
    searchDialog.addEventListener('close', syncDialogState);
    searchDialog.addEventListener('cancel', syncDialogState);
    new MutationObserver(syncDialogState).observe(searchDialog, {
      attributes: true,
      attributeFilter: ['open', 'hidden']
    });
    syncDialogState();
  }

  doc.querySelectorAll('main table').forEach((table) => {
    if (table.parentElement?.classList.contains('pt-table-scroll')) return;
    const wrapper = doc.createElement('div');
    wrapper.className = 'pt-table-scroll';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    const heading = table.closest('section, article')?.querySelector('h2, h3');
    wrapper.setAttribute(
      'aria-label',
      heading?.textContent?.trim()
        ? `جدول: ${heading.textContent.trim()}`
        : 'جدول قابل للتمرير أفقيًا'
    );
    table.parentNode.insertBefore(wrapper, table);
    wrapper.append(table);
  });

  const networkStatus = doc.createElement('div');
  networkStatus.className = 'pt-network-status';
  networkStatus.setAttribute('role', 'status');
  networkStatus.setAttribute('aria-live', 'polite');
  networkStatus.setAttribute('aria-atomic', 'true');
  body.append(networkStatus);

  let networkTimer = 0;
  const showStatus = (message, offline = false, persistent = false) => {
    window.clearTimeout(networkTimer);
    networkStatus.textContent = message;
    networkStatus.classList.toggle('is-offline', offline);
    networkStatus.classList.add('is-visible');
    if (!persistent) {
      networkTimer = window.setTimeout(
        () => networkStatus.classList.remove('is-visible'),
        4600
      );
    }
  };

  const announceNetwork = (online, initial = false) => {
    if (online) {
      if (!initial) showStatus('عاد الاتصال بالإنترنت. تم استئناف تحديث المحتوى.');
      return;
    }
    showStatus(
      'أنت دون اتصال. ستبقى الصفحات المحفوظة وصفحة الطوارئ غير المتصلة متاحة.',
      true,
      true
    );
  };

  window.addEventListener('online', () => announceNetwork(true));
  window.addEventListener('offline', () => announceNetwork(false));
  announceNetwork(navigator.onLine, true);

  let deferredInstallPrompt = null;
  let installButton = null;
  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  const isIOS =
    /iphone|ipad|ipod/i.test(window.navigator.userAgent) ||
    (window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1);

  const ensureInstallButton = () => {
    if (!globalActions || installButton || isStandalone) return installButton;
    installButton = doc.createElement('button');
    installButton.type = 'button';
    installButton.className = 'pt-install-button';
    installButton.setAttribute('aria-label', 'تثبيت المنصة كتطبيق على الجهاز');
    installButton.append(
      Object.assign(doc.createElement('span'), { textContent: 'تثبيت' }),
      Object.assign(doc.createElement('span'), { textContent: '＋' })
    );
    installButton.lastElementChild.setAttribute('aria-hidden', 'true');
    globalActions.prepend(installButton);

    installButton.addEventListener('click', async () => {
      if (!deferredInstallPrompt) {
        if (isIOS) {
          showStatus('لتثبيت المنصة في Safari: اضغط مشاركة، ثم «إضافة إلى الشاشة الرئيسية».');
        }
        return;
      }
      installButton.disabled = true;
      try {
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice;
      } finally {
        deferredInstallPrompt = null;
        installButton.classList.remove('is-available');
        installButton.disabled = false;
      }
    });
    return installButton;
  };

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    ensureInstallButton()?.classList.add('is-available');
  });

  if (isIOS && !isStandalone) {
    ensureInstallButton()?.classList.add('is-available');
  }

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    installButton?.classList.remove('is-available');
    body.dataset.ptInstalled = 'true';
    showStatus('تم تثبيت المنصة بنجاح على جهازك.');
  });

  if (isStandalone) body.dataset.ptInstalled = 'true';
})();
