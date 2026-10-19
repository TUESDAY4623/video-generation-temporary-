# VideoForge — AI Video Generation Pipeline

Transform a topic prompt into a professional 40-50 minute narrated video with visual explanations, animated scenes, and AI-generated audio.

## Quick Start

### 1. Prerequisites

```bash
# Python 3.11+
# PostgreSQL 14+
# Redis 7+
# FFmpeg
# Docker & Docker Compose
```

### 2. Install Dependencies

```bash
cd videoforge-backend
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
pip install -e .
```

### 3. Start Infrastructure

```bash
docker-compose up -d postgres redis
```

### 4. Start Local TTS (StyleTTS2)

```bash
cd "d:\Coder_S3\video generation v3\ElevenLabs\StyleTTS2"
pip install -r requirements.txt
python api.py
# Verify: curl http://localhost:8000/health
```

### 5. Start VideoForge

```bash
cd videoforge-backend
uvicorn main:app --reload
```

### 6. Create a Video Project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Tutorial",
    "topic": "Python Programming",
    "subtopic": "Lists and Data Structures",
    "user_explanation": "Comprehensive guide to Python lists, including slicing, comprehensions, and common operations",
    "target_duration_minutes": 45,
    "target_audience": "intermediate",
    "visual_style": "cinematic",
    "pacing": "moderate"
  }'
```

### 7. Start the Pipeline

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/{project_id}/start
```

Monitor progress via WebSocket:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/{project_id}");
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  9-Stage Pipeline Orchestrator                       │
│                                                      │
│  [1] RESEARCH   → Claude API researches topic        │
│  [2] PROPOSAL   → Chapter structure + visual plan    │
│  [3] SCRIPT     → Full narration with [VISUAL:] cues │
│  [4] CHAPTERIZE → Timed chapters + scene types       │
│  [5] SCENE_PLAN → Animation + transitions per scene  │
│  [6] ASSETS     → HTML scenes + audio (batch TTS)    │
│  [7] EDIT       → Edit plan + transitions            │
│  [8] COMPOSE    → Render HTML→MP4, concatenate clips │
│  [9] PUBLISH    → Final MP4 with music/intro/outro   │
└─────────────────────────────────────────────────────┘
    │
    ▼
Final Video (MP4) + Thumbnail
```

## Audio System (Local-First)

```
AudioService.generate(text)
    │
    ├─► StyleTTS2 (localhost:8000)     ← PRIMARY
    ├─► Seed-VC (localhost:8001)       ← VOICE CLONING
    ├─► MAA (localhost:8002)           ← SFX/MUSIC
    └─► ElevenLabs Cloud (API key)     ← FALLBACK
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects` | Create a new project |
| GET | `/api/v1/projects` | List all projects |
| GET | `/api/v1/projects/{id}` | Get project details |
| DELETE | `/api/v1/projects/{id}` | Delete a project |
| POST | `/api/v1/pipeline/{id}/start` | Start pipeline |
| POST | `/api/v1/pipeline/{id}/pause` | Pause pipeline |
| POST | `/api/v1/pipeline/{id}/abort` | Abort pipeline |
| GET | `/api/v1/pipeline/{id}/status` | Get pipeline status |
| WS | `/ws/{project_id}` | Real-time progress updates |

## Scene Types

| Type | Use Case |
|------|----------|
| `hero_title` | Opening title slide |
| `text_card` | General content |
| `stat_card` | Statistics and metrics |
| `callout` | Key takeaways |
| `comparison` | Side-by-side comparison |
| `bar_chart` | Bar chart data |
| `line_chart` | Trend data |
| `pie_chart` | Proportional data |
| `kpi_grid` | Dashboard metrics |
| `progress_bar` | Step-by-step process |
| `anime_scene` | Animated illustrations |
| `talking_head` | Presenter overlay |
| `code_viz` | Code with syntax highlighting |
| `diagram` | Architecture/flow diagrams |

## Configuration

Key environment variables in `.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Local TTS (StyleTTS2)
ELEVENLABS_STYL_TTS_URL=http://localhost:8000

# Optional: Voice cloning
ELEVENLABS_SEEDVC_URL=http://localhost:8001

# Optional: SFX/Music
ELEVENLABS_MAA_URL=http://localhost:8002

# Optional: Cloud fallback
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

## Directory Structure

```
videoforge-backend/
├── app/
│   ├── adapters/          # External service clients
│   ├── config.py          # Settings management
│   ├── core/              # Database, events, WebSocket
│   ├── generators/        # Code/chart/diagram generators
│   ├── models/            # SQLAlchemy models
│   ├── renderers/         # Video renderers
│   ├── routers/           # FastAPI routers
│   ├── schemas/           # Pydantic schemas
│   └── services/          # Business logic (audio, etc.)
├── pipeline/
│   ├── models/            # Pipeline config + entities
│   ├── quality/           # Quality checker
│   ├── stages/            # 9 pipeline stages
│   ├── templates/         # HTML scene templates
│   └── orchestrator.py    # Pipeline runner
├── workers/               # Celery tasks
└── main.py                # FastAPI entry point
```

## Troubleshooting

**StyleTTS2 won't start:**
- Ensure model checkpoints exist in `StyleTTS2/Models/LibriTTS/`
- Install espeak-ng: `apt-get install espeak-ng`
- Check CUDA compatibility if using GPU

**TTS fails for all scenes:**
- Check `ELEVENLABS_STYL_TTS_URL` in `.env`
- Verify StyleTTS2 is running: `curl http://localhost:8000/health`
- Check logs: StyleTTS2 outputs to stdout

**Pipeline hangs:**
- Ensure Redis is running: `docker-compose ps redis`
- Check Celery worker: `celery -A workers worker --loglevel=info`
- Monitor WebSocket for progress updates

**Video rendering fails:**
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check disk space for output files
- Verify HyperFrames is configured correctly
