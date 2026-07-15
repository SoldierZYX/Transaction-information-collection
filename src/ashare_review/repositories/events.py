"""事件及其原始证据关联的 SQLite 仓储。"""

from __future__ import annotations

from ashare_review.domain.events import EventDraft, EventProcessingResult
from ashare_review.repositories.database import Database


class EventRepository:
    """以稳定事件键幂等保存事件和证据关系。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def store_drafts(self, drafts: list[EventDraft]) -> EventProcessingResult:
        """保存事件；重复执行不会重复创建事件或证据关联。"""
        events_upserted = 0
        evidence_links_created = 0
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for draft in drafts:
                cursor = connection.execute(
                    """
                    INSERT INTO events (
                        event_key, category, direction, importance,
                        freshness, confidence, occurred_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (event_key) DO UPDATE SET
                        freshness = excluded.freshness,
                        confidence = excluded.confidence
                    """,
                    (
                        draft.event_key,
                        draft.category.value,
                        draft.direction.value,
                        draft.importance,
                        draft.freshness,
                        draft.confidence,
                        draft.occurred_at.isoformat(),
                    ),
                )
                events_upserted += int(cursor.rowcount == 1)
                event_row = connection.execute(
                    "SELECT id FROM events WHERE event_key = ?", (draft.event_key,)
                ).fetchone()
                if event_row is None:
                    raise RuntimeError("事件写入后未能读取")
                event_id = int(event_row["id"])
                for raw_record_id in draft.evidence_record_ids:
                    evidence_cursor = connection.execute(
                        """
                        INSERT INTO event_evidence (event_id, raw_record_id, relation_type)
                        VALUES (?, ?, ?)
                        ON CONFLICT (event_id, raw_record_id, relation_type) DO NOTHING
                        """,
                        (event_id, raw_record_id, "source"),
                    )
                    evidence_links_created += int(evidence_cursor.rowcount == 1)
            connection.commit()
        return EventProcessingResult(
            events_upserted=events_upserted,
            evidence_links_created=evidence_links_created,
        )
