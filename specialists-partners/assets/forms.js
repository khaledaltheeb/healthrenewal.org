(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[char]));
  const list = value => String(value || '').split(/[،,\n]/).map(item => item.trim()).filter(Boolean);
  const selected = id => Array.from($(id)?.selectedOptions || []).map(option => option.value);
  const page = document.body.dataset.page || '';

  function status(message, state = 'loading') {
    const box = $('form-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = state;
    box.textContent = message;
    box.focus?.();
  }

  function initTurnstile() {
    const target = $('turnstile-box');
    if (!target || !config.turnstileSiteKey) return;
    const render = () => {
      if (window.turnstile && !target.dataset.rendered) {
        window.turnstile.render(target, {sitekey: config.turnstileSiteKey, theme: 'light', language: 'ar'});
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

  function apiUrl(path) {
    const base = String(config.apiBase || '').replace(/\/$/, '');
    return base ? `${base}${path}` : '';
  }

  async function post(path, payload) {
    const url = apiUrl(path);
    if (!url) throw new Error('backend_not_configured');
    const response = await fetch(url, {
      method: 'POST',
      headers: {'content-type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || 'تعذر إكمال الطلب');
      error.code = data.error || 'request_failed';
      throw error;
    }
    return data;
  }

  function randomId(prefix = 'record') {
    const bytes = new Uint8Array(10);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')}`;
  }

  function joinPayload(form) {
    return {
      submissionId: randomId('application'),
      entityType: $('entityType').value,
      displayName: $('displayName').value.trim(),
      professionalTitle: $('professionalTitle').value.trim() || null,
      centerType: $('centerType').value.trim() || null,
      privateEmail: $('privateEmail').value.trim(),
      phone: $('privatePhone').value.trim() || null,
      specialties: selected('specialties'),
      services: list($('services').value),
      ageGroups: selected('ageGroups'),
      serviceModes: selected('serviceModes'),
      languages: list($('languages').value),
      location: {
        country: $('country').value.trim(),
        governorate: $('governorate').value.trim() || null,
        city: $('city').value.trim(),
        area: $('area').value.trim() || null,
        serviceAreas: list($('serviceAreas').value)
      },
      qualifications: [{
        name: $('qualification').value.trim(),
        institution: $('institution').value.trim(),
        level: $('qualificationLevel').value,
        year: Number($('qualificationYear').value) || null
      }],
      licenses: [{
        authority: $('licenseAuthority').value.trim() || null,
        status: $('licenseStatus').value,
        publicIdentifier: $('licenseIdentifier').value.trim() || null
      }],
      experienceYears: Number($('experienceYears').value) || null,
      currentRole: $('currentRole').value.trim() || null,
      shortBio: $('shortBio').value.trim(),
      workPreferences: {
        availability: $('availability').value,
        typicalResponse: $('typicalResponse').value,
        acceptsInternalMessages: $('acceptsInternalMessages').checked,
        acceptsNewRequests: $('acceptsNewRequests').checked
      },
      publicContactPreferences: {
        showPhone: $('showPhone').checked,
        showEmail: $('showEmail').checked,
        showOfficialProfile: $('showOfficialProfile').checked,
        officialProfile: $('officialProfile').value.trim() || null,
        website: $('website').value.trim() || null
      },
      collaborationInterests: selected('collaborationInterests'),
      consent: {
        dataReview: $('consentReview').checked,
        publication: $('consentPublication').checked,
        internalMessaging: $('consentMessaging').checked,
        submittedAt: new Date().toISOString()
      },
      turnstileToken: turnstileToken(form)
    };
  }

  function downloadJson(payload) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `specialist-application-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function initJoin() {
    const form = $('onboarding-form');
    if (!form) return;
    const output = $('output');
    const preview = () => {
      if (!form.reportValidity()) return null;
      const payload = joinPayload(form);
      output.value = JSON.stringify(payload, null, 2);
      return payload;
    };
    $('preview-record')?.addEventListener('click', () => preview());
    $('copy-output')?.addEventListener('click', async () => {
      const payload = preview();
      if (!payload) return;
      try { await navigator.clipboard.writeText(JSON.stringify(payload, null, 2)); status('تم نسخ السجل المنظم.', 'success'); }
      catch (_) { output.select(); document.execCommand('copy'); status('تم نسخ السجل المنظم.', 'success'); }
    });
    $('download-output')?.addEventListener('click', () => { const payload = preview(); if (payload) downloadJson(payload); });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const payload = preview();
      if (!payload) return;
      const submit = $('submit-application');
      submit.disabled = true;
      status('جارٍ إرسال الطلب إلى إدارة المنصة…', 'loading');
      try {
        const result = await post('/v1/applications', payload);
        status(`تم استلام الطلب بنجاح. رقم المتابعة: ${result.referenceId}`, 'success');
        form.reset();
        output.value = '';
      } catch (error) {
        if (error.message === 'backend_not_configured') {
          status('بوابة الإرسال الآمن مجهزة برمجيًا لكنها لم تُربط بعد بخدمة الاستضافة. نزّل السجل مؤقتًا وأرسله إلى إدارة المنصة.', 'error');
        } else {
          status(error.message || 'تعذر إرسال الطلب. احتفظ بالسجل وحاول لاحقًا.', 'error');
        }
      } finally { submit.disabled = false; }
    });
  }

  async function loadProvider(providerId) {
    const response = await fetch('data/providers.json', {cache:'no-store'});
    if (!response.ok) throw new Error('provider_load_failed');
    const data = await response.json();
    return (data.providers || []).find(provider => provider.id === providerId && provider.publicationStatus === 'published');
  }

  function contactPayload(form, provider) {
    return {
      requestId: randomId('conversation'),
      providerId: provider.id,
      sender: {
        displayName: $('senderName').value.trim(),
        email: $('senderEmail').value.trim(),
        country: $('senderCountry').value.trim(),
        city: $('senderCity').value.trim() || null
      },
      context: {
        ageGroup: $('ageGroup').value,
        preferredMode: $('preferredMode').value,
        topic: $('topic').value,
        urgency: $('urgency').value,
        preferredContactTime: $('preferredContactTime').value.trim() || null
      },
      message: $('message').value.trim(),
      consent: {
        privacy: $('privacyConsent').checked,
        contact: $('contactConsent').checked,
        submittedAt: new Date().toISOString()
      },
      turnstileToken: turnstileToken(form)
    };
  }

  async function initContact() {
    const form = $('contact-form');
    if (!form) return;
    const providerId = new URLSearchParams(location.search).get('provider');
    if (!providerId) {
      status('لم يتم تحديد مختص. ارجع إلى الدليل واختر «تواصل مع المختص».', 'error');
      form.hidden = true;
      return;
    }
    try {
      const provider = await loadProvider(providerId);
      if (!provider || provider.communication?.enabled !== true) throw new Error('provider_not_available');
      $('provider-preview').innerHTML = `<p class="eyebrow">الرسالة موجهة إلى</p><h2>${esc(provider.displayName)}</h2><p>${esc(provider.professionalTitle || provider.centerType || '')}</p><div class="chips">${(provider.specialties || []).map(value => `<span class="chip">${esc(value)}</span>`).join('')}</div>`;
      $('providerId').value = provider.id;
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const payload = contactPayload(form, provider);
        const submit = $('submit-contact');
        submit.disabled = true;
        status('جارٍ إنشاء المحادثة وإرسال الإشعار…', 'loading');
        try {
          const result = await post('/v1/conversations', payload);
          const portal = `portal/?conversation=${encodeURIComponent(result.conversationId)}&token=${encodeURIComponent(result.accessToken)}&role=visitor`;
          status('تم إنشاء المحادثة وإشعار المختص. احتفظ بالرابط التالي للعودة إلى المحادثة.', 'success');
          const link = document.createElement('a');
          link.className = 'button primary';
          link.href = portal;
          link.textContent = 'فتح المحادثة الخاصة';
          $('form-status').append(document.createElement('br'), link);
          form.reset();
        } catch (error) {
          if (error.message === 'backend_not_configured') status('واجهة المحادثة مجهزة، لكن خدمة الرسائل الخلفية لم تُنشر بعد. لا تُرسل معلومات حساسة خارج النظام.', 'error');
          else status(error.message || 'تعذر إنشاء المحادثة.', 'error');
        } finally { submit.disabled = false; }
      });
    } catch (_) {
      status('الملف غير موجود أو التواصل الداخلي غير متاح لهذا المختص.', 'error');
      form.hidden = true;
    }
  }

  function portalCredentials() {
    const params = new URLSearchParams(location.search);
    return {
      conversationId: params.get('conversation') || sessionStorage.getItem('ptConversationId') || '',
      token: params.get('token') || sessionStorage.getItem('ptConversationToken') || '',
      role: params.get('role') || sessionStorage.getItem('ptConversationRole') || 'visitor'
    };
  }

  async function portalRequest(path, options = {}) {
    const url = apiUrl(path);
    if (!url) throw new Error('backend_not_configured');
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'تعذر الوصول إلى المحادثة');
    return data;
  }

  function renderMessages(data, role) {
    const listBox = $('message-list');
    listBox.innerHTML = (data.messages || []).map(message => {
      const mine = message.senderRole === role;
      return `<article class="message ${mine ? 'mine' : 'theirs'}"><p>${esc(message.body)}</p><time datetime="${esc(message.createdAt)}">${esc(new Date(message.createdAt).toLocaleString('ar-JO'))}</time></article>`;
    }).join('') || '<p class="small">لا توجد رسائل بعد.</p>';
    listBox.scrollTop = listBox.scrollHeight;
    $('conversation-title').textContent = data.provider?.displayName ? `محادثة مع ${data.provider.displayName}` : 'محادثة خاصة';
    $('conversation-status').textContent = data.conversation?.status || 'مفتوحة';
    $('conversation-reference').textContent = data.conversation?.referenceId || data.conversation?.id || '';
  }

  async function initPortal() {
    const form = $('message-form');
    if (!form) return;
    const credentials = portalCredentials();
    if (!credentials.conversationId || !credentials.token) {
      status('رابط المحادثة غير مكتمل أو انتهت بيانات الجلسة.', 'error');
      form.hidden = true;
      return;
    }
    sessionStorage.setItem('ptConversationId', credentials.conversationId);
    sessionStorage.setItem('ptConversationToken', credentials.token);
    sessionStorage.setItem('ptConversationRole', credentials.role);

    const load = async () => {
      try {
        const query = new URLSearchParams({token:credentials.token, role:credentials.role});
        const data = await portalRequest(`/v1/conversations/${encodeURIComponent(credentials.conversationId)}?${query}`);
        renderMessages(data, credentials.role);
      } catch (error) { status(error.message, 'error'); }
    };
    await load();
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const body = $('messageBody').value.trim();
      if (!body) return;
      const submit = $('send-message');
      submit.disabled = true;
      try {
        await portalRequest(`/v1/conversations/${encodeURIComponent(credentials.conversationId)}/messages`, {
          method:'POST', headers:{'content-type':'application/json'},
          body:JSON.stringify({token:credentials.token, role:credentials.role, body})
        });
        $('messageBody').value = '';
        await load();
      } catch (error) { status(error.message, 'error'); }
      finally { submit.disabled = false; }
    });
    $('refresh-conversation')?.addEventListener('click', load);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTurnstile();
    if (page === 'join') initJoin();
    if (page === 'contact') initContact();
    if (page === 'portal') initPortal();
  });
})();
