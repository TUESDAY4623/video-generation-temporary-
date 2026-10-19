"""Event types for the WebSocket event system."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All event types the backend can emit."""

    # Pipeline lifecycle
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_PROGRESS = "pipeline_progress"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_PAUSED = "pipeline_paused"
    PIPELINE_RESUMED = "pipeline_resumed"

    # Stage lifecycle
    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAILED = "stage_failed"
    STAGE_AWAITING_APPROVAL = "stage_awaiting_approval"

    # Asset generation
    SCENE_GENERATED = "scene_generated"
    ASSET_GENERATED = "asset_generated"

    # Rendering
    RENDER_PROGRESS = "render_progress"
    RENDER_CHAPTER_COMPLETE = "render_chapter_complete"
    RENDER_COMPLETE = "render_complete"

    # Logging
    LOG_MESSAGE = "log_message"


class PipelineEvent:
    """Factory for pipeline-level events."""

    @staticmethod
    def started(project_id: str, total_stages: int) -> dict:
        return {
            "type": EventType.PIPELINE_STARTED,
            "timestamp": _now(),
            "data": {"project_id": project_id, "total_stages": total_stages},
        }

    @staticmethod
    def progress(
        project_id: str,
        current_stage: str,
        stage_index: int,
        total_stages: int,
        message: str = "",
    ) -> dict:
        return {
            "type": EventType.PIPELINE_PROGRESS,
            "timestamp": _now(),
            "data": {
                "project_id": project_id,
                "current_stage": current_stage,
                "stage_index": stage_index,
                "total_stages": total_stages,
                "overall_progress": round((stage_index / total_stages) * 100, 1),
                "message": message,
            },
        }

    @staticmethod
    def complete(project_id: str, video_url: str, duration_seconds: float) -> dict:
        return {
            "type": EventType.PIPELINE_COMPLETE,
            "timestamp": _now(),
            "data": {
                "project_id": project_id,
                "video_url": video_url,
                "duration_seconds": duration_seconds,
            },
        }

    @staticmethod
    def failed(project_id: str, stage: str, error: str) -> dict:
        return {
            "type": EventType.PIPELINE_FAILED,
            "timestamp": _now(),
            "data": {"project_id": project_id, "failed_at_stage": stage, "error": error},
        }


class StageEvent:
    """Factory for stage-level events."""

    @staticmethod
    def started(stage: str, estimated_seconds: int | None = None) -> dict:
        return {
            "type": EventType.STAGE_STARTED,
            "timestamp": _now(),
            "data": {"stage": stage, "estimated_seconds": estimated_seconds},
        }

    @staticmethod
    def progress(
        stage: str,
        progress_pct: float,
        message: str,
        eta_seconds: float | None = None,
    ) -> dict:
        return {
            "type": EventType.STAGE_PROGRESS,
            "timestamp": _now(),
            "data": {
                "stage": stage,
                "progress_pct": round(progress_pct, 1),
                "message": message,
                "eta_seconds": eta_seconds,
            },
        }

    @staticmethod
    def complete(stage: str, artifacts: list[dict] | None = None) -> dict:
        return {
            "type": EventType.STAGE_COMPLETE,
            "timestamp": _now(),
            "data": {"stage": stage, "artifacts": artifacts or []},
        }

    @staticmethod
    def failed(stage: str, error: str, can_retry: bool = True) -> dict:
        return {
            "type": EventType.STAGE_FAILED,
            "timestamp": _now(),
            "data": {"stage": stage, "error": error, "can_retry": can_retry},
        }

    @staticmethod
    def awaiting_approval(stage: str, approval_data: dict) -> dict:
        return {
            "type": EventType.STAGE_AWAITING_APPROVAL,
            "timestamp": _now(),
            "data": {"stage": stage, "approval_data": approval_data},
        }


class SceneEvent:
    """Factory for scene/asset events."""

    @staticmethod
    def generated(
        chapter: int,
        scene_id: str,
        scene_type: str,
        preview_url: str,
        duration_seconds: float,
    ) -> dict:
        return {
            "type": EventType.SCENE_GENERATED,
            "timestamp": _now(),
            "data": {
                "chapter": chapter,
                "scene_id": scene_id,
                "scene_type": scene_type,
                "preview_url": preview_url,
                "duration_seconds": duration_seconds,
            },
        }

    @staticmethod
    def asset_generated(
        asset_type: str,
        asset_id: str,
        preview_url: str,
        file_size_bytes: int | None = None,
    ) -> dict:
        return {
            "type": EventType.ASSET_GENERATED,
            "timestamp": _now(),
            "data": {
                "asset_type": asset_type,
                "asset_id": asset_id,
                "preview_url": preview_url,
                "file_size_bytes": file_size_bytes,
            },
        }


class RenderEvent:
    """Factory for rendering events."""

    @staticmethod
    def progress(
        chapter: int,
        frame_current: int,
        frame_total: int,
        fps: float,
    ) -> dict:
        pct = (frame_current / frame_total * 100) if frame_total > 0 else 0
        return {
            "type": EventType.RENDER_PROGRESS,
            "timestamp": _now(),
            "data": {
                "chapter": chapter,
                "frame_current": frame_current,
                "frame_total": frame_total,
                "progress_pct": round(pct, 1),
                "fps": round(fps, 1),
            },
        }

    @staticmethod
    def chapter_complete(chapter: int, video_url: str) -> dict:
        return {
            "type": EventType.RENDER_CHAPTER_COMPLETE,
            "timestamp": _now(),
            "data": {"chapter": chapter, "video_url": video_url},
        }

    @staticmethod
    def complete(video_url: str, thumbnail_url: str, duration_seconds: float) -> dict:
        return {
            "type": EventType.RENDER_COMPLETE,
            "timestamp": _now(),
            "data": {
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "duration_seconds": duration_seconds,
            },
        }


class LogEvent:
    """Factory for log events."""

    @staticmethod
    def message(level: str, message: str) -> dict:
        return {
            "type": EventType.LOG_MESSAGE,
            "timestamp": _now(),
            "data": {"level": level, "message": message},
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


from contextlib import asynccontextmanager
from fastapi import FastAPI

class ConnectionManager:
    """Manages WebSocket connections per project."""

    def __init__(self):
        self._connections: dict[str, list] = {}

    def connect(self, project_id: str, websocket):
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)

    def disconnect(self, project_id: str, websocket):
        if project_id in self._connections:
            self._connections[project_id].remove(websocket)
            if not self._connections[project_id]:
                del self._connections[project_id]

    async def send_event(self, project_id: str, event: dict):
        import json
        if project_id in self._connections:
            message = json.dumps(event)
            for ws in self._connections[project_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    pass

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan — startup and shutdown handlers."""
    from app.core.database import init_db
    init_db()
    logger.info("VideoForge started successfully")
    yield
    logger.info("VideoForge shutting down")
