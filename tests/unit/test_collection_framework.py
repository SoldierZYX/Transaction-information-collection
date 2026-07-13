"""采集框架的单元测试。"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from ashare_review.collectors.calendar import MockTradingCalendar
from ashare_review.collectors.contracts import CollectionWindow
from ashare_review.collectors.http import HttpResponse, SafeHttpClient
from ashare_review.collectors.resilience import (
    MinimumIntervalRateLimiter,
    RetryExecutor,
    RetryPolicy,
)


class RecordingTransport:
    """记录请求参数而不进行真实网络访问。"""

    def __init__(self) -> None:
        self.requests: list[tuple[str, float]] = []

    def get(self, url: str, *, timeout_seconds: float) -> HttpResponse:
        self.requests.append((url, timeout_seconds))
        return HttpResponse(status_code=200, body=b"{}", headers={})


def test_retry_executor_retries_timeout_with_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("模拟超时")
        return "ok"

    result = RetryExecutor(
        RetryPolicy(max_attempts=3, initial_delay_seconds=0.1, backoff_multiplier=2),
        sleeper=delays.append,
    ).run(operation)

    assert result == "ok"
    assert attempts == 3
    assert delays == [0.1, 0.2]


def test_rate_limiter_waits_for_minimum_interval() -> None:
    current_time = 0.0
    delays: list[float] = []

    def clock() -> float:
        return current_time

    def sleeper(delay: float) -> None:
        nonlocal current_time
        delays.append(delay)
        current_time += delay

    limiter = MinimumIntervalRateLimiter(1.0, clock=clock, sleeper=sleeper)
    limiter.acquire()
    current_time = 0.25
    limiter.acquire()

    assert delays == [0.75]


def test_safe_http_client_passes_timeout_and_rejects_non_https() -> None:
    transport = RecordingTransport()
    client = SafeHttpClient(
        transport,
        RetryExecutor(RetryPolicy(max_attempts=1)),
        MinimumIntervalRateLimiter(0),
        timeout_seconds=7.5,
    )

    response = client.get("https://example.test/data")

    assert response.status_code == 200
    assert transport.requests == [("https://example.test/data", 7.5)]
    with pytest.raises(ValueError, match="HTTPS"):
        client.get("http://example.test/data")


def test_mock_trading_calendar_handles_trading_and_non_trading_days() -> None:
    calendar = MockTradingCalendar(
        {"CN": frozenset({date(2026, 7, 10), date(2026, 7, 13)})}
    )

    assert calendar.is_trading_day(date(2026, 7, 13), "CN")
    assert not calendar.is_trading_day(date(2026, 7, 11), "CN")
    assert calendar.previous_trading_day(date(2026, 7, 13), "CN") == date(2026, 7, 10)


def test_collection_window_can_use_utc_boundaries() -> None:
    window = CollectionWindow(
        starts_at=datetime(2026, 7, 13, 0, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 13, 1, 0, tzinfo=UTC),
    )

    assert window.ends_at > window.starts_at
