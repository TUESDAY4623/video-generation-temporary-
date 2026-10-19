# VideoForge - Complete Implementation Plan

## Executive Summary

**VideoForge** is a unified video generation platform that takes a simple user prompt (topic + sub-topic + explanation) and automatically produces 40-50 minute educational/explainer videos with:
- AI-generated narration scripts (Claude API)
- Voice-over audio (local ElevenLabs services)
- Animated visuals, diagrams, code visualizations (OpenMontage pipeline + HyperFrames rendering)
- Structured slide layouts (Presenton)
- Professional composition and export (OpenMontage compose stage + HyperFrames)

---

## Part 1: Architecture Overview

```
USER INPUT (topic + subtopic + explanation)
         |
         v
  +------------------+
  |  VideoForge CLI  |  <-- Main entry point (Python)
  +------------------+
         |
         | orchestrates
         v
  +------------------+      +------------------+
  |   Claude API     |      |  Presenton API   |
  |  (Content Intel) |      |  (Slide Design)  |
  +------------------+      +------------------+
         |                        |
         v                        v
  +------------------------------------------+
  |       OpenMontage Pipeline Engine        |
  |  (research -> script -> scene_plan ->    |
  |   assets -> edit -> compose)             |
  +------------------------------------------+
         |              |              |
         v              v              v
  +-------------+ +------------+ +-----------------+
  |  Local      | | HyperFrames| |   FFmpeg        |
  | ElevenLabs  | | (Rendering)| |   (Post-prod)   |
  | (TTS/Audio) | |            | |                 |
  +-------------+ +------------+ +-----------------+
         |              |              |
         +--------------+--------------+
                        v
              +-------------------+
              |  Final MP4 Video  |
              +-------------------+
```

---

## Part 2: Project Structure

### New Files to Create (VideoForge System)

```
d:\Coder_S3\video generation v3\
├── videoforge/                          # <-- NEW: Main orchestration system
│   ├── __init__.py
│   ├── config.py                        # Environment & service config
│   ├── main.py                          # CLI entry point
│   ├── orchestrator.py                  # Master orchestrator (state machine)
│   │
│   ├── stages/                          # Pipeline stage implementations
│   │   ├── __init__.py
│   │   ├── research_stage.py            # Claude-powered content research
│   │   ├── script_stage.py              # Narration script generation
│   │   ├── chapter_stage.py             # Long-form chapter segmentation (NEW)
│   │   ├── scene_plan_stage.py          # Scene-by-scene breakdown
│   │   ├── asset_stage.py               # Asset generation orchestration
│   │   ├── compose_stage.py             # Final composition & rendering
│   │   └── publish_stage.py             # Export final video
│   │
│   ├── adapters/                        # Adapters to external systems
│   │   ├── __init__.py
│   │   ├── claude_adapter.py            # Wrapper for Claude API calls
│   │   ├── presenton_adapter.py         # Presenton API client
│   │   ├── elevenlabs_adapter.py        # Local ElevenLabs TTS client
│   │   ├── hyperframes_adapter.py       # HyperFrames render engine
│   │   ├── openmontage_adapter.py       # OpenMontage tool/pipeline runner
│   │   └── ffmpeg_adapter.py            # FFmpeg composition utility
│   │
│   ├── generators/                      # Content generation (Claude-driven)
│   │   ├── __init__.py
│   │   ├── content_researcher.py        # Deep research on topic
│   │   ├── script_writer.py             # Narration script with timing
│   │   ├── chapterizer.py               # Splits 40-50min into chapters
│   │   ├── visual_designer.py           # Designs visual plan per scene
│   │   ├── code_visualizer.py           # Generates code visualization specs
│   │   ├── diagram_spec.py              # Diagram/chart specifications
│   │   └── slide_spec.py                # Presenton-compatible slide specs
│   │
│   ├── models/                          # Data models
│   │   ├── __init__.py
│   │   ├── user_input.py                # UserRequest dataclass
│   │   ├── video_project.py             # VideoProject state
│   │   ├── chapter.py                   # Chapter (segment of long video)
│   │   ├── scene.py                     # Scene (unit within chapter)
│   │   ├── script.py                    # Script with timing data
│   │   ├── asset_manifest.py            # All generated assets
│   │   ├── render_spec.py               # HyperFrames/Remotion render spec
│   │   └── pipeline_state.py            # Checkpoint/resume state
│   │
│   ├── chapterizer/                     # 40-50min video strategy
│   │   ├── __init__.py
│   │   ├── segmenter.py                 # Splits topic into chapters
│   │   ├── consistency.py               # Maintains visual/audio consistency
│   │   ├── context_manager.py           # Manages Claude context across chapters
│   │   └── continuity.py                # Ensures seamless chapter transitions
│   │
│   ├── skills/                          # Skill definitions (like OpenMontage)
│   │   ├── __init__.py
│   │   ├── content-research-director.md # How to research a topic
│   │   ├── script-director.md           # How to write narration scripts
│   │   ├── chapter-director.md          # How to chapterize long content
│   │   ├── scene-director.md            # How to design scenes
│   │   ├── code-viz-director.md         # How to visualize code
│   │   ├── asset-director.md            # How to generate/manage assets
│   │   ├── compose-director.md          # How to compose final video
│   │   └── hyperframes-skills/          # Reuse from skills folder
│   │       ├── gsap.md
│   │       ├── tailwind.md
│   │       ├── three.md
│   │       ├── lottie.md
│   │       ├── animejs.md
│   │       └── css-animations.md
│   │
│   ├── templates/                       # HyperFrames HTML templates
│   │   ├── base-layout.html             # Base HTML template for scenes
│   │   ├── text-scene.html              # Text/title card scene
│   │   ├── code-scene.html              # Code visualization scene
│   │   ├── diagram-scene.html           # Diagram/chart scene
│   │   ├── transition.html              # Scene transition
│   │   └── chapter-intro.html           # Chapter opening sequence
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── checkpoint.py                # Save/load progress for resume
│   │   ├── cost_tracker.py              # Track API costs
│   │   ├── validators.py                # Validate scripts, scenes, assets
│   │   └── file_utils.py                # Path management
│   │
│   └── pyproject.toml                   # Python package config
│
├── compose/                             # <-- NEW: HyperFrames compositions
│   ├── projects/                         # Per-video render projects
│   │   └── <topic-slug>/
│   │       ├── manifest.json            # HyperFrames project manifest
│   │       ├── scenes/                  # Per-scene HTML files
│   │       │   ├── ch01-sc01.html
│   │       │   ├── ch01-sc02.html
│   │       │   └── ...
│   │       ├── assets/                  # Images, audio, fonts
│   │       └── output/                  # Rendered video segments
│   │
│   └── registry/                        # HyperFrames block registry
│       ├── text-cards.json
│       ├── code-blocks.json
│       ├── diagrams.json
│       └── transitions.json
│
├── projects/                            # VideoForge project workspaces
│   └── <topic-slug>/
│       ├── project.json                 # Project metadata
│       ├── checkpoint_*.json            # Stage checkpoints
│       ├── artifacts/                   # JSON artifacts per stage
│       │   ├── research_brief.json
│       │   ├── script.json
│       │   ├── chapter_plan.json
│       │   ├── scene_plan.json
│       │   └── asset_manifest.json
│       ├── assets/
│       │   ├── images/                  # Generated images
│       │   ├── audio/                   # Narration segments (MP3)
│       │   ├── music/                   # Background music
│       │   └── subtitles.srt
│       └── renders/
│           └── final.mp4
│
├── open montage/                         # EXISTING - Use as-is
├── presenton/                            # EXISTING - Use as-is
├── ElevenLabs/                           # EXISTING - Use as-is
├── hygen/hyperframes-main/               # EXISTING - Use as-is
├── skills/                               # EXISTING - Reuse skills
├── docker-compose.yml                    # <-- NEW: Unified service orchestration
├── Makefile                              # <-- NEW: Build automation
├── .env.example                          # <-- NEW: Environment template
└── README.md                             # <-- NEW: Project documentation
```

