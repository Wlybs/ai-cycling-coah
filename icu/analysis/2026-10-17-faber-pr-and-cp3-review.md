# 2026-10-17 Mount Faber 双向记录与三分钟功率复核

## 数据来源与方法
Ride activities 2026-01-01 to 2026-10-17 with has_segments; 170 segment files scanned, 7 Faber rides, no request errors
Mapped elapsed=time[end_index]-time[start_index]; watts uses [start,end), zeros included. Segment endpoints are those returned by ICU, not independently geospatially aligned or onset-shifted. Strict 180-s sample mean only with 1 Hz complete streams; no gap bridging. Not official Strava effort elapsed or certified all-time segment PR. GPS not published.

原始API活动/streams/segments保存在本地忽略目录 `icu/icu_data_warehouse/9_Coach_Raw/2026-10-17-faber/`。本文件及配套JSON不含GPS。ICU接口 `/activity/{id}/segments` 的 `segment_id,start_index,end_index` 给出ICU映射端点；不把间歇起爆检测移动应用于地理路段边界，也不声称端点已独立对齐。

注意：170条是 has_segments 的Ride，不是170次Faber；全年命中7次。未检出的路段或Strava官方effort更新可能影响真实PR，所以这里只称“已检索2026记录内最快映射时间”。普通间歇非全力，不能用10月训练成绩断言当下全力能力。

## 两方向最快已核实记录
|路段ID/名称|日期/活动|映射时间|路段样本均功率|段内best180|
|---|---|---|---|---|
|633867 Mt Faber Rd Climb (to top)|2026-08-08 / i173586493|3:43|373.2W|392.1W|
|6661458 RT FABER ascent|2026-09-08 / i184403505|3:46|350.5W|348.0W|

比较用同一ID；633867与6661458分别计，不混入下坡7174771/环线632841。10857144（Mount Faber to Faber Peak）为8/8同方向重叠段，起点更远，有停顿：映射elapsed512秒，不将290个索引样本当290秒。

## 三分钟基准
- Faber最高已核连续180s：2026-08-08 `i173586493`，索引[2637,2817)，time3186–3365，395.05W，180个连续1Hz有效样本，零值保留；与90d ICU曲线395W一致。
- 该功率窗比633867映射起点（index2641）早4秒。633867段内best180=392.11W；不能把395.05W写成该段起止范围内的180s。
- 账户all曲线源2026-06-10 `i156006343`：raw[1540,1720)连续180s420.88W，ICU显示420W；活动及坐标国家核实为中国，关联Longjing段31704186，不是Faber。GPS未放共享文件。
- 本轮没有将这些滚动窗口当运动员确认的正式180s测试，不拟合CP/W′/FTP，也不要求运动员重复提供已能从数据定位的链接。

## 最近变化（仅训练条件描述）
- 633867：8/8最快223s373.2W；9/8训练250s；10/6训练258s；10/13训练252s343.0W。
- 6661458：9/8最快226s350.5W；10/6最快230s345.6W；10/13最快261s321.4W。各组、条件及战术不同；尤其10/13反向映射1652–1668m，而9/8、10/6多为1474–1481m，存在端点匹配不一致，不能用耗时差量化能力下降。10/13本人已说明热湿霾，亦不能据此推当前全力能力。
- 8/8原始180s的三个60s均值422.08/409.07/354.00W；对应633867段内最后43s294.05W，地形也明显变缓。功率前高后低是观察，不证明配速错误或耗尽了某个无氧池。

## 教练解释
完整路段约3:43–3:46，CP3目标严格180s。两种纪录相关但不等价。第一阶段将Faber395.1W作为本地历史参照，420.9W保留为账户生涯参照，不把395错误叫生涯纪录，也不承诺八周必破任一。想兼顾可在一次完整PR尝试读取best180，若只破一种则另一次质量日再检验，不能同日反复补考。
测试要同功率计、同路线ID并标注环境、入段速度、前序负荷；不能把Strava时间的改善全部归为FTP提高。

详细处方：`vault/plans/2026-10-19-faber-and-drcc-eight-week.md`。

独立教练审查通过：质量日分配可行；已按审查补入路段匹配误差，未将映射最快当官方PR。
