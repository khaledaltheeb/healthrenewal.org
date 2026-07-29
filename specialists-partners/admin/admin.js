(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const state = {
    apiBase:'',
    accessToken:'',
    role:'',
    actorLabel:'',
    expiresAt:'',
    permissions:new Set(),
    activeTab:'applications',
    applications:[],
    providers:[]
  };
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));
  const list = value => String(value || '').split(/[،,\n]/)
    .map(item => item.trim()).filter(Boolean);
  const selected = id => Array.from($(id)?.selectedOptions || []).map(option => option.value);
  const today = () => new Date().toISOString().slice(0, 10);
  const plusOneYear = () => {
    const date = new Date();
    date.setUTCFullYear(date.getUTCFullYear() + 1);
    return date.toISOString().slice(0, 10);
  };

  function setStatus(message, type = 'loading') {
    const box = $('admin-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = type;
    box.textContent = message;
    box.focus?.();
  }

  function validatedApiBase(value) {
    try {
      const parsed = new URL(String(value || '').trim());
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
          parsed.search || parsed.hash) {
        throw new Error('invalid');
      }
      return parsed.href.replace(/\/$/, '');
    } catch (_) {
      throw new Error('أدخل عنوان Worker صحيحًا يبدأ بـ https ولا يحتوي بيانات دخول أو معاملات.');
    }
  }

  function apiUrl(path) {
    return `${state.apiBase}${path}`;
  }

  async function createSession(apiBase, key) {
    const response = await fetch(`${apiBase}/v1/admin/session`, {
      method:'POST',
      headers:{
        accept:'application/json',
        'x-admin-key':key
      },
      cache:'no-store',
      credentials:'omit',
      referrerPolicy:'no-referrer',
      redirect:'error'
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'تعذر إنشاء الجلسة الإدارية.');
    return data;
  }

  async function request(path, options = {}) {
    if (!state.apiBase || !state.accessToken) {
      throw new Error('جلسة الإدارة غير مفتوحة.');
    }
    const headers = new Headers(options.headers || {});
    headers.set('accept', 'application/json');
    headers.set('authorization', `Bearer ${state.accessToken}`);
    if (options.body != null) headers.set('content-type', 'application/json;charset=UTF-8');
    const response = await fetch(apiUrl(path), {
      ...options,
      headers,
      cache:'no-store',
      credentials:'omit',
      referrerPolicy:'no-referrer',
      redirect:'error'
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) lockConsole(false);
      const error = new Error(data.message || 'تعذر إكمال الطلب الإداري.');
      error.code = data.error || 'request_failed';
      throw error;
    }
    return data;
  }

  function formatDate(value) {
    if (!value) return '—';
    try { return new Date(value).toLocaleString('ar-JO'); }
    catch (_) { return String(value); }
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
      suspended:'موقوف',
      draft:'مسودة',
      review:'بانتظار الاعتماد',
      published:'منشور',
      save_draft:'حفظ مسودة',
      submit_review:'إرسال للمراجعة',
      approve_publish:'اعتماد ونشر',
      revoke_consent:'سحب موافقة النشر',
      verified:'موثّق',
      provisional:'تحقق أولي',
      expired:'منتهي التحقق',
      revoked:'مسحوبة'
    })[value] || value || '—';
  }

  function roleLabel(role) {
    return ({
      owner:'المالك — صلاحية كاملة',
      reviewer:'مراجع مهني — مراجعة دون نشر',
      moderator:'مشرف محادثات — إشراف دون نشر'
    })[role] || role;
  }

  function has(permission) {
    return state.permissions.has(permission);
  }

  function showConsole() {
    $('admin-console').hidden = false;
    document.querySelector('.admin-login')?.classList.add('connected');
  }

  function clearSessionState() {
    state.accessToken = '';
    state.role = '';
    state.actorLabel = '';
    state.expiresAt = '';
    state.permissions = new Set();
    $('admin-api-key').value = '';
    $('admin-console').hidden = true;
    document.querySelector('.admin-login')?.classList.remove('connected');
  }

  async function lockConsole(revoke = true) {
    if (revoke && state.accessToken) {
      try { await request('/v1/admin/session/revoke', {method:'POST'}); }
      catch (_) { /* انتهاء الجلسة يحقق الغرض نفسه. */ }
    }
    clearSessionState();
    setStatus('تم قفل اللوحة ومسح بيانات الجلسة من الذاكرة.', 'success');
  }

  function applyRoleUi() {
    const roleText = roleLabel(state.role);
    $('admin-role-summary').textContent =
      `${roleText}. تنتهي الجلسة: ${formatDate(state.expiresAt)}.`;
    document.querySelectorAll('[data-owner-only]').forEach(element => {
      element.hidden = state.role !== 'owner';
    });
    const tabPermissions = {
      applications:'applications:read',
      conversations:'conversations:moderate',
      providers:'providers:read',
      audit:'audit:read'
    };
    document.querySelectorAll('[data-admin-tab]').forEach(button => {
      button.hidden = !has(tabPermissions[button.dataset.adminTab]);
    });
    const firstVisible = Array.from(document.querySelectorAll('[data-admin-tab]'))
      .find(button => !button.hidden);
    if (firstVisible && document.querySelector(`[data-admin-tab="${state.activeTab}"]`)?.hidden) {
      activateTab(firstVisible.dataset.adminTab);
    }
  }

  async function loadOverview() {
    const data = await request('/v1/admin/overview');
    state.role = data.authorization?.role || state.role;
    state.actorLabel = data.authorization?.actorLabel || '';
    state.expiresAt = data.authorization?.expiresAt || state.expiresAt;
    state.permissions = new Set(data.authorization?.permissions || []);
    $('kpi-applications').textContent = data.applications.total;
    $('kpi-applications-detail').textContent =
      `${data.applications.pending} بانتظار المراجعة · ${data.applications.reviewing} قيد المراجعة`;
    $('kpi-conversations').textContent = data.conversations.total;
    $('kpi-conversations-detail').textContent =
      `${data.conversations.open} مفتوحة · ${data.conversations.blocked} محظورة`;
    $('kpi-providers').textContent = data.providers.total;
    $('kpi-providers-detail').textContent =
      `${data.providers.active} نشطة · ${data.providers.accepting} تستقبل طلبات`;
    $('kpi-published').textContent = data.profiles?.published || 0;
    $('kpi-published-detail').textContent =
      `${data.profiles?.review_due || 0} تحتاج مراجعة خلال 30 يومًا · ${data.profiles?.expired || 0} منتهية`;
    $('kpi-email-failures').textContent = data.notifications.failedLast7Days;
    applyRoleUi();
  }

  function applicationCard(item) {
    const payload = item.payload || {};
    const location = [
      payload.location?.area,
      payload.location?.city,
      payload.location?.country
    ].filter(Boolean).join('، ');
    const specialties = (payload.specialties || [])
      .map(value => `<span class="chip">${esc(value)}</span>`).join('');
    const statuses = state.role === 'owner'
      ? ['pending','reviewing','approved','rejected','withdrawn']
      : ['pending','reviewing'];
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
        <summary>عرض الطلب الخاص للمراجعة</summary>
        <pre>${esc(JSON.stringify(payload, null, 2))}</pre>
      </details>
      <div class="form-grid admin-review-grid">
        <div class="field">
          <label>حالة المراجعة</label>
          <select data-field="status">
            ${statuses.map(value =>
              `<option value="${value}" ${item.status === value ? 'selected' : ''}>${esc(statusLabel(value))}</option>`
            ).join('')}
          </select>
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
      </div>
      <div class="actions">
        <button class="button secondary" type="button" data-action="save-application">حفظ حالة المراجعة</button>
        ${state.role === 'owner' ? '<button class="button primary" type="button" data-action="prepare-provider">فتح في محرر الاعتماد</button>' : ''}
      </div>
    </article>`;
  }

  async function loadApplications() {
    if (!has('applications:read')) return;
    const status = $('applications-filter').value;
    const query = new URLSearchParams({limit:'100'});
    if (status) query.set('status', status);
    const data = await request(`/v1/admin/applications?${query}`);
    state.applications = data.items || [];
    $('applications-list').innerHTML = state.applications.length
      ? state.applications.map(applicationCard).join('')
      : '<div class="empty"><h3>لا توجد طلبات مطابقة</h3></div>';
  }

  async function saveApplication(card) {
    const id = card.dataset.applicationId;
    const payload = {
      status:card.querySelector('[data-field="status"]').value,
      adminNotes:card.querySelector('[data-field="adminNotes"]').value.trim(),
      publicMessage:card.querySelector('[data-field="publicMessage"]').value.trim(),
      notify:card.querySelector('[data-field="notify"]').checked
    };
    await request(`/v1/admin/applications/${encodeURIComponent(id)}`, {
      method:'PATCH',
      body:JSON.stringify(payload)
    });
    setStatus('تم حفظ حالة طلب الانضمام.', 'success');
    await Promise.all([loadOverview(), loadApplications()]);
  }

  function generatedProviderId(entityType) {
    const bytes = new Uint8Array(5);
    crypto.getRandomValues(bytes);
    const suffix = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return `${entityType === 'center' ? 'center' : 'professional'}-${suffix}`;
  }

  function setMulti(id, values) {
    const chosen = new Set(values || []);
    Array.from($(id)?.options || []).forEach(option => {
      option.selected = chosen.has(option.value);
    });
  }

  function setValue(id, value = '') {
    const element = $(id);
    if (element) element.value = value ?? '';
  }

  function setChecked(id, value) {
    const element = $(id);
    if (element) element.checked = Boolean(value);
  }

  function resetProviderForm() {
    $('provider-form').reset();
    setValue('provider-application-id', '');
    setValue('provider-id', '');
    setValue('provider-country', 'الأردن');
    setValue('provider-status', 'active');
    setValue('provider-availability', 'available');
    setValue('provider-response', 'خلال يومي عمل');
    setValue('provider-license-status', 'pending_review');
    setValue('review-legal-authority', 'pending');
    setValue('review-consent-date', today());
    setValue('review-next-date', plusOneYear());
    setValue('review-public-sources', '0');
    setValue('review-private-documents', '0');
    setValue('review-independent-sources', '0');
    setChecked('provider-notifications', true);
    setChecked('provider-accepts', true);
    setChecked('provider-messaging-enabled', true);
  }

  function prepareApplication(application) {
    resetProviderForm();
    const payload = application.payload || {};
    const qualification = payload.qualifications?.[0] || {};
    const license = payload.licenses?.[0] || {};
    const entityType = payload.entityType || application.entityType || 'professional';
    setValue('provider-application-id', application.id);
    setValue('provider-id', generatedProviderId(entityType));
    setValue('provider-display-name', payload.displayName || application.displayName);
    setValue('provider-email', payload.privateEmail || application.email);
    setValue('provider-entity-type', entityType);
    setValue('provider-professional-title', payload.professionalTitle);
    setValue('provider-center-type', payload.centerType);
    setValue('provider-bio', payload.shortBio);
    setMulti('provider-specialties', payload.specialties);
    setValue('provider-services', (payload.services || []).join('\n'));
    setMulti('provider-age-groups', payload.ageGroups);
    setMulti('provider-service-modes', payload.serviceModes);
    setValue('provider-languages', (payload.languages || []).join('، '));
    setValue('provider-response', payload.workPreferences?.typicalResponse || 'خلال يومي عمل');
    setValue('provider-availability', payload.workPreferences?.availability || 'available');
    setChecked('provider-messaging-enabled', payload.workPreferences?.acceptsInternalMessages !== false);
    setChecked('provider-accepts', payload.workPreferences?.acceptsNewRequests !== false);
    setValue('provider-country', payload.location?.country || 'الأردن');
    setValue('provider-governorate', payload.location?.governorate);
    setValue('provider-city', payload.location?.city);
    setValue('provider-area', payload.location?.area);
    setValue('provider-service-areas', (payload.location?.serviceAreas || []).join('\n'));
    setValue('provider-qualification-name', qualification.name);
    setValue('provider-qualification-institution', qualification.institution);
    setValue('provider-qualification-level', qualification.level);
    setValue('provider-qualification-year', qualification.year);
    setValue('provider-license-status', license.status || 'pending_review');
    setValue('provider-license-authority', license.authority);
    setValue('provider-license-public-id', license.publicIdentifier);
    setValue('provider-profile-url',
      payload.publicContactPreferences?.showOfficialProfile
        ? payload.publicContactPreferences?.officialProfile
        : '');
    setValue('provider-website', payload.publicContactPreferences?.website);
    setChecked('review-consent', payload.consent?.publication === true);
    activateTab('providers');
    $('provider-form').scrollIntoView({behavior:'smooth', block:'start'});
    setStatus('تم نقل الطلب إلى محرر الاعتماد. راجع الأدلة وأكمل بوابة التحقق قبل النشر.', 'success');
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
        <div class="field"><label>حالة المحادثة</label>
          <select data-field="conversationStatus">
            ${['open','closed','blocked','archived'].map(value =>
              `<option value="${value}" ${item.status === value ? 'selected' : ''}>${esc(statusLabel(value))}</option>`
            ).join('')}
          </select>
        </div>
        <div class="field full"><label>ملاحظات إدارية</label>
          <textarea data-field="conversationNotes" maxlength="4000">${esc(item.adminNotes || '')}</textarea>
        </div>
      </div>
      <button class="button primary" type="button" data-action="save-conversation">حفظ الحالة</button>
    </article>`;
  }

  async function loadConversations() {
    if (!has('conversations:moderate')) return;
    const status = $('conversations-filter').value;
    const query = new URLSearchParams({limit:'100'});
    if (status) query.set('status', status);
    const data = await request(`/v1/admin/conversations?${query}`);
    $('conversations-list').innerHTML = data.items.length
      ? data.items.map(conversationCard).join('')
      : '<div class="empty"><h3>لا توجد محادثات مطابقة</h3></div>';
  }

  async function saveConversation(card) {
    const id = card.dataset.conversationId;
    await request(`/v1/admin/conversations/${encodeURIComponent(id)}`, {
      method:'PATCH',
      body:JSON.stringify({
        status:card.querySelector('[data-field="conversationStatus"]').value,
        adminNotes:card.querySelector('[data-field="conversationNotes"]').value.trim()
      })
    });
    setStatus('تم تحديث حالة المحادثة.', 'success');
    await Promise.all([loadOverview(), loadConversations()]);
  }

  function providerCard(item) {
    const profile = item.profile || {};
    const place = [profile.location?.city, profile.location?.country].filter(Boolean).join('، ');
    return `<article class="admin-card provider-row" data-provider-id="${esc(item.providerId)}">
      <div class="provider-card-main">
        <p class="eyebrow">${esc(item.providerId)} · الإصدار ${esc(item.publicRevision)}</p>
        <h3>${esc(profile.displayName || item.displayName)}</h3>
        <p>${esc(profile.professionalTitle || profile.centerType || '')}</p>
        <p>${esc(place || 'الموقع غير مكتمل')} · المراجعة القادمة: ${esc(item.nextReviewAt || 'غير محددة')}</p>
        <p class="private-line">بريد الإشعارات الخاص: ${esc(item.email)}</p>
      </div>
      <div class="provider-card-side">
        <div class="chips">
          <span class="badge ${esc(item.publicationStatus)}">${esc(statusLabel(item.publicationStatus))}</span>
          <span class="badge ${esc(item.verificationStatus)}">${esc(statusLabel(item.verificationStatus))}</span>
          <span class="chip">${item.acceptsNewRequests ? 'يستقبل طلبات' : 'لا يستقبل طلبات'}</span>
        </div>
        <button class="button secondary" type="button" data-action="edit-provider">فتح وتحرير</button>
      </div>
    </article>`;
  }

  function renderProviders() {
    const query = String($('providers-search')?.value || '').trim().toLowerCase();
    const publication = $('providers-publication-filter')?.value || '';
    const items = state.providers.filter(item => {
      const profile = item.profile || {};
      const text = [
        item.providerId, item.displayName, item.email, profile.displayName,
        profile.professionalTitle, profile.centerType, profile.location?.city,
        profile.location?.country
      ].filter(Boolean).join(' ').toLowerCase();
      return (!query || text.includes(query)) &&
        (!publication || item.publicationStatus === publication);
    });
    $('providers-list').innerHTML = items.length
      ? items.map(providerCard).join('')
      : '<div class="empty"><h3>لا توجد ملفات مطابقة</h3></div>';
  }

  async function loadProviders() {
    if (!has('providers:read')) return;
    const data = await request('/v1/admin/providers?limit=250');
    state.providers = data.items || [];
    renderProviders();
  }

  function fillProviderForm(item) {
    resetProviderForm();
    const profile = item.profile || {};
    const review = item.review || {};
    const qualification = profile.qualifications?.[0] || {};
    const license = profile.licenses?.[0] || {};
    setValue('provider-application-id', item.applicationId);
    setValue('provider-id', item.providerId);
    setValue('provider-display-name', profile.displayName || item.displayName);
    setValue('provider-email', item.email);
    setValue('provider-status', item.status);
    setValue('provider-entity-type', profile.entityType || 'professional');
    setValue('provider-professional-title', profile.professionalTitle);
    setValue('provider-center-type', profile.centerType);
    setValue('provider-network-role', profile.roleInNetwork);
    setChecked('provider-notifications', item.notificationEnabled);
    setChecked('provider-accepts', item.acceptsNewRequests);
    setValue('provider-bio', profile.shortBio);
    setMulti('provider-specialties', profile.specialties);
    setValue('provider-services', (profile.services || []).join('\n'));
    setMulti('provider-age-groups', profile.ageGroups);
    setMulti('provider-service-modes', profile.serviceModes);
    setValue('provider-languages', (profile.languages || []).join('، '));
    setValue('provider-response', profile.communication?.typicalResponse || 'خلال يومي عمل');
    setValue('provider-availability', profile.availability?.status || 'available');
    setChecked('provider-messaging-enabled', profile.communication?.enabled);
    setValue('provider-country', profile.location?.country || 'الأردن');
    setValue('provider-governorate', profile.location?.governorate);
    setValue('provider-city', profile.location?.city);
    setValue('provider-area', profile.location?.area);
    setValue('provider-service-areas', (profile.serviceAreas || []).join('\n'));
    setValue('provider-qualification-name', qualification.name);
    setValue('provider-qualification-institution', qualification.institution);
    setValue('provider-qualification-level', qualification.level);
    setValue('provider-qualification-year', qualification.year);
    setValue('provider-license-status', license.status || 'pending_review');
    setValue('provider-license-authority', license.authority);
    setValue('provider-license-public-id', license.identifierPublic);
    setValue('provider-license-until', license.validUntil);
    setValue('provider-profile-url', profile.profileUrl);
    setValue('provider-website', profile.contact?.website);
    setValue('provider-public-phone', profile.contact?.publicPhone);
    setValue('provider-public-email', profile.contact?.publicEmail);
    setChecked('review-identity', review.checklist?.identity);
    setChecked('review-qualification', review.checklist?.qualification);
    setChecked('review-scope', review.checklist?.professionalScope);
    setChecked('review-contact', review.checklist?.contact);
    setChecked('review-consent', review.checklist?.consent);
    setValue('review-legal-authority', review.checklist?.legalAuthority || 'pending');
    setChecked('review-consent-approved', item.consentStatus === 'approved');
    setValue('review-consent-date', profile.consent?.approvedAt || today());
    setValue('review-next-date', review.nextReviewAt || item.nextReviewAt || plusOneYear());
    setValue('review-public-sources', review.evidenceSummary?.publicSources || 0);
    setValue('review-private-documents', review.evidenceSummary?.privateDocuments || 0);
    setValue('review-independent-sources', review.evidenceSummary?.independentSources || 0);
    setValue('review-public-note', review.publicNote);
    setValue('review-private-note', review.privateNotes);
    $('provider-form').scrollIntoView({behavior:'smooth', block:'start'});
  }

  function providerPayload(action) {
    const form = $('provider-form');
    if (!form.reportValidity()) return null;
    const qualification = {
      name:$('provider-qualification-name').value.trim(),
      institution:$('provider-qualification-institution').value.trim(),
      level:$('provider-qualification-level').value.trim() || null,
      year:Number($('provider-qualification-year').value) || null
    };
    const license = {
      authority:$('provider-license-authority').value.trim() || null,
      identifierPublic:$('provider-license-public-id').value.trim() || null,
      status:$('provider-license-status').value,
      validUntil:$('provider-license-until').value || null
    };
    return {
      action,
      reason:`owner-console:${action}`,
      applicationId:$('provider-application-id').value || null,
      providerId:$('provider-id').value.trim(),
      displayName:$('provider-display-name').value.trim(),
      email:$('provider-email').value.trim(),
      status:$('provider-status').value,
      notificationEnabled:$('provider-notifications').checked,
      acceptsNewRequests:$('provider-accepts').checked,
      profile:{
        entityType:$('provider-entity-type').value,
        displayName:$('provider-display-name').value.trim(),
        professionalTitle:$('provider-professional-title').value.trim() || null,
        centerType:$('provider-center-type').value.trim() || null,
        roleInNetwork:$('provider-network-role').value || null,
        shortBio:$('provider-bio').value.trim(),
        specialties:selected('provider-specialties'),
        services:list($('provider-services').value),
        ageGroups:selected('provider-age-groups'),
        serviceModes:selected('provider-service-modes'),
        languages:list($('provider-languages').value),
        serviceAreas:list($('provider-service-areas').value),
        location:{
          country:$('provider-country').value.trim(),
          governorate:$('provider-governorate').value.trim() || null,
          city:$('provider-city').value.trim(),
          area:$('provider-area').value.trim() || null,
          accessibility:[]
        },
        qualifications:qualification.name || qualification.institution ? [qualification] : [],
        licenses:[license],
        availability:{status:$('provider-availability').value, updatedAt:today()},
        communication:{
          enabled:$('provider-messaging-enabled').checked,
          acceptsNewRequests:$('provider-accepts').checked,
          typicalResponse:$('provider-response').value
        },
        contact:{
          publicUrl:$('provider-profile-url').value.trim() || null,
          website:$('provider-website').value.trim() || null,
          publicPhone:$('provider-public-phone').value.trim() || null,
          publicEmail:$('provider-public-email').value.trim() || null
        },
        profileUrl:$('provider-profile-url').value.trim() || null
      },
      review:{
        checklist:{
          identity:$('review-identity').checked,
          qualification:$('review-qualification').checked,
          professionalScope:$('review-scope').checked,
          contact:$('review-contact').checked,
          consent:$('review-consent').checked,
          legalAuthority:$('review-legal-authority').value
        },
        evidenceSummary:{
          publicSources:Number($('review-public-sources').value) || 0,
          privateDocuments:Number($('review-private-documents').value) || 0,
          independentSources:Number($('review-independent-sources').value) || 0
        },
        privateNotes:$('review-private-note').value.trim(),
        publicNote:$('review-public-note').value.trim(),
        nextReviewAt:$('review-next-date').value || null,
        consentApproved:$('review-consent-approved').checked,
        consentApprovedAt:$('review-consent-date').value || null
      }
    };
  }

  async function saveProvider(action, button) {
    if (state.role !== 'owner') throw new Error('هذه العملية متاحة للمالك فقط.');
    const payload = providerPayload(action);
    if (!payload) return;
    if (['approve_publish','suspend','archive','revoke_consent'].includes(action)) {
      const question = action === 'approve_publish'
        ? 'سيصبح الملف ظاهرًا للعامة فور تفعيل الخدمة الخلفية. هل أكملت التحقق والموافقة؟'
        : `هل تريد تنفيذ الإجراء: ${statusLabel(action)}؟`;
      if (!window.confirm(question)) return;
    }
    button.disabled = true;
    try {
      let applicationWarning = '';
      const result = await request('/v1/admin/providers', {
        method:'POST',
        body:JSON.stringify(payload)
      });
      if (action === 'approve_publish' && payload.applicationId) {
        try {
          await request(`/v1/admin/applications/${encodeURIComponent(payload.applicationId)}`, {
            method:'PATCH',
            body:JSON.stringify({
              status:'approved',
              adminNotes:'تم اعتماد الملف العام من لوحة المالك.',
              publicMessage:'تم اعتماد ملفك المهني وتفعيل مسار التواصل وفق البيانات التي تمت مراجعتها.',
              notify:true,
              provider:{
                providerId:payload.providerId,
                displayName:payload.displayName,
                email:payload.email,
                status:'active',
                notificationEnabled:payload.notificationEnabled,
                acceptsNewRequests:payload.acceptsNewRequests
              }
            })
          });
        } catch (error) {
          applicationWarning = `تم نشر الملف، لكن تعذر تحديث حالة طلب الانضمام: ${error.message}`;
        }
      }
      if (applicationWarning) {
        setStatus(applicationWarning, 'error');
      } else {
        setStatus(
          action === 'approve_publish'
            ? `تم اعتماد ونشر الملف بالإصدار ${result.publicRevision}.`
            : `تم حفظ الملف وتنفيذ الإجراء: ${statusLabel(result.publicationStatus || action)}.`,
          'success'
        );
      }
      await Promise.all([loadOverview(), loadProviders(), loadApplications()]);
      const current = state.providers.find(item => item.providerId === payload.providerId);
      if (current) fillProviderForm(current);
    } finally {
      button.disabled = false;
    }
  }

  function auditCard(item) {
    return `<article class="admin-card audit-row">
      <div><p class="eyebrow">${esc(item.eventType)}</p><h3>${esc(item.entityId)}</h3></div>
      <time datetime="${esc(item.createdAt)}">${esc(formatDate(item.createdAt))}</time>
      <pre>${esc(JSON.stringify(item.metadata || {}, null, 2))}</pre>
    </article>`;
  }

  async function loadAudit() {
    if (!has('audit:read')) return;
    const data = await request('/v1/admin/audit?limit=150');
    $('audit-list').innerHTML = data.items.length
      ? data.items.map(auditCard).join('')
      : '<div class="empty"><h3>لا توجد أحداث مسجلة</h3></div>';
  }

  async function refreshAll() {
    setStatus('جارٍ تحديث بيانات القطاع…', 'loading');
    await loadOverview();
    await Promise.all([
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
      let key = $('admin-api-key').value;
      try {
        const apiBase = validatedApiBase($('admin-api-base').value);
        const session = await createSession(apiBase, key);
        key = '';
        $('admin-api-key').value = '';
        state.apiBase = apiBase;
        state.accessToken = session.accessToken;
        state.role = session.role;
        state.actorLabel = session.actorLabel;
        state.expiresAt = session.expiresAt;
        showConsole();
        await refreshAll();
        setStatus(`تم فتح اللوحة بصلاحية: ${roleLabel(state.role)}.`, 'success');
      } catch (error) {
        key = '';
        clearSessionState();
        setStatus(error.message || 'تعذر فتح لوحة الإدارة.', 'error');
      }
    });

    $('admin-refresh').addEventListener('click', () =>
      refreshAll().catch(error => setStatus(error.message, 'error')));
    $('admin-lock').addEventListener('click', () => lockConsole(true));
    $('applications-filter').addEventListener('change', () =>
      loadApplications().catch(error => setStatus(error.message, 'error')));
    $('conversations-filter').addEventListener('change', () =>
      loadConversations().catch(error => setStatus(error.message, 'error')));
    $('provider-form-reset').addEventListener('click', resetProviderForm);
    $('providers-search').addEventListener('input', renderProviders);
    $('providers-publication-filter').addEventListener('change', renderProviders);

    document.querySelector('.admin-tabs').addEventListener('click', event => {
      const button = event.target.closest('[data-admin-tab]');
      if (button && !button.hidden) activateTab(button.dataset.adminTab);
    });

    $('applications-list').addEventListener('click', event => {
      const button = event.target.closest('[data-action]');
      if (!button) return;
      const card = button.closest('[data-application-id]');
      if (button.dataset.action === 'prepare-provider') {
        const item = state.applications.find(application =>
          application.id === card.dataset.applicationId);
        if (item) prepareApplication(item);
        return;
      }
      if (button.dataset.action === 'save-application') {
        button.disabled = true;
        saveApplication(card)
          .catch(error => setStatus(error.message, 'error'))
          .finally(() => { button.disabled = false; });
      }
    });

    $('conversations-list').addEventListener('click', event => {
      const button = event.target.closest('[data-action="save-conversation"]');
      if (!button) return;
      button.disabled = true;
      saveConversation(button.closest('[data-conversation-id]'))
        .catch(error => setStatus(error.message, 'error'))
        .finally(() => { button.disabled = false; });
    });

    $('providers-list').addEventListener('click', event => {
      const button = event.target.closest('[data-action="edit-provider"]');
      if (!button) return;
      const card = button.closest('[data-provider-id]');
      const item = state.providers.find(provider => provider.providerId === card.dataset.providerId);
      if (item) fillProviderForm(item);
    });

    document.querySelector('.provider-form-actions').addEventListener('click', event => {
      const button = event.target.closest('[data-provider-action]');
      if (!button) return;
      saveProvider(button.dataset.providerAction, button)
        .catch(error => setStatus(error.message, 'error'));
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('admin-api-base').value = String(config.apiBase || '');
    resetProviderForm();
    bindEvents();
    window.setInterval(() => {
      if (!state.expiresAt || !state.accessToken) return;
      const remaining = Date.parse(state.expiresAt) - Date.now();
      if (remaining <= 0) {
        lockConsole(false);
        setStatus('انتهت الجلسة الإدارية. افتح جلسة جديدة للمتابعة.', 'error');
      } else if (remaining <= 2 * 60 * 1000) {
        setStatus('ستنتهي الجلسة الإدارية خلال أقل من دقيقتين. احفظ عملك ثم افتح جلسة جديدة.', 'loading');
      }
    }, 30_000);
  });
})();
