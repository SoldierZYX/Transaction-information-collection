"""巨潮资讯来源适配器。"""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol

from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.domain.records import RawRecord

SOURCE_IDS = ("SRC-DISCLOSURE-001",)


@dataclass(frozen=True)
class CninfoAnnouncement:
    """巨潮资讯公告的最小元数据。"""

    external_id: str
    title: str
    published_at: datetime
    url: str
    symbol: str | None = None
    security_name: str | None = None


class CninfoDataService(Protocol):
    """已获授权的巨潮资讯数据服务客户端协议。"""

    def list_announcements(self, window: CollectionWindow) -> list[CninfoAnnouncement]:
        """返回窗口内的公告元数据，不返回公告正文。"""


class CninfoAnnouncementCollector:
    """将授权数据服务返回的巨潮公告转为原始记录。"""

    source_id = SOURCE_IDS[0]

    def __init__(self, data_service: CninfoDataService, captured_at: datetime) -> None:
        self._data_service = data_service
        self._captured_at = captured_at

    def fetch(self, window: CollectionWindow) -> list[RawRecord]:
        """采集公告标题、时间、链接和证券标识等最小元数据。"""
        records: list[RawRecord] = []
        for announcement in self._data_service.list_announcements(window):
            payload = {
                "title": announcement.title,
                "symbol": announcement.symbol,
                "security_name": announcement.security_name,
            }
            content_hash = sha256(
                f"{announcement.external_id}|{announcement.title}|{announcement.url}".encode()
            ).hexdigest()
            records.append(
                RawRecord(
                    source_id=self.source_id,
                    record_type="disclosure",
                    external_id=announcement.external_id,
                    captured_at=self._captured_at,
                    payload=payload,
                    content_hash=content_hash,
                    published_at=announcement.published_at,
                    url=announcement.url,
                )
            )
        return records
