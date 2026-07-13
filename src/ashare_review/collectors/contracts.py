"""采集器通用契约与来源健康模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ashare_review.domain.records import RawRecord


@dataclass(frozen=True)
class CollectionWindow:
    """一次采集允许使用的数据时间窗口。"""

    starts_at: datetime
    ends_at: datetime


class SourceHealthStatus(StrEnum):
    """来源健康的受控状态。"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SourceHealthReport:
    """一次采集尝试产生的来源健康记录。"""

    source_id: str
    observed_at: datetime
    status: SourceHealthStatus
    records_fetched: int
    error_type: str | None = None
    error_message: str | None = None


class Collector(Protocol):
    """所有已批准数据源适配器必须实现的接口。"""

    source_id: str

    def fetch(self, window: CollectionWindow) -> list[RawRecord]:
        """获取窗口内的原始记录，不负责持久化或评分。"""
