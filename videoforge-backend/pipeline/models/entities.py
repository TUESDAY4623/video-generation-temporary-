"""Core data models for the video generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class StageName(str, Enum):
    RESEARCH = "research"
    PROPOSAL = "proposal"
    SCRIPT = "script"
    CHAPTERIZE = "chapterize"
    SCENE_PLAN = "scene_plan"
    ASSETS = "assets"
    EDIT = "edit"
    COMPOSE = "compose"
    PUBLISH = "publish"


class SceneType(str, Enum):
    HERO_TITLE = "hero_title"
    TEXT_CARD = "text_card"
    STAT_CARD = "stat_card"
    CALLOUT = "callout"
    COMPARISON = "comparison"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    KPI_GRID = "kpi_grid"
    PROGRESS_BAR = "progress_bar"
    ANIME_SCENE = "anime_scene"
    TALKING_HEAD = "talking_head"
    CODE_VIZ = "code_viz"
    DIAGRAM = "diagram"


class VisualStyle(str, Enum):
    CINEMATIC = "cinematic"
    MINIMAL = "minimal"
    CORPORATE = "corporate"
    EDUCATIONAL = "educational"
    ANIME = "anime"
    RETRO = "retro"
    DOCUMENTARY = "documentary"


class Pacing(str, Enum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"
    VARIED = "varied"


class Audience(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    GENERAL = "general"


@dataclass
class PipelineContext:
    """The central context object passed through all pipeline stages.

    Each stage reads what it needs and writes its output.
    Stages are pure functions of (context) -> context with side effects on the
    sidecar ``StageRun`` record.
    """

    project_id: UUID
    topic: str
    subtopic: str | None = None
    user_explanation: str | None = None
    target_duration_minutes: int = 45
    target_audience: Audience = Audience.INTERMEDIATE
    visual_style: VisualStyle = VisualStyle.CINEMATIC
    pacing: Pacing = Pacing.MODERATE
    words_per_minute: int = 150
    budget_limit_usd: float | None = None

    # Research output
    research_notes: str | None = None
    sources: list[dict] = field(default_factory=list)

    # Proposal output
    proposal: dict | None = None

    # Script output
    script_text: str | None = None
    word_count: int = 0
    estimated_duration_seconds: float = 0.0

    # Chapter output
    chapters: list[dict] = field(default_factory=list)

    # Scene plan
    scenes: list[dict] = field(default_factory=list)

    # Assets
    narration_audio_paths: dict[str, str] = field(default_factory=dict)
    music_path: str | None = None
    sfx_paths: list[str] = field(default_factory=list)

    # Edit plan
    transitions: list[dict] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)

    # Compose
    chapter_video_paths: list[str] = field(default_factory=list)

    # Publish
    final_video_path: str | None = None
    thumbnail_path: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_words_for_duration(self, minutes: float) -> int:
        """Calculate word count needed for a given duration."""
        return int(minutes * self.words_per_minute)

    def get_duration_for_words(self, words: int) -> float:
        """Calculate duration in seconds for a given word count."""
        return (words / self.words_per_minute) * 60

    def remaining_budget(self, current_spend: float) -> float | None:
        """Calculate remaining budget."""
        if self.budget_limit_usd is None:
            return None
        return self.budget_limit_usd - current_spend


@dataclass
class Chapter:
    """A chapter of the video."""

    chapter_number: int
    title: str
    summary: str
    script_section: str
    word_count: int
    duration_seconds: float
    scenes: list[dict] = field(default_factory=list)
    narration_paths: dict[str, str] = field(default_factory=dict)
    video_path: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Scene:
    """A single scene within a chapter."""

    scene_id: str
    scene_type: SceneType
    chapter_number: int
    title: str
    script_text: str
    duration_seconds: float
    narration_path: str | None = None
    html_path: str | None = None
    video_path: str | None = None
    thumbnail_path: str | None = None
    visual_params: dict = field(default_factory=dict)
    transitions: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SceneGenerationRequest:
    """Request to generate a single scene."""

    scene: Scene
    context: PipelineContext
    template_name: str | None = None
    output_dir: str | None = None

    def get_output_path(self) -> str:
        if self.output_dir:
            import os
            return os.path.join(self.output_dir, f"scene_{self.scene.scene_id}.html")
        return f"scene_{self.scene.scene_id}.html"
