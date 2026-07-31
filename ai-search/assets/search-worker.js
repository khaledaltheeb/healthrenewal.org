import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.0.1';

const MODEL_ID = 'Xenova/multilingual-e5-small';
const MODEL_DTYPE = 'q8';
const QUERY_PREFIX = 'query: ';
const ARABIC_DIACRITICS = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;
const NON_WORD = /[^\p{L}\p{N}]+/gu;
const STOP_WORDS = new Set([
  'في', 'من', 'على', 'إلى', 'الى', 'عن', 'ما', 'ماذا', 'كيف', 'هل', 'هو', 'هي', 'هذا', 'هذه',
  'ذلك', 'تلك', 'مع', 'او', 'أو', 'ثم', 'و', 'يا', 'لدى', 'عند', 'بعد', 'قبل', 'كل', 'أي', 'اي',
  'the', 'a', 'an', 'of', 'to', 'and', 'or', 'for', 'in', 'on', 'with', 'is', 'are',
]);

let manifest = null;
let documents = [];
let vectorShards = [];
let extractorPromise = null;
let semanticAvailable = false;

function normalizeArabic(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKC')
    .replace(ARABIC_DIACRITICS, '')
    .replace(/[إأآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ؤ/g, 'و')
    .replace(/ئ/g, 'ي')
    .replace(/ـ/g, '')
    .replace(NON_WORD, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokenize(value) {
  return normalizeArabic(value)
    .split(' ')
    .filter((token) => token.length > 1 && !STOP_WORDS.has(token));
}

function sectionLabel(path) {
  const labels = {
    encyclopedia: 'الموسوعة النفسية',
    'special-needs': 'ذوو الاحتياجات الخاصة',
    'family-guide': 'دليل الأسرة',
    comparisons: 'المقارنات',
    magazine: 'المجلة والأبحاث',
    library: 'المكتبة',
    'care-guides': 'أدلة التعامل',
    'daily-tools': 'الأدوات اليومية',
    assessments: 'المقاييس والتقييم',
    sectors: 'القطاعات',
    tips: 'النصائح',
    'learning-paths': 'مسارات التعلم',
  };
  return labels[path] || path || 'المنصة';
}

function buildFallbackDocuments(payload) {
  const resources = Array.isArray(payload?.resources) ? payload.resources : [];
  return resources.map((resource, index) => {
    const url = resource.url || '#';
    let section = 'المنصة';
    try {
      const segments = new URL(url).pathname.split('/').filter(Boolean);
      section = sectionLabel(segments[1] || segments[0]);
    } catch (_) {
      section = 'المنصة';
    }

    const tags = Array.isArray(resource.tags) ? resource.tags : [];
    const text = [resource.title, tags.join(' '), resource.type, resource.sourcePolicy].filter(Boolean).join('. ');
    return {
      id: resource.id || `fallback-${index}`,
      title: resource.title || 'مورد من المنصة',
      section,
      sectionKey: section,
      audience: ['general'],
      url,
      excerpt: text,
      text,
      normalizedTitle: normalizeArabic(resource.title),
      normalizedText: normalizeArabic(text),
    };
  });
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status} while fetching ${url}`);
  return response.json();
}

async function fetchBinary(url) {
  const response = await fetch(url, { cache: 'force-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status} while fetching ${url}`);
  return response.arrayBuffer();
}

function resolveRelative(baseUrl, relativeUrl) {
  return new URL(relativeUrl, baseUrl).href;
}

function postIndexProgress(message) {
  self.postMessage({ type: 'index-progress', message });
}

async function loadGeneratedIndex(manifestUrl) {
  manifest = await fetchJson(manifestUrl);
  if (!manifest?.ready || !Array.isArray(manifest.shards) || !manifest.shards.length) return false;

  const loadedDocuments = [];
  const loadedShards = [];
  let globalOffset = 0;

  for (let shardIndex = 0; shardIndex < manifest.shards.length; shardIndex += 1) {
    const shard = manifest.shards[shardIndex];
    postIndexProgress(`تحميل جزء الفهرس ${shardIndex + 1} من ${manifest.shards.length}…`);
    const [metadata, buffer] = await Promise.all([
      fetchJson(resolveRelative(manifestUrl, shard.metadata)),
      fetchBinary(resolveRelative(manifestUrl, shard.embeddings)),
    ]);

    if (!Array.isArray(metadata)) throw new Error(`Invalid metadata shard: ${shard.metadata}`);
    if (metadata.length !== shard.count) throw new Error(`Shard count mismatch: ${shard.metadata}`);

    for (const document of metadata) {
      document.normalizedTitle = normalizeArabic(document.title);
      document.normalizedText = normalizeArabic(`${document.title || ''} ${document.section || ''} ${document.text || ''}`);
      loadedDocuments.push(document);
    }

    const vectors = new Uint16Array(buffer);
    const expected = shard.count * manifest.dimensions;
    if (vectors.length !== expected) throw new Error(`Embedding size mismatch: ${shard.embeddings}`);

    loadedShards.push({
      start: globalOffset,
      count: shard.count,
      vectors,
    });
    globalOffset += shard.count;
  }

  documents = loadedDocuments;
  vectorShards = loadedShards;
  semanticAvailable = documents.length > 0 && vectorShards.length > 0;
  return semanticAvailable;
}

function buildSections() {
  const counts = new Map();
  for (const document of documents) {
    const value = document.sectionKey || document.section || 'المنصة';
    const label = document.section || sectionLabel(value);
    const current = counts.get(value) || { value, label, count: 0 };
    current.count += 1;
    counts.set(value, current);
  }
  return [...counts.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, 'ar'));
}

