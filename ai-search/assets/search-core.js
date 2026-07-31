const ARABIC_DIACRITICS = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;
const NON_WORD = /[^\p{L}\p{N}]+/gu;
const STOP_WORDS = new Set([
  'في','من','على','إلى','الى','عن','ما','ماذا','كيف','هل','هو','هي','هذا','هذه','ذلك','تلك','مع','او','أو','ثم','و','يا','لدى','عند','بعد','قبل','كل','أي','اي',
  'the','a','an','of','to','and','or','for','in','on','with','is','are'
]);

export function normalizeArabic(value) {
  return String(value || '').toLowerCase().normalize('NFKC')
    .replace(ARABIC_DIACRITICS, '').replace(/[إأآٱ]/g, 'ا').replace(/ى/g, 'ي')
    .replace(/ؤ/g, 'و').replace(/ئ/g, 'ي').replace(/ـ/g, '')
    .replace(NON_WORD, ' ').replace(/\s+/g, ' ').trim();
}

export function tokenize(value) {
  return normalizeArabic(value).split(' ').filter((token) => token.length > 1 && !STOP_WORDS.has(token));
}

export function sectionLabel(key) {
  const labels = {
    encyclopedia:'الموسوعة النفسية', capabilities:'مكتبة القدرات والحالات', 'special-needs':'ذوو الاحتياجات الخاصة',
    'family-guide':'دليل الأسرة', family:'الأسرة', comparisons:'المقارنات', magazine:'المجلة والأبحاث',
    library:'المكتبة', 'care-guides':'أدلة التعامل', 'daily-tools':'الأدوات اليومية', assessments:'المقاييس والتقييم',
    sectors:'القطاعات', tips:'النصائح', 'learning-paths':'مسارات التعلم', 'provider-assessment-demo':'منصة التقييم',
    'specialists-partners':'المختصون والشركاء', trust:'الثقة والمنهجية', api:'واجهة البيانات'
  };
  return labels[key] || key || 'المنصة';
}

function inferAudience(pathname) {
  const value = pathname.toLowerCase();
  const result = new Set(['general']);
  if (/family|parent|caregiver|child|youth|school/.test(value)) result.add('family');
  if (/provider|professional|specialist|assessment|clinical|service/.test(value)) result.add('professional');
  if (/library|magazine|research|study|evidence|student/.test(value)) result.add('student');
  return [...result];
}

function decodeEntities(value) {
  return String(value || '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)));
}

function humanize(value) {
  let decoded = value;
  try { decoded = decodeURIComponent(value); } catch (_) { /* keep original */ }
  return decoded.replace(/\.(?:html?|php)$/i, '').replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function documentFromUrl(url, basePath, index) {
  const parsed = new URL(url);
  const segments = parsed.pathname.split('/').filter(Boolean);
  const prefix = basePath.split('/').filter(Boolean)[0] || '';
  const contentSegments = segments[0] === prefix ? segments.slice(1) : segments;
  const sectionKey = contentSegments[0] || '';
  const readable = contentSegments.map(humanize).filter(Boolean);
  const section = sectionLabel(sectionKey);
  const title = readable.at(-1) || section;
  const seedText = `${section}. ${readable.join(' · ')}. ${parsed.pathname}`;
  return {
    id:`sitemap-${index}`, title, section, sectionKey, audience:inferAudience(parsed.pathname),
    url:parsed.href, excerpt:seedText, text:seedText, seedText,
    normalizedTitle:normalizeArabic(title), normalizedText:normalizeArabic(seedText)
  };
}

async function fetchText(url, { timeout = 15000, accept = 'text/html,application/xml,text/xml;q=0.9,*/*;q=0.1', cache = 'force-cache' } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { signal:controller.signal, cache, headers:{ Accept:accept } });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
    return response.text();
  } finally { clearTimeout(timer); }
}

