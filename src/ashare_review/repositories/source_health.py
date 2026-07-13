"""数据来源健康记录仓储。"""

from __future__ import annotations

from ashare_review.collectors.contracts import SourceHealthReport
from ashare_review.repositories.database import Database


class SourceHealthRepository:
    """保存每次采集尝试的来源健康状态。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def record(self, report: SourceHealthReport) -> int:
        """追加健康记录并返回数据库标识。"""
        with self._database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO source_health (
                    source_id, observed_at, status, records_fetched, error_type, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.source_id,
                    report.observed_at.isoformat(),
                    report.status.value,
                    report.records_fetched,
                    report.error_type,
                    report.error_message,
                ),
            )
        health_id = cursor.lastrowid
        if health_id is None:
            raise RuntimeError("来源健康记录写入后未返回标识")
        return health_id
