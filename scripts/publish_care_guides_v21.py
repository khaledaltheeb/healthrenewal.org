from __future__ import annotations

# Compatibility entrypoint retained because the production workflow invokes this path.
from publish_care_guides_v246 import *  # noqa: F401,F403
from publish_care_guides_v246 import main


if __name__ == "__main__":
    main()
