# VideoForge — Best-in-Class Video Generation System

> Design focused on **output quality, creative control, and seamless production experience**.
> No cost optimization. No shortcuts. Best possible result.

---

## Philosophy

Most AI video tools produce "template-filled slides with voiceover." VideoForge produces **cinematic educational experiences** — the kind you'd see from a professional motion design studio.

The difference is in four things:

| What | Typical Tool | VideoForge |
|------|-------------|------------|
| Motion | Static slides + fade transitions | GSAP timelines, particle systems, camera moves, easing choreography |
| Visual Variety | Same slide layout repeated | 12+ scene types, no two consecutive scenes look alike |
| Audio | Robotic TTS over silence | Layered: narration + ducked music + SFX + word-synced captions |
| Code | Screenshot of code | Animated typing, line-by-line walkthrough, live highlighting |
| Control | "Generate and hope" | Human review gates at every stage, editable at any point |

---

## The Full Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │ Pipeline  │ │  Script   │ │  Scene   │ │    Video Preview    │   │
│  │ Timeline  │ │  Editor   │ │  Canvas  │ │   (live-updating)   │   │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │  Project  │ │  Asset    │ │  Render  │ │   Approval Gates    │   │
│  │  Gallery  │ │  Library  │ │  Queue   │ │   (concept/script/  │   │
│  │           │ │           │ │          │ │    scenes/assets)   │   │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ WebSocket + REST
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Celery)                       │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐   │
│  │  API Server  │  │  Task Queue   │  │   WebSocket Hub         │   │
│  │  (FastAPI)   │  │  (Celery +    │  │   (real-time progress)  │   │
│  │              │  │   Redis)      │  │                         │   │
│  └──────────────┘  └───────────────┘  └─────────────────────────┘   │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐   │
│  │  Project     │  │  Agent        │  │   Stage Runners         │   │
│  │  Manager     │  │  Runner       │  │   (one per pipeline     │   │
│  │  (CRUD +     │  │  (OpenMontage │  │  stage, parallelizable) │   │
│  │   state)     │  │   agent exec) │  │                         │   │
│  └──────────────┘  └───────────────┘  └─────────────────────────┘   │
└────────┬──────────────┬──────────────┬──────────────────────────────┘
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴──────────┐
    ▼         ▼   ▼         ▼   ▼              ▼
┌─────────┐ ┌───────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│ Claude  │ │Present│ │Local   │ │HyperFrames││  FFmpeg  │
│ API     │ │  on   │ │Eleven  │ │  Engine  │ │  Engine  │
│(Content)│ │(Slides)│ │Labs   │ │(Render)  │ │(Stitch)  │
│         │ │       │ │(TTS)   │ │          │ │          │
│ Sonnet  │ │FastAPI│ │StyleTTS│ │GSAP/3D/  │ │Concat/   │
│ Haiku   │ │5001   │ │SeedVC  │ │Lottie    │ │Subs/Mix  │
└─────────┘ └───────┘ └────────┘ └──────────┘ └──────────┘
```

---

## Part 1: Backend Architecture

### 1.1 API Server (FastAPI)

```
app/
├── __init__.py
├── main.py                    # FastAPI app, WebSocket hub, middleware
├── config.py                  # Settings via pydantic-settings
│
├── api/
│   ├── __init__.py
│   ├── routers/
│   │   ├── projects.py        # CRUD for video projects
│   │   ├── pipeline.py        # Start/stop/resume pipeline
│   │   ├── stages.py          # Get stage status, approve/reject
│   │   ├── assets.py          # Browse/upload/download assets
│   │   ├── preview.py         # Scene preview generation
│   │   ├── settings.py        # API keys, service config
│   │   └── health.py          # Service health checks
│   └── dependencies.py        # DB session, auth, etc.
│
├── models/
│   ├── __init__.py
│   ├── project.py             # SQLAlchemy Project model
│   ├── stage_run.py           # Stage execution record
│   ├── asset.py               # Asset metadata
│   └── user.py                # User/auth (future)
│
├── schemas/
│   ├── __init__.py
│   ├── project.py             # Pydantic schemas for API
│   ├── pipeline.py
│   ├── stage.py
│   └── asset.py
│
├── core/
│   ├── __init__.py
│   ├── database.py            # SQLAlchemy engine + session
│   ├── websocket.py           # WebSocket hub manager
│   ├── progress.py            # Progress event system
│   ├── auth.py                # API key auth
│   └── storage.py             # File storage abstraction
│
├── services/
│   ├── __init__.py
│   ├── project_service.py     # Project CRUD + state management
│   ├── pipeline_service.py    # Pipeline orchestration
│   └── preview_service.py     # Scene preview generation
│
└── workers/
    ├── __init__.py
    ├── celery_app.py          # Celery configuration
    └── tasks/
        ├── __init__.py
        ├── pipeline_runner.py # Celery task: run full pipeline
        ├── stage_runner.py    # Celery task: run single stage
        └── preview_runner.py  # Celery task: generate preview
```

### 1.2 Task Queue (Celery + Redis)

```
Pipeline execution model:
  ┌─────────────┐
  │  User clicks │
  │ "Generate"  │
  └──────┬──────┘
         │
         ▼
  ┌─────────────────────────────────────────┐
  │  celery_app.py                          │
  │  @app.task(bind=True)                   │
  │  def run_pipeline(self, project_id):    │
  │      pipeline = Pipeline(project_id)    │
  │      for stage in pipeline.stages:      │
  │          result = stage.run()           │
  │          self.update_state(             │
  │              state=PROGRESS,            │
  │              meta={                     │
  │                  "stage": stage.name,   │
  │                  "progress": 0.0,       │
  │                  "message": "..."       │
  │              }                          │
  │          )                              │
  │          if not result.approved:        │
  │              break  # Wait for approval │
  │      return pipeline.final_result       │
  └─────────────────────────────────────────┘
         │
         │ publishes progress events
         ▼
  ┌─────────────────────────────────────────┐
  │  Redis Pub/Sub                          │
  │  channel: pipeline:{project_id}         │
  │  messages: {stage, progress, message,   │
  │            scene_preview_url, log}      │
  └─────────────────────────────────────────┘
         │
         │ subscribed by
         ▼
  ┌─────────────────────────────────────────┐
  │  WebSocket Hub                          │
  │  broadcasts to all connected clients    │
  │  for this project                       │
  └─────────────────────────────────────────┘
```

### 1.3 Database Schema

```sql
-- projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    topic VARCHAR(500) NOT NULL,
    subtopic VARCHAR(500),
    user_explanation TEXT,
    target_duration_minutes INTEGER DEFAULT 45,
    target_audience VARCHAR(50) DEFAULT 'intermediate',
    visual_style VARCHAR(50) DEFAULT 'cinematic',
    voice_profile JSONB,
    color_palette JSONB,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, planning, generating, rendering, complete, failed
    current_stage VARCHAR(50),
    stage_status JSONB,                  -- per-stage status map
    budget_limit_usd DECIMAL(10,2),
    budget_spent_usd DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);

-- stages table (execution log)
CREATE TABLE stage_runs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    stage_name VARCHAR(100) NOT NULL,  -- research, proposal, script, scene_plan, assets, edit, compose, publish
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, awaiting_approval, approved, rejected, complete, failed, skipped
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    input_artifacts JSONB,             -- paths to input files
    output_artifacts JSONB,            -- paths to output files
    logs TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- assets table
