(() => {
  'use strict';

  const REFRESH_INTERVAL_MS = 12_000;
  const MESSAGE_PATH = /\/v1\/conversations\/[a-z0-9-]+\/messages$/i;

  function randomMessageKey() {
    if (crypto.randomUUID) return `message-${crypto.randomUUID()}`;
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return `message-${Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')}`;
  }

  function migrateLegacyQueryCredentials() {
    const url = new URL(location.href);
    const conversation = url.searchParams.get('conversation');
    const token = url.searchParams.get('token');
    const role = url.searchParams.get('role');
    if (!conversation && !token && !role) return;

    const fragment = new URLSearchParams(location.hash.replace(/^#/, ''));
    if (conversation && !fragment.has('conversation')) fragment.set('conversation', conversation);
    if (token && !fragment.has('token')) fragment.set('token', token);
    if (role && !fragment.has('role')) fragment.set('role', role);
    url.searchParams.delete('conversation');
    url.searchParams.delete('token');
    url.searchParams.delete('role');
    url.hash = fragment.toString();
    history.replaceState(null, document.title, `${url.pathname}${url.search}${url.hash}`);
  }

  function installMessageIdempotency() {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
      const method = String(init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
      let url;
      try { url = new URL(input instanceof Request ? input.url : String(input), location.href); }
      catch (_) { return nativeFetch(input, init); }
      if (method !== 'POST' || !MESSAGE_PATH.test(url.pathname)) return nativeFetch(input, init);

      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      if (!headers.has('idempotency-key')) headers.set('idempotency-key', randomMessageKey());
      return nativeFetch(input, {...init, headers});
    };
  }

  function setLiveState(text) {
    const node = document.getElementById('live-sync-state');
    if (node) node.textContent = text;
  }

  function startLiveRefresh() {
    const refresh = document.getElementById('refresh-conversation');
    if (!refresh) return;
    let timer = 0;

    const sync = () => {
      if (document.visibilityState !== 'visible' || !navigator.onLine) return;
      refresh.click();
      setLiveState(`تحديث تلقائي نشط · ${new Date().toLocaleTimeString('ar-JO', {hour:'2-digit', minute:'2-digit'})}`);
    };
    const schedule = () => {
      window.clearInterval(timer);
      timer = window.setInterval(sync, REFRESH_INTERVAL_MS);
    };

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') sync();
    });
    window.addEventListener('online', () => { setLiveState('عاد الاتصال؛ جارٍ تحديث الرسائل.'); sync(); });
    window.addEventListener('offline', () => setLiveState('انقطع الاتصال؛ ستتم المزامنة تلقائيًا عند عودته.'));
    window.addEventListener('pagehide', () => window.clearInterval(timer), {once:true});
    schedule();
    setLiveState('تحديث تلقائي كل 12 ثانية.');
  }

  migrateLegacyQueryCredentials();
  installMessageIdempotency();
  document.addEventListener('DOMContentLoaded', startLiveRefresh);
})();
