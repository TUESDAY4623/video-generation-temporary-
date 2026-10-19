"""Pipeline orchestrator — executes all stages sequentially with checkpoint support."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.events import PipelineEvent
from app.core.websocket import manager
from app.models.project import Project, StageRun, StageStatus
from pipeline.models.config import PIPELINE_STAGES, StageConfig
from pipeline.models.entities import PipelineContext
from pipeline.quality.checker import QualityChecker
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the execution of all pipeline stages for a project."""

    def __init__(self, db, project_id, project_dir: Path):
        self.db = db
        self.project_id = project_id
        self.project_dir = project_dir
        self.settings = get_settings()
        self.checker = QualityChecker()
        self._stage_instances: dict[str, tuple[StageRun, Stage]] = {}
        self._abort = False
        self._start_time: float = 0.0

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Run the full pipeline for a project."""
        self._start_time = time.time()
        total_stages = len(PIPELINE_STAGES)

        await manager.send_event(
            str(self.project_id),
            PipelineEvent.started(str(self.project_id), total_stages),
        )

        try:
            for i, stage_config in enumerate(PIPELINE_STAGES):
                if self._abort:
                    raise StageError("Pipeline aborted by user", retryable=False)

                await self._execute_stage(context, stage_config, i, total_stages)

            # Mark project complete
            project = self.db.get(Project, self.project_id)
            if project:
                project.status = ProjectStatus.COMPLETE
                project.current_stage = "publish"
                self.db.commit()

            elapsed = time.time() - self._start_time
            await manager.send_event(
                str(self.project_id),
                PipelineEvent.complete(
                    str(self.project_id),
                    context.final_video_path or "",
                    elapsed,
                ),
            )

            logger.info(f"Pipeline complete for project {self.project_id} in {elapsed:.1f}s")
            return context

        except StageError as e:
            project = self.db.get(Project, self.project_id)
            if project:
                project.status = ProjectStatus.FAILED
                project.error_message = str(e)
                self.db.commit()

            await manager.send_event(
                str(self.project_id),
                PipelineEvent.failed(str(self.project_id), "unknown", str(e)),
            )
            raise

    async def _execute_stage(
        self, context: PipelineContext, config: StageConfig,
        index: int, total: int
    ) -> None:
        """Execute a single stage."""
        stage_name = config.name

        # Report overall progress
        await manager.send_event(
            str(self.project_id),
            PipelineEvent.progress(
                str(self.project_id), stage_name, index, total,
                f"Starting {config.description}...",
            ),
        )

        # Create StageRun record
        stage_run = StageRun(
            project_id=self.project_id,
            stage_name=stage_name,
            status=StageStatus.PENDING,
            progress_pct=0.0,
        )
        self.db.add(stage_run)
        self.db.flush()

        try:
            # Create and run stage
            stage = self._create_stage(stage_name, stage_run)
            stage.set_progress_callback(
                lambda pct, msg: self._on_stage_progress(stage_run, stage_name, pct, msg)
            )

            # Ensure stage directory exists
            stage_dir = self.project_dir / "stages" / stage_name
            stage_dir.mkdir(parents=True, exist_ok=True)
            context.metadata["stage_dir"] = str(stage_dir)

            result_context = await stage.run(context)

            # Update context with result
            context = result_context

            # Run quality check
            quality = self._quality_check(stage_name, context)
            if not quality.is_passing:
                logger.warning(
                    f"Quality check warnings for {stage_name}: "
                    f"{', '.join(quality.issues)}"
                )

            stage_run.status = StageStatus.COMPLETE
            stage_run.progress_pct = 100.0
            stage_run.output_artifacts = self._collect_artifacts(stage_name, context)
            self.db.commit()

        except Exception as e:
            stage_run.status = StageStatus.FAILED
            stage_run.error_message = str(e)
            self.db.commit()
            raise

    def _create_stage(self, name: str, stage_run: StageRun) -> Stage:
        """Create a stage instance by name."""
        # Import here to avoid circular imports
        from pipeline.stages.research import ResearchStage
        from pipeline.stages.proposal import ProposalStage
        from pipeline.stages.script import ScriptStage
        from pipeline.stages.chapterize import ChapterizeStage
        from pipeline.stages.scene_plan import ScenePlanStage
        from pipeline.stages.assets import AssetsStage
        from pipeline.stages.edit import EditStage
        from pipeline.stages.compose import ComposeStage
        from pipeline.stages.publish import PublishStage

        stage_map = {
            "research": ResearchStage,
            "proposal": ProposalStage,
            "script": ScriptStage,
            "chapterize": ChapterizeStage,
            "scene_plan": ScenePlanStage,
            "assets": AssetsStage,
            "edit": EditStage,
            "compose": ComposeStage,
            "publish": PublishStage,
        }

        stage_class = stage_map.get(name)
        if not stage_class:
            raise ValueError(f"Unknown stage: {name}")

        return stage_class(self.db, stage_run)

    def _quality_check(self, stage_name: str, context: PipelineContext) -> Any:
        """Run quality checks for a stage."""
        if stage_name == "scene_plan":
            total_score = 1.0
            for chapter in context.chapters:
                q = self.checker.check_chapter(chapter)
                total_score = min(total_score, q.score)
            return type("QL", (), {"is_passing": total_score >= 0.7, "issues": []})()
        return type("QL", (), {"is_passing": True, "issues": []})()

    def _collect_artifacts(self, stage_name: str, context: PipelineContext) -> dict:
        """Collect output artifacts from a stage."""
        artifacts = {}

        if stage_name == "research":
            artifacts = {
                "research_notes": context.research_notes[:200] if context.research_notes else "",
                "sources_count": len(context.sources),
            }
        elif stage_name == "proposal":
            artifacts = {
                "chapters_planned": len(context.proposal.get("chapters", [])) if context.proposal else 0,
            }
        elif stage_name == "script":
            artifacts = {
                "word_count": context.word_count,
                "duration_seconds": context.estimated_duration_seconds,
            }
        elif stage_name == "chapterize":
            artifacts = {
                "chapters": len(context.chapters),
            }
        elif stage_name == "scene_plan":
            artifacts = {
                "scenes": len(context.scenes),
            }
        elif stage_name == "assets":
            artifacts = {
                "narrations": len(context.narration_audio_paths),
                "music": 1 if context.music_path else 0,
                "sfx": len(context.sfx_paths),
            }
        elif stage_name == "compose":
            artifacts = {
                "chapter_videos": len(context.chapter_video_paths),
            }
        elif stage_name == "publish":
            artifacts = {
                "final_video": context.final_video_path or "",
                "thumbnail": context.thumbnail_path or "",
            }

        return artifacts

    def _on_stage_progress(
        self, stage_run: StageRun, stage_name: str, pct: float, msg: str
    ) -> None:
        """Handle progress updates from a stage."""
        stage_run.progress_pct = pct
        self.db.merge(stage_run)
        self.db.commit()

    def abort(self) -> None:
        """Abort the pipeline."""
        self._abort = True
        for _, (stage_run, stage) in self._stage_instances.items():
            stage.abort()
