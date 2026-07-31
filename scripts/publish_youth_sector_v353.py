#!/usr/bin/env python3
from __future__ import annotations

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
    "information_evaluation": f"{BASE_PATH}/trust/#evidence",
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


shell_footer = _base.shell_footer = _wrap_renderer(_base.shell_footer)
collection_body = _base.collection_body = _wrap_renderer(_base.collection_body)
guide_body = _base.guide_body = _wrap_renderer(_base.guide_body)

publish = _base.publish
main = _base.main


if __name__ == "__main__":
    raise SystemExit(main())
