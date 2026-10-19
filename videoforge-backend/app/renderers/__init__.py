"""Video renderers for different output formats."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.adapters.hyperframes_adapter import HyperFramesAdapter
from app.adapters.ffmpeg_adapter import FFmpegAdapter

logger = logging.getLogger(__name__)


class HyperFramesRenderer:
    """Render HTML scenes using HyperFrames CLI."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.adapter = HyperFramesAdapter()

    async def render_scene(
        self,
        html_path: str | Path,
        output_path: str | Path,
        duration: float | None = None,
    ) -> Path:
        """Render a single HTML scene to video."""
        return await self.adapter.render_scene(
            html_content=html_path,
            output_path=output_path,
            width=self.width,
            height=self.height,
            fps=self.fps,
            duration=duration,
        )

    async def render_chapter(
        self,
        html_paths: list[str | Path],
        output_path: str | Path,
    ) -> Path:
        """Render multiple HTML files as a chapter video."""
        return await self.adapter.render_chapter(
            html_files=html_paths,
            output_path=output_path,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )


class RemotionRenderer:
    """Render scenes using Remotion (React-based video framework)."""

    def __init__(self, remotion_url: str = "http://localhost:3000"):
        self.remotion_url = remotion_url
        self.ffmpeg = FFmpegAdapter()

    async def render_scene(
        self,
        composition_id: str,
        props: dict[str, Any],
        output_path: str | Path,
        duration: float = 30,
    ) -> Path:
        """Render a Remotion composition to video."""
        import httpx

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            response = await client.post(
                f"{self.remotion_url}/api/render",
                json={
                    "compositionId": composition_id,
                    "props": props,
                    "outputPath": str(output_path),
                    "durationInSeconds": duration,
                },
            )
            response.raise_for_status()
            data = response.json()

        if data.get("success") and Path(output_path).exists():
            return output_path

        raise RuntimeError(f"Remotion render failed: {data.get('error', 'unknown')}")


class FFmpegRenderer:
    """High-level FFmpeg rendering operations."""

    def __init__(self):
        self.ffmpeg = FFmpegAdapter()

    async def render_from_images(
        self,
        image_paths: list[str | Path],
        output_path: str | Path,
        duration_per_image: float = 5,
        transition: str = "fade",
        transition_duration: float = 0.5,
    ) -> Path:
        """Create a video from a sequence of images with transitions."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(image_paths) == 1:
            return await self._image_to_video(image_paths[0], output_path, duration_per_image)

        return await self._images_with_transitions(
            image_paths, output_path, duration_per_image, transition, transition_duration
        )

    async def render_from_html(
        self,
        html_path: str | Path,
        output_path: str | Path,
        duration: float | None = None,
    ) -> Path:
        """Render HTML to video using HyperFrames backend."""
        renderer = HyperFramesRenderer()
        return await renderer.render_scene(html_path, output_path, duration)

    async def _image_to_video(
        self, image_path: str | Path, output_path: Path, duration: float
    ) -> Path:
        """Convert a single image to a video of given duration."""
        import subprocess

        result = subprocess.run(
            [
                self.ffmpeg._ffmpeg,
                "-y",
                "-loop", "1",
                "-i", str(image_path),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-t", str(duration),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Image to video failed: {result.stderr[:200]}")
        return output_path

    async def _images_with_transitions(
        self,
        image_paths: list[str | Path],
        output_path: Path,
        duration_per: float,
        transition: str,
        transition_dur: float,
    ) -> Path:
        """Create a slideshow video with transitions."""
        import subprocess
        import tempfile

        video_paths = []
        for i, img in enumerate(image_paths):
            clip = output_path.parent / f"_clip_{i}.mp4"
            await self._image_to_video(img, clip, duration_per)
            video_paths.append(clip)

        try:
            return self.ffmpeg.concat_videos(video_paths, output_path)
        finally:
            for clip in video_paths:
                clip.unlink(missing_ok=True)
