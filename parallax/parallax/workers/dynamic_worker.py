import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.future import select

from parallax.ai.hook_planner.generator import HookPlannerGenerator
from parallax.ai.hook_planner.parser import HookPlannerParser
from parallax.ai.ollama_client import ollama_client
from parallax.core.config import settings
from parallax.core.database import async_session
from parallax.core.models import ExperimentObservationLink, Hypothesis, Observation, Submission
from parallax.core.storage import APK_BUCKET, get_minio_client
from parallax.sandbox.runner import SandboxRunner
from parallax.workers.celery_app import celery_app

try:
    from celery import Task
except ImportError:
    Task = object  # type: ignore[assignment,misc]

STATIC_HOOK_MAP = {
    "sms": "sms_interception.js",
    "text message": "sms_interception.js",
    "message": "sms_interception.js",
    "accessibility": "accessibility_abuse.js",
    "abuse": "accessibility_abuse.js",
    "key": "keylogger.js",
    "keyboard": "keylogger.js",
    "input": "keylogger.js",
    "crypto": "crypto_extraction.js",
    "cipher": "crypto_extraction.js",
    "encrypt": "crypto_extraction.js",
    "decrypt": "crypto_extraction.js",
    "network": "network_logger.js",
    "http": "network_logger.js",
    "url": "network_logger.js",
}

logger = logging.getLogger(__name__)

_parser: Optional[HookPlannerParser] = None
_generator: Optional[HookPlannerGenerator] = None


def get_generator() -> HookPlannerGenerator:
    global _parser, _generator
    if _generator is None:
        _parser = HookPlannerParser()
        _generator = HookPlannerGenerator(ollama_client, _parser)
    return _generator


