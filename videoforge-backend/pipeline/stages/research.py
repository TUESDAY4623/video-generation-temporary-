"""Stage 1: Research the topic and gather comprehensive information."""

from __future__ import annotations

import logging
import time

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ResearchStage(Stage):
    """Research the video topic using Claude API with web search."""

    SYSTEM_PROMPT = """You are an expert researcher specializing in educational content creation.
Your research will be used to create a professional 40-50 minute video. Be thorough, accurate,
and focus on facts that can be visually demonstrated. Prioritize:
- Concrete examples and case studies
- Statistical data and metrics
- Step-by-step processes
- Common misconceptions to address
- Practical applications"""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        self.report_progress(5, "Starting topic research...")

        user_prompt = self._build_research_prompt(context)

        self.report_progress(20, "Querying Claude for research...")

        try:
            response = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=32768,
                temperature=0.3,
            )
        except Exception as e:
            raise StageError(f"Research generation failed: {e}") from e

        context.research_notes = self._clean_response(response)
        context.word_count = len(context.research_notes.split())
        context.metadata["research_duration_seconds"] = time.time() - start

        self.report_progress(100, f"Research complete: {context.word_count} words")
        logger.info("Research: %d words in %.1fs", context.word_count, time.time() - start)
        return context

    def _build_research_prompt(self, context: PipelineContext) -> str:
        lines = [
            f"Research this video topic comprehensively:",
            f"",
            f"TOPIC: {context.topic}",
            f"SUB-TOPIC: {context.subtopic or 'General overview'}",
            f"TARGET DURATION: {context.target_duration_minutes} minutes",
            f"TARGET AUDIENCE: {context.target_audience.value}",
            f"",
            f"USER NOTES: {context.user_explanation or 'None provided'}",
            f"",
            f"Provide a comprehensive research report covering:",
            f"1. Key concepts, definitions, and terminology",
            f"2. Historical background and evolution",
            f"3. Current state-of-the-art and real-world applications",
            f"4. Technical details (if applicable)",
            f"5. Step-by-step processes with examples",
            f"6. Statistical data and metrics",
            f"7. Common misconceptions and pitfalls",
            f"8. Future trends and predictions",
            f"9. Key figures, companies, or tools in this space",
            f"10. Practical takeaways for the audience",
            f"",
            f"Write in a clear, informative style suitable for an educational video.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _clean_response(text: str) -> str:
        """Remove markdown fences and clean up response."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()