async function initialize(message) {
  try {
    postIndexProgress('فحص الفهرس الدلالي…');
    let generated = false;
    try {
      generated = await loadGeneratedIndex(message.manifestUrl);
    } catch (error) {
      self.postMessage({ type: 'warning', message: 'تعذر تحميل الفهرس الدلالي الكامل؛ سيُستخدم الفهرس النصي المؤقت.' });
    }

    if (!generated) {
      postIndexProgress('تحميل فهرس الموارد النصي المؤقت…');
      const fallback = await fetchJson(message.fallbackUrl);
      documents = buildFallbackDocuments(fallback);
      vectorShards = [];
      semanticAvailable = false;
    }

    self.postMessage({
      type: 'ready',
      semanticAvailable,
      chunkCount: documents.length,
      sections: buildSections(),
      model: MODEL_ID,
    });
  } catch (error) {
    self.postMessage({ type: 'error', message: `تعذر تجهيز فهرس البحث: ${error.message}` });
  }
}

function lexicalScore(queryTokens, normalizedQuery, document) {
  if (!queryTokens.length) return 0;
  let matches = 0;
  let titleMatches = 0;

  for (const token of queryTokens) {
    if (document.normalizedText.includes(token)) matches += 1;
    if (document.normalizedTitle.includes(token)) titleMatches += 1;
  }

  const coverage = matches / queryTokens.length;
  const titleCoverage = titleMatches / queryTokens.length;
  const phrase = normalizedQuery && document.normalizedText.includes(normalizedQuery) ? 1 : 0;
  return Math.min(1, (coverage * 0.62) + (titleCoverage * 0.28) + (phrase * 0.10));
}

function titleScore(queryTokens, document) {
  if (!queryTokens.length) return 0;
  let matches = 0;
  for (const token of queryTokens) if (document.normalizedTitle.includes(token)) matches += 1;
  return matches / queryTokens.length;
}

function matchesFilters(document, filters = {}) {
  if (filters.section && (document.sectionKey || document.section) !== filters.section) return false;
  if (filters.audience) {
    const audiences = Array.isArray(document.audience) ? document.audience : ['general'];
    if (!audiences.includes(filters.audience)) return false;
  }
  return true;
}

function halfToFloat(value) {
  const sign = (value & 0x8000) ? -1 : 1;
  const exponent = (value >> 10) & 0x1f;
  const fraction = value & 0x03ff;
  if (exponent === 0) return sign * Math.pow(2, -14) * (fraction / 1024);
  if (exponent === 31) return fraction ? NaN : sign * Infinity;
  return sign * Math.pow(2, exponent - 15) * (1 + fraction / 1024);
}

