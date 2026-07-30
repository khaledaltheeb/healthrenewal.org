(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const SESSION_KEY = 'ptSpecialistAccountSession';
  const $ = id => document.getElementById(id);
  const state = {sessionToken:'', me:null, conversations:[], activeConversation:null};

  function apiBase() {
    const candidate = String(config.accountApiBase || 'https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev').trim();
    try {
      const parsed = new URL(candidate);
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.search || parsed.hash) return '';
      return parsed.href.replace(/\/$/, '');
    } catch (_) {
      return '';
    }
  }

  function status(message, type = 'loading') {
    const box = $('account-status');
    box.hidden = false;
    box.dataset.state = type;
    box.textContent = message;
    box.focus?.();
  }

  function clearStatus() {
    const box = $('account-status');
    box.hidden = true;
    box.textContent = '';
  }

  function randomId(prefix = 'request') {
    if (crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')}`;
  }

  async function api(path, options = {}, authenticated = true) {
    const base = apiBase();
    if (!base) throw new Error('خدمة حسابات المختصين لم تُربط بعد.');
    const headers = new Headers(options.headers || {});
    headers.set('accept', 'application/json');
    headers.set('x-requested-with', 'pterminology-specialist-account');
    if (options.body != null) headers.set('content-type', 'application/json;charset=UTF-8');
    if (authenticated) {
      if (!state.sessionToken) throw new Error('يلزم تسجيل الدخول.');
      headers.set('authorization', `Bearer ${state.sessionToken}`);
    }
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    let response;
    try {
      response = await fetch(`${base}${path}`, {
        ...options,
        headers,
        cache:'no-store',
        credentials:'omit',
        redirect:'error',
        referrerPolicy:'no-referrer',
        signal:controller.signal
      });
    } finally {
      window.clearTimeout(timeout);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || 'تعذر إكمال الطلب.');
      error.code = data.error || 'request_failed';
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function loadSession() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!parsed?.token || !parsed?.expiresAt || Date.parse(parsed.expiresAt) <= Date.now()) {
        sessionStorage.removeItem(SESSION_KEY);
        return;
      }
      state.sessionToken = parsed.token;
    } catch (_) {
      sessionStorage.removeItem(SESSION_KEY);
    }
  }

  function saveSession(token, expiresAt) {
    state.sessionToken = token;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({token, expiresAt}));
  }

  function clearSession() {
    state.sessionToken = '';
    state.me = null;
    state.conversations = [];
    state.activeConversation = null;
    sessionStorage.removeItem(SESSION_KEY);
  }

  function showLogin() {
    $('login-panel').hidden = false;
    $('dashboard').hidden = true;
  }

  function showDashboard() {
    $('login-panel').hidden = true;
    $('dashboard').hidden = false;
  }

  function initTurnstile() {
    const target = $('turnstile-box');
    if (!target || !config.turnstileSiteKey) return;
    const render = () => {
      if (window.turnstile && !target.dataset.rendered) {
        window.turnstile.render(target, {
          sitekey:config.turnstileSiteKey,
          theme:'light',
          language:'ar',
          action:'specialist_login'
        });
        target.dataset.rendered = 'true';
      }
    };
    if (window.turnstile) render();
    else {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.onload = render;
      document.head.append(script);
    }
  }

  function turnstileToken(form) {
    return form.querySelector('[name="cf-turnstile-response"]')?.value || '';
  }

  async function requestLogin(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const token = turnstileToken(form);
    if (config.turnstileSiteKey && !token) {
      status('أكمل التحقق من الاستخدام البشري.', 'error');
      return;
    }
    const button = $('request-login');
    button.disabled = true;
    status('جارٍ إرسال رابط الدخول…', 'loading');
    try {
      const result = await api('/v1/specialist/session/request', {
        method:'POST',
        body:JSON.stringify({email:$('login-email').value.trim(), turnstileToken:token})
      }, false);
      status(result.message || 'تحقق من بريدك لفتح الحساب.', 'success');
      form.reset();
      window.turnstile?.reset?.();
    } catch (error) {
      status(error.message || 'تعذر إرسال رابط الدخول.', 'error');
      window.turnstile?.reset?.();
    } finally {
      button.disabled = false;
    }
  }

  function loginTokenFromFragment() {
    const fragment = new URLSearchParams(location.hash.replace(/^#/, ''));
    const token = fragment.get('loginToken') || '';
    if (location.hash) history.replaceState(null, document.title, `${location.pathname}${location.search}`);
    return token;
  }

  async function verifyMagicLink(token) {
    status('جارٍ التحقق من رابط الدخول…', 'loading');
    try {
      const result = await api('/v1/specialist/session/verify', {
        method:'POST',
        body:JSON.stringify({token})
      }, false);
      saveSession(result.sessionToken, result.expiresAt);
      status('تم تسجيل الدخول بنجاح.', 'success');
      await loadDashboard();
    } catch (error) {
      clearSession();
      showLogin();
      status(error.message || 'رابط الدخول غير صالح أو انتهت صلاحيته.', 'error');
    }
  }

  function labelStatus(value) {
    return ({open:'مفتوحة',closed:'مغلقة',blocked:'محظورة',archived:'مؤرشفة',
      published:'منشور',review:'قيد المراجعة',draft:'مسودة',suspended:'موقوف',
      verified:'موثّق',provisional:'مؤقت',pending:'قيد التحقق',expired:'منتهي',
      rejected:'مرفوض',approved:'معتمد',revoked:'مسحوب'})[value] || value || '—';
  }

  function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ar-JO', {dateStyle:'medium', timeStyle:'short'});
  }

  function renderProfile(data) {
    const provider = data.provider;
    $('profile-title').textContent = provider.displayName;
    $('profile-publication').textContent = labelStatus(provider.publicationStatus);
    $('profile-verification').textContent = labelStatus(provider.verificationStatus);
    $('profile-availability').textContent = provider.acceptsNewRequests ? 'يستقبل طلبات جديدة' : 'متوقف مؤقتًا';
    $('session-expiry').textContent = formatDate(data.session.expiresAt);
  }

  function createElement(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function renderConversationList() {
    const container = $('conversation-list');
    container.replaceChildren();
    $('conversation-count').textContent = String(state.conversations.length);
    if (!state.conversations.length) {
      container.append(createElement('p', 'account-empty', 'لا توجد محادثات مطابقة.'));
      return;
    }
    for (const conversation of state.conversations) {
      const button = createElement('button', 'account-conversation-card');
      button.type = 'button';
      button.dataset.conversationId = conversation.id;
      button.setAttribute('aria-current', state.activeConversation?.conversation?.id === conversation.id ? 'true' : 'false');
      button.append(
        createElement('strong', '', conversation.visitorName || 'مستخدم المنصة'),
        createElement('span', '', conversation.topic || 'دون موضوع'),
        createElement('small', '', conversation.lastMessage || 'لا توجد معاينة'),
      );
      const row = createElement('div', 'account-card-row');
      const badge = createElement('span', `badge ${conversation.status}`, labelStatus(conversation.status));
      const time = createElement('time', '', formatDate(conversation.lastMessageAt));
      time.dateTime = conversation.lastMessageAt || '';
      row.append(badge, time);
      button.append(row);
      button.addEventListener('click', () => openConversation(conversation.id));
      container.append(button);
    }
  }

  async function loadConversations() {
    const statusFilter = $('status-filter').value;
    const query = new URLSearchParams({limit:'100'});
    if (statusFilter) query.set('status', statusFilter);
    const data = await api(`/v1/specialist/conversations?${query}`);
    state.conversations = data.conversations || [];
    renderConversationList();
  }

  function renderContext(conversation) {
    const container = $('conversation-context');
    container.replaceChildren();
    const values = [
      ['المرجع', conversation.referenceId],
      ['الاسم', conversation.visitorName],
      ['الموضوع', conversation.topic],
      ['الأولوية', conversation.urgency],
      ['الفئة العمرية', conversation.context?.ageGroup],
      ['طريقة الخدمة', conversation.context?.preferredMode],
      ['وقت التواصل المفضل', conversation.context?.preferredContactTime]
    ].filter(([, value]) => value);
    const list = createElement('dl');
    for (const [term, value] of values) {
      const item = createElement('div');
      item.append(createElement('dt', '', term), createElement('dd', '', value));
      list.append(item);
    }
    container.append(list);
    container.hidden = values.length === 0;
  }

  function renderMessages(messages) {
    const container = $('message-list');
    container.replaceChildren();
    if (!messages.length) {
      container.append(createElement('p', 'small', 'لا توجد رسائل بعد.'));
      return;
    }
    for (const message of messages) {
      const mine = message.senderRole === 'specialist';
      const article = createElement('article', `message ${message.senderRole === 'system' ? 'system' : mine ? 'mine' : 'theirs'}`);
      article.append(createElement('p', '', message.body));
      const time = createElement('time', '', formatDate(message.createdAt));
      time.dateTime = message.createdAt;
      article.append(time);
      container.append(article);
    }
    container.scrollTop = container.scrollHeight;
  }

  function renderActiveConversation() {
    const data = state.activeConversation;
    if (!data) return;
    const conversation = data.conversation;
    $('conversation-title').textContent = `محادثة مع ${conversation.visitorName || 'مستخدم المنصة'}`;
    $('conversation-summary').textContent = `${conversation.referenceId} · ${conversation.topic} · آخر تحديث ${formatDate(conversation.lastMessageAt)}`;
    const badge = $('conversation-status');
    badge.textContent = labelStatus(conversation.status);
    badge.className = `badge ${conversation.status}`;
    renderContext(conversation);
    renderMessages(data.messages || []);
    const form = $('message-form');
    form.hidden = false;
    const locked = ['blocked','archived'].includes(conversation.status);
    const closed = conversation.status === 'closed';
    $('message-body').disabled = locked || closed;
    $('send-message').disabled = locked || closed;
    const toggle = $('toggle-status');
    toggle.disabled = locked;
    toggle.dataset.nextStatus = closed ? 'open' : 'closed';
    toggle.textContent = closed ? 'إعادة فتح المحادثة' : 'إغلاق المحادثة';
    renderConversationList();
  }

  async function openConversation(conversationId) {
    status('جارٍ تحميل المحادثة…', 'loading');
    try {
      state.activeConversation = await api(`/v1/specialist/conversations/${encodeURIComponent(conversationId)}`);
      renderActiveConversation();
      clearStatus();
    } catch (error) {
      handleAuthError(error);
      status(error.message || 'تعذر تحميل المحادثة.', 'error');
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!state.activeConversation) return;
    const body = $('message-body').value.trim();
    if (!body) return;
    const button = $('send-message');
    button.disabled = true;
    status('جارٍ إرسال الرد…', 'loading');
    try {
      await api(`/v1/specialist/conversations/${encodeURIComponent(state.activeConversation.conversation.id)}/messages`, {
        method:'POST',
        headers:{'idempotency-key':randomId('specialist-message')},
        body:JSON.stringify({body})
      });
      $('message-body').value = '';
      await Promise.all([openConversation(state.activeConversation.conversation.id), loadConversations()]);
      status('تم إرسال الرد وإشعار المستخدم.', 'success');
    } catch (error) {
      handleAuthError(error);
      status(error.message || 'تعذر إرسال الرد.', 'error');
    } finally {
      button.disabled = false;
    }
  }

  async function toggleConversationStatus() {
    if (!state.activeConversation) return;
    const button = $('toggle-status');
    const nextStatus = button.dataset.nextStatus || 'closed';
    button.disabled = true;
    status('جارٍ تحديث حالة المحادثة…', 'loading');
    try {
      await api(`/v1/specialist/conversations/${encodeURIComponent(state.activeConversation.conversation.id)}`, {
        method:'PATCH',
        body:JSON.stringify({status:nextStatus})
      });
      await Promise.all([openConversation(state.activeConversation.conversation.id), loadConversations()]);
      status(nextStatus === 'closed' ? 'تم إغلاق المحادثة.' : 'تمت إعادة فتح المحادثة.', 'success');
    } catch (error) {
      handleAuthError(error);
      status(error.message || 'تعذر تحديث حالة المحادثة.', 'error');
    } finally {
      button.disabled = false;
    }
  }

  function handleAuthError(error) {
    if (error?.status === 401 || error?.code === 'session_expired') {
      clearSession();
      showLogin();
      initTurnstile();
    }
  }

  async function loadDashboard() {
    showDashboard();
    try {
      const [me] = await Promise.all([api('/v1/specialist/me'), loadConversations()]);
      state.me = me;
      renderProfile(me);
      clearStatus();
    } catch (error) {
      handleAuthError(error);
      status(error.message || 'تعذر تحميل حساب المختص.', 'error');
    }
  }

  async function logout() {
    try {
      if (state.sessionToken) await api('/v1/specialist/session/revoke', {method:'POST', body:'{}'});
    } catch (_) {
      // Local revocation still removes the browser credential.
    }
    clearSession();
    showLogin();
    initTurnstile();
    status('تم تسجيل الخروج.', 'success');
  }

  async function refreshDashboard() {
    status('جارٍ تحديث الحساب والمحادثات…', 'loading');
    await loadDashboard();
  }

  document.addEventListener('DOMContentLoaded', async () => {
    $('login-form').addEventListener('submit', requestLogin);
    $('message-form').addEventListener('submit', sendMessage);
    $('toggle-status').addEventListener('click', toggleConversationStatus);
    $('status-filter').addEventListener('change', loadConversations);
    $('refresh-dashboard').addEventListener('click', refreshDashboard);
    $('logout').addEventListener('click', logout);

    loadSession();
    const magicToken = loginTokenFromFragment();
    if (magicToken) {
      await verifyMagicLink(magicToken);
      return;
    }
    if (state.sessionToken) {
      await loadDashboard();
    } else {
      showLogin();
      initTurnstile();
    }
  });
})();
