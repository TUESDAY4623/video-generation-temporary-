"""Anthropic Claude API Adapter for VideoForge.

Handles LLM-powered script writing, research, and visual blueprint extraction.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnthropicAdapter:
    """Wrapper for Anthropic Claude 3.5 Sonnet / Haiku API calls."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic
            if not self.api_key:
                logger.warning("ANTHROPIC_API_KEY is not set. Claude API calls may fail.")
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            return self._client
        except ImportError:
            logger.error("anthropic library is not installed.")
            return None

    async def generate_with_system_prompt(
        self,
        messages: List[Dict[str, str]],
        system: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> str:
        """Generate response from Claude using system prompt and messages."""
        client = self._get_client()
        if client is None or not self.api_key:
            raise RuntimeError("Anthropic API key is missing or client could not be initialized.")

        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return response.content[0].text
