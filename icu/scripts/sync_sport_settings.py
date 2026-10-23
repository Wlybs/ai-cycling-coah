"""同步运动员的区间设置（功率区间、心率区间、FTP 等）。"""
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "6_SportSettings")


def main():
    print("⚙️  正在同步运动区间设置 (Sport Settings)...")
    client = ICUClient()
    try:
        settings = client.get_sport_settings()
        path = save_json(settings, OUTPUT_DIR, "sport_settings.json")
        print(f"✅ 区间设置已保存: {path}")

        # 打印关键区间信息
        for sport in (settings if isinstance(settings, list) else [settings]):
            sport_type = sport.get('type', '?')
            ftp = sport.get('ftp') or sport.get('ftpFTP')
            lthr = sport.get('lthr') or sport.get('thresholdHR')
            zones = sport.get('zones', [])
            print(f"   [{sport_type}] FTP: {ftp}W | LTHR: {lthr}bpm | 区间数: {len(zones)}")
    except Exception as e:
        print(f"❌ 同步失败: {e}")


if __name__ == "__main__":
    main()
