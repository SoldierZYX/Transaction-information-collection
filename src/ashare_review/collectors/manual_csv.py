"""人工导出 CSV 的本地导入适配器。"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from ashare_review.collectors.contracts import SourceHealthReport, SourceHealthStatus
from ashare_review.domain.market import MarketBar, Security
from ashare_review.domain.records import RawRecord
from ashare_review.repositories.market_data import MarketBarRepository, SecurityRepository
from ashare_review.repositories.raw_records import RawRecordRepository
from ashare_review.repositories.source_health import SourceHealthRepository


class CsvImportError(ValueError):
    """CSV 文件结构或字段值不符合约定。"""


@dataclass(frozen=True)
class ImportResult:
    """一次本地 CSV 导入的结果。"""

    source_id: str
    records_processed: int
    health_record_id: int


class ManualCsvImporter:
    """解析本地 CSV，并将合格数据以幂等方式写入 SQLite。"""

    def __init__(
        self,
        market_bars: MarketBarRepository,
        securities: SecurityRepository,
        raw_records: RawRecordRepository,
        source_health: SourceHealthRepository,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._market_bars = market_bars
        self._securities = securities
        self._raw_records = raw_records
        self._source_health = source_health
        self._now = now

    def import_market_bars(self, path: Path, source_id: str) -> ImportResult:
        """导入日线行情 CSV。"""
        try:
            bars = self._read_market_bars(path, source_id)
            processed = self._market_bars.upsert_many(bars)
        except (OSError, ValueError) as error:
            return self._record_failure(source_id, error)
        return self._record_success(source_id, processed)

    def import_securities(self, path: Path, source_id: str) -> ImportResult:
        """导入证券基础信息 CSV。"""
        try:
            securities = self._read_securities(path, source_id)
            processed = self._securities.upsert_many(securities)
        except (OSError, ValueError) as error:
            return self._record_failure(source_id, error)
        return self._record_success(source_id, processed)

    def import_disclosures(self, path: Path, source_id: str) -> ImportResult:
        """导入公告元数据 CSV；不读取或保存公告正文。"""
        try:
            records = self._read_disclosures(path, source_id)
            for record in records:
                self._raw_records.store(record)
        except (OSError, ValueError) as error:
            return self._record_failure(source_id, error)
        return self._record_success(source_id, len(records))

    def _read_market_bars(self, path: Path, source_id: str) -> list[MarketBar]:
        rows = self._read_rows(
            path,
            {"trade_date", "symbol", "open", "high", "low", "close", "volume", "amount"},
        )
        return [
            MarketBar(
                trade_date=date.fromisoformat(self._required(row, "trade_date")),
                symbol=self._required(row, "symbol"),
                open=float(self._required(row, "open")),
                high=float(self._required(row, "high")),
                low=float(self._required(row, "low")),
                close=float(self._required(row, "close")),
                volume=float(self._required(row, "volume")),
                amount=float(self._required(row, "amount")),
                source_id=source_id,
            )
            for row in rows
        ]

    def _read_securities(self, path: Path, source_id: str) -> list[Security]:
        rows = self._read_rows(path, {"symbol", "exchange", "name", "board", "active_from"})
        return [
            Security(
                symbol=self._required(row, "symbol"),
                exchange=self._required(row, "exchange"),
                name=self._required(row, "name"),
                board=self._required(row, "board"),
                active_from=date.fromisoformat(self._required(row, "active_from")),
                active_to=self._optional_date(row, "active_to"),
                source_id=source_id,
            )
            for row in rows
        ]

    def _read_disclosures(self, path: Path, source_id: str) -> list[RawRecord]:
        rows = self._read_rows(path, {"external_id", "published_at", "url", "title"})
        captured_at = self._now()
        return [
            RawRecord(
                source_id=source_id,
                external_id=self._required(row, "external_id"),
                record_type="disclosure",
                content_hash=self._content_hash(row),
                payload={"title": self._required(row, "title")},
                published_at=self._aware_datetime(self._required(row, "published_at")),
                url=self._required(row, "url"),
                captured_at=captured_at,
            )
            for row in rows
        ]

    @staticmethod
    def _read_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            columns = set(reader.fieldnames or [])
            missing = required_columns - columns
            if missing:
                raise CsvImportError(f"CSV 缺少字段: {', '.join(sorted(missing))}")
            return [dict(row) for row in reader]

    @staticmethod
    def _required(row: dict[str, str], field: str) -> str:
        value = row.get(field, "").strip()
        if not value:
            raise CsvImportError(f"CSV 字段不能为空: {field}")
        return value

    @staticmethod
    def _optional_date(row: dict[str, str], field: str) -> date | None:
        value = row.get(field, "").strip()
        return date.fromisoformat(value) if value else None

    @staticmethod
    def _aware_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise CsvImportError("published_at 必须包含时区")
        return parsed

    @staticmethod
    def _content_hash(row: dict[str, str]) -> str:
        canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _record_success(self, source_id: str, records_processed: int) -> ImportResult:
        health_id = self._source_health.record(
            SourceHealthReport(
                source_id=source_id,
                observed_at=self._now(),
                status=SourceHealthStatus.HEALTHY,
                records_fetched=records_processed,
            )
        )
        return ImportResult(source_id, records_processed, health_id)

    def _record_failure(self, source_id: str, error: Exception) -> ImportResult:
        health_id = self._source_health.record(
            SourceHealthReport(
                source_id=source_id,
                observed_at=self._now(),
                status=SourceHealthStatus.UNAVAILABLE,
                records_fetched=0,
                error_type=type(error).__name__,
                error_message="本地 CSV 导入失败，请检查结构化诊断记录",
            )
        )
        return ImportResult(source_id, 0, health_id)
