"""股票池、排除原因和评分明细的 SQLite 仓储。"""

from __future__ import annotations

import json
from datetime import date

from ashare_review.domain.pool import PoolCandidate, PoolExclusion
from ashare_review.repositories.database import Database


class PoolRepository:
    """保存可复现的股票池运行输入、候选和评分。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def create_run(
        self, workflow_run_id: int, target_date: date, rule_version: str, input_snapshot_hash: str
    ) -> int:
        """创建一次股票池运行并返回数据库标识。"""
        with self._database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO pool_runs (
                    workflow_run_id, target_date, rule_version, input_snapshot_hash
                )
                VALUES (?, ?, ?, ?)
                """,
                (workflow_run_id, target_date.isoformat(), rule_version, input_snapshot_hash),
            )
        if cursor.lastrowid is None:
            raise RuntimeError("股票池运行写入后未返回标识")
        return int(cursor.lastrowid)

    def store_exclusions(
        self, pool_run_id: int, exclusions: tuple[PoolExclusion, ...], rule_version: str
    ) -> int:
        """保存被排除的证券及其规则原因。"""
        with self._database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO pool_exclusions (pool_run_id, symbol, reason_code, rule_version)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (pool_run_id, symbol, reason_code) DO NOTHING
                """,
                [(pool_run_id, item.symbol, item.reason_code, rule_version) for item in exclusions],
            )
        return len(exclusions)

    def store_candidates(
        self, pool_run_id: int, candidates: tuple[PoolCandidate, ...], rule_version: str
    ) -> int:
        """保存候选及每个评分维度的输入快照。"""
        stored = 0
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for candidate in candidates:
                cursor = connection.execute(
                    """
                    INSERT INTO candidates (
                        pool_run_id, symbol, total_score, confidence,
                        rationale, conditions, invalidation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pool_run_id,
                        candidate.symbol,
                        candidate.total_score,
                        candidate.confidence,
                        candidate.rationale,
                        candidate.conditions,
                        candidate.invalidation,
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("候选写入后未返回标识")
                candidate_id = int(cursor.lastrowid)
                connection.executemany(
                    """
                    INSERT INTO candidate_scores (
                        candidate_id, component, score, inputs_json, rule_version
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            candidate_id,
                            component.component,
                            component.score,
                            json.dumps(component.inputs, sort_keys=True),
                            rule_version,
                        )
                        for component in candidate.components
                    ],
                )
                stored += 1
            connection.commit()
        return stored
