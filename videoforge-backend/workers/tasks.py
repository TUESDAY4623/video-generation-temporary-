"""Celery tasks for async video generation pipeline."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.database import SessionLocal
from app.models.project import Project, ProjectStatus
from app.services import audio_service
from app.services.audio import AudioRequest
from app.utils.files import ensure_dir
from app.config import get_settings
from pipeline.models.entities import PipelineContext
from pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


def run_pipeline(project_id: str) -> dict:
    """Celery task to run the full video generation pipeline.

    This is a synchronous wrapper because Celery tasks are sync by default.
    It creates an event loop to run the async orchestrator.
    """
    db = SessionLocal()
    try:
        project_uuid = UUID(project_id)
        project = db.get(Project, project_uuid)
        if not project:
            logger.error(f"Project {project_id} not found")
            return {"status": "error", "message": "Project not found"}

        if project.status in (ProjectStatus.GENERATING, ProjectStatus.RENDERING):
            logger.warning(f"Project {project_id} already running")
            return {"status": "error", "message": "Pipeline already running"}

        project.status = ProjectStatus.GENERATING
        project.current_stage = "research"
        db.commit()

        context = PipelineContext.from_project(project)

        orchestrator = PipelineOrchestrator(db, str(project_uuid), project.project_dir)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(orchestrator.execute(context))
            logger.info(f"Pipeline complete for project {project_id}")
            return {
                "status": "complete",
                "project_id": project_id,
                "video_path": result.final_video_path or "",
            }
        except Exception as e:
            logger.error(f"Pipeline failed for project {project_id}: {e}")
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            db.commit()
            return {"status": "failed", "project_id": project_id, "error": str(e)}
        finally:
            loop.close()

    finally:
        db.close()


def generate_narration(project_id: str, scene_id: str, text: str, voice_id: str) -> dict:
    """Celery task to generate narration audio for a scene."""
    settings = get_settings()
    output_dir = ensure_dir(settings.storage_dir / "audio" / project_id)
    output_path = output_dir / f"narration_{scene_id}.mp3"

    async def _generate():
        result = await audio_service.generate(AudioRequest(
            text=text,
            voice_id=voice_id,
            output_path=output_path,
        ))
        if result.success and result.output_path:
            return {"audio_path": str(result.output_path), "scene_id": scene_id}
        return {"audio_path": "", "scene_id": scene_id, "error": result.error}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


def render_scene(project_id: str, scene_id: str, html_path: str) -> dict:
    """Celery task to render a single scene HTML to video."""
    from app.adapters.hyperframes_adapter import HyperFramesAdapter
    from app.utils.files import ensure_dir
    from app.config import get_settings

    settings = get_settings()
    output_dir = ensure_dir(settings.storage_dir / "scenes" / project_id)
    output_path = output_dir / f"{scene_id}.mp4"

    async def _render():
        adapter = HyperFramesAdapter()
        path = await adapter.render_scene(
            html_content=html_path,
            output_path=str(output_path),
            width=1920,
            height=1080,
            fps=30,
        )
        return {"video_path": str(path), "scene_id": scene_id}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_render())
    finally:
        loop.close()
