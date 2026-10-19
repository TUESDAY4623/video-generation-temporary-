"""VideoForge — AI-powered video generation API.

Run with: uvicorn main:app --reload
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.events import lifespan
from app.utils.files import ensure_dir

settings = get_settings()
ensure_dir(settings.projects_dir)
ensure_dir(settings.storage_dir)
ensure_dir(settings.compose_dir)

logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered video generation from prompts",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"name": settings.app_name, "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/v1/ping")
async def ping():
    return {"message": "pong"}


@app.get("/api/v1/system/profile")
@app.get("/system/profile")
async def system_profile():
    from app.utils.hardware import SystemProfiler
    profile = SystemProfiler.get_profile(force_refresh=True)
    specs = SystemProfiler.get_specs()
    from dataclasses import asdict
    return {
        "status": "ok",
        "specs": asdict(specs),
        "profile": profile.to_dict(),
    }


from fastapi.staticfiles import StaticFiles
from app.api.routers import projects, pipeline, assets  # noqa: E402

app.include_router(projects.router, prefix=settings.api_prefix, tags=["projects"])
app.include_router(pipeline.router, prefix=settings.api_prefix, tags=["pipeline"])
app.include_router(assets.router, prefix=settings.api_prefix, tags=["assets"])

# Mount projects static directory for direct video playback and download in browser
if settings.projects_dir.exists():
    app.mount("/projects", StaticFiles(directory=str(settings.projects_dir)), name="projects")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, workers=1)
