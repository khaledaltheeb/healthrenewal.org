from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")


def main() -> None:
    core = Path(__file__).with_name("harden_cognitive_banks_core_v211.py")
    difficulty = Path(__file__).with_name("harden_cognitive_difficulty_v212.py")
    subprocess.run([sys.executable, str(core), str(SITE)], check=True)
    subprocess.run([sys.executable, str(difficulty), str(SITE)], check=True)


if __name__ == "__main__":
    main()
