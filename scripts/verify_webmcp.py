#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "assets" / "brand" / "rawafid-brand.js"


def fail(message: str) -> None:
    print(f"WEBMCP_GUARD_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not JS.is_file():
        fail(f"missing {JS.relative_to(ROOT)}")

    text = JS.read_text(encoding="utf-8")
    required_literals = {
        "model context feature detection": "document.modelContext",
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
        "declarative_home_search=1 schemas=present"
    )


if __name__ == "__main__":
    main()
