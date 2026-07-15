"""基于已导入日线的保守股票池筛选与确定性评分。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import fmean

from ashare_review.domain.market import MarketBar, Security
from ashare_review.domain.pool import PoolCandidate, PoolEvaluation, PoolExclusion, ScoreComponent


@dataclass(frozen=True)
class PoolRules:
    """MVP 股票池规则的可版本化参数。"""

    rule_version: str = "pool-v1"
    min_previous_day_amount_cny: float = 500_000_000
    max_candidates: int = 5
    include_chinext: bool = False


class PoolScorer:
    """执行明确过滤条件，并以日线数据计算可复算评分。"""

    def evaluate(
        self,
        target_date: date,
        securities: list[Security],
        bars: list[MarketBar],
        rules: PoolRules,
    ) -> PoolEvaluation:
        """筛选目标日证券并返回最多指定数量的观察标的。"""
        securities_by_symbol = self._unique_securities(securities)
        bars_by_symbol = self._bars_by_symbol(bars, target_date)
        candidates: list[PoolCandidate] = []
        exclusions: list[PoolExclusion] = []

        for symbol in sorted(securities_by_symbol):
            security = securities_by_symbol[symbol]
            exclusion = self._security_exclusion(security, rules)
            if exclusion is not None:
                exclusions.append(PoolExclusion(symbol, exclusion))
                continue
            symbol_bars = bars_by_symbol.get(symbol, [])
            candidate, reason_code = self._score(symbol, symbol_bars, target_date, rules)
            if candidate is None:
                exclusions.append(PoolExclusion(symbol, reason_code))
                continue
            candidates.append(candidate)

        ranked = sorted(candidates, key=lambda item: (-item.total_score, item.symbol))
        selected = tuple(ranked[: rules.max_candidates])
        for candidate in ranked[rules.max_candidates :]:
            exclusions.append(PoolExclusion(candidate.symbol, "ranked_below_max_candidates"))
        return PoolEvaluation(
            target_date=target_date, candidates=selected, exclusions=tuple(exclusions)
        )

    @staticmethod
    def _unique_securities(securities: list[Security]) -> dict[str, Security]:
        """同一代码存在多个有效映射时保守地排除，避免错误关联。"""
        grouped: dict[str, list[Security]] = defaultdict(list)
        for security in securities:
            grouped[security.symbol].append(security)
        return {symbol: items[0] for symbol, items in grouped.items() if len(items) == 1}

    @staticmethod
    def _bars_by_symbol(bars: list[MarketBar], target_date: date) -> dict[str, list[MarketBar]]:
        """保留目标日及此前按日期排序的日线序列。"""
        grouped: dict[str, list[MarketBar]] = defaultdict(list)
        for bar in bars:
            if bar.trade_date <= target_date:
                grouped[bar.symbol].append(bar)
        return {
            symbol: sorted(items, key=lambda item: item.trade_date)
            for symbol, items in grouped.items()
        }

    @staticmethod
    def _security_exclusion(security: Security, rules: PoolRules) -> str | None:
        """执行板块和证券状态的固定排除规则。"""
        board = security.board.casefold()
        name = security.name.casefold()
        if "科创" in board or "star" in board:
            return "excluded_board_star"
        if "北交" in board or "beijing" in board:
            return "excluded_board_beijing"
        if not rules.include_chinext and ("创业" in board or "chinext" in board):
            return "excluded_board_chinext"
        if name.startswith("st") or name.startswith("*st") or "退" in name or "停牌" in name:
            return "excluded_security_status"
        return None

    @staticmethod
    def _score(
        symbol: str,
        bars: list[MarketBar],
        target_date: date,
        rules: PoolRules,
    ) -> tuple[PoolCandidate | None, str]:
        """要求完整历史和流动性后计算三项非预测性指标。"""
        if not bars or bars[-1].trade_date != target_date:
            return None, "missing_target_day_bar"
        if len(bars) < 21:
            return None, "insufficient_history"
        current = bars[-1]
        if current.amount < rules.min_previous_day_amount_cny:
            return None, "insufficient_liquidity"

        five_day_return = current.close / bars[-6].close - 1
        twenty_day_return = current.close / bars[-21].close - 1
        recent_average_volume = fmean(bar.volume for bar in bars[-6:-1])
        volume_ratio = current.volume / recent_average_volume if recent_average_volume > 0 else 0.0
        short_score = min(max(five_day_return, 0.0) / 0.10, 1.0) * 40
        medium_score = min(max(twenty_day_return, 0.0) / 0.20, 1.0) * 35
        liquidity_score = min(current.amount / 2_000_000_000, 1.0) * 25
        components = (
            ScoreComponent(
                "five_day_momentum",
                short_score,
                {"five_day_return": five_day_return},
            ),
            ScoreComponent(
                "twenty_day_momentum",
                medium_score,
                {"twenty_day_return": twenty_day_return},
            ),
            ScoreComponent(
                "liquidity",
                liquidity_score,
                {"amount": current.amount, "volume_ratio": volume_ratio},
            ),
        )
        return (
            PoolCandidate(
                symbol=symbol,
                total_score=sum(component.score for component in components),
                confidence=1.0,
                rationale="仅基于已导入日线的动量与流动性规则，不构成交易建议。",
                conditions="需保持证券状态合格、目标日行情完整和最低成交额。",
                invalidation="任一关键日线缺失、证券状态变化或成交额低于阈值时失效。",
                components=components,
            ),
            "",
        )
