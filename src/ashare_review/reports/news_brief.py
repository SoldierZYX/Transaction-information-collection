"""新闻快讯 Markdown 简报生成器。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from ashare_review.domain.records import RawRecord


@dataclass(frozen=True)
class NewsBriefReport:
    """已生成新闻简报的摘要信息。"""

    path: Path
    content_hash: str
    record_count: int


class NewsBriefWriter:
    """将原始新闻记录渲染为只含元数据的 Markdown 简报。"""

    def write(
        self,
        records: list[RawRecord],
        *,
        source_name: str,
        generated_at: datetime,
        reports_dir: Path,
    ) -> NewsBriefReport:
        """创建简报文件并返回其路径、哈希和记录数。"""
        content = self._render(records, source_name=source_name, generated_at=generated_at)
        report_dir = reports_dir / generated_at.strftime("%Y-%m-%d")
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / f"{source_name.lower()}-{generated_at.strftime('%H%M%S')}.md"
        path.write_text(content, encoding="utf-8")
        return NewsBriefReport(
            path=path,
            content_hash=sha256(content.encode()).hexdigest(),
            record_count=len(records),
        )

    @staticmethod
    def _render(records: list[RawRecord], *, source_name: str, generated_at: datetime) -> str:
        """渲染标题、发布时间和原始链接，不包含新闻正文。"""
        lines = [
            f"# {source_name} 快讯简报",
            "",
            f"生成时间：{generated_at.isoformat()}",
            f"记录数量：{len(records)}",
            "数据范围：标题、发布时间和原始链接；不包含新闻正文。",
            "",
            "## 快讯",
            "",
        ]
        for record in sorted(
            records, key=lambda item: item.published_at or generated_at, reverse=True
        ):
            title = str(record.payload.get("title", "未命名快讯"))
            published_at = record.published_at.isoformat() if record.published_at else "未知时间"
            if record.url:
                lines.append(f"- {published_at} | [{title}]({record.url})")
            else:
                lines.append(f"- {published_at} | {title}")
        if not records:
            lines.append("本次采集窗口内没有新增快讯。")
        return "\n".join(lines) + "\n"
