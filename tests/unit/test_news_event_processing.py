"""新闻事件标准化、去重和证据关联测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from ashare_review.domain.records import RawRecord
from ashare_review.processors.news_events import NewsEventProcessor
from ashare_review.repositories.database import Database
from ashare_review.repositories.events import EventRepository
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.workflows.event_processing import EventProcessingWorkflow


def _workflow(tmp_path: Path) -> tuple[EventProcessingWorkflow, Database, RawRecordRepository]:
    """创建包含事件表的临时工作流。"""
    database = Database.from_path(tmp_path / "review.sqlite3")
    MigrationRunner(database, Path("migrations")).migrate()
    raw_records = RawRecordRepository(database)
    return (
        EventProcessingWorkflow(raw_records, EventRepository(database), NewsEventProcessor()),
        database,
        raw_records,
    )


def _news_record(external_id: str, title: str, published_at: datetime) -> RawRecord:
    """创建测试用新闻原始记录。"""
    return RawRecord(
        source_id="SRC-TEST-NEWS-001",
        external_id=external_id,
        record_type="news",
        content_hash=f"hash-{external_id}",
        payload={"title": title},
        captured_at=published_at + timedelta(minutes=1),
        published_at=published_at,
        url=f"https://example.test/{external_id}",
    )


def test_event_workflow_normalizes_titles_and_links_all_exact_evidence(tmp_path: Path) -> None:
    """同日标题只因空白或全半角不同的记录应归并为一个事件。"""
    workflow, database, raw_records = _workflow(tmp_path)
    published_at = datetime(2026, 7, 15, 1, tzinfo=UTC)
    raw_records.store(_news_record("news-1", "Ａ股  午间 快讯", published_at))
    raw_records.store(_news_record("news-2", "A股 午间 快讯", published_at + timedelta(minutes=5)))

    result = workflow.run_news()

    assert result.events_upserted == 1
    assert result.evidence_links_created == 2
    with database.connect() as connection:
        event = connection.execute("SELECT category, direction FROM events").fetchone()
        evidence_count = connection.execute("SELECT COUNT(*) FROM event_evidence").fetchone()[0]
    assert event is not None
    assert event["category"] == "news"
    assert event["direction"] == "neutral"
    assert evidence_count == 2


def test_event_workflow_keeps_same_title_on_different_days_separate(tmp_path: Path) -> None:
    """相同标题跨自然日时不合并，避免错误扩大证据范围。"""
    workflow, database, raw_records = _workflow(tmp_path)
    published_at = datetime(2026, 7, 14, 15, tzinfo=UTC)
    raw_records.store(_news_record("news-1", "每日快讯", published_at))
    raw_records.store(_news_record("news-2", "每日快讯", published_at + timedelta(hours=2)))

    workflow.run_news()
    repeated = workflow.run_news()

    assert repeated.evidence_links_created == 0
    with database.connect() as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        evidence_count = connection.execute("SELECT COUNT(*) FROM event_evidence").fetchone()[0]
    assert event_count == 2
    assert evidence_count == 2
