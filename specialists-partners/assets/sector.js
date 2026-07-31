(() => {
  'use strict';

  const core = window.PT_SPECIALIST_DIRECTORY_CORE;
  if (!core) throw new Error('specialist_directory_core_missing');

  const state = {
    providers: [],
    filtered: [],
    updatedAt: null,
    source: 'loading',
    loadState: 'loading',
    matchCriteria: null
  };
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const norm = core.normalizeArabic;
  const config = window.PT_SPECIALIST_CONFIG || {};

  const labels = {
    speech_language:'النطق واللغة والتواصل', audiology:'السمع والسمعيات',
    special_education:'التربية الخاصة والخطط الفردية', early_intervention:'التدخل المبكر',
    occupational_therapy:'العلاج الوظيفي والأداء اليومي', behavior_support:'الدعم السلوكي الإيجابي',
    learning_support:'صعوبات التعلم والدعم الأكاديمي', autism_support:'دعم اضطراب طيف التوحد',
    aac:'التواصل المعزز والبديل', family_training:'تدريب الأسرة ومقدمي الرعاية',
    psychology:'علم النفس والدعم النفسي', psychiatry:'الطب النفسي', social_work:'الخدمة الاجتماعية',
    physiotherapy:'العلاج الطبيعي', nutrition:'التغذية العلاجية', center:'مركز متعدد التخصصات'
  };
  const statusLabels = {verified:'موثّق', provisional:'تحقق أولي', pending:'قيد التحقق', unverified:'غير موثّق'};

  function directorySourceLabel(source) {
    if (source === 'live-verified-registry') return 'السجل الحي الموثّق';
    if (source === 'static-verified-fallback') return 'النسخة العامة الاحتياطية';
    return 'غير متاح';
  }

  function updateDirectoryStatus(status, label) {
    const health = $('directory-health');
    if (health) health.dataset.state = status;
    if ($('directory-health-label')) $('directory-health-label').textContent = label;
    if ($('directory-source')) $('directory-source').textContent = directorySourceLabel(state.source);
    if ($('directory-updated')) $('directory-updated').textContent = core.formatUpdatedAt(state.updatedAt);
  }

  function safeHref(value) {
    if (!value) return '';
    try {
      const parsed = new URL(String(value), location.origin);
      return ['https:','mailto:','tel:'].includes(parsed.protocol) ? parsed.href : '';
    } catch (_) { return ''; }
  }

  function safeWebUrl(value) {
    const href = safeHref(value);
    if (!href) return '';
    try {
      const protocol = new URL(href, location.origin).protocol;
      return protocol === 'https:' ? href : '';
    } catch (_) { return ''; }
  }

  function configuredApiBase() {
    try {
      const parsed = new URL(String(config.apiBase || '').trim());
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
          parsed.search || parsed.hash) return '';
      return parsed.href.replace(/\/$/, '');
    } catch (_) {
      return '';
    }
  }

  function contactUrl(provider) {
    return `contact.html?provider=${encodeURIComponent(provider.id)}`;
  }

  function profileUrl(provider) {
    return safeWebUrl(provider.profileUrl) || '';
  }

  function availabilityBadge(provider) {
    const status = provider.availability?.status || (provider.communication?.acceptsNewRequests ? 'available' : 'unavailable');
    const text = status === 'available' ? 'يستقبل طلبات جديدة' : status === 'limited' ? 'توفر محدود' : 'غير متاح حاليًا';
    const cls = status === 'available' ? 'available' : status === 'limited' ? 'pending' : 'unavailable';
    return `<span class="badge ${cls}">${esc(text)}</span>`;
  }

  function card(provider) {
    const specialties = (provider.specialties || []).slice(0, 5).map(item => `<span class="chip">${esc(labels[item] || item)}</span>`).join('');
    const verification = provider.verification?.status || 'pending';
    const profile = profileUrl(provider);
    const canMessage = provider.communication?.enabled === true && provider.communication?.acceptsNewRequests !== false;
    const areas = [provider.location?.area, ...(provider.serviceAreas || [])].filter(Boolean).join('، ');
    const response = provider.communication?.typicalResponse || 'غير معلن';
    const publicContact = safeHref(provider.contact?.publicUrl || provider.contact?.website || (provider.contact?.publicEmail ? `mailto:${provider.contact.publicEmail}` : '') || (provider.contact?.publicPhone ? `tel:${String(provider.contact.publicPhone).replace(/[^+\d]/g, '')}` : ''));
    const actions = [
      profile ? `<a class="button secondary" href="${esc(profile)}">عرض الملف المهني</a>` : '',
      canMessage ? `<a class="button primary" href="${esc(contactUrl(provider))}">تواصل مع المختص</a>` : '<span class="small">التواصل الداخلي غير متاح حاليًا</span>',
      publicContact ? `<a class="button secondary" href="${esc(publicContact)}" rel="nofollow">وسيلة التواصل العامة</a>` : ''
    ].filter(Boolean).join('');

    return `<article class="provider-card" data-provider-id="${esc(provider.id)}">
      <div class="provider-top">
        <div>
          <p class="eyebrow">${provider.entityType === 'center' ? 'مركز أو جهة شريكة' : 'مختص ضمن الشبكة المهنية'}</p>
          <h3>${esc(provider.displayName)}</h3>
          <div class="provider-meta">${esc(provider.professionalTitle || provider.centerType || '')}</div>
        </div>
        <span class="badge ${esc(verification)}">${esc(statusLabels[verification] || verification)}</span>
      </div>
      <div class="availability-row">${availabilityBadge(provider)}${provider.roleInNetwork ? `<span class="badge provisional">${esc(provider.roleInNetwork)}</span>` : ''}</div>
      <div class="chips">${specialties}</div>
      <dl>
        <dt>الموقع</dt><dd>${esc([provider.location?.city, provider.location?.country].filter(Boolean).join('، ') || 'غير محدد')}</dd>
        <dt>نطاق العمل</dt><dd>${esc(areas || 'وفق الاتفاق')}</dd>
        <dt>الفئات</dt><dd>${esc((provider.ageGroups || []).join('، ') || 'غير محددة')}</dd>
        <dt>طريقة الخدمة</dt><dd>${esc((provider.serviceModes || []).join('، ') || 'غير محددة')}</dd>
        <dt>اللغات</dt><dd>${esc((provider.languages || []).join('، ') || 'غير محددة')}</dd>
        <dt>الرد المتوقع</dt><dd>${esc(response)}</dd>
      </dl>
      <p class="summary">${esc(provider.shortBio || '')}</p>
      <div class="provider-actions">${actions}</div>
      <p class="fine">آخر تحقق: ${esc(core.formatUpdatedAt(provider.verification?.lastVerifiedAt))} · لا يعني التحقق ضمان الملاءمة أو النتيجة.</p>
    </article>`;
  }

  function render() {
    const list = $('provider-list');
    const count = $('provider-count');
    const empty = $('provider-empty');
    if (!list || !count || !empty) return;
    count.textContent = `${state.filtered.length} ملف مطابق`;
    list.innerHTML = state.filtered.map(card).join('');
    empty.classList.toggle('hidden', state.filtered.length > 0);
    const detail = $('provider-empty-detail');
    if (detail && state.filtered.length === 0) {
      if (state.loadState === 'error') {
        detail.textContent = 'تعذر الوصول إلى السجل الحي والنسخة الاحتياطية. أعد المحاولة لاحقًا أو راجع صفحة حالة التحقق.';
      } else if (state.providers.length > 0) {
        detail.textContent = 'لا توجد ملفات تحقق شروط البحث الحالية. غيّر المرشحات أو أعد ضبطها لعرض جميع الملفات المنشورة.';
      } else if (state.source === 'static-verified-fallback') {
        detail.textContent = 'لا تحتوي النسخة العامة الاحتياطية حاليًا أي ملف مكتمل التحقق والنشر والموافقة الكتابية.';
      } else {
        detail.textContent = 'لا توجد حاليًا ملفات مهنية مكتملة التحقق والنشر والموافقة الكتابية في السجل العام.';
      }
    }
    if ($('directory-filter-context')) {
      $('directory-filter-context').textContent = state.matchCriteria
        ? `تطبيق المسار المقترح عبر ${state.matchCriteria.specialtyAny.length} تخصصات محتملة`
        : 'ترتيب محايد: التوفر، ثم حداثة التحقق، ثم الاسم';
    }
    updateMetrics();
  }

  function updateMetrics() {
    const verified = state.providers.filter(p => p.verification?.status === 'verified').length;
    const accepting = state.providers.filter(p => p.communication?.enabled && p.communication?.acceptsNewRequests !== false).length;
    const specialties = new Set(state.providers.flatMap(p => p.specialties || [])).size;
    const countries = new Set(state.providers.map(p => p.location?.country).filter(Boolean)).size;
    if ($('metric-providers')) $('metric-providers').textContent = String(state.providers.length);
    if ($('metric-verified')) $('metric-verified').textContent = String(verified);
    if ($('metric-accepting')) $('metric-accepting').textContent = String(accepting);
    if ($('metric-coverage')) $('metric-coverage').textContent = `${countries || 0}/${specialties || 0}`;
  }

  function populateDynamicFilters() {
    const country = $('country-filter');
    const language = $('language-filter');
    if (country) {
      const values = [...new Set(state.providers.map(p => p.location?.country).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'ar'));
      country.innerHTML = '<option value="">كل الدول</option>' + values.map(value => `<option>${esc(value)}</option>`).join('');
    }
    if (language) {
      const values = [...new Set(state.providers.flatMap(p => p.languages || []))].sort((a,b) => a.localeCompare(b, 'ar'));
      language.innerHTML = '<option value="">كل اللغات</option>' + values.map(value => `<option>${esc(value)}</option>`).join('');
    }
  }

  function currentFilters() {
    return {
      query: $('directory-search')?.value || '',
      type: $('entity-type')?.value || '',
      specialty: $('specialty-filter')?.value || '',
      country: $('country-filter')?.value || '',
      city: $('city-filter')?.value || '',
      area: $('area-filter')?.value || '',
      mode: $('mode-filter')?.value || '',
      age: $('age-filter')?.value || '',
      language: $('language-filter')?.value || '',
      verifiedOnly: Boolean($('verified-only')?.checked),
      acceptingOnly: Boolean($('accepting-only')?.checked)
    };
  }

  function filter() {
    const filters = state.matchCriteria
      ? {...currentFilters(), ...state.matchCriteria}
      : currentFilters();
    state.filtered = core.filterProviders(state.providers, filters, labels);
    render();
  }

  function reset() {
    ['directory-search','entity-type','specialty-filter','country-filter','city-filter','area-filter','mode-filter','age-filter','language-filter'].forEach(id => {
      if ($(id)) $(id).value = '';
    });
    ['verified-only','accepting-only'].forEach(id => { if ($(id)) $(id).checked = false; });
    state.matchCriteria = null;
    filter();
  }

  function match(event) {
    event.preventDefault();
    const need = $('match-need')?.value || '';
    const items = core.recommendations(need);
    const age = $('match-age')?.value || '';
    const mode = $('match-mode')?.value || '';
    const country = $('match-country')?.value || '';
    const city = $('match-city')?.value || '';
    const criteria = {
      specialtyAny: items,
      age,
      mode,
      country,
      city,
      verifiedOnly: true
    };
    const matches = core.filterProviders(state.providers, criteria, labels);
    const names = items.map(item => labels[item] || item);
    const result = $('match-result');
    if (!result) return;
    result.innerHTML = `<h3>المسار المهني الأقرب</h3>
      <p>ابدأ بمراجعة تخصص أو أكثر من المسارات التالية. الاختيار هنا تنظيمي ولا يثبت تشخيصًا أو خطة علاجية.</p>
      <div class="chips">${names.map(name => `<span class="chip">${esc(name)}</span>`).join('')}</div>
      <p><strong>ملفات موثقة مطابقة حاليًا:</strong> ${matches.length}</p>
      ${matches.length ? `<p><a class="button primary" href="#directory" id="apply-match-filter">عرض النتائج المطابقة</a></p>` : '<p class="small">لا توجد حاليًا ملفات منشورة تحقق جميع هذه الشروط. يمكنك توسيع الموقع أو طريقة الخدمة، أو العودة لاحقًا بعد اكتمال التحقق من ملفات جديدة.</p>'}`;
    $('apply-match-filter')?.addEventListener('click', () => {
      reset();
      if ($('country-filter')) $('country-filter').value = country;
      if ($('city-filter')) $('city-filter').value = city;
      if ($('mode-filter')) $('mode-filter').value = mode;
      if ($('age-filter')) $('age-filter').value = age;
      if ($('verified-only')) $('verified-only').checked = true;
      state.matchCriteria = criteria;
      filter();
    });
  }

  async function fetchJson(url, timeoutMs = 6500) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('directory_timeout'), timeoutMs);
    try {
      const response = await fetch(url, {
        cache:'no-store',
        credentials:'omit',
        referrerPolicy:'no-referrer',
        headers:{accept:'application/json'},
        signal:controller.signal
      });
      if (!response.ok) throw new Error(`directory_http_${response.status}`);
      return await response.json();
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function directoryPayload() {
    const apiBase = configuredApiBase();
    if (apiBase) {
      try {
        const payload = await fetchJson(`${apiBase}/v1/providers?limit=250`);
        return {...payload, source:'live-verified-registry'};
      } catch (error) {
        console.warn('specialist_directory_live_fallback', error);
      }
    }
    const payload = await fetchJson('data/providers.json');
    return {...payload, source:'static-verified-fallback'};
  }

  async function load() {
    try {
      const data = await directoryPayload();
      state.providers = core.prepareProviders(data.providers);
      state.filtered = [...state.providers];
      state.updatedAt = data.updatedAt || null;
      state.source = data.source || 'unknown';
      state.loadState = 'ready';
      updateDirectoryStatus(
        state.source === 'live-verified-registry' ? 'healthy' : 'warning',
        state.source === 'live-verified-registry' ? 'متصل بالسجل الحي' : 'وضع القراءة الاحتياطي'
      );
      populateDynamicFilters();
      render();
    } catch (error) {
      state.providers = [];
      state.filtered = [];
      state.updatedAt = null;
      state.source = 'unavailable';
      state.loadState = 'error';
      updateDirectoryStatus('error', 'تعذر تحميل سجل الدليل');
      console.error('specialist_directory_unavailable', error);
      render();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    load();
    ['directory-search','entity-type','specialty-filter','country-filter','city-filter','area-filter','mode-filter','age-filter','language-filter','verified-only','accepting-only']
      .forEach(id => $(id)?.addEventListener('input', () => {
        state.matchCriteria = null;
        filter();
      }));
    $('reset-filters')?.addEventListener('click', reset);
    $('matcher-form')?.addEventListener('submit', match);
    if (!config.apiBase) document.documentElement.dataset.messagingStatus = 'pending-backend';
  });
})();
