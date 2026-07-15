"""股票池筛选与确定性评分的领域模型。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PoolExclusion:
    """一只证券未进入股票池的可审计原因。"""

    symbol: str
    reason_code: str


@dataclass(frozen=True)
class ScoreComponent:
    """单一评分维度及其可复算输入。"""

    component: str
    score: float
    inputs: Mapping[str, float]


@dataclass(frozen=True)
class PoolCandidate:
    """通过筛选的观察标的，不构成交易建议。"""

    symbol: str
    total_score: float
    confidence: float
    rationale: str
    conditions: str
    invalidation: str
    components: tuple[ScoreComponent, ...]


@dataclass(frozen=True)
class PoolEvaluation:
    """某一业务日期的筛选与评分结果。"""

    target_date: date
    candidates: tuple[PoolCandidate, ...]
    exclusions: tuple[PoolExclusion, ...]
