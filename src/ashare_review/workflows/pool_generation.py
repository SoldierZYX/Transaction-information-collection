"""股票池筛选、评分与审计持久化工作流。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ashare_review.analytics.pool_scoring import PoolRules, PoolScorer
from ashare_review.domain.pool import PoolEvaluation
from ashare_review.domain.workflows import WorkflowRunStatus, WorkflowType
from ashare_review.repositories.market_data import MarketBarRepository, SecurityRepository
from ashare_review.repositories.pool import PoolRepository
from ashare_review.repositories.workflows import WorkflowRunRepository


@dataclass(frozen=True)
class PoolGenerationResult:
    """一次股票池生成的审计结果。"""

    acquired: bool
    pool_run_id: int | None
    evaluation: PoolEvaluation | None


class PoolGenerationWorkflow:
    """用唯一运行键保证股票池筛选和评分可重复执行。"""

    def __init__(
        self,
        workflow_runs: WorkflowRunRepository,
        securities: SecurityRepository,
        market_bars: MarketBarRepository,
        pool_repository: PoolRepository,
        scorer: PoolScorer,
    ) -> None:
        self._workflow_runs = workflow_runs
        self._securities = securities
        self._market_bars = market_bars
        self._pool_repository = pool_repository
        self._scorer = scorer

    def run(self, target_date: date, rules: PoolRules) -> PoolGenerationResult:
        """筛选股票池，保存输入哈希、排除原因和评分明细。"""
        run_key = f"pool:{target_date.isoformat()}:{rules.rule_version}"
        claim = self._workflow_runs.claim(run_key, WorkflowType.PREMARKET, target_date)
        if not claim.acquired:
            return PoolGenerationResult(acquired=False, pool_run_id=None, evaluation=None)

        try:
            securities = self._securities.list_active_on(target_date)
            bars = self._market_bars.list_until(target_date)
            evaluation = self._scorer.evaluate(target_date, securities, bars, rules)
            pool_run_id = self._pool_repository.create_run(
                claim.workflow_run.id,
                target_date,
                rules.rule_version,
                self._input_snapshot_hash(securities, bars, target_date),
            )
            self._pool_repository.store_exclusions(
                pool_run_id, evaluation.exclusions, rules.rule_version
            )
            self._pool_repository.store_candidates(
                pool_run_id, evaluation.candidates, rules.rule_version
            )
            self._workflow_runs.finish(run_key, WorkflowRunStatus.COMPLETED)
        except Exception:
            self._workflow_runs.finish(
                run_key, WorkflowRunStatus.FAILED, failure_stage="pool_generation"
            )
            raise
        return PoolGenerationResult(acquired=True, pool_run_id=pool_run_id, evaluation=evaluation)

    @staticmethod
    def _input_snapshot_hash(
        securities: Sequence[object], bars: Sequence[object], target_date: date
    ) -> str:
        """生成数据对象的稳定快照哈希，供后续复算审计。"""
        payload = {
            "target_date": target_date.isoformat(),
            "securities": [str(item) for item in securities],
            "bars": [str(item) for item in bars],
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()