---

## Part 3: The 40-50 Minute Video Strategy

### The Core Challenge

Generating a 40-50 minute video is fundamentally different from a 2-minute explainer:

1. **Context Window Limits**: Claude's context window cannot hold an entire 40-minute script. We need chunking.
2. **Visual Consistency**: 40 minutes of video needs a cohesive visual identity across hundreds of scenes.
3. **Audio Consistency**: Narration must have consistent voice, pacing, and energy.
4. **Cost Management**: 40-50 minutes of video = thousands of API calls. Needs budget tracking.
5. **Resumability**: A 4-hour generation job must survive restarts and partial failures.
6. **Memory**: The system must "remember" the topic, tone, and visual style across all chapters.

### Solution: Chapter-Based Architecture

The video is split into **Chapters** (8-15 minutes each), each independently generated but orchestrated by a master context.

```
40-50 Minute Video
│
├── Chapter 1: "Introduction to <Topic>"      (8-10 min)
│   ├── Scene 1.1  - Hook / Title Card          (30s)
│   ├── Scene 1.2  - What is <Topic>?           (90s)
│   ├── Scene 1.3  - Why Does It Matter?        (90s)
│   ├── Scene 1.4  - Key Concept 1 (visual)     (120s)
│   └── Scene 1.5  - Code Example 1             (180s)
│
├── Chapter 2: "Deep Dive into <Subtopic A>"  (8-10 min)
│   ├── Scene 2.1  - Chapter Intro Card          (30s)
│   ├── Scene 2.2  - Core Mechanism              (150s)
│   ├── Scene 2.3  - Diagram / Flow              (120s)
│   ├── Scene 2.4  - Code Walkthrough            (180s)
│   └── Scene 2.5  - Real-World Example          (120s)
│
├── Chapter 3: "Advanced <Subtopic B>"        (8-10 min)
│   └── ... (5-7 scenes)
│
├── Chapter 4: "Practical Applications"       (8-10 min)
│   └── ... (5-7 scenes)
│
├── Chapter 5: "Future & Conclusion"          (8-10 min)
│   ├── Scene 5.1  - Summary                     (120s)
│   ├── Scene 5.2  - Future Outlook              (120s)
│   └── Scene 5.3  - Final CTA / Credits         (60s)
│
└── Total: 5 chapters × ~8-10 min = 40-50 min
```

### Chapter Generation Strategy

Each chapter is generated semi-independently but inherits a **Global Context Object**:

```python
class GlobalVideoContext:
    topic: str                    # "Machine Learning"
    subtopic: str                 # "Neural Networks"
    user_explanation: str         # User's 5-10 line explanation
    target_audience: str          # "beginners" / "intermediate" / "experts"
    visual_style: str             # "flat-motion" / "minimalist-diagram" / "premium"
    color_palette: list[str]      # Primary, secondary, accent colors
    voice_profile: dict           # Voice settings for ElevenLabs
    pacing: str                    # "relaxed" / "moderate" / "fast"
    chapter_outline: list[ChapterOutline]  # Pre-planned chapter structure
```

Each chapter receives this context plus its own specific outline, ensuring consistency.

---

## Part 4: Complete Workflow (Stage by Stage)

### Stage 0: Initialization

**Input**: User provides topic, subtopic, 5-10 line explanation
**Output**: `project.json`, workspace directories, GlobalVideoContext

```
1. Receive user input
2. Create project workspace under projects/<topic-slug>/
3. Initialize checkpoint system
4. Call Claude to generate GlobalVideoContext:
   - Determine target audience
   - Propose visual style
   - Create chapter outline (5 chapters)
   - Define color palette
   - Set pacing
5. Save to project.json
6. Present plan to user for approval
```

