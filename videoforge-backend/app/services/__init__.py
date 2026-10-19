"""Audio service factory — wires all providers together."""

from __future__ import annotations

import logging

from app.services.audio import AudioEngine, AudioService
from app.services.audio_providers import StyleTTS2Provider
from app.services.seedvc_provider import SeedVCProvider
from app.services.maa_provider import MAAProvider

logger = logging.getLogger(__name__)


def create_audio_service() -> AudioService:
    """Create and configure the audio service with all providers."""
    from app.adapters.elevenlabs_adapter import ElevenLabsCloudProvider

    service = AudioService()

    # Register local providers (priority order)
    service.register_provider(AudioEngine.STY_TTS2, StyleTTS2Provider())
    service.register_provider(AudioEngine.SEED_VC, SeedVCProvider())
    service.register_provider(AudioEngine.MAA, MAAProvider())
    service.register_provider(AudioEngine.ELEVENLABS_CLOUD, ElevenLabsCloudProvider())

    return service


# Global audio service instance
audio_service = create_audio_service()
