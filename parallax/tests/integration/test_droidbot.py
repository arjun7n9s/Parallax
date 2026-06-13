"""
Integration tests for DroidBotGPT UI exploration loop.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parallax.analysis.dynamic.avd_manager import AVDManager
from parallax.analysis.dynamic.droidbot_gpt import DroidBotGPT, hashlib_md5_signature

# Sample UI dump XML for testing parser
MOCK_XML_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]">
    <node index="0" text="Settings" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[44,117][261,166]" clickable="false" enabled="true" />
    <node index="1" text="Search" resource-id="com.android.settings:id/search_action_bar" class="android.widget.Button" package="com.android.settings" bounds="[948,98][1036,186]" clickable="true" enabled="true" />
    <node index="2" text="" resource-id="com.android.settings:id/input_field" class="android.widget.EditText" package="com.android.settings" bounds="[100,200][900,300]" clickable="true" enabled="true" />
  </node>
</hierarchy>
"""


@pytest.fixture
def mock_avd():
    avd = MagicMock(spec=AVDManager)
    avd.adb_bin = "adb"
    avd.device_id = "127.0.0.1:5555"
    avd.shell.return_value = "UI hierarchy dumped to: /sdcard/window_dump.xml"
    return avd


def test_droidbot_parse_ui_xml(mock_avd):
    bot = DroidBotGPT(
        avd_manager=mock_avd, package_name="com.example.malware", session_id="test_session"
    )
    elements = bot.parse_ui_xml(MOCK_XML_CONTENT)

    # Text view has text, button is clickable, edit text is class-based interactive. All should be included.
    assert len(elements) == 3

    # Check Settings TextView
    assert elements[0]["text"] == "Settings"
    assert elements[0]["resource_id"] == "android:id/title"
    assert elements[0]["clickable"] is False

    # Check Search Button
    assert elements[1]["text"] == "Search"
    assert elements[1]["clickable"] is True
    assert elements[1]["center"] == (992, 142)  # (948+1036)//2, (98+186)//2

    # Check EditText
    assert elements[2]["class"] == "android.widget.EditText"
    assert elements[2]["center"] == (500, 250)


def test_hashlib_md5_signature():
    elements1 = [{"id": 0, "resource_id": "btn", "text": "Click", "bounds": "[0,0][10,10]"}]
    elements2 = [{"id": 0, "resource_id": "btn", "text": "Click", "bounds": "[0,0][10,10]"}]
    elements3 = [{"id": 0, "resource_id": "btn", "text": "Double Click", "bounds": "[0,0][10,10]"}]

    sig1 = hashlib_md5_signature(elements1)
    sig2 = hashlib_md5_signature(elements2)
    sig3 = hashlib_md5_signature(elements3)

    assert sig1 == sig2
    assert sig1 != sig3


def test_execute_action_tap(mock_avd):
    bot = DroidBotGPT(
        avd_manager=mock_avd, package_name="com.example.malware", session_id="test_session"
    )
    elements = bot.parse_ui_xml(MOCK_XML_CONTENT)

    action = {"action_type": "tap", "element_id": 1, "reason": "Test click"}
    summary = bot.execute_action(action, elements)

    assert "Tap element 1" in summary
    mock_avd.shell.assert_any_call("input tap 992 142")


def test_execute_action_text(mock_avd):
    bot = DroidBotGPT(
        avd_manager=mock_avd, package_name="com.example.malware", session_id="test_session"
    )
    elements = bot.parse_ui_xml(MOCK_XML_CONTENT)

    action = {"action_type": "text", "element_id": 2, "text": "hello world", "reason": "Test input"}
    summary = bot.execute_action(action, elements)

    assert "Input text 'hello world'" in summary
    mock_avd.shell.assert_any_call("input tap 500 250")
    # Spaces replaced by %s in adb input text
    mock_avd.shell.assert_any_call("input text hello%sworld")


@pytest.mark.asyncio
@patch("parallax.analysis.dynamic.droidbot_gpt.llm")
@patch("parallax.analysis.dynamic.droidbot_gpt.get_minio_client")
async def test_run_exploration(mock_get_minio, mock_llm, mock_avd):
    # Mock minio and the LLM provider
    mock_minio_client = MagicMock()
    mock_get_minio.return_value = mock_minio_client

    # We want select_action to return "done" on the second turn
    mock_llm.complete_json = AsyncMock()
    mock_llm.complete_json.side_effect = [
        {"action_type": "tap", "element_id": 1, "reason": "Explore search"},
        {"action_type": "done", "reason": "Completed testing"},
    ]

    # Mock AVD shell calls dynamically based on command content
    def dynamic_shell(command, *args, **kwargs):
        cmd_lower = command.lower()
        if "uiautomator dump" in cmd_lower:
            return "UI hierarchy dumped to: /sdcard/window_dump.xml"
        elif "cat" in cmd_lower and "window_dump.xml" in cmd_lower:
            return MOCK_XML_CONTENT
        elif "base64" in cmd_lower:
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        return "OK"

    mock_avd.shell.side_effect = dynamic_shell

    bot = DroidBotGPT(
        avd_manager=mock_avd, package_name="com.example.malware", session_id="test_session"
    )
    await bot.run_exploration(max_turns=2)

    assert len(bot.history) == 2
    assert bot.history[0]["action"].startswith("Tap element 1")
    assert "done" in bot.history[1]["decision"]["action_type"]

    # Verify minio put_object was called for both screenshots
    assert mock_minio_client.put_object.call_count == 2
