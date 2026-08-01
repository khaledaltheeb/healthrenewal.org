#!/usr/bin/env python3
"""Create compact, reviewable warning summaries from SEO audit JSON reports."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def summarize(source: Path, output: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    by_code: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    urls: dict[str, list[dict[str, str]]] = defaultdict(list)

    for result in payload.get("results", []):
        warnings = [item for item in result.get("findings", []) if item.get("severity") == "warning"]
        if not warnings:
            continue
        by_kind[result.get("kind", "unknown")] += len(warnings)
        for item in warnings:
            code = item.get("code", "unknown")
            by_code[code] += 1
            urls[result.get("url", "")].append({
                "code": code,
                "message": item.get("message", ""),
            })

    summary = {
        "scope": payload.get("summary", {}).get("scope"),
        "warnings": sum(by_code.values()),
        "warning_codes": dict(sorted(by_code.items(), key=lambda item: (-item[1], item[0]))),
        "warning_kinds": dict(sorted(by_kind.items(), key=lambda item: (-item[1], item[0]))),
        "urls": dict(sorted(urls.items())),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markdown = output.with_suffix(".md")
    lines = [
        "# SEO warning summary",
        "",
        f"- Scope: `{summary['scope']}`",
        f"- Warnings: **{summary['warnings']}**",
        "",
        "## Warning codes",
        "",
    ]
    if by_code:
        lines.extend(f"- `{code}`: **{count}**" for code, count in summary["warning_codes"].items())
    else:
        lines.append("- None")
    lines.extend(["", "## URLs", ""])
    if urls:
        for url, findings in summary["urls"].items():
            lines.append(f"### {url}")
            lines.extend(f"- `{item['code']}` — {item['message']}" for item in findings)
            lines.append("")
    else:
        lines.append("- None")
    markdown.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.source, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
