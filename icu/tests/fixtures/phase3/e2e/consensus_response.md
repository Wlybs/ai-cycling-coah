<planner>
本周 plan_period 2026-W17 BUILD 阶段：
- Tue VO2max 75 min @ 110% FTP（5×4min on / 3min off）
- Thu Threshold 90 min @ 95% FTP（3×16min on / 5min off）
- Sat Long 180 min @ 65% FTP zone 2

数值依据：(1) 周 TSS 380 与 CTL 65 相符（target 5–6× CTL）；(2) HARD 日 2 次匹配 BUILD 配额下限。
</planner>

<critic>
关键反对：

1. **HARD 日数仅达底线**（数据：BUILD 阶段配额 2–3 次，本周 2 次 = 底线；上周 stimulus_score 0.30 在下滑）。建议加 1 次 race-sim sub-Threshold session 替换 Fri Endurance。
2. **VO2max 工作时长偏低**（数据：5×4 = 20 min，response_profile.types.VO2max.tolerance_class=high 应配 22–24 min）。建议升至 6×4 min。
3. **Sat Long 强度模糊**（数据：180 min @ 65% FTP 没有任何 surge / over-under 段，与 race profile 不一致）。建议在 Long 中段加 3×8min @ 90% FTP 段。
</critic>

<physiologist>
- CP=288W, W'=18000J, durability decay 60s=1.5%/1000kJ — 高强度耐受良好。
- response_profile.types.VO2max.tolerance_class=high 支持 6×4min 升级。
- W' balance 周末估算（Sat 180min long 含 surge）可控制在 −40% 内不破红线。
- knee_flag=false，无关节风险护栏触发。
</physiologist>

<arbiter>
verdict: REVISE
confidence: 0.78
justification: VO2max 工作时长偏低 + HARD 日数不足，建议本周补齐到 22 min + 加一次 race-sim。
revisions:
- day: Tue, from: "5×4min @110%", to: "6×4min @110%"
- day: Fri, from: "Endurance 60min", to: "Threshold sub 75min @92% FTP"
</arbiter>

<summary_json>
{
  "verdict": "REVISE",
  "confidence": 0.78,
  "justification": "VO2max 工作时长偏低 + HARD 日数不足；建议补齐 22 min + 加一次 race-sim。",
  "critic_hard_points": [
    "HARD 日数仅达底线",
    "VO2max 工作时长偏低",
    "Sat Long 强度模糊"
  ],
  "physiologist_keywords_used": ["CP", "W'", "durability", "response_profile"],
  "revisions": [
    {"day": "Tue", "from": "5×4min @110%", "to": "6×4min @110%"},
    {"day": "Fri", "from": "Endurance 60min",
     "to": "Threshold sub 75min @92% FTP"}
  ]
}
</summary_json>
