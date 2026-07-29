(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const apiBase = String(config.apiBase || '').replace(/\/$/, '');
  const protectedPaths = new Set(['/v1/applications', '/v1/conversations']);
  const page = document.body?.dataset.page || '';
  const formId = page === 'join' ? 'onboarding-form' : page === 'contact' ? 'contact-form' : '';

  function announce(message) {
    const box = document.getElementById('form-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = 'error';
    box.textContent = message;
    box.focus?.();
  }

  function turnstileToken(form) {
    return form?.querySelector('[name="cf-turnstile-response"]')?.value?.trim() || '';
  }

  function requireHumanVerification(event) {
    if (!apiBase || !config.turnstileSiteKey) return;
    if (turnstileToken(event.currentTarget)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    announce('أكمل التحقق من الاستخدام البشري قبل إرسال الطلب. لم تُرسل أي بيانات.');
  }

  function parseProtectedRequest(resource, options) {
    if (!apiBase || String(options?.method || 'GET').toUpperCase() !== 'POST') return null;
    const rawUrl = typeof resource === 'string' ? resource : resource?.url;
    if (!rawUrl) return null;
    let url;
    try { url = new URL(rawUrl, location.href); } catch (_) { return null; }
    let base;
    try { base = new URL(apiBase, location.href); } catch (_) { return null; }
    if (url.origin !== base.origin) return null;
    const basePath = base.pathname.replace(/\/$/, '');
    const relativePath = url.pathname.startsWith(basePath) ? url.pathname.slice(basePath.length) || '/' : '';
    if (!protectedPaths.has(relativePath)) return null;
    return {url, relativePath};
  }

  function requestIdentity(options) {
    try {
      const body = JSON.parse(String(options?.body || '{}'));
      const identity = body.submissionId || body.requestId;
      return typeof identity === 'string' && /^[a-z0-9-]{12,96}$/i.test(identity) ? identity : '';
    } catch (_) {
      return '';
    }
  }

  function installFetchGuard() {
    if (!apiBase || window.fetch.__ptSubmissionSecurity) return;
    const nativeFetch = window.fetch.bind(window);
    const guardedFetch = async (resource, options = {}) => {
      const target = parseProtectedRequest(resource, options);
      if (!target) return nativeFetch(resource, options);

      const identity = requestIdentity(options);
      if (!identity) throw new Error('تعذر إنشاء معرّف آمن للطلب. أعد تحميل الصفحة وحاول مرة أخرى.');

      const headers = new Headers(options.headers || {});
      headers.set('Accept', 'application/json');
      headers.set('Idempotency-Key', identity);
      headers.set('X-Requested-With', 'pterminology-specialists');

      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort('request_timeout'), 20000);
      try {
        return await nativeFetch(resource, {
          ...options,
          headers,
          signal: options.signal || controller.signal,
          cache: 'no-store',
          credentials: 'omit',
          referrerPolicy: 'no-referrer',
          redirect: 'error'
        });
      } finally {
        window.clearTimeout(timeout);
      }
    };
    guardedFetch.__ptSubmissionSecurity = true;
    window.fetch = guardedFetch;
  }

  function init() {
    if (!formId) return;
    const form = document.getElementById(formId);
    form?.addEventListener('submit', requireHumanVerification, true);
    installFetchGuard();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();