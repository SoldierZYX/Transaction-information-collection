"""本地日线驱动的股票池筛选与审计持久化测试。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ashare_review.analytics.pool_scoring import PoolRules, PoolScorer
from ashare_review.domain.market import MarketBar, Security
from ashare_review.repositories.database import Database
from ashare_review.repositories.market_data import MarketBarRepository, SecurityRepository
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.pool import PoolRepository
from ashare_review.repositories.workflows import WorkflowRunRepository
from ashare_review.workflows.pool_generation import PoolGenerationWorkflow


def _workflow(
    tmp_path: Path,
) -> tuple[PoolGenerationWorkflow, MarketBarRepository, SecurityRepository, Database]:
    """创建带完整初始迁移的股票池工作流。"""
    database = Database.from_path(tmp_path / "review.sqlite3")
    MigrationRunner(database, Path("migrations")).migrate()
    market_bars = MarketBarRepository(database)
    securities = SecurityRepository(database)
    return (
        PoolGenerationWorkflow(
            WorkflowRunRepository(database),
            securities,
            market_bars,
            PoolRepository(database),
            PoolScorer(),
        ),
        market_bars,
        securities,
        database,
    )


def _security(symbol: str, name: str, board: str = "main") -> Security:
    """创建测试用有效证券。"""
    return Security(
        symbol=symbol,
        exchange="SSE",
        name=name,
        board=board,
        active_from=date(2020, 1, 1),
        source_id="SRC-MANUAL-CSV-001",
    )


def _bars(symbol: str, target_date: date, count: int, amount: float) -> list[MarketBar]:
    """创建连续上涨的合格日线序列。"""
    start = target_date - timedelta(days=count - 1)
    return [
        MarketBar(
            trade_date=start + timedelta(days=index),
            symbol=symbol,
            open=10 + index * 0.1,
            high=10.2 + index * 0.1,
            low=9.9 + index * 0.1,
            close=10.1 + index * 0.1,
            volume=1_000_000 + index * 1_000,
            amount=amount,
            source_id="SRC-MANUAL-CSV-001",
        )
        for index in range(count)
    ]


def test_pool_generation_stores_candidates_scores_and_exclusions(tmp_path: Path) -> None:
    """合格日线生成候选，状态和历史不足证券保留排除审计。"""
    workflow, market_bars, securities, database = _workflow(tmp_path)
    target_date = date(2026, 7, 15)
    securities.upsert_many(
        [
            _security("600001", "测试股份"),
            _security("600002", "ST测试"),
            _security("600003", "历史不足"),
        ]
    )
    market_bars.upsert_many(_bars("600001", target_date, 21, 1_000_000_000))
    market_bars.upsert_many(_bars("600002", target_date, 21, 1_000_000_000))
    market_bars.upsert_many(_bars("600003", target_date, 20, 1_000_000_000))

    result = workflow.run(target_date, PoolRules())

    assert result.acquired is True
    assert result.evaluation is not None
    assert [candidate.symbol for candidate in result.evaluation.candidates] == ["600001"]
    assert {item.reason_code for item in result.evaluation.exclusions} == {
        "excluded_security_status",
        "insufficient_history",
    }
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM pool_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM candidate_scores").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM pool_exclusions").fetchone()[0] == 2


def test_pool_generation_is_idempotent_for_same_rule_version(tmp_path: Path) -> None:
    """同一日期和规则版本的重跑不会重复生成候选。"""
    workflow, market_bars, securities, database = _workflow(tmp_path)
    target_date = date(2026, 7, 15)
    securities.upsert_many([_security("600001", "测试股份")])
    market_bars.upsert_many(_bars("600001", target_date, 21, 1_000_000_000))

    first = workflow.run(target_date, PoolRules())
    repeated = workflow.run(target_date, PoolRules())

    assert first.acquired is True
    assert repeated.acquired is False
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 1
