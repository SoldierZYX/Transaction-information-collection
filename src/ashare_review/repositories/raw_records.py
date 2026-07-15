"""原始记录的幂等仓储。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ashare_review.domain.records import RawRecord, StoredRawRecord
from ashare_review.repositories.database import Database


class RawRecordRepository:
    """以来源与外部标识保证原始记录不重复写入。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def store(self, record: RawRecord) -> StoredRawRecord:
        """保存记录；重复调用会返回既有记录。"""
        payload_json = json.dumps(record.payload, ensure_ascii=False, sort_keys=True)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO raw_records (
                    source_id, external_id, record_type, published_at, url,
                    content_hash, payload_json, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (source_id, external_id) DO NOTHING
                """,
                (
                    record.source_id,
                    record.external_id,
                    record.record_type,
                    self._to_storage_time(record.published_at),
                    record.url,
                    record.content_hash,
                    payload_json,
                    self._to_storage_time(record.captured_at),
                ),
            )
            row = connection.execute(
                """
                SELECT id FROM raw_records
                WHERE source_id = ? AND external_id = ?
                """,
                (record.source_id, record.external_id),
            ).fetchone()
            connection.commit()

        if row is None:
            raise RuntimeError("原始记录写入后未能读取")
        return StoredRawRecord(id=int(row["id"]), record=record)

    def list_by_record_type(self, record_type: str) -> list[StoredRawRecord]:
        """按记录类型读取原始数据，用于可重复执行的后续处理。"""
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM raw_records WHERE record_type = ? ORDER BY id", (record_type,)
            ).fetchall()
        return [self._to_stored_record(row) for row in rows]

    @staticmethod
    def _to_stored_record(row: sqlite3.Row) -> StoredRawRecord:
        """将 SQLite 行还原为领域记录。"""
        stored_row = row
        published_at = stored_row["published_at"]
        return StoredRawRecord(
            id=int(stored_row["id"]),
            record=RawRecord(
                source_id=str(stored_row["source_id"]),
                external_id=str(stored_row["external_id"]),
                record_type=str(stored_row["record_type"]),
                content_hash=str(stored_row["content_hash"]),
                payload=json.loads(str(stored_row["payload_json"])),
                captured_at=datetime.fromisoformat(str(stored_row["captured_at"])),
                published_at=(datetime.fromisoformat(str(published_at)) if published_at else None),
                url=str(stored_row["url"]) if stored_row["url"] is not None else None,
            ),
        )

    @staticmethod
    def _to_storage_time(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
