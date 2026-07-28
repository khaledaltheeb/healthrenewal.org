window.PT_SPECIALIST_CONFIG = Object.freeze({
  apiBase: "",
  turnstileSiteKey: "",
  siteBase: "https://khaledaltheeb.github.io/pterminology-site",
  sectorBase: "https://khaledaltheeb.github.io/pterminology-site/specialists-partners",
  environment: "production"
});

window.addEventListener('DOMContentLoaded', () => {
  if (document.body?.dataset.page !== 'join') return;
  const script = document.createElement('script');
  script.src = 'assets/privacy-guard.js?v=2.0.0';
  script.defer = true;
  script.dataset.securityModule = 'private-preview-guard';
  document.head.append(script);
}, {once: true});
