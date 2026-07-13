"""原始记录的幂等仓储。"""

from __future__ import annotations

import json
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

    @staticmethod
    def _to_storage_time(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
