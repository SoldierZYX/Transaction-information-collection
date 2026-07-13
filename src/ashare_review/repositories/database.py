"""SQLite 连接工厂。"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    """将 SQLite URL 解析为受统一配置约束的连接。"""

    def __init__(self, database_url: str) -> None:
        self._path = self._parse_database_url(database_url)

    @classmethod
    def from_path(cls, path: Path) -> Database:
        """为测试和本地运行创建数据库对象。"""
        return cls(f"sqlite:///{path.as_posix()}")

    @property
    def path(self) -> Path:
        """返回数据库文件的本地路径。"""
        return self._path

    def connect(self) -> sqlite3.Connection:
        """打开连接并启用外键与有限等待。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _parse_database_url(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            message = "MVP 仅支持 sqlite:/// 格式的数据库地址"
            raise ValueError(message)

        path = Path(database_url.removeprefix(prefix))
        if not path.name:
            message = "SQLite 数据库地址必须包含文件名"
            raise ValueError(message)
        return path
