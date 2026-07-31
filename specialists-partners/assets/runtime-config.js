window.PT_SPECIALIST_CONFIG = Object.freeze({
  apiBase: "https://pterminology-specialists.pterminology-826ac349.workers.dev",
  accountApiBase: "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev",
  turnstileSiteKey: "0x4AAAAAAD_r2o__Ao1RmBTO",
  siteBase: "https://khaledaltheeb.github.io/pterminology-site",
  sectorBase: "https://khaledaltheeb.github.io/pterminology-site/specialists-partners",
  environment: "production",
  identityVersion: "10.1.0"
});

(() => {
  'use strict';
  if (!/\/specialists-partners\/admin\/?$/.test(location.pathname)) return;
  if (document.querySelector('script[data-pt-admin-recovery-v10]')) return;
  const script = document.createElement('script');
  script.src = '../admin/admin-recovery-v10-final.js?v=10.1.0';
  script.defer = true;
  script.dataset.ptAdminRecoveryV10 = 'true';
  document.head.append(script);
})();
