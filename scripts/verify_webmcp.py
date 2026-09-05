#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "assets" / "brand" / "rawafid-brand.js"
SOURCE = ROOT / "scripts" / "rawafid_brand_runtime.js"
GENERATOR = ROOT / "scripts" / "apply_rawafid_brand.py"


def fail(message: str) -> None:
    print(f"WEBMCP_GUARD_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    for path in (JS, SOURCE, GENERATOR):
        if not path.is_file():
            fail(f"missing {path.relative_to(ROOT)}")

    text = JS.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")

    if text != source:
        fail("deployed WebMCP runtime differs from canonical runtime source")
    if "RUNTIME_SOURCE" not in generator or "rawafid_brand_runtime.js" not in generator:
        fail("brand generator is not pinned to the canonical WebMCP runtime source")

    # Accept direct document.modelContext feature detection or the exact local
    # document alias used by the runtime. This checks the behavior contract
    # without coupling the guard to one equivalent JavaScript spelling.
    direct_model_context = "document.modelContext" in text
    aliased_model_context = "const d=document" in text and "d.modelContext" in text
    if not (direct_model_context or aliased_model_context):
        fail("model context feature detection marker missing")

    required_literals = {
        "imperative registration": "registerTool",
        "declarative form name": "toolname",
        "declarative form description": "tooldescription",
        "declarative parameter description": "toolparamdescription",
        "homepage knowledge search": "rawafid_search_encyclopedia",
        "closed JSON schemas": "additionalProperties:false",
        "safe form annotator": "annotateSafeSearchForms",
        "sensitive password exclusion": 'input[type="password"]',
        "sensitive file exclusion": 'input[type="file"]',
        "sensitive OTP exclusion": 'input[autocomplete="one-time-code"]',
    }
    for label, marker in required_literals.items():
        if marker not in text:
            fail(f"{label} marker missing: {marker}")

    model_context_position = text.find("const modelContext=d.modelContext;")
    first_annotation_pass = text.find("annotateSafeSearchForms();")
    if model_context_position < 0 or first_annotation_pass < 0:
        fail("cannot locate WebMCP initialization order")
    if first_annotation_pass > model_context_position:
        fail("safe declarative form annotation must run before imperative registration")

    expected_tools = {
        "rawafid_get_page_context",
        "rawafid_find_on_page",
        "rawafid_search_knowledge",
        "rawafid_open_section",
    }
    registered = set(re.findall(r"name:'([A-Za-z0-9_.-]+)'", text))
    missing = sorted(expected_tools - registered)
    if missing:
        fail(f"missing imperative tools: {', '.join(missing)}")

    if text.count("inputSchema:") < len(expected_tools):
        fail("not every imperative tool exposes inputSchema")
    if text.count("consequentialHint:false") < len(expected_tools):
        fail("every imperative tool must explicitly declare consequentialHint")

    if "input.name='q'" not in text or "input.required=true" not in text:
        fail("homepage declarative search must expose a named required q parameter")

    if "form.setAttribute('toolname','rawafid_search_encyclopedia')" not in text:
        fail("homepage search is not declaratively registered")

    expected_routes = {
        "home": "/",
        "start": "/start-here/",
        "sections": "/sections/",
        "encyclopedia": "/encyclopedia/",
        "special_needs": "/special-needs/",
        "library": "/library/",
        "magazine": "/magazine/",
        "research": "/library/research/",
        "care_guides": "/care-guides/",
        "daily_tools": "/daily-tools/",
        "assessment_lab": "/assessment-lab/",
        "guided_assessment": "/guided-assessment/",
        "learning_paths": "/learning-paths/",
        "rehabilitation": "/sectors/rehabilitation/",
        "addiction": "/addiction/",
        "team_partners": "/specialists-partners/",
        "trust": "/trust/",
        "api": "/api/",
    }

    route_match = re.search(r"const routes=\{([^}]+)\};", text)
    if not route_match:
        fail("rawafid_open_section route registry missing")
    registered_routes = dict(re.findall(r"([A-Za-z0-9_]+):'([^']+)'", route_match.group(1)))
    if registered_routes != expected_routes:
        missing_routes = sorted(set(expected_routes) - set(registered_routes))
        extra_routes = sorted(set(registered_routes) - set(expected_routes))
        wrong_routes = sorted(
            key for key in set(expected_routes) & set(registered_routes)
            if expected_routes[key] != registered_routes[key]
        )
        fail(
            "route registry drifted "
            f"missing={missing_routes} extra={extra_routes} wrong={wrong_routes}"
        )

    enum_match = re.search(r"enum:\[([^\]]+)\]", text)
    if not enum_match:
        fail("rawafid_open_section enum missing")
    enum_routes = set(re.findall(r"'([A-Za-z0-9_]+)'", enum_match.group(1)))
    if enum_routes != set(expected_routes):
        fail(
            "rawafid_open_section enum differs from route registry "
            f"missing={sorted(set(expected_routes) - enum_routes)} "
            f"extra={sorted(enum_routes - set(expected_routes))}"
        )

    # Some public routes (notably the encyclopedia index) are produced during
    # the publishing build rather than stored as source index.html files. Treat
    # either a source page or an authoritative published-route registry entry
    # as evidence that a fixed agent route is intentional and deployable.
    registry_files = list(ROOT.glob("sitemap*.xml")) + [ROOT / "api" / "v1" / "content-index.json"]
    registry_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in registry_files
        if path.is_file()
    )
    for route_id, route_path in expected_routes.items():
        target = ROOT / "index.html" if route_path == "/" else ROOT / route_path.strip("/") / "index.html"
        public_url = f"https://healthrenewal.org{route_path}"
        if target.is_file() or public_url in registry_text:
            continue
        fail(f"route {route_id} has no source page or published-route registry entry: {route_path}")

    print(
        "WEBMCP_GUARD_OK "
        f"imperative_tools={len(expected_tools)} "
        f"open_section_routes={len(expected_routes)} "
        "declarative_home_search=1 safe_search_annotation=early "
        "schemas=present generator=pinned"
    )


if __name__ == "__main__":
    main()
