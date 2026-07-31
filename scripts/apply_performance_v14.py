from __future__ import annotations

import json
from pathlib import Path

SITE = Path('_site')
BASE = '/'

SW = r'''/* v14 performance-safe service worker */
const CACHE = 'pterminology-v14-performance';
const CORE = [
  '/',
  '/offline.html',
  '/assets/css/marshmallow-v12.css',
  '/assets/js/lab-v12.js'
];
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)));
});
self.addEventListener('activate', event => {
  event.waitUntil(Promise.all([
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))),
    self.clients.claim()
  ]));
});
async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    return (await cache.match(request)) || (await cache.match('/offline.html'));
  }
}
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const update = fetch(request).then(response => {
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);
  return cached || update || Response.error();
}
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const isNavigation = request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html');
  event.respondWith(isNavigation ? networkFirst(request) : staleWhileRevalidate(request));
});
'''

OFFLINE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>غير متصل | مصطلحات علم النفس</title><style>body{font-family:system-ui,Tahoma,sans-serif;background:linear-gradient(135deg,#fff4f8,#e7fbf8);color:#173d40;display:grid;place-items:center;min-height:100vh;margin:0;padding:24px}.box{max-width:620px;background:#fff;border:1px solid #d9efec;border-radius:24px;padding:32px;box-shadow:0 18px 55px rgba(45,110,112,.12)}a{color:#087c79}</style></head><body><main class="box"><h1>لا يوجد اتصال بالإنترنت</h1><p>تعذر تحميل الصفحة الجديدة. تحقق من الاتصال ثم أعد المحاولة.</p><p><a href="/">العودة إلى الصفحة الرئيسية</a></p></main></body></html>'''


def main() -> None:
    if not SITE.exists():
        raise SystemExit('_site is missing')
    (SITE / 'sw.js').write_text(SW, encoding='utf-8')
    (SITE / 'offline.html').write_text(OFFLINE, encoding='utf-8')
    css = SITE / 'assets/css/marshmallow-v12.css'
    if css.exists():
        text = css.read_text(encoding='utf-8')
        marker = '/* v14 rendering performance */'
        if marker not in text:
            text += '''\n\n/* v14 rendering performance */\n@supports (content-visibility:auto){\n  .card,.ency-v13__article article,.grid>article{content-visibility:auto;contain-intrinsic-size:1px 420px}\n}\nimg{content-visibility:auto}\n'''
            css.write_text(text, encoding='utf-8')
    report = {'version':'v14-performance','service_worker':'network-first-html','offline_page':True,'old_cache_eviction':True}
    api = SITE / 'api'; api.mkdir(parents=True, exist_ok=True)
    (api/'performance-v14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