### Stage 1: Content Research (Claude-Powered)

**Input**: GlobalVideoContext
**Output**: `research_brief.json`
**Tool**: Claude API (Haiku/Sonnet)

```
For each chapter:
  1. Call Claude with: topic + subtopic + user_explanation + chapter_theme
  2. Claude generates:
     - Key concepts to cover
     - Analogies and examples
     - Code snippets (if technical topic)
     - Diagram ideas
     - Common misconceptions to address
     - Narration talking points
  3. Validate: each chapter has 4-7 talking points
  4. Save chapter research brief
```

### Stage 2: Script Writing (Claude-Powered)

**Input**: research_brief.json, GlobalVideoContext
**Output**: `script.json` (with timing per scene)
**Tool**: Claude API (Sonnet)

```
For each chapter:
  1. Call Claude with chapter research brief
  2. Generate narration script with:
     - Word-level timing (150 words/min target)
     - Scene breaks with visual cues [VISUAL: diagram of X]
     - Code snippet annotations [CODE: Python example of Y]
     - Emphasis markers [PAUSE], [EMPHASIS]
  3. Validate:
     - Each scene: 60s - 180s duration
     - Total chapter: 8-10 minutes
     - Word count matches timing
  4. Save script with per-scene timings
```

### Stage 3: Chapter Plan & Scene Breakdown

**Input**: script.json
**Output**: `chapter_plan.json`, `scene_plan.json`
**Tool**: Internal logic + Claude validation

```
1. Split script into chapters (already done in script)
2. For each chapter, break into scenes:
   - Scene types: title_card, explanation, diagram, code_viz, example, summary
   - Each scene gets: narration_segment, visual_type, duration, assets_needed
3. Presenton Integration:
   - For "explanation" scenes: generate Presenton slide spec
   - For "title_card" scenes: generate hero slide spec
   - Call Presenton API to generate slide layouts (if needed)
4. Save scene plan with asset requirements
```

### Stage 4: Asset Generation

**Input**: scene_plan.json, asset_manifest.json
**Output**: All images, audio segments, diagrams
**Tools**: Local ElevenLabs (TTS), image generation, diagram tools

```
For each scene across all chapters:
  Parallel (within reason):
  │
  ├── AUDIO: Generate narration via ElevenLabs local service
  │   - Input: scene narration text
  │   - Voice: from GlobalVideoContext.voice_profile
  │   - Output: projects/<slug>/assets/audio/chXX-scXX.mp3
  │
  ├── VISUALS: Generate scene visuals
  │   ├── If "title_card": Generate hero image (image gen API)
  │   ├── If "diagram": Generate diagram spec for HyperFrames
  │   ├── If "code_viz": Generate code visualization HTML
  │   ├── If "explanation": Generate slide via Presenton
  │   │   - Call Presenton API with slide spec
  │   │   - Download generated PPTX/slide images
  │   └── If "example": Generate relevant image/animation
  │
  └── SUBTITLES: Generate SRT from narration text + timing
```

### Stage 5: Composition & Rendering

**Input**: All assets, scene_plan.json
**Output**: Final MP4
**Tools**: HyperFrames (primary), FFmpeg (fallback/stitching)

```
For each chapter:
  1. Build HyperFrames composition:
     - Base layout from templates/base-layout.html
     - Scene HTML from templates/
     - Inject narration audio
     - Add transitions between scenes
     - Add background music (ducked during narration)
  2. Render chapter video via HyperFrames:
     npx hyperframes render compose/ch01/ --output renders/ch01.mp4
  3. Concatenate chapters via FFmpeg:
     ffmpeg -f concat -i chapter_list.txt -c copy renders/full.mp4
  4. Burn subtitles:
     ffmpeg -i renders/full.mp4 -vf subtitles=assets/subtitles.srt final.mp4
```

---

## Part 5: Key Components Deep Dive

### 5.1 Claude Adapter

```python
# videoforge/adapters/claude_adapter.py

import anthropic
from dataclasses import dataclass
from typing import Any

@dataclass
class ClaudeConfig:
    api_key: str
    model: str = "claude-sonnet-5-20250626"
    max_tokens: int = 8192
    temperature: float = 0.7

class ClaudeAdapter:
    """Wrapper for all Claude API calls in VideoForge."""

    def __init__(self, config: ClaudeConfig):
        self.client = anthropic.Anthropic(api_key=config.api_key)
        self.config = config

    def research_topic(self, context: GlobalVideoContext, chapter: int) -> dict:
        """Generate research brief for a chapter."""
        prompt = self._build_research_prompt(context, chapter)
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            temperature=0.7,
            system=RESEARCH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_research(response.content[0].text)

    def write_script(self, research: dict, context: GlobalVideoContext) -> dict:
        """Generate narration script from research brief."""
        prompt = self._build_script_prompt(research, context)
        response = self.client.messages.create(
            model="claude-sonnet-5-20250626",
            max_tokens=8192,
            temperature=0.8,
            system=SCRIPT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_script(response.content[0].text)

    def design_visuals(self, scene: Scene, context: GlobalVideoContext) -> dict:
        """Design visual plan for a single scene."""
        # ... scene-specific visual design

    def generate_code_viz(self, code: str, language: str) -> str:
        """Generate HTML/CSS for code visualization."""
        # Returns HTML string for HyperFrames rendering
```

### 5.2 Presenton Adapter

