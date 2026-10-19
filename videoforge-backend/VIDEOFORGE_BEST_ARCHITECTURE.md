# VideoForge Best Architecture

## Executive Summary

VideoForge is a professional AI-powered video generation system that produces 40-50 minute educational videos from a simple user prompt. This document describes the best-practice architecture, component interactions, and data flow.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIDEOFORGE BACKEND                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   FastAPI    │    │   WebSocket  │    │   Celery Workers     │  │
│  │     API      │◄──►│   Manager    │    │   (Async Pipeline)   │  │
│  │   :8000      │    │   Events     │    │                      │  │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘  │
│         │                                           │               │
│  ┌──────▼───────────────────────────────────────────▼───────────┐  │
│  │                     Pipeline Orchestrator                      │  │
│  │   Coordinates all 9 stages with checkpointing & retry logic   │  │
│  └──────┬────────────────────────────────────────────────────────┘  │
│         │                                                           │
│  ┌──────▼──────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │  9 Stages       │  │  Quality       │  │  Asset Generator   │   │
│  │  (research →    │  │  Checker       │  │  (parallel)        │   │
│  │   publish)      │  │                │  │                    │   │
│  └─────────────────┘  └────────────────┘  └────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                         DATA LAYER                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│  │  PostgreSQL    │  │     Redis      │  │  Local Storage       │   │
│  │  (Projects,    │  │  (Cache +      │  │  (HTML, Audio,       │   │
│  │  Assets, etc)  │  │   Queue)       │  │   Video, Templates)  │   │
│  └────────────────┘  └────────────────┘  └──────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        EXTERNAL SERVICES                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Claude API  │  │  ElevenLabs  │  │  HyperFrames / Presenton │  │
│  │  (Anthropic) │  │  (Optional)  │  │  (HTML → Video Render)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ STY-TTS      │  │  SeedVC      │  │  FFmpeg                  │  │
│  │ :5001        │  │  :5002       │  │  (Audio/Video mixing)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## The 9-Stage Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ STAGE 1  │───►│ STAGE 2  │───►│ STAGE 3  │───►│ STAGE 4  │
│ RESEARCH │    │ PROPOSAL │    │  SCRIPT  │    │CHAPTERIZE│
│          │    │          │    │          │    │          │
│  Input:  │    │  Input:  │    │  Input:  │    │  Input:  │
│  topic   │    │ research │    │ research │    │  script  │
│          │    │ results  │    │ + propsl │    │          │
│ Output:  │    │ Output:  │    │ Output:  │    │ Output:  │
│ research │    │chapter   │    │ narration│    │ chapters │
│ report   │    │ outline  │    │ script   │    │ + scenes │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                  │
                                                  ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ STAGE 9  │◄───│ STAGE 8  │◄───│ STAGE 7  │◄───│ STAGE 5  │
│ PUBLISH  │    │ COMPOSE  │    │   EDIT   │    │SCENE PLAN│
│          │    │          │    │          │    │          │
│  Input:  │    │  Input:  │    │  Input:  │    │  Input:  │
│ chapter  │    │  scenes  │    │  assets  │    │ chapters │
│ videos   │    │  + audio │    │  + scene │    │ + timing │
│          │    │          │    │   plans  │    │          │
│ Output:  │    │ Output:  │    │ Output:  │    │ Output:  │
│ final    │    │ chapter  │    │ edited   │    │ scene    │
│ MP4      │    │ videos   │    │  scenes  │    │ specs    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                  │
                                                  ▼
                                            ┌──────────┐
                                            │ STAGE 6  │
                                            │  ASSETS  │
                                            │          │
                                            │ Parallel │
                                            │generation│
                                            │          │
                                            │ • Audio  │
                                            │ • HTML   │
                                            │ • Code   │
                                            │ • Charts │
                                            │ • Music  │
                                            └──────────┘
