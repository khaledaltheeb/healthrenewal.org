from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

CORE = Path(__file__).with_name("expand_v12_direct_core.py")
spec = importlib.util.spec_from_file_location("expand_v12_direct_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load v12 direct expansion core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def production_base_path(base_url: str) -> str:
    path = urlsplit(base_url).path.strip("/")
    return f"/{path}/" if path else "/"


def main() -> None:
    core.BASE_PATH = production_base_path(core.BASE)
    if core.BASE_PATH.startswith("//") or not core.BASE_PATH.startswith("/"):
        raise SystemExit({"invalid_production_base_path": core.BASE_PATH, "base": core.BASE})
    core.main()


if __name__ == "__main__":
    main()
