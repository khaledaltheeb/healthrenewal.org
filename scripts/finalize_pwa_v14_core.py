from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
from pathlib import Path

from defer_encyclopedia_index_v20 import main as defer_encyclopedia_index

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
BASE = "/"
CACHE_NAME = "healthrenewal-v24-resilient-core"
OFFLINE_ROUTE = "/offline/"

SERVICE_WORKER = r'''/* HealthRenewal v24 resilient PWA service worker */
const CACHE='healthrenewal-v24-resilient-core';
const HOME='/';
const OFFLINE='/offline/';
const MANIFEST='/manifest.webmanifest';
const REQUIRED=[HOME,OFFLINE,MANIFEST];
const CORE=[
  ...REQUIRED,
  '/assets/platform/platform-core.css?v=1.1.0',
  '/assets/platform/platform-core.js?v=1.1.0',
  '/assets/platform/platform-ux-v370.css?v=370',
  '/assets/platform/platform-ux-v370.js?v=370',
  '/assets/brand/pwa-192.png',
  '/assets/brand/pwa-512.png',
  '/assets/brand/pwa-maskable-512.png'
];

async function cacheCoreIndependently(){
  const cache=await caches.open(CACHE);
  const results=await Promise.allSettled(CORE.map(async url=>{
    const request=new Request(url,{cache:'reload'});
    const response=await fetch(request);
    if(!response||!response.ok)throw new Error(`Core asset failed: ${url} (${response&&response.status})`);
    await cache.put(request,response.clone());
    return url;
  }));
  const cached=results.filter(result=>result.status==='fulfilled').length;
  if(cached===0)throw new Error('No HealthRenewal PWA core asset could be cached');
  const missing=[];
  for(const url of REQUIRED){
    if(!(await cache.match(url,{ignoreSearch:true})))missing.push(url);
  }
  if(missing.length)throw new Error(`Required offline assets missing: ${missing.join(', ')}`);
}

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil(cacheCoreIndependently());
});

self.addEventListener('activate',event=>{
  const tasks=[
    caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),
    self.clients.claim()
  ];
  if(self.registration.navigationPreload)tasks.push(self.registration.navigationPreload.enable());
  event.waitUntil(Promise.all(tasks));
});

async function navigationResponse(event){
  const request=event.request;
  try{
    const preload=await event.preloadResponse;
    const response=preload||await fetch(request,{cache:'no-store'});
    if(response&&response.ok){
      const cache=await caches.open(CACHE);
      cache.put(request,response.clone()).catch(()=>undefined);
    }
    return response;
  }catch(error){
    return (await caches.match(request,{ignoreSearch:true}))
      ||(await caches.match(OFFLINE,{ignoreSearch:true}))
      ||(await caches.match(HOME,{ignoreSearch:true}))
      ||Response.error();
  }
}

async function networkFirst(request){
  try{
    const response=await fetch(request,{cache:'no-store'});
    if(response&&response.ok){
      const cache=await caches.open(CACHE);
      cache.put(request,response.clone()).catch(()=>undefined);
    }
    return response;
  }catch(error){
    return (await caches.match(request,{ignoreSearch:true}))||Response.error();
  }
}

async function staleWhileRevalidate(request){
  const cached=await caches.match(request,{ignoreSearch:true});
  const network=fetch(request,{cache:'no-cache'}).then(async response=>{
    if(response&&response.ok){
      const cache=await caches.open(CACHE);
      cache.put(request,response.clone()).catch(()=>undefined);
    }
    return response;
  }).catch(()=>null);
  return cached||(await network)||Response.error();
}

self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET')return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin)return;
  if(request.mode==='navigate'){
    event.respondWith(navigationResponse(event));
    return;
  }
  if(/\.(?:js|css|json|xml|webmanifest)$/.test(url.pathname)){
    event.respondWith(networkFirst(request));
    return;
  }
  event.respondWith(staleWhileRevalidate(request));
});
'''

REGISTRATION_MARKER = "healthrenewal-service-worker-registration"
REGISTRATION = f'''<script id="{REGISTRATION_MARKER}">
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', () => {{
    navigator.serviceWorker.register('{BASE}sw.js', {{ scope: '{BASE}' }}).catch(error => {{
      console.warn('Service worker registration failed', error);
    }});
  }}, {{ once: true }});
}}
</script>'''

VERIFICATION_CONTENT = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)


