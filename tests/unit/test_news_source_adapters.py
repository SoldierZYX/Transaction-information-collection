"""36Kr 与巨潮资讯适配器测试。"""

from datetime import UTC, datetime, timedelta

import pytest

from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.collectors.http import HttpResponse
from ashare_review.collectors.sources.cninfo import (
    CninfoAnnouncement,
    CninfoAnnouncementCollector,
)
from ashare_review.collectors.sources.kr36 import RSS_NEWSFLASH_URL, Kr36RssCollector


class StubHttpClient:
    """返回固定响应的 HTTP 客户端替身。"""

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.requested_urls: list[str] = []

    def get(self, url: str) -> HttpResponse:
        """记录请求地址并返回预设响应。"""
        self.requested_urls.append(url)
        return self.response


class StubCninfoDataService:
    """返回固定公告的巨潮授权服务替身。"""

    def __init__(self, announcements: list[CninfoAnnouncement]) -> None:
        self.announcements = announcements
        self.windows: list[CollectionWindow] = []

    def list_announcements(self, window: CollectionWindow) -> list[CninfoAnnouncement]:
        """记录窗口并返回预设公告。"""
        self.windows.append(window)
        return self.announcements


def test_36kr_rss_collector_collects_only_metadata_in_window() -> None:
    """36Kr 适配器只保留窗口内快讯的最小元数据。"""
    published_at = datetime(2026, 7, 14, 1, tzinfo=UTC)
    xml = """<?xml version='1.0'?><rss><channel><item>
    <title>测试快讯</title><link>https://36kr.com/p/1</link><guid>news-1</guid>
    <pubDate>Tue, 14 Jul 2026 01:00:00 +0000</pubDate>
    </item></channel></rss>""".encode()
    client = StubHttpClient(HttpResponse(status_code=200, body=xml, headers={}))
    collector = Kr36RssCollector(client, captured_at=published_at + timedelta(minutes=1))
    window = CollectionWindow(
        starts_at=published_at - timedelta(minutes=1), ends_at=published_at + timedelta(minutes=1)
    )

    records = collector.fetch(window)

    assert client.requested_urls == [RSS_NEWSFLASH_URL]
    assert len(records) == 1
    assert records[0].external_id == "news-1"
    assert records[0].published_at == published_at
    assert records[0].payload == {"title": "测试快讯"}
    assert records[0].url == "https://36kr.com/p/1"


def test_36kr_rss_collector_rejects_unsuccessful_response() -> None:
    """36Kr RSS 非成功响应不能被当作空数据。"""
    collector = Kr36RssCollector(
        StubHttpClient(HttpResponse(status_code=503, body=b"", headers={})),
        captured_at=datetime(2026, 7, 14, tzinfo=UTC),
    )
    window = CollectionWindow(
        starts_at=datetime(2026, 7, 14, tzinfo=UTC),
        ends_at=datetime(2026, 7, 15, tzinfo=UTC),
    )

    with pytest.raises(RuntimeError, match="状态码：503"):
        collector.fetch(window)


def test_cninfo_collector_converts_authorized_service_metadata() -> None:
    """巨潮适配器仅转换授权服务提供的公告元数据。"""
    published_at = datetime(2026, 7, 14, 2, tzinfo=UTC)
    service = StubCninfoDataService(
        [
            CninfoAnnouncement(
                external_id="notice-1",
                title="测试公告",
                published_at=published_at,
                url="https://www.cninfo.com.cn/notice/1",
                symbol="000001",
                security_name="平安银行",
            )
        ]
    )
    collector = CninfoAnnouncementCollector(
        service, captured_at=published_at + timedelta(minutes=1)
    )
    window = CollectionWindow(
        starts_at=published_at - timedelta(minutes=1), ends_at=published_at + timedelta(minutes=1)
    )

    records = collector.fetch(window)

    assert service.windows == [window]
    assert len(records) == 1
    assert records[0].record_type == "disclosure"
    assert records[0].published_at == published_at
    assert records[0].payload == {
        "title": "测试公告",
        "symbol": "000001",
        "security_name": "平安银行",
    }
