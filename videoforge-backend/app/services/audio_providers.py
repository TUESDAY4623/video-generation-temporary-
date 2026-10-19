"""StyleTTS2 local TTS provider."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.services.audio import AudioEngine, AudioRequest, AudioResult, BaseAudioProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class StyleTTS2Provider(BaseAudioProvider):
    """StyleTTS2 local TTS provider."""

    name = "StyleTTS2"
    engine = AudioEngine.STY_TTS2

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.elevenlabs_styltts_url
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )
        self._voice_map: dict[str, str] = {}

    async def _discover_voices(self) -> dict[str, Any]:
        """Fetch available voices from the StyleTTS2 server."""
        try:
            resp = await self._client.get("/voices")
            if resp.status_code == 200:
                data = resp.json()
                voices = data.get("voices", {})
                if isinstance(voices, dict):
                    return voices
                if isinstance(voices, list):
                    return {v.get("name", v): v.get("path", v) for v in voices}
        except Exception as e:
            logger.warning(f"Could not fetch StyleTTS2 voices: {e}")
        return {}

    async def _ensure_voice(self, voice_id: str) -> str:
        """Resolve voice ID to a reference audio path or name."""
        if not self._voice_map:
            self._voice_map = await self._discover_voices()
        if voice_id in self._voice_map:
            return self._voice_map[voice_id]
        if voice_id != "default" and voice_id not in self._voice_map:
            logger.warning(f"Voice '{voice_id}' not found, using default")
        return self._voice_map.get("default", list(self._voice_map.values())[0] if self._voice_map else "default")

    async def generate(self, request: AudioRequest) -> AudioResult:
        """Generate audio using StyleTTS2."""
        output_path = request.output_path or self.settings.storage_dir / "audio" / f"sty_{hash(request.text) % 10**8}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            voice = await self._ensure_voice(request.voice_id)

            resp = await self._client.post(
                "/generate",
                json={
                    "text": request.text,
                    "target_voice": voice,
                    "language": request.language,
                },
                timeout=httpx.Timeout(300.0),
            )

            if resp.status_code != 200:
                return AudioResult(
                    success=False,
                    engine_used=self.engine,
                    error=f"StyleTTS2 returned {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            audio_url = data.get("audio_url")

            if audio_url and audio_url.startswith("http"):
                # Download the audio file
                audio_resp = await self._client.get(audio_url, timeout=60.0)
                output_path.write_bytes(audio_resp.content)
            elif audio_url and not audio_url.startswith("http"):
                # Local file path
                src = Path(audio_url)
                if src.exists():
                    output_path.write_bytes(src.read_bytes())
                else:
                    return AudioResult(success=False, engine_used=self.engine, error=f"Audio file not found: {src}")
            else:
                # Direct binary response
                output_path.write_bytes(resp.content)

            # Estimate duration from file size (rough: 24kHz, 16-bit mono ≈ 48KB/s)
            duration = output_path.stat().st_size / 48000.0 if output_path.exists() else 0.0

            return AudioResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                engine_used=self.engine,
                metadata={"voice": voice},
            )

        except Exception as e:
            logger.error(f"StyleTTS2 generation failed: {e}")
            return AudioResult(success=False, engine_used=self.engine, error=str(e))

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_voices(self) -> list[dict[str, str]]:
        voices = await self._discover_voices()
        return [{"id": k, "name": k} for k in voices]

    async def close(self) -> None:
        await self._client.aclose()
