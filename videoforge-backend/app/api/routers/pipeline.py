"""Pipeline router."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.schemas.pipeline import PipelineStartResponse, PipelineStatusResponse
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.models.entities import PipelineContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{project_id}/start", response_model=PipelineStartResponse)
async def start_pipeline(project_id: UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if project.status in (ProjectStatus.GENERATING, ProjectStatus.RENDERING):
        raise HTTPException(400, f"Pipeline already running (status: {project.status})")

    project.status = ProjectStatus.GENERATING
    project.current_stage = "research"
    db.commit()

    context = PipelineContext.from_project(project)
    orchestrator = PipelineOrchestrator(db, str(project_id), project.project_dir)

    try:
        result = await orchestrator.execute(context)
        return PipelineStartResponse(
            project_id=project_id,
            message="Pipeline completed",
            celery_task_id=None,
        )
    except Exception as e:
        project.status = ProjectStatus.FAILED
        project.error_message = str(e)
        db.commit()
        logger.error(f"Pipeline failed for {project_id}: {e}")
        raise HTTPException(500, f"Pipeline failed: {e}")


@router.get("/{project_id}/status", response_model=PipelineStatusResponse)
def get_pipeline_status(project_id: UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    from app.models.project import StageRun
    stages = db.query(StageRun).filter(StageRun.project_id == project_id).order_by(StageRun.created_at).all()

    return PipelineStatusResponse(
        project_id=project_id,
        status=project.status,
        current_stage=project.current_stage,
        progress_pct=project.progress_pct or 0.0,
        stages=stages,
    )


@router.post("/{project_id}/abort")
async def abort_pipeline(project_id: UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.status = ProjectStatus.CANCELLED
    db.commit()
    return {"message": "Pipeline aborted", "project_id": project_id}