```python
# videoforge/adapters/presenton_adapter.py

import httpx
from dataclasses import dataclass

@dataclass
class PresentonConfig:
    base_url: str = "http://localhost:5001/api/v1"
    api_key: str = ""

class PresentonAdapter:
    """Client for Presenton's presentation generation API."""

    def __init__(self, config: PresentonConfig):
        self.base_url = config.base_url
        self.client = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=120.0
        )

    def generate_slide(self, slide_spec: SlideSpec) -> bytes:
        """Generate a single slide image from specification."""
        response = self.client.post("/ppt/generate-slide", json={
            "title": slide_spec.title,
            "content": slide_spec.content,
            "layout": slide_spec.layout,
            "style": slide_spec.style,
            "include_code": slide_spec.include_code,
        })
        response.raise_for_status()
        return response.content  # PNG bytes

    def generate_presentation_outline(self, topic: str, num_slides: int) -> dict:
        """Generate outline for a multi-slide presentation."""
        response = self.client.post("/ppt/generate-outline", json={
            "topic": topic,
            "num_slides": num_slides,
        })
        return response.json()

    def generate_from_template(self, outline: dict, template_id: str) -> bytes:
        """Generate full PPTX from outline using template."""
        response = self.client.post("/ppt/generate-from-template", json={
            "outline": outline,
            "template_id": template_id,
        })
        return response.content  # PPTX bytes
```

### 5.3 ElevenLabs Adapter (Local)

```python
# videoforge/adapters/elevenlabs_adapter.py

import httpx
from pathlib import Path

@dataclass
class ElevenLabsConfig:
    styletts_url: str = "http://localhost:8000"
    seedvc_url: str = "http://localhost:8001"
    voice_id: str = "default"
    stability: float = 0.5
    similarity_boost: float = 0.75

class ElevenLabsAdapter:
    """Client for local ElevenLabs services."""

    def __init__(self, config: ElevenLabsConfig):
        self.config = config
        self.style_client = httpx.Client(base_url=config.styletts_url, timeout=60.0)
        self.seed_client = httpx.Client(base_url=config.seedvc_url, timeout=60.0)

    def generate_narration(self, text: str, output_path: Path) -> Path:
        """Generate narration audio for a scene segment."""
        response = self.style_client.post("/tts", json={
            "text": text,
            "voice_id": self.config.voice_id,
            "stability": self.config.stability,
            "similarity_boost": self.config.similarity_boost,
        })
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return output_path

    def generate_music(self, mood: str, duration_seconds: int) -> Path:
        """Generate background music (optional, uses Make-An-Audio)."""
        # Call port 8002 service
        pass

    def check_health(self) -> dict:
        """Check status of all local services."""
        status = {}
        for name, url in [("StyleTTS2", self.config.styletts_url),
                          ("SeedVC", self.config.seedvc_url)]:
            try:
                r = httpx.get(f"{url}/health", timeout=5.0)
                status[name] = "ok" if r.status_code == 200 else "error"
            except Exception:
                status[name] = "unavailable"
        return status
```

### 5.4 HyperFrames Adapter

```python
# videoforge/adapters/hyperframes_adapter.py

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class HyperFramesConfig:
    project_dir: Path
    output_dir: Path

class HyperFramesAdapter:
    """Wrapper for HyperFrames rendering."""

    def __init__(self, config: HyperFramesConfig):
        self.config = config

    def init_project(self, topic_slug: str) -> Path:
        """Initialize HyperFrames project structure."""
        project_path = self.config.project_dir / topic_slug
        subprocess.run(
            ["npx", "hyperframes", "init", str(project_path)],
            check=True, capture_output=True
        )
        return project_path

    def render_scene(self, scene_html: str, scene_id: str, duration: float) -> Path:
        """Render a single scene HTML to video segment."""
        scene_path = self.config.project_dir / "scenes" / f"{scene_id}.html"
        scene_path.write_text(scene_html)

        output = self.config.output_dir / f"{scene_id}.mp4"
        subprocess.run(
            ["npx", "hyperframes", "render",
             str(scene_path),
             "--output", str(output),
             "--duration", str(duration)],
            check=True, capture_output=True
        )
        return output

    def render_composition(self, manifest_path: Path, output_path: Path) -> Path:
        """Render full composition from manifest."""
        subprocess.run(
            ["npx", "hyperframes", "render",
             str(manifest_path),
             "--output", str(output_path)],
            check=True, capture_output=True
        )
        return output_path

    def create_scene_html(self, scene: Scene, template_name: str) -> str:
        """Generate HTML for a scene from template + scene data."""
        template_path = Path(__file__).parent.parent / "templates" / f"{template_name}.html"
        template = template_path.read_text()
        return template.replace("{{TITLE}}", scene.title) \
                       .replace("{{CONTENT}}", scene.content) \
                       .replace("{{DURATION}}", str(scene.duration))
```

### 5.5 Chapterizer (The Key Innovation for Long-Form)

```python
# videoforge/chapterizer/segmenter.py

from dataclasses import dataclass, field
from typing import List
import anthropic

@dataclass
class ChapterOutline:
    chapter_number: int
    title: str
    subtitle: str
    themes: List[str]
    estimated_duration_minutes: int
    key_concepts: List[str]
    code_examples: List[str]
    scenes_estimate: int  # 5-7 scenes per chapter

@dataclass
class ChapterPlan:
    topic: str
    total_duration_target_minutes: int
    chapters: List[ChapterOutline]

class Chapterizer:
    """Splits a topic into coherent chapters for long-form video."""

    def __init__(self, claude_client: anthropic.Anthropic):
        self.claude = claude_client

    def create_chapter_plan(self, context: GlobalVideoContext) -> ChapterPlan:
        """Use Claude to intelligently split a topic into chapters."""
        prompt = f"""
        Create a chapter plan for a {context.target_duration_minutes}-minute
        educational video about "{context.topic}".

        User's context: {context.user_explanation}
        Subtopic focus: {context.subtopic}
        Target audience: {context.target_audience}

        Create exactly 5 chapters, each 8-10 minutes.
        For each chapter, provide:
        - Title and subtitle
        - 3-5 key themes/concepts
        - Whether it needs code examples
        - Estimated scene count (5-7 scenes)

        Respond in JSON format matching the ChapterPlan schema.
        """

        response = self.claude.messages.create(
            model="claude-sonnet-5-20250626",
            max_tokens=4096,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse and return ChapterPlan
        ...

    def get_chapter_context(self, plan: ChapterPlan, chapter_num: int,
                            global_ctx: GlobalVideoContext) -> dict:
        """Build context for a single chapter, including continuity info."""
        chapter = plan.chapters[chapter_num - 1]
        prev_chapter = plan.chapters[chapter_num - 2] if chapter_num > 1 else None
        next_chapter = plan.chapters[chapter_num] if chapter_num < len(plan.chapters) else None

        return {
            "chapter": chapter.__dict__,
            "previous_chapter_summary": self._summarize(prev_chapter) if prev_chapter else None,
            "next_chapter_preview": self._preview(next_chapter) if next_chapter else None,
            "global_context": global_ctx.__dict__,
            "visual_consistency_rules": self._consistency_rules(global_ctx),
        }
```