def async_to_sync(awaitable):
    """Utility to run an async function in a sync context like Celery."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.ensure_future(awaitable)
    return asyncio.run(awaitable)


class AsyncSQLAlchemyTask(Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@celery_app.task(
    bind=True, base=AsyncSQLAlchemyTask, name="parallax.workers.dynamic_worker.run_dynamic_pipeline"
)
def run_dynamic_pipeline(self, submission_id_str: str):
    """
    Celery task that runs the dynamic analysis pipeline:
    1. Downloads APK
    2. Fetches INVESTIGATING hypotheses
    3. Generates Frida hooks via HookPlanner
    4. Orchestrates Sandbox run
    5. Saves Observations
    """
    logger.info(f"Starting dynamic pipeline for submission: {submission_id_str}")
    async_to_sync(_async_run_dynamic_pipeline(submission_id_str))


async def _async_run_dynamic_pipeline(submission_id_str: str):
    try:
        submission_id = uuid.UUID(submission_id_str)
    except ValueError:
        logger.error(f"Invalid submission ID: {submission_id_str}")
        return

    temp_dir = None
    try:
        async with async_session() as db:
            result = await db.execute(select(Submission).where(Submission.id == submission_id))
            submission = result.scalar_one_or_none()

            if not submission:
                logger.error(f"Submission {submission_id_str} not found.")
                return

            # We will set status to dynamic later when the sandbox is actually starting.

            # 1. Download APK
            sha256 = submission.sha256
            temp_dir = tempfile.mkdtemp()
            local_apk_path = os.path.join(temp_dir, f"{sha256}.apk")

            minio_client = get_minio_client()
            minio_client.fget_object(APK_BUCKET, f"{sha256}.apk", local_apk_path)
            logger.info(f"Downloaded APK {sha256} for dynamic analysis")

            # 2. Fetch Hypotheses
            hypotheses_result = await db.execute(
                select(Hypothesis)
                .where(Hypothesis.submission_id == submission_id)
                .where(Hypothesis.status == "INVESTIGATING")
            )
            hypotheses = hypotheses_result.scalars().all()

            if not hypotheses:
                logger.info("No active hypotheses for dynamic analysis. Moving to reasoning.")
                submission.status = "reasoning"
                await db.commit()
                from parallax.workers.reasoning_worker import run_reasoning_pipeline

                run_reasoning_pipeline.delay(submission_id_str)
                return

            # 3. Generate Hooks
            generator = get_generator()

            combined_script = _build_script_prelude(submission_id_str)
            active_hypothesis_ids = []

            for hyp in hypotheses:
                try:
                    # Mocking permissions for now; in a real pipeline these come from static analysis
                    permissions = (
                        submission.metadata_json.get("permissions", [])
                        if submission.metadata_json
                        else []
                    )

                    script, is_unresolved, reason = await generator.generate_hook(
                        str(hyp.hypothesis_id),
                        hyp.claim,
                        submission.package_name or "com.example.malware",
                        permissions,
                        generator.api_dictionary,
                    )

                    if is_unresolved:
                        logger.info(
                            f"Hypothesis {hyp.hypothesis_id} unresolved: {reason}. Trying static fallback..."
                        )
                        claim_lower = hyp.claim.lower()
                        hook_file = None
                        for kw, fname in STATIC_HOOK_MAP.items():
                            if kw in claim_lower:
                                hook_file = fname
                                break

                        if hook_file:
                            hook_path = (
                                Path(__file__).parent.parent
                                / "analysis"
                                / "dynamic"
                                / "frida_hooks"
                                / hook_file
                            )
                            if hook_path.exists():
                                logger.info(
                                    f"Loaded static hook {hook_file} for claim: {hyp.claim}"
                                )
                                fallback_script = hook_path.read_text()
                                # Substitute placeholders
                                pkg = submission.package_name or "com.example.malware"
                                fallback_script = fallback_script.replace("{package_name}", pkg)
                                fallback_script = fallback_script.replace(
                                    "{hypothesis_id}", str(hyp.hypothesis_id)
                                )
                                combined_script += "\n" + fallback_script
                                active_hypothesis_ids.append(str(hyp.hypothesis_id))
                                continue
                            else:
                                logger.error(f"Static hook file not found at {hook_path}")

                        logger.info(
                            f"Hypothesis {hyp.hypothesis_id} unresolved and no static fallback found."
                        )
                        continue

                    combined_script += "\n" + script
                    active_hypothesis_ids.append(str(hyp.hypothesis_id))

                except Exception as e:
                    logger.error(f"Failed to generate hook for hypothesis {hyp.hypothesis_id}: {e}")

            if not active_hypothesis_ids:
                logger.warning(
                    "No valid hooks generated for any hypothesis. Proceeding anyway (maybe just network traffic)."
                )

            # 4. Orchestrate Sandbox Run
            submission.status = "dynamic"
            await db.commit()

            avd_manager = None
            if settings.DYNAMIC_LIVE_DEVICE:
                avd_manager = _provision_device(local_apk_path)

            sandbox = SandboxRunner(
                submission_id=submission_id_str,
                package_name=submission.package_name or "com.example.malware",
                apk_path=local_apk_path,
                avd_manager=avd_manager,
                drive_ui=avd_manager is not None,
            )

            observations_data = await sandbox.run_analysis(
                frida_script=combined_script,
                timeout_seconds=settings.DYNAMIC_TIMEOUT_SECONDS,
            )

            # 5. Save Observations
            for i, obs_payload in enumerate(observations_data):
                new_obs = Observation(
                    submission_id=submission_id,
                    source="mitmproxy" if obs_payload.get("hook") == "mitmproxy.http" else "frida",
                    event_type=obs_payload.get("hook", "unknown"),
                    thread_id=obs_payload.get("thread_id"),
                    thread_name=obs_payload.get("thread_name"),
                    caller_package=obs_payload.get("caller_package"),
                    args=obs_payload.get("args"),
                    return_value=obs_payload.get("return_value"),
                    exception=obs_payload.get("exception"),
                    captured_at_ms=obs_payload.get("captured_at_ms", 0),
                    session_id=obs_payload.get("session_id"),
                )
                db.add(new_obs)

                # Must flush so that new_obs gets its auto-generated UUID assigned
                # otherwise new_obs.id is None when creating the link
                await db.flush()

                hyp_id_str = obs_payload.get("hypothesis_id")
                if hyp_id_str:
                    link = ExperimentObservationLink(
                        hypothesis_id=hyp_id_str, observation_id=new_obs.id
                    )
                    db.add(link)

                if (i + 1) % 50 == 0:
                    await db.commit()

            await db.commit()
            logger.info(f"Saved {len(observations_data)} observations for {sha256}")

            # 6. Transition to next stage
            submission.status = "reasoning"
            await db.commit()
            logger.info(f"Dynamic complete for {sha256}. Status set to 'reasoning'.")

            # Trigger reasoning pipeline (AI Cortex).
            from parallax.workers.reasoning_worker import run_reasoning_pipeline

            run_reasoning_pipeline.delay(submission_id_str)

    except Exception:
        logger.exception(f"Error during dynamic pipeline for {submission_id_str}")
        try:
            async with async_session() as db:
                result = await db.execute(select(Submission).where(Submission.id == submission_id))
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = "failed"
                    await db.commit()
        except Exception:
            pass
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def _provision_device(local_apk_path: str):
    """Provision a live emulator/device for dynamic analysis.

    Installs the APK, ensures frida-server and the mitmproxy CA are present, and
    routes traffic through the proxy. Returns the AVDManager, or ``None`` if the
    device could not be provisioned (the run then falls back to frida+mitm only).
    """
    try:
        from parallax.analysis.dynamic.avd_manager import AVDManager
        from parallax.analysis.dynamic.install import (
            get_default_frida_server_path,
            install_frida_server,
        )

        avd = AVDManager()
        if not avd.is_running():
            avd.boot()
        avd.install_apk(local_apk_path)

        if not avd.is_frida_running():
            try:
                install_frida_server(avd, get_default_frida_server_path(avd))
            except Exception as exc:
                logger.warning("frida-server setup skipped: %s", exc)

        # Route device HTTP(S) through the in-process mitmproxy.
        try:
            avd.shell(f"settings put global http_proxy 127.0.0.1:{8080}")
        except Exception as exc:
            logger.warning("proxy configuration skipped: %s", exc)

        return avd
    except Exception as exc:
        logger.warning("Device provisioning failed; running without live UI: %s", exc)
        return None


def _build_script_prelude(session_id: str) -> str:
    """
    Builds the JS prelude to define the HookRegistry and Session ID.
    """
    return f"""
// === PARALLAX PRELUDE ===
setImmediate(() => {{
    globalThis.SESSION_ID = "{session_id}";
    globalThis.HookRegistry = {{
        _hooks: {{}},
        isHooked: function(hookId) {{ return !!this._hooks[hookId]; }},
        markHooked: function(hookId) {{ this._hooks[hookId] = true; }}
    }};
}});
// ========================
"""