CREATE TABLE assets (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    chapter_id VARCHAR(50),
    scene_id VARCHAR(50),
    asset_type VARCHAR(50),  -- narration, image, music, diagram, code, subtitle, video_segment
    file_path VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,
    mime_type VARCHAR(100),
    metadata JSONB,           -- voice settings, code language, chart type, etc.
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- approvals table
CREATE TABLE approvals (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    stage_run_id UUID REFERENCES stage_runs(id),
    approval_type VARCHAR(50),  -- concept, script, scene_plan, assets
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected, modified
    data JSONB,                  -- the data being approved (script text, scene list, etc.)
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);
```

### 1.4 WebSocket Event Protocol

```python
# Event types sent from backend → frontend

class PipelineEvent:
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILED = "pipeline_failed"

    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"       # {stage, progress_pct, message}
    STAGE_COMPLETE = "stage_complete"       # {stage, output_artifacts}
    STAGE_FAILED = "stage_failed"           # {stage, error}
    STAGE_AWAITING_APPROVAL = "stage_awaiting_approval"  # {stage, approval_data}

    SCENE_GENERATED = "scene_generated"     # {chapter, scene, preview_url}
    ASSET_GENERATED = "asset_generated"     # {asset_type, asset_id, preview_url}
    RENDER_PROGRESS = "render_progress"     # {chapter, frame_current, frame_total, fps}

    LOG_MESSAGE = "log_message"             # {level, message, timestamp}

# Example WebSocket message:
{
    "type": "stage_progress",
    "data": {
        "stage": "script",
        "progress": 0.45,
        "message": "Writing Chapter 3 narration...",
        "estimated_remaining_seconds": 120
    }
}

{
    "type": "scene_generated",
    "data": {
        "chapter": 2,
        "scene": 3,
        "scene_type": "code_viz",
        "preview_url": "/api/projects/abc123/preview/ch02-sc03",
        "duration_seconds": 145
    }
}
```

---

## Part 2: Frontend Architecture

### 2.1 Tech Stack

```
Framework:       Next.js 14 (App Router)
Language:        TypeScript
Styling:         Tailwind CSS + CSS custom properties
Animations:      Framer Motion (UI), GSAP (video preview)
State:           Zustand (client), React Query (server state)
Video Preview:   HTML5 Video + custom controls + canvas overlay
Real-time:       Native WebSocket + React Query subscriptions
File Upload:     react-dropzone
Editor:          CodeMirror 6 (script editing)
Charts:          Recharts (dashboards)
Icons:           Lucide React
```

### 2.2 Page Structure

```
app/
├── layout.tsx                      # Root layout with WebSocket provider
├── page.tsx                        # Project gallery
├── projects/
│   ├── [slug]/
│   │   ├── page.tsx                # Project dashboard (main view)
│   │   ├── pipeline/
│   │   │   └── page.tsx            # Pipeline timeline view
│   │   ├── script/
│   │   │   └── page.tsx            # Script editor
│   │   ├── scenes/
│   │   │   └── page.tsx            # Scene plan viewer/editor
│   │   ├── assets/
│   │   │   └── page.tsx            # Asset library
│   │   └── preview/
│   │       └── page.tsx            # Full video preview player
│   │   └── new/
│   │       └── page.tsx            # New project form
├── components/
│   ├── pipeline/
│   │   ├── PipelineTimeline.tsx    # Horizontal stage timeline with progress
│   │   ├── StageNode.tsx           # Individual stage in timeline
│   │   ├── ApprovalGate.tsx        # Approve/reject/modify button group
│   │   └── StageDetail.tsx         # Expandable stage details
│   ├── preview/
│   │   ├── VideoPlayer.tsx         # Main video preview with custom controls
│   │   ├── ScenePreview.tsx        # Single scene preview (in editor)
│   │   ├── TimelineScrubber.tsx    # Scene-based scrubber
│   │   └── PreviewOverlay.tsx      # Chapter markers, scene labels
│   ├── editor/
│   │   ├── ScriptEditor.tsx        # Rich script editor with timing
│   │   ├── SceneCanvas.tsx         # Visual scene arrangement
│   │   ├── AssetPanel.tsx          # Drag-drop asset management
│   │   └── CodeEditor.tsx          # Code visualization preview
│   ├── dashboard/
│   │   ├── ProjectCard.tsx         # Project thumbnail card
│   │   ├── StatsBar.tsx            # Budget, duration, status
│   │   └── ActivityFeed.tsx        # Real-time activity log
│   └── common/
│       ├── Button.tsx
│       ├── Modal.tsx
│       ├── Toast.tsx
│       └── ProgressBar.tsx
├── hooks/
│   ├── usePipeline.ts              # Pipeline state + WebSocket
│   ├── useProject.ts               # Project CRUD
│   ├── useStageApproval.ts         # Approve/reject stage
│   └── usePreview.ts               # Scene/video preview
└── lib/
    ├── api.ts                      # Fetch wrapper with React Query
    ├── websocket.ts                # WebSocket connection manager
    └── stores/
        ├── pipelineStore.ts        # Zustand store for pipeline state
        └── projectStore.ts         # Zustand store for project state
```

### 2.3 Key UI Views

#### View 1: Project Gallery (Home)

```
┌──────────────────────────────────────────────────────────────────────┐
│  VideoForge                                    [+ New Project] [⚙️]    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│   │ Neural      │  │ Quantum     │  │ History of  │  │  + New   │  │
│   │ Networks    │  │ Computing   │  │ Art         │  │ Project  │  │
│   │             │  │             │  │             │  │          │  │
│   │ ▸ Complete  │  │ ▸ Rendering │  │ ▸ Script    │  │          │  │
│   │ ▸ 45 min    │  │ ▸ 32 min    │  │ ▸ 50 min    │  │          │  │
│   │ ▸ $8.50     │  │ ▸ $6.20     │  │ ▸ $9.10     │  │          │  │
│   │ ▸ 2 days ago│  │ ▸ 5 hrs ago │  │ ▸ 1 week ago│  │          │  │
│   └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### View 2: Pipeline Dashboard (Main Working View)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◀ Neural Networks Deep Dive                    [Resume] [Restart]   │
├──────────┬───────────────────────────────────────────┬───────────────┤
│          │                                           │               │
│ PIPELINE │    ┌─────────────────────────────────┐    │  VIDEO        │
│          │    │                                 │    │  PREVIEW      │
│ ● Research│   │                                 │    │               │
│ │        │   │     [Live Scene Preview]         │    │  ▶ ━━━━━━━━━  │
│ ● Proposal│  │                                 │    │  00:00 ───────│
│ │        │   │     Animated code typing in      │    │  ch1  ch2  ch3 │
│ ● Script  │   │     GSAP timeline                │    │               │
│ │        │   │                                 │    │  ┌──────────┐  │
│ ◉ Scene   │   │                                 │    │  │ Scene    │  │
│   Plan    │   │                                 │    │  │ Controls │  │
│ │        │   │                                 │    │  │          │  │
│ ○ Assets  │   └─────────────────────────────────┘    │  └──────────┘  │
│ │        │                                           │               │
│ ○ Compose │    ┌─────────────────────────────────┐    │               │
│ │        │    │  Log: Writing Chapter 3... 45%  │    │               │
│ ○ Publish │    │  ████████████░░░░░░░░░░░░░░░  │    │               │
│          │    └─────────────────────────────────┘    │               │
├──────────┴───────────────────────────────────────────┴───────────────┤
│ Ch2-Sc03 (code_viz)  ● Generating... 45%  │  Assets: 12/45  │ Cost: $4.2│
└──────────────────────────────────────────────────────────────────────┘
```

#### View 3: Script Editor

```
┌──────────────────────────────────────────────────────────────────────┐
│ Script Editor — Chapter 2: "How Neural Networks Learn"               │
│                                      [Save] [Preview Narration] [▶]   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ Scene 2.1 ──────┐  ┌─ Scene 2.2 ──────┐  ┌─ Scene 2.3 ─────┐  │
│  │ 00:00 — 00:45    │  │ 00:45 — 02:30    │  │ 02:30 — 05:00   │  │
│  │ TITLE CARD       │  │ EXPLANATION       │  │ CODE VIZ        │  │
│  │                   │  │                   │  │                  │  │
│  │ "How Neural      │  │ "At its core, a  │  │ [Code panel      │  │
│  │  Networks Learn" │  │  neural network   │  │  with Python     │  │
│  │                   │  │  is just...       │  │  code typing     │  │
│  │ Visual: Hero     │  │                   │  │  animation]      │  │
│  │ title with       │  │ Visual: Diagram  │  │                  │  │
│  │ particles         │  │ of perceptron    │  │ Visual: VS Code  │  │
│  │                   │  │                   │  │  style window    │  │
│  │ [Edit Scene]     │  │ [Edit Scene]     │  │ [Edit Scene]    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│  ┌─ Narration Text Editor ──────────────────────────────────────┐   │
│  │                                                               │   │
│  │  [00:00] Welcome back. In the last chapter, we saw how a    │   │
│  │  single perceptron works — it takes inputs, applies weights,│   │
│  │  and produces an output. [EMPHASIS] But here's the thing:   │   │
│  │  a single perceptron can only solve [PAUSE] linearly        │   │
│  │  separable problems. [SCENE: diagram showing XOR problem]   │   │
│  │                                                               │   │
│  │  That's where neural networks come in. [SCENE: title_card]  │   │
│  │  By stacking multiple perceptrons into layers, we create... │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│  Chapter timing: 08:32 / 10:00  │  Word count: 1,247  │  WPM: 145   │
└──────────────────────────────────────────────────────────────────────┘
```

#### View 4: Scene Canvas (Visual Editor)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Scene Plan — Chapter 2                                     [+ Add]     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────────┐  │   │
│  │ │ SCENE 2.1  │  Title Card  │  00:00-00:45  │  45s  │[Edit]│  │   │
│  │ │            │              │              │       │       │  │   │
│  │ │ [Preview]  │ Type: HERO   │ Narration:   │ Audio: │       │  │   │
│  │ │            │              │ "How Neural  │ ✓     │       │  │   │
│  │ │            │              │  Networks..." │       │       │  │   │
│  │ │            │              │              │ Visual:│       │  │   │
│  │ │            │              │              │ ✓ Gen  │       │  │   │
│  │ └─────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────────┐  │   │
│  │ │ SCENE 2.2  │  Diagram    │  00:45-02:30  │ 105s  │[Edit]│  │   │
│  │ │            │              │              │       │       │  │   │
│  │ │ [Preview]  │ Type: DIAGRAM│ Narration:   │ Audio: │       │  │   │
│  │ │            │              │ "A perceptron │ ✓     │       │  │   │
│  │ │            │              │  takes inputs │       │       │  │   │
│  │ │            │              │  and applies  │ Visual:│       │  │   │
│  │ │            │              │  weights..."  │ ✓ Gen  │       │  │   │
│  │ └─────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────────┐  │   │
│  │ │ SCENE 2.3  │  Code Viz   │  02:30-05:00  │ 150s  │[Edit]│  │   │
│  │ │            │              │              │       │       │  │   │
│  │ │ [Preview]  │ Type: CODE   │ Narration:   │ Audio: │       │  │   │
│  │ │            │              │ "Let's write │ ✓     │       │  │   │
│  │ │            │              │  a simple    │       │       │  │   │
│  │ │            │              │  perceptron   │ Visual:│       │  │   │
│  │ │            │              │  in Python..."│ ✓ Gen  │       │  │   │
│  │ └─────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.4 Design System

```css
/* The interface should feel like a professional video editing suite */

:root {
  /* Background layers — deep, cinematic, never flat white */
  --bg-deep: #08080c;
  --bg-base: #0e0e14;
  --bg-raised: #16161f;
  --bg-overlay: #1c1c28;
  --bg-hover: #22222f;

  /* Accent palette — electric, energetic */
  --accent-primary: #6366f1;     /* Indigo — primary actions */
  --accent-secondary: #8b5cf6;   /* Violet — highlights */
  --accent-success: #10b981;     /* Emerald — completed stages */
  --accent-warning: #f59e0b;     /* Amber — awaiting approval */
  --accent-danger: #ef4444;      /* Red — errors */
  --accent-info: #3b82f6;        /* Blue — info messages */

  /* Text hierarchy */
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --text-accent: #a5b4fc;

  /* Borders */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.1);
  --border-active: rgba(99, 102, 241, 0.5);

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-display: 'Outfit', 'Inter', sans-serif;

  /* Spacing */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  /* Shadows */
  --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.15);
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.4);
}

