"""仅允许 HTTPS 的采集 HTTP 客户端。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ashare_review.collectors.resilience import MinimumIntervalRateLimiter, RetryExecutor


@dataclass(frozen=True)
class HttpResponse:
    """传输层返回的最小 HTTP 响应。"""

    status_code: int
    body: bytes
    headers: Mapping[str, str]


class HttpTransport(Protocol):
    """可替换的 HTTP 传输接口，便于使用 mock 测试。"""

    def get(self, url: str, *, timeout_seconds: float) -> HttpResponse:
        """按给定超时发起 GET 请求。"""


class UrllibTransport:
    """基于标准库的默认传输实现。"""

    def get(self, url: str, *, timeout_seconds: float) -> HttpResponse:
        """执行 GET 请求；调用方负责限速和重试。"""
        request = Request(url, headers={"User-Agent": "ashare-review/0.1"})
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            return HttpResponse(
                status_code=int(response.status),
                body=response.read(),
                headers=dict(response.headers.items()),
            )


class SafeHttpClient:
    """强制 HTTPS、超时、限速和有限重试的客户端。"""

    def __init__(
        self,
        transport: HttpTransport,
        retry_executor: RetryExecutor,
        rate_limiter: MinimumIntervalRateLimiter,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")
        self._transport = transport
        self._retry_executor = retry_executor
        self._rate_limiter = rate_limiter
        self._timeout_seconds = timeout_seconds

    def get(self, url: str) -> HttpResponse:
        """仅对 HTTPS 地址执行受控请求。"""
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("采集器仅允许使用完整的 HTTPS 地址")

        def fetch_once() -> HttpResponse:
            self._rate_limiter.acquire()
            return self._transport.get(url, timeout_seconds=self._timeout_seconds)

        return self._retry_executor.run(fetch_once)
