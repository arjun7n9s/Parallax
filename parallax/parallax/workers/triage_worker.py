import asyncio
import logging
import os
import tempfile
import uuid

from celery import Task
from sqlalchemy.future import select

from parallax.ai.agents.triage import run_triage
from parallax.ai.hypothesis.engine import HypothesisEngine
from parallax.analysis.ingestion.apkid_runner import run_apkid
from parallax.analysis.ingestion.ssdeep_runner import run_ssdeep
from parallax.core.database import async_session
from parallax.core.models import Submission
from parallax.core.storage import APK_BUCKET, get_minio_client
from parallax.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def async_to_sync(awaitable):
    """Utility to run an async function in a sync context like Celery."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we are already in an event loop, we can't use run_until_complete easily.
        # This typically doesn't happen in Celery workers.
        return asyncio.ensure_future(awaitable)
    return asyncio.run(awaitable)


class AsyncSQLAlchemyTask(Task):
    """A Celery Task base class that provides an async SQLAlchemy session."""

    abstract = True

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@celery_app.task(
    bind=True,
    base=AsyncSQLAlchemyTask,
    name="parallax.workers.triage_worker.run_triage_pipeline"
)
def run_triage_pipeline(self, submission_id_str: str):
    """
    Celery task that runs the full triage pipeline:
    1. Download APK from MinIO
    2. Run APKiD & ssdeep
    3. Run LLM Triage Agent
    4. Initialize Hypothesis Engine
    5. Update Submission status
    """
    logger.info(f"Starting triage pipeline for submission: {submission_id_str}")

    # Run the async pipeline inside the synchronous Celery task
    async_to_sync(_async_run_triage_pipeline(submission_id_str))


async def _async_run_triage_pipeline(submission_id_str: str):
    try:
        submission_id = uuid.UUID(submission_id_str)
    except ValueError:
        logger.error(f"Invalid submission ID: {submission_id_str}")
        return

    async with async_session() as db:
        # 1. Fetch submission
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()

        if not submission:
            logger.error(f"Submission {submission_id_str} not found in database.")
            return

        # Update status
        submission.status = "triaging"
        await db.commit()
        await db.refresh(submission)

        sha256 = submission.sha256

        # We need the APK locally. Let's download it from MinIO to a temp file.
        temp_dir = tempfile.mkdtemp()
        local_apk_path = os.path.join(temp_dir, f"{sha256}.apk")

        try:
            minio_client = get_minio_client()
            object_name = f"{sha256}.apk"
            minio_client.fget_object(APK_BUCKET, object_name, local_apk_path)

            logger.info(f"Downloaded APK {sha256} to {local_apk_path}")

            # 2. Run static pre-checks
            apkid_results = run_apkid(local_apk_path)
            ssdeep_results = run_ssdeep(local_apk_path)

            # We would extract permissions using androguard here, but for now we'll mock it
            # since full androguard integration is Phase 2.
            mock_metadata = {
                "package_name": submission.package_name or "com.example.malware",
                "app_name": "SampleApp",
                "file_size": submission.file_size,
                "apkid_matches": apkid_results.get("matches", {}),
                "ssdeep_match": ssdeep_results.get("hash", "Unknown"),
                "permissions": [
                    "android.permission.INTERNET",
                    "android.permission.BIND_ACCESSIBILITY_SERVICE",
                    "android.permission.RECEIVE_SMS",
                ],
            }

            # 3. Run LLM Triage Agent
            logger.info(f"Running LLM Triage Agent for {sha256}")
            triage_result = await run_triage(mock_metadata)

            # Update submission with triage results
            submission.triage_score = triage_result.get("pre_score", 0.0)
            submission.priority = triage_result.get("priority", "normal")

            # Save metadata JSON (which can include the triage output)
            submission.metadata_json = {
                "apkid": apkid_results,
                "ssdeep": ssdeep_results,
                "triage_raw": triage_result,
            }

            # 4. Initialize Hypothesis Engine
            engine = HypothesisEngine(db)
            logger.info(f"Seeding Hypothesis Engine for {sha256}")
            await engine.seed_initial_hypotheses(str(submission.id), sha256, triage_result)

            # 5. Transition to next stage
            submission.status = "static"
            await db.commit()
            logger.info(f"Triage complete for {sha256}. Status set to 'static'.")

        except Exception:
            logger.exception(f"Error during triage pipeline for {sha256}")
            submission.status = "failed"
            await db.commit()
        finally:
            # Cleanup temp file
            if os.path.exists(local_apk_path):
                os.remove(local_apk_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
