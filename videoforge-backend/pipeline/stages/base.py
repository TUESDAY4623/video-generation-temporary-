"""Base class for all pipeline stages."""

from __future__ import annotations

import asyncio
import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.events import StageEvent, manager
from app.models.project import StageRun, StageStatus
from pipeline.models.config import StageConfig
from pipeline.models.entities import PipelineContext

logger = logging.getLogger(__name__)


class StageError(Exception):
    """Base exception for stage failures."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class Stage(ABC):
    """Abstract base class for pipeline stages.

    All 9 pipeline stages inherit from this class.
    Provides:
    - Automatic retry with exponential backoff
    - Progress reporting via WebSocket
    - Database StageRun lifecycle management
    - Approval gate support
    """

    config: StageConfig | None = None

    def __init__(self, db_session, stage_run: StageRun):
        self.db = db_session
        self.stage_run = stage_run
        self._progress_callback = None
        self._abort = False

    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the stage. Must be overridden by subclasses."""
        ...

    @property
    def name(self) -> str:
        if self.config:
            return self.config.name
        return self.__class__.__name__

    def set_progress_callback(self, callback) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    def report_progress(self, progress_pct: float, message: str) -> None:
        """Report progress via callback and WebSocket."""
        event = StageEvent.progress(self.name, progress_pct, message)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                manager.send_event(str(self.stage_run.project_id), event)
            )
        except RuntimeError:
            pass

        if self._progress_callback:
            self._progress_callback(progress_pct, message)

    def check_abort(self) -> None:
        """Raise StageError if stage was aborted."""
        if self._abort:
            raise StageError("Stage aborted by user", retryable=False)

    def abort(self) -> None:
        """Signal the stage to abort."""
        self._abort = True

    async def run(self, context: PipelineContext) -> PipelineContext:
        """Run the stage with retry logic and lifecycle management."""
        self._update_status(StageStatus.RUNNING)
        await manager.send_event(
            str(self.stage_run.project_id),
            StageEvent.started(self.name, self.config.estimated_seconds if self.config else None),
        )

        try:
            result = await self._execute_with_retry(context)

            if self.config and self.config.requires_approval:
                self._update_status(StageStatus.AWAITING_APPROVAL)
                await manager.send_event(
                    str(self.stage_run.project_id),
                    {
                        "type": "stage_awaiting_approval",
                        "timestamp": _now(),
                        "data": {"stage": self.name, "stage_run_id": str(self.stage_run.id)},
                    },
                )
                result = await self._wait_for_approval(result)

            self._update_status(StageStatus.COMPLETE, progress_pct=100.0)
            await manager.send_event(
                str(self.stage_run.project_id),
                StageEvent.complete(self.name, []),
            )
            return result

        except StageError as e:
            if not e.retryable:
                self._update_status(StageStatus.FAILED)
            else:
                self._update_status(StageStatus.FAILED)
            error_msg = f"{self.name} failed: {e}"
            self._update_logs(error_msg)
            await manager.send_event(
                str(self.stage_run.project_id),
                StageEvent.failed(self.name, error_msg, can_retry=e.retryable),
            )
            raise

    async def _execute_with_retry(self, context: PipelineContext) -> PipelineContext:
        """Execute with retry logic."""
        retry_decorator = retry(
            retry=retry_if_exception_type(StageError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=60),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        async def _do():
            self._update_status(StageStatus.RUNNING, progress_pct=0.0)
            return await self.execute(context)

        return await retry_decorator(_do)()

    async def _wait_for_approval(self, context: PipelineContext) -> PipelineContext:
        """Wait for human approval."""
        logger.info(f"Stage {self.name} awaiting approval — auto-approving in dev mode")
        await asyncio.sleep(1)
        self._update_status(StageStatus.APPROVED)
        return context

    def _update_status(self, status: StageStatus, progress_pct: float | None = None) -> None:
        """Update the StageRun record in the database."""
        self.stage_run.status = status
        if progress_pct is not None:
            self.stage_run.progress_pct = progress_pct
        if status == StageStatus.RUNNING and not self.stage_run.started_at:
            self.stage_run.started_at = datetime.utcnow()
        if status in (StageStatus.COMPLETE, StageStatus.FAILED):
            self.stage_run.completed_at = datetime.utcnow()
        self.db.merge(self.stage_run)
        self.db.commit()

    def _update_logs(self, message: str) -> None:
        """Append a log message."""
        timestamp = datetime.now(timezone.utc).isoformat()
        logs = self.stage_run.logs or ""
        self.stage_run.logs = f"{logs}\n[{timestamp}] {message}" if logs else f"[{timestamp}] {message}"
        self.db.merge(self.stage_run)
        self.db.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
