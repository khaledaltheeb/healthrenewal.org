import { chromium } from 'playwright-core';

const chromePath = process.env.CHROME_BIN;
if (!chromePath) throw new Error('CHROME_BIN is required');

const wasmRequests = [];
const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

try {
  const page = await browser.newPage();
  page.on('console', (message) => console.log(`[browser:${message.type()}] ${message.text()}`));
  page.on('pageerror', (error) => console.error(`[browser:error] ${error.stack || error}`));
  page.on('request', (request) => {
    if (/\.wasm(?:\?|$)/i.test(request.url())) wasmRequests.push(request.url());
  });

  await page.setContent(`<!doctype html>
  <html lang="ar" dir="rtl"><meta charset="utf-8"><body><pre id="status">starting</pre>
  <script type="module">
  const MODEL = 'Xenova/multilingual-e5-small';
  const REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78';
  const DIMENSIONS = 384;
  const status = document.querySelector('#status');
  const dot = (left, right) => left.reduce((sum, value, index) => sum + value * right[index], 0);
  try {
    const { env, pipeline } = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.2.0');
    env.allowLocalModels = false;
    const extractor = await pipeline('feature-extraction', MODEL, { revision: REVISION, dtype: 'q8' });
    const output = await extractor([
      'query: طرق دعم اضطراب طيف التوحد',
      'passage: تشمل خطط دعم اضطراب طيف التوحد التواصل الواضح والتدخل المبكر ودعم الأسرة.',
      'passage: تتغير درجات الحرارة بين الفصول وتختلف كميات الأمطار من منطقة إلى أخرى.',
    ], { pooling: 'mean', normalize: true });
    const rows = output.tolist();
    if (rows.length !== 3 || rows.some((row) => row.length !== DIMENSIONS)) throw new Error('Unexpected embedding shape');
    for (const row of rows) {
      const norm = Math.sqrt(dot(row, row));
      if (Math.abs(norm - 1) > 0.015) throw new Error('Embedding is not normalized: ' + norm);
    }
    const relevant = dot(rows[0], rows[1]);
    const unrelated = dot(rows[0], rows[2]);
    if (!(relevant > unrelated)) throw new Error('Semantic ordering failed');
    window.__e5Smoke = { done: true, ok: true, model: MODEL, revision: REVISION, dimensions: DIMENSIONS, relevant, unrelated };
  } catch (error) {
    window.__e5Smoke = { done: true, ok: false, error: String(error?.stack || error) };
  }
  status.textContent = JSON.stringify(window.__e5Smoke);
  </script></body></html>`, { waitUntil: 'domcontentloaded' });

  await page.waitForFunction(() => globalThis.__e5Smoke?.done === true, null, { timeout: 300000 });
  const report = await page.evaluate(() => globalThis.__e5Smoke);
  if (!report?.ok) throw new Error(`Browser E5 failed: ${report?.error || 'unknown error'}`);
  if (report.dimensions !== 384) throw new Error(`Unexpected browser dimensions: ${report.dimensions}`);
  if (!(report.relevant > report.unrelated)) throw new Error(`Browser semantic ordering failed: ${JSON.stringify(report)}`);
  if (wasmRequests.length === 0) throw new Error('No WASM runtime request was observed in Chromium');

  console.log(JSON.stringify({
    runtime: 'chromium-wasm',
    ...report,
    wasmRequestCount: wasmRequests.length,
    wasmRequest: wasmRequests[0],
  }));
} finally {
  await browser.close();
}
