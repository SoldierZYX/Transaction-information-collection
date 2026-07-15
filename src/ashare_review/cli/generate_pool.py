"""执行本地 CSV 行情驱动的股票池筛选与评分。"""

from __future__ import annotations

import argparse
import json
from datetime import date

from ashare_review.analytics.pool_scoring import PoolRules, PoolScorer
from ashare_review.config.settings import get_settings
from ashare_review.repositories.database import Database
from ashare_review.repositories.market_data import MarketBarRepository, SecurityRepository
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.pool import PoolRepository
from ashare_review.repositories.workflows import WorkflowRunRepository
from ashare_review.workflows.pool_generation import PoolGenerationWorkflow


def main() -> int:
    """生成一次股票池；缺少本地日线时只返回明确错误。"""
    settings = get_settings()
    database = Database(settings.database_url)
    MigrationRunner(database).migrate()
    target_date = _target_date(MarketBarRepository(database))
    if target_date is None:
        print(json.dumps({"status": "failed", "message": "未导入日线行情 CSV"}, ensure_ascii=False))
        return 1
    rules = PoolRules(
        min_previous_day_amount_cny=settings.pool_min_previous_day_amount_cny,
        max_candidates=settings.pool_max_candidates,
        include_chinext=settings.pool_include_chinext,
    )
    result = PoolGenerationWorkflow(
        WorkflowRunRepository(database),
        SecurityRepository(database),
        MarketBarRepository(database),
        PoolRepository(database),
        PoolScorer(),
    ).run(target_date, rules)
    if not result.acquired:
        print(
            json.dumps({"status": "skipped", "message": "相同规则版本已运行"}, ensure_ascii=False)
        )
        return 0
    if result.evaluation is None or result.pool_run_id is None:
        raise RuntimeError("股票池运行未返回结果")
    print(
        json.dumps(
            {
                "status": "completed",
                "target_date": target_date.isoformat(),
                "pool_run_id": result.pool_run_id,
                "candidates": [item.symbol for item in result.evaluation.candidates],
                "exclusions": len(result.evaluation.exclusions),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _target_date(repository: MarketBarRepository) -> date | None:
    """允许使用可选日期参数，否则使用已导入的最新交易日。"""
    parser = argparse.ArgumentParser(description="基于本地 CSV 日线生成股票池")
    parser.add_argument("--date", type=date.fromisoformat, help="目标交易日，格式 YYYY-MM-DD")
    arguments = parser.parse_args()
    return arguments.date or repository.latest_trade_date()


if __name__ == "__main__":
    raise SystemExit(main())
