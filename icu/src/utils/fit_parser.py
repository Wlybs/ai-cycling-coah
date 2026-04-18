import gzip
import io
import fitdecode

def parse_fit_laps(fit_content):
    """
    解析 FIT 文件并提取计圈数据。
    支持 .gz 压缩格式。
    """
    laps = []
    try:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(fit_content)) as gz:
                fit_data = gz.read()
        except Exception:
            fit_data = fit_content

        with fitdecode.FitReader(io.BytesIO(fit_data)) as fit:
            lap_counter = 0
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == 'lap':
                    lap_counter += 1
                    start_time = frame.get_value('start_time')
                    laps.append({
                        "lap_number": lap_counter,
                        "duration_sec": frame.get_value('total_elapsed_time'),
                        "avg_watts": frame.get_value('avg_power'),
                        "avg_hr": frame.get_value('avg_heart_rate'),
                        "avg_cadence": frame.get_value('avg_cadence'),
                        "max_watts": frame.get_value('max_power'),
                        "timestamp_iso": start_time.isoformat() if start_time else None
                    })
    except Exception as e:
        print(f"FIT parsing error: {e}")
        return []
    return laps
