"""原始新闻的标准化、事件归并和证据关联工作流。"""

from __future__ import annotations

from ashare_review.domain.events import EventProcessingResult
from ashare_review.processors.news_events import NewsEventProcessor
from ashare_review.repositories.events import EventRepository
from ashare_review.repositories.raw_records import RawRecordRepository


class EventProcessingWorkflow:
    """处理全部已落库新闻；操作可重复执行。"""

    def __init__(
        self,
        raw_record_repository: RawRecordRepository,
        event_repository: EventRepository,
        processor: NewsEventProcessor,
    ) -> None:
        self._raw_record_repository = raw_record_repository
        self._event_repository = event_repository
        self._processor = processor

    def run_news(self) -> EventProcessingResult:
        """读取新闻原始记录，生成中性事件及其来源证据关系。"""
        records = self._raw_record_repository.list_by_record_type("news")
        drafts = self._processor.build_event_drafts(records)
        return self._event_repository.store_drafts(drafts)
