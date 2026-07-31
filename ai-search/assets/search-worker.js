import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.2.0';
import {
  normalizeArabic,
  tokenize,
  discoverDocuments,
  buildSections,
  matchesFilters,
  lexicalScore,
  titleScore,
  hydrateCandidates,
} from './search-core.js';

const MODEL_ID = 'Xenova/multilingual-e5-small';
const MODEL_REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78';
const BUILDER_MODEL_ID = 'intfloat/multilingual-e5-small';
const DTYPE = 'q8';
const DIMENSIONS = 384;
const QUERY_PREFIX = 'query: ';
const PASSAGE_PREFIX = 'passage: ';
const MAX_SEED_CANDIDATES = 96;
const MAX_HYDRATED_CANDIDATES = 36;
const EMBED_BATCH_SIZE = 12;

const QUERY_ALIASES = [
  [['التوحد', 'طيف التوحد'], ['autism', 'autistic', 'spectrum']],
  [['فرط الحركه', 'تشتت الانتباه', 'اضطراب الانتباه'], ['adhd', 'attention', 'hyperactivity']],
  [['متلازمه داون', 'داون'], ['down', 'syndrome']],
  [['القلق', 'الخوف', 'الهلع'], ['anxiety', 'fear', 'panic']],
  [['الاكتئاب'], ['depression', 'depressive']],
  [['الوسواس القهري', 'الوسواس'], ['ocd', 'obsessive', 'compulsive']],
  [['ثنائي القطب', 'الهوس'], ['bipolar', 'mania']],
  [['الفصام', 'الذهان'], ['schizophrenia', 'psychosis']],
  [['النطق', 'اللغه', 'التواصل'], ['speech', 'language', 'communication']],
  [['السمع', 'الصمم'], ['hearing', 'deafness']],
  [['البصر', 'العمى'], ['visual', 'blindness']],
  [['الاعاقه الفكريه', 'القدرات الفكريه'], ['intellectual', 'disability']],
  [['صعوبات التعلم', 'عسر القراءه'], ['learning', 'dyslexia']],
  [['الشلل الدماغي'], ['cerebral', 'palsy']],
  [['المعالجه الحسيه', 'الحساسيه الحسيه', 'الحواس'], ['sensory', 'processing']],
  [['النوم', 'الارق'], ['sleep', 'insomnia']],
  [['الصدمه', 'اضطراب ما بعد الصدمه'], ['trauma', 'ptsd']],
  [['اضطرابات الاكل', 'فقدان الشهيه'], ['eating', 'anorexia']],
  [['ايذاء النفس', 'الانتحار'], ['self', 'harm', 'suicide']],
  [['الادمان', 'المواد'], ['addiction', 'substance']],
  [['الاسره', 'الوالدين', 'الاهل'], ['family', 'parent', 'caregiver']],
  [['المدرسه', 'التعليم', 'الدمج'], ['school', 'education', 'inclusion']],
  [['التقنيات المساعده'], ['assistive', 'technology']],
  [['العلاج الوظيفي'], ['occupational', 'therapy']],
  [['العلاج الطبيعي'], ['physical', 'therapy']],
  [['السلوك', 'الاضطرابات السلوكيه'], ['behavior', 'behavioral', 'emotional']],
  [['التاخر النمائي', 'النمو'], ['developmental', 'delay']],
  [['المتلازمات الوراثيه', 'وراثي'], ['genetic', 'syndrome']],
  [['اصابه الدماغ', 'الذاكره', 'الوظائف التنفيذيه'], ['brain', 'injury', 'memory', 'executive']],
  [['التوتر', 'الضغط النفسي'], ['stress']],
  [['القلق الاجتماعي', 'الرهاب الاجتماعي'], ['social', 'anxiety']],
];

const pageCache = new Map();
const vectorCache = new Map();
let documents = [];
let origin = '';
let basePath = '/';
let extractorPromise = null;
let generatedIndex = null;
let indexMode = 'local-rerank';

