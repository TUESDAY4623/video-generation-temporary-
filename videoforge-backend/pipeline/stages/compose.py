"""Stage 8: Render scenes and compose chapter videos."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.adapters.ffmpeg_adapter import FFmpegAdapter
from app.adapters.hyperframes_adapter import HyperFramesAdapter
from app.config import get_settings
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class ComposeStage(Stage):
    """Render HTML scenes to video clips and compose into chapter videos."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        settings = get_settings()
        output_dir = Path(settings.storage_dir) / "output" / str(self.stage_run.project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        hyper = HyperFramesAdapter()
        ffmpeg = FFmpegAdapter()

        self.report_progress(5, "Initializing renderers...")

        chapters = context.chapters or [{"chapter_number": 1, "scenes": context.scenes, "title": context.topic}]

        total_chapters = len(chapters)
        chapter_videos: list[str] = []

        for i, chapter in enumerate(chapters):
            chapter_num = chapter.get("chapter_number", i + 1)
            chapter_title = chapter.get("title", f"Chapter {chapter_num}")
            scenes = chapter.get("scenes", [])

            progress = 5 + int((i / total_chapters) * 80)
            self.report_progress(progress, f"Rendering chapter {chapter_num}/{total_chapters}...")

            try:
                chapter_video = await self._render_chapter(
                    chapter_num, chapter_title, scenes, output_dir, hyper, ffmpeg
                )
                chapter_videos.append(chapter_video)
                chapter["video_path"] = chapter_video
            except Exception as e:
                logger.error(f"Chapter {chapter_num} render failed: {e}")
                if i == 0:
                    raise StageError(f"First chapter render failed: {e}") from e
                continue

        context.chapter_video_paths = chapter_videos

        self.report_progress(100, f"Composition complete: {len(chapter_videos)} chapter videos")
        logger.info("Composed %d chapter videos", len(chapter_videos))
        return context

    async def _render_chapter(
        self, chapter_num: int, _title: str, scenes: list[dict],
        output_dir: Path, hyper: HyperFramesAdapter, ffmpeg: FFmpegAdapter,
    ) -> str:
        """Render a single chapter to video."""
        chapter_dir = output_dir / f"chapter_{chapter_num}"
        chapter_dir.mkdir(exist_ok=True)

        scene_clips: list[str] = []

        for j, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", f"{chapter_num}.{j+1}")
            html_path = scene.get("html_path")
            narration_path = scene.get("narration_path")

            if not html_path or not Path(html_path).exists():
                logger.warning(f"Scene {scene_id}: no HTML, skipping")
                continue

            clip_path = chapter_dir / f"clip_{j+1}.mp4"

            try:
                await hyper.render_scene(
                    html_content=Path(html_path).read_text(encoding="utf-8"),
                    scene_type=scene.get("scene_type", "text_card"),
                    output_path=str(clip_path),
                    width=1920,
                    height=1080,
                    fps=30,
                )

                if narration_path and Path(narration_path).exists():
                    audio_clip = chapter_dir / f"clip_{j+1}_audio.mp4"
                    ffmpeg.add_audio(str(clip_path), narration_path, str(audio_clip))
                    clip_path = audio_clip

                scene_clips.append(str(clip_path))

            except Exception as e:
                logger.warning(f"Scene {scene_id} render failed: {e}")

        if not scene_clips:
            raise StageError(f"No scenes rendered for chapter {chapter_num}")

        # Concatenate clips into chapter video
        chapter_video = output_dir / f"chapter_{chapter_num}.mp4"
        try:
            ffmpeg.concat_videos(scene_clips, str(chapter_video))
        except Exception as e:
            logger.warning(f"Concatenation failed: {e}, using first clip")
            shutil.copy(scene_clips[0], str(chapter_video))

        return str(chapter_video)
