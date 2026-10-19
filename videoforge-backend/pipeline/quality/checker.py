"""Quality checkers for pipeline stages."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Result of a quality check."""
    score: float = 1.0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_passing: bool = True


class QualityChecker:
    """Validates the quality of pipeline stage outputs."""

    def check_research(self, text: str) -> QualityResult:
        """Check research quality."""
        result = QualityResult()

        if not text or len(text) < 500:
            result.issues.append("Research text too short")
            result.score -= 0.3

        if len(text) < 2000:
            result.warnings.append("Research could be more detailed")

        word_count = len(text.split())
        if word_count < 300:
            result.issues.append(f"Very low word count: {word_count}")
            result.score -= 0.2

        result.is_passing = result.score >= 0.7 and len(result.issues) == 0
        return result

    def check_script(self, text: str, target_duration_min: int) -> QualityResult:
        """Check script quality."""
        result = QualityResult()

        if not text:
            result.issues.append("Empty script")
            result.score = 0.0
            return result

        word_count = len(text.split())
        target_words = target_duration_min * context_wpm
        ratio = word_count / target_words if target_words > 0 else 1

        if ratio < 0.5:
            result.issues.append(f"Script too short: {word_count} words (target: ~{target_words})")
            result.score -= 0.3
        elif ratio > 2.0:
            result.warnings.append(f"Script very long: {word_count} words (target: ~{target_words})")

        # Check for visual markers
        visual_markers = len(re.findall(r'\[VISUAL:', text))
        if visual_markers == 0:
            result.warnings.append("No [VISUAL:] markers found")

        # Check average sentence length
        sentences = re.split(r'[.!?]+', text)
        avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if avg_len > 25:
            result.warnings.append(f"Average sentence length ({avg_len:.0f} words) may be too long for narration")

        result.is_passing = result.score >= 0.7 and len(result.issues) == 0
        return result

    def check_chapter(self, chapter: dict) -> QualityResult:
        """Check a chapter's quality."""
        result = QualityResult()

        scenes = chapter.get("scenes", [])
        if not scenes:
            result.issues.append("Chapter has no scenes")
            result.score -= 0.5

        total_duration = sum(s.get("duration_seconds", 0) for s in scenes)
        if total_duration < 60:
            result.warnings.append(f"Chapter very short: {total_duration}s")

        # Check scene type variety
        types = set(s.get("scene_type", "") for s in scenes)
        if len(types) < 2 and len(scenes) > 3:
            result.warnings.append("Low scene type variety")

        result.is_passing = result.score >= 0.7 and len(result.issues) == 0
        return result

    def check_scene(self, scene: dict) -> QualityResult:
        """Check a single scene's quality."""
        result = QualityResult()

        duration = scene.get("duration_seconds", 0)
        if duration < 5:
            result.warnings.append(f"Scene very short: {duration}s")
        elif duration > 120:
            result.warnings.append(f"Scene very long: {duration}s")

        if not scene.get("script_text") and not scene.get("text"):
            result.warnings.append("Scene has no text content")

        if not scene.get("scene_type"):
            result.issues.append("Scene has no type")
            result.score -= 0.2

        result.is_passing = result.score >= 0.7 and len(result.issues) == 0
        return result


# Module-level WPM constant (avoids circular imports)
context_wpm = 150  # Default, will be overridden by context


def set_wpm(wpm: int) -> None:
    """Set the WPM for script quality checks."""
    global context_wpm
    context_wpm = wpm