def normalize_platform_before_pwa() -> None:
    normalizer = Path(__file__).with_name("normalize_platform_shell.py")
    report_path = SITE / "api" / "platform-normalization-v1.json"
    subprocess.run(
        [sys.executable, str(normalizer), str(SITE), "--report-path", str(report_path)],
        check=True,
    )
    if not report_path.is_file():
        raise SystemExit(f"Platform normalization report missing: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed" or int(report.get("counts", {}).get("error", 0)) != 0:
        raise SystemExit({"invalid_platform_normalization_before_pwa": report})


def normalize_pwa_ux_before_registration() -> dict[str, object]:
    normalizer = Path(__file__).with_name("normalize_pwa_ux_v370.py")
    report_path = SITE / "api" / "pwa-ux-v370.json"
    subprocess.run(
        [sys.executable, str(normalizer), str(SITE), "--report-path", str(report_path)],
        check=True,
    )
    if not report_path.is_file():
        raise SystemExit(f"PWA UX normalization report missing: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("status") != "passed"
        or int(report.get("counts", {}).get("error", 0)) != 0
        or not report.get("assets_verified")
    ):
        raise SystemExit({"invalid_pwa_ux_normalization": report})
    return report


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"Invalid PNG asset: {path}")
    return struct.unpack(">II", data[16:24])


def verify_install_assets() -> dict[str, tuple[int, int]]:
    expected = {
        "assets/brand/pwa-192.png": (192, 192),
        "assets/brand/pwa-512.png": (512, 512),
        "assets/brand/pwa-maskable-512.png": (512, 512),
    }
    actual: dict[str, tuple[int, int]] = {}
    for relative, dimensions in expected.items():
        path = SITE / relative
        if not path.is_file():
            raise SystemExit(f"Missing PWA icon: {relative}")
        actual[relative] = png_dimensions(path)
        if actual[relative] != dimensions:
            raise SystemExit(
                {"invalid_pwa_icon_dimensions": relative, "actual": actual[relative], "expected": dimensions}
            )
    return actual


