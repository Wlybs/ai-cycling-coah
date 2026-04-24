"""训练计划生成（API-free）+ ICU 日历同步入口。

用法:
  # 生成 prompt 文件（不调用任何 LLM API；默认保存到 coach_memory/plans/）
  python scripts/push_plan.py
  python scripts/push_plan.py --week 2026-03-16   # 指定某周（输入任一周内日期）

  # 拿到 LLM 返回的结构化计划 JSON（用户手动保存的文本文件）后：
  python scripts/push_plan.py --push --plan-file path/to/plan.json
  python scripts/push_plan.py --push --plan-file path/to/plan.json --delete-existing

流程:
  1) 运行 `push_plan.py`（无参数）→ 生成 prompt 文件
  2) 用户复制 prompt 内容到 Gemini CLI / Claude Code 教练模式
  3) 将教练返回的结构化 JSON 保存为文本文件
  4) 运行 `push_plan.py --push --plan-file <file>` 推送到 ICU 日历
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.common import setup_encoding
from src.coach.plan_generator import (
    generate_plan,
    push_plan_from_file,
    delete_plan_events,
    _next_week_range,
)

setup_encoding()


def parse_args():
    parser = argparse.ArgumentParser(description="训练计划 prompt 生成 + ICU 推送（API-free）")
    parser.add_argument("--push", action="store_true",
                        help="推送已有计划 JSON 到 ICU 日历（需配合 --plan-file）")
    parser.add_argument("--plan-file", dest="plan_file",
                        help="用户保存的 LLM 计划 JSON 文件路径，供 --push 使用")
    parser.add_argument("--delete-existing", action="store_true",
                        help="推送前删除目标周内已有 WORKOUT 事件")
    parser.add_argument("--week",
                        help="指定周（任一该周日期 YYYY-MM-DD）")
    parser.add_argument(
        "--engine",
        choices=["v1", "v2"],
        default="v1",
        help="计划生成引擎：v1=legacy generate_plan（默认，prompt 文件）；v2=generate_plan_v2（Phase 2 API-free 完整流水线，失败自动回退 v1）",
    )
    return parser.parse_args()


def _resolve_week(args):
    if args.week:
        try:
            ref_date = datetime.strptime(args.week, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ 日期格式错误，应为 YYYY-MM-DD: {args.week}")
            sys.exit(1)
        monday = ref_date - timedelta(days=ref_date.weekday())
        return monday, monday + timedelta(days=6)
    return _next_week_range()


def _run_v2_engine(week_start, week_end) -> bool:
    """Run the Phase 2 generate_plan_v2 pipeline.

    Returns True on success (plan artifacts written under reports_dir).
    Returns False if the v2 engine returned status=="error" — caller should
    fall back to v1.
    """
    # Lazy import so v1 default path has no new dependency
    from pathlib import Path
    from src.coach.session_designer.generator_v2 import generate_plan_v2

    project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    warehouse_dir = project_root / "icu_data_warehouse"
    memory_dir = project_root / "coach_memory"
    reports_dir = project_root / "coach_memory" / "plans"

    result = generate_plan_v2(
        week_start=week_start,
        week_end=week_end,
        warehouse_dir=warehouse_dir,
        memory_dir=memory_dir,
        reports_dir=reports_dir,
        push_to_icu=False,
    )
    if result.status != "ok":
        print(f"⚠️  v2 engine failed ({result.error}); falling back to v1", file=sys.stderr)
        return False
    print(f"✅ v2 plan generated: {result.plan_md_path}")
    print(f"   prose prompt: {result.prose_prompt_path}")
    print(f"   trace: {result.trace_path}")
    if result.violations:
        print(f"   remaining violations: {len(result.violations)}", file=sys.stderr)
    return True


def main():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    args = parse_args()
    week_start, week_end = _resolve_week(args)

    if args.push:
        if not args.plan_file:
            print("❌ --push 需要配合 --plan-file <path>（LLM 返回的结构化计划 JSON）")
            sys.exit(1)
        if not os.path.exists(args.plan_file):
            print(f"❌ 找不到计划文件: {args.plan_file}")
            sys.exit(1)

        print(f"计划周期: {week_start} 至 {week_end}")
        if args.delete_existing:
            print("\n🗑️  删除已有计划事件...")
            delete_plan_events(week_start, week_end)

        push_plan_from_file(args.plan_file)
        return

    # 默认：生成计划，不推送。
    print(f"计划周期: {week_start} 至 {week_end}")
    if args.engine == "v2":
        if _run_v2_engine(week_start, week_end):
            return
        # else: fall through to v1
    generate_plan(week_start=week_start, week_end=week_end)


if __name__ == "__main__":
    main()
