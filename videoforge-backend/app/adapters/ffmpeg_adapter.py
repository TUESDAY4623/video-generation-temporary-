"""FFmpeg adapter for VideoForge video and audio processing."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class FFmpegAdapter:
    """Provides video/audio operations via FFmpeg CLI."""

    def __init__(self, ffmpeg_path: str | None = None):
        self._ffmpeg = ffmpeg_path or shutil.which("ffmpeg") or "ffmpeg"

    def run_cmd(self, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """Run an ffmpeg command."""
        cmd = [self._ffmpeg, "-y"] + args
        logger.debug("Executing FFmpeg command: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error("FFmpeg failed with code %d: %s", result.returncode, result.stderr[-500:])
            raise RuntimeError(f"FFmpeg command failed: {result.stderr[-300:]}")
        return result

    def concat_videos(self, video_paths: Sequence[str | Path], output_path: str | Path) -> Path:
        """Concatenate multiple video files into a single video."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        valid_paths = [Path(p) for p in video_paths if Path(p).exists()]
        if not valid_paths:
            raise ValueError("No valid video paths to concatenate")

        if len(valid_paths) == 1:
            shutil.copy(str(valid_paths[0]), str(out))
            return out

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for p in valid_paths:
                clean_path = str(p.resolve()).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")
            list_file = f.name

        try:
            self.run_cmd([
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                str(out),
            ])
        except Exception:
            # Fallback to re-encoding if streams are mismatched
            inputs = []
            filter_parts = []
            for i, p in enumerate(valid_paths):
                inputs.extend(["-i", str(p)])
                filter_parts.append(f"[{i}:v:0][{i}:a:0]")
            filter_str = f"{''.join(filter_parts)}concat=n={len(valid_paths)}:v=1:a=1[v][a]"
            self.run_cmd(
                inputs + ["-filter_complex", filter_str, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", str(out)]
            )
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

        return out

    def add_audio(self, video_path: str | Path, audio_path: str | Path, output_path: str | Path) -> Path:
        """Combine video and audio track."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.run_cmd([
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(out),
        ])
        return out

    def mix_audio(
        self,
        video_path: str | Path,
        music_path: str | Path,
        output_path: str | Path,
        music_volume: float = 0.1,
    ) -> Path:
        """Mix background music into video."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            filter_complex = f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]"
            self.run_cmd([
                "-i", str(video_path),
                "-i", str(music_path),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                str(out),
            ])
        except Exception:
            # If video has no audio track, use music track directly
            self.run_cmd([
                "-i", str(video_path),
                "-i", str(music_path),
                "-filter:a", f"volume={music_volume}",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(out),
            ])
        return out

    def concat_with_intro_outro(
        self,
        intro: str | Path,
        main: str | Path,
        outro: str | Path,
        output: str | Path,
    ) -> Path:
        """Concatenate intro, main video, and outro clips."""
        return self.concat_videos([intro, main, outro], output)

    def extract_thumbnail(self, video_path: str | Path, output_path: str | Path, time_sec: float = 1.0) -> Path:
        """Extract a single frame thumbnail from video."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.run_cmd([
            "-ss", str(time_sec),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(out),
        ])
        return out

    def create_text_clip(
        self,
        text: str,
        output_path: str | Path,
        duration: float = 3.0,
        width: int = 1920,
        height: int = 1080,
    ) -> Path:
        """Create a full HD video clip with centered text."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Sanitize text for drawtext
        clean_text = text.replace(":", "\\:").replace("'", "\\'").replace('"', "")
        drawtext = (
            f"drawtext=text='{clean_text}':fontcolor=white:fontsize=56:x=(w-text_w)/2:y=(h-text_h)/2"
        )
        self.run_cmd([
            "-f", "lavfi",
            "-i", f"color=c=0x0f172a:s={width}x{height}:d={duration}",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-vf", drawtext,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(out),
        ])
        return out
