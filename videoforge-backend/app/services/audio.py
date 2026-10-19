"""Audio generation abstraction — local-first with fallback support."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class AudioEngine(str, Enum):
    """Available audio generation engines."""
    STY_TTS2 = "sty_tts2"
    SEED_VC = "seed_vc"
    MAA = "maa"
    ELEVENLABS_CLOUD = "elevenlabs_cloud"


@dataclass
class AudioRequest:
    """Request for audio generation."""
    text: str
    engine: AudioEngine = AudioEngine.STY_TTS2
    voice_id: str = "default"
    language: str = "en"
    speed: float = 1.0
    output_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioResult:
    """Result of audio generation."""
    success: bool
    output_path: Path | None = None
    duration_seconds: float = 0.0
    engine_used: AudioEngine = AudioEngine.STY_TTS2
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAudioProvider(ABC):
    """Abstract base for audio providers."""

    name: str = "base"
    engine: AudioEngine

    @abstractmethod
    async def generate(self, request: AudioRequest) -> AudioResult:
        """Generate audio from text."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        ...

    @abstractmethod
    async def list_voices(self) -> list[dict[str, str]]:
        """List available voices."""
        ...


class AudioService:
    """Orchestrates audio generation across multiple providers.

    Tries providers in priority order until one succeeds.
    Falls back gracefully if a provider is unavailable.
    """

    def __init__(self):
        self.settings = get_settings()
        self._providers: dict[AudioEngine, BaseAudioProvider] = {}
        self._fallback_order = [
            AudioEngine.STY_TTS2,
            AudioEngine.SEED_VC,
            AudioEngine.MAA,
            AudioEngine.ELEVENLABS_CLOUD,
        ]

    def register_provider(self, engine: AudioEngine, provider: BaseAudioProvider) -> None:
        """Register an audio provider."""
        self._providers[engine] = provider
        logger.info(f"Registered audio provider: {provider.name} ({engine.value})")

    async def initialize(self) -> None:
        """Initialize and health-check all registered providers."""
        for engine, provider in self._providers.items():
            try:
                healthy = await provider.health_check()
                if healthy:
                    logger.info(f"Audio provider {provider.name} is healthy")
                else:
                    logger.warning(f"Audio provider {provider.name} is not responding")
            except Exception as e:
                logger.warning(f"Audio provider {provider.name} health check failed: {e}")

    async def generate(self, request: AudioRequest) -> AudioResult:
        """Generate audio, trying providers in fallback order."""
        # If specific engine requested, try only that
        if request.engine != AudioEngine.ELEVENLABS_CLOUD:
            provider = self._providers.get(request.engine)
            if provider:
                return await provider.generate(request)
            return AudioResult(success=False, error=f"Engine {request.engine.value} not registered")

        # Fallback: try all registered providers
        errors = []
        for engine in self._fallback_order:
            provider = self._providers.get(engine)
            if not provider:
                continue
            try:
                result = await provider.generate(request)
                if result.success:
                    return result
                errors.append(f"{provider.name}: {result.error}")
            except Exception as e:
                errors.append(f"{provider.name}: {e}")

        return AudioResult(success=False, error=f"All providers failed: {'; '.join(errors)}")

    async def generate_narration(self, text: str, voice_id: str = "default",
                                 language: str = "en") -> AudioResult:
        """Convenience method for narration generation."""
        output_path = self.settings.storage_dir / "audio" / f"{hash(text) % 10**8}.mp3"
        request = AudioRequest(
            text=text,
            engine=AudioEngine.STY_TTS2,
            voice_id=voice_id,
            language=language,
            output_path=output_path,
        )
        return await self.generate(request)

    async def generate_batch(self, requests: list[AudioRequest]) -> list[AudioResult]:
        """Generate multiple audio files in parallel."""
        import asyncio
        tasks = [self.generate(req) for req in requests]
        return await asyncio.gather(*tasks)