```

## Scene Types (14 Total)

| # | Scene Type | Purpose | Visual Style |
|---|-----------|---------|--------------|
| 1 | **hero_title** | Opening chapter title with animated badge | Large text, gradient background |
| 2 | **text_card** | Clean text explanation | Divider accent, readable paragraphs |
| 3 | **stat_card** | Highlight key numbers | Scale-in animation, large typography |
| 4 | **callout** | Emphasize important points | Bordered box with accent |
| 5 | **bar_chart** | Compare values | Chart.js animated bars |
| 6 | **line_chart** | Show trends over time | Chart.js smooth curve |
| 7 | **pie_chart** | Show proportions | Chart.js doughnut |
| 8 | **comparison** | Side-by-side | VS layout, two panels |
| 9 | **kpi_grid** | Display 3 KPIs | Staggered card animation |
| 10 | **progress_bar** | Show steps/flow | Numbered step layout |
| 11 | **anime_scene** | Engaging visual break | Particles, floating animation |
| 12 | **talking_head** | Presenter explanation | Avatar + speech bubble |
| 13 | **code_viz** | Code walkthrough | GitHub-dark syntax highlighting |
| 14 | **diagram** | Architecture/flow | Mermaid.js diagrams |

## Data Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│         PipelineContext             │
│  ┌───────────────────────────────┐  │
│  │ project_id, topic, subtopic   │  │
│  │ user_explanation              │  │
│  │ target_duration_minutes       │  │
│  │ visual_style, color_palette   │  │
│  │ chapters: list[Chapter]       │  │
│  │ scenes: list[Scene]           │  │
│  │ assets: list[Asset]           │  │
│  │ final_video_path              │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 1: Research             │
│  Claude → web_search → facts        │
│  Output: research_report            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 2: Proposal             │
│  Claude → chapter outline           │
│  Output: chapter_proposal           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 3: Script               │
│  Claude → narration script          │
│  Output: script with [VISUAL:]      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 4: Chapterize           │
│  Claude → timed chapters/scenes     │
│  Output: chapters with scene list   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 5: Scene Plan           │
│  Claude → scene type assignments    │
│  Output: scene specs with types     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 6: Assets               │
│  ┌──────────────────────────────┐   │
│  │ • ElevenLabs → audio/*.mp3  │   │
│  │ • Templates → html/*.html   │   │
│  │ • CodeViz → png/*.png       │   │
│  │ • Charts → html/*.html      │   │
│  │ • Diagrams → html/*.html    │   │
│  │ • Music → bgm/*.mp3         │   │
│  └──────────────────────────────┘   │
│  Output: all scene assets           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 7: Edit                 │
│  FFmpeg → sync audio + captions     │
│  Output: edited scene videos        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 8: Compose              │
│  HyperFrames → render HTML → MP4    │
│  Output: chapter video files        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Stage 9: Publish              │
│  FFmpeg → add music, intro, outro   │
│  Output: final_video.mp4            │
└─────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI | REST API + WebSocket |
| **Database** | PostgreSQL | Project/asset storage |
| **Cache/Queue** | Redis | Celery broker + cache |
| **AI/Content** | Claude (Anthropic) | Research, script, planning |
| **Voice** | ElevenLabs + STY-TTS + SeedVC | Narration generation |
| **Rendering** | HyperFrames + Presenton | HTML → video |
| **Audio/Video** | FFmpeg | Mixing, encoding, composition |
| **Task Queue** | Celery | Async pipeline execution |
| **Container** | Docker + Compose | Deployment |

## Directory Structure

```
videoforge-backend/
├── main.py                        # FastAPI entry point
├── pyproject.toml                 # Dependencies + build config
├── Dockerfile                     # Container image
├── docker-compose.yml             # Local services (postgres, redis, celery)
├── .env.example                   # Environment template
├── README.md                      # Documentation
│
├── app/
│   ├── config.py                  # All environment config
│   ├── __init__.py
│   ├── adapters/                  # Service clients (same as root adapters/)
│   │   ├── __init__.py
│   │   ├── anthropic_adapter.py   # Claude API calls
│   │   ├── base.py                # Base adapter class
│   │   ├── elevenlabs_adapter.py  # Voice generation
│   │   ├── ffmpeg_adapter.py      # Video/audio composition
│   │   ├── hyperframes_adapter.py # HTML → video rendering
│   │   └── presenton_adapter.py   # Slide/frame generation
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── projects.py        # CRUD for projects
│   │       ├── pipeline.py        # Start/stop/status
│   │       └── assets.py          # Asset management
│   ├── core/
│   │   ├── database.py            # SQLAlchemy engine + sessions
│   │   ├── events.py              # Event factory classes + lifespan
│   │   └── websocket.py           # WebSocket connection manager
│   ├── generators/
│   │   └── __init__.py            # CodeVisualization, Chart, Diagram
│   ├── models/
│   │   └── project.py             # SQLAlchemy: Project, StageRun, Asset, Approval
│   ├── renderers/
│   │   └── __init__.py            # HyperFrames, Remotion, FFmpeg
│   ├── schemas/
│   │   ├── project.py             # Pydantic request/response
│   │   ├── pipeline.py            # Pipeline status schemas
│   │   └── asset.py               # Asset CRUD schemas
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text.py                # slugify, word_count, etc.
│   │   └── files.py               # ensure_dir, safe_write, etc.
│   └── workers/
│       └── tasks/                 # Worker sub-tasks
│
├── adapters/                      # Root-level adapters (same files)
├── generators/                    # Re-export from app.generators
├── renderers/                     # Re-export from app.renderers
├── utils/                         # Re-export from app.utils
│
├── pipeline/
│   ├── orchestrator.py            # Runs all 9 stages sequentially
│   ├── models/
│   │   ├── config.py              # StageConfig + PIPELINE_STAGES
│   │   └── entities.py            # PipelineContext, SceneType, etc.
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── base.py                # Stage ABC with retry/approval
│   │   ├── research.py            # Stage 1
│   │   ├── proposal.py            # Stage 2
│   │   ├── script.py              # Stage 3
│   │   ├── chapterize.py          # Stage 4
│   │   ├── scene_plan.py          # Stage 5
│   │   ├── assets.py              # Stage 6
│   │   ├── edit.py                # Stage 7
│   │   ├── compose.py             # Stage 8
│   │   └── publish.py             # Stage 9
│   ├── quality/
│   │   └── checker.py             # Quality validation
│   ├── templates/
│   │   ├── registry.py            # Template manager
│   │   └── scenes/                # 14 HTML templates
│   │       ├── hero_title.html
│   │       ├── text_card.html
│   │       ├── stat_card.html
│   │       ├── callout.html
│   │       ├── bar_chart.html
│   │       ├── line_chart.html
│   │       ├── pie_chart.html
│   │       ├── comparison.html
│   │       ├── kpi_grid.html
│   │       ├── progress_bar.html
│   │       ├── anime_scene.html
│   │       ├── talking_head.html
│   │       ├── code_viz.html
│   │       └── diagram.html
│   └── skills/                    # HyperFrames rendering skills
│       ├── embedded-captions/
│       ├── motion-doctrine/
│       └── changelog-video/
│
├── workers/
│   ├── __init__.py
│   ├── tasks.py                   # Celery tasks
│   └── schedule.py                # Celery Beat schedule
│
├── templates/                     # Jinja2 templates (future)
└── tests/
    ├── fixtures/
    ├── unit/
    └── integration/
