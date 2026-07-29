window.PT_SPECIALIST_CONFIG = Object.freeze({
  apiBase: "",
  turnstileSiteKey: "",
  siteBase: "https://khaledaltheeb.github.io/pterminology-site",
  sectorBase: "https://khaledaltheeb.github.io/pterminology-site/specialists-partners",
  environment: "production"
});

window.addEventListener('DOMContentLoaded', () => {
  const page = document.body?.dataset.page;
  const modules = [];
  if (page === 'join') modules.push(['assets/privacy-guard.js?v=2.0.0', 'private-preview-guard']);
  if (page === 'join' || page === 'contact') modules.push(['assets/submission-security.js?v=2.0.0', 'protected-submission-guard']);

  modules.forEach(([src, name]) => {
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    script.dataset.securityModule = name;
    document.head.append(script);
  });
}, {once: true});