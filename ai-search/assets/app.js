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

const worker = new Worker(new URL('./search-worker.js', import.meta.url), { type: 'module' });
let isReady = false;
let activeRequest = 0;

function setStatus(message, state = 'loading') {
  statusText.textContent = message;
  statusNode.classList.toggle('ready', state === 'ready');
  statusNode.classList.toggle('error', state === 'error');
}

function setBusy(busy) {
  searchButton.disabled = busy;
  searchButton.textContent = busy ? 'جارٍ البحث…' : 'ابحث';
}

function updateUrl(query) {
  const url = new URL(window.location.href);
  if (query) url.searchParams.set('q', query);
  else url.searchParams.delete('q');
  window.history.replaceState({}, '', url);
}

function appendText(element, text) {
  element.append(document.createTextNode(text ?? ''));
}

function createResultCard(result, index) {
  const article = document.createElement('article');
  article.className = 'result-card';

  const meta = document.createElement('div');
  meta.className = 'result-meta';

  const rank = document.createElement('span');
  appendText(rank, `النتيجة ${index + 1}`);
  meta.append(rank);

  if (result.section) {
    const section = document.createElement('span');
    appendText(section, result.section);
    meta.append(section);
  }

  if (Number.isFinite(result.score)) {
    const score = document.createElement('span');
    score.className = 'score';
    score.dir = 'ltr';
    appendText(score, `${Math.round(result.score * 100)}%`);
    score.title = 'درجة صلة نسبية وليست نسبة يقين طبي';
    meta.append(score);
  }

  const heading = document.createElement('h3');
  const link = document.createElement('a');
  link.href = result.url;
  appendText(link, result.title || 'صفحة من المنصة');
  heading.append(link);

  const excerpt = document.createElement('p');
  appendText(excerpt, result.excerpt || result.text || '');

  const sourceLink = document.createElement('a');
  sourceLink.className = 'result-link';
  sourceLink.href = result.url;
  appendText(sourceLink, 'فتح الصفحة الأصلية ←');

  article.append(meta, heading, excerpt, sourceLink);
  return article;
}

function renderResults(payload) {
  resultsNode.replaceChildren();
  const results = Array.isArray(payload.results) ? payload.results : [];
  const modeLabel = payload.mode === 'semantic' ? 'بحث دلالي هجين' : 'بحث نصي محلي';

  if (!results.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    appendText(empty, 'لم تظهر نتائج كافية. جرّب صياغة أقصر، أو استخدم اسم الحالة أو الموضوع مباشرة.');
    resultsNode.append(empty);
    summaryNode.textContent = `لم تُعثر نتائج مناسبة باستخدام ${modeLabel}.`;
    return;
  }

  const fragment = document.createDocumentFragment();
  results.forEach((result, index) => fragment.append(createResultCard(result, index)));
  resultsNode.append(fragment);
  summaryNode.textContent = `${results.length} نتيجة مرتبة باستخدام ${modeLabel}.`;
}

function populateSections(sections = []) {
  for (const section of sections) {
    const option = document.createElement('option');
    option.value = section.value;
    option.textContent = `${section.label} (${section.count})`;
    sectionFilter.append(option);
  }
}

async function submitSearch() {
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    return;
  }

  const requestId = ++activeRequest;
  setBusy(true);
  setStatus(semanticToggle.checked ? 'يجري فهم السؤال وترتيب المقاطع…' : 'يجري البحث النصي في الفهرس…');
  updateUrl(query);

  worker.postMessage({
    type: 'search',
    requestId,
    query,
    semantic: semanticToggle.checked,
    filters: {
      section: sectionFilter.value,
      audience: audienceFilter.value,
    },
    limit: 12,
  });
}

worker.addEventListener('message', (event) => {
  const message = event.data || {};

  if (message.type === 'index-progress') {
    setStatus(message.message || 'جارٍ تحميل فهرس البحث…');
    return;
  }

  if (message.type === 'model-progress') {
    progressNode.hidden = false;
    if (typeof message.progress === 'number') progressNode.value = message.progress;
    setStatus(message.message || 'جارٍ تحميل نموذج فهم اللغة لأول مرة…');
    return;
  }

  if (message.type === 'ready') {
    isReady = true;
    populateSections(message.sections);
    setStatus(message.semanticAvailable
      ? `الفهرس جاهز: ${message.chunkCount.toLocaleString('ar')} مقطع قابل للبحث.`
      : 'النسخة النصية جاهزة. سيعمل الفهرس الدلالي الكامل بعد توليده ونشره.', 'ready');

    const initialQuery = new URL(window.location.href).searchParams.get('q');
    if (initialQuery) {
      queryInput.value = initialQuery;
      submitSearch();
    }
    return;
  }

  if (message.type === 'results') {
    if (message.requestId !== activeRequest) return;
    setBusy(false);
    progressNode.hidden = true;
    renderResults(message);
    setStatus(message.mode === 'semantic'
      ? 'اكتمل البحث الدلالي. الدرجات نسبية لترتيب النتائج فقط.'
      : 'اكتمل البحث النصي المحلي.', 'ready');
    document.querySelector('#results-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  if (message.type === 'warning') {
    if (message.requestId && message.requestId !== activeRequest) return;
    setStatus(message.message, 'error');
    return;
  }

  if (message.type === 'error') {
    if (message.requestId && message.requestId !== activeRequest) return;
    setBusy(false);
    progressNode.hidden = true;
    setStatus(message.message || 'تعذر تشغيل البحث. أعد تحميل الصفحة وحاول مرة أخرى.', 'error');
  }
});

worker.addEventListener('error', () => {
  setBusy(false);
  setStatus('تعذر تشغيل وحدة البحث في هذا المتصفح.', 'error');
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (isReady) submitSearch();
});

for (const button of document.querySelectorAll('[data-example]')) {
  button.addEventListener('click', () => {
    queryInput.value = button.dataset.example || '';
    queryInput.focus();
    if (isReady) submitSearch();
  });
}

worker.postMessage({
  type: 'initialize',
  manifestUrl: new URL('../data/manifest.json', import.meta.url).href,
  fallbackUrl: new URL('../../api/v1/platform.json', import.meta.url).href,
});