### 5.6 Context Manager (Prevents Context Window Overflow)

```python
# videoforge/chapterizer/context_manager.py

class ContextManager:
    """Manages Claude context across multiple chapter generations."""

    def __init__(self, global_context: GlobalVideoContext):
        self.global = global_context
        self.chapter_history: list[dict] = []  # Summaries of completed chapters
        self.max_context_tokens = 100_000  # Leave headroom for responses

    def build_chapter_prompt(self, chapter_num: int, chapter_ctx: dict) -> str:
        """Build a context-aware prompt that stays within token limits."""
        prompt_parts = [
            f"=== GLOBAL CONTEXT (always in scope) ===",
            f"Topic: {self.global.topic}",
            f"Audience: {self.global.target_audience}",
            f"Visual Style: {self.global.visual_style}",
            f"Color Palette: {self.global.color_palette}",
            "",
        ]

        # Add summaries of previous chapters (compressed)
        if self.chapter_history:
            prompt_parts.append("=== PREVIOUS CHAPTERS SUMMARY ===")
            for i, hist in enumerate(self.chapter_history):
                prompt_parts.append(
                    f"Chapter {i+1} ({hist['title']}): {hist['summary'][:200]}..."
                )
            prompt_parts.append("")

        # Add current chapter specific context
        prompt_parts.append(f"=== CURRENT CHAPTER: {chapter_ctx['chapter']['title']} ===")
        prompt_parts.append(f"Subtitle: {chapter_ctx['chapter']['subtitle']}")
        prompt_parts.append(f"Key concepts: {', '.join(chapter_ctx['chapter']['key_concepts'])}")
        if chapter_ctx.get('previous_chapter_summary'):
            prompt_parts.append(f"\nBridges from previous: {chapter_ctx['previous_chapter_summary']}")
        if chapter_ctx.get('next_chapter_preview'):
            prompt_parts.append(f"\nLeads into next: {chapter_ctx['next_chapter_preview']}")

        return "\n".join(prompt_parts)

    def record_chapter_completion(self, chapter_num: int, summary: str):
        """Record completed chapter for continuity in future chapters."""
        self.chapter_history.append({
            "chapter": chapter_num,
            "summary": summary,
        })
```

---

## Part 6: Presenton Integration Details

Presenton is used for **slide/visual layout planning**, not as the final renderer.

### How Presenton Feeds Into VideoForge

```
Scene Type: "explanation" or "title_card"
    │
    ├── VideoForge creates SlideSpec
    │   {
    │     "title": "What is a Neural Network?",
    │     "content": ["Definition", "Analogy", "Key Components"],
    │     "layout": "title-content",
    │     "style": "flat-motion-graphics",
    │     "colors": {"primary": "#6366f1", "bg": "#0f172a"}
    │   }
    │
    ├── PresentonAdapter.generate_slide(slide_spec)
    │   │
    │   ├── Calls Presenton API (port 5001)
    │   ├── Presenton uses Claude to generate slide content
    │   ├── Presenton renders slide as PNG/PPTX
    │   └── Returns image bytes
    │
    └── Image fed into HyperFrames composition as scene background
```

### Presenton API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/api/v1/ppt/generate-outline` | Get slide structure for a topic | POST |
| `/api/v1/ppt/generate-slide` | Generate single slide image | POST |
| `/api/v1/ppt/generate-from-template` | Full presentation from outline | POST |
| `/api/v1/mock/generate-presentation` | Test mode without API keys | POST |

### Slide-to-Video Bridge

Presenton generates static slides. To make them video-ready:

```python
# videoforge/stages/asset_stage.py

class AssetStage:
    def presenton_slide_to_hyperframes_scene(self, slide_image: bytes, scene: Scene) -> str:
        """Convert Presenton slide to animated HyperFrames scene."""
        # Save slide image
        img_path = self.workspace / "assets" / "images" / f"{scene.id}.png"
        img_path.write_bytes(slide_image)

        # Generate HyperFrames HTML that animates the slide
        html = f"""
        <div class="scene" style="width:1920px;height:1080px">
            <img src="../assets/images/{scene.id}.png"
                 style="width:100%;height:100%;object-fit:contain"/>
            <div class="anim-overlay">
                <!-- GSAP animations for text reveals, transitions -->
            </div>
        </div>
        <script>
            // Animate elements in
            gsap.from(".anim-overlay > *", {{
                opacity: 0, y: 30, stagger: 0.2, duration: 0.8
            }});
        </script>
        """
        return html
```

---

## Part 7: Code Visualization Strategy

This is a key differentiator for educational videos.

### Code Visualization Types

