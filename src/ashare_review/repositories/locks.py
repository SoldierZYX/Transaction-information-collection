"""任务锁的 SQLite 仓储。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ashare_review.repositories.database import Database


class TaskLockRepository:
    """使用带过期时间的租约锁防止同一任务并发执行。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def acquire(
        self,
        lock_key: str,
        owner_id: str,
        *,
        ttl: timedelta,
        now: datetime | None = None,
    ) -> bool:
        """获取锁；已有未过期锁时返回 False。"""
        acquired_at = now or datetime.now(UTC)
        expires_at = acquired_at + ttl
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                INSERT INTO task_locks (lock_key, owner_id, acquired_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (lock_key) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    acquired_at = excluded.acquired_at,
                    expires_at = excluded.expires_at
                WHERE task_locks.expires_at <= excluded.acquired_at
                """,
                (lock_key, owner_id, acquired_at.isoformat(), expires_at.isoformat()),
            )
            connection.commit()
        return cursor.rowcount == 1

    def release(self, lock_key: str, owner_id: str) -> bool:
        """仅允许当前持有者释放自己的锁。"""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM task_locks WHERE lock_key = ? AND owner_id = ?",
                (lock_key, owner_id),
            )
            connection.commit()
        return cursor.rowcount == 1
