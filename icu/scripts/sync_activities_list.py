import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "4_Activities_List")


def main():
    print("📋 正在同步活动清单 (Activity List)...")
    client = ICUClient()

    lookback = 30
    if len(sys.argv) > 1:
        try:
            lookback = int(sys.argv[1])
        except ValueError:
            pass

    today = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
    print(f"   查询范围: {oldest} 至 {today} ({lookback}天)")

    try:
        activities = client.get_activities(oldest, today)
        if activities:
            path = save_json(activities, OUTPUT_DIR, "activity_list_clean.json")
            print(f"✅ 活动清单已更新 (共 {len(activities)} 条): {path}")
            print(f"   最新: {activities[0]['name']} ({activities[0]['start_date_local'][:10]})")
        else:
            print("⚠️ 未找到任何活动。")
    except Exception as e:
        print(f"❌ 同步失败: {e}")


if __name__ == "__main__":
    main()
