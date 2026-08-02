from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")


def main() -> None:
    runtime = (SITE / "assets/js/lab-v12.js").read_text(encoding="utf-8")
    index_runtime = (SITE / "assets/js/encyclopedia-v14.js").read_text(encoding="utf-8")
    service_worker = (SITE / "sw.js").read_text(encoding="utf-8")
    index = (SITE / "encyclopedia/index.html").read_text(encoding="utf-8")
    lab_page = (SITE / "assessment-lab/phq-9-plus/index.html").read_text(encoding="utf-8")

    offenders: list[str] = []
    for folder in (SITE / "encyclopedia", SITE / "hubs"):
        for page in folder.rglob("*.html"):
            if "lab-v12.js" in page.read_text(encoding="utf-8"):
                offenders.append(page.relative_to(SITE).as_posix())
                if len(offenders) >= 20:
                    break

    performance = json.loads((SITE / "api/performance-v14.json").read_text(encoding="utf-8"))
    pwa = json.loads((SITE / "api/pwa-v14.json").read_text(encoding="utf-8"))
    integrity = json.loads((SITE / "api/site-integrity-v13.json").read_text(encoding="utf-8"))
    prerendered_cards = index.count('class="ency-v13__card"')

    accepted_cache_names = (
        "pterminology-v14-performance",
        "pterminology-v15-core-sections",
        "pterminology-v20-global-quality",
        "pterminology-v21-global-quality",
        "pterminology-v23-resilient-core",
        "healthrenewal-v24-resilient-core",
    )
    checks = {
        "mutation_observer_absent": "MutationObserver" not in runtime,
        "computed_style_scan_absent": "getComputedStyle" not in runtime,
        "old_cache_name_absent": "pterminology-v12-direct" not in service_worker,
        "current_cache_name_present": any(name in service_worker for name in accepted_cache_names),
        "skip_waiting_present": "skipWaiting" in service_worker,
        "clients_claim_present": "clients.claim" in service_worker,
        "resilient_core_cache_present": "Promise.allSettled" in service_worker,
        "empty_core_cache_rejected": "cached===0" in service_worker,
        "atomic_add_all_absent": "cache.addAll" not in service_worker,
        "page_size_48_present": "PAGE_SIZE=48" in index_runtime,
        "stable_48_card_prerender": prerendered_cards == 48,
        "static_2000_cards_absent": prerendered_cards < 100,
        "lab_runtime_absent_from_index": "lab-v12.js" not in index,
        "paginated_runtime_present": "encyclopedia-v14.js" in index,
        "full_index_deferred": "setTimeout(()=>ensureLoad().catch(()=>{}),10000)" in index_runtime,
        "url_query_parameter_read": "new URLSearchParams(location.search).get('q')" in index_runtime,
        "url_query_applied_on_load": "if(initialQuery.trim())" in index_runtime and "input.value=initialQuery" in index_runtime,
        "shareable_query_url_synced": "history.replaceState" in index_runtime and "searchParams.set('q',term)" in index_runtime,
        "lab_runtime_present_on_assessment": "lab-v12.js" in lab_page,
        "lab_runtime_absent_from_encyclopedia_and_hubs": not offenders,
        "report_observer_removed": performance.get("mutation_observer_removed") is True,
        "report_style_scan_removed": performance.get("computed_style_scan_removed") is True,
        "report_static_cards_removed": performance.get("no_2000_static_cards") is True,
        "report_stable_initial_render": performance.get("stable_initial_render") is True,
        "report_item_count_2000": performance.get("items") == 2000,
        "report_removed_over_2000_tags": performance.get("total_removed_lab_script_tags", 0) > 2000,
        "report_zero_residual_nonlab_tags": performance.get("residual_lab_script_tags_non_lab") == 0,
        "report_lab_tags_retained": performance.get("kept_lab_script_tags_after_regex", 0) > 0,
        "report_old_caches_deleted": pwa.get("old_cache_deleted") is True,
        "report_deferred_index": pwa.get("deferred_encyclopedia_index") is True,
        "report_registration_verified": pwa.get("registration_verified") is True,
        "report_resilient_core_cache": pwa.get("independent_core_cache") is True,
        "report_empty_core_cache_rejected": pwa.get("rejects_empty_core_cache") is True,
        "report_atomic_add_all_removed": pwa.get("atomic_add_all_removed") is True,
        "integrity_zero_errors": integrity.get("errors") == [] and integrity.get("error_count") == 0,
    }
    failed = [name for name, ok in checks.items() if not ok]
    result = {
        "version": 31,
        "checks": checks,
        "failed_checks": failed,
        "offenders": offenders,
        "prerendered_cards": prerendered_cards,
        "performance": performance,
        "pwa": pwa,
        "integrity": integrity,
    }
    report_path = SITE / "api/performance-verification-v14.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit("Failed performance checks: " + ", ".join(failed))


if __name__ == "__main__":
    main()
