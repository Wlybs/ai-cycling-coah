"""
ICU 全量数据同步编排器。

用法:
  python sync_data.py          # 同步所有数据，活动详情默认最新 1 条
  python sync_data.py 5        # 同步最新 5 条活动详情
  python sync_data.py 10 60    # 同步最近 60 天内最新 10 条活动详情
"""
import sys
import os
import subprocess

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable

failures = []


def run_script(script_name, args=None):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print(f"\n{'='*8} {script_name} {'='*8}")
    cmd = [PYTHON_EXE, script_path] + (args or [])
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 运行失败: {e}")
        failures.append(script_name)


def main():
    print("🚀 启动 ICU 全量同步...")

    # 1. 运动员基础信息
    run_script("sync_profile.py")
    run_script("sync_sport_settings.py")

    # 2. 健康 & 训练负荷
    run_script("sync_wellness.py")

    # 3. 性能曲线
    run_script("sync_power_curves.py")

    # 4. 活动数据
    run_script("sync_activities_list.py")

    # 5. 活动详情（透传参数：数量 + 天数）
    detail_args = sys.argv[1:]
    run_script("sync_activity_detail.py", detail_args)

    # 6. 日历事件（计划训练）
    run_script("sync_events.py")

    # 7. 刷新 Coach 记忆
    run_script("build_memory.py")

    # 8. Phase 1 — physiology refresh (soft-fail)
    run_script("refresh_physiology.py")

    # 9. Phase 1 — deep analysis (soft-fail)
    run_script("run_deep_analysis.py")

    # 10. Phase 1 — Coach Brief update (soft-fail)
    run_script("update_coach_brief.py")

    # ---------------------------------------------------------------
    # Phase 3 tail integration (steps 11–13)
    # PHASE_1_2_IMMUTABILITY allowance per docs/superpowers/plans/
    # phase-3/00-index.md decision lock #2: this is the ONE permitted
    # extension point — append-only after step 10, before failures
    # summary. Each step is soft-fail; Phase 1/2 sync never goes red
    # because of Phase 3 (per 00-index.md execution rule #8).
    # ---------------------------------------------------------------
    from datetime import datetime, timezone
    REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
    MEMORY_DIR = os.path.join(REPO_ROOT, "coach_memory")
    WAREHOUSE_DIR = os.path.join(REPO_ROOT, "icu_data_warehouse")
    TODAY = datetime.now(timezone.utc).date().isoformat()

    # 11. Phase 3 — Ledger ingester (back-fill from Phase 2 artefacts)
    run_script("ingest_ledger.py",
               ["--memory", MEMORY_DIR, "--warehouse", WAREHOUSE_DIR])

    # 12. Phase 3 — Daily adaptation (4-signal evaluation)
    run_script("daily_adapt.py",
               ["--date", TODAY,
                "--memory", MEMORY_DIR, "--warehouse", WAREHOUSE_DIR])

    if failures:
        print(f"\n⚠️  同步完成，但 {len(failures)} 个脚本失败:")
        for f in failures:
            print(f"   ✗ {f}")
    else:
        print("\n🎉 全量同步完成！")


if __name__ == "__main__":
    main()
