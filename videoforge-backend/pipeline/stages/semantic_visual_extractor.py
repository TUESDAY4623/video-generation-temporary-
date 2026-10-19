"""Semantic Visual Extractor Stage for VideoForge.

Purpose:
--------
Deeply analyzes narration script sentences using LLM intelligence and generates
precise visual blueprints:
- Mermaid.js Flowcharts, Architecture & Sequence specs.
- Multi-step Process flows.
- Side-by-side Technology / Concept Comparison grids.
- Code walkthrough definitions with targeted line highlights.
- Visual metaphor concept cards.

File Role:
----------
Semantic Scene Intelligence & Visual Blueprint Generator (Pipeline Stage)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.adapters.anthropic_adapter import AnthropicAdapter
from pipeline.models.entities import PipelineContext, SceneType
from pipeline.stages.base import Stage, StageError
from renderers.diagram_renderer import DiagramRenderer, VisualSceneSpec

logger = logging.getLogger(__name__)


class SemanticVisualExtractorStage(Stage):
    """Analyzes script narration and outputs rich, context-aware visual specifications."""

    SYSTEM_PROMPT = """You are an elite Motion Graphics Director and Visual Information Architect.
Your job is to read narration script segments and translate them into clear, engaging visual diagrams, code walkthroughs, comparisons, and process flows.

For each scene, choose the BEST visual representation:
1. "diagram": If the narration explains an architecture, system flow, client-server, pipeline, or relationships. Provide valid Mermaid.js graph/flowchart syntax (e.g., 'graph LR\n  A[Client] -->|Request| B[Server] --> C[(Database)]').
2. "process_flow": If explaining sequential steps, algorithms, or phases. Provide step list with title, desc, icon.
3. "comparison": If comparing two concepts/tools (e.g. REST vs GraphQL, SQL vs NoSQL). Provide comparison cards.
4. "code_walkthrough": If discussing code or implementation. Provide code snippet and lines to highlight.
5. "concept_card": If presenting key takeaways, definitions, or core principles. Provide key bullet points.

Return valid JSON array matching the schema:
[
  {
    "scene_id": "1.1",
    "visual_type": "diagram|process_flow|comparison|code_walkthrough|concept_card",
    "title": "Clear concise header",
    "subtitle": "Short explanatory subtitle",
    "accent_color": "#7c83ff",
    "diagram_code": "graph LR\\n  A[Client] --> B[Server]",
    "steps": [{"title": "Step 1", "desc": "Explanation", "icon": "cpu"}],
    "comparison_items": [{"title": "Item A", "subtitle": "Details", "points": ["Fast", "Simple"], "highlight": true}],
    "code_snippet": "def example():\\n    return True",
    "code_language": "python",
    "highlight_lines": [1, 2],
    "key_points": ["First point", "Second point"]
  }
]
Output JSON only. No markdown fences."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute semantic visual extraction across all chapters and scenes."""
        self.report_progress(5, "Preparing script segments for visual extraction...")
        start_time = time.time()

        adapter = AnthropicAdapter()
        scenes_to_process = []

        # Gather scenes from context
        for chapter in (context.chapters or []):
            for scene in chapter.get("scenes", []):
                script_text = scene.get("script_text") or scene.get("title") or ""
                if script_text:
                    scenes_to_process.append({
                        "scene_id": scene.get("scene_id", f"scene_{len(scenes_to_process)+1}"),
                        "title": scene.get("title", "Scene"),
                        "script_text": script_text,
                        "duration_seconds": scene.get("duration_seconds", 15),
                    })

        if not scenes_to_process:
            self.report_progress(100, "No scenes found to extract visuals.")
            return context

        self.report_progress(25, f"Generating visual specifications for {len(scenes_to_process)} scenes...")

        user_prompt = f"""Extract high-quality visual specifications for these scenes based on their narration:

TOPIC: {context.topic}
TARGET AUDIENCE: {getattr(context, 'audience', 'general')}

SCENES:
{json.dumps(scenes_to_process, indent=2, default=str)}

Generate the JSON visual specs for all scenes."""

        try:
            raw_response = await adapter.generate_with_system_prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=32768,
                temperature=0.2,
            )
        except Exception as e:
            logger.warning("LLM visual extraction failed (%s). Generating heuristic specs.", e)
            raw_response = self._generate_fallback_specs(scenes_to_process)

        self.report_progress(65, "Parsing visual blueprints and creating specs...")
        visual_specs = self._parse_visual_specs(raw_response)

        # Merge visual specs back into context scenes
        specs_map = {spec.get("scene_id"): spec for spec in visual_specs}
        enriched_count = 0

        for chapter in (context.chapters or []):
            for scene in chapter.get("scenes", []):
                sid = scene.get("scene_id")
                if sid in specs_map:
                    vspec = specs_map[sid]
                    scene["visual_spec"] = vspec
                    scene["visual_type"] = vspec.get("visual_type", "concept_card")
                    enriched_count += 1

        context.metadata["semantic_visual_duration"] = time.time() - start_time
        self.report_progress(100, f"Successfully created visual blueprints for {enriched_count} scenes.")
        return context

    def _parse_visual_specs(self, raw_text: str | list) -> List[Dict[str, Any]]:
        """Safely parse JSON response from LLM."""
        if isinstance(raw_text, list):
            return raw_text

        text = raw_text.strip()
        # Remove potential markdown fences
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "scenes" in data:
                return data["scenes"]
            return []
        except Exception as e:
            logger.error("Failed to parse visual specs JSON: %s", e)
            return []

    def _generate_fallback_specs(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate reliable fallback visual specs if LLM call is unavailable."""
        specs = []
        for s in scenes:
            specs.append({
                "scene_id": s["scene_id"],
                "visual_type": "concept_card",
                "title": s["title"],
                "subtitle": "Overview & Concepts",
                "accent_color": "#7c83ff",
                "key_points": [
                    s["script_text"][:80] + "...",
                    "Key concepts and architecture details.",
                    "Core workflow walkthrough."
                ]
            })
        return specs
