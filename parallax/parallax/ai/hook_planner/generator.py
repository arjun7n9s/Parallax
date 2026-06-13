import json
import logging
from typing import Dict, List, Optional, Tuple

from parallax.ai.hook_planner.parser import HookPlannerParser, HookPlannerParserError
from parallax.ai.hook_planner.prompt import HOOK_PLANNER_PROMPT
from parallax.ai.llm import llm

logger = logging.getLogger(__name__)


class HookPlannerGenerator:
    def __init__(self, parser: HookPlannerParser, max_retries: int = 3):
        """
        Args:
            parser: HookPlannerParser instance to validate the output
            max_retries: How many times to retry on grammar failure

        The model is selected by the unified provider via the "hook_planner"
        role (economy tier on the gateway, phi3:mini locally).
        """
        self.parser = parser
        self.max_retries = max_retries

    @property
    def api_dictionary(self) -> Dict:
        return self.parser.api_dictionary

    async def generate_hook(
        self,
        hypothesis_id: str,
        hypothesis_claim: str,
        package_name: str,
        permissions: List[str],
        api_dictionary: Dict,
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Returns (script, is_unresolved, reason).
        Retries up to max_retries times on grammar violation.
        """
        prompt = HOOK_PLANNER_PROMPT
        prompt = prompt.replace("{package_name}", package_name)
        prompt = prompt.replace("{permissions}", json.dumps(permissions))
        prompt = prompt.replace(
            "{hypotheses_json}", json.dumps([{"id": hypothesis_id, "claim": hypothesis_claim}])
        )
        prompt = prompt.replace("{api_dictionary_json}", json.dumps(api_dictionary, indent=2))

        for attempt in range(self.max_retries):
            raw = await llm.complete_text("hook_planner", prompt=prompt)
            try:
                # parser.parse returns (script, is_unresolved, reason)
                return self.parser.parse(raw)
            except HookPlannerParserError as e:
                logger.warning(f"Hook planner grammar violation on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    # Final attempt failed, mark as unresolved
                    return ("", True, f"parser_violation_after_{self.max_retries}_retries: {e}")

                # Inject error feedback into prompt for next retry
                prompt = (
                    prompt + f"\n\n# PREVIOUS ATTEMPT FAILED\n{e}\n# Fix the issue and try again."
                )

        return ("", True, "max_retries_exceeded")
