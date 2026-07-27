(() => {
  'use strict';

  const state = { providers: [], filtered: [], updatedAt: null };
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const norm = value => String(value || '').normalize('NFKD').trim().toLowerCase();
  const same = (a, b) => norm(a) === norm(b);
  const includes = (items, value) => !value || (Array.isArray(items) && items.some(item => same(item, value)));
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

  function safeHref(value) {
    if (!value) return '';
    try {
      const parsed = new URL(String(value), location.origin);
      return ['http:','https:','mailto:','tel:'].includes(parsed.protocol) ? parsed.href : '';
    } catch (_) { return ''; }
  }

  function safeWebUrl(value) {
    const href = safeHref(value);
    if (!href) return '';
    try {
      const protocol = new URL(href, location.origin).protocol;
      return ['http:', 'https:'].includes(protocol) ? href : '';
    } catch (_) { return ''; }
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
      <p class="fine">آخر تحقق: ${esc(provider.verification?.lastVerifiedAt || 'لم يُسجّل بعد')} · لا يعني التحقق ضمان الملاءمة أو النتيجة.</p>
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

  function filter() {
    const query = norm($('directory-search')?.value);
    const type = $('entity-type')?.value || '';
    const specialty = $('specialty-filter')?.value || '';
    const country = norm($('country-filter')?.value);
    const city = norm($('city-filter')?.value);
    const area = norm($('area-filter')?.value);
    const mode = $('mode-filter')?.value || '';
    const age = $('age-filter')?.value || '';
    const language = $('language-filter')?.value || '';
    const verified = Boolean($('verified-only')?.checked);
    const accepting = Boolean($('accepting-only')?.checked);

    state.filtered = state.providers.filter(provider => {
      const text = norm([
        provider.displayName, provider.professionalTitle, provider.centerType, provider.shortBio,
        ...(provider.specialties || []).map(item => labels[item] || item), ...(provider.services || []),
        provider.location?.country, provider.location?.city, provider.location?.area, ...(provider.serviceAreas || [])
      ].join(' '));
      const areaText = norm([provider.location?.area, ...(provider.serviceAreas || [])].filter(Boolean).join(' '));
      return (!query || text.includes(query)) &&
        (!type || provider.entityType === type) &&
        includes(provider.specialties, specialty) &&
        (!country || norm(provider.location?.country).includes(country)) &&
        (!city || norm(provider.location?.city).includes(city)) &&
        (!area || areaText.includes(area)) &&
        includes(provider.serviceModes, mode) &&
        includes(provider.ageGroups, age) &&
        includes(provider.languages, language) &&
        (!verified || provider.verification?.status === 'verified') &&
        (!accepting || (provider.communication?.enabled === true && provider.communication?.acceptsNewRequests !== false));
    });
    render();
  }

  function reset() {
    ['directory-search','entity-type','specialty-filter','country-filter','city-filter','area-filter','mode-filter','age-filter','language-filter'].forEach(id => {
      if ($(id)) $(id).value = '';
    });
    ['verified-only','accepting-only'].forEach(id => { if ($(id)) $(id).checked = false; });
    filter();
  }

  function recommendations(need) {
    return ({
      speech:['speech_language','aac','audiology'], hearing:['audiology','speech_language'],
      learning:['learning_support','special_education'], autism:['autism_support','speech_language','occupational_therapy','special_education'],
      development:['early_intervention','speech_language','occupational_therapy'], behavior:['behavior_support','psychology','family_training'],
      independence:['occupational_therapy','special_education','family_training'], mental_health:['psychology','psychiatry','social_work'],
      family:['family_training','psychology','social_work'], center:['center']
    }[need] || ['special_education']);
  }

  function match(event) {
    event.preventDefault();
    const need = $('match-need')?.value || '';
    const items = recommendations(need);
    const age = $('match-age')?.value || '';
    const mode = $('match-mode')?.value || '';
    const country = norm($('match-country')?.value);
    const city = norm($('match-city')?.value);
    const matches = state.providers.filter(provider =>
      items.some(item => includes(provider.specialties, item) || (item === 'center' && provider.entityType === 'center')) &&
      includes(provider.ageGroups, age) && includes(provider.serviceModes, mode) &&
      (!country || norm(provider.location?.country).includes(country)) &&
      (!city || norm(provider.location?.city).includes(city)) &&
      provider.verification?.status === 'verified'
    );
    const names = items.map(item => labels[item] || item);
    const result = $('match-result');
    if (!result) return;
    result.innerHTML = `<h3>المسار المهني الأقرب</h3>
      <p>ابدأ بمراجعة تخصص أو أكثر من المسارات التالية. الاختيار هنا تنظيمي ولا يثبت تشخيصًا أو خطة علاجية.</p>
      <div class="chips">${names.map(name => `<span class="chip">${esc(name)}</span>`).join('')}</div>
      <p><strong>ملفات موثقة مطابقة حاليًا:</strong> ${matches.length}</p>
      ${matches.length ? `<p><a class="button primary" href="#directory" id="apply-match-filter">عرض النتائج المطابقة</a></p>` : '<p class="small">سيظهر المختصون هنا فور إضافة الملفات وتفعيلها.</p>'}`;
    $('apply-match-filter')?.addEventListener('click', () => {
      if ($('specialty-filter')) $('specialty-filter').value = items[0] || '';
      if ($('country-filter')) $('country-filter').value = $('match-country')?.value || '';
      if ($('city-filter')) $('city-filter').value = $('match-city')?.value || '';
      filter();
    });
  }

  async function load() {
    try {
      const response = await fetch('data/providers.json',{cache:'no-store'});
      if (!response.ok) throw new Error('directory_load_failed');
      const data = await response.json();
      state.providers=(data.providers||[]).filter(p=>p.publicationStatus==='published'&&p.verification?.status==='verified'&&p.consent?.publicProfileApproved===true);
      state.filtered = [...state.providers];
      state.updatedAt = data.updatedAt || null;
      if ($('directory-updated')) $('directory-updated').textContent = state.updatedAt || 'غير محدد';
      populateDynamicFilters();
      render();
    } catch (error) {
      state.providers = [];
      state.filtered = [];
      if ($('directory-updated')) $('directory-updated').textContent = 'تعذر تحميل البيانات';
      render();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    load();
    ['directory-search','entity-type','specialty-filter','country-filter','city-filter','area-filter','mode-filter','age-filter','language-filter','verified-only','accepting-only']
      .forEach(id => $(id)?.addEventListener('input', filter));
    $('reset-filters')?.addEventListener('click', reset);
    $('matcher-form')?.addEventListener('submit', match);
    if (!config.apiBase) document.documentElement.dataset.messagingStatus = 'pending-backend';
  });
})();
