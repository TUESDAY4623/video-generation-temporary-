"""Database models for VideoForge."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.config import get_settings
from pathlib import Path

settings = get_settings()


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class AssetType(str, Enum):
    NARRATION = "narration"
    IMAGE = "image"
    VIDEO = "video"
    MUSIC = "music"
    SFX = "sfx"
    DIAGRAM = "diagram"
    CODE_SNIPPET = "code_snippet"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    SCENE_HTML = "scene_html"
    CHAPTER_VIDEO = "chapter_video"


class Project(Base):
    """Video project — the central entity."""

    __tablename__ = "projects"

    # Relationships FIRST (no defaults for dataclass ordering)
    stage_runs: list[StageRun] = relationship("StageRun", back_populates="project", cascade="all, delete-orphan", order_by="StageRun.created_at")  # type: ignore[assignment]
    assets: list[Asset] = relationship("Asset", back_populates="project", cascade="all, delete-orphan")  # type: ignore[assignment]
    approvals: list[Approval] = relationship("Approval", back_populates="project", cascade="all, delete-orphan")  # type: ignore[assignment]

    # Primary key
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Required fields
    name: str = Column(String(255), nullable=False, default="")
    slug: str = Column(String(255), unique=True, nullable=False, index=True, default="")
    topic: str = Column(String(500), nullable=False, default="")

    # Optional fields (None defaults)
    subtopic: str | None = Column(String(500), default=None)  # type: ignore[assignment]
    user_explanation: str | None = Column(Text, default=None)  # type: ignore[assignment]
    current_stage: str | None = Column(String(100), default=None)  # type: ignore[assignment]
    voice_profile: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    color_palette: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    taste_profile: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    style_guide: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    budget_limit_usd: float | None = Column(Float, default=None)  # type: ignore[assignment]
    error_message: str | None = Column(Text, default=None)  # type: ignore[assignment]
    output_video_path: str | None = Column(String, default=None)  # type: ignore[assignment]
    output_thumbnail_path: str | None = Column(String, default=None)  # type: ignore[assignment]
    completed_at: datetime | None = Column(DateTime, default=None)  # type: ignore[assignment]

    # Fields with non-None defaults
    target_duration_minutes: int = Column(Integer, default=45)
    target_audience: str = Column(String(50), default="intermediate")
    visual_style: str = Column(String(50), default="cinematic")
    pacing: str = Column(String(20), default="moderate")
    words_per_minute: int = Column(Integer, default=150)
    stage_statuses: dict = Column(JSONB, default=dict)
    budget_spent_usd: float = Column(Float, default=0.0)
    status: ProjectStatus = Column(SAEnum(ProjectStatus), default=ProjectStatus.DRAFT)

    # Timestamps (last for dataclass ordering)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)  # type: ignore[assignment]
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<Project {self.slug} ({self.status.value})>"

    @property
    def project_dir(self) -> Path:
        """Get the project's directory path."""
        return Path(settings.projects_dir) / str(self.id)


class StageRun(Base):
    """Record of a single pipeline stage execution."""

    __tablename__ = "stage_runs"

    # Relationships FIRST
    project: Project = relationship("Project", back_populates="stage_runs")  # type: ignore[assignment]
    approvals: list[Approval] = relationship("Approval", back_populates="stage_run", cascade="all, delete-orphan")  # type: ignore[assignment]

    # Columns
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, default=uuid.uuid4)
    stage_name: str = Column(String(100), nullable=False, index=True, default="")
    status: StageStatus = Column(SAEnum(StageStatus), default=StageStatus.PENDING)
    progress_pct: float = Column(Float, default=0.0)
    started_at: datetime | None = Column(DateTime, default=None)  # type: ignore[assignment]
    completed_at: datetime | None = Column(DateTime, default=None)  # type: ignore[assignment]
    input_artifacts: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    output_artifacts: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    logs: str | None = Column(Text, default=None)  # type: ignore[assignment]
    error_message: str | None = Column(Text, default=None)  # type: ignore[assignment]
    retry_count: int = Column(Integer, default=0)
    stage_metadata: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]  (renamed from 'metadata')

    created_at: datetime = Column(DateTime, default=datetime.utcnow)  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<StageRun {self.stage_name} ({self.status.value})>"


class Asset(Base):
    """Generated or uploaded asset for a project."""

    __tablename__ = "assets"

    # Relationships FIRST
    project: Project = relationship("Project", back_populates="assets")  # type: ignore[assignment]

    # Columns
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, default=uuid.uuid4)
    chapter_id: str | None = Column(String(50), index=True, default=None)  # type: ignore[assignment]
    scene_id: str | None = Column(String(50), index=True, default=None)  # type: ignore[assignment]
    asset_type: str = Column(String(50), nullable=False, default="")
    name: str | None = Column(String(255), default=None)  # type: ignore[assignment]
    file_path: str = Column(String, nullable=False, default="")
    file_size_bytes: int | None = Column(Integer, default=None)  # type: ignore[assignment]
    duration_seconds: float | None = Column(Float, default=None)  # type: ignore[assignment]
    mime_type: str | None = Column(String(100), default=None)  # type: ignore[assignment]
    asset_metadata: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]  (renamed from 'metadata')
    status: str = Column(String(50), default="pending")
    created_at: datetime = Column(DateTime, default=datetime.utcnow)  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<Asset {self.asset_type} {self.name or self.id}>"


class Approval(Base):
    """Human approval record for a pipeline stage."""

    __tablename__ = "approvals"

    # Relationships FIRST
    project: Project = relationship("Project", back_populates="approvals")  # type: ignore[assignment]
    stage_run: StageRun = relationship("StageRun", back_populates="approvals")  # type: ignore[assignment]

    # Columns
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, default=uuid.uuid4)
    stage_run_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("stage_runs.id"), nullable=False, default=uuid.uuid4)
    approval_type: str = Column(String(50), nullable=False, default="")
    status: ApprovalStatus = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    data: dict = Column(JSONB, nullable=False, default=dict)
    user_feedback: str | None = Column(Text, default=None)  # type: ignore[assignment]
    user_modified_data: dict | None = Column(JSONB, default=None)  # type: ignore[assignment]
    created_at: datetime = Column(DateTime, default=datetime.utcnow)  # type: ignore[assignment]
    resolved_at: datetime | None = Column(DateTime, default=None)  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<Approval {self.approval_type} ({self.status.value})>"
