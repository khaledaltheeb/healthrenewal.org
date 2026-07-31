(() => {
  'use strict';

  const IDENTITY_API = 'https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev';
  const RESET_PATH = '/v1/auth/password/reset';
  const form = document.getElementById('reset-form');
  const statusBox = document.getElementById('reset-status');
  const saveButton = document.getElementById('save-password');
  const successActions = document.getElementById('success-actions');
  let resetToken = '';

  function setStatus(message, state = 'loading') {
    statusBox.textContent = message;
    statusBox.dataset.state = state;
    statusBox.focus?.();
  }

  function readToken() {
    const params = new URLSearchParams(location.hash.replace(/^#/, ''));
    const token = params.get('resetToken') || '';
    history.replaceState(null, document.title, `${location.pathname}${location.search}`);
    return token;
  }

  function strongEnough(password) {
    const groups = [
      /\p{L}/u.test(password),
      /\d/u.test(password),
      /[^\p{L}\d\s]/u.test(password)
    ].filter(Boolean).length;
    const latinCaseBonus = /[a-z]/.test(password) && /[A-Z]/.test(password);
    return password.length >= 12 && password.length <= 128 && (groups >= 3 || (groups >= 2 && latinCaseBonus));
  }

  async function submit(event) {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const password = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (password !== confirmPassword) {
      setStatus('كلمتا المرور غير متطابقتين.', 'error');
      return;
    }
    if (!strongEnough(password)) {
      setStatus('استخدم 12 محرفًا على الأقل ومزيجًا من الحروف والأرقام والرموز. يمكن استخدام الحروف العربية.', 'error');
      return;
    }
    if (!resetToken) {
      setStatus('الرابط لا يحتوي رمز إعادة تعيين صالحًا. اطلب رابطًا جديدًا.', 'error');
      return;
    }

    saveButton.disabled = true;
    setStatus('جارٍ حفظ كلمة المرور وإلغاء الجلسات والروابط السابقة…');

    try {
      const response = await fetch(`${IDENTITY_API}${RESET_PATH}`, {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json;charset=UTF-8',
          'x-requested-with': 'pterminology-password-reset-v10'
        },
        body: JSON.stringify({ token: resetToken, password }),
        cache: 'no-store',
        credentials: 'omit',
        redirect: 'error',
        referrerPolicy: 'no-referrer'
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || `تعذر حفظ كلمة المرور (HTTP ${response.status}).`);

      resetToken = '';
      form.reset();
      form.hidden = true;
      successActions.hidden = false;
      setStatus(data.message || 'تم تعيين كلمة المرور وإلغاء الجلسات السابقة. يمكنك تسجيل الدخول الآن.', 'success');
    } catch (error) {
      setStatus(error.message || 'تعذر حفظ كلمة المرور.', 'error');
    } finally {
      saveButton.disabled = false;
    }
  }

  function init() {
    resetToken = readToken();
    if (!resetToken || !/^[A-Za-z0-9_-]{32,500}$/.test(resetToken)) {
      setStatus('الرابط غير مكتمل أو لا يحتوي رمزًا صالحًا. استخدم أحدث رابط فقط.', 'error');
      return;
    }
    form.hidden = false;
    setStatus('تم تحميل أحدث رمز إعادة تعيين. أدخل كلمة المرور الجديدة ثم احفظها.', 'success');
    form.addEventListener('submit', submit);
  }

  init();
})();
