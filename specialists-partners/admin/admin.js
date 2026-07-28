(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const state = {apiBase:'', adminKey:'', activeTab:'applications'};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));

  function setStatus(message, type = 'loading') {
    const box = $('admin-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = type;
    box.textContent = message;
    box.focus?.();
  }

  function apiUrl(path) {
    return `${String(state.apiBase || '').replace(/\/$/, '')}${path}`;
  }

  async function request(path, options = {}) {
    if (!state.apiBase || !state.adminKey) throw new Error('بيانات الاتصال الإدارية غير مكتملة.');
    const response = await fetch(apiUrl(path), {
      ...options,
      headers:{
        'content-type':'application/json',
        'x-admin-key':state.adminKey,
        ...(options.headers || {})
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || 'تعذر إكمال الطلب الإداري.');
      error.code = data.error || 'request_failed';
      throw error;
    }
    return data;
  }

  function formatDate(value) {
    if (!value) return '—';
    try { return new Date(value).toLocaleString('ar-JO'); }
    catch (_error) { return String(value); }
  }

  function statusLabel(value) {
    return ({
      pending:'بانتظار المراجعة',
      reviewing:'قيد المراجعة',
      approved:'مقبول',
      rejected:'مرفوض',
      withdrawn:'مسحوب',
      open:'مفتوحة',
      closed:'مغلقة',
      blocked:'محظورة',
      archived:'مؤرشفة',
      active:'نشط',
      suspended:'موقوف'
    })[value] || value;
  }

  function showConsole() {
    $('admin-console').hidden = false;
    document.querySelector('.admin-login')?.classList.add('connected');
  }

  function lockConsole() {
    state.adminKey = '';
    $('admin-api-key').value = '';
    $('admin-console').hidden = true;
    document.querySelector('.admin-login')?.classList.remove('connected');
    setStatus('تم قفل اللوحة ومسح مفتاح الإدارة من الذاكرة.', 'success');
  }

  async function loadOverview() {
    const data = await request('/v1/admin/overview');
    $('kpi-applications').textContent = data.applications.total;
    $('kpi-applications-detail').textContent =
      `${data.applications.pending} بانتظار المراجعة · ${data.applications.reviewing} قيد المراجعة`;
    $('kpi-conversations').textContent = data.conversations.total;
    $('kpi-conversations-detail').textContent =
      `${data.conversations.open} مفتوحة · ${data.conversations.blocked} محظورة`;
    $('kpi-providers').textContent = data.providers.total;
    $('kpi-providers-detail').textContent =
      `${data.providers.active} نشطة · ${data.providers.accepting} تستقبل طلبات`;
    $('kpi-email-failures').textContent = data.notifications.failedLast7Days;
  }

  function applicationCard(item) {
    const payload = item.payload || {};
    const location = [
      payload.location?.area,
      payload.location?.city,
      payload.location?.country
    ].filter(Boolean).join('، ');
    const specialties = (payload.specialties || []).map(value =>
      `<span class="chip">${esc(value)}</span>`).join('');
    const payloadText = esc(JSON.stringify(payload, null, 2));
    return `<article class="admin-card" data-application-id="${esc(item.id)}">
      <header class="admin-card-head">
        <div>
          <p class="eyebrow">${esc(item.referenceId)}</p>
          <h3>${esc(item.displayName)}</h3>
          <p>${esc(item.entityType)} · ${esc(location || 'الموقع غير محدد')}</p>
        </div>
        <span class="badge ${esc(item.status)}">${esc(statusLabel(item.status))}</span>
      </header>
      <div class="chips">${specialties}</div>
      <dl class="admin-details">
        <dt>البريد الخاص</dt><dd>${esc(item.email)}</dd>
        <dt>تاريخ الوصول</dt><dd>${esc(formatDate(item.createdAt))}</dd>
        <dt>آخر مراجعة</dt><dd>${esc(formatDate(item.reviewedAt))}</dd>
      </dl>
      <details>
        <summary>عرض سجل الطلب الكامل</summary>
        <pre>${payloadText}</pre>
      </details>
      <div class="form-grid admin-review-grid">
        <div class="field">
          <label>حالة المراجعة</label>
          <select data-field="status">
            ${['pending','reviewing','approved','rejected','withdrawn'].map(value =>
              `<option value="${value}" ${item.status === value ? 'selected' : ''}>${esc(statusLabel(value))}</option>`
            ).join('')}
          </select>
        </div>
        <div class="field">
          <label>معرف المختص عند القبول</label>
          <input data-field="providerId" pattern="[A-Za-z0-9-]{3,90}" placeholder="مثال: dr-example">
        </div>
        <div class="field full">
          <label>ملاحظات إدارية خاصة</label>
          <textarea data-field="adminNotes" maxlength="4000">${esc(item.adminNotes || '')}</textarea>
        </div>
        <div class="field full">
          <label>رسالة عامة لصاحب الطلب</label>
          <textarea data-field="publicMessage" maxlength="1000" placeholder="لا تضع ملاحظات داخلية هنا."></textarea>
        </div>
        <label class="check-field"><input data-field="notify" type="checkbox" checked> إرسال تحديث الحالة بالبريد</label>
        <label class="check-field"><input data-field="activateProvider" type="checkbox"> تفعيل حساب خاص عند القبول</label>
      </div>
      <div class="actions">
        <button class="button primary" type="button" data-action="save-application">حفظ المراجعة</button>
      </div>
    </article>`;
  }

  async function loadApplications() {
    const status = $('applications-filter').value;
    const query = new URLSearchParams({limit:'50'});
    if (status) query.set('status', status);
    const data = await request(`/v1/admin/applications?${query}`);
    $('applications-list').innerHTML = data.items.length
      ? data.items.map(applicationCard).join('')
      : '<div class="empty"><h3>لا توجد طلبات مطابقة</h3></div>';
  }

  async function saveApplication(card) {
    const id = card.dataset.applicationId;
    const status = card.querySelector('[data-field="status"]').value;
    const adminNotes = card.querySelector('[data-field="adminNotes"]').value.trim();
    const publicMessage = card.querySelector('[data-field="publicMessage"]').value.trim();
    const notify = card.querySelector('[data-field="notify"]').checked;
    const activateProvider = card.querySelector('[data-field="activateProvider"]').checked;
    const providerId = card.querySelector('[data-field="providerId"]').value.trim();
    const payload = {status, adminNotes, publicMessage, notify, reviewedBy:'site-owner'};

    if (status === 'approved' && activateProvider) {
      if (!providerId) throw new Error('أدخل معرف المختص قبل تفعيل الحساب.');
      const itemName = card.querySelector('h3')?.textContent?.trim() || '';
      const email = card.querySelector('.admin-details dd')?.textContent?.trim() || '';
      payload.provider = {
        providerId,
        displayName:itemName,
        email,
        status:'active',
        notificationEnabled:true,
        acceptsNewRequests:true
      };
    }

    await request(`/v1/admin/applications/${encodeURIComponent(id)}`, {
      method:'PATCH',
      body:JSON.stringify(payload)
    });
    setStatus('تم حفظ مراجعة طلب الانضمام.', 'success');
    await Promise.all([loadOverview(), loadApplications(), loadProviders()]);
  }

  function conversationCard(item) {
    return `<article class="admin-card" data-conversation-id="${esc(item.id)}">
      <header class="admin-card-head">
        <div>
          <p class="eyebrow">${esc(item.referenceId)}</p>
          <h3>${esc(item.providerDisplayName)}</h3>
          <p>${esc(item.topic)} · ${esc(item.urgency)}</p>
        </div>
        <span class="badge ${esc(item.status)}">${esc(statusLabel(item.status))}</span>
      </header>
      <dl class="admin-details">
        <dt>المرسل</dt><dd>${esc(item.visitorName)}</dd>
        <dt>البريد</dt><dd>${esc(item.visitorEmail)}</dd>
        <dt>عدد الرسائل</dt><dd>${esc(item.messageCount)}</dd>
        <dt>آخر نشاط</dt><dd>${esc(formatDate(item.lastMessageAt))}</dd>
      </dl>
      <div class="form-grid">
        <div class="field">
          <label>حالة المحادثة</label>
          <select data-field="conversationStatus">
            ${['open','closed','blocked','archived'].map(value =>
              `<option value="${value}" ${item.status === value ? 'selected' : ''}>${esc(statusLabel(value))}</option>`
            ).join('')}
          </select>
        </div>
        <div class="field full">
          <label>ملاحظات إدارية</label>
          <textarea data-field="conversationNotes" maxlength="4000">${esc(item.adminNotes || '')}</textarea>
        </div>
      </div>
      <button class="button primary" type="button" data-action="save-conversation">حفظ الحالة</button>
    </article>`;
  }

  async function loadConversations() {
    const status = $('conversations-filter').value;
    const query = new URLSearchParams({limit:'50'});
    if (status) query.set('status', status);
    const data = await request(`/v1/admin/conversations?${query}`);
    $('conversations-list').innerHTML = data.items.length
      ? data.items.map(conversationCard).join('')
      : '<div class="empty"><h3>لا توجد محادثات مطابقة</h3></div>';
  }

  async function saveConversation(card) {
    const id = card.dataset.conversationId;
    const status = card.querySelector('[data-field="conversationStatus"]').value;
    const adminNotes = card.querySelector('[data-field="conversationNotes"]').value.trim();
    await request(`/v1/admin/conversations/${encodeURIComponent(id)}`, {
      method:'PATCH',
      body:JSON.stringify({status, adminNotes})
    });
    setStatus('تم تحديث حالة المحادثة.', 'success');
    await Promise.all([loadOverview(), loadConversations()]);
  }

  function providerCard(item) {
    return `<article class="admin-card provider-row">
      <div>
        <p class="eyebrow">${esc(item.providerId)}</p>
        <h3>${esc(item.displayName)}</h3>
        <p>${esc(item.email)}</p>
      </div>
      <div class="chips">
        <span class="badge ${esc(item.status)}">${esc(statusLabel(item.status))}</span>
        <span class="chip">${item.notificationEnabled ? 'الإشعارات مفعلة' : 'الإشعارات متوقفة'}</span>
        <span class="chip">${item.acceptsNewRequests ? 'يستقبل طلبات' : 'لا يستقبل طلبات'}</span>
      </div>
    </article>`;
  }

  async function loadProviders() {
    const data = await request('/v1/admin/providers?limit=200');
    $('providers-list').innerHTML = data.items.length
      ? data.items.map(providerCard).join('')
      : '<div class="empty"><h3>لا توجد حسابات مختصين بعد</h3></div>';
  }

  async function saveProvider(event) {
    event.preventDefault();
    const payload = {
      providerId:$('provider-id').value.trim(),
      displayName:$('provider-display-name').value.trim(),
      email:$('provider-email').value.trim(),
      status:$('provider-status').value,
      notificationEnabled:$('provider-notifications').checked,
      acceptsNewRequests:$('provider-accepts').checked
    };
    await request('/v1/admin/providers', {
      method:'POST',
      body:JSON.stringify(payload)
    });
    setStatus('تم حفظ حساب المختص الخاص.', 'success');
    event.currentTarget.reset();
    $('provider-notifications').checked = true;
    $('provider-accepts').checked = true;
    await Promise.all([loadOverview(), loadProviders()]);
  }

  function auditCard(item) {
    return `<article class="admin-card audit-row">
      <div><p class="eyebrow">${esc(item.eventType)}</p><h3>${esc(item.entityId)}</h3></div>
      <time datetime="${esc(item.createdAt)}">${esc(formatDate(item.createdAt))}</time>
      <pre>${esc(JSON.stringify(item.metadata || {}, null, 2))}</pre>
    </article>`;
  }

  async function loadAudit() {
    const data = await request('/v1/admin/audit?limit=100');
    $('audit-list').innerHTML = data.items.length
      ? data.items.map(auditCard).join('')
      : '<div class="empty"><h3>لا توجد أحداث مسجلة</h3></div>';
  }

  async function refreshAll() {
    setStatus('جارٍ تحديث بيانات القطاع…', 'loading');
    await Promise.all([
      loadOverview(),
      loadApplications(),
      loadConversations(),
      loadProviders(),
      loadAudit()
    ]);
    setStatus('تم تحديث لوحة الإدارة.', 'success');
  }

  function activateTab(name) {
    state.activeTab = name;
    document.querySelectorAll('[data-admin-tab]').forEach(button =>
      button.classList.toggle('active', button.dataset.adminTab === name));
    document.querySelectorAll('[data-admin-panel]').forEach(panel =>
      panel.classList.toggle('active', panel.dataset.adminPanel === name));
  }

  function bindEvents() {
    $('admin-auth-form').addEventListener('submit', async event => {
      event.preventDefault();
      state.apiBase = $('admin-api-base').value.trim().replace(/\/$/, '');
      state.adminKey = $('admin-api-key').value;
      try {
        await loadOverview();
        showConsole();
        await Promise.all([loadApplications(), loadConversations(), loadProviders(), loadAudit()]);
        setStatus('تم فتح لوحة الإدارة بنجاح.', 'success');
      } catch (error) {
        state.adminKey = '';
        setStatus(error.message || 'تعذر فتح لوحة الإدارة.', 'error');
      }
    });

    $('admin-refresh').addEventListener('click', () =>
      refreshAll().catch(error => setStatus(error.message, 'error')));
    $('admin-lock').addEventListener('click', lockConsole);
    $('applications-filter').addEventListener('change', () =>
      loadApplications().catch(error => setStatus(error.message, 'error')));
    $('conversations-filter').addEventListener('change', () =>
      loadConversations().catch(error => setStatus(error.message, 'error')));
    $('provider-form').addEventListener('submit', event =>
      saveProvider(event).catch(error => setStatus(error.message, 'error')));

    document.querySelector('.admin-tabs').addEventListener('click', event => {
      const button = event.target.closest('[data-admin-tab]');
      if (button) activateTab(button.dataset.adminTab);
    });

    $('applications-list').addEventListener('click', event => {
      const button = event.target.closest('[data-action="save-application"]');
      if (!button) return;
      button.disabled = true;
      saveApplication(button.closest('[data-application-id]'))
        .catch(error => setStatus(error.message, 'error'))
        .finally(() => { button.disabled = false; });
    });

    $('conversations-list').addEventListener('click', event => {
      const button = event.target.closest('[data-action="save-conversation"]');
      if (!button) return;
      button.disabled = true;
      saveConversation(button.closest('[data-conversation-id]'))
        .catch(error => setStatus(error.message, 'error'))
        .finally(() => { button.disabled = false; });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('admin-api-base').value = String(config.apiBase || '');
    bindEvents();
  });
})();
