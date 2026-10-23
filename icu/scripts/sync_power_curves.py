import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "3_PowerData")


def _watts_at(curve, secs):
    """按时长查曲线功率；secs 是稀疏数组，不能按下标 secs-1 取值。"""
    try:
        return curve['watts'][curve['secs'].index(secs)]
    except (KeyError, ValueError, IndexError):
        return None


def _fetch_window(client, curves, filename, expected_id):
    """拉取一个时间窗并校验响应 id，防止接口静默换成别的窗口。"""
    data = client.get_power_curves(curves=curves)
    entries = (data or {}).get('list') or []
    if not entries:
        print(f"   ⚠️ {curves} 曲线为空，未覆盖旧文件。")
        return None
    got = entries[0].get('id')
    if got != expected_id:
        raise ValueError(f"请求 curves={curves} 但响应 id={got}，未保存")
    path = save_json(data, OUTPUT_DIR, filename)
    e = entries[0]
    print(f"   ✅ 已保存 {path}  ({e.get('start_date_local', '')[:10]} → {e.get('end_date_local', '')[:10]})")
    return e


def main():
    print("📈 正在同步功率曲线 (Power Curves)...")
    client = ICUClient()
    try:
        print("   [1/2] 同步最近 90 天 ...")
        curve = _fetch_window(client, "90d", "power_curves_90d.json", "90d")
        if curve:
            print(f"   1s: {_watts_at(curve, 1)}W | 1min: {_watts_at(curve, 60)}W"
                  f" | 5min: {_watts_at(curve, 300)}W | 20min: {_watts_at(curve, 1200)}W")

        print("   [2/2] 同步全生涯最佳...")
        _fetch_window(client, "all", "power_curves_all_time.json", "all")
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
