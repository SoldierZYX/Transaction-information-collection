"""交易日历的内存 mock。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date


class MockTradingCalendar:
    """只为测试和固定夹具提供交易日判断。"""

    def __init__(self, trading_days: Mapping[str, frozenset[date]]) -> None:
        self._trading_days = trading_days

    def is_trading_day(self, target_date: date, market: str) -> bool:
        """判断指定市场在目标日期是否开市。"""
        return target_date in self._trading_days.get(market, frozenset())

    def previous_trading_day(self, target_date: date, market: str) -> date | None:
        """返回目标日期之前最近的已知交易日。"""
        previous_days = [
            trading_day
            for trading_day in self._trading_days.get(market, frozenset())
            if trading_day < target_date
        ]
        return max(previous_days, default=None)
