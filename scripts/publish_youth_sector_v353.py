#!/usr/bin/env python3
from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import publish_youth_sector_v353_base as _base
from publish_youth_sector_v353_base import *  # noqa: F401,F403

TRUST_ROUTES = {
    "methodology": f"{BASE_PATH}/trust/",
    "information_evaluation": f"{BASE_PATH}/trust/",
}

_RETIRED_ROUTES = {
    BASE_PATH + "/" + "editorial-methodology/": TRUST_ROUTES["methodology"],
    BASE_PATH + "/" + "evaluate-mental-health-information/": TRUST_ROUTES["information_evaluation"],
}


def _rewrite_trust_routes(source: str) -> str:
    for retired, published in _RETIRED_ROUTES.items():
        source = source.replace(f'href="{retired}"', f'href="{published}"')
    return source


def _wrap_renderer(renderer: Callable[..., str]) -> Callable[..., str]:
    def wrapped(*args: Any, **kwargs: Any) -> str:
        return _rewrite_trust_routes(renderer(*args, **kwargs))

    wrapped.__name__ = renderer.__name__
    wrapped.__doc__ = renderer.__doc__
    return wrapped


def _alias_page(title: str, description: str, target: str) -> str:
    safe_title = html.escape(title, quote=True)
    safe_description = html.escape(description, quote=True)
    safe_target = html.escape(target, quote=True)
    absolute = html.escape(f"{BASE}{target.removeprefix(BASE_PATH)}", quote=True)
    return f"""<!doctype html>
<html lang="ar" dir="rtl" data-legacy-path-alias="trust-governance-v354">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} | منصة الصحة النفسية</title>
<meta name="description" content="{safe_description}">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{absolute}">
<meta http-equiv="refresh" content="0;url={safe_target}">
<style>body{{font-family:Tahoma,Arial,sans-serif;line-height:1.9;margin:0;background:#edf9f7;color:#123f43}}main{{width:min(760px,92%);margin:12vh auto;background:#fff;border:1px solid #c8e1de;border-radius:22px;padding:28px}}a{{color:#075f5b;font-weight:800}}</style>
</head>
<body><main><h1>{safe_title}</h1><p>{safe_description}</p><p><a href="{safe_target}">الانتقال إلى صفحة الثقة والمنهجية ←</a></p></main></body>
</html>
"""


def _publish_compatibility_aliases(site: Path) -> None:
    aliases = {
        "editorial-methodology": (
            "المنهجية التحريرية",
            "نُقلت المنهجية التحريرية إلى صفحة الثقة والمصادر والمراجعة الموحدة.",
            TRUST_ROUTES["methodology"],
        ),
        "evaluate-mental-health-information": (
            "تقييم معلومات الصحة النفسية",
            "نُقل دليل تقييم المعلومات النفسية إلى صفحة الثقة والمصادر والمراجعة الموحدة.",
            TRUST_ROUTES["information_evaluation"],
        ),
    }
    for slug, (title, description, target) in aliases.items():
        path = site / slug / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_alias_page(title, description, target), encoding="utf-8")


shell_footer = _base.shell_footer = _wrap_renderer(_base.shell_footer)
collection_body = _base.collection_body = _wrap_renderer(_base.collection_body)
guide_body = _base.guide_body = _wrap_renderer(_base.guide_body)


def publish(site: Path, source_path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    report = _base.publish(site, source_path)
    _publish_compatibility_aliases(site.resolve())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the evidence-backed youth mental-health sector")
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    print(json.dumps(publish(args.site, args.source), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
