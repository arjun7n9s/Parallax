import asyncio
import logging
import os
import shutil
import tempfile
import uuid
import zipfile

from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from parallax.ai.hypothesis.engine import HypothesisEngine
from parallax.ai.re_workbench.artifact_model import (
    REArtifactModel,
    StaticAnalysisFeatures,
    YaraMatch,
)
from parallax.analysis.static.androguard_runner import run_androguard
from parallax.analysis.static.jadx_runner import run_jadx
from parallax.analysis.static.yara_runner import run_yara
from parallax.core.config import settings
from parallax.core.database import async_session

# Celery is optional in lightweight dev venvs (e.g. .venv-fast).
# When missing, fall back to a stub class so module import succeeds.
# Tests that mock at the function level will still work; only the
# @shared_task decorator will fail at runtime if celery is absent.
from parallax.core.errors import TransientError
from parallax.core.logging import bind_log_context, clear_log_context
from parallax.core.metrics import record_stage_failure
from parallax.core.models import Submission, TaintFlow
from parallax.core.storage import APK_BUCKET, DECOMPILED_BUCKET, get_minio_client
from parallax.workers.celery_app import celery_app
from parallax.workers.mixins import RetryableTask

logger = logging.getLogger(__name__)


def _run_flowdroid_taint(local_apk_path: str) -> list[dict]:
    """Run FlowDroid taint analysis (Phase 2.5). Returns flow dicts, [] on any
    failure — taint is additive evidence and must never block the pipeline."""
    if not settings.FLOWDROID_JAR:
        logger.info("FLOWDROID_JAR not configured; skipping taint analysis.")
        return []
    try:
        from parallax.analysis.static.flowdroid_runner import FlowDroidRunner

        runner = FlowDroidRunner(
            jar_path=settings.FLOWDROID_JAR,
            platforms_dir=settings.ANDROID_PLATFORMS_DIR or None,
        )
        flows = runner.run(local_apk_path, timeout=settings.FLOWDROID_TIMEOUT_SECONDS)
        logger.info(f"FlowDroid extracted {len(flows)} taint flows")
        return [
            {
                "source_class": f.source_class,
                "source_method": f.source_method,
                "sink_class": f.sink_class,
                "sink_method": f.sink_method,
                "path": f.path,
                "risk": f.risk,
                "attck_technique": f.attck_technique,
            }
            for f in flows
        ]
    except Exception as exc:
        logger.warning(f"FlowDroid taint analysis skipped: {exc}")
        return []


def async_to_sync(awaitable):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.ensure_future(awaitable)
    return asyncio.run(awaitable)


class AsyncSQLAlchemyTask(RetryableTask):
    abstract = True

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@celery_app.task(
    bind=True, base=AsyncSQLAlchemyTask, name="parallax.workers.static_worker.run_static_pipeline"
)
def run_static_pipeline(self, submission_id_str: str):
    logger.info(f"Starting static pipeline for submission: {submission_id_str}")
    async_to_sync(_async_run_static_pipeline(submission_id_str))


