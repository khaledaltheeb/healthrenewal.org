(() => {
  'use strict';

  const config = window.PT_SPECIALIST_CONFIG || {};
  const $ = id => document.getElementById(id);

  function credentials() {
    const fragment = new URLSearchParams(location.hash.replace(/^#/, ''));
    const params = new URLSearchParams(location.search);
    return {
      conversationId:fragment.get('conversation') || params.get('conversation') ||
        sessionStorage.getItem('ptConversationId') || '',
      token:fragment.get('token') || params.get('token') ||
        sessionStorage.getItem('ptConversationToken') || '',
      role:fragment.get('role') || params.get('role') ||
        sessionStorage.getItem('ptConversationRole') || 'visitor'
    };
  }

  function apiUrl(path) {
    try {
      const parsed = new URL(String(config.apiBase || '').trim());
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
          parsed.search || parsed.hash) return '';
      return `${parsed.href.replace(/\/$/, '')}${path}`;
    } catch (_) {
      return '';
    }
  }

  function displayStatus(message, state = 'loading') {
    const box = $('form-status');
    if (!box) return;
    box.hidden = false;
    box.dataset.state = state;
    box.textContent = message;
    box.focus?.();
  }

  async function patchStatus(nextStatus, auth) {
    const url = apiUrl(`/v1/conversations/${encodeURIComponent(auth.conversationId)}`);
    if (!url) throw new Error('خدمة الرسائل الخلفية غير مرتبطة بعد.');
    const response = await fetch(url, {
      method:'PATCH',
      headers:{
        accept:'application/json',
        authorization:`Bearer ${auth.token}`,
        'x-conversation-role':auth.role,
        'content-type':'application/json;charset=UTF-8'
      },
      body:JSON.stringify({status:nextStatus}),
      cache:'no-store',
      credentials:'omit',
      referrerPolicy:'no-referrer',
      redirect:'error'
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'تعذر تحديث حالة المحادثة.');
    return data;
  }

  function cleanSensitiveUrl() {
    const url = new URL(location.href);
    if (!url.searchParams.has('token') && !url.hash) return;
    url.searchParams.delete('token');
    url.searchParams.delete('conversation');
    url.searchParams.delete('role');
    history.replaceState({}, document.title, `${url.pathname}${url.search}`);
  }

  function updateControls(status, role) {
    const button = $('toggle-conversation-status');
    const form = $('message-form');
    if (!button) return;
    const isClosed = status === 'closed';
    const locked = ['blocked','archived'].includes(status);
    button.hidden = locked || (role === 'visitor' && isClosed);
    button.dataset.nextStatus = isClosed ? 'open' : 'closed';
    button.textContent = isClosed ? 'إعادة فتح المحادثة' : 'إغلاق المحادثة';
    if (form) {
      form.querySelectorAll('textarea,button').forEach(control => {
        if (control.id !== 'toggle-conversation-status') control.disabled = isClosed || locked;
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'portal') return;
    const auth = credentials();
    if (!auth.conversationId || !auth.token) return;

    cleanSensitiveUrl();

    const statusNode = $('conversation-status');
    if (statusNode) {
      const sync = () => updateControls(statusNode.textContent.trim(), auth.role);
      new MutationObserver(sync).observe(statusNode, {childList:true, subtree:true, characterData:true});
      sync();
    }

    $('toggle-conversation-status')?.addEventListener('click', async event => {
      const button = event.currentTarget;
      const nextStatus = button.dataset.nextStatus || 'closed';
      button.disabled = true;
      try {
        const result = await patchStatus(nextStatus, auth);
        displayStatus(
          result.status === 'closed' ? 'تم إغلاق المحادثة.' : 'تمت إعادة فتح المحادثة.',
          'success'
        );
        $('refresh-conversation')?.click();
      } catch (error) {
        displayStatus(error.message || 'تعذر تحديث حالة المحادثة.', 'error');
      } finally {
        button.disabled = false;
      }
    });
  });
})();