function dotHalf(queryVector, halfVector, offset, dimensions) {
  let score = 0;
  const end = offset + dimensions;
  for (let i = offset, q = 0; i < end; i += 1, q += 1) {
    score += queryVector[q] * halfToFloat(halfVector[i]);
  }
  return score;
}

async function getExtractor(requestId) {
  if (!extractorPromise) {
    extractorPromise = pipeline('feature-extraction', MODEL_ID, {
      dtype: MODEL_DTYPE,
      progress_callback: (progress) => {
        const value = Number.isFinite(progress?.progress) ? progress.progress : 0;
        self.postMessage({
          type: 'model-progress',
          requestId,
          progress: Math.max(0, Math.min(100, value)),
          message: progress?.file
            ? `تحميل النموذج: ${progress.file}`
            : 'تحميل نموذج فهم اللغة لأول مرة…',
        });
      },
    });
  }
  return extractorPromise;
}

async function embedQuery(query, requestId) {
  const extractor = await getExtractor(requestId);
  const output = await extractor(`${QUERY_PREFIX}${query}`, { pooling: 'mean', normalize: true });
  return output.data instanceof Float32Array ? output.data : Float32Array.from(output.data);
}

function semanticScores(queryVector) {
  const scores = new Float32Array(documents.length);
  const dimensions = manifest.dimensions;
  for (const shard of vectorShards) {
    for (let localIndex = 0; localIndex < shard.count; localIndex += 1) {
      const globalIndex = shard.start + localIndex;
      const offset = localIndex * dimensions;
      scores[globalIndex] = dotHalf(queryVector, shard.vectors, offset, dimensions);
    }
  }
  return scores;
}

function normalizeSemanticScore(rawScore) {
  return Math.max(0, Math.min(1, (rawScore - 0.55) / 0.45));
}

function compactResult(document, score) {
  return {
    id: document.id,
    title: document.title,
    section: document.section,
    url: document.url,
    excerpt: document.excerpt || String(document.text || '').slice(0, 320),
    audience: document.audience,
    score: Math.max(0, Math.min(1, score)),
  };
}

async function search(message) {
  const query = String(message.query || '').trim().slice(0, 300);
  if (!query) {
    self.postMessage({ type: 'results', requestId: message.requestId, mode: 'lexical', results: [] });
    return;
  }

  const normalizedQuery = normalizeArabic(query);
  const queryTokens = tokenize(query);
  const useSemantic = Boolean(message.semantic && semanticAvailable);
  let semantic = null;
  let mode = 'lexical';

  if (useSemantic) {
    try {
      const vector = await embedQuery(query, message.requestId);
      semantic = semanticScores(vector);
      mode = 'semantic';
    } catch (error) {
      self.postMessage({
        type: 'warning',
        requestId: message.requestId,
        message: 'تعذر تشغيل النموذج الدلالي على هذا الجهاز؛ استُخدم البحث النصي المحلي.',
      });
      mode = 'lexical';
    }
  }

  const ranked = [];
  for (let index = 0; index < documents.length; index += 1) {
    const document = documents[index];
    if (!matchesFilters(document, message.filters)) continue;

    const lexical = lexicalScore(queryTokens, normalizedQuery, document);
    const title = titleScore(queryTokens, document);
    let score = (lexical * 0.78) + (title * 0.22);

    if (semantic) {
      const semanticNormalized = normalizeSemanticScore(semantic[index]);
      score = (semanticNormalized * 0.67) + (lexical * 0.23) + (title * 0.10);
    }

    if (score > 0.015) ranked.push({ index, score });
  }

  ranked.sort((a, b) => b.score - a.score);
  const limit = Math.max(1, Math.min(30, Number(message.limit) || 12));
  const results = ranked.slice(0, limit).map((item) => compactResult(documents[item.index], item.score));

  self.postMessage({ type: 'results', requestId: message.requestId, mode, results });
}

self.addEventListener('message', (event) => {
  const message = event.data || {};
  if (message.type === 'initialize') initialize(message);
  if (message.type === 'search') search(message).catch((error) => {
    self.postMessage({ type: 'error', requestId: message.requestId, message: `تعذر تنفيذ البحث: ${error.message}` });
  });
});
