"""Unified LLM provider for PARALLAX agents.

Every agent talks to the model layer through a *role* (e.g. ``"synthesis"``)
rather than a concrete model name. The roster below maps each role to a local
Ollama model and declares whether the role is allowed to use a cloud model.

Routing is governed by ``settings.LLM_MODE``:

* ``local``  - every role uses its local Ollama model.
* ``cloud``  - cloud-capable roles use the configured cloud provider; the rest
               stay local. Falls back to local if no cloud key is configured.
* ``auto``   - identical to ``cloud`` but silently degrades to local whenever a
               cloud key is missing, so the same config works before and after
               credits land.

The provider exposes three async primitives used across the cortex:
``complete_json``, ``complete_text`` and ``embed``. Vision is supported by
passing base64-encoded PNGs via ``images``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, cast

import httpx

from parallax.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSpec:
    """How a single agent role is served."""

    local_model: str
    cloud_capable: bool = False
    supports_vision: bool = False


# Role -> model mapping. Local models match the pulled Ollama roster.
ROSTER: dict[str, ModelSpec] = {
    "triage": ModelSpec("phi3:mini"),
    "hook_planner": ModelSpec("phi3:mini"),
    "hypothesis": ModelSpec("phi3:mini"),
    "re_workbench": ModelSpec("qwen2.5-coder:7b", cloud_capable=True),
    "code_interpreter": ModelSpec("qwen2.5-coder:7b", cloud_capable=True),
    "behavior_analyst": ModelSpec("mistral:7b", cloud_capable=True),
    "intel_correlator": ModelSpec("mistral:7b", cloud_capable=True),
    "dynamic_explorer": ModelSpec("llava:7b", supports_vision=True),
    "visual": ModelSpec("llava:7b", supports_vision=True),
    "debate": ModelSpec("mistral:7b", cloud_capable=True),
    "synthesis": ModelSpec("mistral:7b", cloud_capable=True),
    "evidence_validator": ModelSpec("mistral:7b", cloud_capable=True),
    "embedding": ModelSpec("nomic-embed-text"),
}

# Fallback for roles not present in the roster.
_DEFAULT_SPEC = ModelSpec("mistral:7b", cloud_capable=True)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from a model response."""
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return cast(dict, json.loads(text))
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)
        if match:
            return cast(dict, json.loads(match.group(0)))
        raise


class LLMProvider:
    """Routes agent requests to a local or cloud backend per role."""

    def __init__(self) -> None:
        # Generous timeout: local 7B inference on CPU-only hosts can take
        # several minutes per call for large prompts. Cloud backends are far
        # faster and bounded by their own SDK timeouts.
        self._ollama = httpx.AsyncClient(
            base_url=settings.OLLAMA_HOST, timeout=httpx.Timeout(900.0, connect=15.0)
        )
        self._anthropic: Any = None  # lazily constructed
        self._openai: Any = None  # lazily constructed

    # ------------------------------------------------------------------ #
    # Routing
    # ------------------------------------------------------------------ #
    def spec_for(self, role: str) -> ModelSpec:
        return ROSTER.get(role, _DEFAULT_SPEC)

    def _cloud_key(self) -> str:
        if settings.CLOUD_PROVIDER == "openai":
            return settings.OPENAI_API_KEY
        return settings.ANTHROPIC_API_KEY

    def provider_for(self, role: str) -> str:
        """Return ``"ollama"``, ``"anthropic"`` or ``"openai"`` for a role."""
        spec = self.spec_for(role)
        mode = settings.LLM_MODE.lower()
        wants_cloud = mode in ("cloud", "auto") and spec.cloud_capable
        if wants_cloud and self._cloud_key():
            return settings.CLOUD_PROVIDER
        if wants_cloud and mode == "cloud":
            logger.warning(
                "LLM_MODE=cloud but no %s key configured; role %r falling back "
                "to local Ollama.",
                settings.CLOUD_PROVIDER,
                role,
            )
        return "ollama"

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    async def complete_text(
        self,
        role: str,
        prompt: str,
        system: str = "",
        images: list[str] | None = None,
        temperature: float = 0.1,
    ) -> str:
        provider = self.provider_for(role)
        if provider == "ollama":
            return await self._ollama_generate(
                self.spec_for(role).local_model, prompt, system, images,
                temperature, json_mode=False,
            )
        return await self._cloud_generate(
            provider, prompt, system, images, temperature, json_mode=False
        )

    async def complete_json(
        self,
        role: str,
        prompt: str,
        system: str = "",
        images: list[str] | None = None,
        temperature: float = 0.1,
    ) -> dict:
        provider = self.provider_for(role)
        if provider == "ollama":
            raw = await self._ollama_generate(
                self.spec_for(role).local_model, prompt, system, images,
                temperature, json_mode=True,
            )
        else:
            raw = await self._cloud_generate(
                provider, prompt, system, images, temperature, json_mode=True
            )
        return _extract_json(raw)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using the local embedding model.

        Embeddings stay local regardless of LLM_MODE: they are cheap, run
        constantly, and keeping them deterministic avoids vector-space drift in
        the TAIG graph when cloud routing toggles.
        """
        model = self.spec_for("embedding").local_model
        vectors: list[list[float]] = []
        for text in texts:
            resp = await self._ollama.post(
                "/api/embeddings", json={"model": model, "prompt": text}
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
        return vectors

    # ------------------------------------------------------------------ #
    # Backends
    # ------------------------------------------------------------------ #
    async def _ollama_generate(
        self,
        model: str,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images
        resp = await self._ollama.post("/api/generate", json=payload)
        resp.raise_for_status()
        return str(resp.json().get("response", ""))

    async def _cloud_generate(
        self,
        provider: str,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if provider == "anthropic":
            return await self._anthropic_generate(
                prompt, system, images, temperature, json_mode
            )
        return await self._openai_generate(
            prompt, system, images, temperature, json_mode
        )

    async def _anthropic_generate(
        self,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if self._anthropic is None:
            from anthropic import AsyncAnthropic

            self._anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        content: list[dict] = []
        for img in images or []:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img,
                    },
                }
            )
        text_prompt = prompt
        if json_mode:
            text_prompt += "\n\nRespond with a single valid JSON object only."
        content.append({"type": "text", "text": text_prompt})

        resp = await self._anthropic.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            temperature=temperature,
            system=system or "You are a precise malware-analysis agent.",
            messages=[{"role": "user", "content": content}],
        )
        return "".join(
            block.text for block in resp.content if block.type == "text"
        )

    async def _openai_generate(
        self,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if self._openai is None:
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        user_content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images or []:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img}"},
                }
            )
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content})

        kwargs: dict = {
            "model": settings.OPENAI_MODEL,
            "temperature": temperature,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self._openai.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def close(self) -> None:
        await self._ollama.aclose()


# Module-level singleton used across the cortex.
llm = LLMProvider()
