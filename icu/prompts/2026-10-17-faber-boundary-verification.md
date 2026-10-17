# Claude Code：核对Faber端点与官方PR，避免错误比较

这是同项目的算法协作提示词，不是已执行任务。按AGENTS/项目memory规则启动，bd任务Cycling-6pj；不要重写教练方案，不代报名或联系外部人员。用户已让教练自行查记录，勿重复索要能从现有数据提取的链接。

已知结果：`icu/analysis/2026-10-17-faber-pr-and-cp3-review.{json,md}`。2026年170条has_segments Ride中7次Faber，细节缓存`icu/icu_data_warehouse/9_Coach_Raw/2026-10-17-faber/scan.json`及各activity文件。两个主要段633867和6661458，10857144为同向重叠长起点。映射最快8/8 223s/9/8 226s，暂不能叫Strava官方PR。反向10/13映射距离1652–1668m，而9/8/10/6多1474–1481m。先查清这约180m差异来自GPS定位、路线实际变化、ICU跨源start_index映射，还是其他数据处理；不要把它当能力变化。

1. 只读现有文件；需要GPS时用现有ICU客户端取streams time,distance,latlng。latlng在本API常是`data`纬度、`data2`经度，长度均N，不是data中交错2N；先检查schema，不硬套格式。不要将经纬度或家附近完整路线写入共享产物、日志、prompt、Git。
2. 对同ID各次经过，检查起终点是否真的相近、记录停顿/elapsed与sample index关系、是否存在Garmin/Strava源流索引混用。可在本地比较端点和行进方向，建立统一地理门线或最近点法，并做端点±若干米的敏感性；GPS不够时明确不确定，不能伪造更精确的PR。
3. 如果合法现有接口确实提供Strava effort elapsed，优先核对；接口没有就标未知，不把ICU数组时间称官方PR，不需要绕过登录/CAPTCHA。
4. 复核三分钟只需确认395.05W窗[2637,2817)来自8/8Faber，对连续性/缺值已有验证；生涯420.88W[1540,1720)在6/10中国。不要将两者合并，不由rolling peak拟合新FTP。完整地理段长于180s，输出同一段PR与180s的分别指标。
5. 输出`icu/analysis/2026-10-17-faber-boundary-verification.{json,md}`：每次ID/日期、原映射与统一边界耗时/距离、定位误差、方法限制、官方PR是否可证。共享产物不含GPS，只含结果和本地源路径。不要修改生产源码或用户未提交文件。
6. 完成后更新bd状态，由教练再读结果调整目标。没有足够证据就保留不确定，不为“完成”强填一个时间。

DRCC GPX/资格属于另一任务Cycling-2v4；当前本任务不必联网重复广搜赛事。
