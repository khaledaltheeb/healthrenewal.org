#!/usr/bin/env python3
from __future__ import annotations

try:
    from .publish_global_metadata_v27_core import *  # type: ignore[F403]  # noqa: F401,F403
    from . import publish_global_metadata_v27_core as _core
    from .upgrade_institutional_seo_v215 import main as _publish_institutional_seo
except ImportError:
    from publish_global_metadata_v27_core import *  # type: ignore[F403]  # noqa: F401,F403
    import publish_global_metadata_v27_core as _core
    from upgrade_institutional_seo_v215 import main as _publish_institutional_seo


def main() -> None:
    _core.main()
    _publish_institutional_seo()


if __name__ == "__main__":
    main()