async def _async_run_static_pipeline(submission_id_str: str):
    bind_log_context(submission_id=submission_id_str, stage="static")
    try:
        submission_id = uuid.UUID(submission_id_str)
    except ValueError:
        logger.error(f"Invalid submission ID: {submission_id_str}")
        return

    async with async_session() as db:
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()

        if not submission:
            logger.error(f"Submission {submission_id_str} not found in database.")
            return

        # The submission status should already be "static" from triage_worker.
        # We proceed directly.

        sha256 = submission.sha256
        temp_dir = None
        jadx_out_dir = None

        try:
            temp_dir = tempfile.mkdtemp()
            local_apk_path = os.path.join(temp_dir, f"{sha256}.apk")
            jadx_out_dir = os.path.join(temp_dir, "jadx_out")

            minio_client = get_minio_client()
            object_name = f"{sha256}.apk"
            minio_client.fget_object(APK_BUCKET, object_name, local_apk_path)

            logger.info(f"Downloaded APK {sha256} to {local_apk_path}")

            # 1. Androguard
            androguard_res = run_androguard(local_apk_path)
            static_features = StaticAnalysisFeatures(
                package_name=androguard_res.get("package_name", "unknown"),
                app_name=androguard_res.get("app_name", "unknown"),
                version_name=androguard_res.get("version_name", ""),
                version_code=androguard_res.get("version_code", ""),
                min_sdk=androguard_res.get("min_sdk", ""),
                target_sdk=androguard_res.get("target_sdk", ""),
                main_activity=androguard_res.get("main_activity"),
                permissions=androguard_res.get("permissions", []),
                activities=androguard_res.get("activities", []),
                services=androguard_res.get("services", []),
                receivers=androguard_res.get("receivers", []),
                providers=androguard_res.get("providers", []),
                is_valid=androguard_res.get("is_valid", False),
            )

            # 2. YARA
            yara_res = run_yara(local_apk_path)
            yara_matches = [YaraMatch(**y) for y in yara_res]

            # 3. Jadx
            jadx_res = run_jadx(local_apk_path, jadx_out_dir)
            decompiled_s3_path = None

            if jadx_res["status"] == "success" and os.path.exists(jadx_out_dir):
                zip_path = os.path.join(temp_dir, f"{sha256}_decompiled.zip")

                # Zip the output
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(jadx_out_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, jadx_out_dir)
                            zipf.write(file_path, arcname)

                # Upload to MinIO
                decompiled_obj_name = f"{sha256}.zip"
                minio_client.fput_object(
                    bucket_name=DECOMPILED_BUCKET,
                    object_name=decompiled_obj_name,
                    file_path=zip_path,
                    content_type="application/zip",
                )
                decompiled_s3_path = f"s3://{DECOMPILED_BUCKET}/{decompiled_obj_name}"
                logger.info(f"Uploaded decompiled code to {decompiled_s3_path}")

            # 4. FlowDroid taint analysis (Phase 2.5) — persisted for the Cortex
            taint_dicts = _run_flowdroid_taint(local_apk_path)
            for flow in taint_dicts:
                db.add(
                    TaintFlow(
                        submission_id=submission.id,
                        source_class=flow["source_class"],
                        source_method=flow["source_method"],
                        sink_class=flow["sink_class"],
                        sink_method=flow["sink_method"],
                        path=flow["path"],
                        risk=flow["risk"],
                        attck_technique=flow["attck_technique"],
                    )
                )

            # 5. Build REArtifactModel
            artifact_model = REArtifactModel(
                sha256=sha256,
                static_features=static_features,
                yara_matches=yara_matches,
                jadx_output_dir=jadx_out_dir if jadx_res["status"] == "success" else None,
                decompiled_s3_path=decompiled_s3_path,
            )

            # 6. Save to submission metadata
            metadata_json = submission.metadata_json or {}
            metadata_json["re_workbench_artifact"] = artifact_model.to_dict()
            submission.metadata_json = metadata_json
            # JSONB columns are not change-tracked on in-place mutation; without
            # this the artifact is silently dropped and the cortex sees no code.
            flag_modified(submission, "metadata_json")

            # Update package name in submission if it was unknown
            if not submission.package_name and static_features.package_name != "unknown":
                submission.package_name = static_features.package_name

            # 7. Close the loop with Hypothesis Engine
            engine = HypothesisEngine(db)
            await engine.process_static_results(submission.id, artifact_model.to_dict())

            # 8. Transition to dynamic
            submission.status = "dynamic"
            await db.commit()
            logger.info(f"Static pipeline complete for {sha256}. Status set to 'dynamic'.")

        except TransientError:
            raise  # transient (infra/LLM/circuit-open): let Celery retry the task
        except Exception as exc:
            record_stage_failure("static", exc)
            logger.exception(f"Error during static pipeline for {sha256}")
            try:
                submission.status = "failed"
                await db.commit()
            except Exception:
                logger.error(f"Failed to commit failure status for {sha256}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            clear_log_context()
