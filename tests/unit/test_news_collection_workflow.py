"""新闻采集、简报与邮件交付的离线测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.collectors.runner import CollectorRunner
from ashare_review.delivery.email import EmailReportSender
from ashare_review.domain.records import RawRecord
from ashare_review.reports.news_brief import NewsBriefWriter
from ashare_review.repositories.database import Database
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.source_health import SourceHealthRepository
from ashare_review.workflows.news_collection import NewsCollectionWorkflow


class StaticCollector:
    """返回固定快讯的采集器替身。"""

    source_id = "SRC-TEST-NEWS-001"

    def __init__(self, records: list[RawRecord]) -> None:
        self._records = records

    def fetch(self, window: CollectionWindow) -> list[RawRecord]:
        """返回预设记录。"""
        return self._records


class BrokenCollector:
    """始终失败的采集器替身。"""

    source_id = "SRC-TEST-NEWS-001"

    def fetch(self, window: CollectionWindow) -> list[RawRecord]:
        """模拟来源不可用。"""
        raise TimeoutError("模拟超时")


class RecordingMailTransport:
    """记录邮件而不连接 SMTP 服务。"""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        """保存待发送邮件以便断言。"""
        self.messages.append(message)


def _workflow(tmp_path: Path) -> tuple[NewsCollectionWorkflow, Database]:
    """创建带迁移的新闻工作流和临时数据库。"""
    database = Database.from_path(tmp_path / "review.sqlite3")
    MigrationRunner(database, Path("migrations")).migrate()
    return (
        NewsCollectionWorkflow(
            CollectorRunner(),
            RawRecordRepository(database),
            SourceHealthRepository(database),
            NewsBriefWriter(),
        ),
        database,
    )


def test_news_workflow_persists_records_and_writes_metadata_report(tmp_path: Path) -> None:
    """成功采集会幂等落库并创建不含正文的 Markdown 简报。"""
    workflow, database = _workflow(tmp_path)
    now = datetime(2026, 7, 14, 3, tzinfo=UTC)
    record = RawRecord(
        source_id="SRC-TEST-NEWS-001",
        external_id="news-1",
        record_type="news",
        content_hash="hash-1",
        payload={"title": "测试快讯"},
        captured_at=now,
        published_at=now - timedelta(minutes=1),
        url="https://example.test/news-1",
    )
    window = CollectionWindow(starts_at=now - timedelta(hours=1), ends_at=now)

    result = workflow.run(
        StaticCollector([record]),
        window,
        source_name="36Kr",
        generated_at=now,
        reports_dir=tmp_path / "reports",
    )

    assert result.report is not None
    assert result.report.record_count == 1
    content = result.report.path.read_text(encoding="utf-8")
    assert "[测试快讯](https://example.test/news-1)" in content
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0] == 1
        assert connection.execute("SELECT status FROM source_health").fetchone()[0] == "healthy"


def test_news_workflow_records_failure_without_writing_report(tmp_path: Path) -> None:
    """采集失败会记录健康状态，但不会生成误导性的空报告。"""
    workflow, database = _workflow(tmp_path)
    now = datetime(2026, 7, 14, 3, tzinfo=UTC)

    result = workflow.run(
        BrokenCollector(),
        CollectionWindow(starts_at=now - timedelta(hours=1), ends_at=now),
        source_name="36Kr",
        generated_at=now,
        reports_dir=tmp_path / "reports",
    )

    assert result.report is None
    assert result.health.error_type == "TimeoutError"
    with database.connect() as connection:
        assert connection.execute("SELECT status FROM source_health").fetchone()[0] == "unavailable"


def test_email_sender_attaches_markdown_report(tmp_path: Path) -> None:
    """邮件发送器将本地简报作为 Markdown 附件交给传输层。"""
    report_path = tmp_path / "36kr.md"
    report_path.write_text("# 简报\n", encoding="utf-8")
    transport = RecordingMailTransport()
    sender = EmailReportSender(transport, "sender@example.test", ("user@example.test",))

    sender.send_markdown_report(report_path, subject="测试简报")

    assert len(transport.messages) == 1
    message = transport.messages[0]
    attachment = next(message.iter_attachments())
    assert attachment.get_filename() == "36kr.md"
    assert attachment.get_content_type() == "text/markdown"
