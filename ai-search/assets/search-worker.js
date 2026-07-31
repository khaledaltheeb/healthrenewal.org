import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.2.0';
import {
  normalizeArabic, tokenize, discoverDocuments, buildSections, matchesFilters, lexicalScore, titleScore,
  hydrateCandidates, readVectorCache, writeVectorCache
} from './search-core.js';

const MODEL_ID = 'Xenova/multilingual-e5-small';
const DTYPE = 'q8';
const DIM = 384;
const QUERY_PREFIX = 'query: ';
const PASSAGE_PREFIX = 'passage: ';
const pageCache = new Map();
let documents = [], origin = '', basePath = '/', fingerprint = '';
let localVectors = null, extractorPromise = null, generated = null;
let mode = 'local-sitemap';

function progress(message) { self.postMessage({ type:'index-progress', message }); }
async function fetchJson(url) { const r = await fetch(url, { cache:'no-cache' }); if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
async function fetchBinary(url) { const r = await fetch(url, { cache:'force-cache' }); if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.arrayBuffer(); }

function halfToFloat(value) {
  const sign = value & 0x8000 ? -1 : 1, exponent = value >> 10 & 0x1f, fraction = value & 0x03ff;
  if (exponent === 0) return sign * 2 ** -14 * (fraction / 1024);
  if (exponent === 31) return fraction ? NaN : sign * Infinity;
  return sign * 2 ** (exponent - 15) * (1 + fraction / 1024);
}
function dotHalf(query, data, offset) { let sum = 0; for (let i=0;i<DIM;i++) sum += query[i] * halfToFloat(data[offset+i]); return sum; }
function dotFloat(query, data, offset) { let sum = 0; for (let i=0;i<DIM;i++) sum += query[i] * data[offset+i]; return sum; }
function semanticScore(raw) { return Math.max(0, Math.min(1, (raw - .5) / .5)); }

async function loadGenerated(manifestUrl) {
  const manifest = await fetchJson(manifestUrl);
  if (!manifest?.ready || !manifest.shards?.length || manifest.dimensions !== DIM) return false;
  const docs = [], shards = []; let start = 0;
  for (let i=0;i<manifest.shards.length;i++) {
    progress(`تحميل جزء الفهرس ${i+1} من ${manifest.shards.length}…`);
    const shard = manifest.shards[i];
    const [metadata, buffer] = await Promise.all([
      fetchJson(new URL(shard.metadata, manifestUrl)), fetchBinary(new URL(shard.embeddings, manifestUrl))
    ]);
    if (!Array.isArray(metadata) || metadata.length !== shard.count) throw new Error('فهرس غير متطابق');
    for (const doc of metadata) {
      doc.normalizedTitle = normalizeArabic(doc.title);
      doc.normalizedText = normalizeArabic(`${doc.title || ''} ${doc.section || ''} ${doc.text || ''}`);
      docs.push(doc);
    }
    const vectors = new Uint16Array(buffer);
    if (vectors.length !== shard.count * DIM) throw new Error('حجم متجهات غير صحيح');
    shards.push({ start, count:shard.count, vectors }); start += shard.count;
  }
  documents = docs; generated = { shards }; mode = 'generated';
  return true;
}

async function initialize(message) {
  try {
    progress('فحص الفهرس الدلالي…');
    let ready = false;
    try { ready = await loadGenerated(message.manifestUrl); } catch (_) { /* local fallback */ }
    if (!ready) {
      const discovered = await discoverDocuments(message.sitemapIndexUrl, message.fallbackUrl, progress);
      ({ documents, origin, basePath, fingerprint } = discovered);
      mode = 'local-sitemap';
    }
    self.postMessage({
      type:'ready', semanticAvailable:documents.length > 0, indexMode:mode,
      chunkCount:documents.length, sections:buildSections(documents), model:MODEL_ID
    });
  } catch (error) { self.postMessage({ type:'error', message:`تعذر تجهيز البحث: ${error.message}` }); }
}

async function createExtractor(requestId) {
  const callback = (item) => self.postMessage({
    type:'model-progress', requestId, progress:Math.max(0, Math.min(100, Number(item?.progress) || 0)),
    message:item?.file ? `تحميل النموذج: ${item.file}` : 'تحميل نموذج فهم اللغة لأول مرة…'
  });
  if (self.navigator?.gpu) {
    try { return await pipeline('feature-extraction', MODEL_ID, { dtype:DTYPE, device:'webgpu', progress_callback:callback }); }
    catch (_) { /* use WASM */ }
  }
  return pipeline('feature-extraction', MODEL_ID, { dtype:DTYPE, device:'wasm', progress_callback:callback });
}
async function extractor(requestId) { if (!extractorPromise) extractorPromise = createExtractor(requestId); return extractorPromise; }

async function embed(texts, prefix, requestId) {
  const model = await extractor(requestId);
  const input = texts.map((text) => `${prefix}${String(text || '').slice(0, 1400)}`);
  const output = await model(input, { pooling:'mean', normalize:true });
  const data = output.data instanceof Float32Array ? output.data : Float32Array.from(output.data);
  if (data.length !== input.length * DIM) throw new Error('أبعاد النموذج غير متوقعة');
  return data;
}
async function embedQuery(query, requestId) { return (await embed([query], QUERY_PREFIX, requestId)).slice(0, DIM); }

async function ensureLocalVectors(requestId) {
  if (localVectors?.length === documents.length * DIM) return localVectors;
  const key = `${MODEL_ID}|${fingerprint}|${DIM}`;
  const cached = await readVectorCache(key);
  if (cached?.buffer && cached.count === documents.length && cached.dimensions === DIM) {
    const restored = new Float32Array(cached.buffer);
    if (restored.length === documents.length * DIM) {
      localVectors = restored; progress(`استُعيد الفهرس المحفوظ: ${documents.length.toLocaleString('ar')} صفحة.`); return localVectors;
    }
  }
  localVectors = new Float32Array(documents.length * DIM);
  const batchSize = self.navigator?.gpu ? 80 : 20;
  for (let start=0;start<documents.length;start+=batchSize) {
    const batch = documents.slice(start, start+batchSize);
    localVectors.set(await embed(batch.map((doc) => doc.seedText || doc.text), PASSAGE_PREFIX, requestId), start * DIM);
    progress(`بناء الفهرس المحلي: ${Math.min(start+batch.length, documents.length).toLocaleString('ar')} من ${documents.length.toLocaleString('ar')} صفحة…`);
  }
  await writeVectorCache(key, { count:documents.length, dimensions:DIM, buffer:localVectors.buffer });
  return localVectors;
}

function rankLexical(tokens, normalizedQuery, filters) {
  const result = [];
  for (const doc of documents) {
    if (!matchesFilters(doc, filters)) continue;
    const lexical = lexicalScore(tokens, normalizedQuery, doc), title = titleScore(tokens, doc);
    const score = lexical * .78 + title * .22;
    if (score > .005) result.push({ document:doc, lexical, title, score });
  }
  return result.sort((a,b) => b.score - a.score);
}

async function searchGenerated(message, query, tokens, normalizedQuery) {
  let semantic = null;
  if (message.semantic) {
    const queryVector = await embedQuery(query, message.requestId);
    semantic = new Float32Array(documents.length);
    for (const shard of generated.shards) for (let i=0;i<shard.count;i++) semantic[shard.start+i] = dotHalf(queryVector, shard.vectors, i*DIM);
  }
  const ranked = [];
  for (let i=0;i<documents.length;i++) {
    const doc = documents[i]; if (!matchesFilters(doc, message.filters)) continue;
    const lexical = lexicalScore(tokens, normalizedQuery, doc), title = titleScore(tokens, doc);
    const score = semantic ? semanticScore(semantic[i])*.67 + lexical*.23 + title*.10 : lexical*.78 + title*.22;
    if (score > .01) ranked.push({ document:doc, score });
  }
  ranked.sort((a,b) => b.score-a.score);
  return { ranked, resultMode:semantic ? 'semantic' : 'lexical' };
}

async function searchLocal(message, query, tokens, normalizedQuery) {
  if (!message.semantic) {
    let ranked = await hydrateCandidates(rankLexical(tokens, normalizedQuery, message.filters), origin, basePath, pageCache);
    for (const item of ranked) item.score = lexicalScore(tokens, normalizedQuery, item.document)*.78 + titleScore(tokens, item.document)*.22;
    ranked.sort((a,b) => b.score-a.score); return { ranked, resultMode:'lexical' };
  }
  const queryVector = await embedQuery(query, message.requestId), vectors = await ensureLocalVectors(message.requestId), candidates = [];
  for (let i=0;i<documents.length;i++) {
    const doc = documents[i]; if (!matchesFilters(doc, message.filters)) continue;
    const seed = semanticScore(dotFloat(queryVector, vectors, i*DIM));
    const lexical = lexicalScore(tokens, normalizedQuery, doc), title = titleScore(tokens, doc);
    candidates.push({ document:doc, seed, score:seed*.76 + lexical*.17 + title*.07 });
  }
  candidates.sort((a,b) => b.score-a.score);
  const hydrated = await hydrateCandidates(candidates, origin, basePath, pageCache);
  const detail = await embed(hydrated.map((item) => item.document.text || item.document.seedText), PASSAGE_PREFIX, message.requestId);
  for (let i=0;i<hydrated.length;i++) {
    const item = hydrated[i], precise = semanticScore(dotFloat(queryVector, detail, i*DIM));
    item.score = precise*.62 + item.seed*.23 + lexicalScore(tokens, normalizedQuery, item.document)*.10 + titleScore(tokens, item.document)*.05;
  }
  hydrated.sort((a,b) => b.score-a.score); return { ranked:hydrated, resultMode:'semantic' };
}

function compact(item) {
  const doc = item.document;
  return { id:doc.id, title:doc.title, section:doc.section, url:doc.url, excerpt:doc.excerpt || String(doc.text || '').slice(0,360), audience:doc.audience, score:Math.max(0,Math.min(1,item.score)) };
}

async function search(message) {
  const query = String(message.query || '').trim().slice(0,300);
  if (!query) return self.postMessage({ type:'results', requestId:message.requestId, mode:'lexical', results:[] });
  const tokens = tokenize(query), normalizedQuery = normalizeArabic(query);
  let outcome;
  try { outcome = mode === 'generated' ? await searchGenerated(message, query, tokens, normalizedQuery) : await searchLocal(message, query, tokens, normalizedQuery); }
  catch (error) {
    self.postMessage({ type:'warning', requestId:message.requestId, message:`تعذر البحث الدلالي (${error.message})؛ استُخدم البحث النصي.` });
    outcome = mode === 'generated' ? await searchGenerated({ ...message, semantic:false }, query, tokens, normalizedQuery) : await searchLocal({ ...message, semantic:false }, query, tokens, normalizedQuery);
  }
  const limit = Math.max(1, Math.min(30, Number(message.limit) || 12));
  self.postMessage({ type:'results', requestId:message.requestId, mode:outcome.resultMode, results:outcome.ranked.filter((x) => x.score > .01).slice(0,limit).map(compact) });
}

self.addEventListener('message', (event) => {
  const message = event.data || {};
  if (message.type === 'initialize') initialize(message);
  if (message.type === 'search') search(message).catch((error) => self.postMessage({ type:'error', requestId:message.requestId, message:`تعذر تنفيذ البحث: ${error.message}` }));
});
