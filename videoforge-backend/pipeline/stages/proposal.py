"""Stage 2: Create a video proposal with chapter outline and visual strategy."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ProposalStage(Stage):
    """Create a video proposal with chapter outline, visual recommendations,
    and audience-appropriate pacing."""

    SYSTEM_PROMPT = """You are a video content strategist and educational designer.
Create detailed video proposals that maximize engagement and learning retention.
Output valid JSON matching the requested schema. No markdown fences, no prose."""

    SCHEMA_HINT = """{
  "title": "string",
  "hook": "string",
  "summary": "string",
  "learning_objectives": ["string"],
  "chapters": [{"number": 1, "title": "string", "duration_minutes": 5, "key_points": ["string"], "scene_types": ["text_card"], "description": "string"}],
  "visual_recommendations": {"color_palette": {"primary": "#hex", "accent": "#hex"}, "transition_style": "fade", "text_density": "medium"},
  "total_word_count": 5000,
  "estimated_duration_minutes": 45
}"""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        adapter = AnthropicAdapter()
        start = time.time()

        self.report_progress(5, "Building proposal prompt...")

        user_prompt = self._build_proposal_prompt(context)

        self.report_progress(25, "Generating proposal with Claude...")

        try:
            raw = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=8192,
                temperature=0.2,
            )
        except Exception as e:
            raise StageError(f"Proposal generation failed: {e}") from e

        self.report_progress(70, "Parsing proposal JSON...")

        proposal = self._parse_json(raw)
        if not proposal:
            proposal = self._build_fallback_proposal(context)

        context.proposal = proposal
        context.metadata["proposal_duration_seconds"] = time.time() - start

        chapters = proposal.get("chapters", [])
        self.report_progress(100, f"Proposal complete: {len(chapters)} chapters")
        logger.info("Proposal: %d chapters in %.1fs", len(chapters), time.time() - start)
        return context

    def _build_proposal_prompt(self, context: PipelineContext) -> str:
        research_snippet = (context.research_notes or "")[:6000]
        return f"""Create a video proposal for:

TOPIC: {context.topic}
SUB-TOPIC: {context.subtopic or 'General overview'}
TARGET DURATION: {context.target_duration_minutes} minutes
TARGET AUDIENCE: {context.target_audience.value}
VISUAL STYLE: {context.visual_style.value}
PACING: {context.pacing.value}

RESEARCH FINDINGS:
{research_snippet}

USER CONTEXT: {context.user_explanation or 'None provided'}

Rules:
- Chapters must sum to ~{context.target_duration_minutes} minutes
- Each chapter: 3-8 minutes
- For code topics: include code_viz scenes
- For data topics: include chart scenes
- Alternate visual types for engagement
- Output ONLY valid JSON matching this schema:
{self.SCHEMA_HINT}"""

    @staticmethod
    def _parse_json(raw: str) -> Optional[dict[str, Any]]:
        """Extract JSON object from Claude response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass
        return None

    def _build_fallback_proposal(self, context: PipelineContext) -> dict[str, Any]:
        """Create a basic proposal when JSON parsing fails."""
        return {
            "title": context.topic,
            "hook": f"An introduction to {context.topic}",
            "summary": (context.research_notes or "")[:500],
            "learning_objectives": [],
            "chapters": [],
            "visual_recommendations": {},
            "total_word_count": 0,
            "estimated_duration_minutes": context.target_duration_minutes,
        }