/* Typography scale */
.text-display { font-family: var(--font-display); font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em; }
.text-heading { font-family: var(--font-display); font-size: 1.5rem; font-weight: 600; }
.text-title   { font-size: 1.125rem; font-weight: 600; }
.text-body    { font-size: 0.9375rem; line-height: 1.6; }
.text-caption { font-size: 0.8125rem; color: var(--text-secondary); }
.text-mono    { font-family: var(--font-mono); font-size: 0.875rem; }
```

---

## Part 3: The Pipeline (OpenMontage-Powered, Extended)

### 3.1 Pipeline Stages (Full Definition)

VideoForge extends OpenMontage's 8-stage pipeline with two additional stages for long-form video:

```
research → proposal → script → chapterize → scene_plan → assets → edit → compose → publish
                              ↑
                        NEW STAGE
                   (long-form splitting)
```

### Stage 0: Research

**Purpose**: Deep-dive into the topic. Find facts, data points, analogies, code examples, visual opportunities.

**Input**: `UserInput` (topic, subtopic, explanation, duration, audience)
**Output**: `ResearchBrief` (key concepts, sources, data points, visual opportunities)
**Agent**: Claude Haiku (fast, cheap) for broad research → Claude Sonnet for deep synthesis
**Tools**: Web search, Presenton web search, reference gathering

**Quality Gate**: Brief must have 4-7 key concepts per planned chapter, at least 2 data points, at least 1 code example (if technical topic).

```
┌─────────────────────────────────────────────────────────────┐
│  research_stage.py                                          │
│                                                              │
│  async def run(project: Project) -> ResearchBrief:          │
│      # Call Claude with web search enabled                  │
│      brief = await claude.research(                         │
│          topic=project.topic,                               │
│          subtopic=project.subtopic,                         │
│          context=project.user_explanation,                  │
│          audience=project.target_audience,                  │
│          duration_minutes=project.target_duration_minutes,  │
│          web_search=True                                    │
│      )                                                      │
│                                                              │
│      # Validate coverage                                   │
│      validate_research_coverage(brief, project)             │
│                                                              │
│      # Save artifacts                                      │
│      save_json(project, "research_brief.json", brief)       │
│      return brief                                           │
└─────────────────────────────────────────────────────────────┘
```

### Stage 1: Proposal (Interactive)

**Purpose**: Present the user with concept options. Get their buy-in before heavy investment.

**Input**: `ResearchBrief`
**Output**: `ConceptProposal` (selected concept, visual style, runtime choice, chapter outline)
**Agent**: Claude Sonnet (creative + analytical)
**Tools**: Presenton (generate concept mockup slides), image gen (generate style reference)

**This is the FIRST approval gate.**

```
┌─────────────────────────────────────────────────────────────┐
│  proposal_stage.py                                          │
│                                                              │
│  async def run(project: Project, brief: ResearchBrief)      │
│          -> ConceptProposal:                                │
│                                                              │
│      proposal = await claude.create_proposal(               │
│          brief=brief,                                       │
│          style_options=["cinematic", "bold-motion",          │
│                         "premium-minimal", "playful"]       │
│      )                                                      │
│                                                              │
│      # Generate visual reference via Presenton               │
│      reference_slides = await presenton.generate_outline(   │
│          topic=proposal.title_slide,                        │
│          num_slides=3,                                      │
│          style=proposal.visual_style                        │
│      )                                                      │
│                                                              │
│      # Present to user + WAIT for approval                  │
│      await wait_for_approval(project, "concept", {          │
│          "proposal": proposal.__dict__,                     │
│          "reference_slides": reference_slides,               │
│          "estimated_cost": estimate_cost(proposal),          │
│          "estimated_duration": estimate_duration(proposal)   │
│      })                                                     │
│                                                              │
│      save_json(project, "concept_proposal.json", proposal)   │
│      return proposal                                        │
└─────────────────────────────────────────────────────────────┘
```

### Stage 2: Script

**Purpose**: Write the complete narration script with timing, scene cues, and performance directions.

**Input**: `ConceptProposal`, `ResearchBrief`
**Output**: `VideoScript` (chapters → scenes → narration text, timing, performance cues)
**Agent**: Claude Sonnet (creative writing + technical accuracy)
**Tools**: None (pure generation)

**SECOND approval gate.**

```
┌─────────────────────────────────────────────────────────────┐
│  script_stage.py                                            │
│                                                              │
│  async def run(project, proposal, brief) -> VideoScript:    │
│      script = await claude.write_script(                    │
│          proposal=proposal,                                 │
│          research=brief,                                    │
│          pacing=proposal.pacing,  # relaxed/moderate/fast   │
│          wpm=proposal.words_per_minute,  # 140-160          │
│      )                                                      │
│                                                              │
│      # Validate timing                                      │
│      total_words = sum(ch.word_count for ch in script.chapters) │
│      estimated_minutes = total_words / project.wpm           │
│      assert abs(estimated_minutes - project.target_duration) │
│             < project.target_duration * 0.1                  │
│                                                              │
│      await wait_for_approval(project, "script", {           │
│          "script": script.to_editable_dict(),               │
│          "total_duration_estimated": estimated_minutes,      │
│          "chapter_breakdown": [...],                         │
│      })                                                     │
│                                                              │
│      save_json(project, "script.json", script)               │
│      return script                                          │
└─────────────────────────────────────────────────────────────┘
```

### Stage 3: Chapterize (NEW — for long-form)

**Purpose**: Split the script into independently-renderable chapters with continuity bridges.

**Input**: `VideoScript`
**Output**: `ChapterPlan` (5 chapters, each 8-10 min, with transitions)

```
┌─────────────────────────────────────────────────────────────┐
│  chapterize_stage.py                                        │
│                                                              │
│  async def run(project, script) -> ChapterPlan:             │
│      plan = await claude.chapterize(                        │
│          script=script,                                     │
│          target_chapter_minutes=8,  # max per chapter       │
│          min_chapter_minutes=5,                             │
│      )                                                      │
│                                                              │
│      # Ensure transitions between chapters                  │
│      for i, chapter in enumerate(plan.chapters):            │
│          if i > 0:                                          │
│              chapter.transition_from = plan.chapters[i-1]   │
│              chapter.transition_to = plan.chapters[i+1]     │
│                                                              │
│      save_json(project, "chapter_plan.json", plan)           │
│      return plan                                            │
└─────────────────────────────────────────────────────────────┘
```

### Stage 4: Scene Plan

**Purpose**: Break each chapter into scenes with visual variety enforcement.

**Input**: `ChapterPlan`, `VideoScript`
**Output**: `ScenePlan` (all scenes across all chapters, with types, timing, assets needed)
**Agent**: Claude Sonnet (visual design thinking)
**Tools**: None

**THIRD approval gate.**

**KEY QUALITY RULE: No 3+ consecutive scenes of the same type.**

```
┌─────────────────────────────────────────────────────────────┐
│  scene_plan_stage.py                                        │
│                                                              │
│  async def run(project, chapter_plan, script) -> ScenePlan: │
│      all_scenes = []                                        │
│      for chapter in chapter_plan.chapters:                  │
│          chapter_scenes = await claude.design_scenes(       │
│              chapter=chapter,                               │
│              script=script.get_chapter(chapter.id),         │
│              visual_style=project.visual_style,             │
│              available_types=SCENE_TYPES,                   │
│          )                                                  │
│                                                              │
│          # Enforce visual variety                           │
│          validate_scene_variety(chapter_scenes)             │
│          # → No 3+ consecutive same-type scenes            │
│          # → Each scene has different primary visual subject│
│                                                              │
│          all_scenes.extend(chapter_scenes)                  │
│                                                              │
│      await wait_for_approval(project, "scene_plan", {      │
│          "scenes": [s.to_dict() for s in all_scenes],       │
│          "total_scenes": len(all_scenes),                   │
│          "scene_type_breakdown": count_types(all_scenes),   │
│          "visual_style_guide": generate_style_guide(...),   │
│      })                                                     │
│                                                              │
│      save_json(project, "scene_plan.json", all_scenes)      │
│      return all_scenes                                      │
└─────────────────────────────────────────────────────────────┘
```

### Scene Types (The 12 Types)

These are the visual "building blocks" — each is a distinct visual treatment:

| Type | Visual Treatment | Best For | Animation Style |
|------|-----------------|----------|-----------------|
| `hero_title` | Large cinematic title with particle effects, depth | Chapter openings, major sections | Fade in + scale + particles |
| `text_card` | Clean text on textured background with subtle motion | Explanations, definitions | Slide + fade with parallax bg |
| `stat_card` | Big number + label + contextual visual | Statistics, metrics | Count-up + scale |
| `callout` | Highlighted text box with accent border + glow | Key takeaways, warnings | Bounce + glow pulse |
| `comparison` | Side-by-side or A vs B layout | Comparing concepts | Slide-in from opposite sides |
| `bar_chart` | Animated bar chart with labels | Data comparisons | Grow-up + stagger |
| `line_chart` | Animated line/area chart | Trends over time | Draw + fade-in |
| `pie_chart` | Animated pie/donut chart | Proportions, distributions | Expand + rotate-in |
| `kpi_grid` | Grid of stat cards | Overview dashboards | Cascade fade-in |
| `progress_bar` | Animated progress indicator | Step-by-step processes | Sequential fill |
| `anime_scene` | Multi-image crossfade + particles + camera | Emotional beats, storytelling | Crossfade + particles + camera |
| `talking_head` | Avatar with lip-synced narration | Direct explanation | Idle sway + lip sync |
| `code_viz` | Syntax-highlighted code with typing animation | Code examples | Type-in + line highlight |
| `diagram` | Custom diagram with animated elements | Architecture, flows | Draw + label sequence |

### Stage 5: Assets

**Purpose**: Generate all visual and audio assets for every scene.

**Input**: `ScenePlan`
**Output**: `AssetManifest` (all audio, images, video segments)
**Agent**: Claude Haiku (orchestration) + tool calls
**Tools**: ElevenLabs TTS, image generation, diagram_gen, code_snippet, music_gen, Presenton
**FOURTH approval gate.**

```
┌─────────────────────────────────────────────────────────────┐
│  asset_stage.py                                             │
│                                                             │
│  async def run(project, scene_plan) -> AssetManifest:       │
│      manifest = AssetManifest()                             │
│                                                             │
│      for chapter in scene_plan.chapters:                    │
│          for scene in chapter.scenes:                       │
│              # Generate assets in parallel                  │
│              results = await asyncio.gather(                │
│                  self._generate_narration(scene),           │
│                  self._generate_visual(scene),              │
│                  self._generate_music_if_needed(scene),     │
│              )                                              │
│              manifest.add(scene.id, results)                │
│                                                             │
│      await wait_for_approval(project, "assets", {           │
│          "total_assets": manifest.count(),                  │
│          "assets_by_type": manifest.breakdown(),            │
│          "total_audio_duration": manifest.total_audio_dur,  │
│          "previews": manifest.scene_previews(),             │
│      })                                                     │
│                                                             │
│      save_json(project, "asset_manifest.json", manifest)    │
│      return manifest                                        │
└─────────────────────────────────────────────────────────────┘
```

### Stage 6: Edit

**Purpose**: Make edit decisions — cuts, transitions, music ducking, subtitle styling, color grading.

**Input**: `AssetManifest`, `ScenePlan`
**Output**: `EditDecisions` (timeline with all timing and effect decisions)
**Agent**: Claude Sonnet (editorial judgment)
**Tools**: None (decisions only; applied in compose)

```
┌─────────────────────────────────────────────────────────────┐
│  edit_stage.py                                              │
│                                                             │
│  async def run(project, manifest, scene_plan)               │
│          -> EditDecisions:                                  │
│      decisions = await claude.make_edit_decisions(          │
│          scenes=scene_plan.scenes,                          │
│          assets=manifest,                                   │
│          pacing=project.pacing,                             │
│          music_style=project.music_style,                   │
│      )                                                      │
│                                                             │
│      # Define timeline                                      │
│      timeline = Timeline()                                  │
│      for scene in scene_plan.scenes:                        │
│          timeline.add_clip(                                 │
│              scene_id=scene.id,                             │
│              source=manifest.get_video(scene.id),           │
│              audio=manifest.get_audio(scene.id),            │
│              in_time=0,                                     │
│              out_time=scene.duration,                       │
│              transition=decisions.get_transition(scene.id), │
│              music_duck=decisions.get_music_duck(scene.id), │
│              subtitle_style=decisions.subtitle_style,       │
│          )                                                  │
│                                                             │
│      save_json(project, "edit_decisions.json", decisions)   │
│      return decisions                                       │
└─────────────────────────────────────────────────────────────┘
```

### Stage 7: Compose

**Purpose**: Render the final video by composing all scenes.

**Input**: `EditDecisions`, `AssetManifest`
**Output**: Final video files (per chapter + full concatenation)
**Agent**: System (no AI — pure rendering)
**Tools**: Remotion / HyperFrames / FFmpeg (chosen at proposal stage)

```
┌──────────────────────────────────────────────────────────────────┐
│  compose_stage.py                                                │
│                                                                  │
│  async def run(project, decisions, manifest) -> RenderResult:    │
│      runtime = project.chosen_runtime  # "remotion"|"hyperframes"│
│                                                                  │
│      if runtime == "hyperframes":                                │
│          return await self._render_hyperframes(                  │
│              project, decisions, manifest                        │
│          )                                                       │
│      elif runtime == "remotion":                                 │
│          return await self._render_remotion(                     │
│              project, decisions, manifest                        │
│          )                                                       │
│      else:                                                       │
│          return await self._render_ffmpeg(                       │
│              project, decisions, manifest                        │
│          )                                                       │
│                                                                  │
│  async def _render_hyperframes(self, project, decisions,         │
│      manifest) -> RenderResult:                                  │
│      # 1. Generate HTML for each scene                           │
│      for chapter in decisions.chapters:                          │
│          for scene in chapter.scenes:                            │
│              html = self.generate_scene_html(                    │
│                  scene, manifest, project.style_guide            │
│              )                                                   │
│              write_file(html_path(scene.id), html)               │
│                                                                  │
│          # 2. Create composition manifest                        │
│          compose_manifest = self.build_manifest(chapter)         │
│                                                                  │
│          # 3. Render via HyperFrames CLI                         │
│          output = await run_hyperframes_render(                  │
│              manifest=compose_manifest,                          │
│              output=f"renders/{project.slug}/ch{chapter.num}.mp4"│
│          )                                                       │
│                                                                  │
│      # 4. Stitch chapters via FFmpeg                             │
│      final = await ffmpeg_concat_chapters(                       │
│          chapter_outputs,                                        │
│          output=f"renders/{project.slug}/final.mp4"              │
│      )                                                           │
│                                                                  │
│      # 5. Burn subtitles                                         │
│      final = await ffmpeg_burn_subs(                             │
│          video=final,                                            │
│          subs=manifest.subtitles,                                │
│          output=f"renders/{project.slug}/final_subs.mp4"         │
│      )                                                           │
│                                                                  │
│      return RenderResult(path=final, ...)                        │
└──────────────────────────────────────────────────────────────────┘
```

### Stage 8: Publish

**Purpose**: Final packaging with SEO metadata, chapters, thumbnails.

**Input**: `RenderResult`
**Output**: `PublishPackage`
```
┌─────────────────────────────────────────────────────────────┐
│  publish_stage.py                                           │
│                                                              │
│  async def run(project, render) -> PublishPackage:          │
│      # Generate thumbnail from best frame                    │
│      thumbnail = await extract_thumbnail(render.path)        │
│                                                              │
│      # Generate SRT subtitles                               │
│      srt = await generate_srt(render.audio_track)           │
│                                                              │
│      # Package everything                                  │
│      package = PublishPackage(                              │
│          video_path=render.path,                            │
│          thumbnail=thumbnail,                               │
│          subtitles=srt,                                     │
│          metadata={                                         │
│              "title": f"{project.topic} — {project.subtopic}",│
│              "description": generate_description(project),  │
│              "tags": project.tags,                          │
│              "chapters": [                                 │
│                  {"title": ch.title, "start": ch.start_sec} │
│                  for ch in project.chapters                  │
│              ]                                              │
│          },                                                 │
│          chapters_json=project.chapters_json,               │
│      )                                                      │
│                                                              │
│      # Copy to output directory                             │
│      package.export(project.output_dir)                     │
│      return package                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 4: Rendering Engines

