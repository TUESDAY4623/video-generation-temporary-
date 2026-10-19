"""Stage 5: Design detailed scene breakdown for each chapter."""

from __future__ import annotations

import json
import logging
import re
import time

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ScenePlanStage(Stage):
    """Enrich scenes with visual specifications, transitions, and asset requirements."""

    SYSTEM_PROMPT = """You are a video director and visual designer.
For each scene, specify exactly how it should look, animate, and transition.
Output valid JSON only. No markdown fences."""

    SCHEMA_HINT = """[
  {
    "scene_id": "1.1",
    "scene_type": "text_card",
    "title": "string",
    "script_text": "narration text",
    "duration_seconds": 30,
    "animation": "fade_in|slide_in|zoom_in|typewriter|none",
    "transition_in": "fade|slide|wipe|none",
    "transition_out": "fade|slide|wipe|none",
    "visual_elements": ["string"],
    "color_scheme": {"primary": "#hex", "accent": "#hex"},
    "font": "string",
    "layout": "centered|split|full_width",
    "music_cue": "none|upbeat|dramatic|calm",
    "sfx_cue": "none|click|whoosh|chime"
  }
]"""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        self.report_progress(5, "Building scene plan prompt...")

        # Build scene list from existing chapters
        scenes_input = []
        for chapter in (context.chapters or []):
            for scene in chapter.get("scenes", []):
                scenes_input.append({
                    "scene_id": scene.get("scene_id"),
                    "scene_type": scene.get("scene_type"),
                    "title": scene.get("title"),
                    "script_text": (scene.get("script_text") or "")[:200],
                    "duration_seconds": scene.get("duration_seconds", 30),
                })

        if not scenes_input:
            self.report_progress(100, "No scenes to plan")
            return context

        user_prompt = f"""Create a detailed scene plan for these scenes:

SCENES:
{json.dumps(scenes_input[:100], indent=2, default=str)}

VISUAL STYLE: {context.visual_style.value}
TOPIC: {context.topic}

For each scene, specify animation, transitions, visual elements, color scheme, layout, music/SFX cues.
Return a JSON array matching this schema:
{self.SCHEMA_HINT}"""

        self.report_progress(25, "Generating scene plan...")

        try:
            raw = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=32768,
                temperature=0.3,
            )
        except Exception as e:
            raise StageError(f"Scene planning failed: {e}") from e

        self.report_progress(60, "Merging scene plan...")

        enriched = self._parse_scene_plan(raw)
        if enriched:
            enriched_map = {s["scene_id"]: s for s in enriched}
            for chapter in context.chapters or []:
                for scene in chapter.get("scenes", []):
                    if scene.get("scene_id") in enriched_map:
                        scene.update(enriched_map[scene["scene_id"]])

        context.metadata["scene_plan_duration_seconds"] = time.time() - start
        self.report_progress(100, f"Scene plan complete: {len(context.scenes)} scenes")
        logger.info("Scene plan: %d scenes in %.1fs", len(context.scenes), time.time() - start)
        return context

    @staticmethod
    def _parse_scene_plan(raw: str) -> list[dict]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        match = re.search(r"\[[\s\S]*\]", cleaned)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return []