```

## API Reference

### Create Project

```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "Introduction to Machine Learning",
  "topic": "Machine Learning",
  "subtopic": "Neural Networks",
  "user_explanation": "Explain how neural networks learn through backpropagation",
  "target_duration_minutes": 45,
  "target_audience": "intermediate",
  "visual_style": "cinematic",
  "pacing": "moderate"
}
```

### Start Pipeline

```http
POST /api/v1/pipeline/{project_id}/start
```

### Get Pipeline Status

```http
GET /api/v1/pipeline/{project_id}/status
```

### WebSocket Events

```
ws://localhost:8000/api/v1/ws/{project_id}
```

Events emitted:
- `pipeline_started`
- `pipeline_progress`
- `stage_started`
- `stage_progress`
- `stage_complete`
- `render_progress`
- `pipeline_complete`
- `pipeline_failed`

## Deployment

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

### Manual Setup

```bash
# 1. Install dependencies
pip install -e .

# 2. Start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=videoforge \
  -e POSTGRES_PASSWORD=videoforge \
  postgres:16-alpine

# 3. Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# 4. Run server
uvicorn main:app --reload

# 5. Run Celery worker
celery -A workers worker --loglevel=info

# 6. Run Celery beat
celery -A workers beat --loglevel=info
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Target video duration | 40-50 minutes |
| Total generation time | ~50-60 minutes |
| Parallel asset generation | Yes (Stage 6) |
| Scene types supported | 14 |
| Max concurrent renders | 2 (Celery workers) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| API framework | FastAPI |

## Cost Estimation

For a 45-minute video:
- Claude API calls: ~$2-5 (research + script + planning)
- ElevenLabs (optional): ~$3-8 (narration)
- HyperFrames rendering: Free (self-hosted)
- Infrastructure: Free (local)

Total: **$5-13 per video** (mostly AI API costs)

## Future Enhancements

1. **Frontend Dashboard** — React/Vue web interface for project management
2. **Multi-language** — Support for non-English narration
3. **Custom Voices** — Voice cloning from local samples
4. **Batch Processing** — Queue multiple videos
5. **YouTube Integration** — Direct upload to YouTube
6. **Analytics** — Track video performance
7. **Template Marketplace** — Share custom scene templates
8. **Real-time Preview** — Live preview during generation