async function fetchJson(url) {
  const response = await fetch(url, { cache:'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
  return response.json();
}

function parseLocs(xml) {
  const result = [];
  const pattern = /<loc(?:\s[^>]*)?>([\s\S]*?)<\/loc>/gi;
  let match;
  while ((match = pattern.exec(xml))) result.push(decodeEntities(match[1].trim()));
  return result;
}

async function mapLimit(items, limit, mapper) {
  const output = new Array(items.length);
  let cursor = 0;
  const workers = Array.from({ length:Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      try { output[index] = await mapper(items[index], index); } catch (_) { output[index] = null; }
    }
  });
  await Promise.all(workers);
  return output;
}

function searchable(url, origin, basePath) {
  try {
    const parsed = new URL(url);
    if (parsed.origin !== origin || !parsed.pathname.startsWith(basePath)) return false;
    const path = parsed.pathname.toLowerCase();
    if (/\/(?:assets|api|reports|node_modules|tests|scripts)\//.test(path)) return false;
    if (/\.(?:xml|json|txt|css|js|mjs|map|svg|png|jpe?g|webp|gif|ico|pdf|zip|gz|woff2?|ttf|mp3|mp4)$/i.test(path)) return false;
    return path.endsWith('/') || /\.html?$/i.test(path);
  } catch (_) { return false; }
}

function curatedDocuments(payload, basePath) {
  return (Array.isArray(payload?.resources) ? payload.resources : []).map((resource, index) => {
    const url = resource.url || '#';
    let sectionKey = '', section = 'المنصة', audience = ['general'];
    try {
      const parsed = new URL(url);
      const segments = parsed.pathname.split('/').filter(Boolean);
      const prefix = basePath.split('/').filter(Boolean)[0] || '';
      const content = segments[0] === prefix ? segments.slice(1) : segments;
      sectionKey = content[0] || ''; section = sectionLabel(sectionKey); audience = inferAudience(parsed.pathname);
    } catch (_) { /* keep defaults */ }
    const tags = Array.isArray(resource.tags) ? resource.tags : [];
    const text = [resource.title, tags.join(' '), resource.type, resource.sourcePolicy].filter(Boolean).join('. ');
    return {
      id:resource.id || `curated-${index}`, title:resource.title || 'مورد من المنصة', section, sectionKey, audience, url,
      excerpt:text, text, seedText:text, normalizedTitle:normalizeArabic(resource.title), normalizedText:normalizeArabic(text)
    };
  });
}

export async function discoverDocuments(sitemapIndexUrl, fallbackUrl, progress, maxDocuments = 6000) {
  const indexUrl = new URL(sitemapIndexUrl);
  const pathParts = indexUrl.pathname.split('/').filter(Boolean);
  const basePath = pathParts.length > 1 ? `/${pathParts[0]}/` : '/';
  progress('قراءة خرائط الموقع واكتشاف الصفحات…');
  const rootXml = await fetchText(sitemapIndexUrl, { accept:'application/xml,text/xml' });
  let urls = [];
  if (/<sitemapindex\b/i.test(rootXml)) {
    const sitemaps = parseLocs(rootXml).filter((url) => {
      try { const parsed = new URL(url); return parsed.origin === indexUrl.origin && parsed.pathname.startsWith(basePath); }
      catch (_) { return false; }
    }).slice(0, 50);
    const xmlFiles = await mapLimit(sitemaps, 6, (url) => fetchText(url, { accept:'application/xml,text/xml' }));
    for (const xml of xmlFiles) if (xml) urls.push(...parseLocs(xml));
  } else urls = parseLocs(rootXml);

  const unique = [...new Set(urls.filter((url) => searchable(url, indexUrl.origin, basePath)))].slice(0, maxDocuments);
  const byUrl = new Map(unique.map((url, index) => [url, documentFromUrl(url, basePath, index)]));
  try {
    for (const doc of curatedDocuments(await fetchJson(fallbackUrl), basePath)) {
      if (!doc.url || doc.url === '#') continue;
      const old = byUrl.get(doc.url);
      byUrl.set(doc.url, old ? { ...old, ...doc, seedText:doc.text } : doc);
    }
  } catch (_) { /* sitemap corpus is sufficient */ }
  const documents = [...byUrl.values()];
  documents.forEach((doc, index) => { doc.id ||= `page-${index}`; });
  return { documents, origin:indexUrl.origin, basePath, fingerprint:fingerprint(documents) };
}

function fingerprint(documents) {
  let hash = 2166136261;
  for (const doc of documents) {
    const value = `${doc.url}|${doc.seedText}\n`;
    for (let i = 0; i < value.length; i += 1) {
      hash ^= value.charCodeAt(i); hash = Math.imul(hash, 16777619);
    }
  }
  return `${documents.length}-${(hash >>> 0).toString(16)}`;
}

export function buildSections(documents) {
  const map = new Map();
  for (const doc of documents) {
    const value = doc.sectionKey || doc.section || 'platform';
    const current = map.get(value) || { value, label:doc.section || sectionLabel(value), count:0 };
    current.count += 1; map.set(value, current);
  }
  return [...map.values()].sort((a,b) => b.count - a.count || a.label.localeCompare(b.label, 'ar'));
}

export function matchesFilters(doc, filters = {}) {
  if (filters.section && (doc.sectionKey || doc.section) !== filters.section) return false;
  if (filters.audience && !(Array.isArray(doc.audience) ? doc.audience : ['general']).includes(filters.audience)) return false;
  return true;
}

export function lexicalScore(tokens, normalizedQuery, doc) {
  if (!tokens.length) return 0;
  let textMatches = 0, titleMatches = 0;
  for (const token of tokens) {
    if (doc.normalizedText.includes(token)) textMatches += 1;
    if (doc.normalizedTitle.includes(token)) titleMatches += 1;
  }
  const phrase = normalizedQuery && doc.normalizedText.includes(normalizedQuery) ? 1 : 0;
  return Math.min(1, (textMatches / tokens.length) * .62 + (titleMatches / tokens.length) * .28 + phrase * .10);
}

export function titleScore(tokens, doc) {
  if (!tokens.length) return 0;
  let matches = 0;
  for (const token of tokens) if (doc.normalizedTitle.includes(token)) matches += 1;
  return matches / tokens.length;
}

function stripHtml(source) {
  return decodeEntities(String(source || '').replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(script|style|svg|template|noscript|nav|footer)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
}

function extractMeta(source, key) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const patterns = [
    new RegExp(`<meta[^>]+(?:name|property)=["']${escaped}["'][^>]+content=["']([^"']+)["'][^>]*>`, 'i'),
    new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:name|property)=["']${escaped}["'][^>]*>`, 'i')
  ];
  for (const pattern of patterns) { const match = pattern.exec(source); if (match) return decodeEntities(match[1]).replace(/\s+/g, ' ').trim(); }
  return '';
}

function extractTag(source, pattern) { const match = pattern.exec(source); return match ? stripHtml(match[1]) : ''; }

export async function hydrateDocument(doc, origin, basePath, cache, textLimit = 1800) {
  if (cache.has(doc.url)) return cache.get(doc.url);
  const task = (async () => {
    try {
      const parsed = new URL(doc.url);
      if (parsed.origin !== origin || !parsed.pathname.startsWith(basePath)) return doc;
      const html = await fetchText(doc.url, { timeout:9000, accept:'text/html' });
      const title = extractMeta(html, 'og:title') || extractTag(html, /<title[^>]*>([\s\S]*?)<\/title>/i)
        || extractTag(html, /<h1[^>]*>([\s\S]*?)<\/h1>/i) || doc.title;
      const description = extractMeta(html, 'description') || extractMeta(html, 'og:description');
      const main = /<main\b[^>]*>([\s\S]*?)<\/main>/i.exec(html);
      const visible = stripHtml(main?.[1] || html).slice(0, textLimit);
      const hydrated = { ...doc, title, excerpt:[description, visible].filter(Boolean).join(' — ').slice(0, textLimit), text:`${title}. ${description}. ${visible}` };
      hydrated.normalizedTitle = normalizeArabic(hydrated.title);
      hydrated.normalizedText = normalizeArabic(hydrated.text);
      return hydrated;
    } catch (_) { return doc; }
  })();
  cache.set(doc.url, task);
  return task;
}

export async function hydrateCandidates(items, origin, basePath, cache, limit = 28) {
  const selected = items.slice(0, limit);
  const docs = await mapLimit(selected, 5, (item) => hydrateDocument(item.document, origin, basePath, cache));
  return selected.map((item, index) => ({ ...item, document:docs[index] || item.document }));
}

const DB_NAME = 'pterminology-semantic-search';
const STORE = 'vectors';
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function readVectorCache(key) {
  try {
    const db = await openDb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const request = tx.objectStore(STORE).get(key);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  } catch (_) { return null; }
}

export async function writeVectorCache(key, value) {
  try {
    const db = await openDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(value, key);
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
  } catch (_) { /* optional cache */ }
}
