import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "1_Profile")


def main():
    print("👤 正在同步运动员档案 (Profile)...")
    client = ICUClient()
    try:
        profile = client.get_athlete()
        path = save_json(profile, OUTPUT_DIR, "athlete_profile.json")
        print(f"✅ 档案已更新: {path}")
        print(f"   ID: {profile.get('id')} | Name: {profile.get('name')}")
        print(f"   FTP: {profile.get('icu_ftp')}W | Weight: {profile.get('weight')}kg")
    except Exception as e:
        print(f"❌ 同步失败: {e}")


if __name__ == "__main__":
    main()
