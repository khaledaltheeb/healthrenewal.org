const form = document.querySelector('#search-form');
const queryInput = document.querySelector('#query');
const searchButton = document.querySelector('#search-button');
const resultsNode = document.querySelector('#results');
const summaryNode = document.querySelector('#results-summary');
const statusNode = document.querySelector('#status');
const statusText = document.querySelector('#status-text');
const progressNode = document.querySelector('#model-progress');
const sectionFilter = document.querySelector('#section-filter');
const audienceFilter = document.querySelector('#audience-filter');
const semanticToggle = document.querySelector('#semantic-toggle');

const worker = new Worker(new URL('./search-worker.js', import.meta.url), { type:'module' });
let ready = false;
let activeRequest = 0;
let indexMode = 'local-sitemap';

function setStatus(message, state = 'loading') {
  statusText.textContent = message;
  statusNode.classList.toggle('ready', state === 'ready');
  statusNode.classList.toggle('error', state === 'error');
}
function setBusy(value) {
  searchButton.disabled = value;
  searchButton.textContent = value ? 'جارٍ البحث…' : 'ابحث';
}
function updateUrl(query) {
  const url = new URL(location.href);
  query ? url.searchParams.set('q', query) : url.searchParams.delete('q');
  history.replaceState({}, '', url);
}
function text(node, value) { node.append(document.createTextNode(value ?? '')); }

function resultCard(result, index) {
  const article = document.createElement('article');
  article.className = 'result-card';
  const meta = document.createElement('div');
  meta.className = 'result-meta';
  const rank = document.createElement('span'); text(rank, `النتيجة ${index + 1}`); meta.append(rank);
  if (result.section) { const section = document.createElement('span'); text(section, result.section); meta.append(section); }
  if (Number.isFinite(result.score)) {
    const score = document.createElement('span'); score.className = 'score'; score.dir = 'ltr';
    text(score, `${Math.round(result.score * 100)}%`); score.title = 'درجة صلة نسبية وليست نسبة يقين طبي'; meta.append(score);
  }
  const heading = document.createElement('h3');
  const link = document.createElement('a'); link.href = result.url; text(link, result.title || 'صفحة من المنصة'); heading.append(link);
  const excerpt = document.createElement('p'); text(excerpt, result.excerpt || result.text || '');
  const source = document.createElement('a'); source.className = 'result-link'; source.href = result.url; text(source, 'فتح الصفحة الأصلية ←');
  article.append(meta, heading, excerpt, source);
  return article;
}

function render(payload) {
  resultsNode.replaceChildren();
  const results = Array.isArray(payload.results) ? payload.results : [];
  const label = payload.mode === 'semantic' ? 'بحث دلالي هجين' : 'بحث نصي محلي';
  if (!results.length) {
    const empty = document.createElement('div'); empty.className = 'empty';
    text(empty, 'لم تظهر نتائج كافية. جرّب صياغة أقصر أو اسم الحالة أو الموضوع مباشرة.');
    resultsNode.append(empty); summaryNode.textContent = `لم تُعثر نتائج مناسبة باستخدام ${label}.`; return;
  }
  const fragment = document.createDocumentFragment();
  results.forEach((result, index) => fragment.append(resultCard(result, index)));
  resultsNode.append(fragment); summaryNode.textContent = `${results.length} نتيجة مرتبة باستخدام ${label}.`;
}

function populateSections(sections = []) {
  sectionFilter.querySelectorAll('option:not(:first-child)').forEach((option) => option.remove());
  for (const section of sections) {
    const option = document.createElement('option'); option.value = section.value;
    option.textContent = `${section.label} (${section.count})`; sectionFilter.append(option);
  }
}

function submitSearch() {
  const query = queryInput.value.trim();
  if (!query) return queryInput.focus();
  const requestId = ++activeRequest;
  setBusy(true);
  setStatus(semanticToggle.checked
    ? (indexMode === 'local-sitemap' ? 'يجري فهم السؤال وبناء أو استعادة الفهرس المحلي…' : 'يجري فهم السؤال وترتيب المقاطع…')
    : 'يجري البحث النصي في فهرس الصفحات…');
  updateUrl(query);
  worker.postMessage({
    type:'search', requestId, query, semantic:semanticToggle.checked,
    filters:{ section:sectionFilter.value, audience:audienceFilter.value }, limit:12
  });
}

worker.addEventListener('message', (event) => {
  const message = event.data || {};
  if (message.type === 'index-progress') { setStatus(message.message || 'جارٍ تجهيز فهرس البحث…'); return; }
  if (message.type === 'model-progress') {
    progressNode.hidden = false;
    if (Number.isFinite(message.progress)) progressNode.value = message.progress;
    setStatus(message.message || 'جارٍ تحميل نموذج فهم اللغة لأول مرة…'); return;
  }
  if (message.type === 'ready') {
    ready = true; indexMode = message.indexMode || 'local-sitemap'; populateSections(message.sections);
    const count = Number(message.chunkCount || 0).toLocaleString('ar');
    setStatus(indexMode === 'generated'
      ? `الفهرس الدلالي المسبق جاهز: ${count} مقطع.`
      : `اكتُشفت ${count} صفحة. عند أول بحث دلالي سيُبنى الفهرس محليًا ويُحفظ على هذا الجهاز.`, 'ready');
    const initial = new URL(location.href).searchParams.get('q');
    if (initial) { queryInput.value = initial; submitSearch(); }
    return;
  }
  if (message.type === 'results') {
    if (message.requestId !== activeRequest) return;
    setBusy(false); progressNode.hidden = true; render(message);
    setStatus(message.mode === 'semantic'
      ? 'اكتمل البحث الدلالي. الدرجات نسبية لترتيب النتائج فقط.'
      : 'اكتمل البحث النصي المحلي.', 'ready');
    document.querySelector('#results-title').scrollIntoView({ behavior:'smooth', block:'start' }); return;
  }
  if (message.type === 'warning') {
    if (message.requestId && message.requestId !== activeRequest) return;
    setStatus(message.message, 'error'); return;
  }
  if (message.type === 'error') {
    if (message.requestId && message.requestId !== activeRequest) return;
    setBusy(false); progressNode.hidden = true;
    setStatus(message.message || 'تعذر تشغيل البحث. أعد تحميل الصفحة وحاول مرة أخرى.', 'error');
  }
});
worker.addEventListener('error', () => { setBusy(false); setStatus('تعذر تشغيل وحدة البحث في هذا المتصفح.', 'error'); });
form.addEventListener('submit', (event) => { event.preventDefault(); if (ready) submitSearch(); });
for (const button of document.querySelectorAll('[data-example]')) button.addEventListener('click', () => {
  queryInput.value = button.dataset.example || ''; queryInput.focus(); if (ready) submitSearch();
});

worker.postMessage({
  type:'initialize',
  manifestUrl:new URL('../data/manifest.json', import.meta.url).href,
  sitemapIndexUrl:new URL('../../sitemap-index.xml', import.meta.url).href,
  fallbackUrl:new URL('../../api/v1/platform.json', import.meta.url).href
});
