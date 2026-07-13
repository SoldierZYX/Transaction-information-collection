"""36Kr 来源适配器。"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Protocol
from xml.etree import ElementTree

from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.collectors.http import HttpResponse
from ashare_review.domain.records import RawRecord

SOURCE_IDS = ("SRC-36KR-001",)
RSS_NEWSFLASH_URL = "https://36kr.com/feed-newsflash"


class HttpGetClient(Protocol):
    """支持 GET 请求的最小 HTTP 客户端协议。"""

    def get(self, url: str) -> HttpResponse:
        """获取指定地址的响应。"""


class Kr36RssCollector:
    """从 36Kr 官方快讯 RSS 采集标题、时间和链接。"""

    source_id = SOURCE_IDS[0]

    def __init__(self, http_client: HttpGetClient, captured_at: datetime) -> None:
        self._http_client = http_client
        self._captured_at = captured_at

    def fetch(self, window: CollectionWindow) -> list[RawRecord]:
        """拉取 RSS 并筛选位于采集窗口内的快讯。"""
        response = self._http_client.get(RSS_NEWSFLASH_URL)
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"36Kr RSS 请求失败，状态码：{response.status_code}")

        root = ElementTree.fromstring(response.body)
        records: list[RawRecord] = []
        for item in root.findall(".//item"):
            title = self._text(item, "title")
            url = self._text(item, "link")
            external_id = self._text(item, "guid") or url
            published_at = self._published_at(item)
            if not title or not url or not external_id or published_at is None:
                continue
            if not window.starts_at <= published_at < window.ends_at:
                continue

            content_hash = sha256(f"{external_id}|{title}|{url}".encode()).hexdigest()
            records.append(
                RawRecord(
                    source_id=self.source_id,
                    record_type="news",
                    external_id=external_id,
                    captured_at=self._captured_at,
                    payload={"title": title},
                    content_hash=content_hash,
                    published_at=published_at,
                    url=url,
                )
            )
        return records

    @staticmethod
    def _text(item: ElementTree.Element, name: str) -> str:
        """读取并清理 RSS 节点文本。"""
        return (item.findtext(name) or "").strip()

    @staticmethod
    def _published_at(item: ElementTree.Element) -> datetime | None:
        """解析 RSS 标准发布时间。"""
        raw_value = (item.findtext("pubDate") or "").strip()
        if not raw_value:
            return None
        return parsedate_to_datetime(raw_value)
