"""Run a local Postgres backup/restore drill against docker compose.

The drill:
1. pg_dump's the source DB inside the Postgres container.
2. Restores it into a disposable restore DB.
3. Starts a temporary API pointed at the restored DB.
4. Verifies /api/v1/history can read prior submissions.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parallax.core.config import settings


def _run(args: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(args, check=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else ""


def _docker_exec(container: str, *args: str, capture: bool = False) -> str:
    return _run(["docker", "exec", container, *args], capture=capture)


def _psql_scalar(container: str, user: str, db: str, sql: str) -> str:
    return _docker_exec(container, "psql", "-U", user, "-d", db, "-tAc", sql, capture=True)


def _get_json(url: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(1)
    raise RuntimeError(f"Restored API did not serve history before timeout: {last_error}")


def _wait_for_history(port: int, timeout_seconds: int) -> dict:
    url = f"http://127.0.0.1:{port}{settings.API_V1_STR}/history?page_size=1"
    return _get_json(url, timeout_seconds)


def _verify_report_artifact(container: str, user: str, db: str, port: int) -> None:
    submission_id = _psql_scalar(
        container,
        user,
        db,
        """
        SELECT id::text
        FROM submissions
        WHERE metadata_json ? 'delivery_artifacts'
        LIMIT 1
        """,
    )
    if not submission_id:
        return
    url = f"http://127.0.0.1:{port}{settings.API_V1_STR}/analysis/{submission_id}/report.pdf"
    with urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"Restored API report fetch returned {response.status}")
        if len(response.read()) < 100:
            raise RuntimeError("Restored API report fetch returned an unexpectedly small body.")


def _start_restored_api(restore_db: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["POSTGRES_DB"] = restore_db
    env["API_KEY"] = ""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "parallax.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def drill(args: argparse.Namespace) -> None:
    source_db = args.source_db
    restore_db = args.restore_db or f"{source_db}_restore_drill"
    if restore_db in {source_db, "postgres", "template0", "template1"}:
        raise RuntimeError("Restore database must be disposable and distinct from the source DB.")

    source_count = int(
        _psql_scalar(args.container, args.user, source_db, "SELECT count(*) FROM submissions")
    )
    if source_count < 1:
        raise RuntimeError(
            "Source database has no submissions; seed or submit a sample before DR drill."
        )

    dump_path = f"/tmp/{restore_db}.dump"
    _docker_exec(args.container, "rm", "-f", dump_path)
    _docker_exec(args.container, "pg_dump", "-U", args.user, "-Fc", "-f", dump_path, source_db)
    _docker_exec(args.container, "dropdb", "-U", args.user, "--if-exists", restore_db)
    _docker_exec(args.container, "createdb", "-U", args.user, restore_db)
    _docker_exec(args.container, "pg_restore", "-U", args.user, "-d", restore_db, dump_path)

    restored_count = int(
        _psql_scalar(args.container, args.user, restore_db, "SELECT count(*) FROM submissions")
    )
    if restored_count != source_count:
        raise RuntimeError(
            f"Restored submission count mismatch: source={source_count}, restored={restored_count}"
        )

    api = None
    try:
        if not args.skip_api:
            api = _start_restored_api(restore_db, args.api_port)
            history = _wait_for_history(args.api_port, args.api_timeout)
            if int(history.get("total", 0)) < 1:
                raise RuntimeError("Restored API served history but returned no submissions.")
            _verify_report_artifact(args.container, args.user, restore_db, args.api_port)
    finally:
        if api is not None:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
        if args.cleanup:
            _docker_exec(args.container, "dropdb", "-U", args.user, "--if-exists", restore_db)
            _docker_exec(args.container, "rm", "-f", dump_path)

    print(
        "Postgres restore drill passed: "
        f"source_db={source_db} restore_db={restore_db} submissions={restored_count}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="parallax_postgres")
    parser.add_argument("--user", default=settings.POSTGRES_USER)
    parser.add_argument("--source-db", default=settings.POSTGRES_DB)
    parser.add_argument("--restore-db", default="")
    parser.add_argument("--api-port", type=int, default=8010)
    parser.add_argument("--api-timeout", type=int, default=45)
    parser.add_argument("--skip-api", action="store_true")
    parser.add_argument("--no-cleanup", dest="cleanup", action="store_false")
    parser.set_defaults(cleanup=True)
    return parser.parse_args()


if __name__ == "__main__":
    drill(parse_args())
