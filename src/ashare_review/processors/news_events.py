"""新闻元数据标准化、精确去重和事件草稿生成。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from unicodedata import normalize
from zoneinfo import ZoneInfo

from ashare_review.domain.events import EventCategory, EventDirection, EventDraft
from ashare_review.domain.records import StoredRawRecord

BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class NormalizedNews:
    """用于确定性去重的最小新闻标准化结果。"""

    raw_record_id: int
    normalized_title: str
    occurred_at: datetime


class NewsEventProcessor:
    """只依据标题和日期进行保守的新闻事件归并。"""

    def build_event_drafts(self, records: list[StoredRawRecord]) -> list[EventDraft]:
        """标准化新闻标题，并合并同日标题完全一致的记录。"""
        groups: dict[tuple[str, str], list[NormalizedNews]] = defaultdict(list)
        for stored_record in records:
            normalized = self._normalize(stored_record)
            if normalized is None:
                continue
            business_day = normalized.occurred_at.astimezone(BUSINESS_TIMEZONE).date().isoformat()
            groups[(business_day, normalized.normalized_title)].append(normalized)

        drafts: list[EventDraft] = []
        for (business_day, normalized_title), group in sorted(groups.items()):
            first_occurred_at = min(item.occurred_at for item in group)
            event_key = self._event_key(business_day, normalized_title)
            drafts.append(
                EventDraft(
                    event_key=event_key,
                    category=EventCategory.NEWS,
                    direction=EventDirection.NEUTRAL,
                    importance=0.0,
                    freshness=1.0,
                    confidence=1.0,
                    occurred_at=first_occurred_at,
                    evidence_record_ids=tuple(sorted(item.raw_record_id for item in group)),
                )
            )
        return drafts

    @staticmethod
    def _normalize(stored_record: StoredRawRecord) -> NormalizedNews | None:
        """清理标题空白与兼容字符，缺失必要字段时跳过记录。"""
        record = stored_record.record
        if record.record_type != "news" or record.published_at is None:
            return None
        title = record.payload.get("title")
        if not isinstance(title, str):
            return None
        normalized_title = " ".join(normalize("NFKC", title).split()).casefold()
        if not normalized_title:
            return None
        return NormalizedNews(
            raw_record_id=stored_record.id,
            normalized_title=normalized_title,
            occurred_at=record.published_at,
        )

    @staticmethod
    def _event_key(business_day: str, normalized_title: str) -> str:
        """生成可复现的精确去重键，不使用正文或模型推断。"""
        value = f"news|{business_day}|{normalized_title}".encode()
        return f"news:{sha256(value).hexdigest()}"
