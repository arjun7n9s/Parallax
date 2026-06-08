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

        if not os.path.exists(dictionary_path):
            raise FileNotFoundError(
                f"API dictionary not found at {dictionary_path}. "
                f"Pass dictionary_path explicitly to HookPlannerParser()."
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
            # Use the first line only to avoid capturing junk
            first_line = content.split("\n")[0]
            reason = first_line.split("// UNRESOLVED:", 1)[1].strip()
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
        import re

        # Extract all classes used: Java.use('some.class')
        used_classes = re.findall(r"Java\.use\(['\"]([\w.$]+)['\"]\)", script)
        for class_name in used_classes:
            if class_name in ["java.lang.Exception", "android.os.Process"]:
                continue
            if class_name not in self.api_dictionary:
                raise HookPlannerParserError(f"Java.use('{class_name}') violates the allowed API dictionary.")

        # Extract all overloads: someVar.methodName.overload('type1', 'type2')
        # This is a basic regex to catch the pattern. We extract the method name and the arguments string.
        # It assumes standard formatting like .methodName.overload(...)
        overload_matches = re.findall(r"\.(\w+)\.overload\(([^)]*)\)", script)
        for method_name, args_str in overload_matches:
            # Normalize whitespace (handles multi-line overload declarations)
            args_str = re.sub(r"\s+", " ", args_str).strip()
            # Process the arguments string: split by comma, strip whitespace and quotes
            args_list = [arg.strip(" '\"") for arg in args_str.split(",")] if args_str else []
            
            # Find which class(es) have this method in the dictionary to check the overload
            found_method = False
            valid_overload = False
            
            for class_name, definition in self.api_dictionary.items():
                if definition.get("method") == method_name:
                    found_method = True
                    for overload in definition.get("overloads", []):
                        if overload.get("params") == args_list:
                            valid_overload = True
                            break
                    if valid_overload:
                        break
            
            # If the method exists in the dict, but we didn't find the matching overload:
            if found_method and not valid_overload:
                raise HookPlannerParserError(f"Method '{method_name}' with overload params {args_list} is not allowed.")

    def parse(self, raw_output: str) -> Tuple[str, bool, Optional[str]]:
        """
        Full parse and validate pipeline.
        Returns the safe, extracted script, or raises HookPlannerParserError on grammar/API violation.
        """
        script, is_unresolved, reason = self.extract_script(raw_output)

        if not is_unresolved:
            self.validate_api_usage(script)

        return (script, is_unresolved, reason)
