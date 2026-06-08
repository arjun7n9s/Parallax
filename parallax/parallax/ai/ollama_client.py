import json
import logging
from typing import Any

import httpx

from parallax.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for interacting with the local Ollama instance."""

    def __init__(self):
        # We can configure the URL in settings, defaulting to http://localhost:11434
        self.base_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    async def generate_json(self, model: str, prompt: str, system_prompt: str = "") -> dict[str, Any]:
        """
        Generate a JSON response from the specified Ollama model.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,  # Keep temperature low for structured extraction
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()
            
            response_text = result.get("response", "")
            
            # Ollama's json format usually guarantees valid JSON, but let's be safe
            return json.loads(response_text)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with Ollama: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Ollama response: {e}")
            logger.debug(f"Raw response: {result.get('response', '')}")
            raise

    async def close(self):
        await self.client.aclose()


# Global client instance
ollama_client = OllamaClient()
