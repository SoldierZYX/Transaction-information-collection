"""执行 36Kr 快讯采集并生成简报的命令行入口。"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.collectors.http import SafeHttpClient, UrllibTransport
from ashare_review.collectors.resilience import (
    MinimumIntervalRateLimiter,
    RetryExecutor,
    RetryPolicy,
)
from ashare_review.collectors.runner import CollectorRunner
from ashare_review.collectors.sources.kr36 import Kr36RssCollector
from ashare_review.config.settings import Settings, get_settings
from ashare_review.delivery.email import EmailReportSender, SmtpEmailTransport
from ashare_review.reports.news_brief import NewsBriefWriter
from ashare_review.repositories.database import Database
from ashare_review.repositories.locks import TaskLockRepository
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.source_health import SourceHealthRepository
from ashare_review.workflows.locking import TaskLease
from ashare_review.workflows.news_collection import NewsCollectionWorkflow


def main() -> int:
    """运行一次 36Kr 快讯采集，成功时生成本地简报。"""
    arguments = _parse_arguments()
    settings = get_settings()
    database = Database(settings.database_url)
    MigrationRunner(database).migrate()

    now = datetime.now(UTC)
    window = CollectionWindow(starts_at=now - timedelta(hours=arguments.hours), ends_at=now)
    http_client = SafeHttpClient(
        UrllibTransport(),
        RetryExecutor(RetryPolicy(max_attempts=settings.collection_max_attempts)),
        MinimumIntervalRateLimiter(settings.collection_minimum_interval_seconds),
        timeout_seconds=settings.collection_timeout_seconds,
    )
    workflow = NewsCollectionWorkflow(
        CollectorRunner(),
        RawRecordRepository(database),
        SourceHealthRepository(database),
        NewsBriefWriter(),
    )
    collector = Kr36RssCollector(http_client, captured_at=now)

    try:
        with TaskLease(
            TaskLockRepository(database),
            "collect:36kr-newsflash",
            owner_id=str(uuid.uuid4()),
            ttl=timedelta(minutes=10),
        ):
            result = workflow.run(
                collector,
                window,
                source_name="36Kr",
                generated_at=now,
                reports_dir=settings.reports_dir,
            )
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False))
        return 1

    if result.report is None:
        print(
            json.dumps(
                {"status": "failed", "message": result.health.error_message}, ensure_ascii=False
            )
        )
        return 1

    try:
        delivery_status = _send_email_if_enabled(settings, result.report.path, now)
    except Exception as error:
        delivery_status = f"failed:{type(error).__name__}"
    print(
        json.dumps(
            {
                "status": "completed",
                "records": len(result.records),
                "report_path": str(result.report.path),
                "email": delivery_status,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _parse_arguments() -> argparse.Namespace:
    """读取采集时间窗口参数。"""
    parser = argparse.ArgumentParser(description="采集 36Kr 官方 RSS 快讯并生成简报")
    parser.add_argument("--hours", type=int, default=24, help="采集最近多少小时，默认 24")
    arguments = parser.parse_args()
    if arguments.hours <= 0:
        parser.error("--hours 必须大于 0")
    return arguments


def _send_email_if_enabled(settings: Settings, report_path: Path, generated_at: datetime) -> str:
    """仅在完整邮件配置启用后发送简报，否则明确返回未启用状态。"""
    if not settings.email_enabled:
        return "disabled"
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise ValueError("邮件已启用，但 SMTP 主机、用户名或授权码未配置")
    recipients = tuple(
        address.strip()
        for address in (settings.smtp_recipients or "").split(",")
        if address.strip()
    )
    sender = EmailReportSender(
        SmtpEmailTransport(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password.get_secret_value(),
            use_ssl=settings.smtp_use_ssl,
        ),
        settings.smtp_username,
        recipients,
    )
    sender.send_markdown_report(report_path, subject=f"36Kr 快讯简报 {generated_at:%Y-%m-%d}")
    return "sent"


if __name__ == "__main__":
    raise SystemExit(main())
