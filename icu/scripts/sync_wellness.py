import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "2_Wellness")


def main():
    print("🏥 正在同步健康数据 (Wellness)...")
    client = ICUClient()
    today = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    try:
        wellness_data = client.get_wellness(oldest, today)
        if wellness_data:
            path = save_json(wellness_data, OUTPUT_DIR, "wellness_history.json")
            print(f"✅ 健康数据已更新 ({len(wellness_data)} 条): {path}")
            latest = wellness_data[-1]
            print(f"   最新: {latest.get('id')} | HRV: {latest.get('hrvSDNN')}ms"
                  f" | RHR: {latest.get('restingHR')}bpm | CTL: {latest.get('ctl')}")
        else:
            print("⚠️ 未获取到健康数据。")
    except Exception as e:
        print(f"❌ 同步失败: {e}")


if __name__ == "__main__":
    main()
