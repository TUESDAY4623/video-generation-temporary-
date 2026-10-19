"""ElevenLabs cloud TTS provider with Edge-TTS fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.services.audio import AudioEngine, AudioRequest, AudioResult, BaseAudioProvider

logger = logging.getLogger(__name__)


class ElevenLabsCloudProvider(BaseAudioProvider):
    """ElevenLabs Cloud TTS provider with Edge-TTS fallback."""

    name = "ElevenLabs Cloud"
    engine = AudioEngine.ELEVENLABS_CLOUD

    def __init__(self):
        self.settings = get_settings()
        self.api_key = getattr(self.settings, "elevenlabs_api_key", "")
        self.default_voice_id = getattr(self.settings, "elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM") or "21m00Tcm4TlvDq8ikWAM"

    async def health_check(self) -> bool:
        """Check if ElevenLabs or Edge-TTS is available."""
        if self.api_key and self.api_key not in ("", "your-elevenlabs-key-here"):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.elevenlabs.io/v1/user",
                        headers={"xi-api-key": self.api_key},
                    )
                    return resp.status_code == 200
            except Exception:
                pass
        # Fallback to Edge-TTS
        return True

    async def list_voices(self) -> list[dict[str, str]]:
        """List available voices."""
        if self.api_key and self.api_key not in ("", "your-elevenlabs-key-here"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.elevenlabs.io/v1/voices",
                        headers={"xi-api-key": self.api_key},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return [
                            {"id": v["voice_id"], "name": v["name"]}
                            for v in data.get("voices", [])
                        ]
            except Exception as e:
                logger.warning(f"Failed to fetch ElevenLabs voices: {e}")

        # Edge-TTS default voices
        return [
            {"id": "en-US-ChristopherNeural", "name": "Christopher (US Male)"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US Female)"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male)"},
            {"id": "en-US-AriaNeural", "name": "Aria (US Female)"},
        ]

    async def generate(self, request: AudioRequest) -> AudioResult:
        """Generate audio using ElevenLabs or Edge-TTS fallback."""
        output_path = request.output_path or (
            self.settings.storage_dir / "audio" / f"eleven_{abs(hash(request.text)) % 10**8}.mp3"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_id = request.voice_id
        if not voice_id or voice_id == "default":
            voice_id = self.default_voice_id

        # 1. Try ElevenLabs API if key is set
        if self.api_key and self.api_key not in ("", "your-elevenlabs-key-here"):
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "text": request.text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    output_path.write_bytes(resp.content)
                    return AudioResult(
                        success=True,
                        output_path=output_path,
                        engine_used=self.engine,
                        metadata={"provider": "elevenlabs"},
                    )
            except Exception as e:
                logger.warning(f"ElevenLabs generation failed: {e}. Falling back to Edge-TTS.")

        # 2. Fallback to Edge-TTS
        try:
            import edge_tts

            edge_voice = voice_id if "Neural" in voice_id else "en-US-ChristopherNeural"
            communicate = edge_tts.Communicate(request.text, edge_voice)
            await communicate.save(str(output_path))

            return AudioResult(
                success=True,
                output_path=output_path,
                engine_used=self.engine,
                metadata={"provider": "edge-tts"},
            )
        except Exception as e:
            logger.error(f"Edge-TTS generation failed: {e}")
            return AudioResult(
                success=False,
                engine_used=self.engine,
                error=f"ElevenLabs and Edge-TTS both failed: {e}",
            )
