"""Pydantic schemas for Project API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    topic: str = Field(..., min_length=1, max_length=500)
    subtopic: str | None = Field(None, max_length=500)
    user_explanation: str | None = None
    target_duration_minutes: int = Field(default=45, ge=5, le=120)
    target_audience: str = Field(default="intermediate")
    visual_style: str = Field(default="cinematic")
    pacing: str = Field(default="moderate")
    words_per_minute: int = Field(default=150, ge=100, le=200)
    budget_limit_usd: float | None = Field(None, ge=0)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    topic: str | None = Field(None, max_length=500)
    subtopic: str | None = Field(None, max_length=500)
    user_explanation: str | None = None
    target_duration_minutes: int | None = Field(None, ge=5, le=120)
    visual_style: str | None = None
    pacing: str | None = None
    budget_limit_usd: float | None = Field(None, ge=0)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    topic: str
    subtopic: str | None
    user_explanation: str | None
    target_duration_minutes: int
    target_audience: str
    visual_style: str
    pacing: str
    words_per_minute: int
    status: str
    current_stage: str | None
    budget_limit_usd: float | None
    budget_spent_usd: float
    output_video_path: str | None
    output_thumbnail_path: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    topic: str
    status: str
    current_stage: str | None
    target_duration_minutes: int
    budget_spent_usd: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
