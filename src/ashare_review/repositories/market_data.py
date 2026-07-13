"""证券基础信息与日线行情仓储。"""

from __future__ import annotations

from ashare_review.domain.market import MarketBar, Security
from ashare_review.repositories.database import Database


class SecurityRepository:
    """以证券、交易所和生效日唯一保存证券信息。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_many(self, securities: list[Security]) -> int:
        """保存证券列表并返回处理的记录数。"""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                """
                INSERT INTO securities (
                    symbol, exchange, name, board, active_from, active_to, source_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, exchange, active_from) DO UPDATE SET
                    name = excluded.name,
                    board = excluded.board,
                    active_to = excluded.active_to,
                    source_id = excluded.source_id
                """,
                [
                    (
                        security.symbol,
                        security.exchange,
                        security.name,
                        security.board,
                        security.active_from.isoformat(),
                        security.active_to.isoformat() if security.active_to is not None else None,
                        security.source_id,
                    )
                    for security in securities
                ],
            )
            connection.commit()
        return len(securities)


class MarketBarRepository:
    """以交易日、证券和来源唯一保存原始日线行情。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_many(self, bars: list[MarketBar]) -> int:
        """保存日线行情并返回处理的记录数。"""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                """
                INSERT INTO market_bars (
                    trade_date, symbol, open, high, low, close, volume, amount, source_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (trade_date, symbol, source_id) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    amount = excluded.amount
                """,
                [
                    (
                        bar.trade_date.isoformat(),
                        bar.symbol,
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume,
                        bar.amount,
                        bar.source_id,
                    )
                    for bar in bars
                ],
            )
            connection.commit()
        return len(bars)
