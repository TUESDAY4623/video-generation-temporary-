"""Stage 6: Generate all visual and audio assets."""

from __future__ import annotations

import logging
from pathlib import Path

from app.services import audio_service
from app.services.audio import AudioRequest
from app.config import get_settings
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError
from pipeline.templates.registry import TemplateRegistry, build_inline_template

logger = logging.getLogger(__name__)


class AssetsStage(Stage):
    """Generate all visual (HTML scenes) and audio assets for the video."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        settings = get_settings()
        full_assets_dir = Path(settings.assets_dir) / str(self.stage_run.project_id)
        full_assets_dir.mkdir(parents=True, exist_ok=True)
        context.metadata["assets_dir"] = str(full_assets_dir)

        self.report_progress(5, "Initializing asset generators...")

        template_registry = TemplateRegistry(
            Path(settings.assets_dir) / "templates"
        )

        # Gather scenes from all chapters
        all_scenes: list[dict] = []
        for chapter in context.chapters:
            all_scenes.extend(chapter.get("scenes", []))
        context.scenes = all_scenes

        total = len(all_scenes)
        if total == 0:
            raise StageError("No scenes to generate assets for")

        self.report_progress(10, f"Processing {total} scenes...")

        narration_requests: list[tuple[str, str]] = []

        for i, scene in enumerate(all_scenes):
            scene_num = i + 1
            scene_id = scene.get("scene_id", f"{i+1}")
            script_text = scene.get("script_text", "")
            scene_type = scene.get("scene_type", "text_card")

            progress = 10 + int((scene_num / total) * 70)
            self.report_progress(progress, f"Processing scene {scene_num}/{total}: {scene.get('title', '')[:50]}")

            template_context = self._build_template_context(scene, context)
            html_content = template_registry.render_template(
                f"scenes/{scene_type}.html", template_context
            ) if template_registry.get_template(f"scenes/{scene_type}.html") else \
                build_inline_template(scene_type, template_context)

            html_path = full_assets_dir / f"scene_{scene_id}.html"
            html_path.write_text(html_content, encoding="utf-8")
            scene["html_path"] = str(html_path)

            if script_text and scene_type not in ("hero_title",):
                narration_requests.append((scene_id, script_text))

        self.report_progress(80, "Generating audio narrations...")

        # Batch-generate narrations through the audio service
        audio_results = await audio_service.generate_batch([
            AudioRequest(text=text, output_path=full_assets_dir / f"narration_{scene_id}.mp3")
            for scene_id, text in narration_requests
        ])

        for (scene_id, _), result in zip(narration_requests, audio_results):
            if result.success and result.output_path:
                context.narration_audio_paths[scene_id] = str(result.output_path)
                for scene in context.scenes:
                    if scene.get("scene_id") == scene_id:
                        scene["narration_path"] = str(result.output_path)
            else:
                logger.warning(f"TTS failed for scene {scene_id}: {result.error}")

        self.report_progress(95, "Generating background music...")

        try:
            music_path = full_assets_dir / "background_music.mp3"
            music_result = await audio_service.generate(AudioRequest(
                text=f"Ambient background music for a {context.visual_style.value} video about {context.topic}",
                output_path=music_path,
                metadata={"role": "background_music"},
            ))
            if music_result.success and music_result.output_path:
                context.music_path = str(music_result.output_path)
        except Exception as e:
            logger.warning(f"Music generation failed: {e}")

        self.report_progress(100, "Asset generation complete")
        logger.info(f"Assets: {total} HTML scenes, {len(context.narration_audio_paths)} narrations")
        return context

    def _build_template_context(self, scene: dict, context: PipelineContext) -> dict:
        """Build the template context for a scene."""
        return {
            "title": scene.get("title", ""),
            "text": scene.get("script_text", ""),
            "topic": context.topic,
            "palette": {
                "primary": "#1a1a2e",
                "secondary": "#16213e",
                "accent": "#e94560",
                "text": "#ffffff",
                "text_secondary": "#a0a0a0",
                "background": "#0f0f23",
            },
            **{k: v for k, v in scene.get("visual_params", {}).items()},
        }
