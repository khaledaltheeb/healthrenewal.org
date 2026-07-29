(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const selected = id => Array.from($(id)?.selectedOptions || []).map(option => option.value);
  const splitList = value => String(value || '').split(/[،,\n]/).map(item => item.trim()).filter(Boolean);
  const safeWebUrl = value => {
    const candidate = String(value || '').trim();
    if (!candidate) return null;

    try {
      const parsed = new URL(candidate);
      if (!['http:', 'https:'].includes(parsed.protocol)) return null;
      if (parsed.username || parsed.password) return null;
      return parsed.href;
    } catch (_) {
      return null;
    }
  };

  function publicReviewRecord() {
    const showOfficialProfile = Boolean($('showOfficialProfile')?.checked);
    return {
      recordType: 'specialist_application_public_review',
      applicationStatus: 'new',
      entityType: $('entityType')?.value || '',
      displayName: $('displayName')?.value.trim() || '',
      professionalTitle: $('professionalTitle')?.value.trim() || null,
      centerType: $('centerType')?.value.trim() || null,
      specialties: selected('specialties'),
      services: splitList($('services')?.value),
      ageGroups: selected('ageGroups'),
      serviceModes: selected('serviceModes'),
      languages: splitList($('languages')?.value),
      location: {
        country: $('country')?.value.trim() || '',
        governorate: $('governorate')?.value.trim() || null,
        city: $('city')?.value.trim() || '',
        area: $('area')?.value.trim() || null,
        serviceAreas: splitList($('serviceAreas')?.value)
      },
      qualifications: [{
        name: $('qualification')?.value.trim() || '',
        institution: $('institution')?.value.trim() || '',
        level: $('qualificationLevel')?.value || '',
        year: Number($('qualificationYear')?.value) || null
      }],
      licenses: [{
        authority: $('licenseAuthority')?.value.trim() || null,
        status: 'pending_review'
      }],
      experienceYears: Number($('experienceYears')?.value) || null,
      currentRole: $('currentRole')?.value.trim() || null,
      shortBio: $('shortBio')?.value.trim() || '',
      workPreferences: {
        availability: $('availability')?.value || '',
        typicalResponse: $('typicalResponse')?.value || '',
        acceptsInternalMessages: Boolean($('acceptsInternalMessages')?.checked),
        acceptsNewRequests: Boolean($('acceptsNewRequests')?.checked)
      },
      publicContactPreferences: {
        showPhone: Boolean($('showPhone')?.checked),
        showEmail: Boolean($('showEmail')?.checked),
        showOfficialProfile,
        officialProfile: showOfficialProfile ? safeWebUrl($('officialProfile')?.value) : null,
        website: safeWebUrl($('website')?.value)
      },
      collaborationInterests: selected('collaborationInterests'),
      privacyNotice: 'هذه نسخة مراجعة عامة. لا تتضمن البريد الخاص أو الهاتف الإداري أو أرقام الترخيص أو رموز مكافحة السبام أو بيانات الجلسة.'
    };
  }

  function setStatus(message, state = 'success') {
    const box = $('form-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = state;
    box.textContent = message;
    box.focus?.();
  }

  function validateAndBuild() {
    const form = $('onboarding-form');
    if (!form?.reportValidity()) return null;
    const record = publicReviewRecord();
    const output = $('output');
    if (output) output.value = JSON.stringify(record, null, 2);
    return record;
  }

  function download(record) {
    const blob = new Blob([JSON.stringify(record, null, 2)], {type: 'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `specialist-public-review-${Date.now()}.json`;
    anchor.rel = 'noopener';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'join') return;

    $('preview-record')?.addEventListener('click', event => {
      event.stopImmediatePropagation();
      if (validateAndBuild()) setStatus('تم إنشاء نسخة مراجعة منقحة لا تحتوي بيانات الاتصال الخاصة أو أرقام الترخيص أو رموز الحماية.');
    }, true);

    $('copy-output')?.addEventListener('click', async event => {
      event.stopImmediatePropagation();
      const record = validateAndBuild();
      if (!record) return;
      const text = JSON.stringify(record, null, 2);
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        const output = $('output');
        output?.select();
        document.execCommand('copy');
      }
      setStatus('تم نسخ نسخة المراجعة المنقحة فقط.');
    }, true);

    $('download-output')?.addEventListener('click', event => {
      event.stopImmediatePropagation();
      const record = validateAndBuild();
      if (!record) return;
      download(record);
      setStatus('تم تنزيل نسخة مراجعة منقحة دون بيانات خاصة.');
    }, true);

    $('onboarding-form')?.addEventListener('submit', () => {
      window.setTimeout(() => {
        const output = $('output');
        if (output) output.value = '';
      }, 0);
    }, true);
  });
})();
