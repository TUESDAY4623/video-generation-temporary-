"""Pipeline stages — ordered imports for the video generation pipeline."""

from pipeline.stages.base import Stage, StageError
from pipeline.stages.research import ResearchStage
from pipeline.stages.proposal import ProposalStage
from pipeline.stages.script import ScriptStage
from pipeline.stages.chapterize import ChapterizeStage
from pipeline.stages.scene_plan import ScenePlanStage
from pipeline.stages.semantic_visual_extractor import SemanticVisualExtractorStage
from pipeline.stages.assets import AssetsStage
from pipeline.stages.edit import EditStage
from pipeline.stages.compose import ComposeStage
from pipeline.stages.publish import PublishStage

__all__ = [
    "Stage",
    "StageError",
    "ResearchStage",
    "ProposalStage",
    "ScriptStage",
    "ChapterizeStage",
    "ScenePlanStage",
    "SemanticVisualExtractorStage",
    "AssetsStage",
    "EditStage",
    "ComposeStage",
    "PublishStage",
]