```python
# videoforge/generators/code_visualizer.py

class CodeVisualizer:
    """Generates animated code visualizations for educational videos."""

    CODE_THEME = {
        "background": "#1e293b",    # Dark slate
        "line_numbers": "#64748b",
        "keyword": "#c678dd",       # Purple
        "string": "#98c379",        # Green
        "function": "#61afef",      # Blue
        "comment": "#5c6370",       # Grey
        "highlight": "#e5c07b",     # Yellow (current line)
        "cursor": "#dc2626",        # Red blinking cursor
    }

    def generate_syntax_highlighted_code(self, code: str, language: str) -> str:
        """Generate syntax-highlighted HTML for code display."""
        # Use Pygments or manual highlighting
        # Returns HTML with span-wrapped tokens
        pass

    def generate_typing_animation_spec(self, code: str, speed: float = 1.0) -> dict:
        """Generate spec for typing animation (line by line reveal)."""
        return {
            "type": "typing_animation",
            "code": code,
            "speed_wpm": int(200 * speed),
            "highlight_current_line": True,
            "show_line_numbers": True,
            "theme": self.CODE_THEME,
        }

    def generate_code_walkthrough(self, code: str, explanation: str) -> dict:
        """Generate multi-step code walkthrough with annotations."""
        lines = code.split('\n')
        annotations = self._parse_annotations(explanation, lines)
        return {
            "type": "code_walkthrough",
            "code": code,
            "annotations": annotations,  # {line_num: explanation_text}
            "auto_scroll": True,
            "highlight_lines": [a["line"] for a in annotations],
        }

    def generate_hyperframes_code_scene(self, viz_spec: dict) -> str:
        """Generate HyperFrames HTML for a code visualization scene."""
        if viz_spec["type"] == "typing_animation":
            return self._typing_template(viz_spec)
        elif viz_spec["type"] == "code_walkthrough":
            return self._walkthrough_template(viz_spec)
        ...
```

### Code Scene HTML Template

```html
<!-- videoforge/templates/code-scene.html -->
<div class="code-scene" style="width:1920px;height:1080px;background:#0f172a;font-family:'JetBrains Mono',monospace">
    <div class="code-container" style="padding:40px;width:100%;height:100%">
        <div class="line-numbers" style="color:#64748b;float:left;text-align:right;width:60px">
            <!-- Line numbers generated by JS -->
        </div>
        <pre class="code-content" style="margin-left:80px;font-size:24px;line-height:1.8">
            <!-- Code with syntax highlighting spans -->
            <code>{{CODE_HTML}}</code>
        </pre>
    </div>
    <div class="annotation-panel" style="position:absolute;right:40px;top:50%;transform:translateY(-50%);width:500px;background:rgba(30,41,59,0.95);border-radius:12px;padding:24px">
        <p class="annotation-text" style="color:#e2e8f0;font-size:20px">{{ANNOTATION}}</p>
    </div>
</div>
<script>
    // GSAP typing animation
    const codeLines = {{CODE_LINES_JSON}};
    const tl = gsap.timeline();
    codeLines.forEach((line, i) => {{
        tl.to(`.line-{{i}}`, {{ opacity: 1, duration: 0.3 }});
    }});
</script>
```

---

## Part 8: OpenMontage Integration

VideoForge **leverages** OpenMontage rather than reinventing it.

### What We Reuse from OpenMontage

| Component | How We Use It |
|-----------|---------------|
| Pipeline manifest system | Adapt our stages to use OpenMontage's YAML manifests |
| Tool registry | Use `tool_registry.py` for capability discovery |
| BaseTool pattern | Our adapters follow the same `.execute(params)` interface |
| Checkpoint system | Use `lib/checkpoint.py` for resumability |
| Stage director skills | Reference same skill pattern for our stages |
| 8-stage pipeline | We map to OpenMontage's stages |
| Backlot board | Compatible with our project workspace layout |

### What We Add/Override

