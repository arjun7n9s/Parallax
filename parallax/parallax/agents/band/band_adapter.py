"""Band SDK and API adapter. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from parallax.core.config import settings

logger = logging.getLogger(__name__)


class BandAdapterError(RuntimeError):
    """Raised when a live Band API call cannot be completed."""


@dataclass(frozen=True)
class BandConfig:
    mode: str = settings.BAND_MODE
    rest_url: str = settings.BAND_REST_URL.rstrip("/")
    rest_api_key: str = settings.BAND_REST_API_KEY
    chatrooms_path: str = settings.BAND_CHATROOMS_PATH

    @property
    def live(self) -> bool:
        return self.mode.lower() == "live"


class BandAdapter:
    """Thin REST wrapper with deterministic mock mode for tests and demos."""

    def __init__(self, config: BandConfig | None = None):
        self.config = config or BandConfig()
        self._mock_messages: dict[str, list[dict[str, Any]]] = {}

    def create_chatroom(self, name: str, participants: list[str]) -> dict[str, Any]:
        if not self.config.live:
            room_id = (
                "mock-room-"
                + hashlib.sha256(f"{name}|{','.join(participants)}".encode("utf-8")).hexdigest()[
                    :12
                ]
            )
            self._mock_messages.setdefault(room_id, [])
            return {"id": room_id, "name": name, "participants": participants, "mock": True}

        payload = {"name": name, "participants": participants}
        return self._request("POST", self.config.chatrooms_path, json=payload)

    def post_message(
        self,
        room_id: str,
        *,
        sender_id: str,
        body: str,
        mentions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "sender_id": sender_id,
            "body": body,
            "mentions": mentions or [],
            "metadata": metadata or {},
        }
        if not self.config.live:
            message = {
                "id": "mock-msg-"
                + hashlib.sha256(
                    f"{room_id}|{sender_id}|{body}|{len(self._mock_messages.get(room_id, []))}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:12],
                "room_id": room_id,
                **payload,
                "mock": True,
            }
            self._mock_messages.setdefault(room_id, []).append(message)
            return message

        return self._request(
            "POST",
            f"{self.config.chatrooms_path}/{room_id}/messages",
            json=payload,
        )

    def get_messages(self, room_id: str, since: str | None = None) -> list[dict[str, Any]]:
        if not self.config.live:
            return list(self._mock_messages.get(room_id, []))
        params = {"since": since} if since else None
        response = self._request(
            "GET",
            f"{self.config.chatrooms_path}/{room_id}/messages",
            params=params,
        )
        if isinstance(response, list):
            return response
        return list(response.get("messages", []))

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any] | list[dict[str, Any]]:
        if not self.config.rest_api_key:
            raise BandAdapterError("BAND_REST_API_KEY is required when BAND_MODE=live")
        headers = {"Authorization": f"Bearer {self.config.rest_api_key}"}
        try:
            with httpx.Client(
                base_url=self.config.rest_url,
                headers=headers,
                timeout=30.0,
            ) as client:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Band API request failed: %s %s: %s", method, path, exc)
            raise BandAdapterError(str(exc)) from exc
