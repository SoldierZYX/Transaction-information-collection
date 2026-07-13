"""工作流运行审计的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class WorkflowType(StrEnum):
    """MVP 支持的日常工作流类型。"""

    PREMARKET = "premarket"
    POSTMARKET = "postmarket"


class WorkflowRunStatus(StrEnum):
    """工作流运行的受控状态。"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_NON_TRADING_DAY = "skipped_non_trading_day"


@dataclass(frozen=True)
class WorkflowRun:
    """一条可审计的工作流运行记录。"""

    id: int
    run_key: str
    workflow_type: WorkflowType
    target_date: date
    status: WorkflowRunStatus
    started_at: datetime
    ended_at: datetime | None
    failure_stage: str | None
    force_run: bool


@dataclass(frozen=True)
class WorkflowRunClaim:
    """获取运行权后的结果；重复运行会返回已有记录。"""

    workflow_run: WorkflowRun
    acquired: bool
