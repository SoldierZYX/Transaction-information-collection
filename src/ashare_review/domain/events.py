"""可审计事件与证据关联的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EventCategory(StrEnum):
    """MVP 支持的事件类别。"""

    NEWS = "news"


class EventDirection(StrEnum):
    """事件方向；新闻元数据默认不作方向性推断。"""

    NEUTRAL = "neutral"


@dataclass(frozen=True)
class EventDraft:
    """由确定性规则生成、尚未持久化的事件。"""

    event_key: str
    category: EventCategory
    direction: EventDirection
    importance: float
    freshness: float
    confidence: float
    occurred_at: datetime
    evidence_record_ids: tuple[int, ...]


@dataclass(frozen=True)
class EventProcessingResult:
    """一次事件处理的持久化统计。"""

    events_upserted: int
    evidence_links_created: int
