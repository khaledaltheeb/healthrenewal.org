(() => {
  'use strict';

  const IDENTITY_API = 'https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev';
  const CORE_API = 'https://pterminology-specialists.pterminology-826ac349.workers.dev';
  const TURNSTILE_SITE_KEY = '0x4AAAAAAD_r2o__Ao1RmBTO';
  const REQUEST_TIMEOUT_MS = 18_000;
  const SESSION_KEYS = [
    'ptIdentitySessionV6',
    'ptAdminIdentityV6',
    'ptSpecialistAccountSessionV5',
    'ptSpecialistSessionV5',
    'ptSpecialistSession',
    'ptAdminSessionV4',
  ];

  const $ = (id) => document.getElementById(id);

  function setStatus(message, state = 'loading') {
    const box = $('recover-status');
    box.textContent = message;
    box.dataset.state = state;
    box.focus?.();
  }

  function extractToken(raw) {
    try {
      const data = JSON.parse(raw || 'null');
      return data?.token || data?.sessionToken || data?.accessToken || '';
    } catch (_) {
      return '';
    }
  }

  async function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeout);
    try {
      return await fetch(url, {
        ...options,
        mode: 'cors',
        redirect: 'follow',
        signal: controller.signal,
      });
    } catch (error) {
      const networkError = new Error(
        error?.name === 'AbortError'
          ? 'انتهت مهلة الاتصال بخدمة الحسابات. حاول مرة أخرى بعد لحظات.'
          : 'تعذر الاتصال بخدمة الحسابات. تحقق من الاتصال أو أعد المحاولة بعد اكتمال نشر الخدمة.',
      );
      networkError.code = error?.name === 'AbortError' ? 'request_timeout' : 'network_unavailable';
      networkError.networkFailure = true;
      throw networkError;
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function remoteRevoke(token, base) {
    if (!token) return;
    try {
      await fetchWithTimeout(`${base}/v1/auth/logout`, {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json;charset=UTF-8',
          'x-requested-with': 'pterminology-recovery-v10.3',
          authorization: `Bearer ${token}`,
        },
        body: '{}',
        cache: 'no-store',
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
      }, 6_000);
    } catch (_) {
      // Local session removal remains authoritative for this browser tab.
    }
  }

  async function clearSessions() {
    const tokens = [];
    for (const key of SESSION_KEYS) {
      const token = extractToken(sessionStorage.getItem(key));
      if (token) tokens.push(token);
      sessionStorage.removeItem(key);
    }

    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index) || '';
      if (!/^pt(?:Identity|Admin|Specialist).*Session/i.test(key)) continue;
      const token = extractToken(sessionStorage.getItem(key));
      if (token) tokens.push(token);
      sessionStorage.removeItem(key);
    }

    await Promise.allSettled(tokens.flatMap((token) => [
      remoteRevoke(token, IDENTITY_API),
      remoteRevoke(token, CORE_API),
    ]));

    $('session-result').textContent = 'تم حذف الجلسة المحلية القديمة من هذه النافذة. يمكنك الآن طلب رابط جديد أو العودة لتسجيل الدخول.';
    setStatus('تم تسجيل الخروج محليًا وتنظيف الجلسة القديمة.', 'success');
  }

  function initTurnstile() {
    const render = () => {
      if (!window.turnstile) return;
      const target = $('recover-turnstile');
      if (!target || target.dataset.rendered) return;
      window.turnstile.render(target, {
        sitekey: TURNSTILE_SITE_KEY,
        theme: 'light',
        language: 'ar',
        action: 'password_reset',
      });
      target.dataset.rendered = 'true';
    };

    if (window.turnstile) {
      render();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.onload = render;
    script.onerror = () => setStatus('تعذر تحميل التحقق البشري. أعد تحميل الصفحة ثم حاول مرة أخرى.', 'error');
    document.head.append(script);
  }

  function turnstileToken() {
    return $('recover-turnstile')?.querySelector('[name="cf-turnstile-response"]')?.value || '';
  }

  async function postReset(base, payload) {
    const response = await fetchWithTimeout(`${base}/v1/auth/password/request`, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json;charset=UTF-8',
        'x-requested-with': 'pterminology-recovery-v10.3',
      },
      body: JSON.stringify(payload),
      cache: 'no-store',
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    });
    const data = await response.json().catch(() => ({}));
    return { response, data, base };
  }

  async function requestReset(payload) {
    try {
      const primary = await postReset(IDENTITY_API, payload);
      if (primary.response.status !== 404) return primary;
    } catch (error) {
      if (!error.networkFailure) throw error;
    }

    try {
      return await postReset(CORE_API, payload);
    } catch (error) {
      if (!error.networkFailure) throw error;
      const unavailable = new Error('خدمة استعادة الحساب غير متاحة من عنوانَي التشغيل حاليًا. لم يُرسل رابط. حاول مرة أخرى بعد دقائق.');
      unavailable.code = 'all_account_endpoints_unavailable';
      throw unavailable;
    }
  }

  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;

    const token = turnstileToken();
    if (!token) {
      setStatus('أكمل التحقق من الاستخدام البشري.', 'error');
      return;
    }

    const button = $('recover-submit');
    button.disabled = true;
    setStatus('جارٍ الاتصال بخدمة الحسابات وإرسال رابط إعادة التعيين…');

    const payload = {
      email: $('recover-email').value.trim(),
      turnstileToken: token,
    };

    try {
      const result = await requestReset(payload);
      if (!result.response.ok) {
        throw new Error(result.data.message || `تعذر إرسال الرابط (HTTP ${result.response.status}).`);
      }
      setStatus(result.data.message || 'تم قبول الطلب. افحص البريد خلال دقائق.', 'success');
      form.reset();
      $('recover-email').value = 'pterminology@gmail.com';
    } catch (error) {
      setStatus(error.message || 'تعذر إرسال رابط إعادة التعيين. لم يُرسل رابط.', 'error');
    } finally {
      try {
        window.turnstile?.reset?.();
      } catch (_) {
        // The next page load can recreate the widget if reset is unavailable.
      }
      button.disabled = false;
    }
  }

  async function init() {
    await clearSessions();
    initTurnstile();
    $('recover-form').addEventListener('submit', submit);
  }

  init();
})();
