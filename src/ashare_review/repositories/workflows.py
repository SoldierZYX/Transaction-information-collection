"""工作流运行审计仓储。"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from typing import cast

from ashare_review.domain.workflows import (
    WorkflowRun,
    WorkflowRunClaim,
    WorkflowRunStatus,
    WorkflowType,
)
from ashare_review.repositories.database import Database


class WorkflowRunRepository:
    """用唯一运行键提供幂等的工作流获取与审计更新。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def claim(
        self,
        run_key: str,
        workflow_type: WorkflowType,
        target_date: date,
        *,
        force_run: bool = False,
    ) -> WorkflowRunClaim:
        """尝试获取运行权；已有运行键时返回已有记录。"""
        started_at = datetime.now(UTC)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO workflow_runs (
                        run_key, workflow_type, target_date, status, started_at, force_run
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_key,
                        workflow_type.value,
                        target_date.isoformat(),
                        WorkflowRunStatus.RUNNING.value,
                        started_at.isoformat(),
                        int(force_run),
                    ),
                )
            except sqlite3.IntegrityError:
                row = self._get_row(connection, run_key)
                connection.commit()
                return WorkflowRunClaim(workflow_run=self._to_workflow_run(row), acquired=False)

            row = connection.execute(
                "SELECT * FROM workflow_runs WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            connection.commit()

        if row is None:
            raise RuntimeError("工作流运行写入后未能读取")
        return WorkflowRunClaim(workflow_run=self._to_workflow_run(row), acquired=True)

    def finish(
        self,
        run_key: str,
        status: WorkflowRunStatus,
        *,
        failure_stage: str | None = None,
    ) -> WorkflowRun:
        """结束已有运行，并保存可审计的结束状态。"""
        if status is WorkflowRunStatus.RUNNING:
            raise ValueError("结束运行时不能使用 running 状态")

        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE workflow_runs
                SET status = ?, ended_at = ?, failure_stage = ?
                WHERE run_key = ?
                """,
                (status.value, datetime.now(UTC).isoformat(), failure_stage, run_key),
            )
            row = self._get_row(connection, run_key)
            connection.commit()
        return self._to_workflow_run(row)

    @staticmethod
    def _get_row(connection: sqlite3.Connection, run_key: str) -> sqlite3.Row:
        row = cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM workflow_runs WHERE run_key = ?", (run_key,)
            ).fetchone(),
        )
        if row is None:
            raise KeyError(f"不存在的工作流运行: {run_key}")
        return row

    @staticmethod
    def _to_workflow_run(row: sqlite3.Row) -> WorkflowRun:
        ended_at_value = row["ended_at"]
        return WorkflowRun(
            id=int(row["id"]),
            run_key=str(row["run_key"]),
            workflow_type=WorkflowType(str(row["workflow_type"])),
            target_date=date.fromisoformat(str(row["target_date"])),
            status=WorkflowRunStatus(str(row["status"])),
            started_at=datetime.fromisoformat(str(row["started_at"])),
            ended_at=(
                datetime.fromisoformat(str(ended_at_value)) if ended_at_value is not None else None
            ),
            failure_stage=str(row["failure_stage"]) if row["failure_stage"] is not None else None,
            force_run=bool(row["force_run"]),
        )
