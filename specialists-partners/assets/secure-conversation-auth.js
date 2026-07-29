(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const apiBase = String(config.apiBase || '').replace(/\/$/, '');
  const nativeFetch = window.fetch.bind(window);
  const allowedRoles = new Set(['visitor', 'provider', 'reviewer', 'admin']);

  function isConversationApi(url) {
    if (!apiBase) return false;
    try {
      const target = new URL(url, location.href);
      const base = new URL(`${apiBase}/`, location.href);
      return target.origin === base.origin &&
        target.pathname.startsWith(`${base.pathname.replace(/\/$/, '')}/v1/conversations/`);
    } catch (_) {
      return false;
    }
  }

  function readJsonBody(body) {
    if (typeof body !== 'string' || !body.trim()) return null;
    try {
      const parsed = JSON.parse(body);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  function sanitizeRole(value) {
    return allowedRoles.has(value) ? value : 'visitor';
  }

  window.fetch = async function secureConversationFetch(input, init = {}) {
    const rawUrl = input instanceof Request ? input.url : String(input);
    if (!isConversationApi(rawUrl)) return nativeFetch(input, init);

    const url = new URL(rawUrl, location.href);
    const originalRequest = input instanceof Request ? input : null;
    const requestInit = {...init};
    const headers = new Headers(originalRequest?.headers || {});
    new Headers(init.headers || {}).forEach((value, key) => headers.set(key, value));

    const jsonBody = readJsonBody(requestInit.body);
    const token =
      url.searchParams.get('token') ||
      jsonBody?.token ||
      sessionStorage.getItem('ptConversationToken') ||
      '';
    const role = sanitizeRole(
      url.searchParams.get('role') ||
      jsonBody?.role ||
      sessionStorage.getItem('ptConversationRole') ||
      'visitor'
    );

    url.searchParams.delete('token');
    url.searchParams.delete('role');

    if (jsonBody) {
      delete jsonBody.token;
      delete jsonBody.role;
      requestInit.body = JSON.stringify(jsonBody);
    }

    if (token) headers.set('authorization', `Bearer ${token}`);
    headers.set('x-conversation-role', role);
    headers.set('cache-control', 'no-store');
    requestInit.headers = headers;
    requestInit.cache = 'no-store';
    requestInit.referrerPolicy = 'no-referrer';

    return nativeFetch(url.toString(), requestInit);
  };
})();