### 4.1 HyperFrames Rendering (Primary for Explainer Videos)

HyperFrames is the primary rendering engine for VideoForge explainer videos. It produces the most visually impressive results due to HTML/CSS/JS flexibility with GSAP animation.

**Scene HTML Generation Strategy:**

Each scene is a self-contained HTML file with:
- `data-duration` attribute for total scene length
- GSAP timeline registered on `window.__timelines`
- All CSS in `<style>` tags
- All JS in `<script>` tags
- CDN links for GSAP, Lottie, Three.js as needed

```python
class HyperFramesRenderer:
    """Generates HyperFrames HTML and renders to video."""

    TEMPLATES = {
        "hero_title": "templates/hero-title.html",
        "text_card": "templates/text-card.html",
        "stat_card": "templates/stat-card.html",
        "callout": "templates/callout.html",
        "comparison": "templates/comparison.html",
        "bar_chart": "templates/bar-chart.html",
        "line_chart": "templates/line-chart.html",
        "pie_chart": "templates/pie-chart.html",
        "kpi_grid": "templates/kpi-grid.html",
        "progress_bar": "templates/progress-bar.html",
        "anime_scene": "templates/anime-scene.html",
        "talking_head": "templates/talking-head.html",
        "code_viz": "templates/code-viz.html",
        "diagram": "templates/diagram.html",
    }

    def render_chapter(self, chapter: Chapter, assets: AssetManifest,
                       style_guide: StyleGuide) -> str:
        """Render a complete chapter to MP4."""
        scene_htmls = []
        for scene in chapter.scenes:
            html = self._render_scene_html(scene, assets, style_guide)
            scene_htmls.append(html)

        # Build composition
        composition = self._build_composition(
            scenes=scene_htmls,
            transitions=chapter.transitions,
            background_music=assets.get_music(chapter.id),
            subtitles=assets.get_subtitles(chapter.id),
            style_guide=style_guide,
        )

        # Write to project directory
        compose_dir = self.project_path / "compose" / f"ch{chapter.number:02d}"
        compose_dir.mkdir(parents=True, exist_ok=True)
        (compose_dir / "index.html").write_text(composition)

        # Render via HyperFrames CLI
        output_path = self.project_path / "renders" / f"ch{chapter.number:02d}.mp4"
        subprocess.run([
            "npx", "hyperframes", "render",
            str(compose_dir / "index.html"),
            "--output", str(output_path),
            "--fps", "30",
            "--resolution", "1920x1080",
        ], check=True, capture_output=True)

        return str(output_path)
```

