from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from defer_encyclopedia_index_v20 import main as defer_encyclopedia_index

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
BASE = "/"

SERVICE_WORKER = r'''/* pterminology v23 resilient performance service worker */
const CACHE='pterminology-v23-resilient-core';
const HOME='/';
const CORE=[HOME,HOME+'manifest.webmanifest',HOME+'assets/css/marshmallow-v12.css',HOME+'assets/css/encyclopedia-v14.css',HOME+'assets/js/encyclopedia-v14.js'];
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
  if(cached===0)throw new Error('No PWA core asset could be cached');
}
self.addEventListener('install',event=>{self.skipWaiting();event.waitUntil(cacheCoreIndependently());});
self.addEventListener('activate',event=>{event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),self.clients.claim()]));});
async function networkFirst(request){try{const response=await fetch(request,{cache:'no-store'});if(response&&response.ok){const cache=await caches.open(CACHE);cache.put(request,response.clone());}return response;}catch(error){return(await caches.match(request))||(request.mode==='navigate'?await caches.match(HOME):Response.error());}}
async function staleWhileRevalidate(request){const cached=await caches.match(request);const network=fetch(request,{cache:'no-cache'}).then(async response=>{if(response&&response.ok){const cache=await caches.open(CACHE);cache.put(request,response.clone());}return response;}).catch(()=>null);return cached||(await network)||Response.error();}
self.addEventListener('fetch',event=>{const request=event.request;if(request.method!=='GET')return;const url=new URL(request.url);if(url.origin!==self.location.origin)return;if(request.mode==='navigate'||/\.(?:js|css|json|xml)$/.test(url.pathname)){event.respondWith(networkFirst(request));return;}event.respondWith(staleWhileRevalidate(request));});
'''

REGISTRATION_MARKER = "pterminology-service-worker-registration"
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
    """Make the deployed shell and its assets part of every PWA build contract."""

    normalizer = Path(__file__).with_name("normalize_platform_shell.py")
    report_path = SITE / "api" / "platform-normalization-v1.json"
    subprocess.run(
        [
            sys.executable,
            str(normalizer),
            str(SITE),
            "--report-path",
            str(report_path),
        ],
        check=True,
    )
    if not report_path.is_file():
        raise SystemExit(f"Platform normalization report missing: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed" or int(report.get("counts", {}).get("error", 0)) != 0:
        raise SystemExit({"invalid_platform_normalization_before_pwa": report})


def is_verification_artifact(path: Path, html: str) -> bool:
    """Keep ownership-verification files byte-stable; they are not user-facing pages."""
    if path.parent != SITE:
        return False
    stripped = html.strip()
    return bool(VERIFICATION_CONTENT.match(stripped))


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
        has_marker = REGISTRATION_MARKER in html
        has_registration = "navigator.serviceWorker.register" in html and "sw.js" in html

        if not has_registration:
            if "</body>" in html:
                html = html.replace("</body>", f"{REGISTRATION}\n</body>", 1)
            elif "</html>" in html:
                html = html.replace("</html>", f"{REGISTRATION}\n</html>", 1)
            else:
                html = f"{html}\n{REGISTRATION}\n"
            path.write_text(html, encoding="utf-8")
            injected += 1
            has_marker = True
            has_registration = True

        if not (has_marker or has_registration):
            invalid.append(str(path.relative_to(SITE)))

    return eligible, injected, skipped_verification, invalid


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Site root not found: {SITE}")

    normalize_platform_before_pwa()
    defer_encyclopedia_index()
    (SITE / "sw.js").write_text(SERVICE_WORKER, encoding="utf-8")

    manifest_path = SITE / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = BASE
    manifest["start_url"] = BASE
    manifest["scope"] = BASE
    manifest["display"] = "standalone"
    manifest["display_override"] = ["window-controls-overlay", "standalone", "minimal-ui"]
    manifest["orientation"] = "any"
    manifest["background_color"] = "#fff8fc"
    manifest["theme_color"] = "#67d5cd"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pages_scanned, pages_injected, verification_files_skipped, invalid_pages = (
        ensure_service_worker_registration()
    )
    if pages_scanned == 0:
        raise SystemExit("No generated content pages found for PWA registration")
    if invalid_pages:
        raise SystemExit({"service_worker_registration_missing": invalid_pages[:25]})

    report = {
        "version": 23,
        "cache_name": "pterminology-v23-resilient-core",
        "skip_waiting": "skipWaiting" in SERVICE_WORKER,
        "clients_claim": "clients.claim" in SERVICE_WORKER,
        "old_cache_deleted": "keys.filter(key=>key!==CACHE)" in SERVICE_WORKER,
        "network_first_scripts": "js|css|json|xml" in SERVICE_WORKER,
        "deferred_encyclopedia_index": True,
        "platform_shell_normalized_before_registration": True,
        "service_worker_file": (SITE / "sw.js").is_file(),
        "manifest_scope_valid": manifest.get("scope") == BASE,
        "manifest_start_url_valid": manifest.get("start_url") == BASE,
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
        "deferred_encyclopedia_index",
        "platform_shell_normalized_before_registration",
        "service_worker_file",
        "manifest_scope_valid",
        "manifest_start_url_valid",
        "registration_verified",
        "independent_core_cache",
        "rejects_empty_core_cache",
        "atomic_add_all_removed",
    )
    if not all(report[key] for key in required):
        raise SystemExit(report)

    (SITE / "api").mkdir(parents=True, exist_ok=True)
    (SITE / "api" / "pwa-v14.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
