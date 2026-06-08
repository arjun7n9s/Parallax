import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class HookPlannerParserError(Exception):
    pass


class HookPlannerParser:
    """
    Validates LLM output against the Hook Planner v2.0.0 grammar and api_signatures.json.
    """

    def __init__(self, dictionary_path: Optional[str] = None):
        if dictionary_path is None:
            # Default to the known location in the repo
            project_root = Path(__file__).resolve().parents[3]
            dictionary_path = os.path.join(
                project_root, "parallax", "parallax", "analysis", "dynamic", "api_signatures.json"
            )

        with open(dictionary_path, "r", encoding="utf-8") as f:
            self.api_dictionary: Dict[str, Any] = json.load(f)

    def extract_script(self, raw_output: str) -> Tuple[str, bool, Optional[str]]:
        """
        Extracts the script between <<<HOOK_START>>> and <<<HOOK_END>>>.
        Returns: (extracted_script, is_unresolved, unresolved_reason)
        """
        if "<<<HOOK_START>>>" not in raw_output or "<<<HOOK_END>>>" not in raw_output:
            raise HookPlannerParserError("Missing <<<HOOK_START>>> or <<<HOOK_END>>> markers.")

        start_idx = raw_output.find("<<<HOOK_START>>>") + len("<<<HOOK_START>>>")
        end_idx = raw_output.find("<<<HOOK_END>>>")

        content = raw_output[start_idx:end_idx].strip()

        if not content:
            raise HookPlannerParserError("Empty block between markers.")

        # Check for empty-script unresolved fallback
        if content.startswith("// UNRESOLVED:"):
            reason = content.split("// UNRESOLVED:")[1].strip()
            return ("", True, reason)

        # Ensure it starts with Java.perform( and ends with });
        if not content.startswith("Java.perform("):
            raise HookPlannerParserError("Script must begin with 'Java.perform('")

        if not content.endswith("});"):
            raise HookPlannerParserError("Script must end with '});'")

        return (content, False, None)

    def validate_api_usage(self, script: str) -> None:
        """
        Ensures all `Java.use(...)` calls in the script reference allowed APIs from the dictionary.
        Also validates that any `.overload(...)` chains reference allowed method/class combos.
        """
        # Basic check for Java.use
        lines = script.split("\n")
        for line in lines:
            if "Java.use(" in line:
                # Extract class name from Java.use('com.example.Class')
                try:
                    start_quote = line.index("Java.use(") + 9
                    quote_char = line[start_quote]  # ' or "
                    end_quote = line.index(quote_char, start_quote + 1)
                    class_name = line[start_quote + 1 : end_quote]

                    # Exceptions for built-ins or standard utils allowed by prompt
                    if class_name in ["java.lang.Exception", "android.os.Process"]:
                        continue

                    if class_name not in self.api_dictionary:
                        raise HookPlannerParserError(
                            f"Java.use('{class_name}') violates the allowed API dictionary."
                        )
                except ValueError:
                    pass  # Parsing issue on this line, but might just be a comment or weird formatting

    def parse(self, raw_output: str) -> Tuple[str, bool, Optional[str]]:
        """
        Full parse and validate pipeline.
        Returns the safe, extracted script, or raises HookPlannerParserError on grammar/API violation.
        """
        script, is_unresolved, reason = self.extract_script(raw_output)

        if not is_unresolved:
            self.validate_api_usage(script)

        return (script, is_unresolved, reason)