| Component | What's New |
|-----------|------------|
| Chapterizer | No equivalent in OpenMontage (it's short-form focused) |
| Context Manager | Cross-chapter state management |
| Presenton Adapter | Presenton is not in OpenMontage |
| Code Visualizer | Educational-specific visual generation |
| Long-form orchestration | OpenMontage is single-pipeline; we run 5 pipelines sequentially |

### Integration Approach

```
VideoForge does NOT modify OpenMontage code.
VideoForge calls OpenMontage as a subprocess/library.

Option A: Library Import
  - Add OpenMontage to Python path
  - Import tool_registry, checkpoint, BaseTool
  - Call tools directly

Option B: Subprocess (Safer)
  - Run OpenMontage CLI commands
  - Parse JSON artifacts from projects/ directory
  - More isolation, easier debugging
```

**Recommendation: Option B (Subprocess)** for robustness. The projects/ directory is the shared contract.

---

## Part 9: Complete Data Flow

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: PLANNING (One-time, ~2-3 minutes)                 │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │   Claude    │───▶│ Chapterizer │───▶│ Chapter Plan  │   │
│  │  (Research) │    │ (Segmenter)  │    │   (5 chapters)│   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                                    │              │
│         ▼                                    ▼              │
│  ┌─────────────┐                    ┌───────────────────┐   │
│  │ GlobalVideo │                    │ Presenton creates │   │
│  │  Context    │                    │ visual style guide│   │
│  └─────────────┘                    └───────────────────┘   │
│         │                                    │              │
│         └──────────────┬─────────────────────┘              │
│                        ▼                                    │
│              ┌─────────────────┐                            │
│              │  User Approval  │                            │
│              └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: CHAPTER GENERATION (Loop, 5 chapters)             │
│                                                             │
│  For each chapter:                                          │
│                                                             │
│  ┌────────────────┐   ┌────────────────┐   ┌─────────────┐  │
│  │ Claude writes  │──▶│ Scene Plan     │──▶│ Presenton  │  │
│  │   narration    │   │ (scenes w/     │   │ generates   │  │
│  │   script       │   │  visual types) │   │ slide specs │  │
│  └────────────────┘   └────────────────┘   └─────────────┘  │
│         │                       │                    │      │
│         ▼                       ▼                    ▼      │
│  ┌────────────────┐   ┌────────────────┐   ┌─────────────┐  │
│  │ElevenLabs local│   │ Image/Diagram  │   │ Code Viz    │  │
│  │  generates     │   │   generation   │   │  generator  │  │
│  │ narration MP3  │   │  (per scene)   │   │  (HTML)     │  │
│  └────────────────┘   └────────────────┘   └─────────────┘  │
│         │                       │                    │      │
│         └───────────────────────┼────────────────────┘      │
│                                 ▼                           │
│                    ┌────────────────────┐                   │
│                    │  Scene Assets      │                   │
│                    │ (audio+visual+code)│                   │
│                    └────────────────────┘                   │
│                                 │                           │
│                                 ▼                           │
│                    ┌────────────────────┐                   │
│                    │ HyperFrames renders│                   │
│                    │  chapter video     │                   │
│                    │  (chXX.mp4)        │                   │
│                    └────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: FINAL ASSEMBLY (~5 minutes)                       │
│                                                             │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐      │
│  │FFmpeg concat│─▶│Subtitle burn│─▶│  Final MP4     │      │
│  │ all chapters│  │  (SRT file) │  │  40-50 minutes  │      │
│  └────────────┘  └─────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
  DELIVERED VIDEO
```

---

## Part 10: Technology Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| **Orchestrator** | Python 3.11+ | Fast, good async support, OpenMontage compatible |
| **Content Intelligence** | Claude API (Sonnet 5 / Haiku 5) | Best-in-class for long-form content generation |
| **Slide Design** | Presenton (FastAPI, port 5001) | AI-powered presentation generation, 14 LLM providers |
| **TTS / Audio** | Local ElevenLabs (StyleTTS2 + SeedVC, ports 8000/8001) | Free, local, high-quality voices |
| **Rendering** | HyperFrames (Node.js + Bun, HTML-to-video) | GSAP, Lottie, Three.js support; beautiful motion |
| **Post-processing** | FFmpeg | Concatenation, subtitle burn, encoding |
| **Animations** | GSAP + Lottie + CSS Animations | Via HyperFrames skills |
| **Code Viz** | Custom HTML/CSS with GSAP typing animation | Manual implementation |
| **Diagrams** | Claude-generated SVG/HTML specs | Via HyperFrames rendering |
| **State Management** | JSON checkpoints + file system | Resumability, no DB needed |
| **Container** | Docker Compose | All services in one command |

---

## Part 11: Docker Compose (Unified Services)

```yaml
# docker-compose.yml

version: '3.8'

services:
  # ===== VideoForge Core =====
  videoforge:
    build: ./videoforge
    volumes:
      - ./projects:/app/projects
      - ./compose:/app/compose
      - ./skills:/app/skills
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - PRESENTON_URL=http://presenton:5001
      - ELEVENLABS_STYLETTS_URL=http://elevenlabs-stylitts:8000
      - ELEVENLABS_SEEDVC_URL=http://elevenlabs-seedvc:8001
    depends_on:
      - presenton
      - elevenlabs-stylitts
      - elevenlabs-seedvc
    command: python -m videoforge.main

  # ===== Presenton (Presentation Generator) =====
  presenton:
    build: ./presenton/servers/fastapi
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://presenton:presenton@postgres:5432/presenton
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    volumes:
      - ./presenton/data:/app/app_data
    depends_on:
      - postgres
    command: uvicorn api.main:app --host 0.0.0.0 --port 5001

  # ===== ElevenLabs Services =====
  elevenlabs-stylitts:
    build: ./ElevenLabs
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  elevenlabs-seedvc:
    build: ./ElevenLabs
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: python -m seedvc_server --port 8001

  # ===== PostgreSQL (Presenton DB) =====
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=presenton
      - POSTGRES_PASSWORD=presenton
      - POSTGRES_DB=presenton
    volumes:
      - ./presenton/pgdata:/var/lib/postgresql/data

  # ===== HyperFrames CLI (via npx, no container needed) =====
  # HyperFrames runs on host Node.js (>= 22)

volumes:
  pgdata:
  presenton_data:
  videoforge_projects:
```

---

## Part 12: Implementation Phases (TDD Approach)

### Phase 1: Foundation (Week 1-2)
**Goal**: Core infrastructure working

```
□ Set up project structure (videoforge/ directory)
□ Implement config.py (environment loading)
□ Implement models/ (dataclasses for all data structures)
□ Implement checkpoint.py (save/load/resume)
□ Implement Claude adapter with basic API calls
□ Write unit tests for models and checkpoint
□ Docker compose with Postgres + Presenton + ElevenLabs
□ Verify all services start and health-check passes
```

### Phase 2: Content Generation (Week 3-4)
**Goal**: Claude can generate scripts and chapter plans

```
□ Implement chapterizer (segmenter + context_manager)
□ Implement content researcher (Claude research prompts)
□ Implement script writer (Claude script prompts)
□ Implement visual designer (scene type classification)
□ Write integration tests for content generation
□ Test end-to-end: user prompt → chapter plan → script
□ Validate script timing and quality
```

### Phase 3: Asset Pipeline (Week 5-6)
**Goal**: All asset types can be generated

```
□ Implement ElevenLabs adapter (TTS generation)
□ Implement Presenton adapter (slide generation)
□ Implement code visualizer (syntax highlighting + animation specs)
□ Implement diagram spec generator
□ Implement asset_stage.py (orchestrate parallel asset gen)
□ Write tests for each adapter
□ Test: script → all assets generated per scene
□ Validate audio timing matches script
```

### Phase 4: Rendering (Week 7-8)
**Goal**: Video can be composed and rendered

```
□ Implement HyperFrames adapter (init, render_scene, render_composition)
□ Create base HTML templates (base-layout, text-scene, code-scene, diagram-scene)
□ Implement chapter composition builder (assembles scenes into chapter)
□ Implement FFmpeg adapter (concat, subtitle burn)
□ Implement compose_stage.py (chapter-by-chapter rendering + final assembly)
□ Write tests for rendering pipeline
□ Test: assets → single chapter video
□ Test: 5 chapters → concatenated final video
```

### Phase 5: Polish & Integration (Week 9-10)
**Goal**: Production-ready end-to-end

```
□ Implement CLI (main.py with argparse/click)
□ Add progress tracking and logging
□ Add cost tracking
□ Add error handling and retry logic
□ Implement resumability (checkpoint-based)
□ Add quality validation (audio sync, scene transitions)
□ Create Docker setup (docker-compose + Dockerfiles)
□ Write documentation
□ End-to-end integration test: topic → final video
□ Performance optimization (parallel asset generation)
```

---

## Part 13: Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestrator language** | Python | OpenMontage is Python; reuse tool registry, checkpoint system |
| **Content generation** | Claude API (Sonnet 5) | Best quality for long-form content; Haiku for fast/repeat tasks |
| **TTS** | Local ElevenLabs | Free, no per-request cost, high quality |
| **Rendering** | HyperFrames (primary), FFmpeg (fallback) | HTML-based = infinite visual flexibility; FFmpeg for stitching |
| **Slide design** | Presenton | Already built, AI-powered, multi-provider |
| **Project workspace** | File-system (projects/ dir) | Simple, debuggable, compatible with OpenMontage |
| **Resumability** | JSON checkpoints | Human-readable, easy to debug, no DB migration |
| **Long-form strategy** | Chapter-based | Solves context window, consistency, cost, and resumability |
| **Visual style** | User-selectable playbooks | Same as OpenMontage (clean-professional, flat-motion, etc.) |

---

## Part 14: What Gets Reused vs What's New

### Reused (As-Is)
- OpenMontage's entire pipeline engine, tool registry, checkpoint system
- Presenton's FastAPI backend (slides + LLM routing)
- ElevenLabs local services (StyleTTS2, SeedVC, Make-An-Audio)
- HyperFrames CLI and rendering engine
- All skills from `skills/` folder (gsap, animejs, lottie, three.js, etc.)

### Adapted (Modified for VideoForge)
- OpenMontage stage directors → VideoForge stage directors (chapter-aware)
- OpenMontage pipeline manifests → VideoForge pipeline manifests (long-form)
- Presenton slide generation → VideoForge scene asset generation (automated, not interactive)

### New (Built From Scratch)
- `videoforge/` directory (orchestrator, adapters, generators, chapterizer)
- Chapter-based long-form architecture
- Context manager for cross-chapter state
- Code visualization system
- Presenton-to-HyperFrames bridge
- Long-form CLI interface
- Docker compose for unified deployment

---

## Part 15: CLI Usage Example

```bash
# Generate a 45-minute video
$ python -m videoforge.main \
    --topic "Machine Learning" \
    --subtopic "Neural Networks Deep Dive" \
    --explanation "I want to explain how neural networks work from basic perceptrons to deep learning, with Python code examples" \
    --duration 45 \
    --audience "intermediate" \
    --style "flat-motion-graphics" \
    --voice "rachel"

# Or interactive mode
$ python -m videoforge.main
VideoForge> Enter topic: Machine Learning
VideoForge> Enter subtopic: Neural Networks
VideoForge> Describe what you want (5-10 lines): ...
VideoForge> Target duration (minutes) [45]: 45
VideoForge> Target audience [intermediate]: intermediate
VideoForge> Visual style [flat-motion-graphics]: flat-motion-graphics

# Resume a failed generation
$ python -m videoforge.main --resume projects/neural-networks-deep-dive

# Preview a single chapter
$ python -m videoforge.main --preview-chapter 3 --project projects/neural-networks-deep-dive
```

---

## Part 16: Cost Estimation

For a 45-minute video (~5 chapters × 9 scenes = 45 scenes):

| Resource | Unit Cost | Quantity | Total |
|----------|-----------|----------|-------|
| Claude Sonnet (planning) | $3/1M input, $15/1M output | ~200K input, ~50K output | ~$1.50 |
| Claude Haiku (asset specs) | $0.80/1M input, $4/1M output | ~100K input, ~30K output | ~$0.20 |
| Claude Sonnet (scripts) | $3/1M input, $15/1M output | ~500K input, ~200K output | ~$4.50 |
| ElevenLabs (local, free) | $0 | ~45 min audio | $0 |
| HyperFrames (local, free) | $0 | 45 min render | $0 |
| Image generation (if any) | Varies | ~10 images | ~$0.50 |
| **TOTAL** | | | **~$7-10 per 45-min video** |

---

## Summary

This plan creates **VideoForge** — a unified video generation system that:

1. **Leverages all three existing projects** (OpenMontage, Presenton, ElevenLabs) without modifying them
2. **Solves the 40-50 minute challenge** through a chapter-based architecture with cross-chapter context management
3. **Uses Claude API as the intelligence layer** for content research, script writing, visual design, and code visualization
4. **Integrates Presenton** for AI-powered slide/layout generation
5. **Uses local ElevenLabs** for free, high-quality TTS narration
6. **Renders via HyperFrames** with GSAP animations, Lottie, code typing effects, and more
7. **Produces professional-quality videos** with visual explanations, animated code, diagrams, and consistent styling
8. **Is fully resumable** with checkpoint-based state management
9. **Costs ~$7-10 per 45-minute video** (mostly Claude API calls; TTS and rendering are free/local)
10. **Deploys via Docker Compose** — one command to start all services

The implementation follows a phased approach over 10 weeks, with each phase independently testable via TDD.