### 4.2 Visual Style Guide (Generated per Project)

This is the **secret sauce** for visual consistency across a 45-minute video:

```python
@dataclass
class StyleGuide:
    # Color system
    primary_color: str          # "#6366f1"
    secondary_color: str        # "#8b5cf6"
    accent_color: str           # "#f43f5e"
    bg_primary: str             # "#0f172a" (dark slate)
    bg_secondary: str           │ "#1e293b"
    text_primary: str           │ "#f1f5f9"
    text_secondary: str         │ "#94a3b8"
    gradient_colors: list[str]  │ ["#6366f1", "#8b5cf6", "#d946ef"]

    # Typography
    heading_font: str           │ "Outfit"
    body_font: str              │ "Inter"
    mono_font: str              │ "JetBrains Mono"
    heading_weight: int         │ 700
    body_weight: int            │ 400

    # Motion
    default_easing: str         │ "power3.inOut"
    scene_duration_min: float   │ 8.0
    scene_duration_max: float   │ 180.0
    transition_type: str        │ "fade" | "slide" | "dissolve"
    transition_duration: float  │ 0.5

    # Background
    bg_style: str               │ "gradient" | "solid" | "noise" | "mesh"
    bg_has_particles: bool      │ True
    bg_particle_type: str       │ "dots" | "lines" | "grid" | "none"

    # Effects
    glass_morphism: bool        │ True
    glow_effects: bool          │ True
    grain_overlay: bool         │ True (subtle film grain)
    shadow_style: str           │ "soft" | "hard" | "neon"
```

The style guide is:
1. Proposed by Claude based on the topic and user preferences
2. Shown to user at the proposal stage for approval
3. Locked after approval — every scene MUST use it
4. Passed to every scene HTML generator as context

### 4.3 Scene HTML Templates (Example: Code Visualization)

```html
<!-- templates/code-viz.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      width: 1920px; height: 1080px;
      background: {{BG_PRIMARY}};
      font-family: 'Inter', sans-serif;
      overflow: hidden;
    }
    .scene {{
      width: 1920px; height: 1080px;
      position: relative;
      display: flex;
    }}
    .code-panel {{
      width: 55%; height: 100%;
      background: {{BG_SECONDARY}};
      border-right: 1px solid {{BORDER_SUBTLE}};
      padding: 60px;
      font-family: 'JetBrains Mono', monospace;
      position: relative;
    }}
    .line-numbers {{
      position: absolute; left: 20px; top: 60px;
      color: {{TEXT_MUTED}}; font-size: 18px;
      line-height: 2; text-align: right; width: 40px;
    }}
    .code-content {{
      margin-left: 70px; font-size: 20px;
      line-height: 2; color: {{TEXT_PRIMARY}};
    }}
    .code-line {{
      opacity: 0;
      white-space: pre;
    }}
    .line-highlight {{
      background: {{PRIMARY_COLOR}}22;
      border-left: 3px solid {{PRIMARY_COLOR}};
      margin-left: -70px; padding-left: 67px;
    }}
    .annotation-panel {{
      width: 45%; height: 100%;
      padding: 80px 60px;
      display: flex; flex-direction: column;
      justify-content: center;
    }}
    .annotation-title {{
      font-size: 28px; font-weight: 600;
      color: {{PRIMARY_COLOR}}; margin-bottom: 16px;
    }}
    .annotation-text {{
      font-size: 22px; line-height: 1.7;
      color: {{TEXT_SECONDARY}};
    }}
    .annotation-line-ref {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 16px; color: {{ACCENT_COLOR}};
      margin-top: 24px; padding: 8px 16px;
      background: {{BG_OVERLAY}}; border-radius: 8px;
      display: inline-block;
    }}
    /* Syntax colors */
    .kw {{ color: #c678dd; }}    /* keyword */
    .str {{ color: #98c379; }}   /* string */
    .fn {{ color: #61afef; }}    /* function */
    .cm {{ color: #5c6370; }}    /* comment */
    .num {{ color: #d19a66; }}   /* number */
    .op {{ color: #56b6c2; }}    /* operator */
  </style>
</head>
<body>
  <div class="scene" data-duration="{{DURATION}}">
    <div class="code-panel">
      <div class="line-numbers">{{LINE_NUMBERS}}</div>
      <div class="code-content">{{CODE_LINES}}</div>
    </div>
    <div class="annotation-panel">
      <div class="annotation-title">{{ANNOTATION_TITLE}}</div>
      <div class="annotation-text">{{ANNOTATION_TEXT}}</div>
      <div class="annotation-line-ref">Line {{CURRENT_LINE}}</div>
    </div>
  </div>
  <script>
    // GSAP typing animation with annotations
    const codeLines = {{CODE_LINES_JSON}};
    const annotations = {{ANNOTATIONS_JSON}};
    const tl = gsap.timeline({{ paused: true }});
    const mainTl = gsap.timeline({{ paused: true }});

    // Animate code lines in one by one
    codeLines.forEach((line, i) => {{
      tl.to(`.line-{{i}}`, {{
        opacity: 1, duration: 0.15,
        onStart: () => {{
          // Update annotation panel
          if (annotations[i]) {{
            gsap.to('.annotation-title', {{
              textContent: annotations[i].title, duration: 0.3
            }});
            gsap.to('.annotation-text', {{
              textContent: annotations[i].text, duration: 0.3
            }});
          }}
        }}
      }});
    }});

    mainTl.add(tl);
    window.__timelines = [mainTl];
  </script>
</body>
</html>
```

### 4.4 Audio Pipeline (Layered)

