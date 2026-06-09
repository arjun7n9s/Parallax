import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from parallax.ai.hook_planner.generator import HookPlannerGenerator
from parallax.ai.hook_planner.parser import HookPlannerParser, HookPlannerParserError
from parallax.ai.ollama_client import ollama_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dynamic", tags=["Dynamic Analysis"])


class DynamicAnalysisRequest(BaseModel):
    submission_id: str
    hypothesis_id: str
    hypothesis_claim: str
    package_name: str
    permissions: list[str] = []

    model_config = ConfigDict(extra="ignore")


class DynamicAnalysisResponse(BaseModel):
    submission_id: str
    hypothesis_id: str
    script: Optional[str] = None
    is_unresolved: bool = False
    unresolved_reason: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# We initialize parser and generator once per worker process
_parser: Optional[HookPlannerParser] = None
_generator: Optional[HookPlannerGenerator] = None

def get_generator() -> HookPlannerGenerator:
    global _parser, _generator
    if _generator is None:
        _parser = HookPlannerParser()
        _generator = HookPlannerGenerator(ollama_client=ollama_client, parser=_parser, max_retries=3)
    return _generator


@router.post("/analyze", response_model=DynamicAnalysisResponse)
async def generate_dynamic_hook(
    request: DynamicAnalysisRequest,
    generator: HookPlannerGenerator = Depends(get_generator)
):
    """
    Generate a Frida hook for a specific hypothesis using the Hook Planner LLM.
    """
    logger.info(f"Generating dynamic hook for hypothesis {request.hypothesis_id} (Submission {request.submission_id})")

    try:
        script, is_unresolved, reason = await generator.generate_hook(
            hypothesis_id=request.hypothesis_id,
            hypothesis_claim=request.hypothesis_claim,
            package_name=request.package_name,
            permissions=request.permissions,
            api_dictionary=generator.api_dictionary,
        )

        return DynamicAnalysisResponse(
            submission_id=request.submission_id,
            hypothesis_id=request.hypothesis_id,
            script=script,
            is_unresolved=is_unresolved,
            unresolved_reason=reason
        )
    except HookPlannerParserError as e:
        logger.exception(f"Parser error for hypothesis {request.hypothesis_id}: {e}")
        raise HTTPException(status_code=422, detail=f"Hook planning failed: {e}")
    except Exception as e:
        logger.exception(f"Failed to generate hook for hypothesis {request.hypothesis_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
