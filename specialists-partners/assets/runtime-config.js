window.PT_SPECIALIST_CONFIG = Object.freeze({
  apiBase: "https://pterminology-specialists.pterminology-826ac349.workers.dev",
  accountApiBase: "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev",
  turnstileSiteKey: "0x4AAAAAAD_r2o__Ao1RmBTO",
  siteBase: "https://healthrenewal.org/",
  sectorBase: "https://healthrenewal.org/specialists-partners",
  environment: "production",
  identityVersion: "10.3.0"
});

(() => {
  'use strict';
  if (!/\/specialists-partners\/admin\/?$/.test(location.pathname)) return;
  const scripts = [
    ['../admin/admin-recovery-v10-final.js?v=10.3.0', 'ptAdminRecoveryV10'],
    ['../admin/admin-provider-status-v10.js?v=10.3.0', 'ptAdminProviderStatusV10']
  ];
  for (const [src, key] of scripts) {
    const attribute = `data-${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`;
    if (document.querySelector(`script[${attribute}]`)) continue;
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    script.dataset[key] = 'true';
    document.head.append(script);
  }
})();