```
Scene Audio Architecture:
┌─────────────────────────────────────────┐
│           MIXED OUTPUT                  │
│  ┌───────────────────────────────────┐  │
│  │  Layer 1: Narration (TTS)         │  │
│  │  - Individual scene segments      │  │
│  │  - Voice cloned via SeedVC        │  │
│  │  - Stitched with crossfades       │  │
│  │  - Loudness: -16 LUFS             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Layer 2: Background Music        │  │
│  │  - Generated via Make-An-Audio    │  │
│  │  - Or curated from library        │  │
│  │  - Ducked -20dB during narration  │  │
│  │  - Fade in/out at chapter bounds  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Layer 3: SFX (optional)          │  │
│  │  - Transition swooshes            │  │
│  │  - Click/tap sounds               │  │
│  │  - Whoosh for scene changes       │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Layer 4: Subtitles               │  │
│  │  - Word-level timed SRT           │  │
│  │  - Burned into video in compose   │  │
│  │  - Styled per brand guide         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Part 5: Quality System

### 5.1 The Taste Profile

Every project has a **taste profile** — three dials (1-10) that control the creative output:

```python
@dataclass
class TasteProfile:
    project_id: str

    # Visual variance: How different do consecutive scenes look?
    # 1 = every scene looks the same (boring slides)
    # 10 = every scene is radically different (busy, disjointed)
    visual_variance: int = 6

    # Motion intensity: How much animation?
    # 1 = static slides, minimal motion
    # 10 = constant particle effects, camera moves, morphing
    motion_intensity: int = 5

    # Information density: How much content per frame?
    # 1 = one idea per frame, lots of breathing room
    # 10 = dense dashboards, multiple data streams
    information_density: int = 4

    def get_scene_diversity_rules(self) -> dict:
        """Generate rules based on taste profile."""
        return {
            "min_types_before_repeat": max(2, 11 - self.visual_variance),
            "max_motion_density": self.motion_intensity / 10,
            "max_content_elements": 2 + self.information_density,
            "particle_probability": self.motion_intensity / 10,
            "transition_complexity": self.motion_intensity / 10,
        }
```

### 5.2 Quality Checks (Automated + AI)

Every scene and chapter passes through quality validation:

```python
class QualityChecker:
    """Multi-layer quality validation."""

    async def validate_scene(self, scene: Scene, html: str) -> list[QualityIssue]:
        issues = []

        # Automated checks
        issues.extend(await self._check_html_structure(html))
        issues.extend(await self._check_timing(scene, html))
        issues.extend(await self._check_visual_density(scene, html))
        issues.extend(await self._check_animation_performance(html))
        issues.extend(await self._check_style_guide_compliance(scene, html))

        # AI-powered checks (Claude vision)
        issues.extend(await self._ai_check_visual_quality(scene, html))
        issues.extend(await self._ai_check_narration_sync(scene))

        return issues

    async def _ai_check_visual_quality(self, scene: Scene, html: str) -> list:
        """Render a frame, send to Claude vision for quality assessment."""
        frame = await render_frame(html, time=scene.duration / 2)
        assessment = await claude.assess_visual_quality(
            image=frame,
            scene_type=scene.type,
            style_guide=scene.style_guide,
            narration=scene.narration_text,
        )
        return assessment.issues
```

### 5.3 Reviewer System (From OpenMontage)

```python
class Reviewer:
    """AI-powered reviewer that checks each stage's output."""

    MAX_REVIEW_ROUNDS = 2

    async def review_stage(self, stage_name: str, artifacts: dict,
                          project: Project) -> ReviewResult:
        """Review a stage's output. Enforces quality before proceeding."""

        review_prompt = REVIEW_SKILLS[stage_name]  # From skills folder

        assessment = await claude.review(
            system=review_prompt,
            artifacts=artifacts,
            project_context=project.summary(),
        )

        result = ReviewResult(
            verdict=assessment.verdict,  # pass | revise | fail
            findings=assessment.findings,
            critical_count=sum(1 for f in assessment.findings if f.severity == "critical"),
        )

        # Enforce: no critical findings can pass
        if result.critical_count > 0:
            result.verdict = "revise"

        return result
