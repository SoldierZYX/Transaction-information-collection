"""证券基础信息与日线行情仓储。"""

from __future__ import annotations

from datetime import date

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

    def list_active_on(self, target_date: date) -> list[Security]:
        """读取目标日期有效的证券映射。"""
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT symbol, exchange, name, board, active_from, active_to, source_id
                FROM securities
                WHERE active_from <= ? AND (active_to IS NULL OR active_to >= ?)
                ORDER BY symbol, exchange, active_from DESC
                """,
                (target_date.isoformat(), target_date.isoformat()),
            ).fetchall()
        return [
            Security(
                symbol=str(row["symbol"]),
                exchange=str(row["exchange"]),
                name=str(row["name"]),
                board=str(row["board"]),
                active_from=date.fromisoformat(str(row["active_from"])),
                active_to=(date.fromisoformat(str(row["active_to"])) if row["active_to"] else None),
                source_id=str(row["source_id"]),
            )
            for row in rows
        ]


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

    def list_until(self, target_date: date) -> list[MarketBar]:
        """读取目标日期及此前的全部日线，供确定性指标计算。"""
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT trade_date, symbol, open, high, low, close, volume, amount, source_id
                FROM market_bars
                WHERE trade_date <= ?
                ORDER BY symbol, trade_date, source_id
                """,
                (target_date.isoformat(),),
            ).fetchall()
        return [
            MarketBar(
                trade_date=date.fromisoformat(str(row["trade_date"])),
                symbol=str(row["symbol"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                amount=float(row["amount"]),
                source_id=str(row["source_id"]),
            )
            for row in rows
        ]

    def latest_trade_date(self) -> date | None:
        """返回已导入日线中的最近交易日期。"""
        with self._database.connect() as connection:
            row = connection.execute("SELECT MAX(trade_date) AS value FROM market_bars").fetchone()
        if row is None or row["value"] is None:
            return None
        return date.fromisoformat(str(row["value"]))
