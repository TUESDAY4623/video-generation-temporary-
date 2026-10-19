"""Stage 4: Break script into chapters with timing and scene breakdowns."""

from __future__ import annotations

import json
import logging
import re
import time

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ChapterizeStage(Stage):
    """Split the script into timed chapters with scene breakdowns."""

    SYSTEM_PROMPT = """You are a video production editor. Break scripts into chapters
and scenes with precise timing. Output valid JSON only. No markdown fences."""

    SCHEMA_HINT = """[
  {
    "chapter_number": 1,
    "title": "string",
    "summary": "string",
    "duration_seconds": 300,
    "word_count": 450,
    "key_points": ["string"],
    "scenes": [
      {
        "scene_id": "1.1",
        "scene_type": "hero_title|text_card|stat_card|callout|comparison|bar_chart|line_chart|pie_chart|kpi_grid|progress_bar|anime_scene|talking_head|code_viz|diagram",
        "title": "string",
        "script_text": "narration text",
        "duration_seconds": 30,
        "visual_params": {}
      }
    ]
  }
]"""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        self.report_progress(5, "Building chapterization prompt...")

        user_prompt = f"""Break this script into chapters and scenes:

SCRIPT:
{(context.script_text or "")[:12000]}

TARGET DURATION: {context.target_duration_minutes} minutes
TOTAL WORDS: {context.word_count or 0}
TOPIC: {context.topic}

Rules:
- Each scene: 10-60 seconds
- Total durations must sum to ~{context.target_duration_minutes * 60} seconds
- Use diverse scene types: hero_title, text_card, stat_card, callout, comparison, bar_chart, line_chart, pie_chart, kpi_grid, progress_bar, anime_scene, talking_head, code_viz, diagram
- For code examples: use code_viz
- For comparisons: use comparison
- For statistics: use stat_card or bar_chart
- For processes: use progress_bar
- For architecture: use diagram
- Open with hero_title, close with callout or text_card
- Output ONLY valid JSON array matching this schema:
{self.SCHEMA_HINT}"""

        self.report_progress(25, "Generating chapter breakdown...")

        try:
            raw = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=32768,
                temperature=0.3,
            )
        except Exception as e:
            raise StageError(f"Chapterization failed: {e}") from e

        self.report_progress(60, "Parsing chapters...")

        chapters = self._parse_chapters(raw)

        if not chapters:
            chapters = [self._build_fallback_chapter(context)]

        context.chapters = chapters

        total_scenes = sum(len(c.get("scenes", [])) for c in context.chapters)
        context.metadata["chapterization_duration_seconds"] = time.time() - start

        self.report_progress(100, f"Complete: {len(chapters)} chapters, {total_scenes} scenes")
        logger.info("Chapters: %d, scenes: %d in %.1fs", len(chapters), total_scenes, time.time() - start)
        return context

    @staticmethod
    def _parse_chapters(raw: str) -> list[dict]:
        """Parse chapter JSON from Claude response."""
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

    def _build_fallback_chapter(self, context: PipelineContext) -> dict:
        duration = int(getattr(context, 'estimated_duration_seconds', 300))
        word_count = int(getattr(context, 'word_count', 0))
        script_text = getattr(context, 'script_text', "") or ""
        topic = getattr(context, 'topic', "Video Content")
        return {
            "chapter_number": 1,
            "title": topic,
            "summary": "Complete video content",
            "duration_seconds": duration,
            "word_count": word_count,
            "key_points": [],
            "scenes": [{
                "scene_id": "1.1",
                "scene_type": "text_card",
                "title": topic,
                "script_text": script_text,
                "duration_seconds": duration,
                "visual_params": {},
            }],
        }
