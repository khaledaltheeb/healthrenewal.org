(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const list = value => String(value || '').split(/[،,\n]/).map(item => item.trim()).filter(Boolean);
  const selected = id => Array.from($(id)?.selectedOptions || []).map(option => option.value);
  const page = document.body.dataset.page || '';
  const MAX_JSON_BYTES = 96_000;
  const REQUEST_TIMEOUT_MS = 20_000;

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
    if (!base) return '';
    try {
      const parsed = new URL(base);
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
          parsed.search || parsed.hash) return '';
      return `${parsed.href.replace(/\/$/, '')}${path}`;
    } catch (_) {
      return '';
    }
  }

  function safeWebUrl(value) {
    const candidate = String(value || '').trim();
    if (!candidate) return null;
    try {
      const parsed = new URL(candidate);
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password) return null;
      return parsed.href;
    } catch (_) {
      return null;
    }
  }

  async function post(path, payload) {
    const url = apiUrl(path);
    if (!url) throw new Error('backend_not_configured');
    const identity = payload.submissionId || payload.requestId;
    if (!identity || !/^[a-z0-9-]{12,120}$/i.test(identity)) {
      throw new Error('تعذر إنشاء معرف آمن للطلب. أعد تحميل الصفحة ثم حاول مرة أخرى.');
    }
    if (config.turnstileSiteKey && !String(payload.turnstileToken || '').trim()) {
      throw new Error('أكمل التحقق من الاستخدام البشري قبل الإرسال.');
    }
    const body = JSON.stringify(payload);
    if (new TextEncoder().encode(body).byteLength > MAX_JSON_BYTES) {
      throw new Error('حجم الطلب أكبر من الحد المسموح. قلّل النص وحاول مرة أخرى.');
    }
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('request_timeout'), REQUEST_TIMEOUT_MS);
    let response;
    try {
      response = await fetch(url, {
        method:'POST',
        headers:{
          accept:'application/json',
          'content-type':'application/json;charset=UTF-8',
          'idempotency-key':identity,
          'x-requested-with':'pterminology-specialists'
        },
        body,
        cache:'no-store',
        credentials:'omit',
        referrerPolicy:'no-referrer',
        redirect:'error',
        signal:controller.signal
      });
    } finally {
      window.clearTimeout(timeout);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || 'تعذر إكمال الطلب');
      error.code = data.error || 'request_failed';
      throw error;
    }
    try { window.turnstile?.reset?.(); } catch (_) { /* تحقق الخادم هو الأساس. */ }
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

  function publicReviewRecord() {
    const showOfficialProfile = Boolean($('showOfficialProfile')?.checked);
    return {
      recordType:'specialist_application_public_review',
      applicationStatus:'new',
      entityType:$('entityType').value,
      displayName:$('displayName').value.trim(),
      professionalTitle:$('professionalTitle').value.trim() || null,
      centerType:$('centerType').value.trim() || null,
      specialties:selected('specialties'),
      services:list($('services').value),
      ageGroups:selected('ageGroups'),
      serviceModes:selected('serviceModes'),
      languages:list($('languages').value),
      location:{
        country:$('country').value.trim(),
        governorate:$('governorate').value.trim() || null,
        city:$('city').value.trim(),
        area:$('area').value.trim() || null,
        serviceAreas:list($('serviceAreas').value)
      },
      qualifications:[{
        name:$('qualification').value.trim(),
        institution:$('institution').value.trim(),
        level:$('qualificationLevel').value,
        year:Number($('qualificationYear').value) || null
      }],
      licenses:[{
        authority:$('licenseAuthority').value.trim() || null,
        status:'pending_review'
      }],
      experienceYears:Number($('experienceYears').value) || null,
      currentRole:$('currentRole').value.trim() || null,
      shortBio:$('shortBio').value.trim(),
      workPreferences:{
        availability:$('availability').value,
        typicalResponse:$('typicalResponse').value,
        acceptsInternalMessages:$('acceptsInternalMessages').checked,
        acceptsNewRequests:$('acceptsNewRequests').checked
      },
      publicContactPreferences:{
        showPhone:$('showPhone').checked,
        showEmail:$('showEmail').checked,
        showOfficialProfile,
        officialProfile:showOfficialProfile ? safeWebUrl($('officialProfile').value) : null,
        website:safeWebUrl($('website').value)
      },
      collaborationInterests:selected('collaborationInterests'),
      privacyNotice:'هذه نسخة مراجعة عامة. لا تتضمن البريد الخاص أو الهاتف الإداري أو أرقام الترخيص أو رموز مكافحة السبام أو بيانات الجلسة.'
    };
  }

  function downloadJson(payload) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `specialist-public-review-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function initJoin() {
    const form = $('onboarding-form');
    if (!form) return;
    const output = $('output');
    const preview = () => {
      if (!form.reportValidity()) return null;
      const payload = publicReviewRecord();
      output.value = JSON.stringify(payload, null, 2);
      output.dataset.privateFieldsRedacted = 'true';
      return payload;
    };
    $('preview-record')?.addEventListener('click', () => preview());
    $('copy-output')?.addEventListener('click', async () => {
      const payload = preview();
      if (!payload) return;
      try { await navigator.clipboard.writeText(JSON.stringify(payload, null, 2)); status('تم نسخ نسخة المراجعة المنقحة.', 'success'); }
      catch (_) { output.select(); document.execCommand('copy'); status('تم نسخ نسخة المراجعة المنقحة.', 'success'); }
    });
    $('download-output')?.addEventListener('click', () => { const payload = preview(); if (payload) downloadJson(payload); });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const payload = joinPayload(form);
      output.value = '';
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

  async function fetchProviderPayload(url) {
    const response = await fetch(url, {
      cache:'no-store',
      credentials:'omit',
      referrerPolicy:'no-referrer',
      headers:{accept:'application/json'}
    });
    if (!response.ok) throw new Error('provider_load_failed');
    return await response.json();
  }

  async function loadProvider(providerId) {
    const liveUrl = apiUrl(`/v1/providers/${encodeURIComponent(providerId)}`);
    if (liveUrl) {
      try {
        const data = await fetchProviderPayload(liveUrl);
        if (data.provider?.publicationStatus === 'published') return data.provider;
      } catch (_) { /* العودة إلى النسخة العامة الاحتياطية. */ }
    }
    const data = await fetchProviderPayload('data/providers.json');
    return (data.providers || []).find(provider =>
      provider.id === providerId &&
      provider.publicationStatus === 'published' &&
      provider.verification?.status === 'verified' &&
      provider.consent?.publicProfileApproved === true
    );
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
          const portal = `portal/#conversation=${encodeURIComponent(result.conversationId)}&token=${encodeURIComponent(result.accessToken)}&role=visitor`;
          status('تم إنشاء المحادثة وإشعار المختص. احتفظ بالرابط التالي للعودة إلى المحادثة.', 'success');
          const link = document.createElement('a');
          link.className = 'button primary';
          link.href = portal;
          link.rel = 'noreferrer';
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
    const fragment = new URLSearchParams(location.hash.replace(/^#/, ''));
    const legacyQuery = new URLSearchParams(location.search);
    const credentials = {
      conversationId:fragment.get('conversation') || legacyQuery.get('conversation') ||
        sessionStorage.getItem('ptConversationId') || '',
      token:fragment.get('token') || legacyQuery.get('token') ||
        sessionStorage.getItem('ptConversationToken') || '',
      role:fragment.get('role') || legacyQuery.get('role') ||
        sessionStorage.getItem('ptConversationRole') || 'visitor'
    };
    if (!['visitor','specialist'].includes(credentials.role)) credentials.role = 'visitor';
    if (location.hash || location.search) {
      history.replaceState(null, document.title, location.pathname);
    }
    return credentials;
  }

  async function portalRequest(path, options = {}, credentials = null) {
    const url = apiUrl(path);
    if (!url) throw new Error('backend_not_configured');
    const auth = credentials || {
      token:sessionStorage.getItem('ptConversationToken') || '',
      role:sessionStorage.getItem('ptConversationRole') || 'visitor'
    };
    const headers = new Headers(options.headers || {});
    headers.set('accept', 'application/json');
    headers.set('authorization', `Bearer ${auth.token}`);
    headers.set('x-conversation-role', auth.role);
    if (options.body != null) headers.set('content-type', 'application/json;charset=UTF-8');
    const response = await fetch(url, {
      ...options,
      headers,
      cache:'no-store',
      credentials:'omit',
      referrerPolicy:'no-referrer',
      redirect:'error'
    });
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
        const data = await portalRequest(
          `/v1/conversations/${encodeURIComponent(credentials.conversationId)}`,
          {},
          credentials
        );
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
          body:JSON.stringify({body})
        }, credentials);
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
