"""Drive the full PARALLAX analysis pipeline in-process on one APK.

Usage:
    python scripts/run_pipeline.py samples/<sha256>.apk

Replicates the API submission (hashes + MinIO upload + Submission row), then
runs the real worker functions in sequence — triage -> static -> reasoning ->
delivery — the same code Celery would call. The dynamic/emulator stage is
skipped when no live device is configured (it would yield zero observations),
and that is stated in the output. Prints the literal verdict, two-layer risk
score, family attribution, IOC count and generated artifacts.
"""

import asyncio
import hashlib
import sys
import uuid

from sqlalchemy.future import select

from parallax.core.database import async_session
from parallax.core.models import IOC, Submission, TaintFlow
from parallax.core.storage import APK_BUCKET, REPORTS_BUCKET, get_minio_client


def _hashes(path: str):
    sha, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
    with open(path, "rb") as fh:
        while chunk := fh.read(8192):
            sha.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), md5.hexdigest(), size


def _disable_celery_chaining():
    """Stop each stage from enqueuing the next — we drive them ourselves."""
    for mod in (
        "parallax.workers.triage_worker",
        "parallax.workers.static_worker",
        "parallax.workers.reasoning_worker",
    ):
        __import__(mod)
    import parallax.workers.delivery_worker as dlw
    import parallax.workers.reasoning_worker as rw
    import parallax.workers.static_worker as sw
    import parallax.workers.triage_worker as tw

    class _NoDelay:
        def delay(self, *a, **k):
            return None

    # Each stage normally enqueues the next via .delay(); we drive them in order.
    # These tasks are imported inside the worker functions from their source
    # modules, so patch the source module attributes.
    tw.run_static_pipeline = _NoDelay()  # type: ignore[attr-defined]
    sw.run_static_pipeline = _NoDelay()  # type: ignore[attr-defined]
    rw.run_reasoning_pipeline = _NoDelay()  # type: ignore[attr-defined]
    dlw.run_delivery_pipeline = _NoDelay()  # type: ignore[attr-defined]


async def _seed(path: str) -> str:
    sha, md5, size = _hashes(path)
    client = get_minio_client()
    client.fput_object(
        APK_BUCKET, f"{sha}.apk", path, content_type="application/vnd.android.package-archive"
    )
    async with async_session() as db:
        existing = await db.execute(select(Submission).where(Submission.sha256 == sha))
        sub = existing.scalar_one_or_none()
        if sub:
            sub.status = "queued"
            sub.metadata_json = None
            sub.verdict = None
            sub.final_score = None
            await db.commit()
            return str(sub.id)
        sid = uuid.uuid4()
        db.add(
            Submission(
                id=sid,
                sha256=sha,
                md5=md5,
                file_name=path.split("/")[-1],
                file_size=size,
                status="queued",
                priority="normal",
                s3_path=f"s3://{APK_BUCKET}/{sha}.apk",
            )
        )
        await db.commit()
        return str(sid)


async def _set_status(sid: str, status: str):
    async with async_session() as db:
        res = await db.execute(select(Submission).where(Submission.id == uuid.UUID(sid)))
        sub = res.scalar_one()
        sub.status = status
        await db.commit()


def _pdf_pages(data: bytes) -> str:
    try:
        import io

        from pypdf import PdfReader  # type: ignore

        return str(len(PdfReader(io.BytesIO(data)).pages))
    except Exception:
        return f"~{data.count(b'/Type /Page') + data.count(b'/Type/Page')}"


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    apk = sys.argv[1]

    _disable_celery_chaining()
    from parallax.workers.reasoning_worker import _async_run_reasoning_pipeline
    from parallax.workers.static_worker import _async_run_static_pipeline
    from parallax.workers.triage_worker import _async_run_triage_pipeline

    sid = await _seed(apk)
    print(f"submission_id = {sid}\n")

    print(">>> STAGE 1/4 triage ...")
    await _async_run_triage_pipeline(sid)
    print(">>> STAGE 2/4 static ...")
    await _async_run_static_pipeline(sid)

    from parallax.core.config import settings

    if settings.DYNAMIC_LIVE_DEVICE:
        print(">>> STAGE 3/4 dynamic (LIVE emulator: frida + mitmproxy + DroidBot) ...")
        from parallax.workers.dynamic_worker import _async_run_dynamic_pipeline

        await _async_run_dynamic_pipeline(sid)  # transitions status to 'reasoning'
    else:
        print(
            ">>> STAGE 3/4 dynamic ... SKIPPED (DYNAMIC_LIVE_DEVICE=false; 0 runtime observations)"
        )
        await _set_status(sid, "reasoning")
    print(">>> STAGE 4/4 reasoning (AI cortex via aimlapi) ...")
    await _async_run_reasoning_pipeline(sid)

    # Delivery
    try:
        from parallax.workers.delivery_worker import _async_run_delivery

        print(">>> delivery (report/STIX/YARA) ...")
        await _async_run_delivery(sid)
    except Exception as exc:  # noqa: BLE001
        print(f"    delivery error: {type(exc).__name__}: {exc}")

    # ---- Literal results from the DB ----
    async with async_session() as db:
        res = await db.execute(select(Submission).where(Submission.id == uuid.UUID(sid)))
        sub = res.scalar_one()
        iocs = (await db.execute(select(IOC).where(IOC.submission_id == sub.id))).scalars().all()
        taints = (
            (await db.execute(select(TaintFlow).where(TaintFlow.submission_id == sub.id)))
            .scalars()
            .all()
        )
        meta = sub.metadata_json or {}
        cortex = meta.get("cortex_result", {})
        risk = cortex.get("risk", {})
        intel = cortex.get("intel_correlator", {})

    print("\n" + "=" * 60)
    print("RESULT (literal)")
    print("=" * 60)
    print(f"status             : {sub.status}")
    print(f"verdict            : {sub.verdict}")
    print(f"final_score        : {sub.final_score}")
    print(f"  evidence_score   : {risk.get('evidence_score')}")
    print(f"  calibrated_score : {risk.get('calibrated_score')}")
    print(f"  confidence_interval: {risk.get('confidence_interval')}")
    print(f"  components        : {risk.get('components')}")
    for note in risk.get("notes", []):
        print(f"  note             : {note}")
    print(
        f"family_attribution : {intel.get('family_attribution')!r} "
        f"(confidence {intel.get('family_confidence')})"
    )
    print(f"attck_techniques   : {cortex.get('attck_techniques')}")
    print(f"IOC rows (DB)      : {len(iocs)}")
    for i in iocs[:20]:
        print(f"    - {i.ioc_type}: {i.value}  [{i.confidence}]")
    print(f"taint_flows (DB)   : {len(taints)}")

    # Artifacts
    client = get_minio_client()
    try:
        objs = list(client.list_objects(REPORTS_BUCKET, prefix=f"{sid}/", recursive=True))
        print(f"artifacts          : {len(objs)}")
        for o in objs:
            extra = ""
            if o.object_name.endswith(".pdf"):
                data = client.get_object(REPORTS_BUCKET, o.object_name).read()
                extra = f"  pages={_pdf_pages(data)}"
            print(f"    - {o.object_name}  ({o.size:,} bytes){extra}")
    except Exception as exc:  # noqa: BLE001
        print(f"    artifact listing error: {exc}")

    return 0 if sub.verdict else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
