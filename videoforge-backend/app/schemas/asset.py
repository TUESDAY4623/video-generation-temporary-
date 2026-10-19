"""Pydantic schemas for Asset API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AssetCreate(BaseModel):
    project_id: UUID
    chapter_id: str | None = None
    scene_id: str | None = None
    asset_type: str
    name: str | None = None
    file_path: str
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    mime_type: str | None = None
    metadata: dict[str, Any] | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class AssetResponse(BaseModel):
    id: UUID
    project_id: UUID
    chapter_id: str | None
    scene_id: str | None
    asset_type: str
    name: str | None
    file_path: str
    file_size_bytes: int | None
    duration_seconds: float | None
    mime_type: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
