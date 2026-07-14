"""新闻来源采集、落库与简报交付工作流。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ashare_review.collectors.contracts import CollectionWindow, Collector, SourceHealthReport
from ashare_review.collectors.runner import CollectorRunner
from ashare_review.domain.records import RawRecord
from ashare_review.reports.news_brief import NewsBriefReport, NewsBriefWriter
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.source_health import SourceHealthRepository


@dataclass(frozen=True)
class NewsCollectionResult:
    """一次新闻采集、落库和简报生成的结果。"""

    records: tuple[RawRecord, ...]
    health: SourceHealthReport
    report: NewsBriefReport | None


class NewsCollectionWorkflow:
    """运行单一新闻来源，并将成功采集的结果落库和生成简报。"""

    def __init__(
        self,
        runner: CollectorRunner,
        raw_record_repository: RawRecordRepository,
        source_health_repository: SourceHealthRepository,
        report_writer: NewsBriefWriter,
    ) -> None:
        self._runner = runner
        self._raw_record_repository = raw_record_repository
        self._source_health_repository = source_health_repository
        self._report_writer = report_writer

    def run(
        self,
        collector: Collector,
        window: CollectionWindow,
        *,
        source_name: str,
        generated_at: datetime,
        reports_dir: Path,
    ) -> NewsCollectionResult:
        """采集后记录健康状态；成功时幂等落库并生成简报。"""
        records, health = self._runner.collect(collector, window)
        self._source_health_repository.record(health)
        if health.error_type is not None:
            return NewsCollectionResult(records=(), health=health, report=None)

        for record in records:
            self._raw_record_repository.store(record)
        report = self._report_writer.write(
            records,
            source_name=source_name,
            generated_at=generated_at,
            reports_dir=reports_dir,
        )
        return NewsCollectionResult(records=tuple(records), health=health, report=report)
