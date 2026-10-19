"""Stage 7: Assemble scenes with transitions and effects."""

from __future__ import annotations

import json
import logging
import re
import time

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.ffmpeg_adapter import FFmpegAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class EditStage(Stage):
    """Create the edit plan with transitions, effects, and timing."""

    SYSTEM_PROMPT = """You are a video editor. Create edit plans with transitions,
timing, and effects. Output valid JSON only. No markdown fences."""

    SCHEMA_HINT = """{
  "total_duration_seconds": 2700,
  "chapters": [{
    "chapter_number": 1,
    "scenes": [{
      "scene_id": "1.1",
      "order": 1,
      "start_time": 0,
      "duration_seconds": 30,
      "transition_in": "fade",
      "transition_out": "fade",
      "effect": "none|ken_burns|zoom|pan",
      "audio": "narration|music|both|none",
      "volume_narration": 1.0,
      "volume_music": 0.15
    }]
  }],
  "global_settings": {
    "background_music_volume": 0.1,
    "fade_in_duration": 1.0,
    "fade_out_duration": 2.0,
    "intro_duration": 5,
    "outro_duration": 10
  }
}"""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        scenes = context.scenes or []
        chapters = context.chapters or []

        self.report_progress(5, "Building edit plan prompt...")

        # Build scene timeline
        scene_list = []
        current_time = 0
        for chapter in chapters:
            for scene in chapter.get("scenes", []):
                duration = scene.get("duration_seconds", 30)
                scene_list.append({
                    "scene_id": scene.get("scene_id"),
                    "chapter": chapter.get("chapter_number"),
                    "title": scene.get("title", "Untitled"),
                    "scene_type": scene.get("scene_type", "text_card"),
                    "start_time": current_time,
                    "duration_seconds": duration,
                })
                current_time += duration

        user_prompt = f"""Create an edit plan for this video:

TOPIC: {context.topic}
VISUAL STYLE: {context.visual_style.value}
TOTAL DURATION: ~{context.target_duration_minutes} minutes
TOTAL SCENES: {len(scene_list)}

SCENE TIMELINE:
{json.dumps(scene_list[:100], indent=2)}

Rules:
- Start each scene with a 0.5s fade-in
- End each scene with a 0.3s fade-out
- Use "ken_burns" effect for text_card scenes
- Use "none" effect for code_viz and chart scenes
- Narration volume: 1.0, music volume: 0.1-0.15
- Add 5s intro, 10s outro
- Total duration must match scene sum

Output valid JSON matching:
{self.SCHEMA_HINT}"""

        self.report_progress(25, "Generating edit plan...")

        try:
            raw = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=16384,
                temperature=0.2,
            )
        except Exception as e:
            raise StageError(f"Edit plan generation failed: {e}") from e

        self.report_progress(60, "Parsing edit plan...")

        edit_plan = self._parse_edit_plan(raw)
        context.metadata["edit_plan"] = edit_plan or {}

        # Apply transitions to scenes
        for scene in scenes:
            scene.setdefault("transition_in", "fade")
            scene.setdefault("transition_out", "fade")
            scene.setdefault("effect", "none")

        context.metadata["edit_plan_duration_seconds"] = time.time() - start
        self.report_progress(100, f"Edit plan complete: {len(scenes)} scenes")
        logger.info("Edit plan: %d scenes in %.1fs", len(scenes), time.time() - start)
        return context

    @staticmethod
    def _parse_edit_plan(raw: str) -> dict | None:
        """Parse edit plan JSON from Claude response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        return None
