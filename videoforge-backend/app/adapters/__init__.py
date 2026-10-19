"""Adapters package for external engines and models."""

from app.adapters.chat_tts_adapter import ChatTTSAdapter
from app.adapters.whisper_aligner import WhisperAligner

__all__ = ["ChatTTSAdapter", "WhisperAligner"]


