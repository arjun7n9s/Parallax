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
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx

from parallax.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from parallax.core.config import settings
from parallax.core.errors import LLMBadOutputError, LLMError
from parallax.core.metrics import record_llm_call

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSpec:
    """How a single agent role is served.

    ``cloud_model`` is the aimlapi gateway model ID for the role; an empty
    string pins the role to local Ollama regardless of LLM_MODE. The roster
    is deliberately tiered by cost: economy models for high-frequency
    structured tasks, one mid-tier model for the two roles where output
    quality is decision-critical. Nothing in this pipeline justifies an
    Opus-class model.
    """

    local_model: str
    cloud_model: str = ""
    supports_vision: bool = False

    @property
    def cloud_capable(self) -> bool:
        return bool(self.cloud_model)


# Cost tiers (aimlapi model IDs).
_ECONOMY = "gpt-4o-mini"  # small structured-JSON tasks, high call volume
_ECONOMY_LONG = "google/gemini-2.5-flash"  # long-context + vision, still cheap
_PREMIUM = "anthropic/claude-sonnet-4.6"  # decision-critical reasoning only

# Role -> model mapping. Local models match the pulled Ollama roster.
ROSTER: dict[str, ModelSpec] = {
    # Economy: small prompts, strict JSON, validators downstream.
    "triage": ModelSpec("phi3:mini", _ECONOMY),
    "hook_planner": ModelSpec("phi3:mini", _ECONOMY),
    "hypothesis": ModelSpec("phi3:mini", _ECONOMY),
    "intel_correlator": ModelSpec("mistral:7b", _ECONOMY),
    "debate": ModelSpec("mistral:7b", _ECONOMY),
    # Economy long-context / vision: observation timelines and screenshots.
    "behavior_analyst": ModelSpec("mistral:7b", _ECONOMY_LONG),
    "evidence_validator": ModelSpec("mistral:7b", _ECONOMY_LONG),
    "dynamic_explorer": ModelSpec("llava:7b", _ECONOMY_LONG, supports_vision=True),
    "visual": ModelSpec("llava:7b", _ECONOMY_LONG, supports_vision=True),
    # Premium (the only two): decompiled-code interpretation and the final
    # bank-facing synthesis. Detection quality and report quality live here.
    "re_workbench": ModelSpec("qwen2.5-coder:7b", _PREMIUM),
    "code_interpreter": ModelSpec("qwen2.5-coder:7b", _PREMIUM),
    "synthesis": ModelSpec("mistral:7b", _PREMIUM),
    # Embeddings stay local always — see embed() docstring.
    "embedding": ModelSpec("nomic-embed-text"),
}

