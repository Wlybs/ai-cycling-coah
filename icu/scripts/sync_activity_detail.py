"""
同步活动详情：FIT 计圈 + Streams 数据打包入仓库。

用法:
  python sync_activity_detail.py          # 同步最新 1 条
  python sync_activity_detail.py 5        # 同步最新 5 条
  python sync_activity_detail.py 30 60   # 同步最近 60 天内最新 30 条
"""
import sys
import os
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.utils.fit_parser import parse_fit_laps
from src.analyzer.lap_alignment import align_laps_to_streams
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()
load_dotenv(override=True)

DIR_ACT_DETAIL = os.path.join(get_warehouse_dir(), "5_Activities_Detail")


def sanitize_filename(name):
    return re.sub(r'[\/*?:"<>|]', "", name)


def process_single_ride(client, act, current_idx, total_count):
    act_id = act['id']
    act_name = act['name']
    act_date = act['start_date_local'][:10]

    print(f"\n[{current_idx}/{total_count}] {act_date} | {act_name}")
    eftp = act.get('icu_pm_ftp')
    if eftp:
        print(f"   eFTP: {eftp}W (设定值: {act.get('icu_ftp')}W)")

    try:
        # ICU 活动详情（含结构化间歇段）
        try:
            icu_detail = client.get_activity(act_id)
            icu_intervals = icu_detail.get('icu_intervals', []) if icu_detail else []
            print(f"   ✅ ICU 间歇段: {len(icu_intervals)} 个")
        except Exception as e:
            print(f"   ⚠️ ICU 间歇段获取失败: {e}")
            icu_intervals = []

        # FIT 文件 → 计圈
        try:
            fit_content = client.get_activity_file(act_id)
            raw_laps = parse_fit_laps(fit_content)
            print(f"   ✅ FIT 计圈: {len(raw_laps)} 个")
        except Exception as e:
            print(f"   ⚠️ FIT 获取失败: {e}")
            raw_laps = []

        # Streams
        try:
            streams_list = client.get_activity_streams(act_id)
            streams_data = {}
            if isinstance(streams_list, list):
                for s in streams_list:
                    streams_data[s['type']] = s['data']
            else:
                streams_data = streams_list
        except Exception as e:
            print(f"   ❌ Streams 获取失败: {e}")
            return False

        # 功率/心率分布直方图
        power_histogram = None
        hr_histogram = None
        try:
            power_histogram = client.get_power_histogram(act_id)
        except Exception:
            pass
        try:
            hr_histogram = client.get_hr_histogram(act_id)
        except Exception:
            pass

        # 计圈与 stream 对齐：按 FIT lap 起始时间映射到 streams.time（duration_sec 含暂停，不能累加当索引）
        final_laps = align_laps_to_streams(raw_laps, streams_data.get('time') or [], act.get('start_date'))

        final_package = {
            "summary": act,
            "icu_intervals": icu_intervals,
            "laps": final_laps,
            "streams": streams_data,
            "power_histogram": power_histogram,
            "hr_histogram": hr_histogram,
            "metadata": {
                "downloaded_at": datetime.now().isoformat(),
                "source": "Intervals.icu v1",
            }
        }

        filename = f"{act_date}_{act_id}.json"
        save_json(final_package, DIR_ACT_DETAIL, filename)
        print(f"   🎉 已归档: {filename}")
        return True

    except Exception as e:
        print(f"   ❌ 处理异常: {e}")
        return False


def main():
    print("🚀 启动活动详情同步...")
    client = ICUClient()

    # 参数解析：count [lookback_days]
    count = 1
    lookback = 30
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        try:
            lookback = int(sys.argv[2])
        except ValueError:
            pass

    today = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
    print(f"🔍 查找 {oldest} 至 {today} 的骑行活动...")

    try:
        activities = client.get_activities(oldest, today)
        activities = [a for a in activities if a.get('type') in ['Ride', 'VirtualRide']]
        if not activities:
            print("❌ 未找到骑行活动。")
            return

        activities.sort(key=lambda x: x['start_date_local'], reverse=True)
        count = min(count, len(activities))
        print(f"✅ 找到 {len(activities)} 个骑行活动，将同步最新 {count} 个。")

        for i in range(count):
            process_single_ride(client, activities[i], i + 1, count)
            if i < count - 1:
                time.sleep(1)

    except Exception as e:
        print(f"❌ 出错: {e}")


if __name__ == "__main__":
    main()
