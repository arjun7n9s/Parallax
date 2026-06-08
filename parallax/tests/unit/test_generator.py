import pytest
from unittest.mock import AsyncMock

from parallax.ai.hook_planner.generator import HookPlannerGenerator
from parallax.ai.hook_planner.parser import HookPlannerParser


@pytest.fixture
def parser(tmp_path):
    import json
    # Mock dictionary
    dict_content = {
        "android.telephony.SmsManager": {
            "method": "sendTextMessage",
            "overloads": [
                {"params": ["java.lang.String", "java.lang.String", "java.lang.String", "android.app.PendingIntent", "android.app.PendingIntent"]}
            ]
        }
    }
    dict_file = tmp_path / "api_signatures.json"
    dict_file.write_text(json.dumps(dict_content))
    return HookPlannerParser(dictionary_path=str(dict_file))


@pytest.fixture
def ollama_client():
    client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_generator_success_path(parser, ollama_client):
    ollama_client.generate.return_value = """<<<HOOK_START>>>
Java.perform(function() {
    var SmsManager = Java.use('android.telephony.SmsManager');
});
<<<HOOK_END>>>"""

    generator = HookPlannerGenerator(ollama_client, parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is False
    assert "SmsManager" in script
    # The LLM was called exactly once
    ollama_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_generator_retry_on_grammar_violation(parser, ollama_client):
    # First attempt: misses end marker
    # Second attempt: valid
    ollama_client.generate.side_effect = [
        "<<<HOOK_START>>>\nJava.perform(function() { });",
        "<<<HOOK_START>>>\nJava.perform(function() { var SmsManager = Java.use('android.telephony.SmsManager'); });\n<<<HOOK_END>>>"
    ]

    generator = HookPlannerGenerator(ollama_client, parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is False
    assert "SmsManager" in script
    assert ollama_client.generate.call_count == 2
    
    # Check that error feedback was injected
    second_call_prompt = ollama_client.generate.call_args_list[1][1]['prompt']
    assert "# PREVIOUS ATTEMPT FAILED" in second_call_prompt
    assert "Missing <<<HOOK_START>>> or <<<HOOK_END>>> markers" in second_call_prompt


@pytest.mark.asyncio
async def test_generator_max_retries_exceeded(parser, ollama_client):
    # Always returns bad grammar
    ollama_client.generate.return_value = "This is not a valid script"

    generator = HookPlannerGenerator(ollama_client, parser, max_retries=2)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is True
    assert script == ""
    assert "parser_violation_after_2_retries" in reason
    assert ollama_client.generate.call_count == 2


@pytest.mark.asyncio
async def test_generator_empty_script_handling(parser, ollama_client):
    ollama_client.generate.return_value = """<<<HOOK_START>>>
// UNRESOLVED: native code
<<<HOOK_END>>>"""

    generator = HookPlannerGenerator(ollama_client, parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App does native stuff", "com.example.app", [], {}
    )

    assert is_unresolved is True
    assert script == ""
    assert reason == "native code"
    ollama_client.generate.assert_called_once()
