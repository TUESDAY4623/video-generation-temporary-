"""Seed-VC voice cloning provider."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.services.audio import AudioEngine, AudioRequest, AudioResult, BaseAudioProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class SeedVCProvider(BaseAudioProvider):
    """Seed-VC voice cloning provider."""

    name = "Seed-VC"
    engine = AudioEngine.SEED_VC

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.elevenlabs_seedvc_url
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def generate(self, request: AudioRequest) -> AudioResult:
        """Clone voice using Seed-VC.

        Requires a reference audio file. The reference audio path
        should be provided in request.metadata["reference_audio"].
        """
        output_path = request.output_path or self.settings.storage_dir / "audio" / f"seedvc_{hash(request.text) % 10**8}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        reference_audio = request.metadata.get("reference_audio")
        if not reference_audio:
            return AudioResult(
                success=False,
                engine_used=self.engine,
                error="Seed-VC requires reference_audio in request.metadata",
            )

        try:
            # Read the reference audio file
            ref_path = Path(reference_audio)
            if not ref_path.exists():
                return AudioResult(
                    success=False,
                    engine_used=self.engine,
                    error=f"Reference audio not found: {reference_audio}",
                )

            files = {
                "source_audio": ("source.wav", ref_path.read_bytes(), "audio/wav"),
            }
            data = {
                "text": request.text,
                "target_voice": request.voice_id,
            }

            resp = await self._client.post(
                "/convert",
                files=files,
                data=data,
                timeout=httpx.Timeout(300.0),
            )

            if resp.status_code != 200:
                return AudioResult(
                    success=False,
                    engine_used=self.engine,
                    error=f"Seed-VC returned {resp.status_code}: {resp.text[:200]}",
                )

            output_path.write_bytes(resp.content)

            duration = output_path.stat().st_size / 48000.0 if output_path.exists() else 0.0

            return AudioResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                engine_used=self.engine,
                metadata={"reference_audio": str(ref_path)},
            )

        except Exception as e:
            logger.error(f"Seed-VC generation failed: {e}")
            return AudioResult(success=False, engine_used=self.engine, error=str(e))

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_voices(self) -> list[dict[str, str]]:
        return [{"id": "custom", "name": "Custom (provide reference_audio)"}]

    async def close(self) -> None:
        await self._client.aclose()
