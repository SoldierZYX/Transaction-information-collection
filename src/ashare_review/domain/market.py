"""证券与日线行情的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Security:
    """一条证券基础信息。"""

    symbol: str
    exchange: str
    name: str
    board: str
    active_from: date
    source_id: str
    active_to: date | None = None


@dataclass(frozen=True)
class MarketBar:
    """一条未复权日线行情。"""

    trade_date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    source_id: str

    def __post_init__(self) -> None:
        """拒绝不符合 OHLC 范围或含负成交量的行情。"""
        if self.low > min(self.open, self.close) or max(self.open, self.close) > self.high:
            raise ValueError("日线价格不满足 low <= open/close <= high")
        if self.volume < 0 or self.amount < 0:
            raise ValueError("成交量和成交额不能为负数")
