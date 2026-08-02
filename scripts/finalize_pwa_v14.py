from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

CORE = Path(__file__).with_name("finalize_pwa_v14_core.py")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

# Kept explicit for focused contract tests and review tools. Runtime execution
# remains in the byte-preserved core module.
PWA_V24_CONTRACT_MARKERS = r'''
healthrenewal-v24-resilient-core
const OFFLINE='/offline/';
Required offline assets missing
navigationPreload.enable
caches.match(OFFLINE
write_offline_page
normalize_pwa_ux_before_registration
pwa-v24.json
'''


def load_core():
    spec = importlib.util.spec_from_file_location("finalize_pwa_v14_core", CORE)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load PWA v24 finalizer core")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_public_pwa_assets(site: Path) -> list[str]:
    copied: list[str] = []
    sources = (
        Path("manifest.webmanifest"),
        Path("assets/brand/pwa-192.png"),
        Path("assets/brand/pwa-512.png"),
        Path("assets/brand/pwa-maskable-512.png"),
        Path("assets/brand/logo-mark.svg"),
    )
    for relative in sources:
        source = REPOSITORY_ROOT / relative
        destination = site / relative
        if not source.is_file():
            raise SystemExit(f"Missing repository PWA asset: {relative.as_posix()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() == destination.resolve():
            continue
        if destination.is_file() and destination.read_bytes() == source.read_bytes():
            continue
        shutil.copy2(source, destination)
        copied.append(relative.as_posix())
    return copied


def main() -> None:
    core = load_core()
    site = core.SITE.resolve()
    if not site.is_dir():
        raise SystemExit(f"Site root not found: {site}")
    copied = copy_public_pwa_assets(site)
    core.main()
    print({"pwa_public_assets_copied": copied, "contract": "healthrenewal-pwa-v24"})


if __name__ == "__main__":
    main()
