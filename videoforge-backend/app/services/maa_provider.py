"""Make-An-Audio (MAA) provider for SFX and music."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.services.audio import AudioEngine, AudioRequest, AudioResult, BaseAudioProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class MAAProvider(BaseAudioProvider):
    """Make-An-Audio provider for sound effects and music generation."""

    name = "Make-An-Audio"
    engine = AudioEngine.MAA

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.elevenlabs_maa_url
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def generate(self, request: AudioRequest) -> AudioResult:
        """Generate audio using MAA. Best for sound effects and short music clips."""
        output_path = request.output_path or self.settings.storage_dir / "audio" / f"maa_{hash(request.text) % 10**8}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            payload = {
                "prompt": request.text,
                "duration_seconds": request.metadata.get("duration_seconds", 10),
                "force_instrumental": True,
            }

            resp = await self._client.post(
                "/generate",
                json=payload,
                timeout=httpx.Timeout(300.0),
            )

            if resp.status_code != 200:
                return AudioResult(
                    success=False,
                    engine_used=self.engine,
                    error=f"MAA returned {resp.status_code}: {resp.text[:200]}",
                )

            output_path.write_bytes(resp.content)

            duration = output_path.stat().st_size / 48000.0 if output_path.exists() else 0.0

            return AudioResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                engine_used=self.engine,
                metadata=request.metadata,
            )

        except Exception as e:
            logger.error(f"MAA generation failed: {e}")
            return AudioResult(success=False, engine_used=self.engine, error=str(e))

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_voices(self) -> list[dict[str, str]]:
        return []

    async def close(self) -> None:
        await self._client.aclose()
