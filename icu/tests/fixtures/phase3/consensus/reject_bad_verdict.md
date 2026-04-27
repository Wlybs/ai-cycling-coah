<planner>
本周训练目标：BUILD 阶段第 2 周，2 次 HARD（VO2 + Threshold）+ 1 次 endurance long ride，目标周 TSS=480。
依据：CTL=72.3、phase=BUILD、weekly_plan.total_tss=480。
</planner>

<critic>
1. 周 HARD 仅排了 1 次，违反 BUILD 阶段 2 次底线（weekly_plan.hard_days=1，target=2）。
2. VO2max 工作间总时长 14 min，低于 high tolerance 18 min 底线（response_profile.types.VO2max.tolerance_class=high）。
3. 周三 Threshold session 持续 60min，对应 IF=0.92 偏高（IF=0.92 vs target 0.88）。
</critic>

<physiologist>
当前 CP=288W，W'=18500J，durability decay 60s ≈ 6%/1000kJ；response_profile.types.VO2max.tolerance_class=high。
周末 W' balance 预估 −45%，knee_flag 当前为 false。
</physiologist>

<arbiter>
REVISE — 调整周二 Endurance 为 VO2max session 以补足 HARD 配额。confidence 0.72。
</arbiter>

<summary_json>
{
  "verdict": "MAYBE",
  "confidence": 0.72,
  "critic_hard_points": [
    "weekly_plan.hard_days=1 vs target 2",
    "VO2 work_min=14 vs floor 18",
    "Threshold IF=0.92 vs target 0.88"
  ],
  "changes": [
    {"day": "Tue", "from": "Endurance", "to": "VO2max"}
  ]
}
</summary_json>
