"""Pydantic schemas for Pipeline API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StageRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    stage_name: str
    status: str
    progress_pct: float
    started_at: datetime | None
    completed_at: datetime | None
    logs: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StageRunDetail(StageRunResponse):
    input_artifacts: dict | None
    output_artifacts: dict | None
    metadata: dict | None


class PipelineStartResponse(BaseModel):
    project_id: UUID
    message: str
    celery_task_id: str | None


class PipelineStatusResponse(BaseModel):
    project_id: UUID
    status: str
    current_stage: str | None
    progress_pct: float
    stages: list[StageRunResponse]


class ApprovalAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|modify)$")
    feedback: str | None = None
    modified_data: dict | None = None