function postProgress(message) {
  self.postMessage({ type: 'index-progress', message });
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function fetchBinary(url) {
  const response = await fetch(url, { cache: 'force-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.arrayBuffer();
}

function decodeBase64ToArrayBuffer(value) {
  const binary = atob(String(value || ''));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes.buffer;
}

async function fetchShardVectorBuffer(shard, manifestUrl) {
  if (shard.embeddingsJson) {
    const payload = await fetchJson(new URL(shard.embeddingsJson, manifestUrl));
    if (payload?.version !== 1 || payload?.encoding !== 'base64') {
      throw new Error('ترميز متجهات الفهرس غير مدعوم.');
    }
    if (payload.dtype !== 'float16' || payload.endianness !== 'little') {
      throw new Error('نوع متجهات الفهرس غير متوافق.');
    }
    if (payload.dimensions !== DIMENSIONS || payload.count !== shard.count) {
      throw new Error('أبعاد حزمة المتجهات غير متطابقة.');
    }
    const buffer = decodeBase64ToArrayBuffer(payload.data);
    if (buffer.byteLength !== payload.byteLength || buffer.byteLength !== shard.embeddingBytes) {
      throw new Error('حجم حزمة المتجهات غير صحيح.');
    }
    return buffer;
  }
  return fetchBinary(new URL(shard.embeddings, manifestUrl));
}

function halfToFloat(value) {
  const sign = value & 0x8000 ? -1 : 1;
  const exponent = (value >> 10) & 0x1f;
  const fraction = value & 0x03ff;
  if (exponent === 0) return sign * (2 ** -14) * (fraction / 1024);
  if (exponent === 31) return fraction ? Number.NaN : sign * Number.POSITIVE_INFINITY;
  return sign * (2 ** (exponent - 15)) * (1 + fraction / 1024);
}

function dotHalf(queryVector, halfVector, offset) {
  let score = 0;
  for (let index = 0; index < DIMENSIONS; index += 1) {
    score += queryVector[index] * halfToFloat(halfVector[offset + index]);
  }
  return score;
}

function dotFloat(left, right, offset = 0) {
  let score = 0;
  for (let index = 0; index < DIMENSIONS; index += 1) score += left[index] * right[offset + index];
  return score;
}

function normalizeSemanticScore(rawScore) {
  return Math.max(0, Math.min(1, (rawScore - 0.5) / 0.5));
}

async function loadGeneratedIndex(manifestUrl) {
  const manifest = await fetchJson(manifestUrl);
  if (!manifest?.ready || !Array.isArray(manifest.shards) || !manifest.shards.length) return false;
  if (manifest.version < 2) throw new Error('نسخة الفهرس المسبق قديمة.');
  if (manifest.dimensions !== DIMENSIONS) throw new Error('أبعاد الفهرس المسبق غير متوافقة.');
  if (manifest.model !== BUILDER_MODEL_ID) throw new Error('نموذج بناء الفهرس غير متوافق.');
  if (manifest.browserModel !== MODEL_ID) throw new Error('نموذج المتصفح غير متوافق.');
  if (manifest.browserModelRevision !== MODEL_REVISION) throw new Error('مراجعة نموذج المتصفح غير متوافقة.');
  if (manifest.queryPrefix !== QUERY_PREFIX || manifest.passagePrefix !== PASSAGE_PREFIX) {
    throw new Error('بادئات E5 في الفهرس غير متوافقة.');
  }
  if (manifest.normalized !== true || manifest.dtype !== 'float16') {
    throw new Error('تنسيق متجهات الفهرس غير متوافق.');
  }

  const loadedDocuments = [];
  const loadedShards = [];
  let globalOffset = 0;

  for (let shardIndex = 0; shardIndex < manifest.shards.length; shardIndex += 1) {
    const shard = manifest.shards[shardIndex];
    postProgress(`تحميل جزء الفهرس ${shardIndex + 1} من ${manifest.shards.length}…`);
    const [metadata, buffer] = await Promise.all([
      fetchJson(new URL(shard.metadata, manifestUrl)),
      fetchShardVectorBuffer(shard, manifestUrl),
    ]);
    if (!Array.isArray(metadata) || metadata.length !== shard.count) throw new Error('بيانات الفهرس غير متطابقة.');
    for (const document of metadata) {
      document.normalizedTitle = normalizeArabic(document.title);
      document.normalizedText = normalizeArabic(`${document.title || ''} ${document.section || ''} ${document.text || ''}`);
      loadedDocuments.push(document);
    }
    const vectors = new Uint16Array(buffer);
    if (vectors.length !== shard.count * DIMENSIONS) throw new Error('حجم متجهات الفهرس غير صحيح.');
    loadedShards.push({ start: globalOffset, count: shard.count, vectors });
    globalOffset += shard.count;
  }

  documents = loadedDocuments;
  generatedIndex = { shards: loadedShards };
  indexMode = 'generated';
  return true;
}

async function initialize(message) {
  try {
    postProgress('فحص الفهرس الدلالي المسبق…');
    let loaded = false;
    try {
      loaded = await loadGeneratedIndex(message.manifestUrl);
    } catch (_) {
      loaded = false;
    }

    if (!loaded) {
      const discovered = await discoverDocuments(message.sitemapIndexUrl, message.fallbackUrl, postProgress);
      ({ documents, origin, basePath } = discovered);
      indexMode = 'local-rerank';
    }

    self.postMessage({
      type: 'ready',
      semanticAvailable: documents.length > 0,
      indexMode,
      chunkCount: documents.length,
      sections: buildSections(documents),
      model: MODEL_ID,
    });
  } catch (error) {
    self.postMessage({ type: 'error', message: `تعذر تجهيز البحث: ${error.message}` });
  }
}

async function createExtractor(requestId) {
  const progressCallback = (item) => self.postMessage({
    type: 'model-progress',
    requestId,
    progress: Math.max(0, Math.min(100, Number(item?.progress) || 0)),
    message: item?.file ? `تحميل النموذج: ${item.file}` : 'تحميل نموذج فهم اللغة لأول مرة…',
  });

  if (self.navigator?.gpu) {
    try {
      return await pipeline('feature-extraction', MODEL_ID, {
        dtype: DTYPE,
        device: 'webgpu',
        revision: MODEL_REVISION,
        progress_callback: progressCallback,
      });
    } catch (_) {
      // Fall through to portable WASM.
    }
  }

  return pipeline('feature-extraction', MODEL_ID, {
    dtype: DTYPE,
    revision: MODEL_REVISION,
    progress_callback: progressCallback,
  });
}

async function getExtractor(requestId) {
  if (!extractorPromise) extractorPromise = createExtractor(requestId);
  return extractorPromise;
}

async function embedTexts(texts, prefix, requestId) {
  const model = await getExtractor(requestId);
  const allVectors = new Float32Array(texts.length * DIMENSIONS);

  for (let start = 0; start < texts.length; start += EMBED_BATCH_SIZE) {
    const batch = texts.slice(start, start + EMBED_BATCH_SIZE)
      .map((text) => `${prefix}${String(text || '').slice(0, 1400)}`);
    const output = await model(batch, { pooling: 'mean', normalize: true });
    const data = output.data instanceof Float32Array ? output.data : Float32Array.from(output.data);
    if (data.length !== batch.length * DIMENSIONS) throw new Error('أبعاد النموذج غير متوقعة.');
    allVectors.set(data, start * DIMENSIONS);
  }

  return allVectors;
}

async function embedQuery(query, requestId) {
  return (await embedTexts([query], QUERY_PREFIX, requestId)).slice(0, DIMENSIONS);
}

function textSignature(document) {
  const value = `${document.url}|${String(document.text || document.seedText || '').slice(0, 1600)}`;
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `${document.url}|${(hash >>> 0).toString(16)}`;
}

async function embedDocuments(candidateDocuments, requestId) {
  const output = new Float32Array(candidateDocuments.length * DIMENSIONS);
  const missing = [];

  candidateDocuments.forEach((document, index) => {
    const signature = textSignature(document);
    const cached = vectorCache.get(signature);
    if (cached) output.set(cached, index * DIMENSIONS);
    else missing.push({ document, index, signature });
  });

  if (missing.length) {
    const vectors = await embedTexts(
      missing.map(({ document }) => document.text || document.seedText || document.title),
      PASSAGE_PREFIX,
      requestId,
    );
    missing.forEach((item, position) => {
      const vector = vectors.slice(position * DIMENSIONS, (position + 1) * DIMENSIONS);
      output.set(vector, item.index * DIMENSIONS);
      vectorCache.set(item.signature, vector);
    });
    while (vectorCache.size > 256) vectorCache.delete(vectorCache.keys().next().value);
  }

  return output;
}

function expandedQueryTokens(query) {
  const normalized = normalizeArabic(query);
  const result = new Set(tokenize(query));
  for (const [phrases, aliases] of QUERY_ALIASES) {
    if (phrases.some((phrase) => normalized.includes(normalizeArabic(phrase)))) {
      aliases.forEach((alias) => result.add(alias));
    }
  }
  return [...result];
}

function rankLexically(queryTokens, normalizedQuery, filters) {
  const ranked = [];
  for (const document of documents) {
    if (!matchesFilters(document, filters)) continue;
    const lexical = lexicalScore(queryTokens, normalizedQuery, document);
    const title = titleScore(queryTokens, document);
    const score = (lexical * 0.78) + (title * 0.22);
    if (score > 0.003) ranked.push({ document, lexical, title, score });
  }
  return ranked.sort((left, right) => right.score - left.score);
}

function candidatePool(queryTokens, normalizedQuery, filters) {
  const ranked = rankLexically(queryTokens, normalizedQuery, filters);
  const selected = [];
  const seen = new Set();

  const add = (item) => {
    if (!item?.document?.url || seen.has(item.document.url) || selected.length >= MAX_SEED_CANDIDATES) return;
    seen.add(item.document.url);
    selected.push(item);
  };

  ranked.slice(0, MAX_SEED_CANDIDATES).forEach(add);

  if (selected.length < MAX_SEED_CANDIDATES) {
    const sectionCounts = new Map();
    const fillers = documents
      .filter((document) => matchesFilters(document, filters))
      .sort((left, right) => {
        const leftDepth = new URL(left.url).pathname.split('/').filter(Boolean).length;
        const rightDepth = new URL(right.url).pathname.split('/').filter(Boolean).length;
        return leftDepth - rightDepth || left.url.localeCompare(right.url);
      });

    for (const document of fillers) {
      const section = document.sectionKey || document.section || 'platform';
      const count = sectionCounts.get(section) || 0;
      if (count >= 8) continue;
      sectionCounts.set(section, count + 1);
      add({ document, lexical: 0, title: 0, score: 0 });
      if (selected.length >= MAX_SEED_CANDIDATES) break;
    }
  }

  return selected;
}

async function searchGenerated(message, query, queryTokens, normalizedQuery) {
  let semanticScores = null;
  if (message.semantic) {
    const queryVector = await embedQuery(query, message.requestId);
    semanticScores = new Float32Array(documents.length);
    for (const shard of generatedIndex.shards) {
      for (let index = 0; index < shard.count; index += 1) {
        semanticScores[shard.start + index] = dotHalf(queryVector, shard.vectors, index * DIMENSIONS);
      }
    }
  }

  const ranked = [];
  for (let index = 0; index < documents.length; index += 1) {
    const document = documents[index];
    if (!matchesFilters(document, message.filters)) continue;
    const lexical = lexicalScore(queryTokens, normalizedQuery, document);
    const title = titleScore(queryTokens, document);
    const score = semanticScores
      ? (normalizeSemanticScore(semanticScores[index]) * 0.67) + (lexical * 0.23) + (title * 0.10)
      : (lexical * 0.78) + (title * 0.22);
    if (score > 0.01) ranked.push({ document, score });
  }

  ranked.sort((left, right) => right.score - left.score);
  return { ranked, resultMode: semanticScores ? 'semantic' : 'lexical' };
}

async function searchLocal(message, query, queryTokens, normalizedQuery) {
  if (!message.semantic) {
    const initial = rankLexically(queryTokens, normalizedQuery, message.filters);
    const hydrated = await hydrateCandidates(initial, origin, basePath, pageCache, MAX_HYDRATED_CANDIDATES);
    for (const item of hydrated) {
      item.score = (lexicalScore(queryTokens, normalizedQuery, item.document) * 0.78)
        + (titleScore(queryTokens, item.document) * 0.22);
    }
    hydrated.sort((left, right) => right.score - left.score);
    return { ranked: hydrated, resultMode: 'lexical' };
  }

  const pool = candidatePool(queryTokens, normalizedQuery, message.filters);
  if (!pool.length) return { ranked: [], resultMode: 'semantic' };

  const queryVector = await embedQuery(query, message.requestId);
  postProgress(`ترتيب ${pool.length.toLocaleString('ar')} مرشحًا دلاليًا…`);
  const seedVectors = await embedDocuments(pool.map((item) => item.document), message.requestId);

  for (let index = 0; index < pool.length; index += 1) {
    const item = pool[index];
    const semantic = normalizeSemanticScore(dotFloat(queryVector, seedVectors, index * DIMENSIONS));
    item.seedSemantic = semantic;
    item.score = (semantic * 0.74) + (item.lexical * 0.18) + (item.title * 0.08);
  }
  pool.sort((left, right) => right.score - left.score);

  postProgress(`جلب محتوى أفضل ${MAX_HYDRATED_CANDIDATES.toLocaleString('ar')} صفحة للتحقق النهائي…`);
  const hydrated = await hydrateCandidates(pool, origin, basePath, pageCache, MAX_HYDRATED_CANDIDATES);
  const detailVectors = await embedDocuments(hydrated.map((item) => item.document), message.requestId);

  for (let index = 0; index < hydrated.length; index += 1) {
    const item = hydrated[index];
    const preciseSemantic = normalizeSemanticScore(dotFloat(queryVector, detailVectors, index * DIMENSIONS));
    const lexical = lexicalScore(queryTokens, normalizedQuery, item.document);
    const title = titleScore(queryTokens, item.document);
    item.score = (preciseSemantic * 0.64) + ((item.seedSemantic || 0) * 0.20) + (lexical * 0.11) + (title * 0.05);
  }
  hydrated.sort((left, right) => right.score - left.score);
  return { ranked: hydrated, resultMode: 'semantic' };
}

function dedupeRankedByUrl(ranked) {
  const bestByUrl = new Map();
  for (const item of ranked) {
    const url = item?.document?.url;
    if (!url) continue;
    const previous = bestByUrl.get(url);
    if (!previous || item.score > previous.score) bestByUrl.set(url, item);
  }
  return [...bestByUrl.values()].sort((left, right) => right.score - left.score);
}

function compactResult(item) {
  const document = item.document;
  return {
    id: document.id,
    title: document.title,
    section: document.section,
    url: document.url,
    heading: document.heading,
    excerpt: document.excerpt || String(document.text || '').slice(0, 360),
    audience: document.audience,
    score: Math.max(0, Math.min(1, item.score)),
  };
}

async function search(message) {
  const query = String(message.query || '').trim().slice(0, 300);
  if (!query) {
    self.postMessage({ type: 'results', requestId: message.requestId, mode: 'lexical', results: [] });
    return;
  }

  const normalizedQuery = normalizeArabic(query);
  const queryTokens = expandedQueryTokens(query);
  let outcome;

  try {
    outcome = indexMode === 'generated'
      ? await searchGenerated(message, query, queryTokens, normalizedQuery)
      : await searchLocal(message, query, queryTokens, normalizedQuery);
  } catch (error) {
    self.postMessage({
      type: 'warning',
      requestId: message.requestId,
      message: `تعذر البحث الدلالي (${error.message})؛ استُخدم البحث النصي.`,
    });
    const lexicalMessage = { ...message, semantic: false };
    outcome = indexMode === 'generated'
      ? await searchGenerated(lexicalMessage, query, queryTokens, normalizedQuery)
      : await searchLocal(lexicalMessage, query, queryTokens, normalizedQuery);
  }

  const limit = Math.max(1, Math.min(30, Number(message.limit) || 12));
  const uniqueRanked = dedupeRankedByUrl(outcome.ranked.filter((item) => item.score > 0.01));
  self.postMessage({
    type: 'results',
    requestId: message.requestId,
    mode: outcome.resultMode,
    results: uniqueRanked.slice(0, limit).map(compactResult),
  });
}

self.addEventListener('message', (event) => {
  const message = event.data || {};
  if (message.type === 'initialize') initialize(message);
  if (message.type === 'search') {
    search(message).catch((error) => self.postMessage({
      type: 'error',
      requestId: message.requestId,
      message: `تعذر تنفيذ البحث: ${error.message}`,
    }));
  }
});
