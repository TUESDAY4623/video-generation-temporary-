"""HyperFrames adapter for rendering HTML scenes to video."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

from app.adapters.ffmpeg_adapter import FFmpegAdapter

logger = logging.getLogger(__name__)


class HyperFramesAdapter:
    """Renders HTML-based animated scenes to MP4 video using headless browser and FFmpeg."""

    def __init__(self):
        self.ffmpeg = FFmpegAdapter()

    async def render_scene(
        self,
        html_content: str | Path,
        output_path: str | Path,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        duration: float | None = None,
        scene_type: str = "text_card",
    ) -> Path:
        """Render a single HTML scene into an MP4 video clip."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        dur = duration or 10.0

        temp_dir = Path(tempfile.mkdtemp(prefix="hyperframes_"))
        try:
            # Prepare HTML file
            if isinstance(html_content, Path) or (isinstance(html_content, str) and os.path.exists(html_content)):
                html_file = Path(html_content).resolve()
            else:
                html_file = temp_dir / "scene.html"
                html_file.write_text(str(html_content), encoding="utf-8")

            render_script = Path(__file__).resolve().parent.parent.parent / "_render_clip.py"
            cmd = [
                "python",
                str(render_script),
                str(html_file),
                str(dur),
                str(width),
                str(height),
                str(temp_dir),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            webm_output = temp_dir / "output.webm"
            if webm_output.exists():
                # Transcode WEBM to MP4
                self.ffmpeg.run_cmd([
                    "-i", str(webm_output),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    "-t", str(dur),
                    str(out),
                ])
            else:
                logger.warning(
                    "Playwright output missing. Generating fallback text card. Stderr: %s",
                    stderr.decode() if stderr else "",
                )
                self.ffmpeg.create_text_clip(
                    text=f"Scene: {scene_type}",
                    output_path=out,
                    duration=dur,
                    width=width,
                    height=height,
                )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return out

    async def render_chapter(
        self,
        html_files: Sequence[str | Path],
        output_path: str | Path,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_duration: float = 10.0,
    ) -> Path:
        """Render a series of HTML files into one combined chapter video."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        clips: list[Path] = []
        for i, html_file in enumerate(html_files):
            clip = out.parent / f"_temp_clip_{i}.mp4"
            await self.render_scene(
                html_content=html_file,
                output_path=clip,
                width=width,
                height=height,
                fps=fps,
                duration=scene_duration,
            )
            clips.append(clip)

        try:
            return self.ffmpeg.concat_videos(clips, out)
        finally:
            for clip in clips:
                if clip.exists():
                    clip.unlink(missing_ok=True)
