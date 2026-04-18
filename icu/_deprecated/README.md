# _deprecated/

此目录存放早期一次性 / ad-hoc 探索脚本和临时数据。**已从主流程中移除，等待确认后删除**。

当前结构已稳定：
- 同步 / 分析 / 计划 统一走 `scripts/`（例如 `extract_ride_summary.py`、`analyze_rides.py`、`run_deep_analysis.py`）
- 教练日志写入改为手动编辑 `coach_memory/coach_log.md`，不再通过 `append_*.py` 一次性脚本追加

## 迁移清单

| 文件 | 处理方式 | 原因 |
|------|---------|------|
| `analyze_microbursts.py` | Deprecated | 一次性脚本；硬编码功率阈值 50W 的起脚/滑行块分析，未模块化。深度分析能力已由 `scripts/run_deep_analysis.py` + `src/analyzer/` 覆盖。 |
| `analyze_microbursts_v2.py` | Deprecated | 同上，且硬编码特定 ride 文件路径（`2026-04-12_i139065650.json`）。纯 ad-hoc。 |
| `analyze_recent.py` | Deprecated | 硬编码 5 个 ride_id，循环调用 `scripts/extract_ride_summary.py` 打印。已被 `scripts/analyze_rides.py` 替代。 |
| `append_aerobic_rules.py` | Deprecated | 一次性脚本：把固定的 2026-04-13 有氧法则文本追加到 `coach_memory/coach_log.md`。内容已写入，脚本不再需要。 |
| `append_log.py` | Deprecated | 同上，追加 2026-04-13 龙井 VO2max 复盘文本，已写入。 |
| `append_lsd_log.py` | Deprecated | 同上，追加 2026-04-13 LSD 锚点文本，已写入。 |
| `get_lap_info.py` | Deprecated | 硬编码 ride_id `i139065650`，调用 `extract_ride_summary.py` 打印 laps / intervals。直接调 `extract_ride_summary.py <id>` 即可。 |
| `print_icu.py` | Deprecated | 硬编码同一个 ride 文件，打印 ICU 间歇段。`extract_ride_summary.py` 已输出同内容。 |
| `print_laps.py` | Deprecated | 硬编码 6 个 ride_id 打印 laps。用 `analyze_rides.py` 或直接调 `extract_ride_summary.py` 替代。 |
| `print_summaries.py` | Deprecated | 依赖 `latest_6_rides.json`（UTF-16 临时 dump）。数据源已不再维护。 |
| `latest_6_rides.json` | Deprecated | 一次性数据 dump（UTF-16，165KB）。不应 check-in。 |
| `temp_summary.json` | Deprecated | 临时调试 dump（24KB）。 |

## 处置建议

确认无历史回溯需求后：

```bash
rm -rf /mnt/d/Cycling/icu/_deprecated
```

如需保留历史记录，可打 tag 后再删除：

```bash
git tag legacy-scripts-archived-2026-04-18
rm -rf /mnt/d/Cycling/icu/_deprecated
git commit -am "chore: remove archived legacy scripts"
```
