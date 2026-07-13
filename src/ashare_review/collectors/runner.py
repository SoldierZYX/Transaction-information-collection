"""采集器运行与来源健康记录。"""

from __future__ import annotations

from datetime import UTC, datetime

from ashare_review.collectors.contracts import (
    CollectionWindow,
    Collector,
    SourceHealthReport,
    SourceHealthStatus,
)
from ashare_review.domain.records import RawRecord


class CollectorRunner:
    """执行单个采集器，并生成不泄露敏感信息的健康报告。"""

    def collect(
        self, collector: Collector, window: CollectionWindow
    ) -> tuple[list[RawRecord], SourceHealthReport]:
        """运行采集器；失败时返回空记录和不可用状态。"""
        observed_at = datetime.now(UTC)
        try:
            records = collector.fetch(window)
        except Exception as error:
            return [], SourceHealthReport(
                source_id=collector.source_id,
                observed_at=observed_at,
                status=SourceHealthStatus.UNAVAILABLE,
                records_fetched=0,
                error_type=type(error).__name__,
                error_message="采集失败，详见本地结构化诊断记录",
            )

        return records, SourceHealthReport(
            source_id=collector.source_id,
            observed_at=observed_at,
            status=SourceHealthStatus.HEALTHY,
            records_fetched=len(records),
        )
