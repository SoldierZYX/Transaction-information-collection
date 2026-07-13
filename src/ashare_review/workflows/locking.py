"""工作流任务锁的上下文管理器。"""

from __future__ import annotations

from datetime import timedelta

from ashare_review.repositories.locks import TaskLockRepository


class TaskAlreadyRunningError(RuntimeError):
    """同一任务已有未过期实例正在运行。"""


class TaskLease:
    """将 SQLite 租约锁包装为工作流可用的上下文管理器。"""

    def __init__(
        self,
        repository: TaskLockRepository,
        lock_key: str,
        owner_id: str,
        *,
        ttl: timedelta,
    ) -> None:
        self._repository = repository
        self._lock_key = lock_key
        self._owner_id = owner_id
        self._ttl = ttl

    def __enter__(self) -> TaskLease:
        """获取锁，失败时阻止并发工作流继续执行。"""
        if not self._repository.acquire(self._lock_key, self._owner_id, ttl=self._ttl):
            raise TaskAlreadyRunningError(f"任务正在运行: {self._lock_key}")
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """退出工作流范围时释放锁。"""
        self._repository.release(self._lock_key, self._owner_id)
