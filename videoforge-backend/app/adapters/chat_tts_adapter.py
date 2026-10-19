"""ChatTTS & Edge-TTS Voice Generation Adapter for VideoForge.

Generates high fidelity, natural conversational narration with zero API cost.
Supports ChatTTS (Local AI voice model) with fallback to Microsoft Edge-TTS neural voices.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChatTTSAdapter:
    """Conversational TTS generation with ChatTTS and Microsoft Edge-TTS fallback."""

    def __init__(self, voice_id: Optional[str] = None):
        self.voice_id = voice_id or os.getenv("CHAT_TTS_VOICE", "seed_default")
        self.edge_voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
        self._chat_tts = None

    def _init_chat_tts(self):
        """Lazy initialization of ChatTTS local model."""
        if self._chat_tts is not None:
            return self._chat_tts
        try:
            import ChatTTS
            import torch
            logger.info("Initializing ChatTTS engine...")
            chat = ChatTTS.Chat()
            chat.load(compile=False)
            self._chat_tts = chat
            return self._chat_tts
        except Exception as e:
            logger.warning("ChatTTS not available on this machine (%s). Falling back to Edge-TTS.", e)
            return None

    async def generate_speech(
        self,
        text: str,
        output_path: str | Path,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Path:
        """Generate audio for the given narration text."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Narration text is empty")

        provider = os.getenv("TTS_PROVIDER", "edge").lower()
        if provider == "chat_tts":
            chat = self._init_chat_tts()
            if chat is not None:
                try:
                    import soundfile as sf
                    wavs = chat.infer([cleaned_text])
                    if wavs and len(wavs) > 0:
                        sf.write(str(output_path), wavs[0][0], 24000)
                        logger.info("ChatTTS audio saved: %s", output_path)
                        return output_path
                except Exception as e:
                    logger.warning("ChatTTS inference failed (%s). Using Edge-TTS fallback.", e)

        try:
            import edge_tts
            selected_voice = voice or self.edge_voice
            communicate = edge_tts.Communicate(
                text=cleaned_text,
                voice=selected_voice,
                rate=rate,
                pitch=pitch,
            )
            await communicate.save(str(output_path))
            logger.info("Edge-TTS audio saved: %s", output_path)
            return output_path
        except Exception as edge_err:
            logger.warning("Edge-TTS failed (%s). Using Windows System.Speech fallback.", edge_err)

        # Fallback to Windows SpeechSynthesizer
        temp_wav = output_path.with_suffix(".temp.wav")
        safe_text = cleaned_text.replace("'", "''").replace('"', '`"')
        ps_script = f"""Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile('{temp_wav.as_posix()}'); $s.Speak('{safe_text}'); $s.Dispose()"""
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps_script,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        await proc.communicate()

        if temp_wav.exists() and temp_wav.stat().st_size > 1000:
            # Convert WAV to MP3 using ffmpeg
            conv = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", str(temp_wav), "-c:a", "libmp3lame", "-b:a", "192k", str(output_path),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            await conv.communicate()
            temp_wav.unlink(missing_ok=True)
            if output_path.exists():
                logger.info("Windows System.Speech audio saved: %s", output_path)
                return output_path

        raise RuntimeError(f"All TTS generation methods failed for: {cleaned_text[:50]}")

