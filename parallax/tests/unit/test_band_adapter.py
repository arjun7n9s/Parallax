"""Tests for the Band REST adapter mock path."""

from __future__ import annotations

import pytest

from parallax.agents.band.band_adapter import BandAdapter, BandAdapterError, BandConfig


def test_mock_adapter_creates_room_and_records_messages():
    adapter = BandAdapter(BandConfig(mode="mock"))

    room = adapter.create_chatroom("PARALLAX CASE", ["agent-a"])
    message = adapter.post_message(
        room["id"],
        sender_id="agent-a",
        body="hello",
        mentions=["agent-b"],
        metadata={"kind": "test"},
    )

    assert room["mock"] is True
    assert message["mock"] is True
    assert adapter.get_messages(room["id"]) == [message]


def test_live_adapter_requires_rest_key():
    adapter = BandAdapter(BandConfig(mode="live", rest_api_key=""))

    with pytest.raises(BandAdapterError, match="SDK-connected remote agents"):
        adapter.create_chatroom("PARALLAX CASE", ["agent-a"])


def test_live_adapter_does_not_fake_message_transport():
    adapter = BandAdapter(BandConfig(mode="live", rest_api_key="test-key"))

    with pytest.raises(BandAdapterError, match="SDK-connected remote agents"):
        adapter.post_message("room-1", sender_id="agent-a", body="hello")
