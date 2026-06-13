from unittest.mock import AsyncMock, patch

import pytest

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
                {
                    "params": [
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.String",
                        "android.app.PendingIntent",
                        "android.app.PendingIntent",
                    ]
                }
            ],
        }
    }
    dict_file = tmp_path / "api_signatures.json"
    dict_file.write_text(json.dumps(dict_content))
    return HookPlannerParser(dictionary_path=str(dict_file))


@pytest.fixture
def gen_llm():
    """Patch the unified provider's text completion used by the generator."""
    with patch(
        "parallax.ai.hook_planner.generator.llm.complete_text", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_generator_success_path(parser, gen_llm):
    gen_llm.return_value = """<<<HOOK_START>>>
Java.perform(function() {
    var SmsManager = Java.use('android.telephony.SmsManager');
});
<<<HOOK_END>>>"""

    generator = HookPlannerGenerator(parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is False
    assert "SmsManager" in script
    # The LLM was called exactly once, via the hook_planner role.
    gen_llm.assert_called_once()
    assert gen_llm.call_args[0][0] == "hook_planner"


@pytest.mark.asyncio
async def test_generator_retry_on_grammar_violation(parser, gen_llm):
    # First attempt: misses end marker. Second attempt: valid.
    gen_llm.side_effect = [
        "<<<HOOK_START>>>\nJava.perform(function() { });",
        "<<<HOOK_START>>>\nJava.perform(function() { var SmsManager = Java.use('android.telephony.SmsManager'); });\n<<<HOOK_END>>>",
    ]

    generator = HookPlannerGenerator(parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is False
    assert "SmsManager" in script
    assert gen_llm.call_count == 2

    # Check that error feedback was injected into the retry prompt.
    second_call_prompt = gen_llm.call_args_list[1][1]["prompt"]
    assert "# PREVIOUS ATTEMPT FAILED" in second_call_prompt
    assert "Missing <<<HOOK_START>>> or <<<HOOK_END>>> markers" in second_call_prompt


@pytest.mark.asyncio
async def test_generator_max_retries_exceeded(parser, gen_llm):
    # Always returns bad grammar.
    gen_llm.return_value = "This is not a valid script"

    generator = HookPlannerGenerator(parser, max_retries=2)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App sends SMS", "com.example.app", [], parser.api_dictionary
    )

    assert is_unresolved is True
    assert script == ""
    assert "parser_violation_after_2_retries" in reason
    assert gen_llm.call_count == 2


@pytest.mark.asyncio
async def test_generator_empty_script_handling(parser, gen_llm):
    gen_llm.return_value = """<<<HOOK_START>>>
// UNRESOLVED: native code
<<<HOOK_END>>>"""

    generator = HookPlannerGenerator(parser)
    script, is_unresolved, reason = await generator.generate_hook(
        "HYP-1", "App does native stuff", "com.example.app", [], {}
    )

    assert is_unresolved is True
    assert script == ""
    assert reason == "native code"
    gen_llm.assert_called_once()
