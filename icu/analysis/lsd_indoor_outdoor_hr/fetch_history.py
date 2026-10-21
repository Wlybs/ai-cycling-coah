"""只读拉取 2026-10-20 室内/户外 LSD 心率分析所需的历史活动清单与原始 streams。

只调用 ICU GET 接口；输出全部落在本次专属目录
icu_data_warehouse/9_Coach_Raw/2026-10-20-outdoor-lsd-tradeoff/，不覆盖常规 sync 缓存。

用法:
    python fetch_history.py list               # 拉 2026-08-01..2026-10-20 活动清单
    python fetch_history.py streams <id> ...   # 拉指定活动的完整 streams
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ICU_ROOT = Path("D:/Cycling/icu")
OUT_DIR = ICU_ROOT / "icu_data_warehouse/9_Coach_Raw/2026-10-20-outdoor-lsd-tradeoff"
STREAM_TYPES = "time,watts,heartrate,cadence,velocity_smooth,distance,latlng,temp,altitude"
LIST_RANGE = ("2026-08-01", "2026-10-20")

load_dotenv(ICU_ROOT / ".env")  # 显式路径：默认查找在本机会抛 AssertionError
sys.path.insert(0, str(ICU_ROOT))
from src.fetcher.icu_client import ICUClient  # noqa: E402


def save(name, obj):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    print(f"saved {path} ({path.stat().st_size} bytes)")


def fetch_list(client):
    acts = client.get_activities(*LIST_RANGE)
    save(f"activities_{LIST_RANGE[0]}_{LIST_RANGE[1]}.json", acts)


def fetch_streams(client, ids):
    for aid in ids:
        target = OUT_DIR / f"streams_{aid}.json"
        if target.exists():
            print(f"skip {aid}: already fetched")
            continue
        save(target.name, client.get_activity_streams(aid, types=STREAM_TYPES))


def main():
    client = ICUClient()
    if sys.argv[1] == "list":
        fetch_list(client)
    elif sys.argv[1] == "streams":
        fetch_streams(client, sys.argv[2:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
