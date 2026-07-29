(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const apiBase = String(config.apiBase || '').replace(/\/$/, '');
  const protectedPaths = new Set(['/v1/applications', '/v1/conversations']);
  const page = document.body?.dataset.page || '';
  const formId = page === 'join' ? 'onboarding-form' : page === 'contact' ? 'contact-form' : '';
  const REQUEST_TIMEOUT_MS = 20000;
  const MAX_JSON_BYTES = 256 * 1024;

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

  function apiBaseUrl() {
    try {
      const base = new URL(apiBase, location.href);
      if (base.username || base.password || !/^https:$/.test(base.protocol)) return null;
      return base;
    } catch (_) {
      return null;
    }
  }

  function parseProtectedRequest(resource, options) {
    const method = String(options?.method || (resource instanceof Request ? resource.method : 'GET')).toUpperCase();
    if (!apiBase || method !== 'POST') return null;

    const rawUrl = typeof resource === 'string' ? resource : resource?.url;
    if (!rawUrl) return null;

    let url;
    try { url = new URL(rawUrl, location.href); } catch (_) { return null; }
    const base = apiBaseUrl();
    if (!base || url.origin !== base.origin) return null;

    const basePath = base.pathname.replace(/\/$/, '');
    const pathMatchesBase = !basePath || url.pathname === basePath || url.pathname.startsWith(`${basePath}/`);
    if (!pathMatchesBase) return null;

    const relativePath = url.pathname.slice(basePath.length) || '/';
    if (!protectedPaths.has(relativePath)) return null;
    if (url.search || url.hash) {
      throw new Error('يجب إرسال الطلبات المحمية دون معاملات أو أجزاء داخل عنوان URL.');
    }

    return {url, relativePath};
  }

  function parseJsonBody(options) {
    if (typeof options?.body !== 'string') {
      throw new Error('يجب إنشاء الطلب المحمي بجسم JSON نصي صريح حتى يمكن التحقق منه قبل الإرسال.');
    }
    if (new TextEncoder().encode(options.body).byteLength > MAX_JSON_BYTES) {
      throw new Error('حجم الطلب أكبر من الحد المسموح. قلّل البيانات أو استخدم مسار رفع المستندات الآمن.');
    }
    let body;
    try {
      body = JSON.parse(options.body);
    } catch (_) {
      throw new Error('تعذر قراءة بيانات الطلب بصيغة JSON صحيحة.');
    }
    if (!body || Array.isArray(body) || typeof body !== 'object') {
      throw new Error('يجب أن يكون جسم الطلب كائن JSON صالحًا.');
    }
    return body;
  }

  function requestIdentity(body) {
    const identity = body.submissionId || body.requestId;
    return typeof identity === 'string' && /^[a-z0-9-]{12,96}$/i.test(identity) ? identity : '';
  }

  function requireBoundTurnstileToken(body) {
    if (!config.turnstileSiteKey) return;
    const form = document.getElementById(formId);
    const currentToken = turnstileToken(form);
    const payloadToken = typeof body.turnstileToken === 'string' ? body.turnstileToken.trim() : '';
    if (!currentToken || !payloadToken || payloadToken !== currentToken) {
      throw new Error('رمز التحقق البشري مفقود أو غير مطابق للنموذج الحالي. أعد التحقق ثم حاول مرة أخرى.');
    }
  }

  function combinedAbortSignal(externalSignal, timeoutController) {
    if (!externalSignal) return timeoutController.signal;
    if (typeof AbortSignal.any === 'function') {
      return AbortSignal.any([externalSignal, timeoutController.signal]);
    }
    if (externalSignal.aborted) {
      timeoutController.abort(externalSignal.reason);
    } else {
      externalSignal.addEventListener('abort', () => timeoutController.abort(externalSignal.reason), {once: true});
    }
    return timeoutController.signal;
  }

  function installFetchGuard() {
    if (!apiBase || window.fetch.__ptSubmissionSecurity) return;
    const nativeFetch = window.fetch.bind(window);
    const guardedFetch = async (resource, options = {}) => {
      const target = parseProtectedRequest(resource, options);
      if (!target) return nativeFetch(resource, options);

      if (resource instanceof Request && options.body == null) {
        throw new Error('يجب إنشاء الطلب المحمي بجسم JSON صريح حتى يمكن التحقق منه قبل الإرسال.');
      }

      const body = parseJsonBody(options);
      const identity = requestIdentity(body);
      if (!identity) throw new Error('تعذر إنشاء معرّف آمن للطلب. أعد تحميل الصفحة وحاول مرة أخرى.');
      requireBoundTurnstileToken(body);

      const headers = new Headers(resource instanceof Request ? resource.headers : undefined);
      new Headers(options.headers || {}).forEach((value, key) => headers.set(key, value));
      if (headers.has('Authorization') || headers.has('Proxy-Authorization')) {
        throw new Error('لا يُسمح بإرسال بيانات اعتماد ضمن طلبات النماذج العامة.');
      }
      headers.set('Accept', 'application/json');
      headers.set('Content-Type', 'application/json;charset=UTF-8');
      headers.set('Idempotency-Key', identity);
      headers.set('X-Requested-With', 'pterminology-specialists');

      const timeoutController = new AbortController();
      const signal = combinedAbortSignal(options.signal || (resource instanceof Request ? resource.signal : null), timeoutController);
      const timeout = window.setTimeout(() => timeoutController.abort('request_timeout'), REQUEST_TIMEOUT_MS);
      try {
        return await nativeFetch(resource, {
          ...options,
          method: 'POST',
          headers,
          signal,
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
