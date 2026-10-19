"""Stage 3: Write the full narration script with timing and visual cues."""

from __future__ import annotations

import json
import logging
import time

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ScriptStage(Stage):
    """Generate the full narration script with word timing and visual cues."""

    SYSTEM_PROMPT = """You are a professional video scriptwriter specializing in educational content.
Write narration that is:
- Conversational and engaging
- Short sentences (15-20 words max)
- Clear enunciation for TTS
- Natural pauses between ideas
- [VISUAL: ...] markers for visual elements

Avoid complex words when simple ones work. Never use "..." as a pause indicator."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        target_words = context.get_words_for_duration(context.target_duration_minutes)
        proposal = context.proposal or {}
        chapters = proposal.get("chapters", [])

        self.report_progress(5, "Building script prompt...")

        user_prompt = f"""Write a complete narration script for a {context.target_duration_minutes}-minute video.

TOPIC: {context.topic}
SUB-TOPIC: {context.subtopic or 'General overview'}
AUDIENCE: {context.target_audience.value}
TARGET WORD COUNT: ~{target_words} words (~{context.words_per_minute} WPM)

CHAPTER STRUCTURE:
{json.dumps(chapters, indent=2, default=str) if chapters else "Write a natural flowing script"}

RESEARCH CONTEXT:
{(context.research_notes or "")[:4000]}

USER NOTES: {context.user_explanation or 'None'}

Write a complete narration script that:
1. Opens with a compelling hook (30 seconds)
2. Covers each chapter with smooth transitions
3. Uses short, clear sentences for TTS narration
4. Includes [VISUAL: description] markers every 30-60 seconds
5. Has natural paragraph breaks for pauses
6. Ends with a clear summary

Format as plain text paragraphs. No markdown headers."""

        self.report_progress(25, "Generating script with Claude...")

        try:
            response = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=32768,
                temperature=0.7,
            )
        except Exception as e:
            raise StageError(f"Script generation failed: {e}") from e

        context.script_text = self._clean_response(response)
        context.word_count = len(context.script_text.split())
        context.estimated_duration_seconds = context.get_duration_for_words(context.word_count)
        context.metadata["script_duration_seconds"] = time.time() - start

        self.report_progress(100, f"Script complete: {context.word_count} words")
        logger.info("Script: %d words (~%.0fs) in %.1fs", context.word_count, context.estimated_duration_seconds, time.time() - start)
        return context

    @staticmethod
    def _clean_response(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()
