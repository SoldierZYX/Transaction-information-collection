"""轻量 SQLite 迁移执行器。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ashare_review.repositories.database import Database


@dataclass(frozen=True)
class MigrationResult:
    """一次迁移执行的结果。"""

    applied_versions: tuple[int, ...]


class MigrationRunner:
    """按文件名前缀的递增版本执行 SQL 迁移。"""

    def __init__(self, database: Database, migrations_dir: Path = Path("migrations")) -> None:
        self._database = database
        self._migrations_dir = migrations_dir

    def migrate(self) -> MigrationResult:
        """执行尚未应用的迁移，并记录执行时间。"""
        migration_paths = self._migration_paths()
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied_versions = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            newly_applied: list[int] = []

            for path in migration_paths:
                version = self._version_from_path(path)
                if version in applied_versions:
                    continue

                connection.executescript(path.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(UTC).isoformat()),
                )
                newly_applied.append(version)

        return MigrationResult(applied_versions=tuple(newly_applied))

    def _migration_paths(self) -> list[Path]:
        if not self._migrations_dir.is_dir():
            message = f"迁移目录不存在: {self._migrations_dir}"
            raise FileNotFoundError(message)
        return sorted(self._migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))

    @staticmethod
    def _version_from_path(path: Path) -> int:
        return int(path.name.split("_", maxsplit=1)[0])
