"""按网站拆分的来源适配器。"""

from ashare_review.collectors.sources.cninfo import CninfoAnnouncementCollector
from ashare_review.collectors.sources.kr36 import Kr36RssCollector

__all__ = ["CninfoAnnouncementCollector", "Kr36RssCollector"]
