"""同步日历事件（计划训练、比赛、目标等）。"""
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

OUTPUT_DIR = os.path.join(get_warehouse_dir(), "8_Events")


def main():
    print("📅 正在同步日历事件 (Events)...")
    client = ICUClient()

    # 默认同步前30天到后90天（覆盖近期历史和未来计划）
    oldest = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    newest = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

    try:
        events = client.get_events(oldest, newest)
        if not isinstance(events, list):
            raise ValueError(f"events 接口返回非列表: {type(events).__name__}")
        # 空列表也要写入：日历被清空时若保留旧文件，下游会继续读到已删除的旧课表/旧比赛
        path = save_json(events, OUTPUT_DIR, "events.json")
        print(f"✅ 日历事件已保存 ({len(events)} 条, {oldest} → {newest}): {path}")

        # 统计各类型数量
        type_counts = {}
        for e in events:
            t = e.get('type', 'Unknown')
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, cnt in sorted(type_counts.items()):
            print(f"   {t}: {cnt} 条")
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
