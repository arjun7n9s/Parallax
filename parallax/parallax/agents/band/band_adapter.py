"""Offline Band adapter for PARALLAX demos. Part of PARALLAX x Band integration. See Claude/band_plan.md.

Live Band agents are not driven through PARALLAX REST pushes. They run as
remote-agent processes over the Band SDK/WebSocket runtime; see
``band_orchestrator.py``. This adapter intentionally stays mock-only so local
tests and transcript generation keep working without implying the wrong API.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from parallax.core.config import settings


class BandAdapterError(RuntimeError):
    """Raised when a caller tries to use mock-only helpers as live transport."""


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
    """Deterministic in-memory Band room for offline demos and tests."""

    def __init__(self, config: BandConfig | None = None):
        self.config = config or BandConfig()
        self._mock_messages: dict[str, list[dict[str, Any]]] = {}

    def create_chatroom(self, name: str, participants: list[str]) -> dict[str, Any]:
        if self.config.live:
            raise BandAdapterError(
                "Live Band rooms are created by SDK-connected remote agents, "
                "not the offline BandAdapter. Use band_orchestrator.py."
            )
        room_id = (
            "mock-room-"
            + hashlib.sha256(f"{name}|{','.join(participants)}".encode("utf-8")).hexdigest()[:12]
        )
        self._mock_messages.setdefault(room_id, [])
        return {"id": room_id, "name": name, "participants": participants, "mock": True}

    def post_message(
        self,
        room_id: str,
        *,
        sender_id: str,
        body: str,
        mentions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.config.live:
            raise BandAdapterError(
                "Live Band messages are sent by SDK-connected remote agents, "
                "not the offline BandAdapter. Use band_orchestrator.py."
            )
        payload = {
            "sender_id": sender_id,
            "body": body,
            "mentions": mentions or [],
            "metadata": metadata or {},
        }
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

    def get_messages(self, room_id: str, since: str | None = None) -> list[dict[str, Any]]:
        if self.config.live:
            raise BandAdapterError(
                "Live Band transcript reads should use the Band Agent API/context endpoint."
            )
        return list(self._mock_messages.get(room_id, []))
