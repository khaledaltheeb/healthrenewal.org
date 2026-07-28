(() => {
  'use strict';

  const PRIVATE_PLACEHOLDER = '[خاص — محفوظ للإرسال الآمن فقط]';

  function sanitizeApplicationRecord(raw) {
    const safe = JSON.parse(JSON.stringify(raw || {}));
    delete safe.turnstileToken;
    delete safe.privateEmail;
    delete safe.phone;
    safe.privateData = {
      email: PRIVATE_PLACEHOLDER,
      phone: PRIVATE_PLACEHOLDER,
      note: 'لا تتضمن نسخة المعاينة أو التنزيل البيانات الخاصة أو رموز التحقق.'
    };
    return safe;
  }

  function parseCurrentOutput(output) {
    if (!output?.value) return null;
    try {
      return JSON.parse(output.value);
    } catch (_) {
      return null;
    }
  }

  function writeSafeOutput(output) {
    const raw = parseCurrentOutput(output);
    if (!raw) return null;
    const safe = sanitizeApplicationRecord(raw);
    output.value = JSON.stringify(safe, null, 2);
    output.dataset.privateFieldsRedacted = 'true';
    return safe;
  }

  function announce(message, state = 'success') {
    const box = document.getElementById('form-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = state;
    box.textContent = message;
    box.focus?.();
  }

  function downloadSafeJson(payload) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `specialist-application-public-preview-${Date.now()}.json`;
    anchor.rel = 'noopener';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function init() {
    if (document.body?.dataset.page !== 'join') return;
    const form = document.getElementById('onboarding-form');
    const output = document.getElementById('output');
    const previewButton = document.getElementById('preview-record');
    const copyButton = document.getElementById('copy-output');
    const downloadButton = document.getElementById('download-output');
    if (!form || !output) return;

    const refreshSafePreview = () => {
      if (!form.reportValidity()) return null;
      return writeSafeOutput(output);
    };

    previewButton?.addEventListener('click', () => {
      queueMicrotask(() => writeSafeOutput(output));
    });

    copyButton?.addEventListener('click', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      previewButton?.click();
      await new Promise(resolve => queueMicrotask(resolve));
      const safe = refreshSafePreview();
      if (!safe) return;
      try {
        await navigator.clipboard.writeText(JSON.stringify(safe, null, 2));
      } catch (_) {
        output.select();
        document.execCommand('copy');
      }
      announce('تم نسخ سجل معاينة منقّح دون البريد الخاص أو الهاتف أو رمز التحقق.');
    }, true);

    downloadButton?.addEventListener('click', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      previewButton?.click();
      await new Promise(resolve => queueMicrotask(resolve));
      const safe = refreshSafePreview();
      if (!safe) return;
      downloadSafeJson(safe);
      announce('تم تنزيل سجل معاينة منقّح دون بيانات الاتصال الخاصة أو رمز التحقق.');
    }, true);

    const note = document.createElement('p');
    note.className = 'small';
    note.id = 'private-preview-notice';
    note.textContent = 'حماية الخصوصية: المعاينة والنسخ والتنزيل تستبعد البريد الخاص والهاتف ورمز التحقق تلقائيًا. تُرسل هذه البيانات فقط عبر بوابة الإرسال الآمن.';
    output.insertAdjacentElement('beforebegin', note);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();
