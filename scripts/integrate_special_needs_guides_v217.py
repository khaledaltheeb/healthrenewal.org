#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate-all-labs-v22.yml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")

    compile_anchor = "scripts/enforce_platform_identity_v201.py; do python -m py_compile \"$f\"; done"
    compile_replacement = (
        "scripts/enforce_platform_identity_v201.py "
        "scripts/publish_special_needs_guides_v209.py "
        "scripts/publish_special_needs_guides_v209_compat.py "
        "scripts/publish_special_needs_guides_v210.py "
        "scripts/publish_special_needs_guides_v211.py "
        "scripts/publish_special_needs_guides_v212.py "
        "scripts/publish_special_needs_guides_v217.py; do python -m py_compile \"$f\"; done"
    )
    text = replace_once(text, compile_anchor, compile_replacement, "compile list")

    homepage_anchor = "          python scripts/apply_homepage_v20.py _site\n"
    homepage_replacement = (
        homepage_anchor
        + "          python scripts/publish_special_needs_guides_v217.py _site\n"
    )
    text = replace_once(text, homepage_anchor, homepage_replacement, "production publisher")

    health_anchor = "          python scripts/verify_sleep_log_v49.py\n          python scripts/polish_site_v16.py _site\n"
    health_replacement = (
        "          python scripts/verify_sleep_log_v49.py\n"
        "          python scripts/enforce_health_publication_gate_v192.py _site\n"
        "          python scripts/polish_site_v16.py _site\n"
    )
    text = replace_once(text, health_anchor, health_replacement, "health gate rerun")

    identity_anchor = "      - name: Enforce platform identity production contract\n"
    guide_step = '''      - name: Enforce twenty special-needs guide production contract
        run: |
          set -euxo pipefail
          test "$(find _site/special-needs -mindepth 2 -name index.html | wc -l)" -ge 20
          test -f _site/api/special-needs-guides-v217.json
          python - <<'PY'
          import json
          from pathlib import Path
          report=json.loads(Path('_site/api/special-needs-guides-v217.json').read_text(encoding='utf-8'))
          assert report['status']=='passed' and report['production_status']=='integrated',report
          assert report['batch_count']==4 and report['guide_count']==20,report
          assert report['batches']==[209,210,211,212],report
          assert report['minimum_rendered_words']>=700,report
          assert report['minimum_h2']>=9 and report['minimum_citations']>=2,report
          assert report['hub_linked_guides']==20,report
          assert report['professional_limits_visible'] is True,report
          assert report['source_citations_visible'] is True,report
          assert report['inclusive_language_gate'] is True,report
          assert report['unsafe_runtime_detected'] is False,report
          assert report['external_review_completed'] is False,report
          assert all(batch['status']=='production-integrated' and batch['guide_count']==5 for batch in report['batch_reports']),report
          print({'special_needs_guides':'20/20','batches':'4/4','minimum_words':report['minimum_rendered_words'],'sitemap_mode':report['main_sitemap_mode'],'status':'passed'})
          PY

'''
    text = replace_once(text, identity_anchor, guide_step + identity_anchor, "guide production gate")

    final_load_anchor = "          homepage=json.loads(Path('_site/api/homepage-v20.json').read_text())\n"
    final_load_replacement = (
        final_load_anchor
        + "          special_guides=json.loads(Path('_site/api/special-needs-guides-v217.json').read_text())\n"
    )
    text = replace_once(text, final_load_anchor, final_load_replacement, "final report load")

    final_assert_anchor = "          assert homepage['lab_tool_count']==93 and homepage['lab_inventory_metadata_updated'] is True,homepage\n"
    final_assert_replacement = (
        final_assert_anchor
        + "          assert special_guides['status']=='passed' and special_guides['guide_count']==20 and special_guides['hub_linked_guides']==20,special_guides\n"
    )
    text = replace_once(text, final_assert_anchor, final_assert_replacement, "final guide assertion")

    old_print = "'homepage_lab_tools':homepage['lab_tool_count']})"
    new_print = "'homepage_lab_tools':homepage['lab_tool_count'],'special_needs_guides':'20/20'})"
    text = replace_once(text, old_print, new_print, "final summary")

    required = (
        "python scripts/publish_special_needs_guides_v217.py _site",
        "python scripts/enforce_health_publication_gate_v192.py _site",
        "Enforce twenty special-needs guide production contract",
        "special-needs-guides-v217.json",
        "'special_needs_guides':'20/20'",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit(f"Production workflow integration is incomplete: {missing}")
    if text.count("python scripts/publish_special_needs_guides_v217.py _site") != 1:
        raise SystemExit("Special-needs guide publisher must run exactly once")
    if text.count("Enforce twenty special-needs guide production contract") != 1:
        raise SystemExit("Special-needs guide contract step must exist exactly once")

    WORKFLOW.write_text(text, encoding="utf-8")
    print({"workflow": str(WORKFLOW.relative_to(ROOT)), "guides": 20, "batches": 4, "status": "integrated"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