```

---

## Part 6: Project Structure (Final)

```
d:\Coder_S3\video generation v3\
│
├── videoforge-backend/                 # NEW — Backend service
│   ├── pyproject.toml                  # Python package
│   ├── Dockerfile                      # Backend container
│   ├── .env.example                    # Environment template
│   │
│   ├── app/                            # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                     # App factory, WebSocket hub
│   │   ├── config.py                   # Settings
│   │   │
│   │   ├── api/                        # REST API
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                 # Shared dependencies
│   │   │   └── routers/
│   │   │       ├── projects.py         # Project CRUD
│   │   │       ├── pipeline.py         # Pipeline control
│   │   │       ├── stages.py           # Stage management
│   │   │       ├── assets.py           # Asset browsing
│   │   │       ├── preview.py          # Scene preview
│   │   │       ├── upload.py           # File uploads
│   │   │       └── health.py           # Health checks
│   │   │
│   │   ├── models/                     # Database models
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── stage_run.py
│   │   │   ├── asset.py
│   │   │   └── approval.py
│   │   │
│   │   ├── schemas/                    # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── pipeline.py
│   │   │   ├── stage.py
│   │   │   └── asset.py
│   │   │
│   │   ├── core/                       # Core infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── database.py             # SQLAlchemy setup
│   │   │   ├── websocket.py            # WebSocket manager
│   │   │   ├── events.py               # Event types + serialization
│   │   │   ├── storage.py              # File storage abstraction
│   │   │   └── auth.py                 # API key auth
│   │   │
│   │   ├── services/                   # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py      # Project CRUD
│   │   │   ├── pipeline_service.py     # Pipeline orchestration
│   │   │   ├── event_bus.py            # Redis pub/sub wrapper
│   │   │   └── preview_service.py      # Scene preview generation
│   │   │
│   │   └── workers/                    # Celery workers
│   │       ├── __init__.py
│   │       ├── celery_app.py           # Celery configuration
│   │       └── tasks/
│   │           ├── __init__.py
│   │           ├── pipeline_runner.py  # Run full pipeline
│   │           ├── stage_runner.py     # Run single stage
│   │           ├── preview_runner.py   # Generate preview
│   │           └── asset_runner.py     # Generate single asset
│   │
│   ├── pipeline/                       # Pipeline implementation
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # Pipeline state machine
│   │   ├── state.py                    # Project state management
│   │   ├── stages/                     # Stage implementations
│   │   │   ├── __init__.py
│   │   │   ├── research_stage.py
│   │   │   ├── proposal_stage.py
│   │   │   ├── script_stage.py
│   │   │   ├── chapterize_stage.py     # NEW: long-form splitting
│   │   │   ├── scene_plan_stage.py
│   │   │   ├── asset_stage.py
│   │   │   ├── edit_stage.py
│   │   │   ├── compose_stage.py
│   │   │   └── publish_stage.py
│   │   ├── models/                     # Pipeline data models
│   │   │   ├── __init__.py
│   │   │   ├── user_input.py
│   │   │   ├── research_brief.py
│   │   │   ├── concept_proposal.py
│   │   │   ├── video_script.py
│   │   │   ├── chapter.py
│   │   │   ├── scene.py
│   │   │   ├── asset_manifest.py
│   │   │   ├── edit_decisions.py
│   │   │   ├── render_result.py
│   │   │   └── publish_package.py
│   │   ├── quality/                    # Quality system
│   │   │   ├── __init__.py
│   │   │   ├── checker.py              # Automated quality checks
│   │   │   ├── reviewer.py             # AI-powered review
│   │   │   ├── style_guide.py          # Visual style enforcement
│   │   │   └── taste_profile.py        # Creative direction dials
│   │   └── skills/                     # Director skills
│   │       ├── __init__.py
│   │       ├── research-director.md
│   │       ├── proposal-director.md
│   │       ├── script-director.md
│   │       ├── chapter-director.md
│   │       ├── scene-director.md
│   │       ├── asset-director.md
│   │       ├── compose-director.md
│   │       └── reviewer.md
│   │
│   ├── adapters/                       # External service adapters
│   │   ├── __init__.py
│   │   ├── claude.py                   # Anthropic API client
│   │   ├── presenton.py                # Presenton API client
│   │   ├── elevenlabs.py               # Local ElevenLabs TTS client
│   │   ├── hyperframes.py              # HyperFrames render engine
│   │   ├── remotion.py                 # Remotion render engine
│   │   └── ffmpeg.py                   # FFmpeg composition
│   │
│   ├── generators/                     # Content generation
│   │   ├── __init__.py
│   │   ├── content_researcher.py       # Research synthesis
│   │   ├── script_writer.py            # Narration script generation
│   │   ├── chapterizer.py              # Long-form chapter splitting
│   │   ├── scene_designer.py           # Scene visual design
│   │   ├── code_visualizer.py          # Code animation specs
│   │   ├── diagram_spec.py             # Diagram specifications
│   │   └── style_guide_gen.py          # Generate project style guide
│   │
│   ├── renderers/                      # Rendering engines
│   │   ├── __init__.py
│   │   ├── base.py                     # Base renderer interface
│   │   ├── hyperframes_renderer.py     # HyperFrames HTML → MP4
│   │   ├── remotion_renderer.py        # Remotion React → MP4
│   │   ├── ffmpeg_renderer.py          # FFmpeg stitch + effects
│   │   └── scene_html_builder.py       # Build scene HTML from templates
│   │
│   ├── templates/                      # HyperFrames HTML templates
│   │   ├── base.html                   # Base HTML shell
│   │   ├── hero-title.html
│   │   ├── text-card.html
│   │   ├── stat-card.html
│   │   ├── callout.html
│   │   ├── comparison.html
│   │   ├── bar-chart.html
│   │   ├── line-chart.html
│   │   ├── pie-chart.html
│   │   ├── kpi-grid.html
│   │   ├── progress-bar.html
│   │   ├── anime-scene.html
│   │   ├── talking-head.html
│   │   ├── code-viz.html
│   │   ├── diagram.html
│   │   ├── chapter-intro.html
│   │   └── outro.html
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── checkpoint.py               # Save/load pipeline state
│   │   ├── validators.py               # Validate artifacts
│   │   ├── timing.py                   # Timing calculations
│   │   └── file_utils.py               # Path management
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── test_models.py
│       │   ├── test_checkpoint.py
│       │   ├── test_validators.py
│       │   └── test_timing.py
│       ├── integration/
│       │   ├── test_pipeline.py
│       │   ├── test_claude_adapter.py
│       │   └── test_renderers.py
│       └── fixtures/
│           ├── sample_script.json
│           ├── sample_scene_plan.json
│           └── sample_style_guide.json
│
├── videoforge-frontend/                # NEW — Next.js frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   ├── Dockerfile
│   │
│   ├── src/
│   │   ├── app/                        # Next.js App Router
│   │   │   ├── layout.tsx              # Root layout + providers
│   │   │   ├── page.tsx                # Project gallery
│   │   │   ├── new/
│   │   │   │   └── page.tsx            # New project wizard
│   │   │   ├── projects/
│   │   │   │   └── [slug]/
│   │   │   │       ├── page.tsx        # Project dashboard
│   │   │   │       ├── pipeline/
│   │   │   │       │   └── page.tsx    # Pipeline timeline
│   │   │   │       ├── script/
│   │   │   │       │   └── page.tsx    # Script editor
│   │   │   │       ├── scenes/
│   │   │   │       │   └── page.tsx    # Scene plan editor
│   │   │   │       ├── assets/
│   │   │   │       │   └── page.tsx    # Asset library
│   │   │   │       ├── preview/
│   │   │   │       │   └── page.tsx    # Video preview player
│   │   │   │       └── settings/
│   │   │   │           └── page.tsx    # Project settings
│   │   │   └── api/                    # API routes (proxies)
│   │   │       └── ws/                 # WebSocket route
│   │   │
│   │   ├── components/                 # React components
│   │   │   ├── pipeline/
│   │   │   │   ├── PipelineTimeline.tsx
│   │   │   │   ├── StageNode.tsx
│   │   │   │   ├── ApprovalGate.tsx
│   │   │   │   └── StageDetail.tsx
│   │   │   ├── preview/
│   │   │   │   ├── VideoPlayer.tsx
│   │   │   │   ├── ScenePreview.tsx
│   │   │   │   ├── TimelineScrubber.tsx
│   │   │   │   └── PreviewOverlay.tsx
│   │   │   ├── editor/
│   │   │   │   ├── ScriptEditor.tsx
│   │   │   │   ├── SceneCanvas.tsx
│   │   │   │   ├── AssetPanel.tsx
│   │   │   │   └── CodePreview.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   ├── StatsBar.tsx
│   │   │   │   └── ActivityFeed.tsx
│   │   │   └── common/
│   │   │       ├── Button.tsx
│   │   │       ├── Modal.tsx
│   │   │       ├── Toast.tsx
│   │   │       └── ProgressRing.tsx
│   │   │
│   │   ├── hooks/                      # Custom React hooks
│   │   │   ├── usePipeline.ts          # Pipeline state + WS
│   │   │   ├── useProject.ts           # Project CRUD
│   │   │   ├── useApproval.ts          # Stage approval flow
│   │   │   ├── usePreview.ts           # Scene/video preview
│   │   │   └── useWebSocket.ts         # WS connection mgmt
│   │   │
│   │   ├── stores/                     # Zustand stores
│   │   │   ├── pipelineStore.ts
│   │   │   ├── projectStore.ts
│   │   │   └── uiStore.ts
│   │   │
│   │   ├── lib/                        # Utilities
│   │   │   ├── api.ts                  # Fetch + React Query
│   │   │   ├── websocket.ts            # WS client
│   │   │   ├── formats.ts              # Time formatting, etc.
│   │   │   └── constants.ts            # Scene types, statuses, etc.
│   │   │
│   │   └── styles/
│   │       ├── globals.css             # Global styles + CSS vars
│   │       └── components.css          # Component styles
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── fonts/                      # Self-hosted fonts
│   │       ├── Inter.woff2
│   │       ├── Outfit.woff2
│   │       └── JetBrainsMono.woff2
│   │
│   ├── .env.example
│   ├── .eslintrc.json
│   └── tailwind.config.ts
│
├── docker-compose.yml                  # Unified service orchestration
├── docker-compose.dev.yml              # Development overrides
├── Makefile                            # Build automation
├── .env.example                        # Shared env template
├── .gitignore
└── README.md                           # Project documentation
```

---

## Part 7: Docker Composition

### 7.1 Production Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ===== Frontend =====
  frontend:
    build:
      context: ./videoforge-frontend
      dockerfile: Dockerfile.prod
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_WS_URL=ws://backend:8000/ws
    depends_on:
      - backend
    volumes:
      - ./videoforge-frontend/public:/app/public
    deploy:
      resources:
        limits:
          memory: 1G

  # ===== Backend API =====
  backend:
    build:
      context: ./videoforge-backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://videoforge:videoforge@postgres:5432/videoforge
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PRESENTON_URL=http://presenton:5001
      - ELEVENLABS_STYLETTS_URL=http://elevenlabs-stylitts:8000
      - ELEVENLABS_SEEDVC_URL=http://elevenlabs-seedvc:8001
      - STORAGE_PATH=/app/storage
    volumes:
      - ./projects:/app/projects
      - ./compose:/app/compose
      - ./storage:/app/storage
      - ./skills:/app/skills
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      presenton:
        condition: service_healthy
      elevenlabs-stylitts:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  # ===== Celery Worker =====
  celery-worker:
    build:
      context: ./videoforge-backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://videoforge:videoforge@postgres:5432/videoforge
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - PRESENTON_URL=http://presenton:5001
      - ELEVENLABS_STYLETTS_URL=http://elevenlabs-stylitts:8000
    volumes:
      - ./projects:/app/projects
      - ./compose:/app/compose
      - ./storage:/app/storage
      - ./skills:/app/skills
    depends_on:
      - backend
      - redis
      - presenton
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

  # ===== Celery Beat (scheduled tasks) =====
  celery-beat:
    build:
      context: ./videoforge-backend
      dockerfile: Dockerfile
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A app.workers.celery_app beat --loglevel=info

  # ===== Flower (Celery monitoring) =====
  flower:
    build:
      context: ./videoforge-backend
      dockerfile: Dockerfile
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A app.workers.celery_app flower --port=5555

  # ===== PostgreSQL =====
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=videoforge
      - POSTGRES_PASSWORD=videoforge
      - POSTGRES_DB=videoforge
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U videoforge"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ===== Redis =====
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ===== Presenton =====
  presenton:
    build:
      context: ./presenton/servers/fastapi
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://presenton:presenton@postgres:5432/presenton
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./presenton/data:/app/app_data
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===== ElevenLabs StyleTTS2 =====
  elevenlabs-stylitts:
    build:
      context: ./ElevenLabs
      dockerfile: Dockerfile.stylitts
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./ElevenLabs/models:/app/models
      - ./storage/audio:/app/output
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 10

  # ===== ElevenLabs SeedVC =====
  elevenlabs-seedvc:
    build:
      context: ./ElevenLabs
      dockerfile: Dockerfile.seedvc
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./ElevenLabs/models:/app/models
      - ./storage/audio:/app/output

  # ===== ElevenLabs Make-An-Audio =====
  elevenlabs-maa:
    build:
      context: ./ElevenLabs
      dockerfile: Dockerfile.maa
    ports:
      - "8002:8002"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # ===== MinIO (S3-compatible for asset storage) =====
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    environment:
      - MINIO_ROOT_USER=videoforge
      - MINIO_ROOT_PASSWORD=videoforge123
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  redisdata:
  miniodata:
```

---

## Part 8: API Contract (Backend → Frontend)

### REST API

