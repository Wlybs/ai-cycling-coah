import glob
import json
import os
import sys
from collections import deque

from dotenv import load_dotenv

load_dotenv(override=True)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WAREHOUSE_ROOT = os.getenv("OUTPUT_WAREHOUSE_DIR", "./icu_data_warehouse")
DETAIL_DIR = os.path.join(WAREHOUSE_ROOT, "5_Activities_Detail")
WELLNESS_DIR = os.path.join(WAREHOUSE_ROOT, "2_Wellness")
PROFILE_DIR = os.path.join(WAREHOUSE_ROOT, "1_Profile")
REPORT_DIR = os.getenv("REPORT_DIR", "./reports")

class MetricsCalculator:
    @staticmethod
    def calculate_np(watts_stream):
        if not watts_stream:
            return 0
        rolling_avg = []
        window = deque(maxlen=30)
        for w in watts_stream:
            window.append(w)
            if len(window) == 30:
                avg = sum(window) / 30
                rolling_avg.append(avg)
        if not rolling_avg:
            return sum(watts_stream)/len(watts_stream)
        sum_pow4 = sum([x**4 for x in rolling_avg])
        avg_pow4 = sum_pow4 / len(rolling_avg)
        return int(avg_pow4 ** 0.25)

    @staticmethod
    def calculate_decoupling(watts_stream, hr_stream):
        if not watts_stream or not hr_stream or len(watts_stream) != len(hr_stream):
            return None
        length = len(watts_stream)
        if length < 1200:
            return None
        mid = length // 2
        p1 = sum(watts_stream[:mid]) / mid
        hr1 = sum(hr_stream[:mid]) / mid
        p2 = sum(watts_stream[mid:]) / (length - mid)
        hr2 = sum(hr_stream[mid:]) / (length - mid)
        if hr1 == 0 or hr2 == 0:
            return None
        ratio1 = p1 / hr1
        ratio2 = p2 / hr2
        decoupling = (ratio1 - ratio2) / ratio1 * 100
        return decoupling

class RideAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self._load_data()
        self.summary = self.data.get('summary', {})
        self.laps = self.data.get('laps', [])
        self.streams = self.data.get('streams', {})

        self.profile = self._load_profile()

        self.ftp = 200
        if self.profile and self.profile.get('icu_ftp'):
            self.ftp = self.profile.get('icu_ftp')
        else:
            self.ftp = self.summary.get('icu_ftp', 200)

        self.weight = 65.0
        if self.profile and self.profile.get('weight'):
            self.weight = self.profile.get('weight')
        else:
            self.weight = self.summary.get('icu_weight', 65.0)

        # CP for W' balance model: at least FTP (ICU may underestimate CP)
        self.cp = max(self.summary.get('icu_pm_cp') or 0, self.ftp)

        self.w_prime_cap = self.summary.get('icu_pm_w_prime', 20000)

        self.output_buffer = []
        self.wellness = self._load_wellness()

    def _load_data(self):
        try:
            with open(self.file_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 无法读取文件: {e}")
            sys.exit(1)

    def _load_profile(self):
        try:
            p_file = os.path.join(PROFILE_DIR, "athlete_profile.json")
            if os.path.exists(p_file):
                with open(p_file, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载运动员档案失败: {e}")
        return None

    def _load_wellness(self):
        try:
            wellness_file = os.path.join(WELLNESS_DIR, "wellness_history.json")
            if not os.path.exists(wellness_file):
                return None

            with open(wellness_file, encoding='utf-8') as f:
                wellness_list = json.load(f)

            target_date = self.summary.get('start_date_local', '')[:10]

            for w in wellness_list:
                if w.get('id') == target_date:
                    return w
            return None
        except Exception:
            return None

    def _log(self, text=""):
        self.output_buffer.append(text)

    def _fmt_time(self, seconds):
        if not seconds:
            return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h{m}m"
        return f"{m}m{s}s"

    def analyze_lap(self, lap, idx):
        dur = int(lap.get('duration_sec', 0))
        if dur < 5:
            return None

        avg_w = lap.get('avg_watts', 0)
        avg_hr = lap.get('avg_hr', 0)
        s_idx = lap.get('stream_start_index')
        e_idx = lap.get('stream_end_index')

        watts_chunk = []
        hr_chunk = []
        w_bal_chunk = []
        altitude_chunk = []

        if s_idx is not None and e_idx is not None:
            if 'watts' in self.streams:
                watts_chunk = self.streams['watts'][s_idx:e_idx]
                watts_chunk = [w if w is not None else 0 for w in watts_chunk]
                if watts_chunk:
                    avg_w = sum(watts_chunk) / len(watts_chunk)
            if 'heartrate' in self.streams:
                hr_chunk = self.streams['heartrate'][s_idx:e_idx]
                hr_chunk = [h if h is not None else 0 for h in hr_chunk]
                if hr_chunk:
                    avg_hr = sum(hr_chunk) / len(hr_chunk)
            if 'w_bal' in self.streams:
                w_bal_chunk = self.streams['w_bal'][s_idx:e_idx]
                w_bal_chunk = [w if w is not None else self.w_prime_cap for w in w_bal_chunk]
            if 'altitude' in self.streams:
                altitude_chunk = [a for a in self.streams['altitude'][s_idx:e_idx] if a is not None]

        np = MetricsCalculator.calculate_np(watts_chunk)
        vi = (np / avg_w) if avg_w > 0 else 1.0
        if_val = np / self.ftp if self.ftp > 0 else 0
        ef = (np / avg_hr) if avg_hr > 0 else 0
        decouple = MetricsCalculator.calculate_decoupling(watts_chunk, hr_chunk)

        # 使用 ICU 提供的 w_bal (Joules)
        min_w_pct = None
        if w_bal_chunk:
            min_joules = min(w_bal_chunk)
            # 自动推断 Capacity：取该段（或者应该取全场？）的最大值作为充满状态
            # 但如果是分段，可能某段没充满。应该用全场的 max 或者 summary 里的
            # 为了简单和安全，我们假设全场最大值接近 Capacity
            # 这里先用 self.w_prime_cap，如果 min > cap, 说明 cap 取小了
            cap = max(self.w_prime_cap, max(w_bal_chunk))
            min_w_pct = (min_joules / cap) * 100

        # Calculate HRR (Heart Rate Recovery)
        # Definition: Drop in HR from start of lap to 60s into lap (or end if < 60s)
        hrr_val = None
        if hr_chunk:
            start_hr = hr_chunk[0]
            if len(hr_chunk) >= 60:
                check_hr = hr_chunk[60]
            else:
                check_hr = hr_chunk[-1]
            hrr_val = start_hr - check_hr

        # 海拔净变化（正=爬升，负=下降）
        net_elevation = None
        if len(altitude_chunk) >= 2:
            net_elevation = altitude_chunk[-1] - altitude_chunk[0]
        is_descending = net_elevation is not None and net_elevation < -10

        # 数据质量异常检测：功率极低但心率正常偏高，优先怀疑设备故障
        data_anomaly = False
        data_anomaly_reason = ""
        if avg_w < 30 and avg_hr > 100 and dur > 60:
            data_anomaly = True
            data_anomaly_reason = f"❓数据存疑(功率{int(avg_w)}w/心率{int(avg_hr)}bpm，请确认功率计是否正常)"
        elif watts_chunk:
            zero_ratio = sum(1 for w in watts_chunk if w == 0) / len(watts_chunk)
            if zero_ratio > 0.3 and avg_hr > 90 and dur > 60:
                data_anomaly = True
                data_anomaly_reason = f"❓功率信号丢失({zero_ratio:.0%}为零值/心率{int(avg_hr)}bpm，请确认功率计或特殊地形)"

        lap_type = "Endurance"
        if if_val < 0.55:
            lap_type = "Recovery"
        elif if_val < 0.75:
            lap_type = "Endurance"
        elif if_val < 0.88:
            lap_type = "Tempo"
        elif if_val < 1.05:
            lap_type = "Threshold"
        elif if_val < 1.50:
            lap_type = "VO2Max"
        else:
            lap_type = "Anaerobic"

        if dur > 60 and avg_w < 20:
            lap_type = "Rest/Supply"
        elif dur < 180 and if_val < 0.6:
            lap_type = "Rest"
        elif dur > 600 and if_val < 0.6:
            lap_type = "Warmup/Cool"

        # 低功率+下坡：标记为下坡恢复/应激，而非体力不支
        if if_val < 0.65 and is_descending and not data_anomaly:
            lap_type = "Downhill恢复"

        insight = []
        if data_anomaly:
            insight.append(data_anomaly_reason)
        elif lap_type == "Rest/Supply":
            insight.append("☕️补给中")
        else:
            if lap_type == "Downhill恢复":
                desc_m = abs(int(net_elevation))
                insight.append(f"↘下坡{desc_m}m(下坡恢复/应激，非体力不支)")
            if vi < 1.05 and dur > 300:
                insight.append("稳态")
            if vi > 1.2 and avg_w > 150:
                insight.append("波动")
            if decouple and decouple > 5:
                insight.append(f"⚠️Decoupling {decouple:.1f}%")
            if min_w_pct is not None and min_w_pct < 10:
                insight.append("🔥W'耗尽")

        return {
            "id": idx + 1,
            "type": lap_type,
            "dur": dur,
            "w": int(avg_w),
            "np": np,
            "if": if_val,
            "vi": vi,
            "hr": int(avg_hr),
            "hrr": hrr_val,
            "ef": ef,
            "decouple": decouple,
            "min_w": min_w_pct,
            "insight": ", ".join(insight)
        }

    def calculate_full_ride_metrics(self):
        watts = self.streams.get('watts', [])
        hr = self.streams.get('heartrate', [])
        watts = [w if w is not None else 0 for w in watts]
        hr = [h if h is not None else 0 for h in hr]
        if not watts:
            return {}

        avg_p = sum(watts) / len(watts)
        np = MetricsCalculator.calculate_np(watts)
        vi = (np / avg_p) if avg_p > 0 else 1.0
        if_val = np / self.ftp if self.ftp > 0 else 0
        avg_hr = sum(hr) / len(hr) if hr else 0
        ef = (np / avg_hr) if avg_hr > 0 else 0
        decouple = MetricsCalculator.calculate_decoupling(watts, hr)

        return {
            "avg_p": int(avg_p),
            "np": np,
            "if": if_val,
            "vi": vi,
            "avg_hr": int(avg_hr),
            "ef": ef,
            "decouple": decouple
        }

    def generate_report(self):
        s = self.summary
        date_str = s.get('start_date_local', '')[:10]
        clean_date = date_str.replace('-', '')
        name = s.get('name', 'Unknown')
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()

        total_time = self._fmt_time(s.get('moving_time', 0))
        dist = s.get('distance', 0) / 1000
        tss = s.get('icu_training_load', 0)

        full = self.calculate_full_ride_metrics()

        self._log("\n" + "="*75)
        self._log(f"🚴 {date_str} | {name}")
        self._log(f"⏱️  {total_time} | 🛣️  {dist:.1f}km | TSS: {tss} | FTP设: {self.ftp}w (CP: {self.cp}w)")
        self._log("-" * 75)

        if self.wellness:
            w = self.wellness
            hrv = w.get('hrvSDNN')
            rhr = w.get('restingHR')
            ctl = w.get('ctl')
            atl = w.get('atl')

            hrv_str = f"{hrv}ms" if hrv else "-"
            rhr_str = f"{rhr}bpm" if rhr else "-"

            tsb_str = "-"
            if ctl is not None and atl is not None:
                tsb = ctl - atl
                tsb_sign = "+" if tsb > 0 else ""
                tsb_str = f"{tsb_sign}{tsb:.1f}"

            ctl_str = f"{ctl:.1f}" if ctl else "-"

            self._log("🏥 [状态上下文]")
            self._log(f"   🔹 HRV: {hrv_str}  |  RHR: {rhr_str}  |  TSB: {tsb_str} (Fitness {ctl_str})")
        else:
            self._log("🏥 [状态上下文] (未找到当日健康数据)")

        d_str = f"{full['decouple']:.1f}%" if full['decouple'] is not None else "-"
        self._log("\n📊 [全场概览]")
        self._log(f"   🔹 AP: {full['avg_p']}w  |  NP: {full['np']}w  |  IF: {full['if']:.2f}  |  VI: {full['vi']:.2f}")
        self._log(f"   🔹 HR: {full['avg_hr']}bpm |  EF: {full['ef']:.2f}  |  Decoupling: {d_str}")
        self._log("="*75)

        self._log("\n📊 [计圈详解 - Lap Analysis]")
        min_w_label = "Min W'"
        header = f"{'#':<3} {'Type':<12} {'Time':<8} {'AP':<4} {'NP':<4} {'IF':<5} {'VI':<5} {'HR':<4} {'HRR':<4} {'EF':<5} {'Dec%':<6} {min_w_label:<7} {'点评'}"
        self._log(header)
        self._log("-" * len(header))

        work_laps = []
        display_idx = 1

        for idx, lap in enumerate(self.laps):
            res = self.analyze_lap(lap, idx)
            if not res:
                continue

            if res['if'] > 0.75 and res['dur'] > 120:
                work_laps.append(res)

            dur_str = self._fmt_time(res['dur'])
            dec_str = f"{res['decouple']:.1f}" if res['decouple'] is not None else "-"
            w_str = f"{int(res['min_w'])}%" if res['min_w'] is not None else "-"
            hrr_str = f"{res['hrr']}" if res['hrr'] is not None else "-"

            self._log(f"{display_idx:<3} {res['type']:<12} {dur_str:<8} {res['w']:<4} {res['np']:<4} {res['if']:.2f}  {res['vi']:.2f}  {res['hr']:<4} {hrr_str:<4} {res['ef']:.2f}  {dec_str:<6} {w_str:<7} {res['insight']}")
            display_idx += 1

        if len(work_laps) > 1:
            self._log("\n📈 [训练组聚合分析]")
            self._log(f"识别到 {len(work_laps)} 个有效训练组 (Tempo+):")

            avg_work_p = sum([l['w'] for l in work_laps]) / len(work_laps)
            p_variance = max([l['w'] for l in work_laps]) - min([l['w'] for l in work_laps])
            consistency = "⭐⭐⭐⭐⭐" if p_variance < 10 else ("⭐⭐⭐" if p_variance < 20 else "⭐")

            self._log(f"   🔹 平均功率: {int(avg_work_p)}w")
            self._log(f"   🔹 执行一致性: {consistency} (波动范围 {p_variance}w)")

            first_w = work_laps[0]['w']
            last_w = work_laps[-1]['w']
            if first_w - last_w > 15:
                self._log(f"   ⚠️ 功率衰减警告: 最后一组比第一组低 {first_w - last_w}w")

        self._log("\n" + "="*75 + "\n")

        if not os.path.exists(REPORT_DIR):
            os.makedirs(REPORT_DIR)

        filename = f"report_{clean_date}_{safe_name}.txt"
        filepath = os.path.join(REPORT_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.output_buffer))
            print(f"✅ 报告已生成: {filepath}")
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")

def get_latest_file():
    search_pattern = os.path.join(DETAIL_DIR, "*.json")
    files = glob.glob(search_pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.exists(arg):
            target_file = arg
        else:
            search_pattern = os.path.join(DETAIL_DIR, f"*{arg}*.json")
            matches = glob.glob(search_pattern)
            target_file = matches[0] if matches else None
            if not target_file:
                print(f"❌ 找不到文件: {arg}")
                return
    else:
        target_file = get_latest_file()
        if not target_file:
            print("❌ 仓库为空，请先同步数据。")
            return

    analyzer = RideAnalyzer(target_file)
    analyzer.generate_report()

if __name__ == "__main__":
    main()