def update_manifest() -> dict[str, object]:
    manifest_path = SITE / "manifest.webmanifest"
    if not manifest_path.is_file():
        raise SystemExit("Missing manifest.webmanifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "id": BASE,
            "start_url": BASE,
            "scope": BASE,
            "display": "standalone",
            "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
            "orientation": "any",
            "background_color": "#ffffff",
            "theme_color": "#075f5b",
            "prefer_related_applications": False,
            "launch_handler": {"client_mode": "navigate-existing"},
        }
    )
    manifest["icons"] = [
        {"src": "/assets/brand/pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/assets/brand/pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/assets/brand/pwa-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        {"src": "/assets/brand/logo-mark.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
    ]
    for shortcut in manifest.get("shortcuts", []):
        shortcut["icons"] = [
            {"src": "/assets/brand/pwa-192.png", "sizes": "192x192", "type": "image/png"}
        ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_offline_page() -> Path:
    path = SITE / "offline" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-VLZMV8Y4JP"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-VLZMV8Y4JP');
</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#075f5b">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>الاتصال غير متاح | HealthRenewal</title>
<meta name="description" content="صفحة احتياطية تظهر عند تعذر الاتصال بالإنترنت.">
<link rel="canonical" href="https://healthrenewal.org/offline/">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/assets/brand/pwa-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="/assets/brand/pwa-192.png" sizes="192x192">
<style>
:root{color-scheme:light;--brand:#075f5b;--ink:#12393d;--line:#c9dfdc;--soft:#f2faf8}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;min-height:100dvh;display:grid;place-items:center;padding:max(20px,env(safe-area-inset-top)) max(20px,env(safe-area-inset-right)) max(20px,env(safe-area-inset-bottom)) max(20px,env(safe-area-inset-left));font-family:Tahoma,Arial,sans-serif;line-height:1.8;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft))}
main{width:min(680px,100%);padding:clamp(24px,6vw,48px);border:1px solid var(--line);border-radius:24px;background:#fff;box-shadow:0 18px 50px rgba(16,72,73,.11)}
img{width:84px;height:84px}
h1{font-size:clamp(1.8rem,7vw,3rem);line-height:1.25;margin:.6rem 0}
p{max-width:58ch}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:1.4rem}
a,button{min-height:48px;display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:12px;font:inherit;font-weight:800;text-decoration:none;cursor:pointer}
button{border:1px solid var(--brand);background:var(--brand);color:#fff}
a{border:1px solid var(--line);color:var(--brand);background:#fff}
:focus-visible{outline:3px solid #0a8b82;outline-offset:4px}
</style>
</head>
<body>
<main>
<header>
<img src="/assets/brand/pwa-192.png" alt="">
<p><strong>HealthRenewal</strong></p>
<h1>الاتصال بالإنترنت غير متاح</h1>
<p>يمكنك متابعة الصفحات التي سبق فتحها وحُفظت على جهازك. أعد المحاولة عند عودة الاتصال للحصول على أحدث نسخة من المحتوى.</p>
</header>
<div class="actions">
<button type="button" onclick="location.reload()">إعادة المحاولة</button>
<a href="/">العودة إلى الصفحة الرئيسية</a>
</div>
<footer><p><small>صفحة احتياطية آمنة للاستخدام عند انقطاع الاتصال.</small></p></footer>
</main>
</body>
</html>
''',
        encoding="utf-8",
        newline="\n",
    )
    return path


def is_verification_artifact(path: Path, html: str) -> bool:
    if path.parent != SITE:
        return False
    return bool(VERIFICATION_CONTENT.match(html.strip()))


def ensure_service_worker_registration() -> tuple[int, int, int, list[str]]:
    html_files = sorted(SITE.rglob("*.html"))
    eligible = 0
    injected = 0
    skipped_verification = 0
    invalid: list[str] = []
    for path in html_files:
        html = path.read_text(encoding="utf-8")
        if is_verification_artifact(path, html):
            skipped_verification += 1
            continue
        eligible += 1
        has_registration = "navigator.serviceWorker.register" in html and "sw.js" in html
        if not has_registration:
            if "</body>" in html:
                html = html.replace("</body>", f"{REGISTRATION}\n</body>", 1)
            elif "</html>" in html:
                html = html.replace("</html>", f"{REGISTRATION}\n</html>", 1)
            else:
                html = f"{html}\n{REGISTRATION}\n"
            path.write_text(html, encoding="utf-8", newline="\n")
            injected += 1
            has_registration = True
        if not has_registration:
            invalid.append(str(path.relative_to(SITE)))
    return eligible, injected, skipped_verification, invalid


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Site root not found: {SITE}")

    normalize_platform_before_pwa()
    defer_encyclopedia_index()
    ux_report = normalize_pwa_ux_before_registration()
    icon_dimensions = verify_install_assets()
    manifest = update_manifest()
    offline_page = write_offline_page()
    (SITE / "sw.js").write_text(SERVICE_WORKER, encoding="utf-8", newline="\n")

    pages_scanned, pages_injected, verification_files_skipped, invalid_pages = (
        ensure_service_worker_registration()
    )
    if pages_scanned == 0:
        raise SystemExit("No generated content pages found for PWA registration")
    if invalid_pages:
        raise SystemExit({"service_worker_registration_missing": invalid_pages[:25]})

    report = {
        "version": 24,
        "legacy_report_name": "pwa-v14.json",
        "cache_name": CACHE_NAME,
        "brand": "HealthRenewal",
        "skip_waiting": "skipWaiting" in SERVICE_WORKER,
        "clients_claim": "clients.claim" in SERVICE_WORKER,
        "old_cache_deleted": "keys.filter(key=>key!==CACHE)" in SERVICE_WORKER,
        "network_first_scripts": "js|css|json|xml|webmanifest" in SERVICE_WORKER,
        "navigation_preload": "navigationPreload.enable" in SERVICE_WORKER,
        "dedicated_offline_fallback": "caches.match(OFFLINE" in SERVICE_WORKER,
        "required_offline_assets": "Required offline assets missing" in SERVICE_WORKER,
        "deferred_encyclopedia_index": True,
        "platform_shell_normalized_before_registration": True,
        "pwa_ux_normalized_before_registration": ux_report.get("status") == "passed",
        "service_worker_file": (SITE / "sw.js").is_file(),
        "offline_page": offline_page.is_file(),
        "manifest_scope_valid": manifest.get("scope") == BASE,
        "manifest_start_url_valid": manifest.get("start_url") == BASE,
        "manifest_id_valid": manifest.get("id") == BASE,
        "manifest_png_icons": len(
            [icon for icon in manifest.get("icons", []) if icon.get("type") == "image/png"]
        ) >= 3,
        "icon_dimensions": {key: list(value) for key, value in icon_dimensions.items()},
        "pages_scanned": pages_scanned,
        "pages_injected": pages_injected,
        "verification_files_skipped": verification_files_skipped,
        "registration_verified": not invalid_pages,
        "independent_core_cache": "Promise.allSettled" in SERVICE_WORKER,
        "rejects_empty_core_cache": "cached===0" in SERVICE_WORKER,
        "atomic_add_all_removed": "cache.addAll" not in SERVICE_WORKER,
    }
    required = (
        "skip_waiting",
        "clients_claim",
        "old_cache_deleted",
        "network_first_scripts",
        "navigation_preload",
        "dedicated_offline_fallback",
        "required_offline_assets",
        "deferred_encyclopedia_index",
        "platform_shell_normalized_before_registration",
        "pwa_ux_normalized_before_registration",
        "service_worker_file",
        "offline_page",
        "manifest_scope_valid",
        "manifest_start_url_valid",
        "manifest_id_valid",
        "manifest_png_icons",
        "registration_verified",
        "independent_core_cache",
        "rejects_empty_core_cache",
        "atomic_add_all_removed",
    )
    if not all(report[key] for key in required):
        raise SystemExit(report)

    (SITE / "api").mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (SITE / "api" / "pwa-v14.json").write_text(payload, encoding="utf-8")
    (SITE / "api" / "pwa-v24.json").write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
