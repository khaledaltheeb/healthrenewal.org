from __future__ import annotations

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import daily_tools_v100 as v100
from scripts import daily_tools_v150 as v150
from scripts import publish_daily_tools_v24 as publisher


def publish(site: Path | str) -> dict:
    target=Path(site).resolve()
    if not target.is_dir():
        raise SystemExit(f'Missing site output: {target}')
    data=v150.upgrade_data(v100.load_data())
    special=target/'daily-tools/sleep-wind-down-plan/index.html'
    preserved=None
    if special.is_file():
        candidate=special.read_text(encoding='utf-8')
        if 'data-sleep-log' in candidate and 'sleep-log-v49.js' in candidate:
            preserved=candidate
    publisher.publish(data,target)
    if preserved is not None:
        special.parent.mkdir(parents=True,exist_ok=True)
        special.write_text(preserved,encoding='utf-8')
    return v150.enhance(data,target)


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
    print(publish(target))
