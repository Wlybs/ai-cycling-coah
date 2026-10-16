import time
import socket
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds
PROXY_PROBE_TIMEOUT = 1.0  # seconds

# requests drops proxy keys explicitly set to None *after* merging env proxies,
# so this forces a direct connection even when env http(s)_proxy is set.
DIRECT_PROXIES = {"http": None, "https": None}


def _proxy_reachable(port) -> bool:
    """True if something is listening on 127.0.0.1:<port>."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=PROXY_PROBE_TIMEOUT):
            return True
    except (OSError, ValueError):
        return False


class ICUClient:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.athlete_id = os.getenv("ATHLETE_ID")
        self.base_url = "https://intervals.icu/api/v1"
        self.auth = ('API_KEY', self.api_key)
        self.proxies = self._resolve_proxies(os.getenv("PROXY_PORT"))

    @staticmethod
    def _resolve_proxies(proxy_port):
        """PROXY_PORT 可达则走本地代理；不可达则直连，避免整轮 sync 因代理关闭而失败。"""
        if not proxy_port:
            return None
        if _proxy_reachable(proxy_port):
            return {
                "http": f"http://127.0.0.1:{proxy_port}",
                "https": f"http://127.0.0.1:{proxy_port}",
            }
        print(f"   ⚠️  PROXY_PORT={proxy_port} 无法连接，改为直连 intervals.icu")
        return DIRECT_PROXIES

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method, url, auth=self.auth, proxies=self.proxies, **kwargs
                )
                if response.status_code not in RETRYABLE_STATUS or attempt == MAX_RETRIES:
                    response.raise_for_status()
                    return response
                delay = BASE_DELAY * (2 ** attempt)
                print(f"   ⚠️  HTTP {response.status_code}, retrying in {delay}s...")
                time.sleep(delay)
            except requests.ConnectionError:
                if attempt == MAX_RETRIES:
                    raise
                delay = BASE_DELAY * (2 ** attempt)
                print(f"   ⚠️  Connection error, retrying in {delay}s...")
                time.sleep(delay)
        return response  # unreachable, but satisfies linters

    def _get(self, path, params=None):
        return self._request("GET", path, params=params).json()

    def _get_bytes(self, path):
        return self._request("GET", path).content

    # ── 运动员基础 ──────────────────────────────────────────────────────────────

    def get_athlete(self):
        return self._get(f"/athlete/{self.athlete_id}")

    def get_sport_settings(self):
        """功率区间、心率区间、配速区间、FTP/LTHR 等设置。"""
        return self._get(f"/athlete/{self.athlete_id}/sport-settings")

    # ── 健康数据 ────────────────────────────────────────────────────────────────

    def get_wellness(self, oldest, newest):
        """健康数据，含 CTL/ATL/TSB/eFTP 等训练负荷扩展字段。"""
        params = {
            "oldest": oldest,
            "newest": newest,
            "cols": "ctl,atl,rampRate,ctlLoad,atlLoad,eftp,hrv,restingHR,weight,sportInfo"
        }
        return self._get(f"/athlete/{self.athlete_id}/wellness", params=params)

    # ── 活动列表 ────────────────────────────────────────────────────────────────

    def get_activities(self, oldest, newest):
        return self._get(f"/athlete/{self.athlete_id}/activities",
                         params={"oldest": oldest, "newest": newest})

    # ── 活动详情 ────────────────────────────────────────────────────────────────

    def get_activity(self, activity_id):
        """活动详情，含 ICU 识别的结构化间歇段。"""
        return self._get(f"/activity/{activity_id}", params={"intervals": "true"})

    def get_activity_file(self, activity_id):
        """原始 FIT 文件（二进制）。"""
        return self._get_bytes(f"/activity/{activity_id}/file")

    def get_activity_streams(self, activity_id,
                             types="time,watts,heartrate,cadence,velocity_smooth,altitude,w_bal"):
        return self._get(f"/activity/{activity_id}/streams", params={"types": types})

    def get_power_histogram(self, activity_id):
        """单次活动的功率分布直方图。"""
        return self._get(f"/activity/{activity_id}/power-histogram")

    def get_hr_histogram(self, activity_id):
        """单次活动的心率分布直方图。"""
        return self._get(f"/activity/{activity_id}/hr-histogram")

    # ── 功率 / 心率曲线 ─────────────────────────────────────────────────────────

    # ICU 曲线接口忽略 start/end（会静默返回 1y），时间窗必须用 curves 指定，
    # 如 "90d" / "1y" / "all"。响应 list[0].id 与所请求的 curves 一致。

    def get_power_curves(self, curves="all", type="Ride"):
        params = {"type": type, "curves": curves}
        return self._get(f"/athlete/{self.athlete_id}/power-curves", params=params)

    def get_hr_curves(self, curves="all"):
        """心率最佳曲线（类似功率曲线）。"""
        return self._get(f"/athlete/{self.athlete_id}/hr-curves", params={"curves": curves})

    # ── 日历事件 / 训练计划 ─────────────────────────────────────────────────────

    def get_events(self, oldest, newest):
        """日历事件：计划训练、比赛、备注、目标等。"""
        return self._get(f"/athlete/{self.athlete_id}/events",
                         params={"oldest": oldest, "newest": newest, "resolve": "true"})

    def create_event(self, event_data):
        """在 ICU 日历上创建训练计划事件。"""
        path = f"/athlete/{self.athlete_id}/events"
        return self._request("POST", path, json=event_data).json()

    def delete_event(self, event_id):
        """删除指定 ICU 日历事件。"""
        path = f"/athlete/{self.athlete_id}/events/{event_id}"
        self._request("DELETE", path)

    def get_workouts(self):
        """训练模板库（已保存的 workout）。"""
        return self._get(f"/athlete/{self.athlete_id}/workouts")

    def update_event(self, event_id, event_data) -> dict:
        """更新 ICU 日历上指定的训练计划事件。

        发起 PUT /athlete/{athlete_id}/events/{event_id}，返回更新后的事件 JSON。
        `event_data` 应为完整事件载荷（PUT 语义，非 PATCH 局部更新）。
        """
        path = f"/athlete/{self.athlete_id}/events/{event_id}"
        return self._request("PUT", path, json=event_data).json()
