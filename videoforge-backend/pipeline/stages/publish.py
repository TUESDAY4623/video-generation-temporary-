"""Stage 9: Final assembly, add music/SFX, generate thumbnail, publish."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.adapters.ffmpeg_adapter import FFmpegAdapter
from app.config import get_settings
from pipeline.models.entities import PipelineContext
from pipeline.stages.base import Stage, StageError

logger = logging.getLogger(__name__)


class PublishStage(Stage):
    """Finalize the video: add music, SFX, intro/outro, generate thumbnail."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        settings = get_settings()
        output_dir = Path(settings.storage_dir) / "output" / str(self.stage_run.project_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg = FFmpegAdapter()
        chapter_videos = context.chapter_video_paths

        if not chapter_videos:
            raise StageError("No chapter videos to publish")

        # Concatenate all chapter videos
        self.report_progress(20, "Concatenating chapters...")
        raw_output = output_dir / "raw_combined.mp4"
        try:
            ffmpeg.concat_videos(chapter_videos, str(raw_output))
        except Exception as e:
            raise StageError(f"Video concatenation failed: {e}") from e

        # Add background music
        self.report_progress(45, "Adding background music...")
        music_mixed = output_dir / "with_music.mp4"
        try:
            if context.music_path and Path(context.music_path).exists():
                ffmpeg.mix_audio(
                    video_path=str(raw_output),
                    music_path=context.music_path,
                    output_path=str(music_mixed),
                    music_volume=0.1,
                )
            else:
                shutil.copy(str(raw_output), str(music_mixed))
        except Exception as e:
            logger.warning(f"Music mixing failed: {e}, using raw video")
            shutil.copy(str(raw_output), str(music_mixed))

        # Add intro and outro
        self.report_progress(70, "Adding intro and outro...")
        final_output = output_dir / f"{context.topic.replace(' ', '_')}_final.mp4"
        try:
            intro_path = self._create_text_clip(output_dir, context.topic, ffmpeg, duration=3)
            outro_path = self._create_text_clip(output_dir, "Thanks for watching!", ffmpeg, duration=5)

            if intro_path and outro_path:
                ffmpeg.concat_with_intro_outro(
                    intro=str(intro_path),
                    main=str(music_mixed),
                    outro=str(outro_path),
                    output=str(final_output),
                )
            else:
                shutil.copy(str(music_mixed), str(final_output))
        except Exception as e:
            logger.warning(f"Intro/outro failed: {e}, using music-mixed video")
            shutil.copy(str(music_mixed), str(final_output))

        context.final_video_path = str(final_output)

        # Generate thumbnail
        self.report_progress(90, "Generating thumbnail...")
        try:
            thumb_path = output_dir / "thumbnail.png"
            ffmpeg.extract_thumbnail(str(final_output), str(thumb_path))
            context.thumbnail_path = str(thumb_path)
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        self.report_progress(100, "Publishing complete")
        logger.info("Final video: %s", context.final_video_path)
        return context

    def _create_text_clip(self, output_dir: Path, text: str, ffmpeg: FFmpegAdapter, duration: int = 3) -> Path | None:
        """Create a simple text clip."""
        clip_path = output_dir / f"text_{hash(text) % 10000}.mp4"
        try:
            ffmpeg.create_text_clip(
                text=text,
                output_path=str(clip_path),
                duration=duration,
                width=1920,
                height=1080,
            )
        except Exception:
            return None
        if clip_path.exists():
            return clip_path
        return None
