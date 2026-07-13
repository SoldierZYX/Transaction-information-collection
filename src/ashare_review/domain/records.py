"""原始数据审计的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """采集器落库前的原始记录。"""

    source_id: str
    external_id: str
    record_type: str
    content_hash: str
    payload: dict[str, Any]
    captured_at: datetime
    published_at: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class StoredRawRecord:
    """带持久化标识的原始记录。"""

    id: int
    record: RawRecord
