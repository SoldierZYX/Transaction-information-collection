"""SQLite 迁移与幂等仓储的集成测试。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from ashare_review.domain.records import RawRecord
from ashare_review.domain.workflows import WorkflowRunStatus, WorkflowType
from ashare_review.repositories.database import Database
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.workflows import WorkflowRunRepository


def _migrated_database(tmp_path: Path) -> Database:
    """创建已应用初始迁移的临时 SQLite 数据库。"""
    database = Database.from_path(tmp_path / "ashare_review.sqlite3")
    result = MigrationRunner(database, Path("migrations")).migrate()

    assert result.applied_versions == (1,)
    assert MigrationRunner(database, Path("migrations")).migrate().applied_versions == ()
    return database


def test_initial_migration_creates_core_tables(tmp_path: Path) -> None:
    database = _migrated_database(tmp_path)

    with database.connect() as connection:
        names = {
            str(row["name"])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert {"schema_migrations", "raw_records", "workflow_runs", "reports"} <= names


def test_workflow_run_claim_is_idempotent(tmp_path: Path) -> None:
    repository = WorkflowRunRepository(_migrated_database(tmp_path))

    first = repository.claim("premarket:2026-07-13", WorkflowType.PREMARKET, date(2026, 7, 13))
    repeated = repository.claim("premarket:2026-07-13", WorkflowType.PREMARKET, date(2026, 7, 13))

    assert first.acquired is True
    assert repeated.acquired is False
    assert repeated.workflow_run.id == first.workflow_run.id

    finished = repository.finish(
        "premarket:2026-07-13", WorkflowRunStatus.COMPLETED
    )
    assert finished.status is WorkflowRunStatus.COMPLETED
    assert finished.ended_at is not None


def test_raw_record_store_is_idempotent(tmp_path: Path) -> None:
    repository = RawRecordRepository(_migrated_database(tmp_path))
    record = RawRecord(
        source_id="SRC-TEST-001",
        external_id="notice-001",
        record_type="announcement",
        content_hash="abc123",
        payload={"title": "测试公告"},
        published_at=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
        captured_at=datetime(2026, 7, 13, 8, 5, tzinfo=UTC),
        url="https://example.test/notices/001",
    )

    first = repository.store(record)
    repeated = repository.store(record)

    assert repeated.id == first.id

    with repository._database.connect() as connection:  # noqa: SLF001
        count = connection.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0]
    assert count == 1
