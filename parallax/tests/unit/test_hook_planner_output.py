import os
import pytest
from pathlib import Path

from parallax.ai.hook_planner.parser import HookPlannerParser, HookPlannerParserError
from parallax.ai.hook_planner.prompt import HOOK_PLANNER_PROMPT


@pytest.fixture
def parser():
    """Returns a HookPlannerParser initialized with the actual api_signatures.json"""
    # Assuming test is run from project root or parallax/
    project_root = Path(__file__).resolve().parents[3]
    dict_path = project_root / "parallax" / "parallax" / "analysis" / "dynamic" / "api_signatures.json"
    
    if not dict_path.exists():
        pytest.skip(f"Dictionary not found at {dict_path}")
        
    return HookPlannerParser(dictionary_path=str(dict_path))


def test_grammar_start_marker_required(parser):
    output = "Java.perform(function() { });\n<<<HOOK_END>>>"
    with pytest.raises(HookPlannerParserError, match="Missing <<<HOOK_START>>>"):
        parser.parse(output)


def test_grammar_end_marker_required(parser):
    output = "<<<HOOK_START>>>\nJava.perform(function() { });"
    with pytest.raises(HookPlannerParserError, match="Missing <<<HOOK_START>>> or <<<HOOK_END>>>"):
        parser.parse(output)


def test_grammar_empty_script_form_valid(parser):
    output = "<<<HOOK_START>>>\n// UNRESOLVED: native code behavior requires Phase 3.5\n<<<HOOK_END>>>"
    script, is_unresolved, reason = parser.parse(output)
    assert is_unresolved is True
    assert script == ""
    assert reason == "native code behavior requires Phase 3.5"


def test_grammar_example_itself_is_valid(parser):
    """
    Extracts the example directly from the v2.0.0 prompt and verifies it parses cleanly.
    This ensures the example we show the LLM is fully compliant with our own parser.
    """
    prompt = HOOK_PLANNER_PROMPT
    start_example = prompt.rfind("<<<HOOK_START>>>")
    end_example = prompt.rfind("<<<HOOK_END>>>") + len("<<<HOOK_END>>>")
    example_output = prompt[start_example:end_example]

    script, is_unresolved, reason = parser.parse(example_output)
    
    assert is_unresolved is False
    assert script.startswith("Java.perform(")
    assert script.endswith("});")
    assert "SmsManager.sendTextMessage" in script


def test_dictionary_all_java_use_calls_match_dictionary(parser):
    output = """<<<HOOK_START>>>
Java.perform(function() {
    var Valid = Java.use('android.telephony.SmsManager');
    var Invalid = Java.use('com.hacker.MadeUpClass');
});
<<<HOOK_END>>>"""
    with pytest.raises(HookPlannerParserError, match="violates the allowed API dictionary"):
        parser.parse(output)


def test_dictionary_inner_class_dollar_sign_preserved(parser):
    output = """<<<HOOK_START>>>
Java.perform(function() {
    var Secure = Java.use('android.provider.Settings$Secure');
});
<<<HOOK_END>>>"""
    script, is_unresolved, reason = parser.parse(output)
    assert is_unresolved is False
    assert "android.provider.Settings$Secure" in script


def test_session_id_referenced_in_payload():
    """Ensures the example payload explicitly references globalThis.SESSION_ID"""
    assert "globalThis.SESSION_ID" in HOOK_PLANNER_PROMPT


def test_caller_package_uses_placeholder_not_hardcoded():
    """Ensures the LLM is instructed to use the Python template placeholder"""
    assert "{package_name}" in HOOK_PLANNER_PROMPT


def test_exception_capture_uses_stack_or_tostring():
    """Ensures the exception capture grabs the full stack trace if available"""
    assert "e.stack ? e.stack : e.toString()" in HOOK_PLANNER_PROMPT


def test_rate_limit_counter_present():
    """Ensures the rate limiter threshold rule is present"""
    assert ">100 times in the last 60 seconds" in HOOK_PLANNER_PROMPT


def test_try_catch_wraps_original_call():
    """Ensures the original call is wrapped in try/catch in the example"""
    assert "try {" in HOOK_PLANNER_PROMPT
    assert "} catch (e) {" in HOOK_PLANNER_PROMPT


def test_args_is_named_object_not_positional():
    """Ensures the schema explicitly asks for named arguments"""
    assert "Extract arguments as a JSON object with parameter names as keys" in HOOK_PLANNER_PROMPT


def test_hook_registry_check_present():
    """Ensures the deduplication / Identity reuse logic is present"""
    assert "globalThis.HookRegistry.isHooked" in HOOK_PLANNER_PROMPT

# TODO: Add test_llm_produces_valid_output_for_sms_hypothesis (integration test)
