"""采集请求的限速、超时和重试策略。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep
from typing import TypeVar

ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class RetryPolicy:
    """有限重试的退避参数。"""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.5
    backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts 必须至少为 1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds 不能为负数")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier 必须不小于 1")


class RetryExecutor:
    """仅对明确可重试的异常执行有限次重试。"""

    def __init__(
        self,
        policy: RetryPolicy,
        *,
        sleeper: Callable[[float], None] = sleep,
        is_retryable: Callable[[Exception], bool] | None = None,
    ) -> None:
        self._policy = policy
        self._sleeper = sleeper
        self._is_retryable = is_retryable or (lambda error: isinstance(error, TimeoutError))

    def run(self, operation: Callable[[], ResultT]) -> ResultT:
        """运行操作；达到次数上限后抛出最后一个异常。"""
        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                return operation()
            except Exception as error:
                if attempt == self._policy.max_attempts or not self._is_retryable(error):
                    raise
                delay = self._policy.initial_delay_seconds * (
                    self._policy.backoff_multiplier ** (attempt - 1)
                )
                self._sleeper(delay)

        raise RuntimeError("重试执行器未产生结果")


class MinimumIntervalRateLimiter:
    """以最小请求间隔实现保守限速。"""

    def __init__(
        self,
        minimum_interval_seconds: float,
        *,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds 不能为负数")
        self._minimum_interval_seconds = minimum_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._last_started_at: float | None = None

    def acquire(self) -> None:
        """等待到满足最小间隔后再允许下一次请求。"""
        now = self._clock()
        if self._last_started_at is not None:
            elapsed = now - self._last_started_at
            remaining = self._minimum_interval_seconds - elapsed
            if remaining > 0:
                self._sleeper(remaining)
        self._last_started_at = self._clock()