```
# Projects
GET    /api/projects                    # List all projects
POST   /api/projects                    # Create new project
GET    /api/projects/{id}               # Get project details
PATCH  /api/projects/{id}               # Update project
DELETE /api/projects/{id}               # Delete project

# Pipeline
POST   /api/projects/{id}/pipeline/start    # Start pipeline
POST   /api/projects/{id}/pipeline/pause    # Pause
POST   /api/projects/{id}/pipeline/resume   # Resume
POST   /api/projects/{id}/pipeline/restart  # Restart from stage
POST   /api/projects/{id}/pipeline/stop     # Stop

# Stages
GET    /api/projects/{id}/stages              # List all stages
GET    /api/projects/{id}/stages/{stage}     # Get stage details
POST   /api/projects/{id}/stages/{stage}/approve    # Approve stage
POST   /api/projects/{id}/stages/{stage}/reject     # Reject + feedback
POST   /api/projects/{id}/stages/{stage}/modify    # Modify + re-run

# Assets
GET    /api/projects/{id}/assets              # List all assets
GET    /api/projects/{id}/assets/{asset_id}   # Get asset detail
GET    /api/projects/{id}/assets/{asset_id}/download  # Download asset
POST   /api/projects/{id}/assets/upload       # Upload custom asset
GET    /api/projects/{id}/preview/{scene_id}  # Get scene preview (frame)

# Video
GET    /api/projects/{id}/video/preview       # Stream video preview
GET    /api/projects/{id}/video/download      # Download final video
GET    /api/projects/{id}/video/thumbnail     # Get thumbnail

# Settings
GET    /api/settings                        # Get global settings
PATCH  /api/settings                        # Update settings
GET    /api/services/health                 # Check all services
```

### WebSocket Events (Backend → Frontend)

```typescript
// events.ts — TypeScript event types

export type PipelineEvent =
  | { type: "pipeline_started"; data: { project_id: string } }
  | { type: "pipeline_complete"; data: { project_id: string; video_url: string } }
  | { type: "pipeline_failed"; data: { project_id: string; error: string } }
  | { type: "pipeline_paused"; data: { project_id: string; stage: string } }
  ;

export type StageEvent =
  | { type: "stage_started"; data: { stage: string; estimated_seconds?: number } }
  | { type: "stage_progress"; data: { stage: string; progress: number; message: string; eta_seconds?: number } }
  | { type: "stage_complete"; data: { stage: string; artifacts: ArtifactInfo[] } }
  | { type: "stage_failed"; data: { stage: string; error: string; can_retry: boolean } }
  | { type: "stage_awaiting_approval"; data: { stage: string; approval_data: any } }
  ;

export type SceneEvent =
  | { type: "scene_generated"; data: { chapter: number; scene: string; type: SceneType; preview_url: string; duration: number } }
  | { type: "asset_generated"; data: { asset_type: string; asset_id: string; preview_url: string } }
  ;

export type RenderEvent =
  | { type: "render_progress"; data: { chapter: number; frame_current: number; frame_total: number; fps: number } }
  | { type: "render_chapter_complete"; data: { chapter: number; video_url: string } }
  | { type: "render_complete"; data: { video_url: string; thumbnail_url: string } }
  ;

export type LogEvent =
  | { type: "log"; data: { level: "info" | "warn" | "error"; message: string; timestamp: string } }
  ;

export type ServerEvent = PipelineEvent | StageEvent | SceneEvent | RenderEvent | LogEvent;
```

---

## Part 9: Implementation Plan (Quality-First, Phased)

### Phase 1: Backend Foundation (Week 1-2)
**Goal**: Full backend running with pipeline orchestration, no frontend yet.

```
□ Set up FastAPI project structure
□ Implement config + environment loading
□ Implement all data models (Project, Stage, Asset, Approval)
□ Set up PostgreSQL + SQLAlchemy + Alembic
□ Set up Redis + Celery
□ Implement WebSocket hub
□ Implement event bus (Redis pub/sub)
□ Implement Claude adapter
□ Implement Presenton adapter
□ Implement ElevenLabs adapter
□ Implement pipeline orchestrator (state machine)
□ Implement checkpoint/resume system
□ Implement all 9 pipeline stages (research → publish)
□ Write unit tests for models, adapters, stages
□ Docker compose with all services
□ End-to-end test: project → all stages → JSON artifacts
```

### Phase 2: Rendering Engines (Week 3-4)
**Goal**: Can render actual video from scene plans.

```
□ Implement HyperFrames adapter (init, render_scene, render_composition)
□ Create all 14 HTML scene templates
□ Implement style guide injection into templates
□ Implement code visualization template with typing animation
□ Implement chart animation templates (bar, line, pie)
□ Implement anime scene template with particles + camera
□ Implement Remotion renderer (for chart-heavy scenes)
□ Implement FFmpeg renderer (stitching, subtitles, color grade)
□ Implement compose stage (chapter rendering + final assembly)
□ Implement audio mixing pipeline (narration + music + SFX)
□ Write tests for each renderer
□ Test: scene plan → chapter MP4
□ Test: 5 chapters → final concatenated video
```

### Phase 3: Frontend Core (Week 5-6)
**Goal**: Beautiful, functional frontend for project management.

```
□ Set up Next.js + TypeScript + Tailwind
□ Implement design system (colors, typography, components)
□ Implement project gallery page
□ Implement new project wizard
□ Implement project dashboard with live pipeline timeline
□ Implement WebSocket client with React hooks
□ Implement real-time progress updates in UI
□ Implement pipeline timeline component
□ Implement stage detail panels
□ Implement approval gate UI
□ Implement activity feed
□ Implement responsive layout
```

### Phase 4: Frontend Editors (Week 7-8)
**Goal**: Script editor, scene editor, asset management.

```
□ Implement script editor (rich text + timing)
□ Implement scene plan editor (drag-drop, visual arrangement)
□ Implement asset library (browse, preview, download)
□ Implement video preview player (custom controls, chapter markers)
□ Implement scene preview (render single scene for review)
□ Implement project settings page
□ Implement style guide editor
□ Implement taste profile dials UI
□ Connect all editors to backend API
□ Implement optimistic updates + error handling
```

### Phase 5: Quality + Polish (Week 9-10)
**Goal**: Production-ready, quality-assured output.

```
□ Implement automated quality checker
□ Implement AI-powered reviewer (Claude vision)
□ Implement style guide compliance checker
□ Implement scene variety validator
□ Implement performance profiler (render time, API cost)
□ Add error handling + retry logic throughout
□ Add progress persistence (resumability)
□ Add cost tracking dashboard
□ Add batch export (multiple resolutions/formats)
□ Implement thumbnail generation
□ Implement subtitle generation (word-level timed)
□ Performance optimization (parallel rendering, caching)
□ Load testing
□ Documentation
□ End-to-end integration test
```

---

## Part 10: What Makes This the BEST

Compared to every existing tool:

| Feature | Runway | Pika | Sora | OpenMontage (alone) | **VideoForge** |
|---------|--------|------|------|---------------------|----------------|
| Long-form (40-50 min) | ❌ | ❌ | ❌ | ✅ (manual) | ✅ (automated chapters) |
| Interactive frontend | ❌ | ❌ | ❌ | ❌ | ✅ (full dashboard) |
| Real-time progress | ❌ | ❌ | ❌ | ❌ | ✅ (WebSocket) |
| Human approval gates | ❌ | ❌ | ❌ | ✅ (CLI only) | ✅ (UI + API) |
| Code visualization | ❌ | ❌ | ❌ | ⚠️ (basic) | ✅ (animated typing + walkthrough) |
| 12 scene types | ❌ | ❌ | ❌ | ✅ | ✅ (all 12) |
| Chart animations | ❌ | ❌ | ❌ | ✅ | ✅ (10 animation styles) |
| Anime + particles | ❌ | ❌ | ❌ | ✅ | ✅ |
| Talking head + lip sync | ❌ | ❌ | ❌ | ✅ | ✅ |
| Style guide enforcement | ❌ | ❌ | ❌ | ⚠️ | ✅ (per-project locked) |
| Taste profile dials | ❌ | ❌ | ❌ | ❌ | ✅ (creative control) |
| Chapter transitions | ❌ | ❌ | ❌ | ⚠️ | ✅ (seamless) |
| Layered audio | ❌ | ❌ | ❌ | ✅ | ✅ (narration + music + SFX + subs) |
| Voice cloning | ❌ | ❌ | ❌ | ⚠️ | ✅ (SeedVC local) |
| Resumability | ❌ | ❌ | ❌ | ✅ | ✅ (checkpoint + Celery) |
| Cost tracking | ❌ | ❌ | ❌ | ✅ | ✅ (per-stage dashboard) |
| Quality AI reviewer | ❌ | ❌ | ❌ | ✅ | ✅ |
| Open source / self-hosted | ❌ | ❌ | ❌ | ✅ | ✅ |

**No existing tool comes close to this combination of quality, control, and automation.**

---

## Summary

VideoForge is not "another AI video tool." It's a **professional video production pipeline** that happens to use AI for content creation. The frontend + backend architecture gives you:

1. **Full creative control** — review and edit at every stage
2. **Real-time visibility** — watch your video being made, scene by scene
3. **Professional quality** — 12 scene types, cinematic motion, layered audio, style enforcement
4. **Long-form capability** — automated chapter splitting with continuity
5. **Resumability** — never lose work, restart from any stage
6. **Cost visibility** — track spending per stage in real-time
7. **Quality assurance** — automated + AI-powered checks at every stage

The implementation is 10 weeks, 5 phases, fully testable. Every component has a clear contract, clear tests, and clear integration points.
