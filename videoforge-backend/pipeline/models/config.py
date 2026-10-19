"""Pipeline configuration and stage definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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


@dataclass
class StageConfig:
    """Configuration for a single pipeline stage."""
    name: str
    description: str
    requires_approval: bool = False
    approval_type: str = "human"
    depends_on: list[str] = field(default_factory=list)
    estimated_seconds: int = 60
    can_skip: bool = False
    can_retry: bool = True
    produces: list[str] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)


# All 9 pipeline stages in execution order
PIPELINE_STAGES: list[StageConfig] = [
    StageConfig(
        name="research",
        description="Research the topic and gather authoritative sources",
        depends_on=[],
        estimated_seconds=120,
        produces=["research_notes", "sources"],
    ),
    StageConfig(
        name="proposal",
        description="Create a video proposal with outline and structure",
        depends_on=["research"],
        estimated_seconds=90,
        requires_approval=True,
        approval_type="concept",
        produces=["proposal"],
    ),
    StageConfig(
        name="script",
        description="Write the full narration script with timing",
        depends_on=["proposal"],
        estimated_seconds=180,
        produces=["script", "word_count"],
    ),
    StageConfig(
        name="chapterize",
        description="Break script into chapters with timing and visual notes",
        depends_on=["script"],
        estimated_seconds=60,
        produces=["chapters"],
    ),
    StageConfig(
        name="scene_plan",
        description="Design scene breakdown for each chapter",
        depends_on=["chapterize"],
        estimated_seconds=120,
        requires_approval=True,
        approval_type="scene_plan",
        produces=["scene_plan"],
    ),
    StageConfig(
        name="assets",
        description="Generate all visual and audio assets",
        depends_on=["scene_plan"],
        estimated_seconds=600,
        requires_approval=True,
        approval_type="assets",
        produces=["scenes", "audio_narrations", "music", "sfx"],
    ),
    StageConfig(
        name="edit",
        description="Assemble scenes with transitions and effects",
        depends_on=["assets"],
        estimated_seconds=180,
        produces=["edit_plan"],
    ),
    StageConfig(
        name="compose",
        description="Compose final video from scenes, audio, and effects",
        depends_on=["edit"],
        estimated_seconds=300,
        produces=["chapter_videos"],
    ),
    StageConfig(
        name="publish",
        description="Finalize, encode, and produce output files",
        depends_on=["compose"],
        estimated_seconds=120,
        produces=["final_video", "thumbnail", "metadata"],
    ),
]


def get_stage_config(name: str) -> StageConfig | None:
    """Get configuration for a specific stage."""
    for stage in PIPELINE_STAGES:
        if stage.name == name:
            return stage
    return None


def get_stage_names() -> list[str]:
    """Return ordered list of stage names."""
    return [s.name for s in PIPELINE_STAGES]


def validate_stage_order(stage_sequence: list[str]) -> bool:
    """Validate that a stage sequence respects dependencies."""
    completed = set()
    for stage_name in stage_sequence:
        config = get_stage_config(stage_name)
        if config is None:
            return False
        for dep in config.depends_on:
            if dep not in completed:
                return False
        completed.add(stage_name)
    return True
