"""构建/刷新 Coach 记忆 + 趋势分析 + 计划执行评估。在同步数据后运行。

管道:
  build_memory.py
    ├── memory_builder.build_all()   → athlete_snapshot, training_history, fitness_trend
    ├── trend_analyzer.run_analysis()→ training_analysis (含 recovery_alerts / race_readiness)
    └── plan_evaluator.evaluate_plan() → plan_adherence (如果 reports/ 存在计划)

每一步都捕获异常并继续，保证下游步骤不被上游错误阻断。
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.common import setup_encoding

setup_encoding()


def _safe(step_name, fn):
    try:
        fn()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        print(f"\n❌ {step_name} 失败: {exc}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    from src.coach.memory_builder import build_all
    from src.analyzer.trend_analyzer import run_analysis
    from src.coach.plan_evaluator import evaluate_plan

    results = {
        "memory": _safe("memory_builder", build_all),
    }
    print()
    results["analysis"] = _safe("trend_analyzer", run_analysis)
    print()
    print("📝 计划执行评估...")
    results["adherence"] = _safe("plan_evaluator", evaluate_plan)
    print()
    bad = [k for k, v in results.items() if not v]
    if bad:
        print(f"⚠️  以下步骤出错: {', '.join(bad)}。请查看日志。")
        sys.exit(1)
    print("🎯 所有步骤完成。")
