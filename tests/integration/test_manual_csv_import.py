"""本地 CSV 导入的集成测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ashare_review.collectors.manual_csv import ManualCsvImporter
from ashare_review.repositories.database import Database
from ashare_review.repositories.market_data import MarketBarRepository, SecurityRepository
from ashare_review.repositories.migrations import MigrationRunner
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.source_health import SourceHealthRepository


def _importer(tmp_path: Path) -> tuple[ManualCsvImporter, Database]:
    """创建带完整迁移的本地 CSV 导入器。"""
    database = Database.from_path(tmp_path / "ashare_review.sqlite3")
    MigrationRunner(database, Path("migrations")).migrate()
    importer = ManualCsvImporter(
        MarketBarRepository(database),
        SecurityRepository(database),
        RawRecordRepository(database),
        SourceHealthRepository(database),
        now=lambda: datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
    )
    return importer, database


def test_import_market_bars_is_idempotent(tmp_path: Path) -> None:
    importer, database = _importer(tmp_path)
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "trade_date,symbol,open,high,low,close,volume,amount\n"
        "2026-07-13,600000,10,10.3,9.9,10.2,1200000,12240000\n",
        encoding="utf-8",
    )

    assert importer.import_market_bars(csv_path, "SRC-MANUAL-CSV-001").records_processed == 1
    assert importer.import_market_bars(csv_path, "SRC-MANUAL-CSV-001").records_processed == 1

    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0]
    assert count == 1


def test_import_securities_and_disclosures(tmp_path: Path) -> None:
    importer, database = _importer(tmp_path)
    securities_path = tmp_path / "securities.csv"
    securities_path.write_text(
        "symbol,exchange,name,board,active_from,active_to\n"
        "600000,SSE,浦发银行,main,1999-11-10,\n",
        encoding="utf-8",
    )
    disclosures_path = tmp_path / "disclosures.csv"
    disclosures_path.write_text(
        "external_id,published_at,url,title\n"
        "notice-001,2026-07-13T08:00:00+08:00,https://example.test/notice/001,示例公告\n",
        encoding="utf-8",
    )

    security_result = importer.import_securities(securities_path, "SRC-MANUAL-CSV-001")
    first_disclosure_result = importer.import_disclosures(disclosures_path, "SRC-MANUAL-CSV-001")
    repeated_disclosure_result = importer.import_disclosures(
        disclosures_path, "SRC-MANUAL-CSV-001"
    )

    assert security_result.records_processed == 1
    assert first_disclosure_result.records_processed == 1
    assert repeated_disclosure_result.records_processed == 1

    with database.connect() as connection:
        securities_count = connection.execute("SELECT COUNT(*) FROM securities").fetchone()[0]
        disclosure_count = connection.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0]
    assert securities_count == 1
    assert disclosure_count == 1


def test_import_failure_records_unavailable_health(tmp_path: Path) -> None:
    importer, database = _importer(tmp_path)
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_text("trade_date,symbol\n2026-07-13,600000\n", encoding="utf-8")

    result = importer.import_market_bars(invalid_path, "SRC-MANUAL-CSV-001")

    assert result.records_processed == 0
    with database.connect() as connection:
        row = connection.execute("SELECT status FROM source_health").fetchone()
    assert row is not None
    assert row["status"] == "unavailable"