# Fallback for roles not present in the roster.
_DEFAULT_SPEC = ModelSpec("mistral:7b", _ECONOMY_LONG)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _openai_usage(resp: Any) -> tuple[int, int]:
    """Extract (prompt_tokens, completion_tokens) from an OpenAI-shaped
    response, tolerant of providers that omit the usage block."""
    u = getattr(resp, "usage", None)
    if u is None:
        return (0, 0)
    return (getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)


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
        self._aiml: Any = None  # lazily constructed (OpenAI SDK against the gateway)
        # One breaker per backend, so a down provider fails fast instead of
        # burning the full timeout on every analysis.
        self._breakers: dict[str, CircuitBreaker] = {}

    def _guarded(self, backend: str, factory):
        """Run a backend network call under a per-backend circuit breaker,
        normalizing any failure to LLMError (CircuitOpenError passes through)."""

        async def run():
            cb = self._breakers.get(backend)
            if cb is None:
                cb = CircuitBreaker(backend, failure_threshold=5, recovery_timeout=300.0)
                self._breakers[backend] = cb
            try:
                return await cb.call(factory)
            except (CircuitOpenError, LLMError):
                raise
            except Exception as exc:  # noqa: BLE001 — normalize to a typed transient error
                raise LLMError(f"{backend} call failed: {type(exc).__name__}: {exc}") from exc

        return run()

    # ------------------------------------------------------------------ #
    # Routing
    # ------------------------------------------------------------------ #
    def spec_for(self, role: str) -> ModelSpec:
        return ROSTER.get(role, _DEFAULT_SPEC)

    def _cloud_key(self) -> str:
        provider = settings.CLOUD_PROVIDER
        if provider == "aiml":
            return settings.AIML_API
        if provider == "openai":
            return settings.OPENAI_API_KEY
        return settings.ANTHROPIC_API_KEY

    def provider_for(self, role: str) -> str:
        """Return ``"ollama"``, ``"aiml"``, ``"anthropic"`` or ``"openai"``."""
        # Data residency overrides everything: never route off-host.
        if settings.LOCAL_ONLY:
            return "ollama"
        spec = self.spec_for(role)
        mode = settings.LLM_MODE.lower()
        wants_cloud = mode in ("cloud", "auto") and spec.cloud_capable
        if wants_cloud and self._cloud_key():
            return settings.CLOUD_PROVIDER
        if wants_cloud and mode == "cloud":
            logger.warning(
                "LLM_MODE=cloud but no %s key configured; role %r falling back to local Ollama.",
                settings.CLOUD_PROVIDER,
                role,
            )
        return "ollama"

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    async def _generate(
        self,
        provider: str,
        role: str,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, tuple[int, int]]:
        """Single timed entry point for every backend, so latency and token
        volume are recorded once per logical call (per role + provider)."""
        start = time.perf_counter()
        if provider == "ollama":
            text, usage = await self._ollama_generate(
                self.spec_for(role).local_model, prompt, system, images, temperature, json_mode
            )
        else:
            text, usage = await self._cloud_generate(
                provider, role, prompt, system, images, temperature, json_mode
            )
        record_llm_call(role, provider, time.perf_counter() - start, usage[0], usage[1])
        return text, usage

    async def complete_text(
        self,
        role: str,
        prompt: str,
        system: str = "",
        images: list[str] | None = None,
        temperature: float = 0.1,
    ) -> str:
        provider = self.provider_for(role)
        text, _ = await self._generate(provider, role, prompt, system, images, temperature, False)
        return text

    async def complete_json(
        self,
        role: str,
        prompt: str,
        system: str = "",
        images: list[str] | None = None,
        temperature: float = 0.1,
    ) -> dict:
        provider = self.provider_for(role)
        raw, _ = await self._generate(provider, role, prompt, system, images, temperature, True)
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMBadOutputError(f"role {role!r} returned unparseable JSON: {exc}") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using the local embedding model.

        Embeddings stay local regardless of LLM_MODE: they are cheap, run
        constantly, and keeping them deterministic avoids vector-space drift in
        the TAIG graph when cloud routing toggles.
        """
        model = self.spec_for("embedding").local_model
        vectors: list[list[float]] = []
        for text in texts:

            async def _do(t: str = text):
                r = await self._ollama.post("/api/embeddings", json={"model": model, "prompt": t})
                r.raise_for_status()
                return r

            resp = await self._guarded("ollama", _do)
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
    ) -> tuple[str, tuple[int, int]]:
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

        async def _do():
            r = await self._ollama.post("/api/generate", json=payload)
            r.raise_for_status()
            return r

        resp = await self._guarded("ollama", _do)
        data = resp.json()
        usage = (int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0)))
        return str(data.get("response", "")), usage

    async def _cloud_generate(
        self,
        provider: str,
        role: str,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, tuple[int, int]]:
        if provider == "aiml":
            return await self._aiml_generate(role, prompt, system, images, temperature, json_mode)
        if provider == "anthropic":
            return await self._anthropic_generate(prompt, system, images, temperature, json_mode)
        return await self._openai_generate(prompt, system, images, temperature, json_mode)

    async def _aiml_generate(
        self,
        role: str,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, tuple[int, int]]:
        """Generate via the aimlapi.com gateway (OpenAI-compatible).

        The gateway fronts 400+ models behind one key; the per-role model ID
        comes from the roster. ``response_format`` is deliberately NOT sent —
        it is not supported uniformly across gateway models, so JSON is
        enforced by instruction and parsed tolerantly by ``_extract_json``.
        """
        if self._aiml is None:
            from openai import AsyncOpenAI

            self._aiml = AsyncOpenAI(base_url=settings.AIML_BASE_URL, api_key=settings.AIML_API)

        text_prompt = prompt
        if json_mode:
            text_prompt += "\n\nRespond with a single valid JSON object only."
        user_content: list[dict] = [{"type": "text", "text": text_prompt}]
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

        resp = await self._guarded(
            "aiml",
            lambda: self._aiml.chat.completions.create(
                model=self.spec_for(role).cloud_model or _DEFAULT_SPEC.cloud_model,
                temperature=temperature,
                # Synthesis emits large structured JSON (full IRT + findings +
                # recommendations); 4096 truncated it mid-object. 8192 is safe
                # across the gateway's Claude/GPT/Gemini models.
                max_tokens=8192,
                messages=messages,
            ),
        )
        return resp.choices[0].message.content or "", _openai_usage(resp)

    async def _anthropic_generate(
        self,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, tuple[int, int]]:
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
        text = "".join(block.text for block in resp.content if block.type == "text")
        u = getattr(resp, "usage", None)
        usage = (getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0)
        return text, usage

    async def _openai_generate(
        self,
        prompt: str,
        system: str,
        images: list[str] | None,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, tuple[int, int]]:
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
        return resp.choices[0].message.content or "", _openai_usage(resp)

    async def close(self) -> None:
        await self._ollama.aclose()
        if self._aiml is not None:
            await self._aiml.close()


# Module-level singleton used across the cortex.
llm = LLMProvider()
