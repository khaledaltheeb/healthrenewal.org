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
    }
    for label, marker in required_literals.items():
        if marker not in text:
            fail(f"{label} marker missing: {marker}")

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

    if "input.name='q'" not in text or "input.required=true" not in text:
        fail("homepage declarative search must expose a named required q parameter")

    if "form.setAttribute('toolname','rawafid_search_encyclopedia')" not in text:
        fail("homepage search is not declaratively registered")

    print(
        "WEBMCP_GUARD_OK "
        f"imperative_tools={len(expected_tools)} "
        "declarative_home_search=1 schemas=present generator=pinned"
    )


if __name__ == "__main__":
    main()
